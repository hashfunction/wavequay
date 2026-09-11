muse_create_qml_module(appshell_qml FOR appshell)

set(APPSHELL_EXTENSIONS_VIEW DevTools/Extensions/ExtensionsListView.qml)
if(NOT MUSE_MODULE_EXTENSIONS)
    # The framework stub does not register DevExtensionsListModel. Even a hidden
    # DevTools page is resolved while the main window's QML is loaded.
    set(APPSHELL_EXTENSIONS_VIEW DevTools/Extensions/stubs/ExtensionsListView.qml)
    set_source_files_properties(${APPSHELL_EXTENSIONS_VIEW} PROPERTIES
        QT_RESOURCE_ALIAS "DevTools/Extensions/ExtensionsListView.qml")
endif()

qt_add_qml_module(appshell_qml
    URI Audacity.AppShell
    VERSION 1.0
    SOURCES
        aboutmodel.cpp
        aboutmodel.h
        appmenumodel.cpp
        appmenumodel.h
        DevTools/Settings/settingslistmodel.cpp
        DevTools/Settings/settingslistmodel.h
        DevTools/Table/tabletestsmodel.cpp
        DevTools/Table/tabletestsmodel.h
        FirstLaunchSetup/clipvisualizationpagemodel.cpp
        FirstLaunchSetup/clipvisualizationpagemodel.h
        FirstLaunchSetup/firstlaunchsetupmodel.cpp
        FirstLaunchSetup/firstlaunchsetupmodel.h
        FirstLaunchSetup/themespagemodel.cpp
        FirstLaunchSetup/themespagemodel.h
        FirstLaunchSetup/workspacelayoutpagemodel.cpp
        FirstLaunchSetup/workspacelayoutpagemodel.h
        FirstLaunchSetup/signinaudiocompagemodel.cpp
        FirstLaunchSetup/signinaudiocompagemodel.h
        FirstLaunchSetup/appupdateusageinfopagemodel.cpp
        FirstLaunchSetup/appupdateusageinfopagemodel.h
        framelesswindowmodel.cpp
        framelesswindowmodel.h
        maintoolbarmodel.cpp
        maintoolbarmodel.h
        mainwindowtitleprovider.cpp
        mainwindowtitleprovider.h
        projectpagemodel.cpp
        projectpagemodel.h
        PublishPage/publishtoolbarmodel.cpp
        PublishPage/publishtoolbarmodel.h
        windowdroparea.cpp
        windowdroparea.h
        welcomedialogmodel.cpp
        welcomedialogmodel.h
    QML_FILES
        AboutDialog.qml
        AboutDialogAudacityTab.qml
        AboutDialogPrivacyTab.qml
        AlphaWelcomePopup.qml
        AppWindow.qml
        DevTools/CrashHandler/CrashHandlerDevTools.qml
        DevTools/DevToolsMenu.qml
        DevTools/DevToolsPage.qml
        ${APPSHELL_EXTENSIONS_VIEW}
        DevTools/Gallery/GeneralComponentsGallery.qml
        DevTools/Interactive/InteractiveTests.qml
        DevTools/Interactive/SampleDialog.qml
        DevTools/KeyNav/KeyNavExample.qml
        DevTools/KeyNav/KeyNavSection.qml
        DevTools/KeyNav/KeyNavSubSection.qml
        DevTools/Preferences/SettingsPage.qml
        DevTools/Table/TableTests.qml
        FirstLaunchSetup/ClipVisualizationPage.qml
        FirstLaunchSetup/DoublePage.qml
        FirstLaunchSetup/FirstLaunchSetupDialog.qml
        FirstLaunchSetup/Page.qml
        FirstLaunchSetup/PlaybackPage.qml
        FirstLaunchSetup/ThemesPage.qml
        FirstLaunchSetup/TutorialsPage.qml
        FirstLaunchSetup/UnderConstructionPage.qml
        FirstLaunchSetup/WorkspaceLayoutPage.qml
        HomePage/CloudItem.qml
        HomePage/HomeMenu.qml
        HomePage/HomePage.qml
        HomePage/PluginsPage.qml
        Main.qml
        Main.wasm.qml
        MainToolBar.qml
        platform/AppButtonBackground.qml
        platform/AppMenuBar.qml
        platform/PlatformMenuBar.qml
        ProjectPage/ProjectPage.qml
        ProjectPage/ProjectStatusBar.qml
        PublishPage/PublishPage.qml
        PublishPage/PublishToolBar.qml
        shared/AccentColorsList.qml
        shared/ThemeSamplesList.qml
        shared/internal/ThemeSample.qml
        WelcomeDialog.qml
        WindowContent.qml
    RESOURCES
        FirstLaunchSetup/resources/ClipVisuals_ClassicClips.png
        FirstLaunchSetup/resources/ClipVisuals_ColorfulClips.png
        FirstLaunchSetup/resources/MuseSounds.png
        FirstLaunchSetup/resources/UnderConstruction.png
        FirstLaunchSetup/resources/VideoTutorials.png
    IMPORTS
        TARGET muse_ui_qml
        TARGET muse_uicomponents_qml
        TARGET muse_cloud_qml
        TARGET muse_dockwindow_qml
        TARGET muse_diagnostics_qml
        TARGET muse_extensions_qml
        TARGET muse_learn_qml
        TARGET muse_shortcuts_qml
        TARGET muse_toast_qml
        TARGET muse_tours_qml
)

if(NOT AU_TRIEFLOW_DISTRIBUTION)
    qt_target_qml_sources(appshell_qml QML_FILES
        FirstLaunchSetup/SigninAudiocomPage.qml
        FirstLaunchSetup/AppUpdatesAndUsageInfoPage.qml
        SigninAudiocomDialog.qml)
endif()

if (AU_BUILD_CLOUD_AUDIOCOM)
    qt_target_qml_sources(appshell_qml
        QML_FILES
            HomePage/AccountPage.qml
    )
endif()

if (OS_IS_MAC)
    qt_target_qml_sources(appshell_qml
        QML_FILES
            platform/mac/Main.qml
    )
elseif(OS_IS_WIN)
    qt_target_qml_sources(appshell_qml
        QML_FILES
            platform/win/AppSystemButtons.qml
            platform/win/AppTitleBar.qml
            platform/win/Main.qml
    )
elseif(OS_IS_LIN OR OS_IS_FREEBSD)
    qt_target_qml_sources(appshell_qml
        QML_FILES
            platform/linux/Main.qml
    )
else()
    message(FATAL_ERROR "Unsupported OS")
endif()

if (NOT OS_IS_MAC)
    target_sources(appshell_qml PRIVATE
        navigableappmenumodel.cpp
        navigableappmenumodel.h
    )

    # we use QKeyMapper to fix https://github.com/musescore/MuseScore/issues/10181
    find_package(Qt6 REQUIRED COMPONENTS GuiPrivate)
    target_link_libraries(appshell_qml PRIVATE Qt6::GuiPrivate)
endif(NOT OS_IS_MAC)

target_link_libraries(appshell_qml PRIVATE Qt::Widgets)

fixup_qml_module_dependencies(appshell_qml)

# Necessary for the auto-generated sources
target_include_directories(appshell_qml PRIVATE
    DevTools/Settings
    DevTools/Table
    FirstLaunchSetup
    PublishPage
)
