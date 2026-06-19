#include <iostream>
#include <vector>
#include <numeric>
#include <cstdlib>
#include <ctime>
#include <unistd.h> // sleep 기능
#include <fstream>  // 파일 저장
#include <iomanip>  // 시간 포맷 설정
#include <sstream>  // 문자열 조립

using namespace std;

enum ErrorCode {
    NORMAL = 0,
    NEED_INSPECTION = 101, 
    IMMEDIATE_STOP = 102   
};

struct VibrationLog {
    string timestamp;
    int total_vibrations;
    int error_code;
};

string getTimeForFilename() {
    time_t now = time(0);
    struct tm tstruct;
    char buf[80];
    tstruct = *localtime(&now);
    strftime(buf, sizeof(buf), "%Y%m%d_%H%M%S", &tstruct);
    return string(buf);
}

string getCurrentTime() {
    time_t now = time(0);
    struct tm tstruct;
    char buf[80];
    tstruct = *localtime(&now);
    strftime(buf, sizeof(buf), "%Y-%m-%d %H:%M:%S", &tstruct);
    return string(buf);
}

int main() {
    srand(time(NULL));

    cout << "==================================================" << endl;
    cout << "  1호기 비상 진동 4회 누적 시 셧다운 시스템 가동 " << endl;
    cout << "==================================================" << endl;

    vector<VibrationLog> periodic_buffer;
    int elapsed_seconds = 0; 
    int SAVE_INTERVAL = 30; // 30초 주기 (실제 30분 가상)
    
    // [핵심 추가] 16회 이상 비상 진동이 발생한 횟수를 기억할 누적 카운터 변수
    int critical_counter = 0; 

    while (true) {
        cout << "\n[새로운 실시간 진동 모니터링 중... (" << elapsed_seconds << "초 경과)]" << endl;

        int sensor1 = rand() % 3; 
        int sensor2 = rand() % 3;
        int sensor3 = rand() % 3;

        // ★ 테스트를 원활하게 하기 위해 비상 상황(모터 이상)이 터질 확률을 조금 더 높여두었습니다 (20%)
        int machine_condition = rand() % 5; 
        if (machine_condition == 0) {
            cout << "ℹ️ [현장 상황] 설비에 가벼운 일시적 충격 감지 (+6회)" << endl;
            sensor1 += 3; sensor2 += 3;
        } 
        else if (machine_condition == 1) {
            cout << "🚨 [현장 상황] 설비에 대형 모터 이상 진동 발생!!! (+18회)" << endl;
            sensor1 += 6; sensor2 += 6; sensor3 += 6;
        }

        int total_vibrations = sensor1 + sensor2 + sensor3;
        if (total_vibrations > 30) total_vibrations = 30;

        cout << " -> 센서 현황 [ S1: " << sensor1 << "회 | S2: " << sensor2 << "회 | S3: " << sensor3 << "회 ]" << endl;
        cout << " >> 1호기 누적 진동: [ " << total_vibrations << " 회 ]" << endl;

        int current_error_code = NORMAL;
        bool trigger_shutdown = false; // 진짜 종료할지 결정하는 깃발

        if (total_vibrations <= 4) {
            current_error_code = NORMAL;
            cout << "【결과】 정상 작동 중" << endl;
        } 
        else if (total_vibrations >= 5 && total_vibrations <= 15) {
            current_error_code = NEED_INSPECTION;
            cout << "【결과】 ⚠️ 경고: 설비 육안 점검 필요 (에러코드: " << current_error_code << ")" << endl;
        } 
        else if (total_vibrations >= 16 && total_vibrations <= 30) {
            current_error_code = IMMEDIATE_STOP;
            
            // [변경 부분] 즉시 멈추지 않고 카운터를 1 올립니다.
            critical_counter++;
            cout << "【결과】 🚨 비상 진동 발생! 현재 누적 횟수: [ " << critical_counter << " / 4 회 ]" << endl;
            
            // 카운터가 4번 쌓였을 때만 진짜 종료 깃발을 올립니다!
            if (critical_counter >= 4) {
                cout << "【최종 판단】 위험 진동이 4회 연속/누적되어 설비를 강제 정지합니다!" << endl;
                trigger_shutdown = true;
            }
        }

        VibrationLog current_log = { getCurrentTime(), total_vibrations, current_error_code };

        // [종료 로직] 4번 누적 깃발이 올라왔을 때만 실행되는 긴급 세이브 및 셧다운
        if (trigger_shutdown) {
            cout << "⚠️ [시스템 경고] 최종 셧다운 전 현재까지의 일반 가동 데이터를 안전하게 저장합니다." << endl;
            
            // 1. 그동안 버퍼에 모여있던 일반 데이터 먼저 백업
            if (!periodic_buffer.empty()) {
                stringstream periodic_ss;
                periodic_ss << getTimeForFilename() << "_1호기_INTERVAL_30M_이전데이터.csv";
                string crash_backup_filename = periodic_ss.str();

                ofstream pFile(crash_backup_filename);
                if (pFile.is_open()) {
                    for (size_t i = 0; i < periodic_buffer.size(); ++i) {
                        pFile << periodic_buffer[i].timestamp << ", 1, " 
                              << periodic_buffer[i].total_vibrations << ", " 
                              << periodic_buffer[i].error_code << "\n";
                    }
                    pFile.close();
                    cout << "💾 [PRE-CRASH BACKUP] 가동 일지 대피 완료: [ " << crash_backup_filename << " ]" << endl;
                }
            }

            // 2. 최종 4회 누적을 유발한 셧다운 비상 파일 생성
            stringstream filename_stream;
            filename_stream << getTimeForFilename() << "_1호기_CRITICAL_누적4회오류.csv";
            string critical_filename = filename_stream.str();

            ofstream logFile(critical_filename); 
            if (logFile.is_open()) {
                logFile << current_log.timestamp << ", 1, " << current_log.total_vibrations << ", " << current_log.error_code << "\n";
                logFile.close(); 
                cout << "🚨 [BLACKBOX] 4회 누적 비상 로그 파일 추출 완료: [ " << critical_filename << " ]" << endl;
            }

            cout << "\n[SYSTEM SHUTDOWN] 설비 위험 누적 한계 도달로 시스템을 강제 종료합니다." << endl;
            exit(0); 
        }

        // 아직 4회가 안 되었다면, 현재 비상 데이터건 정상 데이터건 바구니에 차곡차곡 모아둠
        periodic_buffer.push_back(current_log);

        sleep(3); 
        elapsed_seconds += 3;

        // 정기 30분 주기 도래 시 정상 저장 로직
        if (elapsed_seconds >= SAVE_INTERVAL) {
            stringstream filename_stream;
            filename_stream << getTimeForFilename() << "_1호기_INTERVAL_30M.csv";
            string periodic_filename = filename_stream.str();

            ofstream periodicFile(periodic_filename);
            if (periodicFile.is_open()) {
                for (size_t i = 0; i < periodic_buffer.size(); ++i) {
                    periodicFile << periodic_buffer[i].timestamp << ", 1, "
                                 << periodic_buffer[i].total_vibrations << ", "
                                 << periodic_buffer[i].error_code << "\n";
                }
                periodicFile.close();
                cout << "💾 [PERIODIC BACKUP] 30분 정기 일반 가동 일지 생성 완료! -> [ " << periodic_filename << " ]" << endl;
            }

            periodic_buffer.clear();
            elapsed_seconds = 0;
            // 정기 저장이 무사히 끝나면 누적 에러 카운트도 초기화해줄 수 있습니다. (원하시면 유지, 여기서는 지속 누적으로 설정)
        }
        cout << "--------------------------------------------------" << endl;
    }

    return 0;
}