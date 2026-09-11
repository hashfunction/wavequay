# Device-free integration of the real model, real export settings and Muse IoC.
# The encoder/filesystem/UI services are mocks; no GUI application is started.
find_package(Qt6 6.10 REQUIRED COMPONENTS Core Gui Qml Widgets)
set(WAVEQUAY_GLOBAL "${WAVEQUAY_SOURCE_ROOT}/muse/framework/global")
include(FetchContent)
set(WAVEQUAY_UTFCPP_URL "https://github.com/nemtrif/utfcpp/archive/refs/tags/v4.1.1.tar.gz")
set(WAVEQUAY_UTFCPP_SHA256 "1ca68016f0abc24172998e39ce0d8f8e2b7a26f7579a0ff85d4e1b9a7aea56f8")
set(WAVEQUAY_UTFCPP_ARCHIVE "${CMAKE_CURRENT_BINARY_DIR}/test-dependency-downloads/utfcpp-4.1.1.tar.gz")
file(MAKE_DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}/test-dependency-downloads")
if(NOT EXISTS "${WAVEQUAY_UTFCPP_ARCHIVE}")
    file(DOWNLOAD "${WAVEQUAY_UTFCPP_URL}" "${WAVEQUAY_UTFCPP_ARCHIVE}"
        EXPECTED_HASH "SHA256=${WAVEQUAY_UTFCPP_SHA256}" TLS_VERIFY ON)
endif()
file(SHA256 "${WAVEQUAY_UTFCPP_ARCHIVE}" WAVEQUAY_UTFCPP_ACTUAL_SHA256)
if(NOT WAVEQUAY_UTFCPP_ACTUAL_SHA256 STREQUAL WAVEQUAY_UTFCPP_SHA256)
    message(FATAL_ERROR "WaveQuay utfcpp archive hash does not match the pinned Muse dependency")
endif()
if(FETCHCONTENT_SOURCE_DIR_WAVEQUAY_UTFCPP)
    message(FATAL_ERROR "The qualified test host requires the verified utfcpp source archive")
endif()
FetchContent_Declare(wavequay_utfcpp
    URL "${WAVEQUAY_UTFCPP_ARCHIVE}"
    URL_HASH "SHA256=${WAVEQUAY_UTFCPP_SHA256}"
    DOWNLOAD_EXTRACT_TIMESTAMP TRUE)
FetchContent_GetProperties(wavequay_utfcpp)
if(NOT wavequay_utfcpp_POPULATED)
    FetchContent_Populate(wavequay_utfcpp)
endif()
file(TO_CMAKE_PATH "${GTest_DIR}" WAVEQUAY_GTEST_CONFIG_DIR)
file(CONFIGURE OUTPUT "${CMAKE_CURRENT_BINARY_DIR}/wavequay-test-dependencies.json" CONTENT [=[
{
  "schemaVersion": 1,
  "utfcpp": {
    "version": "4.1.1",
    "url": "@WAVEQUAY_UTFCPP_URL@",
    "expectedSha256": "@WAVEQUAY_UTFCPP_SHA256@",
    "verifiedArchiveSha256": "@WAVEQUAY_UTFCPP_ACTUAL_SHA256@",
    "archive": "test-dependency-downloads/utfcpp-4.1.1.tar.gz",
    "verification": "CMake file(SHA256) equality check before FetchContent; URL_HASH verifies extraction input"
  },
  "gtest": {
    "source": "Externally configured GTest CONFIG package; repository pin supplied by qualification runner",
    "version": "@GTest_VERSION@",
    "configDirectory": "@WAVEQUAY_GTEST_CONFIG_DIR@",
    "requiredTargets": ["GTest::gtest_main", "GTest::gmock"]
  },
  "host": "QCoreApplication; actual export model, export configuration, Muse settings and IoC; mocked encoder and UI services",
  "qtVersion": "@Qt6_VERSION@"
}
]=] @ONLY)
# Configure the real framework template for this isolated, single-process host.
set(MUSE_MODULE_MULTIWINDOWS OFF)
configure_file("${WAVEQUAY_GLOBAL}/../cmake/muse_framework_config.h.in"
    "${CMAKE_CURRENT_BINARY_DIR}/model-host/muse_framework_config.h")
include("${WAVEQUAY_GLOBAL}/thirdparty/kors_logger/logger.cmake")
include("${WAVEQUAY_GLOBAL}/thirdparty/kors_modularity/modularity/modularity.cmake")
include("${WAVEQUAY_GLOBAL}/thirdparty/kors_async/async/async.cmake")
add_executable(exportpreferencesmodel_recipe_tests
    exportpreferencesmodel_recipe_tests.cpp
    ../view/exportpreferencesmodel.cpp ../view/exportpreferencesmodel.h
    ../internal/exportconfiguration.cpp ../internal/exportconfiguration.h
    ../internal/exportrecipestore.cpp ../internal/exportrecipecontroller.cpp
    ../types/exportrecipe.cpp ../types/exporttypes.h ../exportutils.cpp
    "${WAVEQUAY_SOURCE_ROOT}/src/trackedit/trackeditutils.cpp"
    ${KORS_LOGGER_SRC} ${KORS_MODULARITY_SRC} ${KORS_ASYNC_SRC}
    "${WAVEQUAY_GLOBAL}/modularity/ioccontext.cpp" "${WAVEQUAY_GLOBAL}/modularity/ioc.h"
    "${WAVEQUAY_GLOBAL}/types/val.cpp" "${WAVEQUAY_GLOBAL}/types/ret.cpp"
    "${WAVEQUAY_GLOBAL}/types/string.cpp" "${WAVEQUAY_GLOBAL}/types/bytearray.cpp"
    "${WAVEQUAY_GLOBAL}/types/uri.cpp" "${WAVEQUAY_GLOBAL}/types/datetime.cpp"
    "${WAVEQUAY_GLOBAL}/io/path.cpp" "${WAVEQUAY_GLOBAL}/io/fileinfo.cpp"
    "${WAVEQUAY_GLOBAL}/io/dir.cpp"
    "${WAVEQUAY_GLOBAL}/stringutils.cpp" "${WAVEQUAY_GLOBAL}/translation.cpp"
    "${WAVEQUAY_GLOBAL}/settings.cpp" "${WAVEQUAY_GLOBAL}/runtime.cpp"
)
set_target_properties(exportpreferencesmodel_recipe_tests PROPERTIES AUTOMOC ON)
# The real model and GoogleMock interfaces exceed classic COFF section limits.
if(MSVC)
    target_compile_options(exportpreferencesmodel_recipe_tests PRIVATE /bigobj)
endif()
target_compile_definitions(exportpreferencesmodel_recipe_tests PRIVATE KORS_LOGGER_QT_SUPPORT)
target_include_directories(exportpreferencesmodel_recipe_tests PRIVATE
    "${WAVEQUAY_SOURCE_ROOT}/src" "${WAVEQUAY_SOURCE_ROOT}/src/appshell"
    "${WAVEQUAY_SOURCE_ROOT}/muse" "${WAVEQUAY_SOURCE_ROOT}/muse/framework"
    "${WAVEQUAY_GLOBAL}" "${wavequay_utfcpp_SOURCE_DIR}/source"
    "${CMAKE_CURRENT_BINARY_DIR}/model-host")
target_link_libraries(exportpreferencesmodel_recipe_tests PRIVATE
    Qt6::Core Qt6::Gui Qt6::Qml Qt6::Widgets GTest::gmock)
add_test(NAME exportpreferencesmodel_recipe_tests COMMAND exportpreferencesmodel_recipe_tests)
