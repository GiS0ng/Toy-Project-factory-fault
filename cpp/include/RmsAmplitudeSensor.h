// include/RmsAmplitudeSensor.h
#ifndef RMS_AMPLITUDE_SENSOR_H
#define RMS_AMPLITUDE_SENSOR_H

#include <vector>
#include "IVibrationSensor.h"

class RmsAmplitudeSensor : public IVibrationSensor {
private:
    int sensorId;
    // 내부 진폭 샘플링 시뮬레이션용 헬퍼 함수
    std::vector<double> readRawAmplitudeSamples();

public:
    RmsAmplitudeSensor(int id);
    virtual ~RmsAmplitudeSensor() {}
    
    // 인터페이스 가상 함수 구현 선언
    virtual int getVibration() override; 
};

#endif