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
#include <algorithm>

using namespace std;

// 1. 생성자 구현
MachineMonitor::MachineMonitor(int id, IVibrationSensor* s1, IVibrationSensor* s2, IVibrationSensor* s3, int intervalSec) 
    : machineId(id), criticalCounter(0), elapsedSeconds(0), saveInterval(intervalSec),
      sensor1(s1), sensor2(s2), sensor3(s3) {}

// 2. 시간 관련 헬퍼 함수
string MachineMonitor::getCurrentTime() const {
    time_t now = time(nullptr);
    struct tm tstruct = *localtime(&now);
    char buf[80];
    strftime(buf, sizeof(buf), "%Y-%m-%d %H:%M:%S", &tstruct);
    return string(buf);
}

string MachineMonitor::getTimeForFilename() const {
    time_t now = time(nullptr);
    struct tm tstruct = *localtime(&now);
    char buf[80];
    strftime(buf, sizeof(buf), "%Y%m%d_%H%M%S", &tstruct);
    return string(buf);
}

// 3. 파이썬 전송 함수 (소켓)
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
    }
    close(sock);
}

// 4. 로그 저장 함수들
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

// 5. 핵심 메인 루프 (ISO 10816-3 적용)
void MachineMonitor::run() {
    cout << "🏭 ISO 10816-3 표준 기반 모니터링 엔진 가동..." << endl;

    while (true) {
        int v1 = sensor1->getVibration();
        int v2 = sensor2->getVibration();
        int v3 = sensor3->getVibration();

        int maxVib = max({v1, v2, v3});
        
        string packetHeader = "PERIODIC";
        int currentErrorCode = 0; // ISO_NORMAL
        string statusMsg = "🟢 [NORMAL]";

        if (maxVib >= 600) {
            packetHeader = "CRITICAL";
            currentErrorCode = 2; // ISO_CRITICAL
            statusMsg = "🚨 [CRITICAL]";
            criticalCounter++;
        } 
        else if (maxVib >= 400) {
            packetHeader = "WARNING";
            currentErrorCode = 1; // ISO_WARNING
            statusMsg = "🟡 [WARNING]";
            criticalCounter = 0;
        } 
        else {
            criticalCounter = 0;
        }

        cout << "\n[" << getCurrentTime() << "] " << statusMsg << " Max: " << maxVib << " μm/s" << endl;

        // 파이썬 전송
        sendToPython(packetHeader, maxVib, currentErrorCode);

        // 위험 누적 시 종료
        if (criticalCounter >= 4) {
            cout << "❌ 위험 수치 누적으로 시스템을 정지합니다." << endl;
            saveCriticalLog({getCurrentTime(), maxVib, currentErrorCode});
            exit(0);
        }

        // 데이터 버퍼링 및 정기 저장
        periodicBuffer.push_back({getCurrentTime(), maxVib, currentErrorCode});
        
        if (elapsedSeconds >= saveInterval) {
            savePeriodicLog();
        }

        sleep(3);
        elapsedSeconds += 3;
    }
}