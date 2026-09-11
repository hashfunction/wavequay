# SPDX-License-Identifier: GPL-3.0-only
# MuseScore-CLA-applies
#
# MuseScore
# Music Composition & Notation
#
# Copyright (C) 2021 MuseScore BVBA and others
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 3 as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

muse_create_module(appshell)

target_sources(appshell PRIVATE
    appshellmodule.cpp
    appshellmodule.h
    iappshellconfiguration.h
    iapplicationactioncontroller.h
    istartupscenario.h
    appshelltypes.h
    internal/applicationuiactions.cpp
    internal/applicationuiactions.h
    internal/appshellconfiguration.cpp
    internal/appshellconfiguration.h
    internal/applicationactioncontroller.cpp
    internal/applicationactioncontroller.h
    internal/framelesswindowcontroller.cpp
    internal/framelesswindowcontroller.h
    internal/startupscenario.cpp
    internal/startupscenario.h
    internal/isessionsmanager.h
    internal/sessionsmanager.cpp
    internal/sessionsmanager.h

    internal/splashscreen/splashscreen.cpp
    internal/splashscreen/splashscreen.h
    internal/splashscreen/loadingscreenview.cpp
    internal/splashscreen/loadingscreenview.h
    internal/splashscreen/newinstanceloadingscreenview.cpp
    internal/splashscreen/newinstanceloadingscreenview.h
)

if (OS_IS_MAC)
    target_sources(appshell PRIVATE
        internal/platform/macos/macosappmenumodelhook.mm
        internal/platform/macos/macosappmenumodelhook.h
    )

    set_source_files_properties(
        internal/platform/macos/macosappmenumodelhook.mm
        PROPERTIES
        SKIP_UNITY_BUILD_INCLUSION ON
        SKIP_PRECOMPILE_HEADERS ON
    )
endif(OS_IS_MAC)

if (OS_IS_WIN)
    target_sources(appshell PRIVATE
        internal/platform/win/winframelesswindowcontroller.cpp
        internal/platform/win/winframelesswindowcontroller.h
    )

    set(MODULE_LINK ${MODULE_LINK} dwmapi)
endif(OS_IS_WIN)

set(APPSHELL_COMMON_RESOURCES
    resources/Classic.svg
    resources/Colorful.svg
    resources/win_opengl_buglist.json
    resources/gpl-30.html
)
if(NOT AU_TRIEFLOW_DISTRIBUTION)
    list(APPEND APPSHELL_COMMON_RESOURCES
        resources/AboutBanner.png
        resources/LoadingScreen.svg
        resources/GoogleLogo.png
        resources/welcomedialog/YT_Release_Video_Thumb_v1.png
        resources/welcomedialog/Audacity_Feature_Survey.png
        resources/welcomedialog/Audacity_Merch_Store.png
        resources/welcomedialog/AudioDotCom_Dark.png
        resources/welcomedialog/AudioDotCom_Light.png
        resources/welcomedialog/MuseHubPromo.jpg
        resources/welcomedialog/Soap_Voice_Cleaner.png
    )
else()
    # Preserve the resource name used by the startup screen with our own art.
    set(WAVEQUAY_LOADING_ART "${PROJECT_SOURCE_DIR}/distribution/branding/wavequay.svg")
    set_source_files_properties(${WAVEQUAY_LOADING_ART} PROPERTIES QT_RESOURCE_ALIAS "resources/LoadingScreen.svg")
    list(APPEND APPSHELL_COMMON_RESOURCES ${WAVEQUAY_LOADING_ART})
endif()
qt_add_resources(appshell appshell_resources PREFIX / FILES ${APPSHELL_COMMON_RESOURCES})

target_link_libraries(appshell PRIVATE
    muse::ui
    muse::uicomponents
    muse::dockwindow
    Qt::Quick
    Qt::Svg
    Qt::Widgets
)

add_subdirectory(qml/Audacity/AppShell)

if (AU_BUILD_APPSHELL_TESTS)
    add_subdirectory(tests)
endif()
