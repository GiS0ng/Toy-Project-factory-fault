#include <exception>
#include <iostream>
#include <vector>

#include "MachineMonitor.h"
#include "MachineProfile.h"
#include "RmsAmplitudeSensor.h"
#include "TelemetrySender.h"

int main(int argc, char* argv[]) {
    if (argc != 2) {
        std::cerr << "사용법: factory_monitor <machine-profile.conf>\n";
        return 64;
    }

    try {
        const auto profile = MachineProfile::load(argv[1]);
        RmsAmplitudeSensor sensor1(1);
        RmsAmplitudeSensor sensor2(2);
        RmsAmplitudeSensor sensor3(3);
        TcpTelemetrySender sender(profile.telemetryHost, profile.telemetryPort);
        MachineMonitor monitor(
            1,
            std::vector<IVibrationSensor*>{&sensor1, &sensor2, &sensor3},
            profile,
            sender);
        return monitor.run();
    } catch (const std::exception& error) {
        std::cerr << "초기화 또는 실행 실패: " << error.what() << '\n';
        return 1;
    }
}
