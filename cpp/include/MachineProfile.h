#pragma once

#include <filesystem>
#include <string>

enum class SupportType { Rigid, Flexible };
enum class Protocol { Json, Csv };

struct ZoneBoundaries {
    double zoneAB;
    double zoneBC;
    double zoneCD;
};

struct MachineProfile {
    std::string standard;
    std::string machineGroup;
    SupportType supportType;
    double ratedPowerKw;
    int operatingSpeedRpm;
    ZoneBoundaries boundaries;
    int consecutiveZoneDLimit;
    int sampleIntervalMs;
    int saveIntervalSeconds;
    std::string telemetryHost;
    int telemetryPort;
    Protocol protocol;
    std::filesystem::path dataDirectory;

    static MachineProfile load(const std::filesystem::path& path);
    void validate() const;
};
