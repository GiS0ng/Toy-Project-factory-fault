// src/MachineMonitor.cpp
#include "../include/MachineMonitor.h"
#include <iostream>
#include <fstream>
#include <unistd.h>
#include <iomanip>
#include <sstream>
#include <ctime>
#include <cstdlib>

using namespace std;

MachineMonitor::MachineMonitor(int id, IVibrationSensor* s1, IVibrationSensor* s2, IVibrationSensor* s3, int intervalSec) 
    : machineId(id), criticalCounter(0), elapsedSeconds(0), saveInterval(intervalSec),
      sensor1(s1), sensor2(s2), sensor3(s3) {}

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

// 📂 [수정] 정기 데이터는 파이썬이 알아채기 쉽게 'periodic_' 접두사를 붙여 data_queue 폴더에 저장
void MachineMonitor::savePeriodicLog() {
    if (periodicBuffer.empty()) return;

    stringstream ss;
    ss << "data_queue/periodic_" << machineId << "호기_" << getTimeForFilename() << ".csv";
    string filename = ss.str();

    ofstream pFile(filename);
    if (pFile.is_open()) {
        for (const auto& log : periodicBuffer) {
            pFile << log.timestamp << ", " << machineId << ", "
                  << log.totalVibrations << ", " << log.errorCode << "\n";
        }
        pFile.close();
        cout << "💾 [PERIODIC] 파이썬 대기방에 정기 일지 생성 완료! -> [ " << filename << " ]" << endl;
    }
    periodicBuffer.clear();
    elapsedSeconds = 0;
}

// 📂 [수정] 강제종료 직전 백업 데이터도 대기방으로 대피
void MachineMonitor::savePreCrashLog() {
    if (periodicBuffer.empty()) return;

    stringstream ss;
    ss << "data_queue/periodic_" << machineId << "호기_" << getTimeForFilename() << "_이전데이터.csv";
    string filename = ss.str();

    ofstream pFile(filename);
    if (pFile.is_open()) {
        for (const auto& log : periodicBuffer) {
            pFile << log.timestamp << ", " << machineId << ", "
                  << log.totalVibrations << ", " << log.errorCode << "\n";
        }
        pFile.close();
        cout << "💾 [PRE-CRASH] 강제종료 직전 데이터 대피 완료: [ " << filename << " ]" << endl;
    }
}

// 📂 [수정] 긴급 카톡용 블랙박스 데이터는 'critical_' 접두사를 붙여 data_queue 폴더에 저장
void MachineMonitor::saveCriticalLog(const VibrationLog& currentLog) {
    stringstream ss;
    ss << "data_queue/critical_" << machineId << "호기_" << getTimeForFilename() << ".csv";
    string filename = ss.str();

    ofstream logFile(filename);
    if (logFile.is_open()) {
        logFile << currentLog.timestamp << ", " << machineId << ", "
                << currentLog.totalVibrations << ", " << currentLog.errorCode << "\n";
        logFile.close();
        cout << "🚨 [CRITICAL] 파이썬 대기방에 SOS 블랙박스 생성 완료! -> [ " << filename << " ]" << endl;
    }
}

void MachineMonitor::run(bool isTestMode) {
    cout << "==================================================" << endl;
    cout << "  " << machineId << "호기 모니터링 시스템 (" 
         << (isTestMode ? "🧪 테스트 모드" : "🏭 실제 현장 모드") << " 가동)" << endl;
    cout << "==================================================" << endl;

    while (true) {
        cout << "\n[" << machineId << "호기 실시간 감시 중... (" << elapsedSeconds << "초 경과)]" << endl;

        int s1 = sensor1->getVibration();
        int s2 = sensor2->getVibration();
        int s3 = sensor3->getVibration();

        int totalVibrations = s1 + s2 + s3;

        if (!isTestMode) {
            int machineCondition = rand() % 5;
            if (machineCondition == 0) {
                cout << "ℹ️ [현장 상황] 설비에 가벼운 일시적 충격 감지 (+6회)" << endl;
                s1 += 3; s2 += 3;
            } 
            else if (machineCondition == 1) {
                cout << "🚨 [현장 상황] 설비에 대형 모터 이상 진동 발생!!! (+18회)" << endl;
                s1 += 6; s2 += 6; s3 += 6;
            }
            totalVibrations = s1 + s2 + s3;
        }

        if (totalVibrations > 30) totalVibrations = 30;

        cout << " -> 센서 상세 [ S1: " << s1 << "회 | S2: " << s2 << "회 | S3: " << s3 << "회 ]" << endl;
        cout << " >> 총합 진동수: [ " << totalVibrations << " 회 ]" << endl;

        int currentErrorCode = NORMAL;
        bool triggerShutdown = false;

        if (totalVibrations <= 4) {
            currentErrorCode = NORMAL;
            cout << "【결과】 정상 작동 중" << endl;
        } 
        else if (totalVibrations >= 5 && totalVibrations <= 15) {
            currentErrorCode = NEED_INSPECTION;
            cout << "【결과】 ⚠️ 경고: 설비 육안 점검 필요" << endl;
        } 
        else if (totalVibrations >= 16 && totalVibrations <= 30) {
            currentErrorCode = IMMEDIATE_STOP;
            criticalCounter++;
            cout << "【결과】 🚨 비상 진동 발생! 현재 누적 횟수: [ " << criticalCounter << " / 4 회 ]" << endl;
            
            if (criticalCounter >= 4) {
                cout << "【최종 판단】 위험 누적 한계 도달로 설비를 정지합니다!" << endl;
                triggerShutdown = true;
            }
        }

        VibrationLog currentLog{ getCurrentTime(), totalVibrations, currentErrorCode };

        if (triggerShutdown) {
            cout << "⚠️ [시스템 경고] 최종 셧다운 전 데이터를 세이브합니다." << endl;
            savePreCrashLog();        
            saveCriticalLog(currentLog); 
            cout << "\n[SYSTEM SHUTDOWN] 시스템을 종료합니다." << endl;
            
            if (isTestMode) return; 
            else exit(0);
        }

        periodicBuffer.push_back(currentLog);

        if (!isTestMode) {
            sleep(3);
        }
        elapsedSeconds += 3;

        if (elapsedSeconds >= saveInterval) {
            savePeriodicLog();
        }
        cout << "--------------------------------------------------" << endl;
    }
}