#pragma once

#include <string>

#include "VibrationEvent.h"

class EventSerializer {
public:
    static std::string toCsv(const VibrationEvent& event);
    static std::string toJson(const VibrationEvent& event, const std::string& standard);
};
