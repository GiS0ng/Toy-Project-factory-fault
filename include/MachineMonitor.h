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
private: //외부에서 접근 불가하도록 하는 변수
    int machine_id; // 기기 식별 번호
    int critical_counter;   // 에러 카운터 
    int elapsed_seconds; //누적 시간 추적
    int save_interval; //정기 저장주기 
    std::vector<VibrationLog> periodic_buffer; //메모리 임시 저장소 버퍼 개념
    
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