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

// 30분 정기 저장 바구니에 담을 데이터 구조체 정의
struct VibrationLog {
    string timestamp;
    int total_vibrations;
    int error_code;
};

// 파일 이름용 시간 포맷 (YYYYMMDD_HHMMSS)
string getTimeForFilename() {
    time_t now = time(0);
    struct tm tstruct;
    char buf[80];
    tstruct = *localtime(&now);
    strftime(buf, sizeof(buf), "%Y%m%d_%H%M%S", &tstruct);
    return string(buf);
}

// 로그 텍스트 내부용 시간 포맷 (YYYY-MM-DD HH:MM:SS)
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
    cout << "  1호기 이원화 저장 시스템 가동 (정기 30분 백업 기능) " << endl;
    cout << "==================================================" << endl;

    // 30분 데이터를 모아둘 바구니(버퍼) 생성
    vector<VibrationLog> periodic_buffer;
    int elapsed_seconds = 0; // 흘러간 시간을 체크할 누적 타이머

    // ★ 실제 현업 주기는 30분 = 1800초입니다.
    // ★ 테스트를 빠르게 해보기 위해 '30초'가 지나면 파일이 저장되도록 세팅했습니다.
    int SAVE_INTERVAL = 30; 

    while (true) {
        cout << "\n[새로운 실시간 진동 모니터링 중... (" << elapsed_seconds << "초 경과)]" << endl;

        // 평소 진동수 세팅 (0~2회)
        int sensor1 = rand() % 3; 
        int sensor2 = rand() % 3;
        int sensor3 = rand() % 3;

        // 20% 확률로 기계 돌발 노이즈 상황 연출
        int machine_condition = rand() % 10;
        if (machine_condition == 0) {
            cout << "ℹ️ [현장 상황] 설비에 가벼운 일시적 충격 감지 (+6회)" << endl;
            sensor1 += 3; sensor2 += 3;
        } 
        else if (machine_condition == 1) {
            cout << "🚨 [현장 상황] 설비에 대형 모터 이상 진동 감지 (+18회)" << endl;
            sensor1 += 6; sensor2 += 6; sensor3 += 6;
        }

        int total_vibrations = sensor1 + sensor2 + sensor3;
        if (total_vibrations > 30) total_vibrations = 30;

        cout << " -> 센서 현황 [ S1: " << sensor1 << "회 | S2: " << sensor2 << "회 | S3: " << sensor3 << "회 ]" << endl;
        cout << " >> 1호기 누적 진동: [ " << total_vibrations << " 회 ]" << endl;

        int current_error_code = NORMAL;
        bool is_critical = false;

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
            cout << "【결과】 🚨 비상: 설비 즉시 스탑!!! (에러코드: " << current_error_code << ")" << endl;
            is_critical = true;
        }

        // 현재 데이터를 임시 로그 구조체에 담기
        VibrationLog current_log = { getCurrentTime(), total_vibrations, current_error_code };

        // [A타입 루트] 만약 치명적 에러(102)라면? -> 기다리지 않고 그 즉시 고유 파일 만들고 강제 종료!
        if (is_critical) {
            stringstream filename_stream;
            filename_stream << getTimeForFilename() << "_1호기_CRITICAL.csv";
            string critical_filename = filename_stream.str();

            ofstream logFile(critical_filename); 
            if (logFile.is_open()) {
                logFile << current_log.timestamp << ", 1, " << current_log.total_vibrations << ", " << current_log.error_code << "\n";
                logFile.close(); 
                cout << "🚨 [BLACKBOX] 비상 로그 파일 즉시 추출 완료: [ " << critical_filename << " ]" << endl;
            }
            cout << "\n[SYSTEM SHUTDOWN] 치명적 에러로 시스템을 강제 종료합니다." << endl;
            exit(0); 
        }

        // [B타입 루트] 평소 일반/경고 데이터는 바구니(버퍼)에 저장해 둠
        periodic_buffer.push_back(current_log);


        // 3초 대기했으니 경과 시간에 3초 추가
        sleep(3); 
        elapsed_seconds += 3;

        // --- [정기 저장 핵심 코드] 설정한 주기(30초 = 실제 30분 가상)가 다 되었을 때 ---
        if (elapsed_seconds >= SAVE_INTERVAL) {
            stringstream filename_stream;
            filename_stream << getTimeForFilename() << "_1호기_INTERVAL_30M.csv";
            string periodic_filename = filename_stream.str();

            ofstream periodicFile(periodic_filename);
            if (periodicFile.is_open()) {
                // 바구니에 담아둔 그동안의 일반 정상 데이터를 한 번에 쏟아부어 파일로 기록합니다.
                for (size_t i = 0; i < periodic_buffer.size(); ++i) {
                    periodicFile << periodic_buffer[i].timestamp << ", "
                                 << "1, "
                                 << periodic_buffer[i].total_vibrations << ", "
                                 << periodic_buffer[i].error_code << "\n";
                }
                periodicFile.close();
                cout << "💾 [PERIODIC BACKUP] 30분 정기 일반 가동 일지 생성 완료! -> [ " << periodic_filename << " ]" << endl;
            } else {
                cout << "❌ 정기 파일 생성 실패!" << endl;
            }

            // 파일로 보냈으니 다음 30분을 위해 바구니와 타이머를 비워줍니다.
            periodic_buffer.clear();
            elapsed_seconds = 0;
        }
        cout << "--------------------------------------------------" << endl;
    }

    return 0;
}