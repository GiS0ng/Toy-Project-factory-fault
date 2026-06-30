#include "../include/MachineMonitor.h"
#include <iostream>
#include <fstream>
#include <unistd.h>
#include <iomanip>
#include <sstream>
#include <ctime>
#include <cstdlib>
#include <arpa/inet.h>
#include <sys/socket.h>
#include <cstring>

using namespace std;

MachineMonitor::MachineMonitor(int id, IVibrationSensor* s1, IVibrationSensor* s2, IVibrationSensor* s3, int intervalSec) 
    : machineId(id), criticalCounter(0), elapsedSeconds(0), saveInterval(intervalSec),
      sensor1(s1), sensor2(s2), sensor3(s3) {}

// --- [통신 로직 통합] ---
void MachineMonitor::sendToPython(const string& type, int vibration, int errorCode) {
    int sock = socket(AF_INET, SOCK_STREAM, 0);
    if (sock < 0) return;

    struct sockaddr_in serv_addr;
    memset(&serv_addr, 0, sizeof(serv_addr));
    serv_addr.sin_family = AF_INET;
    serv_addr.sin_port = htons(9999);
    serv_addr.sin_addr.s_addr = inet_addr("127.0.0.1");

    if (connect(sock, (struct sockaddr*)&serv_addr, sizeof(serv_addr)) >= 0) {
        string payload = type + "," + to_string(machineId) + "," + to_string(vibration) + "," + to_string(errorCode);
        send(sock, payload.c_str(), payload.length(), 0);
        cout << "📡 [Network] Python 브릿지로 전송 성공 (" << type << ")" << endl;
    }
    close(sock);
}

// --- [기존 로깅 함수들 생략 - 구조는 동일함] ---
string MachineMonitor::getCurrentTime() const {
    time_t now = time(nullptr);
    struct tm tstruct = *localtime(&now);
    char buf[80]; strftime(buf, sizeof(buf), "%Y-%m-%d %H:%M:%S", &tstruct);
    return string(buf);
}

string MachineMonitor::getTimeForFilename() const {
    time_t now = time(nullptr);
    struct tm tstruct = *localtime(&now);
    char buf[80]; strftime(buf, sizeof(buf), "%Y%m%d_%H%M%S", &tstruct);
    return string(buf);
}

void MachineMonitor::savePeriodicLog() {
    if (periodicBuffer.empty()) return;
    string filename = "data_queue/periodic_" + to_string(machineId) + "_" + getTimeForFilename() + ".csv";
    ofstream pFile(filename);
    if (pFile.is_open()) {
        for (const auto& log : periodicBuffer) {
            pFile << log.timestamp << "," << machineId << "," << log.totalVibrations << "," << log.errorCode << "\n";
        }
        cout << "💾 [File] 정기 로그 저장 완료: " << filename << endl;
    }
    periodicBuffer.clear();
    elapsedSeconds = 0;
}

void MachineMonitor::saveCriticalLog(const VibrationLog& currentLog) {
    string filename = "data_queue/critical_" + to_string(machineId) + "_" + getTimeForFilename() + ".csv";
    ofstream logFile(filename);
    if (logFile.is_open()) {
        logFile << currentLog.timestamp << "," << machineId << "," << currentLog.totalVibrations << "," << currentLog.errorCode << "\n";
        cout << "🚨 [File] 긴급 블랙박스 생성 완료: " << filename << endl;
    }
}

// --- [핵심 실행 루프] ---
void MachineMonitor::run() {
    cout << "🚀 [" << machineId << "호기] 모니터링 엔진 가동..." << endl;

    while (true) {
        // 1. 센서 데이터 수집
        int v1 = sensor1->getVibration();
        int v2 = sensor2->getVibration();
        int v3 = sensor3->getVibration();
        int totalVibrations = v1 + v2 + v3;
        if (totalVibrations > 30) totalVibrations = 30;

        // 2. 상태 판별 및 에러 코드 설정
        int currentErrorCode = NORMAL;
        string statusMsg = "정상";

        if (totalVibrations >= 16) {
            currentErrorCode = IMMEDIATE_STOP;
            criticalCounter++;
            statusMsg = "🚨 비상 정지 위기 (누적: " + to_string(criticalCounter) + "/4)";
        } else if (totalVibrations >= 5) {
            currentErrorCode = NEED_INSPECTION;
            statusMsg = "⚠️ 점검 필요";
            criticalCounter = 0;
        } else {
            criticalCounter = 0;
        }

        VibrationLog currentLog{ getCurrentTime(), totalVibrations, currentErrorCode };
        periodicBuffer.push_back(currentLog);

        // 3. 실시간 화면 출력 및 파이썬 전송
        cout << "\n[" << currentLog.timestamp << "] 진동: " << totalVibrations << " | 상태: " << statusMsg << endl;
        
        // 4. 상황별 분기 처리
        if (criticalCounter >= 4) {
            cout << "❌ [SYSTEM SHUTDOWN] 치명적 오류로 설비를 정지합니다." << endl;
            saveCriticalLog(currentLog);
            sendToPython("CRITICAL", totalVibrations, currentErrorCode);
            exit(0);
        }

        // 3초마다 정기 전송
        sendToPython("PERIODIC", totalVibrations, currentErrorCode);

        // 5. 정기 파일 저장 체크 (설정된 주기에 도달하면)
        if (elapsedSeconds >= saveInterval) {
            savePeriodicLog();
        }

        sleep(3);
        elapsedSeconds += 3;
    }
}