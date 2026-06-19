// main.cpp
#include <iostream>
#include <cstdlib>
#include <ctime>
#include "include/MachineMonitor.h" // 폴더 경로를 명시하여 설계도를 가져옴

int main() {
    srand(time(nullptr));

    // 1호기 모니터링 시스템 세팅 (호기번호: 1, 정기저장주기: 30초)
    MachineMonitor monitor1(1, 30);
    
    // 실행
    monitor1.run();

    return 0;
}