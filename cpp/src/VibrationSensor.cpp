// src/VibrationSensor.cpp
#include "../include/IVibrationSensor.h"
#include <cstdlib>

// 표준 인터페이스를 상속받은 "실제 현장용 랜덤 센서" 클래스 정의
class RealVibrationSensor : public IVibrationSensor {
public:
    // 인터페이스의 규칙에 따라 평소 0~2회 진동 발생 기능 구현
    virtual int getVibration() override {
        return rand() % 3;
    }
};
// 메인 함수나 외부에서 진짜 센서 부품을 찍어낼 수 있도록 팩토리용 헬퍼 함수를 제공할 수도 있으나,
// 여기서는 깔끔하게 구현 부 안에서 분리만 해둡니다. (main에서 부를 수 있게 부모 타입으로 사용)