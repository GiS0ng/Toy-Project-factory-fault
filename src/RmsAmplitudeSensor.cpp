// src/RmsAmplitudeSensor.cpp
#include "../include/RmsAmplitudeSensor.h"
#include <cstdlib>
#include <cmath>

using namespace std;

RmsAmplitudeSensor::RmsAmplitudeSensor(int id) : sensorId(id) {}

// 1초 동안 100번 미세 진폭 파형 샘플링 시뮬레이션
vector<double> RmsAmplitudeSensor::readRawAmplitudeSamples() {
    vector<double> samples;
    for (int i = 0; i < 100; ++i) {
        double baseWave = sin(i * 0.1) * 1.2; 
        double noise = ((rand() % 100) / 100.0) * 0.4; 

        // 1/15 확률로 순간 강한 물리 충격 진폭 발생 연출
        if (rand() % 15 == 0) {
            baseWave *= 6.5; 
        }
        samples.push_back(baseWave + noise); 
    }
    return samples;
}

// 핵심 RMS 연산 알고리즘 처리 후 정수형 지수로 변환
int RmsAmplitudeSensor::getVibration() {
    vector<double> samples = readRawAmplitudeSamples();
    
    double sumOfSquares = 0.0;
    for (double amplitude : samples) {
        sumOfSquares += amplitude * amplitude; // 1. 제곱의 합
    }
    double meanOfSquares = sumOfSquares / samples.size(); // 2. 평균
    double rmsValue = sqrt(meanOfSquares); // 3. 루트 (실효값)
    
    int finalVibrationIndex = static_cast<int>(rmsValue * 10); 
    if (finalVibrationIndex > 30) finalVibrationIndex = 30;

    return finalVibrationIndex; 
}