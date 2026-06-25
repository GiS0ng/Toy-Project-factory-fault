// main.cpp
#include <iostream>
#include <cstdlib>
#include <ctime>
#include <cstring>
#include <unistd.h>
#include <arpa/inet.h>
#include <sys/socket.h>
#include "include/MachineMonitor.h"
#include "include/RmsAmplitudeSensor.h"

using namespace std;

int main() {
    srand(time(nullptr));

    cout << "🏭 현장 물리 기반 RMS 센서 객체 조립 완료..." << endl;

    // 1. 분리된 독립 센서 객체 3개 생성
    RmsAmplitudeSensor s1(1), s2(2), s3(3);

    // 2. ⭐ 빼먹었던 모니터 엔진 객체 선언 복구!
    MachineMonitor monitor(1, &s1, &s2, &s3, 3);

    cout << "🚀 3초 주기 실시간 설비 모니터링 및 노션 전송 시작..." << endl;
    
    // 3초마다 지속적으로 데이터를 수집하여 서버로 전송하는 무한 루프
    while (true) {
        // 센서들로부터 실시간 진동 데이터 추출
        int v1 = s1.getVibration();
        int v2 = s2.getVibration();
        int v3 = s3.getVibration();

        int final_vibration = v1; 
        int error_code = 0; 

        // 파이썬 'parse_and_route' 규격 매칭: "데이터타입,기계ID,진동값,에러코드"
        string data_payload = "PERIODIC,1," + to_string(final_vibration) + "," + to_string(error_code);

        // 📡 3초마다 파이썬 서버에 연결하여 데이터 전송
        int sock = socket(AF_INET, SOCK_STREAM, 0);
        if (sock >= 0) {
            struct sockaddr_in serv_addr;
            memset(&serv_addr, 0, sizeof(serv_addr));
            serv_addr.sin_family = AF_INET;
            serv_addr.sin_port = htons(9999);      // 파이썬 포트 9999
            serv_addr.sin_addr.s_addr = inet_addr("127.0.0.1");

            if (connect(sock, (struct sockaddr*)&serv_addr, sizeof(serv_addr)) >= 0) {
                if (send(sock, data_payload.c_str(), data_payload.length(), 0) >= 0) {
                    cout << "[C++ ➔ 파이썬 3초 주기 전송 성공] 데이터: " << data_payload << endl;
                } else {
                    cerr << "❌ 데이터 전송 실패" << endl;
                }
            } else {
                cerr << "❌ 파이썬 서버 연결 실패! (receiver.py가 켜져 있는지 확인하세요)" << endl;
            }
            close(sock); // 전송 후 즉시 소켓 닫기
        }

        // ⏱️ 3초 대기
        sleep(3); 
    }

    return 0;
}