cmake_minimum_required(VERSION 3.20)
project(factory_fault_monitor LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

add_library(factory_core
    cpp/src/EventSerializer.cpp
    cpp/src/MachineMonitor.cpp
    cpp/src/MachineProfile.cpp
    cpp/src/RmsAmplitudeSensor.cpp
    cpp/src/TelemetrySender.cpp
    cpp/src/VibrationEvaluator.cpp
)
target_include_directories(factory_core PUBLIC cpp/include)

if(MSVC)
    target_compile_options(factory_core PRIVATE /W4 /permissive-)
else()
    target_compile_options(factory_core PRIVATE -Wall -Wextra -Wpedantic)
endif()

if(WIN32)
    target_link_libraries(factory_core PUBLIC ws2_32)
endif()

add_executable(factory_monitor cpp/main.cpp)
target_link_libraries(factory_monitor PRIVATE factory_core)

include(CTest)
if(BUILD_TESTING)
    add_executable(factory_core_tests cpp/tests/factory_core_tests.cpp)
    target_link_libraries(factory_core_tests PRIVATE factory_core)
    add_test(NAME factory_core_tests COMMAND factory_core_tests)
endif()
