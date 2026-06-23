#include <iostream>
#include <cstdlib>
#include <ctime>
#include "include/MachineMonitor.h"
#include "include/IVibrationSensor.h"

using namespace std;

// [진짜 현장용 센서]
class RealSensor : public IVibrationSensor {
public:
    virtual int getVibration() override { return rand() % 3; }
};

// [테스트용 가전 값 고정 센서]
class FixedValueSensor : public IVibrationSensor {
private:
    int val;
public:
    FixedValueSensor(int v) : val(v) {}
    virtual int getVibration() override { return val; }
};

int main() {
    srand(time(nullptr));

    // 0: 실제 공장 모드, 1: 시나리오 테스트 모드
    int mode = 0; 

    if (mode == 0) {
        RealSensor s1, s2, s3;
        MachineMonitor monitor1(1, &s1, &s2, &s3, 30);
        monitor1.run(false); 
    } 
    else if (mode == 1) {
        // 무조건 센서당 6씩 뱉어서 총 18회(비상) 유발 테스트
        FixedValueSensor mock_s1(6), mock_s2(6), mock_s3(6);
        
        MachineMonitor test_monitor(1, &mock_s1, &mock_s2, &mock_s3, 15);
        test_monitor.run(true); 
    }

    return 0;
}