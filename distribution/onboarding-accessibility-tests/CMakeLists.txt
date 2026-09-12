# SPDX-License-Identifier: GPL-3.0-only
cmake_minimum_required(VERSION 3.24)
project(wavequay_onboarding_accessibility_tests LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_AUTOMOC ON)
find_package(Qt6 6.10 REQUIRED COMPONENTS Core Qml Quick QuickPrivate Widgets)
get_filename_component(WAVEQUAY_ROOT "${CMAKE_CURRENT_LIST_DIR}/../.." ABSOLUTE)
include(FetchContent)
FetchContent_Declare(wavequay_utfcpp
    URL "https://github.com/nemtrif/utfcpp/archive/refs/tags/v4.1.1.tar.gz"
    URL_HASH SHA256=1ca68016f0abc24172998e39ce0d8f8e2b7a26f7579a0ff85d4e1b9a7aea56f8
    DOWNLOAD_EXTRACT_TIMESTAMP TRUE SOURCE_SUBDIR source)
FetchContent_MakeAvailable(wavequay_utfcpp)
if(EXISTS "${WAVEQUAY_ROOT}/.ci-googletest/CMakeLists.txt")
    set(BUILD_GMOCK ON CACHE BOOL "" FORCE)
    set(gtest_force_shared_crt ON CACHE BOOL "" FORCE)
    add_subdirectory("${WAVEQUAY_ROOT}/.ci-googletest" googletest EXCLUDE_FROM_ALL)
else()
    find_package(GTest CONFIG REQUIRED)
endif()
set(MUSE "${WAVEQUAY_ROOT}/muse/framework")
set(GLOBAL "${MUSE}/global")
set(ACCESS "${MUSE}/accessibility")
set(NAV "${MUSE}/ui/qml/Muse/Ui")
set(THIRDPARTY "${GLOBAL}/thirdparty")
include("${THIRDPARTY}/kors_logger/logger.cmake")
include("${THIRDPARTY}/kors_profiler/profiler/profiler.cmake")
include("${THIRDPARTY}/kors_async/async/async.cmake")
set(MUSE_MODULE_MULTIWINDOWS OFF)
configure_file("${MUSE}/cmake/muse_framework_config.h.in" "${CMAKE_CURRENT_BINARY_DIR}/muse_framework_config.h")
add_executable(onboarding_accessibility_probe
    onboarding_accessibility_probe.cpp
    "${WAVEQUAY_ROOT}/src/appshell/internal/accessibilitygraphdiagnostics.cpp"
    "${WAVEQUAY_ROOT}/src/appshell/qml/Audacity/AppShell/FirstLaunchSetup/firstlaunchsetupmodel.cpp"
    ${KORS_LOGGER_SRC} ${KORS_PROFILER_SRC} ${KORS_ASYNC_SRC}
    "${THIRDPARTY}/kors_modularity/modularity/ioc.cpp"
    "${GLOBAL}/modularity/ioccontext.cpp" "${GLOBAL}/modularity/ioc.h"
    "${GLOBAL}/translation.cpp" "${GLOBAL}/types/string.cpp"
    "${GLOBAL}/types/bytearray.cpp" "${GLOBAL}/types/val.cpp"
    "${GLOBAL}/types/uri.cpp" "${GLOBAL}/stringutils.cpp"
    "${GLOBAL}/io/path.cpp" "${GLOBAL}/io/fileinfo.cpp" "${GLOBAL}/io/dir.cpp"
    "${GLOBAL}/types/ret.cpp" "${GLOBAL}/types/mnemonicstring.cpp"
    "${ACCESS}/internal/accessibilitycontroller.cpp"
    "${ACCESS}/internal/accessiblewindowinterface.cpp"
    "${ACCESS}/internal/accessibleobject.cpp"
    "${ACCESS}/internal/accessibleiteminterface.cpp"
    "${ACCESS}/internal/accessibleapprootobject.cpp"
    "${ACCESS}/internal/accessibleapprootinterface.cpp"
    "${ACCESS}/internal/accessiblestub.cpp"
    "${ACCESS}/internal/qaccessibleinterfaceregister.cpp"
    "${NAV}/qmlaccessible.cpp" "${NAV}/abstractnavigation.cpp"
    "${NAV}/navigationsection.cpp" "${NAV}/navigationpanel.cpp"
    "${NAV}/navigationcontrol.cpp" "${NAV}/navigationevent.cpp"
    "${MUSE}/ui/internal/navigationcontroller.cpp"
    "${MUSE}/actions/internal/actionsdispatcher.cpp"
    "${MUSE}/rcommand/internal/commanddispatcher.cpp")
target_include_directories(onboarding_accessibility_probe PRIVATE
    "${WAVEQUAY_ROOT}" "${WAVEQUAY_ROOT}/src" "${WAVEQUAY_ROOT}/src/appshell"
    "${WAVEQUAY_ROOT}/muse" "${MUSE}" "${GLOBAL}" "${ACCESS}" "${MUSE}/actions"
    "${MUSE}/rcommand" "${MUSE}/ui" "${CMAKE_CURRENT_BINARY_DIR}"
    ${KORS_LOGGER_INC} "${THIRDPARTY}/kors_profiler/profiler" "${wavequay_utfcpp_SOURCE_DIR}/source")
target_compile_definitions(onboarding_accessibility_probe PRIVATE
    KORS_LOGGER_QT_SUPPORT KORS_PROFILER_QT_SUPPORT AU_TRIEFLOW_DISTRIBUTION)
target_link_libraries(onboarding_accessibility_probe PRIVATE Qt6::Core Qt6::Qml Qt6::Quick Qt6::QuickPrivate Qt6::Widgets GTest::gmock)
if(MSVC)
    target_compile_options(onboarding_accessibility_probe PRIVATE /bigobj)
endif()
if(UNIX AND NOT APPLE)
    find_package(Qt6 REQUIRED COMPONENTS CorePrivate)
    target_link_libraries(onboarding_accessibility_probe PRIVATE Qt6::CorePrivate)
endif()
set(IMPORTS "${CMAKE_CURRENT_BINARY_DIR}/imports")
set(FONTS "${CMAKE_CURRENT_BINARY_DIR}/fonts")
file(MAKE_DIRECTORY "${FONTS}")
configure_file("${MUSE}/draw/tests/fonts/FreeSerif.ttf" "${FONTS}/FreeSerif.ttf" COPYONLY)
target_compile_definitions(onboarding_accessibility_probe PRIVATE WAVEQUAY_TEST_FONTS="${FONTS}")
file(MAKE_DIRECTORY "${IMPORTS}/Audacity/AppShell" "${IMPORTS}/Muse/UiComponents")
set(PAGES "${WAVEQUAY_ROOT}/src/appshell/qml/Audacity/AppShell/FirstLaunchSetup")
foreach(name Page FirstLaunchSetupDialog)
    configure_file("${PAGES}/${name}.qml" "${IMPORTS}/Audacity/AppShell/${name}.qml" COPYONLY)
endforeach()
foreach(name FlatButton StyledDialogView)
    configure_file("${MUSE}/uicomponents/qml/Muse/UiComponents/${name}.qml"
        "${IMPORTS}/Muse/UiComponents/${name}.qml" COPYONLY)
endforeach()
file(COPY "${CMAKE_CURRENT_SOURCE_DIR}/controls/" DESTINATION "${IMPORTS}/Muse/UiComponents")
file(COPY "${CMAKE_CURRENT_SOURCE_DIR}/pages/" DESTINATION "${IMPORTS}/Audacity/AppShell")
file(MAKE_DIRECTORY "${IMPORTS}/RecipeDialogs")
foreach(name SaveExportRecipeDialog ManageExportRecipesDialog)
    configure_file("${WAVEQUAY_ROOT}/src/importexport/export/qml/Export/${name}.qml"
        "${IMPORTS}/RecipeDialogs/${name}.qml" COPYONLY)
endforeach()
target_compile_definitions(onboarding_accessibility_probe PRIVATE WAVEQUAY_TEST_IMPORTS="${IMPORTS}")
