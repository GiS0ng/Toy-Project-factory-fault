#pragma once

#include <random>
#include "IVibrationSensor.h"

class RmsAmplitudeSensor : public IVibrationSensor {
private:
    int sensorId_;
    std::mt19937 generator_;

public:
    explicit RmsAmplitudeSensor(int id, unsigned int seed = std::random_device{}());
    double readVelocityRmsMmPerSec() override;
    int sensorId() const override;
};
