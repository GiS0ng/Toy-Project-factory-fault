// main.cpp
#include <iostream>
#include <cstdlib>
#include <ctime>
#include "include/MachineMonitor.h"
#include "include/RmsAmplitudeSensor.h" // 헤더 추가 ★

using namespace std;

int main() {
    srand(time(nullptr));

    cout << "🏭 현장 물리 기반 RMS 센서 객체 조립 완료..." << endl;

    // 분리된 독립 센서 객체 3개 생성
    RmsAmplitudeSensor s1(1), s2(2), s3(3);
    
    // 15초 주기로 정기 스캔하도록 모니터 엔진 가동
    MachineMonitor monitor(1, &s1, &s2, &s3, 15);
    monitor.run(false); 

    return 0;
}