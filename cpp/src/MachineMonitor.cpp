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
#include <cerrno>
#include <algorithm>
#include <filesystem>

using namespace std;

// 1. 생성자 구현
MachineMonitor::MachineMonitor(int id, IVibrationSensor* s1, IVibrationSensor* s2, IVibrationSensor* s3, int intervalSec) 
    : machineId(id), criticalCounter(0), elapsedSeconds(0), saveInterval(intervalSec),
      retrySequence(0),
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
bool MachineMonitor::sendPayloadToPython(const string& payload) {
    struct sockaddr_in serv_addr;
    memset(&serv_addr, 0, sizeof(serv_addr));
    serv_addr.sin_family = AF_INET;
    serv_addr.sin_port = htons(9999);
    serv_addr.sin_addr.s_addr = inet_addr("127.0.0.1");

    constexpr int maxAttempts = 3;

    for (int attempt = 1; attempt <= maxAttempts; ++attempt) {
        int sock = socket(AF_INET, SOCK_STREAM, 0);
        if (sock < 0) {
            cerr << "⚠️ [Network] 소켓 생성 실패 (" << attempt << "/"
                 << maxAttempts << "): " << strerror(errno) << endl;
        } else if (connect(sock, reinterpret_cast<struct sockaddr*>(&serv_addr),
                           sizeof(serv_addr)) < 0) {
            const int connectionError = errno;
            cerr << "⚠️ [Network] Python 브리지 연결 실패 (" << attempt << "/"
                 << maxAttempts << "): " << strerror(connectionError) << endl;
            close(sock);
        } else {
            size_t bytesSent = 0;
            int sendError = 0;
            while (bytesSent < payload.size()) {
                ssize_t sent = send(
                    sock,
                    payload.c_str() + bytesSent,
                    payload.size() - bytesSent,
                    MSG_NOSIGNAL
                );
                if (sent <= 0) {
                    sendError = sent == 0 ? EPIPE : errno;
                    break;
                }
                bytesSent += static_cast<size_t>(sent);
            }

            close(sock);
            if (bytesSent == payload.size()) {
                return true;
            }

            cerr << "⚠️ [Network] Python 브리지 전송 실패 (" << attempt << "/"
                 << maxAttempts << "): " << strerror(sendError) << endl;
        }

        if (attempt < maxAttempts) {
            usleep(100000);
        }
    }

    cerr << "❌ [Network] Python 브리지 전송을 포기했습니다: "
         << payload.substr(0, payload.size() - 1) << endl;
    return false;
}

void MachineMonitor::saveFailedPayload(const string& payload) {
    const filesystem::path retryPath("data_queue/network_retry");
    error_code directoryError;
    filesystem::create_directories(retryPath, directoryError);
    if (directoryError) {
        cerr << "❌ [Network] 재전송 큐 폴더를 만들 수 없습니다: "
             << directoryError.message() << endl;
        return;
    }

    filesystem::path filename;
    do {
        filename = retryPath / ("pending_" + getTimeForFilename() + "_"
            + to_string(++retrySequence) + ".packet");
    } while (filesystem::exists(filename));

    ofstream queueFile(filename);
    if (!queueFile.is_open()) {
        cerr << "❌ [Network] 재전송 패킷을 저장할 수 없습니다: "
             << filename << endl;
        return;
    }

    queueFile << payload;
    queueFile.close();
    if (queueFile.fail()) {
        cerr << "❌ [Network] 재전송 패킷 저장에 실패했습니다: "
             << filename << endl;
        return;
    }

    cerr << "💾 [Network] 재전송 패킷 저장 완료: " << filename << endl;
}

void MachineMonitor::retryFailedPayloads() {
    const filesystem::path retryPath("data_queue/network_retry");
    constexpr size_t maxRetriesPerCycle = 10;
    error_code directoryError;
    if (!filesystem::exists(retryPath, directoryError)) {
        if (directoryError) {
            cerr << "⚠️ [Network] 재전송 큐를 확인할 수 없습니다: "
                 << directoryError.message() << endl;
        }
        return;
    }

    vector<filesystem::path> pendingPaths;
    for (const auto& entry : filesystem::directory_iterator(retryPath, directoryError)) {
        if (directoryError) {
            cerr << "⚠️ [Network] 재전송 큐를 읽을 수 없습니다: "
                 << directoryError.message() << endl;
            return;
        }

        const string filename = entry.path().filename().string();
        if (!entry.is_regular_file() || filename.rfind("pending_", 0) != 0) {
            continue;
        }

        pendingPaths.push_back(entry.path());
    }

    sort(pendingPaths.begin(), pendingPaths.end());
    if (pendingPaths.size() > maxRetriesPerCycle) {
        cerr << "⚠️ [Network] 보류 패킷이 " << pendingPaths.size()
             << "건입니다. 이번 주기에는 " << maxRetriesPerCycle
             << "건만 재전송합니다." << endl;
    }

    const size_t retryCount = min(pendingPaths.size(), maxRetriesPerCycle);
    for (size_t index = 0; index < retryCount; ++index) {
        const filesystem::path& pendingPath = pendingPaths[index];
        const string filename = pendingPath.filename().string();
        ifstream queueFile(pendingPath);
        string payload((istreambuf_iterator<char>(queueFile)),
                       istreambuf_iterator<char>());
        if (!queueFile.good() && !queueFile.eof()) {
            cerr << "⚠️ [Network] 재전송 패킷을 읽을 수 없습니다: "
                 << pendingPath << endl;
            continue;
        }

        if (payload.empty() || !sendPayloadToPython(payload)) {
            continue;
        }

        const filesystem::path completedPath = pendingPath.parent_path()
            / ("sent_" + filename.substr(8));
        error_code renameError;
        filesystem::rename(pendingPath, completedPath, renameError);
        if (renameError) {
            cerr << "⚠️ [Network] 재전송 완료 상태를 기록할 수 없습니다: "
                 << renameError.message() << endl;
            continue;
        }

        cout << "📤 [Network] 보류 패킷 재전송 완료: " << completedPath << endl;
    }
}

void MachineMonitor::sendToPython(const string& type, int vibration, int errorCode) {
    retryFailedPayloads();

    const string payload = type + "," + to_string(machineId) + ","
        + to_string(vibration) + "," + to_string(errorCode) + "\n";
    if (!sendPayloadToPython(payload)) {
        saveFailedPayload(payload);
    }
}

// 4. 로그 저장 함수들
void MachineMonitor::savePeriodicLog() {
    if (periodicBuffer.empty()) {
        return;
    }

    const filesystem::path dataQueuePath("data_queue");
    error_code directoryError;
    filesystem::create_directories(dataQueuePath, directoryError);
    if (directoryError) {
        cerr << "❌ [File] 로그 저장 폴더를 만들 수 없습니다: "
             << directoryError.message() << endl;
        return;
    }

    string filename = (dataQueuePath / ("periodic_" + to_string(machineId)
        + "_" + getTimeForFilename() + ".csv")).string();
    ofstream pFile(filename);
    if (!pFile.is_open()) {
        cerr << "❌ [File] 정기 로그 파일을 열 수 없습니다: " << filename << endl;
        return;
    }

    for (const auto& log : periodicBuffer) {
        pFile << log.timestamp << "," << machineId << ","
              << log.totalVibrations << "," << log.errorCode << "\n";
    }
    pFile.close();

    if (pFile.fail()) {
        cerr << "❌ [File] 정기 로그 저장에 실패했습니다. 버퍼를 유지합니다: "
             << filename << endl;
        return;
    }

    periodicBuffer.clear();
    elapsedSeconds = 0;
    cout << "💾 [File] 정기 로그 저장 완료: " << filename << endl;
}

void MachineMonitor::saveCriticalLog(const VibrationLog& currentLog) {
    const filesystem::path dataQueuePath("data_queue");
    error_code directoryError;
    filesystem::create_directories(dataQueuePath, directoryError);
    if (directoryError) {
        cerr << "❌ [File] 긴급 로그 폴더를 만들 수 없습니다: "
             << directoryError.message() << endl;
        return;
    }

    string filename = (dataQueuePath / ("critical_" + to_string(machineId)
        + "_" + getTimeForFilename() + ".csv")).string();
    ofstream logFile(filename);
    if (!logFile.is_open()) {
        cerr << "❌ [File] 긴급 로그 파일을 열 수 없습니다: " << filename << endl;
        return;
    }

    for (const auto& log : periodicBuffer) {
        logFile << log.timestamp << "," << machineId << ","
                << log.totalVibrations << "," << log.errorCode << "\n";
    }
    logFile << currentLog.timestamp << "," << machineId << ","
            << currentLog.totalVibrations << "," << currentLog.errorCode << "\n";
    logFile.close();

    if (logFile.fail()) {
        cerr << "❌ [File] 긴급 로그 저장에 실패했습니다: " << filename << endl;
        return;
    }

    cout << "🚨 [File] 긴급 블랙박스 생성 완료: " << filename
         << " (이전 로그 " << periodicBuffer.size() << "건 포함)" << endl;
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

        // 위험 수치가 4회 연속 발생하면 종료
        if (criticalCounter >= 4) {
            cout << "❌ 위험 수치가 4회 연속 발생해 시스템을 정지합니다." << endl;
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
