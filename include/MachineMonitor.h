// include/MachineMonitor.h
#ifndef MACHINE_MONITOR_H
#define MACHINE_MONITOR_H

#include <string>
#include <vector>
#include "ErrorCode.h"
#include "IVibrationSensor.h"

// 로그 구조체 선언
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
    
    // 다형성을 위해 부모 인터페이스 포인터로 센서들을 가리킴
    IVibrationSensor* sensor1;
    IVibrationSensor* sensor2;
    IVibrationSensor* sensor3;

    std::string getTimeForFilename() const;
    std::string getCurrentTime() const;
    void savePeriodicLog();
    void savePreCrashLog();
    
    // 에러 수정: 인자 타입을 명확히 VibrationLog 구조체로 지정
    void saveCriticalLog(const VibrationLog& current_log); 

public:
    MachineMonitor(int id, IVibrationSensor* s1, IVibrationSensor* s2, IVibrationSensor* s3, int interval_sec = 30);
    void run(bool is_test_mode = false); 
};

#endif