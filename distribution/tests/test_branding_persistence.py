"""Run the actual Qt application-identity statements against a retained INI fixture."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class BrandingPersistenceTests(unittest.TestCase):
    def test_actual_windows_metadata_fragments_bind_name_executable_and_version(self):
        app = (ROOT / 'src/app/CMakeLists.txt').read_text()
        app_metadata = app[app.index('set(EXECUTABLE_NAME audacity)'):app.index('    if (CC_IS_MSVC)')] + '\nendif()\n'
        packaging = (ROOT / 'buildscripts/packaging/Windows/SetupWindowsPackaging.cmake').read_text()
        packaging = packaging[:packaging.index('# Wix-specific options')]
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory)
            (source / 'distribution').mkdir()
            for name in ('RecordWindowsRuntimes.cmake', 'RecordConsumedDependencies.cmake'):
                shutil.copyfile(ROOT / 'distribution' / name, source / 'distribution' / name)
            (source / 'app-metadata.cmake').write_text(app_metadata)
            (source / 'package-metadata.cmake').write_text(packaging)
            (source / 'CMakeLists.txt').write_text(
                'cmake_minimum_required(VERSION 3.24)\nproject(WindowsMetadata LANGUAGES C CXX)\n'
                f'set(MUSE_FRAMEWORK_SRC_PATH "{ROOT.as_posix()}/muse/framework")\n'
                f'list(APPEND CMAKE_MODULE_PATH "{ROOT.as_posix()}" '
                f'"{ROOT.as_posix()}/muse/buildscripts/cmake" "{ROOT.as_posix()}/muse/framework/cmake")\n'
                'include(SetupConfigure)\n'
                # Select the Windows metadata branch, without compiling or claiming Windows execution.
                'set(OS_IS_WIN TRUE)\n'
                f'set(CMAKE_CURRENT_SOURCE_DIR "{ROOT.as_posix()}/src/app")\n'
                f'include("{source.as_posix()}/app-metadata.cmake")\n'
                f'include("{source.as_posix()}/package-metadata.cmake")\n'
                'file(WRITE "${CMAKE_BINARY_DIR}/package.txt" "${CPACK_PACKAGE_NAME}\\n${CPACK_PACKAGE_VERSION}\\n${MUSE_EXECUTABLE_NAME}\\n${CPACK_PACKAGE_HOMEPAGE_URL}")\n')
            build = source / 'build'
            result = subprocess.run(['cmake', '-S', str(source), '-B', str(build), '-G', 'Ninja',
                '-C', str(ROOT / 'buildscripts/ci/windows/wavequay-release.cmake')],
                capture_output=True, text=True, timeout=90)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual((build / 'package.txt').read_text().splitlines(),
                             ['WaveWeft', '1.0.1.0', 'WaveWeft', 'https://waveweft.trieflow.com'])
            resource = (build / 'windows_version.rc').read_text()
            for field in ('FILEVERSION    1,0,1,0', 'PRODUCTVERSION 1,0,1,0',
                          '"CompanyName",      "Trieflow"', '"OriginalFilename", "WaveWeft.exe"',
                          '"InternalName",     "WaveWeft"', '"ProductName",      "WaveWeft 1.0.1"'):
                self.assertIn(field, resource)
            self.assertIn('1999-2026 Audacity and others', resource)

    def test_release_brand_keeps_existing_qt_settings_and_documents_namespace(self):
        main = (ROOT / 'src/app/main.cpp').read_text()
        # Extract unchanged production initialization, including its preprocessor
        # branches. The assertions below express the compatibility contract.
        name = main[main.index('    const char* appName;'):main.index('\n#ifdef Q_OS_WIN', main.index('    const char* appName;'))]
        start = main.index('    QCoreApplication::setApplicationName(appName);')
        end_marker = '    QCoreApplication::setApplicationVersion(MUSE_APP_VERSION);'
        identity = main[start:main.index(end_marker, start) + len(end_marker)]
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory)
            (source / 'probe.cpp').write_text('''
#include <QCoreApplication>
#include <QSettings>
#include <QTemporaryDir>
#include <QFile>
#include <iostream>
#include "muse_framework_config.h"
int main(int argc, char** argv) {
    QCoreApplication app(argc, argv);
    QTemporaryDir data;
    if (!data.isValid()) return 1;
    QSettings::setPath(QSettings::IniFormat, QSettings::UserScope, data.path());
    QCoreApplication::setOrganizationName("Trieflow");
    QCoreApplication::setApplicationName("Audacity4");
    QString path;
    QByteArray original;
    {
        QSettings existing(QSettings::IniFormat, QSettings::UserScope, "Trieflow", "Audacity4");
        existing.setValue("export/lastRecipe", "12345678-1234-4567-8123-123456789abc");
        existing.setValue("ui/theme", "dark");
        existing.sync();
        if (existing.status() != QSettings::NoError) return 2;
        path = existing.fileName();
        QFile file(path); if (!file.open(QIODevice::ReadOnly)) return 3;
        original = file.readAll();
    }
''' + name + '\n' + identity + '''
    if (QCoreApplication::applicationName() != "Audacity4" ||
        QCoreApplication::organizationName() != "Trieflow" ||
        QCoreApplication::organizationDomain() != "trieflow.com" ||
        QCoreApplication::applicationVersion() != "1.0.1") return 4;
    {
        QSettings reopened(QSettings::IniFormat, QSettings::UserScope,
            QCoreApplication::organizationName(), QCoreApplication::applicationName());
        if (reopened.fileName() != path ||
            reopened.value("export/lastRecipe").toString() != "12345678-1234-4567-8123-123456789abc" ||
            reopened.value("ui/theme").toString() != "dark") return 5;
    }
    QFile file(path); if (!file.open(QIODevice::ReadOnly) || file.readAll() != original) return 6;
    std::cout << "PASS: actual release identity reopens unchanged legacy settings\\n";
}
''')
            (source / 'CMakeLists.txt').write_text(
                'cmake_minimum_required(VERSION 3.24)\nproject(BrandPersistence LANGUAGES C CXX)\n'
                f'set(MUSE_FRAMEWORK_SRC_PATH "{ROOT.as_posix()}/muse/framework")\n'
                f'list(APPEND CMAKE_MODULE_PATH "{ROOT.as_posix()}" '
                f'"{ROOT.as_posix()}/muse/buildscripts/cmake" "{ROOT.as_posix()}/muse/framework/cmake")\n'
                'include(SetupConfigure)\nfind_package(Qt6 6.10 REQUIRED COMPONENTS Core)\n'
                'add_executable(brand_persistence probe.cpp)\n'
                'target_include_directories(brand_persistence PRIVATE "${CMAKE_BINARY_DIR}")\n'
                'target_compile_definitions(brand_persistence PRIVATE AU_TRIEFLOW_DISTRIBUTION)\n'
                'target_link_libraries(brand_persistence PRIVATE Qt6::Core)\n')
            build = source / 'build'
            for command in (
                ['cmake', '-S', str(source), '-B', str(build), '-G', 'Ninja',
                 '-C', str(ROOT / 'buildscripts/ci/windows/wavequay-release.cmake')],
                ['cmake', '--build', str(build), '--parallel', '2'],
            ):
                result = subprocess.run(command, capture_output=True, text=True, timeout=90)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            binary = next(path for path in (build / 'brand_persistence', build / 'brand_persistence.exe') if path.is_file())
            result = subprocess.run([str(binary)], capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn('actual release identity reopens unchanged legacy settings', result.stdout)
