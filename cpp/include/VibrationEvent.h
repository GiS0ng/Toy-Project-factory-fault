#pragma once

#include <string>
#include <vector>

#include "ErrorCode.h"

struct SensorReading {
    int sensorId;
    double velocityRmsMmPerSec;
};

struct VibrationEvent {
    std::string timestamp;
    int machineId;
    std::vector<SensorReading> readings;
    double maximumVelocityRmsMmPerSec;
    VibrationZone zone;
    ErrorCode errorCode;
};
