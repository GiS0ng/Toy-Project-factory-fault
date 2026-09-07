#pragma once

// 모든 센서가 상속받아야 할 순수 추상 클래스
class IVibrationSensor {
public:
    virtual ~IVibrationSensor() = default;
    virtual double readVelocityRmsMmPerSec() = 0;
    virtual int sensorId() const = 0;
};
