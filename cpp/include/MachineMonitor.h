#pragma once

#include <chrono>
#include <functional>
#include <string>
#include <vector>

#include "IVibrationSensor.h"
#include "MachineProfile.h"
#include "TelemetrySender.h"
#include "VibrationEvaluator.h"
#include "VibrationEvent.h"

enum class MonitorResult { Continue, StopRequested };

class MachineMonitor {
public:
    using Clock = std::function<std::chrono::system_clock::time_point()>;

    MachineMonitor(
        int machineId,
        std::vector<IVibrationSensor*> sensors,
        MachineProfile profile,
        ITelemetrySender& telemetrySender,
        Clock clock = std::chrono::system_clock::now);

    MonitorResult sampleOnce();
    int run();

private:
    int machineId_;
    std::vector<IVibrationSensor*> sensors_;
    MachineProfile profile_;
    ITelemetrySender& telemetrySender_;
    Clock clock_;
    VibrationEvaluator evaluator_;
    int consecutiveZoneDCount_ = 0;
    bool lastSaveSucceeded_ = true;
    std::chrono::system_clock::time_point lastPeriodicSave_;
    std::vector<VibrationEvent> periodicBuffer_;

    VibrationEvent collectEvent();
    bool saveEvents(const std::string& prefix, const std::vector<VibrationEvent>& events);
    bool savePeriodicLog();
    bool savePreCrashLog(const VibrationEvent& currentEvent);
    void sendTelemetry(const VibrationEvent& event);
};
