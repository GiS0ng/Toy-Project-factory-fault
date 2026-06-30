#include "../include/RmsAmplitudeSensor.h"
#include <cstdlib>

RmsAmplitudeSensor::RmsAmplitudeSensor(int id) : sensorId(id) {}

int RmsAmplitudeSensor::getVibration() {
    int dice = rand() % 100;
    
    if (dice < 92) { 
        // Grade A/B: 0 ~ 399 μm/s
        return rand() % 400;
    } 
    else if (dice < 97) { 
        // Grade C: 400 ~ 599 μm/s
        return 400 + (rand() % 200);
    } 
    else { 
        // Grade D: 600 ~ 800 μm/s
        return 600 + (rand() % 201);
    }
}