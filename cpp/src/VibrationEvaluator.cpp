#include "VibrationEvaluator.h"

#include <stdexcept>

VibrationEvaluator::VibrationEvaluator(ZoneBoundaries boundaries) : boundaries_(boundaries) {
    if (!(0.0 < boundaries_.zoneAB && boundaries_.zoneAB < boundaries_.zoneBC &&
          boundaries_.zoneBC < boundaries_.zoneCD)) {
        throw std::invalid_argument("Zone 경계값 순서가 잘못되었습니다");
    }
}

VibrationZone VibrationEvaluator::evaluate(double value) const {
    if (value < 0.0) {
        throw std::invalid_argument("진동 속도 RMS는 음수일 수 없습니다");
    }
    if (value < boundaries_.zoneAB) {
        return VibrationZone::A;
    }
    if (value < boundaries_.zoneBC) {
        return VibrationZone::B;
    }
    if (value < boundaries_.zoneCD) {
        return VibrationZone::C;
    }
    return VibrationZone::D;
}
