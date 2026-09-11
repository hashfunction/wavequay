# SPDX-License-Identifier: GPL-3.0-only
cmake_minimum_required(VERSION 3.24)
project(wavequay_qml_module_tests LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_AUTOMOC ON)
find_package(Qt6 6.10 REQUIRED COMPONENTS Core Qml Quick Widgets)
get_filename_component(WAVEQUAY_ROOT "${CMAKE_CURRENT_LIST_DIR}/../.." ABSOLUTE)
include("${WAVEQUAY_ROOT}/distribution/ConfigureWaveQuay.cmake")

# Instantiate the real appshell QML source selection without linking its audio engine.
# Native UI controls are replaced only at the unrelated styling boundary below.
function(muse_create_qml_module target)
    add_library(${target} STATIC "${PROJECT_SOURCE_DIR}/empty.cpp")
endfunction()
function(fixup_qml_module_dependencies target)
endfunction()
function(qt_add_qml_module target)
    qt_target_qml_sources(${target} ${ARGN})
endfunction()
function(qt_target_qml_sources target)
    cmake_parse_arguments(QML "" "URI;VERSION" "SOURCES;QML_FILES;RESOURCES;IMPORTS" ${ARGN})
    foreach(source IN LISTS QML_QML_FILES)
        get_filename_component(absolute "${source}" ABSOLUTE)
        get_source_file_property(alias "${source}" QT_RESOURCE_ALIAS)
        if(alias STREQUAL "NOTFOUND")
            set(alias "${source}")
        endif()
        if(alias MATCHES "(^|/)ExtensionsListView.qml$")
            get_property(selected GLOBAL PROPERTY EXTENSIONS_VIEW)
            if(selected)
                message(FATAL_ERROR "Multiple ExtensionsListView resources selected")
            endif()
            set_property(GLOBAL PROPERTY EXTENSIONS_VIEW "${absolute}")
            set_property(GLOBAL PROPERTY EXTENSIONS_ALIAS "${alias}")
        endif()
    endforeach()
endfunction()
# Avoid the unrelated platform-native app menu implementation in this fixture.
set(OS_IS_MAC ON)
add_subdirectory("${WAVEQUAY_ROOT}/src/appshell/qml/Audacity/AppShell" appshell-selection)
get_property(view GLOBAL PROPERTY EXTENSIONS_VIEW)
get_property(alias GLOBAL PROPERTY EXTENSIONS_ALIAS)
if(NOT view OR NOT alias STREQUAL "DevTools/Extensions/ExtensionsListView.qml")
    message(FATAL_ERROR "The selected developer view must keep its production QML resource alias")
endif()
file(WRITE "${CMAKE_CURRENT_BINARY_DIR}/selected-view.txt" "${view}\n")

add_executable(qml_module_probe qml_module_probe.cpp)
target_link_libraries(qml_module_probe PRIVATE Qt6::Core Qt6::Qml Qt6::Quick)
set_source_files_properties("${view}" PROPERTIES QT_RESOURCE_ALIAS "${alias}")
# The versioned Qt API is not intercepted: exercise its real resource alias and
# qmldir/type generation too, not a hand-written appshell module declaration.
qt6_add_qml_module(qml_module_probe URI Audacity.AppShell VERSION 1.0
    RESOURCE_PREFIX /qt/qml NO_CACHEGEN QML_FILES "${view}")

# The actual disabled extensions module supplies no native QML model. Its two
# production QML files are retained, with the same module/version registration.
set(stub "${WAVEQUAY_ROOT}/muse/framework/stubs/extensions/qml/Muse/Extensions")
file(WRITE "${CMAKE_CURRENT_BINARY_DIR}/qmldir" "module Muse.Extensions\nExtensionsListPanel 1.0 ExtensionsListPanel.qml\nExtensionsToolBar 1.0 ExtensionsToolBar.qml\n")
qt_add_resources(qml_module_probe extensions_stub PREFIX /qt/qml/Muse/Extensions
    BASE "${stub}" FILES "${stub}/ExtensionsListPanel.qml" "${stub}/ExtensionsToolBar.qml")
qt_add_resources(qml_module_probe extensions_directory PREFIX /qt/qml/Muse/Extensions
    BASE "${CMAKE_CURRENT_BINARY_DIR}" FILES "${CMAKE_CURRENT_BINARY_DIR}/qmldir")
qt_add_resources(qml_module_probe control_doubles PREFIX /qt/qml/Muse/UiComponents
    BASE "${CMAKE_CURRENT_SOURCE_DIR}/controls" FILES controls/qmldir
    controls/StyledListView.qml controls/ListItemBlank.qml controls/StyledTextLabel.qml)
