#include <iostream>
#include <cstdlib>
#include <ctime>
#include "include/MachineMonitor.h"
#include "include/RmsAmplitudeSensor.h"

using namespace std;

int main() {
    srand(time(nullptr));

    // 1. 센서 부품 조립
    RmsAmplitudeSensor s1(1), s2(2), s3(3);

    // 2. 모니터링 엔진 생성 (기계ID: 1, 센서들, 파일저장주기: 30초)
    MachineMonitor monitor(1, &s1, &s2, &s3, 30);

    // 3. 엔진 가동
    monitor.run();

    return 0;
}