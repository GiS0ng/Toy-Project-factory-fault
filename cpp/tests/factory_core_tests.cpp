#include <cassert>
#include <filesystem>
#include <string>
#include <utility>
#include <vector>

#include "EventSerializer.h"
#include "MachineMonitor.h"
#include "VibrationEvaluator.h"

namespace {
class SequenceSensor final : public IVibrationSensor {
public:
    explicit SequenceSensor(std::vector<double> values) : values_(std::move(values)) {}

    double readVelocityRmsMmPerSec() override {
        assert(index_ < values_.size());
        return values_[index_++];
    }

    int sensorId() const override { return 1; }

private:
    std::vector<double> values_;
    std::size_t index_ = 0;
};

class CapturingSender final : public ITelemetrySender {
public:
    bool send(const std::string& message) override {
        messages.push_back(message);
        return true;
    }

    std::vector<std::string> messages;
};

MachineProfile testProfile(const std::filesystem::path& dataDirectory) {
    return {
        "ISO 20816-3:2022",
        "TEST_GROUP",
        SupportType::Rigid,
        20.0,
        1500,
        {2.0, 4.0, 6.0},
        4,
        1,
        3600,
        "127.0.0.1",
        9999,
        Protocol::Json,
        dataDirectory};
}
}  // namespace

int main() {
    const VibrationEvaluator evaluator({2.0, 4.0, 6.0});
    assert(evaluator.evaluate(0.0) == VibrationZone::A);
    assert(evaluator.evaluate(2.0) == VibrationZone::B);
    assert(evaluator.evaluate(4.0) == VibrationZone::C);
    assert(evaluator.evaluate(6.0) == VibrationZone::D);

    const VibrationEvent event{
        "2026-09-04T00:00:00Z", 1, {{1, 6.5}}, 6.5, VibrationZone::D, ErrorCode::Critical};
    assert(EventSerializer::toCsv(event) == "CRITICAL,1,6.500,2");
    const auto json = EventSerializer::toJson(event, "ISO 20816-3:2022");
    assert(json.find("\"version\":1") != std::string::npos);
    assert(json.find("\"zone\":\"D\"") != std::string::npos);

    const auto outputDirectory = std::filesystem::temp_directory_path() / "factory_fault_cpp_test";
    SequenceSensor sensor({6.1, 6.2, 6.3, 6.4});
    CapturingSender sender;
    MachineMonitor monitor(1, {&sensor}, testProfile(outputDirectory), sender);
    assert(monitor.sampleOnce() == MonitorResult::Continue);
    assert(monitor.sampleOnce() == MonitorResult::Continue);
    assert(monitor.sampleOnce() == MonitorResult::Continue);
    assert(monitor.sampleOnce() == MonitorResult::StopRequested);
    assert(sender.messages.size() == 4);

    bool foundCriticalLog = false;
    for (const auto& entry : std::filesystem::directory_iterator(outputDirectory)) {
        foundCriticalLog = foundCriticalLog || entry.path().filename().string().find("critical_") == 0;
    }
    assert(foundCriticalLog);
    return 0;
}
