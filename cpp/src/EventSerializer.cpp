#include "EventSerializer.h"

#include <iomanip>
#include <sstream>

namespace {
std::string messageType(VibrationZone zone) {
    if (zone == VibrationZone::D) {
        return "CRITICAL";
    }
    if (zone == VibrationZone::C) {
        return "WARNING";
    }
    return "PERIODIC";
}

std::string escapeJson(const std::string& input) {
    std::string output;
    for (const char ch : input) {
        if (ch == '\\' || ch == '"') {
            output.push_back('\\');
        }
        output.push_back(ch);
    }
    return output;
}
}  // namespace

std::string EventSerializer::toCsv(const VibrationEvent& event) {
    std::ostringstream output;
    output << messageType(event.zone) << ',' << event.machineId << ',' << std::fixed
           << std::setprecision(3) << event.maximumVelocityRmsMmPerSec << ','
           << static_cast<int>(event.errorCode);
    return output.str();
}

std::string EventSerializer::toJson(const VibrationEvent& event, const std::string& standard) {
    std::ostringstream output;
    output << "{\"version\":1,\"type\":\"" << messageType(event.zone)
           << "\",\"timestamp\":\"" << escapeJson(event.timestamp) << "\",\"machine_id\":"
           << event.machineId << ",\"standard\":\"" << escapeJson(standard)
           << "\",\"unit\":\"mm/s RMS\",\"max_velocity_rms\":" << std::fixed
           << std::setprecision(3) << event.maximumVelocityRmsMmPerSec << ",\"zone\":\""
           << toString(event.zone) << "\",\"error_code\":" << static_cast<int>(event.errorCode)
           << ",\"readings\":[";
    for (std::size_t index = 0; index < event.readings.size(); ++index) {
        if (index > 0) {
            output << ',';
        }
        output << "{\"sensor_id\":" << event.readings[index].sensorId << ",\"velocity_rms\":"
               << event.readings[index].velocityRmsMmPerSec << '}';
    }
    output << "]}";
    return output.str();
}
