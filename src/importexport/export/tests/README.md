# WaveWeft export recipe tests

The standalone CMake project builds two device-free GoogleTest executables:

- `exportrecipestore_tests`: production recipe validation, persistence and controller.
- `exportpreferencesmodel_recipe_tests`: the actual `ExportPreferencesModel`,
  `ExportConfiguration`, Muse settings and IoC, with a temporary recipe store and
  settings directory. The encoder, project/audio services, file-existence service
  and interactive dialogs are mocks. It creates only `QCoreApplication`.

Configure with C++17, Qt 6.10+ Core/Gui/Qml/Widgets and a GTest CONFIG package that
includes both `GTest::gtest_main` and `GTest::gmock`:

```sh
cmake -S src/importexport/export/tests -B build-recipe-tests -G Ninja
cmake --build build-recipe-tests
ctest --test-dir build-recipe-tests --output-on-failure
```

For split Homebrew Qt installations, add
`-DCMAKE_PREFIX_PATH=/opt/homebrew` and
`-DQt6Qml_DIR=/opt/homebrew/opt/qtdeclarative/lib/cmake/Qt6Qml`.
Windows qualification supplies its exact external GTest build and Qt installation.
The test host uses the exact utfcpp 4.1.1 archive/hash from the pinned Muse dependency
recipe, verifies the downloaded archive at configure time and records that hash,
the GTest package location/version and Qt version in
`build-recipe-tests/wavequay-test-dependencies.json`.

Model tests apply stored recipes without exporting, inspect one actual
`IExporter::exportData(path, options)` invocation, compare every recipe option and
typed encoder parameter, change live settings during overwrite confirmation,
exercise cancel/failure/completion behavior, and reject incompatible input maps.
The same production trim resolver and mapping filter called by `Au3Exporter` are
executed, including differing fallback settings and muted/selected row order.

These tests do not instantiate `Au3Exporter`, encode audio, operate a device,
create a GUI window or execute QML. Full native compilation, real WAV/compressed
output, mixed mute/solo/selection, consecutive custom/mono exports and installed
Windows interaction remain part of the Windows qualification matrix.
