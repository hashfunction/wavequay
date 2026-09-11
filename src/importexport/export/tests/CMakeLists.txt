# The recipe boundary can be qualified without audio devices or binary SDKs.
if(CMAKE_SOURCE_DIR STREQUAL CMAKE_CURRENT_SOURCE_DIR)
    cmake_minimum_required(VERSION 3.24)
    project(wavequay_recipe_tests LANGUAGES CXX)
    set(CMAKE_CXX_STANDARD 17)
    enable_testing()
    find_package(Qt6 6.10 REQUIRED COMPONENTS Core)
    find_package(GTest CONFIG REQUIRED)
else()
    set(MODULE_TEST exportrecipestore_tests)
    set(MODULE_TEST_SRC
        ${CMAKE_CURRENT_LIST_DIR}/exportrecipestore_tests.cpp
        ${CMAKE_CURRENT_LIST_DIR}/exportrecipecontroller_tests.cpp)
    set(MODULE_TEST_LINK exporter)
    include(SetupGTest)
    return()
endif()

get_filename_component(WAVEQUAY_SOURCE_ROOT "${CMAKE_CURRENT_LIST_DIR}/../../../.." ABSOLUTE)
add_executable(exportrecipestore_tests
    exportrecipestore_tests.cpp
    exportrecipecontroller_tests.cpp
    ../internal/exportrecipecontroller.cpp
    ../internal/exportrecipestore.cpp
    ../types/exportrecipe.cpp
)
target_include_directories(exportrecipestore_tests PRIVATE
    "${WAVEQUAY_SOURCE_ROOT}/src" "${WAVEQUAY_SOURCE_ROOT}/muse")
target_link_libraries(exportrecipestore_tests PRIVATE Qt6::Core GTest::gtest_main)
add_test(NAME exportrecipestore_tests COMMAND exportrecipestore_tests)

include(${CMAKE_CURRENT_LIST_DIR}/model-integration.cmake)
