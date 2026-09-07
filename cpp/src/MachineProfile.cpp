#include "MachineProfile.h"

#include <algorithm>
#include <cctype>
#include <fstream>
#include <map>
#include <stdexcept>

namespace {
std::string trim(std::string value) {
    const auto isNotSpace = [](unsigned char ch) { return !std::isspace(ch); };
    value.erase(value.begin(), std::find_if(value.begin(), value.end(), isNotSpace));
    value.erase(std::find_if(value.rbegin(), value.rend(), isNotSpace).base(), value.end());
    return value;
}

std::map<std::string, std::string> readValues(const std::filesystem::path& path) {
    std::ifstream input(path);
    if (!input) {
        throw std::runtime_error("설정 파일을 열 수 없습니다: " + path.string());
    }

    std::map<std::string, std::string> values;
    std::string line;
    int lineNumber = 0;
    while (std::getline(input, line)) {
        ++lineNumber;
        line = trim(line);
        if (line.empty() || line.front() == '#') {
            continue;
        }
        const auto separator = line.find('=');
        if (separator == std::string::npos) {
            throw std::runtime_error("잘못된 설정 행: " + std::to_string(lineNumber));
        }
        const auto key = trim(line.substr(0, separator));
        const auto value = trim(line.substr(separator + 1));
        if (key.empty() || value.empty()) {
            throw std::runtime_error("빈 설정 키 또는 값: " + std::to_string(lineNumber));
        }
        if (!values.emplace(key, value).second) {
            throw std::runtime_error("중복 설정 키: " + key);
        }
    }
    return values;
}

const std::string& required(
    const std::map<std::string, std::string>& values, const std::string& key) {
    const auto found = values.find(key);
    if (found == values.end()) {
        throw std::runtime_error("필수 설정 누락: " + key);
    }
    return found->second;
}
}  // namespace

MachineProfile MachineProfile::load(const std::filesystem::path& path) {
    const auto values = readValues(path);
    const auto support = required(values, "support_type");
    const auto protocolValue = required(values, "protocol");

    MachineProfile profile{
        required(values, "standard"),
        required(values, "machine_group"),
        support == "rigid" ? SupportType::Rigid : SupportType::Flexible,
        std::stod(required(values, "rated_power_kw")),
        std::stoi(required(values, "operating_speed_rpm")),
        {std::stod(required(values, "zone_ab_mm_s_rms")),
         std::stod(required(values, "zone_bc_mm_s_rms")),
         std::stod(required(values, "zone_cd_mm_s_rms"))},
        std::stoi(required(values, "consecutive_zone_d_limit")),
        std::stoi(required(values, "sample_interval_ms")),
        std::stoi(required(values, "save_interval_seconds")),
        required(values, "telemetry_host"),
        std::stoi(required(values, "telemetry_port")),
        protocolValue == "json" ? Protocol::Json : Protocol::Csv,
        required(values, "data_directory")};

    if (support != "rigid" && support != "flexible") {
        throw std::runtime_error("support_type은 rigid 또는 flexible이어야 합니다");
    }
    if (protocolValue != "json" && protocolValue != "csv") {
        throw std::runtime_error("protocol은 json 또는 csv여야 합니다");
    }
    profile.validate();
    return profile;
}

void MachineProfile::validate() const {
    if (standard != "ISO 20816-3:2022") {
        throw std::runtime_error("지원하지 않는 표준 버전입니다: " + standard);
    }
    if (machineGroup.empty()) {
        throw std::runtime_error("machine_group은 비워 둘 수 없습니다");
    }
    if (ratedPowerKw <= 15.0) {
        throw std::runtime_error("ISO 20816-3:2022 프로필은 정격 출력 15 kW 초과가 필요합니다");
    }
    if (operatingSpeedRpm < 120 || operatingSpeedRpm > 30000) {
        throw std::runtime_error("운전 속도는 120~30000 r/min 범위여야 합니다");
    }
    if (!(0.0 < boundaries.zoneAB && boundaries.zoneAB < boundaries.zoneBC &&
          boundaries.zoneBC < boundaries.zoneCD)) {
        throw std::runtime_error("Zone 경계값은 0 < AB < BC < CD 순서여야 합니다");
    }
    if (consecutiveZoneDLimit <= 0 || sampleIntervalMs <= 0 || saveIntervalSeconds <= 0) {
        throw std::runtime_error("반복 횟수와 시간 설정은 양수여야 합니다");
    }
    if (telemetryPort < 1 || telemetryPort > 65535) {
        throw std::runtime_error("telemetry_port 범위가 잘못되었습니다");
    }
}
