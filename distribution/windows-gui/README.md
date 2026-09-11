# Staged Windows GUI qualification

This observer is a qualification tool, not part of the installed application.
It does not load Qt, use runner Qt tools, write preferences, import media, or
simulate successful product output. Actual GUI evidence remains pending until
`distribution/qualify-windows.ps1` passes on a disposable Windows CI desktop.

The qualifier runs the existing distribution tests and a real Windows helper
fixture (UI Automation activation and owned-process job cleanup) before the long
native build. After installation it inventories the stage, then runs:

```powershell
# PowerShell 7 on the disposable Windows runner, with CI=true.
$revision = (git rev-parse HEAD).Trim()
./distribution/invoke-windows-gui.ps1 -SourceCommit $revision
python distribution/verify_gui_evidence.py `
  --report build-evidence/gui/gui-observations.json `
  --inventory build-evidence/stage-inventory.json --source-commit $revision
```

The launcher uses the OS's x64 Windows PowerShell 5.1 and .NET Framework UI
Automation, Forms, Drawing and WindowsBase assemblies. It compiles the C# helper
with that host's compiler. An outer 180-second watchdog bounds stalled native
providers; the inner observation budget is 90 seconds. WaveQuay is placed in an
owned `KILL_ON_JOB_CLOSE` job before UI operations. The helper closes that job on
success/failure; timeout also kills only its exact helper process tree. No
process-name based global kill or preference cleanup is performed.

The target is exactly `stage/bin/WaveQuay.exe`, with no command-line arguments.
Its environment is cleared and rebuilt from an allowlist; PATH contains only
`stage/bin`, Windows/System32 and Windows. The working directory is stage/bin.
No inherited Qt/QML/compiler/plugin path, token, or build-tool directory is
passed. Every loaded module must be an inventoried, hash-matching stage file or
a Windows system file. Required Qt Core/Gui/Qml/Quick and qwindows.dll must all
come from the stage, even if an external Qt DLL sits under Windows. Reparse
points in runtime paths are rejected. This is runtime provenance checking, not
native licensing closure or network isolation.

Windows Qt uses known folders, so private APPDATA/LOCALAPPDATA/USERPROFILE/TEMP
environment directories alone **do not isolate Qt preferences**. This tool
requires an unused disposable runner profile and fails on existing relevant
known-folder paths. Current `src/app/main.cpp` still uses `Trieflow` plus
`Audacity4Development`/`Audacity4` for QCoreApplication settings identity; those
actual INI/data/Documents paths and prospective WaveQuay names are checked.
That legacy basename is an outstanding baseline branding/data-directory issue;
the qualification helper does not change the application or claim to fix it.
It never resets, injects, edits, copies into, or deletes settings to bypass
onboarding. Repeating qualification requires another fresh runner/profile.

Real onboarding must expose, in order, “Select a theme”, “Clip visualization”,
and “What UI layout (workspace) do you want?” in “Getting started”. The observer
uses UIA InvokePattern on Next, Next, and Accept & continue. When the source's
accessibility timer deliberately hides the active button, it permits Enter only
after verifying the exact focused UIA name “page title. button title” and the
owned foreground process. It does not use unverified coordinates, generic Enter,
private QML calls, test-only startup switches, or injected configuration.

Completion requires all three observed pages, genuine PNG captures, and two
“WaveQuay 4” editing-window observations at least three seconds apart. Both must
contain the visible enabled Playback toolbar and Add track button. Unexpected
modal/native/error dialogs and early process exit fail. Screenshots must be of
the owned foreground window, entirely on the visible desktop, at least 400x300,
and show pixel variation. The Python verifier independently checks page/action
order, source revision, module hashes/paths, environment, UI controls, image
hashes/dimensions, observation duration, and owned-process cleanup.

Artifacts preserve `gui-observations.json`, latest raw UI tree, page/main/failure
screenshots, target stdout/stderr (including Qt plugin diagnostics), helper
stdout/stderr, watchdog results and helper self-test evidence. The workflow
explicitly excludes stage binaries, helper binaries and private environment
contents. Failure leaves `windows_main_window_verified=false` while preserving
completed build/stage/test flags. Audio devices, native export, source/license
closure and submission remain false regardless of GUI outcome. Screenshots also
need human review; this check does not cover menu completeness, recipe editing,
audio, devices, high contrast, scaling, packaging, or Store qualification.

## Local development checks

```sh
python3 -m unittest discover -s distribution/tests -v
# Cross-compiles the observer against reference assemblies; cannot run Windows UI.
# .NET SDK 8.0.204 was used locally; references are pinned and hash-locked.
dotnet build distribution/windows-gui/GuiProbe.csproj --nologo \
  -p:RestoreLockedMode=true -p:BaseIntermediateOutputPath=/tmp/wavequay-gui-obj/ \
  -o /tmp/wavequay-gui-compile
```

`test_gui_evidence.py` uses explicitly synthetic observations and generated PNG
fixtures. Passing these is evidence about the fail-closed policy, never evidence
that WaveQuay displayed a window. The Windows helper self-test is similarly
reported separately from actual WaveQuay qualification.
