#include <iostream>
#include <cstdlib>   // rand()를 사용하기 위함
#include <ctime>     // time()을 사용하기 위함
#include <thread>    // 1초씩 쉬어 가기 위함 (Sleep)
#include <chrono>
#include <string>

using namespace std;

// 1. 하나의 장비 내 3개 측정 포인트를 관리할 구조체 선언
struct EquipmentPoints {
    double pt1_bearing;  // 포인트 1: 베어링 부위 진동
    double pt2_rotor;    // 포인트 2: 모터 본체 부위 진동
    double pt3_gearbox;  // 포인트 3: 감속기 기어 부위 진동
};

int main() {
    srand(time(NULL));

    cout << "==================================================" << endl;
    cout << "  [스마트팩토리 설비별 3포인트 멀티 감시 시스템]   " << endl;
    cout << "==================================================" << endl;
    cout << "총 4개 호기의 '3포인트 센서 구조체' 메모리를 할당합니다.\n" << endl;

    // 2. 4개의 장비를 가리킬 포인터 배열 선언
    EquipmentPoints* machineAddresses[4];

    // 3. 포인터로 각 장비의 3포인트 구조체 메모리를 동적 할당
    for (int i = 0; i < 4; i++) {
        machineAddresses[i] = new EquipmentPoints; // 메모리에 PT1, PT2, PT3 방을 생성
        cout << "[메모리 할당] " << i + 1 << "호기 센서 모듈 주소: " << machineAddresses[i] << endl;
    }
    cout << "--------------------------------------------------" << endl;
    cout << "실시간 3포인트 위치별 모니터링을 시작합니다... (종료: Ctrl + C)\n" << endl;

    while (true) {
        // 4. 4개의 장비(포인터)를 돌면서 데이터 수집 및 검사
        for (int i = 0; i < 4; i++) {
            
            // 각 포인트의 평소 정상 진동 생성 (0.8 ~ 1.2 G)
            double vPT1 = 0.8 + ((rand() % 5) / 10.0);
            double vPT2 = 0.8 + ((rand() % 5) / 10.0);
            double vPT3 = 0.8 + ((rand() % 5) / 10.0);

            // 5%의 확률로 특정 호기의 '특정 위치(포인트)'에 이상 충격 발생 (3.0 ~ 4.5 G)
            if ((rand() % 20) == 0) {
                int randomPoint = rand() % 3; // 0:베어링, 1:본체, 2:감속기 불량 유도
                if (randomPoint == 0) vPT1 = 3.0 + ((rand() % 16) / 10.0);
                else if (randomPoint == 1) vPT2 = 3.0 + ((rand() % 16) / 10.0);
                else vPT3 = 3.0 + ((rand() % 16) / 10.0);
            }

            // ⭐ 포인터가 가리키는 구조체 메모리에 실시간 진동 데이터 저장
            machineAddresses[i]->pt1_bearing = vPT1;
            machineAddresses[i]->pt2_rotor = vPT2;
            machineAddresses[i]->pt3_gearbox = vPT3;

            // 출력 형식 설정 (소수점 한 자리)
            cout.precision(1);
            cout << fixed;

            // 5. 위치별 실시간 데이터 모니터링 출력
            cout << "[" << i + 1 << "호기] 베어링:" << machineAddresses[i]->pt1_bearing 
                 << " / 본체:" << machineAddresses[i]->pt2_rotor 
                 << " / 감속기:" << machineAddresses[i]->pt3_gearbox << " G";

            // 6. ⭐ 어느 한 포인트라도 3.0 G 이상이면 구체적인 에러 코드 생성
            if (machineAddresses[i]->pt1_bearing >= 3.0 || 
                machineAddresses[i]->pt2_rotor >= 3.0 || 
                machineAddresses[i]->pt3_gearbox >= 3.0) {
                
                string pointCode = "";
                if (machineAddresses[i]->pt1_bearing >= 3.0) pointCode = "_PT1_BEARING";
                else if (machineAddresses[i]->pt2_rotor >= 3.0) pointCode = "_PT2_ROTOR";
                else pointCode = "_PT3_GEARBOX";

                // 최종 고유 에러 코드 조합 (예: ERR_VIB_002_CH1_PT3_GEARBOX)
                string errorCode = "ERR_VIB_002_CH" + to_string(i + 1) + pointCode;
                cout << "  ➡️  [⚠️ ALARM] 에러코드: [" << errorCode << "]";
            }
            cout << endl;
        }

        cout << "--------------------------------------------------" << endl;
        this_thread::sleep_for(chrono::seconds(1));
    }

    // 7. 동적 할당 메모리 안전하게 해제
    for (int i = 0; i < 4; i++) {
        delete machineAddresses[i];
    }

    return 0;
}