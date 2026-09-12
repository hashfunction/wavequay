# WaveWeft local audio workflow candidate

This extends the existing normal, unpackaged Windows consumer launch after its
three real onboarding pages and two verified editor observations. The preceding
native run 34687443314 tested source adc1ff6acf77d7bc39e0124af48826f059d87e59
and completed the original startup qualification. It did not run this new file
workflow. **The new driver is pending actual Windows execution.**

## Ordinary UI route

`ConsumerDriver.cs` is a separate part of the external Windows PowerShell 5.1
observer. It retains the original Process object, job and editor HWND. It loads
no product assemblies and calls no product API, command dispatcher or settings
writer. The product starts with its original empty argument list and onboarding.

1. Ctrl+Shift+I opens the source-defined native `Open` picker. Type the exact
   marker-owned `Dawn-thread.wav`, read the native filename back, and confirm.
   Observe and click the real `Clip: Dawn-thread` control.
2. Ctrl+A selects audio. The ordinary Effect menu → Special → Reverse route
   invokes the noninteractive built-in Reverse effect. Capture the visible edit.
3. Ctrl+S opens Save project; select `On your computer` when the local/cloud
   choice appears. Save the real `Dawn-thread.aup4` through the owned native
   picker. Capture the saved editor.
4. Ctrl+Shift+E opens Export audio. Check the fresh WAV format and 44100 Hz rate,
   select Signed 16-bit PCM and Stereo, and edit the ordinary File name/Folder
   controls. Save the named `Dawn thread stereo` export recipe through its dialog.
5. Select Mono and observe the actual selected-state property. Select the saved
   recipe and observe Stereo restored. Capture both saved/applied recipe stages.
6. Export `reversed.wav`. Close the project with Ctrl+W and require the normal
   home-window title before Ctrl+O reopens the saved project. Observe its clip,
   apply the saved recipe again, and export `reopened.wav`.
7. Alt+F4 requests normal close. Require the retained process to exit 0 and the
   native job accounting to reach zero active processes before profile reads.

Routes come from `src/app/configs/data/shortcuts.xml`,
`src/project/internal/projectactionscontroller.cpp`,
`src/project/internal/opensaveprojectscenario.cpp`,
`src/project/qml/Audacity/Project/AskLocationTypeDialog.qml`,
`src/projectscene/qml/Audacity/ProjectScene/tracksitemsview/ClipItem.qml`,
`src/effects/builtin_collection/reverse/reverseeffect.h` and `.cpp`,
`src/importexport/export/qml/Export/ExportDialog.qml` and
`SaveExportRecipeDialog.qml`. Menu/dropdown roles and keyboard navigation come
from the pinned Muse `StyledMenuItem.qml`, `StyledDropdownView.qml`,
`ListItemBlank.qml` and `TextInputField.qml`.

## Evidence boundaries

Every click rechecks the unique exact role/name, retained PID, native owner
chain, foreground HWND, point hit HWND/PID, full visible geometry and runtime
identity immediately before SendInput. Keyboard input independently rechecks
native thread focus, foreground, UIA focus PID/identity and the expected field's
ancestry. The source-defined dropdowns do not activate their native popup;
normal bounded arrow navigation and exact focused item + Enter preserve the
parent's native focus instead of relaxing mouse hit-window equality.

The first consumer run has no existing Windows evidence for its picker, menu,
clip, text-readback or radio-state topology. Unknown labels/roles, duplicate
controls, inaccessible fields, changed windows, partial input, or unproved
filename topology stop with real trees and an unedited failure screenshot.
This is a fail-closed candidate, not a claim that the complete route has run.
The native picker policy recognizes the exact writable Edit 1148 → ComboBox 1148
→ ComboBoxEx32 1148 chain, or Edit 1001 → ComboBox 0 → FloatNotifySink 0 →
DirectUIHWND 0 → DUIViewWndClassName 0, ending at the same owned `#32770`.
Both are observed Windows file-picker chains from Tint run 34681764386;
neither is represented as WaveWeft evidence. Direct Edit 1148 is rejected.
The observer retains bounded native Edit ancestry/IDs/PIDs before input. Additional
topologies require actual evidence and review; the helper does not guess IDs.

The original 90-second onboarding/editor deadline, exact five-event verifier,
module hashes and source checks are retained. The consumer driver has its own
420-second total budget; the outer observer allows 600 seconds for both phases
plus diagnostics/cleanup. Screenshot and metadata artifacts use the existing
top-level GUI globs. Audio, project and profile payloads are excluded.
The original startup module observation is retained separately; the same
strict stage verifier also checks every module observed after file export.

`consumer_audio.py` independently checks both WAV outputs as 44100 Hz, stereo,
signed 16-bit PCM, exactly 264600 frames/six seconds. Every output frame must match
the reversed generated original, allowing at most 4 LSB and a mean 1.5 LSB for
float-to-PCM dithering. Silence, clipping, shifted/partial/unchanged audio,
channel swaps and rate changes fail. The project is inspected read-only as
SQLite with AUDY application ID, an intact document and audio sample blocks.
Reopening and exporting it through the UI supplies the persistence check.
The recipe JSON is read only after proven normal exit and must contain exactly
the named WAV/stereo/44100/PCM16 recipe, with no media or destination fields.

The fixture's six-second stereo composition is original Trieflow material
dedicated to CC0. `protected.txt` and the input WAV are SHA256-protected. The
fixture path and outputs are exclusively created; existing trees are refused.

## Fresh profile and cleanup

Qt's applicationName remains Audacity4/Audacity4Development and organization
Trieflow for compatibility. Environment redirection alone does not prove
Windows known-folder/registry isolation. The helper first rejects every
existing compatibility profile candidate, then exclusively creates and marks
the six actual Local/Roaming/Documents roots and its private environment. It
also refuses existing HKCU `Software\\Trieflow\\Audacity4*` keys and exclusively
claims the two exact new keys with an ownership-only marker value. It writes
no preference values. No existing profile or registry key is adopted.

After application logs are retained and all job processes are proved stopped,
the independent finalizer binds profile roots back to native Windows known
folders, checks every owner marker, and inventories bounded file/registry
metadata. It checks the complete snapshots again before cleanup and each file
immediately before deletion. Unexpected fixture names, modified protected
bytes, redirects, changed snapshots, foreign roots/registry keys or missing
markers refuse cleanup and leave the qualification failed. It removes only
claimed leaves; shared parent directories/registry keys remain intact.

## Local validation and remaining work

The production scalar mouse and keyboard guards have positive fixtures and
40 negative ownership/focus/geometry mutations. Independent audio, project,
recipe, fresh-root and cleanup fixtures exercise the actual Python validator.
The original distribution test suite and observer compilation against .NET
Framework 4.8 are retained. Fixture tests are explicitly not native product
qualification or marketing screenshots.

Local validation receipt, September 12, 2026:

- Full distribution suite: 69 tests passed (including the first 10 audio-policy
  fixtures); log `/private/tmp/waveweft-consumer-python-tests.log`.
- Final focused Python policy suite: 16 tests passed; log
  `/private/tmp/waveweft-consumer-focused.log`.
- Actual scalar consumer policy: one positive mouse/keyboard case each and
  40 negative mutations passed. Original onboarding policy also passed.
- Complete C# 5 observer build: zero warnings/errors against cached .NET
  Framework 4.8 reference assemblies; log
  `/private/tmp/waveweft-consumer-net48.log`. This checks compilation only;
  the next Windows run executes the real native job/input self-test.

Reproduce focused checks from the repository root:

```sh
python3 -m unittest discover -s distribution/tests -p test_consumer_audio.py -v
pwsh -NoLogo -NoProfile -File distribution/windows-gui/test_consumer_input.ps1
pwsh -NoLogo -NoProfile -File distribution/windows-gui/test_onboarding_input.ps1
```

The local compiler used the existing cached reference nupkg
SHA256 `8a7e348538e7eb91351696911689f49e3d4f63f8bab517432bbe159b8b1104a2`,
with `TargetFrameworkRootPath` and `FrameworkPathOverride` pointing at the
disposable `/private/tmp/waveweft-consumer-reference/build/` extraction.
No dependency lock or product build input was changed or represented as
newly restored. Windows uses its installed Framework reference assemblies
through the existing PowerShell 5.1 Add-Type entry point.

## Cross-process text-readback review correction

Review of 9ed20576 found that the filename Edit readback used GetWindowText,
which does not read another application's Edit contents. Microsoft directs
callers to send WM_GETTEXT for that case.
See [GetWindowTextW documentation](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-getwindowtextw).

The corrected native adapter sends only WM_GETTEXT through
SendMessageTimeoutW: exact retained control HWND, 4096 UTF-16 code-unit buffer,
SMTO_BLOCK | SMTO_ABORTIFHUNG | SMTO_ERRORONEXIT, at most 500ms per native query,
with the remaining convergence deadline limiting the last query. A failed or
timed-out query fails immediately. Successful reads may converge for at most
five seconds/101 observations after the single original SendInput sequence.
Native owner/filename topology and exact native/UIA focus are revalidated on
both sides of each read. The same read-only convergence policy wraps ordinary
UIA ValuePattern/TextPattern field and recipe-name reads. It has no input
delegate and cannot replay typing. Query packets, copied counts, observed
values and before/after ownership snapshots are retained in `textReadbacks`.
The API packet and result semantics follow
[SendMessageTimeoutW](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-sendmessagetimeoutw)
and [WM_GETTEXT](https://learn.microsoft.com/en-us/windows/win32/winmsg/wm-gettext).

Managed seam regressions check the exact native packet, Unicode and delayed
native/UIA convergence, failed/native-timeout queries, copied-count mismatch,
truncation, forbidden broadcast, changed ownership before/after a read,
provider exceptions, deadline exhaustion, late results and a stalled clock.
The actual scalar filename policy accepts the two recorded legacy/modern
chains and rejects 40 per-node mutations, two missing ancestors and direct 1148.
These run before the product build in Windows qualification:

```sh
pwsh -NoLogo -NoProfile -File distribution/windows-gui/test_consumer_text_readback.ps1
pwsh -NoLogo -NoProfile -File distribution/windows-gui/test_consumer_input.ps1
```

The complete C# 5/.NET Framework 4.8 observer rebuild passed after this correction
with zero warnings and zero errors. The focused text-readback and scalar input
suites also passed. The convergence deadline rejects late UIA results; the
existing synchronous UIA provider calls and ownership queries are still subject
to the outer observer process deadline.
No Windows consumer run or picker success is claimed by these managed tests.

Root must review this candidate and dispatch Windows. Read
`consumer-workflow.json`, `consumer-validation.json`, the nine real stage
screenshots, any failure tree, and original `gui-observations.json`. Only a
fully successful independent finalizer sets
`windows_local_file_workflow_verified`. Recording/playback hardware tests,
broader export matrix, installed MSIX qualification, corresponding-source
closure and Store readiness remain separate and unclaimed.
