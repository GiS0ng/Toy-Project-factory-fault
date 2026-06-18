#include <iostream>
#include <vector>
#include <numeric>
#include <cstdlib>
#include <ctime>
#include <unistd.h> // sleep 기능을 위해 사용

using namespace std;

// 에러 코드를 정의하는 열거형 (나중에 파이썬으로 보낼 때 사용하기 좋습니다)
enum ErrorCode {
    NORMAL = 0,
    NEED_INSPECTION = 101, // 5~15회: 육안 점검
    IMMEDIATE_STOP = 102   // 16~30회: 즉시 스탑
};

int main() {
    // 랜덤 함수 초기화
    srand(time(NULL));

    cout << "==================================================" << endl;
    cout << "  1호기 3포인트 센서 진동 모니터링 시스템 (30초 주기) " << endl;
    cout << "==================================================" << endl;

    // 실시간으로 계속 감시하는 루프
    while (true) {
        cout << "\n[새로운 30초 모니터링 시작...]" << endl;

        // 1호기에 있는 3개의 센서의 진동 횟수를 기록할 변수
        int sensor1 = 0;
        int sensor2 = 0;
        int sensor3 = 0;

        // 30초 동안 진동이 쌓이는 과정을 시뮬레이션 (원래는 센서 하드웨어 값을 읽어옴)
        // 각 센서는 최대 10회까지 진동할 수 있음 (0 ~ 10 랜덤 발생)
        sensor1 = rand() % 11;
        sensor2 = rand() % 11;
        sensor3 = rand() % 11;

        // 1호기 총 진동 횟수 합산 (최대 30회)
        int total_vibrations = sensor1 + sensor2 + sensor3;

        cout << " -> 센서 1번 진동 횟수: " << sensor1 << " 회" << endl;
        cout << " -> 센서 2번 진동 횟수: " << sensor2 << " 회" << endl;
        cout << " -> 센서 3번 진동 횟수: " << sensor3 << " 회" << endl;
        cout << " >> 1호기 30초간 총 누적 진동: [ " << total_vibrations << " 회 ]" << endl;

        // --- 여기서부터 회원님이 기획하신 3안 조건문 알고리즘입니다 ---
        int current_error_code = NORMAL;

        if (total_vibrations <= 4) {
            current_error_code = NORMAL;
            cout << "【결과】 에러 없음: 설비가 안정적으로 작동 중입니다." << endl;
        } 
        else if (total_vibrations >= 5 && total_vibrations <= 15) {
            current_error_code = NEED_INSPECTION;
            cout << "【결과】 에러 코드 [ " << current_error_code << " ] 발생 !!" << endl;
            cout << "        ⚠️ 경고: 설비 육안 점검이 필요합니다. (5~15회 조건 걸림)" << endl;
        } 
        else if (total_vibrations >= 16 && total_vibrations <= 30) {
            current_error_code = IMMEDIATE_STOP;
            cout << "【결과】 에러 코드 [ " << current_error_code << " ] 발생 !!!" << endl;
            cout << "        🚨 비상: 설비 즉시 스탑!!! (16~30회 위험 조건 걸림)" << endl;
        }

        cout << "--------------------------------------------------" << endl;
        
        // 30초 주기를 가상으로 표현하기 위해 3초만 쉬고 다음 감시로 넘어갑니다.
        // (테스트를 빠르게 하기 위해 잠시 3초로 해두었습니다)
        sleep(3); 
    }

    return 0;
}