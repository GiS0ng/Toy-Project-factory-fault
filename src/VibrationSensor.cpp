// src/VibrationSensor.cpp
#include "../include/VibrationSensor.h" // 상위 폴더로 나가서 include를 찾음
#include <cstdlib>

int VibrationSensor::getVibration() const {
    return rand() % 3;
}