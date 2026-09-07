#pragma once

enum class VibrationZone { A, B, C, D };

enum class ErrorCode {
    Normal = 0,
    Warning = 1,
    Critical = 2,
};

inline ErrorCode toErrorCode(VibrationZone zone) {
    if (zone == VibrationZone::D) {
        return ErrorCode::Critical;
    }
    if (zone == VibrationZone::C) {
        return ErrorCode::Warning;
    }
    return ErrorCode::Normal;
}

inline const char* toString(VibrationZone zone) {
    switch (zone) {
        case VibrationZone::A:
            return "A";
        case VibrationZone::B:
            return "B";
        case VibrationZone::C:
            return "C";
        case VibrationZone::D:
            return "D";
    }
    return "UNKNOWN";
}
