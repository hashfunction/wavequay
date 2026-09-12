# WaveWeft Windows qualification matrix

All rows below remain **not run** at source handoff. Root CI and a Windows audio
host must add exact source/package hashes, build logs, Windows/driver versions,
results and failure evidence. A successful compiler run alone cannot pass these
runtime rows.

| Area | Required evidence |
| --- | --- |
| Build | Exact Audacity/Muse/dependency commits, Qt 6.11.2, MSVC, Ninja, offline flags, app and focused-test results |
| Native closure | Every installed binary's hash, license, corresponding source archive and patches; explicit codec/SDK decisions |
| Stage | Full file inventory, service-marker scan, expected `WaveWeft.exe`, resources, Qt platform/QML plug-ins |
| Startup | App-owned main window with no exception/error dialog; cloud, upload, updater and marketplace controls absent |
| Network | Offline launch/record/edit/export plus network observation; no upstream service requests |
| Devices | WASAPI/MME input/output, mono/stereo recording/playback, latency, unplug/reconnect, device errors |
| Projects | Multitrack editing, cleanup effects, local save/reopen, original project unchanged after recipe selection |
| Recipes | Unicode names, duplicate Update/Create choices, confirmed deletion, restart persistence, corrupt/future data handling, unavailable format/parameter |
| Export | Exact recipe options at the real exporter, WAV and audited compressed output validity, long export, cancel, inaccessible/Unicode paths |
| Overwrite | Existing-output cancel preserves bytes; explicit replace; errors and export completion reported correctly |
| Accessibility | Keyboard traversal, focus restoration, accessible names, high contrast and 100/150/200% display scaling |
| Package | MSIX identity/manifest/capabilities, install, launch, upgrade, uninstall and WACK |
| Release | GPL source and notices, canonical product/privacy/support pages, Store metadata and approved package |
