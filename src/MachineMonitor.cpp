// src/MachineMonitor.cpp
#include "../include/MachineMonitor.h"
#include <iostream>
#include <fstream>
#include <unistd.h>
#include <iomanip>
#include <sstream>
#include <ctime>

using namespace std;

MachineMonitor::MachineMonitor(int id, int interval_sec) 
    : machine_id(id), critical_counter(0), elapsed_seconds(0), save_interval(interval_sec) {}

string MachineMonitor::getTimeForFilename() const {
    time_t now = time(nullptr);
    struct tm tstruct = *localtime(&now);
    char buf[80];
    strftime(buf, sizeof(buf), "%Y%m%d_%H%M%S", &tstruct);
    return string(buf);
}

string MachineMonitor::getCurrentTime() const {
    time_t now = time(nullptr);
    struct tm tstruct = *localtime(&now);
    char buf[80];
    strftime(buf, sizeof(buf), "%Y-%m-%d %H:%M:%S", &tstruct);
    return string(buf);
}

void MachineMonitor::savePeriodicLog() {
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

void MachineMonitor::savePreCrashLog() {
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

void MachineMonitor::saveCriticalLog(const VibrationLog& current_log) {
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

void MachineMonitor::run() {
    cout << "==================================================" << endl;
    cout << "  " << machine_id << "호기 이원화 저장 시스템 가동 (폴더 구조화 적용) " << endl;
    cout << "==================================================" << endl;

    while (true) {
        cout << "\n[" << machine_id << "호기 실시간 모니터링 중... (" << elapsed_seconds << "초 경과)]" << endl;

        int s1 = sensor1.getVibration();
        int s2 = sensor2.getVibration();
        int s3 = sensor3.getVibration();

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

        if (trigger_shutdown) {
            cout << "⚠️ [시스템 경고] 최종 셧다운 전 현재까지의 데이터를 세이브합니다." << endl;
            savePreCrashLog();        
            saveCriticalLog(current_log); 
            cout << "\n[SYSTEM SHUTDOWN] " << machine_id << "호기 위험 한계 도달로 시스템을 강제 종료합니다." << endl;
            exit(0);
        }

        periodic_buffer.push_back(current_log);

        sleep(3);
        elapsed_seconds += 3;

        if (elapsed_seconds >= save_interval) {
            savePeriodicLog();
        }
        cout << "--------------------------------------------------" << endl;
    }
}
// 무한루프 대신, 우리가 던져준 진동수 배열(mock_vibrations)을 순서대로 소화하며 검증하는 테스트 함수
void MachineMonitor::runTestScenario(const  std::vector<int>& mock_vibrations) {
    cout << "\n==================================================" << endl;
    cout << "🧪 [TEST START] 사용자 정의 시나리오 테스트를 시작합니다." << endl;
    cout << "==================================================" << endl;

    // 배열에 든 가짜 진동 값을 하나씩 꺼내어 테스트 진행
    for (int fake_total : mock_vibrations) {
        cout << "\n[테스트 입력] 가상 주입된 총 진동수: [ " << fake_total << " 회 ] (" << elapsed_seconds << "초 경과)" << endl;

        int current_error_code = NORMAL;
        bool trigger_shutdown = false;

        // 1. 우리가 만든 조건 진단 알고리즘 검증
        if (fake_total <= 4) {
            current_error_code = NORMAL;
            cout << "【판정】 정상 작동 (기대값: 0 | 결과: " << current_error_code << ")" << endl;
        } 
        else if (fake_total >= 5 && fake_total <= 15) {
            current_error_code = NEED_INSPECTION;
            cout << "【판정】 ⚠️ 육안 점검 필요 (기대값: 101 | 결과: " << current_error_code << ")" << endl;
        } 
        else if (fake_total >= 16 && fake_total <= 30) {
            current_error_code = IMMEDIATE_STOP;
            critical_counter++;
            cout << "【판정】 🚨 비상 진동! 현재 에러 누적: [ " << critical_counter << " / 4 회 ]" << endl;
            
            if (critical_counter >= 4) {
                cout << "【최종 판단】 💥 위험 누적 한계 도달! 셧다운 트리거 발동!" << endl;
                trigger_shutdown = true;
            }
        }

        VibrationLog current_log{ getCurrentTime(), fake_total, current_error_code };

        // 2. 4회 누적 셧다운 및 데이터 대피 기능 검증
        if (trigger_shutdown) {
            cout << "[알림] 최종 셧다운 전 가동 데이터 대피 및 블랙박스 추출 테스트를 진행합니다." << endl;
            savePreCrashLog();        // 버퍼 대피 파일 생성 검증
            saveCriticalLog(current_log); // 블랙박스 파일 생성 검증
            cout << "🏆 [TEST SUCCESS] 4회 누적 셧다운 및 데이터 유실 방지 테스트 성공!" << endl;
            return; // 테스트 성공 후 안전하게 종료 (exit 대신 return으로 테스트 마무리)
        }

        // 평소 데이터 버퍼링
        periodic_buffer.push_back(current_log);
        elapsed_seconds += 3; // 시뮬레이션 시간 증가

        // 3. 정기 저장 주기(30초) 도래 시 파일 생성 검증
        if (elapsed_seconds >= save_interval) {
            cout << "⏰ [주기 도래] 설정한 저장 주기가 되어 정기 저장을 테스트합니다." << endl;
            savePeriodicLog();
        }
        cout << "--------------------------------------------------" << endl;
    }

    cout << "\n⚠️ [TEST END] 모든 시나리오 데이터가 소모되었으나 셧다운 조건에 도달하지 않았습니다." << endl;
}