cmake_minimum_required(VERSION 3.24)
project(wavequay_startup_diagnostics_tests LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 17)
find_package(Qt6 6.10 REQUIRED COMPONENTS Core)
get_filename_component(WAVEQUAY_ROOT "${CMAKE_CURRENT_LIST_DIR}/../.." ABSOLUTE)
set(LOGGER "${WAVEQUAY_ROOT}/muse/framework/global/thirdparty/kors_logger/src")
add_executable(startup_diagnostics_tests
    startup_diagnostics_tests.cpp
    ../startupdiagnostics.cpp
    "${LOGGER}/logger.cpp" "${LOGGER}/logdefdest.cpp")
target_include_directories(startup_diagnostics_tests PRIVATE "${WAVEQUAY_ROOT}/distribution" "${LOGGER}" "${WAVEQUAY_ROOT}/muse/framework/global")

if(WIN32)
    target_compile_definitions(startup_diagnostics_tests PRIVATE UNICODE _UNICODE)
endif()

# Match the production logger and Qt keyword/message-handler compilation.
target_compile_definitions(startup_diagnostics_tests PRIVATE KORS_LOGGER_QT_SUPPORT)
target_link_libraries(startup_diagnostics_tests PRIVATE Qt6::Core)
