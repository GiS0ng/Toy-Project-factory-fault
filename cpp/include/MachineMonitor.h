#ifndef MACHINE_MONITOR_H
#define MACHINE_MONITOR_H

#include <string>
#include <vector>
#include "ErrorCode.h"
#include "IVibrationSensor.h"

struct VibrationLog {
    std::string timestamp;
    int totalVibrations;
    int errorCode;
};

class MachineMonitor {
private:
    int machineId;
    int criticalCounter;
    int elapsedSeconds;
    int saveInterval;
    std::vector<VibrationLog> periodicBuffer;
    
    IVibrationSensor *sensor1, *sensor2, *sensor3;

    // 내부 헬퍼 함수
    std::string getTimeForFilename() const;
    std::string getCurrentTime() const;
    void savePeriodicLog();
    void savePreCrashLog();
    void saveCriticalLog(const VibrationLog& currentLog);
    
    // [추가] 파이썬 브릿지로 데이터 전송
    void sendToPython(const std::string& type, int vibration, int errorCode);

public:
    MachineMonitor(int id, IVibrationSensor* s1, IVibrationSensor* s2, IVibrationSensor* s3, int intervalSec = 30);
    void run(); 
};

#endif