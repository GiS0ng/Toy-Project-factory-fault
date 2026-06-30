#ifndef I_VIBRATION_SENSOR_H
#define I_VIBRATION_SENSOR_H

// 모든 센서가 상속받아야 할 순수 추상 클래스
class IVibrationSensor {
public:
    virtual ~IVibrationSensor() {}
    
    // 이 부분이 똑바로 정의되어 있어야 자식 클래스에서 override를 쓸 수 있습니다.
    virtual int getVibration() = 0; 
};

#endif