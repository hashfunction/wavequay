# WaveQuay local distribution

Status: source implementation, pending Windows build and runtime qualification.
No package is approved for redistribution by this document.

Configure a clean Windows checkout with:

```powershell
cmake -S . -B build -G Ninja -C buildscripts/ci/windows/wavequay-release.cmake -DMUSE_ENABLE_UNIT_TESTS=OFF -DAU_BUILD_EXPORT_TESTS=OFF
cmake --build build --target audacity
cmake --install build --prefix stage
python distribution/scan-package.py stage > package-scan.json
```

The Windows CMake target stays `audacity`; the distribution output is
`WaveQuay.exe`. Qt 6.11.2 is the root CI qualification baseline. The source is
C++17 (the approved plan's C++20 label did not match upstream CMake).

## Excluded integrations

`ConfigureWaveQuay.cmake` runs before dependency acquisition. It rejects explicit
conflicting cloud, analytics, update, extension, native crash-upload, ASIO and
service-key options. It forces the corresponding options off. Cloud, network,
update and extension composition uses the pinned upstream stubs. Local
crash/log diagnostics remain available; no Crashpad uploader is built.

WaveQuay omits cloud save/publish/sign-in routes and first-run account/usage
pages. It substitutes a local welcome card and independent About attribution.
The owned app QRC contains no update/learning feeds. The effects-marketplace
model, action and route are excluded; `au3-musehub` and `au3-network-manager`
are not built. Native Sentry uses its header-only disabled implementation.
Qt Network may remain a Qt dependency; absence of network activity still needs
runtime evidence. Merely disabling the Muse network module was insufficient
because AU3 previously included a separate Qt network backend.

`scan-package.py` inventories and hashes every staged regular file and rejects
known Audio.com authentication/API, MuseHub, MuseScore API, Sentry, Crashpad and
Audacity updater markers in UTF-8 and UTF-16. It rejects symbolic links and empty
stages. It is a supplemental check: compressed resource payloads and dynamically
assembled endpoints require composition review and Windows runtime observation.
No packaged scan or network trace has run locally.

## Native dependencies and source duties

Audacity, Muse and Muse dependencies remain at the qualified commits recorded
in `dependencies.spdx.json`. PortAudio uses the pinned upstream source checksum
and exact Windows patches copied into `distribution/recipes/portaudio`; the only
build change is explicit `PA_USE_ASIO=OFF`. The resolver's supported
`portaudio_resolve_override` selects that recipe, forcing a rebuild and avoiding
an unaudited ASIO-enabled prebuilt. No ASIO SDK is requested.

All other native dependency artifacts, codec decisions, VST3 SDK terms, source
archives, patches, notices and binary hashes require root release qualification.
FFmpeg is not bundled by this change; custom FFmpeg recipes are rejected because
the editor stores additional codec state outside the recipe contract. LAME and
other encoders use the existing pinned dependency graph and remain subject to
that audit. No paid plug-in is added. The SPDX document is a source inventory,
not an assertion that native binary license closure is complete.

## Recipe storage and export behavior

Recipes live in the app's Muse user-data directory as `export-recipes-v1.json`.
They contain a UUID, Unicode name, exact format identifier, process mode,
channel mode/count/mapping, sample rate, trim preference and typed encoder
parameters. They contain no audio, project path or destination path. Limits are
200 recipes and 2 MiB per store; invalid/future schema data is preserved and
blocks modifications until repaired or moved. A hashed recovery copy is made
where possible. Cross-window locking plus reload under the lock prevents stale
in-memory collections from losing other windows' saved recipes. `QSaveFile`
uses a sibling atomic commit with direct-write fallback disabled.

The export preferences model uses the tested `ExportRecipeController` to save
and apply. The live AU3 exporter describes settings using a private encoder
editor and never calls `Store()` during validation. Variant types and read-only
settings are checked before invoking typed setters; the completed descriptor
is checked for available choices, ranges, rates and channels before current
configuration changes. Applying never chooses a destination or invokes export.
Actual export passes an explicit `IExporter::Options` map through the existing
overwrite/progress/completion route. File overwrite behavior itself is inherited
and still needs Windows qualification.

The standalone tests exercise the production store/controller and descriptor
validation. They do not instantiate the full Muse QML context, real encoding,
or device/export cancellation. Those are release gates, not inferred results.
