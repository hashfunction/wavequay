# WaveQuay: retain the pinned PortAudio source and upstream patches, but
# never compile the proprietary ASIO SDK into this GPL distribution.
list(APPEND DEP_CMAKE_ARGS -DPA_USE_ASIO=OFF)
_bd_cmake_build("${SRC}")
