#include "MachineMonitor.h"

#include <algorithm>
#include <ctime>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <thread>
#include <utility>

#include "EventSerializer.h"

namespace {
std::string formatTimestamp(std::chrono::system_clock::time_point timePoint, const char* format) {
    const std::time_t rawTime = std::chrono::system_clock::to_time_t(timePoint);
    std::tm utcTime{};
#ifdef _WIN32
    gmtime_s(&utcTime, &rawTime);
#else
    gmtime_r(&rawTime, &utcTime);
#endif
    std::ostringstream output;
    output << std::put_time(&utcTime, format);
    return output.str();
}
}  // namespace

MachineMonitor::MachineMonitor(
    int machineId,
    std::vector<IVibrationSensor*> sensors,
    MachineProfile profile,
    ITelemetrySender& telemetrySender,
    Clock clock)
    : machineId_(machineId),
      sensors_(std::move(sensors)),
      profile_(std::move(profile)),
      telemetrySender_(telemetrySender),
      clock_(std::move(clock)),
      evaluator_(profile_.boundaries),
      lastPeriodicSave_(clock_()) {
    profile_.validate();
    if (machineId_ <= 0 || sensors_.empty() ||
        std::any_of(sensors_.begin(), sensors_.end(), [](const auto* sensor) { return sensor == nullptr; })) {
        throw std::invalid_argument("설비 ID와 센서 구성이 잘못되었습니다");
    }
}

VibrationEvent MachineMonitor::collectEvent() {
    VibrationEvent event{};
    event.timestamp = formatTimestamp(clock_(), "%Y-%m-%dT%H:%M:%SZ");
    event.machineId = machineId_;

    for (auto* sensor : sensors_) {
        const double value = sensor->readVelocityRmsMmPerSec();
        if (value < 0.0) {
            throw std::runtime_error("센서가 음수 진동값을 반환했습니다");
        }
        event.readings.push_back({sensor->sensorId(), value});
        event.maximumVelocityRmsMmPerSec =
            std::max(event.maximumVelocityRmsMmPerSec, value);
    }
    event.zone = evaluator_.evaluate(event.maximumVelocityRmsMmPerSec);
    event.errorCode = toErrorCode(event.zone);
    return event;
}

void MachineMonitor::sendTelemetry(const VibrationEvent& event) {
    const std::string payload = profile_.protocol == Protocol::Json
                                    ? EventSerializer::toJson(event, profile_.standard)
                                    : EventSerializer::toCsv(event);
    if (!telemetrySender_.send(payload)) {
        std::cerr << "[WARN] Python 브리지 전송 실패; 로컬 로그는 계속 보존합니다.\n";
    }
}

bool MachineMonitor::saveEvents(
    const std::string& prefix, const std::vector<VibrationEvent>& events) {
    if (events.empty()) {
        return true;
    }
    std::error_code directoryError;
    std::filesystem::create_directories(profile_.dataDirectory, directoryError);
    if (directoryError) {
        std::cerr << "[ERROR] 데이터 디렉터리 생성 실패: " << directoryError.message() << '\n';
        return false;
    }

    const auto filename = prefix + "_" + std::to_string(machineId_) + "_" +
                          formatTimestamp(clock_(), "%Y%m%d_%H%M%S") + ".csv";
    const auto path = profile_.dataDirectory / filename;
    std::ofstream output(path, std::ios::out | std::ios::trunc);
    if (!output) {
        std::cerr << "[ERROR] 로그 파일 열기 실패: " << path.string() << '\n';
        return false;
    }
    output << "timestamp,machine_id,max_velocity_mm_s_rms,zone,error_code\n";
    for (const auto& event : events) {
        output << event.timestamp << ',' << event.machineId << ',' << std::fixed
               << std::setprecision(3) << event.maximumVelocityRmsMmPerSec << ','
               << toString(event.zone) << ',' << static_cast<int>(event.errorCode) << '\n';
    }
    output.flush();
    if (!output.good()) {
        std::cerr << "[ERROR] 로그 쓰기 실패: " << path.string() << '\n';
        return false;
    }
    std::cout << "[FILE] 로그 저장 완료: " << path.string() << '\n';
    return true;
}

bool MachineMonitor::savePeriodicLog() {
    if (!saveEvents("periodic", periodicBuffer_)) {
        return false;
    }
    periodicBuffer_.clear();
    lastPeriodicSave_ = clock_();
    return true;
}

bool MachineMonitor::savePreCrashLog(const VibrationEvent&) {
    if (!saveEvents("critical", periodicBuffer_)) {
        return false;
    }
    periodicBuffer_.clear();
    return true;
}

MonitorResult MachineMonitor::sampleOnce() {
    const auto event = collectEvent();
    periodicBuffer_.push_back(event);
    sendTelemetry(event);

    if (event.zone == VibrationZone::D) {
        ++consecutiveZoneDCount_;
    } else {
        consecutiveZoneDCount_ = 0;
    }

    std::cout << '[' << event.timestamp << "] Zone " << toString(event.zone) << " | Max "
              << std::fixed << std::setprecision(3) << event.maximumVelocityRmsMmPerSec
              << " mm/s RMS | D count " << consecutiveZoneDCount_ << '/'
              << profile_.consecutiveZoneDLimit << '\n';

    if (consecutiveZoneDCount_ >= profile_.consecutiveZoneDLimit) {
        lastSaveSucceeded_ = savePreCrashLog(event);
        return MonitorResult::StopRequested;
    }

    const auto elapsed =
        std::chrono::duration_cast<std::chrono::seconds>(clock_() - lastPeriodicSave_).count();
    if (elapsed >= profile_.saveIntervalSeconds) {
        lastSaveSucceeded_ = savePeriodicLog();
    }
    return MonitorResult::Continue;
}

int MachineMonitor::run() {
    std::cout << "ISO 20816-3:2022 설정형 진동 모니터를 시작합니다.\n";
    while (sampleOnce() == MonitorResult::Continue) {
        std::this_thread::sleep_for(std::chrono::milliseconds(profile_.sampleIntervalMs));
    }
    std::cout << "Zone D 연속 감지 한도에 도달해 정상 종료합니다.\n";
    return lastSaveSucceeded_ ? 0 : 2;
}
