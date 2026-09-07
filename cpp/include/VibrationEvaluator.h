#pragma once

#include "ErrorCode.h"
#include "MachineProfile.h"

class VibrationEvaluator {
public:
    explicit VibrationEvaluator(ZoneBoundaries boundaries);
    VibrationZone evaluate(double velocityRmsMmPerSec) const;

private:
    ZoneBoundaries boundaries_;
};
