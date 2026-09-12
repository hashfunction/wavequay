# cmake -C buildscripts/ci/windows/wavequay-release.cmake -S . -B build -G Ninja
set(AU_TRIEFLOW_DISTRIBUTION ON CACHE BOOL "Offline WaveWeft distribution")
set(AU4_BUILD_MODE release CACHE STRING "Release mode")
set(AU4_BUILD_CONFIGURATION app CACHE STRING "Desktop application")
set(CMAKE_BUILD_TYPE Release CACHE STRING "Build type")
set(MUSE_COMPILE_ASAN OFF CACHE BOOL "No sanitizer in release")
