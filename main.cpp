#include <iostream>
#include <vector>
#include <cstdlib>
#include <ctime>
#include <unistd.h>
#include <fstream>
#include <iomanip>
#include <sstream>

using namespace std;

// 에러 코드 정의
enum ErrorCode {
    NORMAL = 0,
    NEED_INSPECTION = 101, 
    IMMEDIATE_STOP = 102   
};

// 로그 데이터 구조체
struct VibrationLog {
    string timestamp;
    int total_vibrations;
    int error_code;
};


// ==========================================
// 1. 진동 센서 클래스 (VibrationSensor)
// ==========================================
class VibrationSensor {
public:
    // 평소 기본 진동수(0~2회)를 측정하여 반환하는 함수
    int getVibration() const {
        return rand() % 3;
    }
};


// ==========================================
// 2. 설비 모니터링 관리 클래스 (MachineMonitor)
// ==========================================
class MachineMonitor {
private:
    int machine_id;                  // 호기 번호 (예: 1호기, 2호기)
    int critical_counter;            // 16회 이상 비상 진동 누적 카운터
    int elapsed_seconds;             // 정기 저장을 위한 타이머
    int save_interval;               // 저장 주기 (초)
    vector<VibrationLog> periodic_buffer; // 메모리 데이터 바구니
    VibrationSensor sensor1, sensor2, sensor3; // 설비에 장착된 3개의 센서 객체

    // [헬퍼 함수] 파일 이름용 시간 포맷 (YYYYMMDD_HHMMSS)
    string getTimeForFilename() const {
        time_t now = time(nullptr);
        struct tm tstruct = *localtime(&now);
        char buf[80];
        strftime(buf, sizeof(buf), "%Y%m%d_%H%M%S", &tstruct);
        return string(buf);
    }

    // [헬퍼 함수] 로그 내부용 시간 포맷 (YYYY-MM-DD HH:MM:SS)
    string getCurrentTime() const {
        time_t now = time(nullptr);
        struct tm tstruct = *localtime(&now);
        char buf[80];
        strftime(buf, sizeof(buf), "%Y-%m-%d %H:%M:%S", &tstruct);
        return string(buf);
    }

    // 정기 일반 가동 일지 저장 함수
    void savePeriodicLog() {
        if (periodic_buffer.empty()) return;

        stringstream ss;
        ss << getTimeForFilename() << "_" << machine_id << "호기_INTERVAL_30M.csv";
        string filename = ss.str();

        ofstream pFile(filename);
        if (pFile.is_open()) {
            for (const auto& log : periodic_buffer) {
                pFile << log.timestamp << ", " << machine_id << ", "
                      << log.total_vibrations << ", " << log.error_code << "\n";
            }
            pFile.close();
            cout << "💾 [PERIODIC BACKUP] 정기 가동 일지 생성 완료! -> [ " << filename << " ]" << endl;
        }
        periodic_buffer.clear();
        elapsed_seconds = 0;
    }

    // 강제 종료 직전 데이터 대피 함수
    void savePreCrashLog() {
        if (periodic_buffer.empty()) return;

        stringstream ss;
        ss << getTimeForFilename() << "_" << machine_id << "호기_INTERVAL_30M_이전데이터.csv";
        string filename = ss.str();

        ofstream pFile(filename);
        if (pFile.is_open()) {
            for (const auto& log : periodic_buffer) {
                pFile << log.timestamp << ", " << machine_id << ", "
                      << log.total_vibrations << ", " << log.error_code << "\n";
            }
            pFile.close();
            cout << "💾 [PRE-CRASH BACKUP] 강제종료 직전 가동 일지 대피 완료: [ " << filename << " ]" << endl;
        }
    }

    // 최종 비상 로그 파일 생성 함수
    void saveCriticalLog(const VibrationLog& current_log) {
        stringstream ss;
        ss << getTimeForFilename() << "_" << machine_id << "호기_CRITICAL_누적4회오류.csv";
        string filename = ss.str();

        ofstream logFile(filename);
        if (logFile.is_open()) {
            logFile << current_log.timestamp << ", " << machine_id << ", "
                    << current_log.total_vibrations << ", " << current_log.error_code << "\n";
            logFile.close();
            cout << "🚨 [BLACKBOX] 4회 누적 비상 로그 파일 추출 완료: [ " << filename << " ]" << endl;
        }
    }

public:
    // 생성자: 호기 번호와 저장 주기를 받아 초기화 세팅
    MachineMonitor(int id, int interval_sec = 30) 
        : machine_id(id), critical_counter(0), elapsed_seconds(0), save_interval(interval_sec) {}

    // 모니터링 시스템을 구동하는 핵심 실행 함수
    void run() {
        cout << "==================================================" << endl;
        cout << "  " << machine_id << "호기 이원화 저장 시스템 시스템 가동 (OOP 적용) " << endl;
        cout << "==================================================" << endl;

        while (true) {
            cout << "\n[" << machine_id << "호기 실시간 모니터링 중... (" << elapsed_seconds << "초 경과)]" << endl;

            // 각 센서 객체로부터 값을 읽어옴
            int s1 = sensor1.getVibration();
            int s2 = sensor2.getVibration();
            int s3 = sensor3.getVibration();

            // 20% 확률로 현장 돌발 충격 및 대형 모터 노이즈 연출
            int machine_condition = rand() % 5;
            if (machine_condition == 0) {
                cout << "ℹ️ [현장 상황] 설비에 가벼운 일시적 충격 감지 (+6회)" << endl;
                s1 += 3; s2 += 3;
            } 
            else if (machine_condition == 1) {
                cout << "🚨 [현장 상황] 설비에 대형 모터 이상 진동 발생!!! (+18회)" << endl;
                s1 += 6; s2 += 6; s3 += 6;
            }

            int total_vibrations = s1 + s2 + s3;
            if (total_vibrations > 30) total_vibrations = 30;

            cout << " -> 센서 현황 [ S1: " << s1 << "회 | S2: " << s2 << "회 | S3: " << s3 << "회 ]" << endl;
            cout << " >> " << machine_id << "호기 누적 진동: [ " << total_vibrations << " 회 ]" << endl;

            int current_error_code = NORMAL;
            bool trigger_shutdown = false;

            // 조건 진단 알고리즘
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
                critical_counter++;
                cout << "【결과】 🚨 비상 진동 발생! 현재 누적 횟수: [ " << critical_counter << " / 4 회 ]" << endl;
                
                if (critical_counter >= 4) {
                    cout << "【최종 판단】 위험 진동이 4회 누적되어 설비를 강제 정지합니다!" << endl;
                    trigger_shutdown = true;
                }
            }

            VibrationLog current_log{ getCurrentTime(), total_vibrations, current_error_code };

            // 4회 누적 셧다운 처리 로직
            if (trigger_shutdown) {
                cout << "⚠️ [시스템 경고] 최종 셧다운 전 현재까지의 데이터를 세이브합니다." << endl;
                savePreCrashLog();        // 1. 버퍼 대피
                saveCriticalLog(current_log); // 2. 비상 파일 생성
                cout << "\n[SYSTEM SHUTDOWN] " << machine_id << "호기 위험 한계 도달로 시스템을 강제 종료합니다." << endl;
                exit(0);
            }

            // 평소 데이터 버퍼링
            periodic_buffer.push_back(current_log);

            sleep(3);
            elapsed_seconds += 3;

            // 정기 저장 주기 판단
            if (elapsed_seconds >= save_interval) {
                savePeriodicLog();
            }
            cout << "--------------------------------------------------" << endl;
        }
    }
};


// ==========================================
// 3. 메인 스위치 엔트리 포인트
// ==========================================
int main() {
    srand(time(nullptr));

    // 1호기 모니터링 객체 생성 (호기번호: 1, 정기저장주기: 30초 설정)
    MachineMonitor monitor1(1, 30);
    
    // 모니터링 시스템 스타트!
    monitor1.run();

    return 0;
}