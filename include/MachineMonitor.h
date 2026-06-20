// include/MachineMonitor.h
#ifndef MACHINE_MONITOR_H
#define MACHINE_MONITOR_H

#include <string>
#include <vector>
#include "ErrorCode.h"
#include "VibrationSensor.h"

struct VibrationLog {
    std::string timestamp;
    int total_vibrations;
    int error_code;
};

class MachineMonitor {
private:
    int machine_id;
    int critical_counter;
    int elapsed_seconds;
    int save_interval;
    std::vector<VibrationLog> periodic_buffer;
    
    // 센서 객체 3개 장착
    VibrationSensor sensor1, sensor2, sensor3;

    // 내부 헬퍼 함수들
    std::string getTimeForFilename() const;
    std::string getCurrentTime() const;
    void savePeriodicLog();
    void savePreCrashLog();
    void saveCriticalLog(const VibrationLog& current_log);

public:
    MachineMonitor(int id, int interval_sec = 30);
    void run();
    void runTestScenario(const std::vector<int>& mock_vibrations);
};

#endif