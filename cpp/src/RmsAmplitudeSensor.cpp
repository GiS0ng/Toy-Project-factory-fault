#include "RmsAmplitudeSensor.h"

RmsAmplitudeSensor::RmsAmplitudeSensor(int id, unsigned int seed)
    : sensorId_(id), generator_(seed) {}

double RmsAmplitudeSensor::readVelocityRmsMmPerSec() {
    std::uniform_real_distribution<double> probability(0.0, 1.0);
    const double roll = probability(generator_);

    if (roll < 0.92) {
        return std::uniform_real_distribution<double>(0.0, 3.99)(generator_);
    }
    if (roll < 0.97) {
        return std::uniform_real_distribution<double>(4.0, 5.99)(generator_);
    }
    return std::uniform_real_distribution<double>(6.0, 8.0)(generator_);
}

int RmsAmplitudeSensor::sensorId() const { return sensorId_; }
