# WaveWeft native-input and MSIX contract review

Base source: `3ad647abcf4433bcba36c2ce3231de70efb653ac`. This is the first reviewable chunk of the approved Store integration plan. It does not build, sign, install, upload or qualify a package, and does not claim source/license closure.

The actual prior Windows stage contained 512 files / 154,862,384 bytes, including 82 PE files. Existing stage hashes and downloaded-archive hashes do not independently establish every runtime member's source and notices. The new configure-time observer records only the pinned resolver's actual consumed dependency set, exact source URLs/hashes and resolved paths. It preserves the owned PortAudio recipe override; it does not invoke the all-platform source-prefetch target or change dependency resolution.

`native_sources.py` verifies current recipe signatures against the exact Windows x64 prebuilt lock, measures the retained archive/prefix/payload, and matches native files by leaf name and bytes/hash. It explicitly distinguishes a resolved-prefix match from proof of original archive membership. Unknown native owners and outstanding source/notice/publication checks are retained; `sourceLicenseClosure` is always false in this observational chunk. Original Qt metadata is inventoried separately. Native archive extraction/member comparison, Qt component mapping and complete source/notice delivery remain subsequent work.

`package.py` fixes the disposable qualification identity and the assigned Store identity independently. Store mode uses name `1659hashfunction.WaveQuay`, publisher `CN=B6A2631A-FD32-45CC-AE12-82466975F528`, family `1659hashfunction.WaveQuay_r3hxytd7jt6c4`, publisher display `hashfunction`, documented Application.Id `WaveQuay`, `bin/WaveWeft.exe`, x64/Desktop and version `1.0.1.0`. Exact manifest structure rejects additional capabilities/extensions or identity confusion. Package payload is regenerated from the current stage and source-owned WaveWeft artwork; container and unpacked validation compare the complete file set and bytes. Signing inputs, aliases, special files and redirected destinations are rejected. SDK invocation/receipts and installed lifecycle are deliberately not present yet.

The file/PNG/container primitives retain their Scriblark/ReticleQuay MIT provenance and both original license files. Current WaveWeft runtime sources, settings, UI driver, audio oracle and existing qualification workflow are unchanged.

Validation on macOS:

- Ten initial production-boundary cases failed before their implementation; they then passed. The CMake fixture executes the actual consumed-record function using current Flac, RapidJSON and owned PortAudio recipes; the current Flac signature/lock is checked, and an altered recipe is rejected.
- The full distribution suite passed 87 tests in 79.864 seconds, log `/private/tmp/waveweft-msix-contract-tests.log`.
- An additional redirected-destination regression first reproduced a write through the redirected parent. The destination ancestry check fixes that boundary; all six package-contract cases passed afterward. The unchanged native-source suite has five cases.
- `git diff --check` passes. No Windows package success is claimed. Root independent review precedes publication/integration of later chunks.
