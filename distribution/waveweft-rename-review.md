# WaveWeft 1.0.1 source rename review

Base: `656e6cd9df0c54455612989a5bd0602f4e3c1029`, including the separately
reviewed ApplicationWindow accessibility repair. This commit changes branding
and its exact qualification expectations. A fresh Windows build and observed
editor are pending; no renamed screenshots or Store qualification are claimed.

## Production changes

The distribution now identifies as WaveWeft 1.0.1, emits `WaveWeft.exe`, and
uses the exact configured main title `WaveWeft 1.0.1`. Both the native observer
and independent evidence verifier require the new executable/title while
retaining source, inventory/module hashes, ownership, input, visible controls,
screenshot, survival and cleanup requirements. The qualification workflow and
its metadata artifact are named `WaveWeft Windows qualification` and
`WaveWeft-Windows-qualification`; the branch and source paths remain stable.

Welcome/About text, export-recipe errors, diagnostic labels, app resources,
current documentation and product/privacy/support/source links use WaveWeft and
`https://waveweft.trieflow.com`. Original logo geometry/PNG/ICO bytes are preserved
under renamed resource filenames. Windows PE metadata uses the actual output
basename (fixing the former appended-major OriginalFilename mismatch), version
1.0.1.0 and Trieflow company attribution while retaining Audacity copyright.
Existing CPack metadata selects WaveWeft, the same version, executable and icon.

This source has no MSIX manifest or packager. Parent-owned Store packaging must
retain Identity `1659hashfunction.WaveQuay`, its assigned publisher and
ApplicationId `WaveQuay`, and set the new display name/version separately.
No parent packaging, public site, source publication or Store action was taken.

## Compatibility and immutable records

`src/app/main.cpp` is byte-for-byte unchanged: the release application continues
using the `Trieflow` / `Audacity4` settings and document namespace, and the
unstable namespace remains `Audacity4Development`. Existing GUI identifier
`com.trieflow.WaveQuay`, internal CMake/QML/C#/diagnostic environment names,
recipe schema/storage basename, project formats and upstream attributions remain.
The GUI preflight retains every former protected profile root and adds exact
prospective WaveWeft roots; bounded diagnostic collection accepts renamed logs
alongside old logs only in its existing owned/fresh-root policy.

The source inventory `dependencies.spdx.json` is the unchanged dated historical
record, including its original namespace and source pins. Historical GUI run
notes and `editor-accessibility-review.md` retain their actual old names, hashes
and screenshots. Muse `3c5512eb8ee1a863a6123e62bd75a6ab55045752`, muse_deps
`b915e6703a2a9839b2a98d4ca2468a88e361929f`, source archives, dependency recipes,
license files and upstream original README text are unchanged.

## Verification

- Added actual complete release-CMake brand/version/title checks and negative
  old-title/old-executable cases: both new tests failed against the base; all
  25 GUI evidence tests then passed. Logs `/private/tmp/waveweft-rename-red.log`
  and `/private/tmp/waveweft-rename-green.log`.
- New Qt Core fixture compiles the exact unchanged main.cpp identity statements
  with actual release configuration, reopens a seeded legacy INI recipe/theme
  fixture and verifies its path, values and bytes remain unchanged. A second
  fixture evaluates the actual Windows application/packaging CMake metadata
  fragments and generated RC. Both passed; these are local configuration and
  persistence checks, not native Windows execution.
- Full `python3 -m unittest discover -s distribution/tests -v`: **52 tests pass**,
  including the real Qt/Muse ApplicationWindow and onboarding provider cases,
  compiled C# discovery replay, QML routing/modules, diagnostics and all policy
  mutations. Log `/private/tmp/waveweft-rename-distribution.log`.
- Actual native recipe tests: **3/3 CTest entries pass**: 13 store/controller tests,
  11 model/options tests, and the 11-case model lifecycle suite repeated 20 times.
  Log `/private/tmp/waveweft-rename-recipes.log`.
- Existing actual PowerShell onboarding guard passes positive/negative-monitor
  and 21 mutation cases. Display tests pass supported-mode selection, native
  structure/flags, test-before-apply, dynamic change, original-mode restoration,
  partial-apply and restoration-failure checks. Changed scripts parse cleanly.
- Full .NET Framework observer cross-compiles with locked references: zero
  warnings/errors. Log `/private/tmp/waveweft-rename-observer.log`.
- `git diff --check` passes. All QRC file targets resolve. Direct byte comparison
  confirms unchanged original artwork, license, submodule records, actual app
  identity initialization, accessibility fix and qualification lifecycle script.

Local tools: Qt 6.11.2/Homebrew CMake; Python 3.10; .NET SDK 10.0.401 and PowerShell
7.6.6 at the sibling FileQuay source `.tools` paths. Native test build directories
were owned temporary directories and were removed on completion. No full product
build or large download was attempted locally.

Fresh Windows remains necessary for the final branded binary/PE resource,
ApplicationWindow provider, actual onboarding/stable editor and genuine screen
captures. Audio/export, source-license closure, MSIX and Store gates remain open.
