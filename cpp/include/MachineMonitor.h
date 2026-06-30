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
    
    IVibrationSensor* sensor1;
    IVibrationSensor* sensor2;
    IVibrationSensor* sensor3;

    std::string getTimeForFilename() const;
    std::string getCurrentTime() const;
    void savePeriodicLog();
    void savePreCrashLog();
    void saveCriticalLog(const VibrationLog& currentLog);

public:
    MachineMonitor(int id, IVibrationSensor* s1, IVibrationSensor* s2, IVibrationSensor* s3, int intervalSec = 30);
    void run(bool isTestMode = false);
};

#endif