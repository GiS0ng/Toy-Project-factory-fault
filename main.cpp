#include <iostream>
#include <vector>
#include <numeric>
#include <cstdlib>
#include <ctime>
#include <unistd.h> 
#include <fstream>  
#include <iomanip>  
#include <sstream>  

using namespace std;

enum ErrorCode {
    NORMAL = 0,
    NEED_INSPECTION = 101, 
    IMMEDIATE_STOP = 102   
};

string getTimeForFilename() {
    time_t now = time(0);
    struct tm tstruct;
    char buf[80];
    tstruct = *localtime(&now);
    strftime(buf, sizeof(buf), "%Y%m%d_%H%M%S", &tstruct);
    return string(buf);
}

string getCurrentTime() {
    time_t now = time(0);
    struct tm tstruct;
    char buf[80];
    tstruct = *localtime(&now);
    strftime(buf, sizeof(buf), "%Y-%m-%d %H:%M:%S", &tstruct);
    return string(buf);
}

int main() {
    srand(time(NULL));

    cout << "==================================================" << endl;
    cout << "  1호기 확률 조정된 진동 모니터링 시스템 시작 " << endl;
    cout << "==================================================" << endl;

    while (true) {
        cout << "\n[새로운 30초 모니터링 시작...]" << endl;

        // [수정 부분] 평소에는 0, 1, 2회 중에서만 진동이 발생하도록 대폭 낮춤
        int sensor1 = rand() % 3; 
        int sensor2 = rand() % 3;
        int sensor3 = rand() % 3;

        // [수정 부분] 돌발 변수 추가 (20%의 확률로 대형 진동 노이즈 발생)
        // 0부터 9까지의 숫자 중 0이나 1이 나오면 기계가 일시적으로 덜컹거림
        int machine_condition = rand() % 10;
        if (machine_condition == 0) {
            cout << "ℹ️ [현장 상황] 설비에 가벼운 일시적 충격 감지 (+6회)" << endl;
            sensor1 += 3;
            char buf[80];
            sensor2 += 3;
        } 
        else if (machine_condition == 1) {
            cout << "🚨 [현장 상황] 설비에 대형 모터 이상 진동 감지 (+18회)" << endl;
            sensor1 += 6;
            sensor2 += 6;
            sensor3 += 6;
        }

        int total_vibrations = sensor1 + sensor2 + sensor3;

        // 최대 30회를 넘지 않도록 안전장치 마련
        if (total_vibrations > 30) total_vibrations = 30;

        cout << " -> 센서 상세 정보 [ S1: " << sensor1 << "회 | S2: " << sensor2 << "회 | S3: " << sensor3 << "회 ]" << endl;
        cout << " >> 1호기 총 누적 진동: [ " << total_vibrations << " 회 ]" << endl;

        int current_error_code = NORMAL;
        string error_type = "NORMAL";
        bool should_shutdown = false;

        if (total_vibrations <= 4) {
            current_error_code = NORMAL;
            error_type = "NORMAL";
            cout << "【결과】 정상 작동 중" << endl;
        } 
        else if (total_vibrations >= 5 && total_vibrations <= 15) {
            current_error_code = NEED_INSPECTION;
            error_type = "WARNING";
            cout << "【결과】 ⚠️ 경고: 설비 육안 점검 필요 (에러코드: " << current_error_code << ")" << endl;
        } 
        else if (total_vibrations >= 16 && total_vibrations <= 30) {
            current_error_code = IMMEDIATE_STOP;
            error_type = "CRITICAL";
            cout << "【결과】 🚨 비상: 설비 즉시 스탑!!! (에러코드: " << current_error_code << ")" << endl;
            should_shutdown = true;
        }

        // 파일 이름 및 저장 로직
        stringstream filename_stream;
        filename_stream << getTimeForFilename() << "_1호기_" << error_type << ".csv";
        string final_filename = filename_stream.str();

        ofstream logFile(final_filename); 
        if (logFile.is_open()) {
            logFile << getCurrentTime() << ", " << "1, " << total_vibrations << ", " << current_error_code << "\n";
            logFile.close(); 
            cout << "💾 고유 로그 파일 생성 완료: [ " << final_filename << " ]" << endl;
        }

        if (should_shutdown) {
            cout << "\n[SYSTEM SHUTDOWN] 치명적인 에러(102) 감지로 인해 시스템을 강제 종료합니다." << endl;
            cout << "==================================================" << endl;
            exit(0); 
        }

        cout << "--------------------------------------------------" << endl;
        sleep(3); 
    }

    return 0;
}