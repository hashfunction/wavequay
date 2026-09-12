# WaveWeft editor label observation — run 34683084553

Base source `fde4da563e0b15ed598ea6c952c0bb396a595998`, public snapshot
`c72e00d1e284f990a5b15468febf286650251023`. This is a two-label correction to
the native observer and its independent verifier, not an application/provider
change or evidence that the failed Windows run passed.

## Actual evidence and cause

The genuine failure screenshot was inspected before changing code. It shows
WaveWeft 1.0.1 with the complete empty editor, visible playback controls and Add
track button. The retained process was PID 1744, main HWND 131466. All three
onboarding pages and their exact owned native button clicks were recorded.
The observer then timed out at its unchanged 90-second limit, with no main-window
acceptance events and `survivedUntilCleanup=false`.

Unlike the preceding failure, `latest-ui-tree.json` now has 84 nodes, including
Muse editor controls. This confirms the ApplicationWindow provider correction
reached the actual Windows tree. The relevant enabled, onscreen, PID-1744 nodes
are:

| Accessible name | Windows UIA control type |
| --- | --- |
| Playback toolbar | Text |
| Add track | Text |
| Add track panel, Add track | Button |

`src/projectscene/qml/Audacity/ProjectScene/trackspanel/TracksTitleBar.qml`
assigns Add track to both the navigation panel and FlatButton. The pinned Muse
`muse/framework/accessibility/internal/accessibleiteminterface.cpp`, in
`AccessibleItemInterface::text(QAccessible::Name)`, prepends the translated
`<panel name> panel, ` when the item is the last focused control and the
controller needs to announce panel context. That source behavior explains the
exact observed button label. The plain Add track node in this snapshot is the
panel, not a Button. Requiring only the plain-name Button made both the C#
observer and Python verifier reject this genuine accessible editor.

Original evidence under
`/private/tmp/waveweft-34683084553-review/WaveWeft-Windows-qualification/build-evidence/gui`:

- `gui-observations.json`: `eba2cf744a503024e9d1d3c9f05c4bd5f47f41e10f03311309b984d1070e2a5a`
- `latest-ui-tree.json`: `fd991d3c7b2ea1cca0834f62fb17b4ab28c0fd5cd4c8c61519bbfc32ba9751be`
- `failure-window.png`: `93ef01000517ea28d82cfa2da596d48c3311f38a9fa8d9a7a120c7204a46c095`

The failed run recorded owned-job closure/process exit and restoration of the
original 1024x768 display after a tested, enumerated 1920x1080 mode. Its screenshot
is 1166x839 because the capture path restores the actual window before capturing;
these are real pixels, not a final marketing asset. No renamed project/audio
workflow or export is established by the empty-editor screenshot.

## Narrow correction

Both production predicates accept only `Add track` or
`Add track panel, Add track`, with the existing Button role, exact retained PID,
enabled and onscreen checks. There is no substring, suffix, case-insensitive,
plain Text-node or arbitrary-panel fallback. The visible Playback toolbar,
exact configured title, two observations separated by at least three seconds,
three real onboarding actions, source/executable/module hashes, retained process
lifetime, screenshot checks and owned cleanup remain mandatory and unchanged.
Application QML, providers, pinned Muse/dependencies, product/version/identity,
settings, input code, display code and lifecycle code are unchanged.

## Regression and verification

`test_editor_observation.py` compiles the actual C# Has method and exact editor
rejection expression read from GuiProbe.cs, using portable dictionaries with the
recorded roles/labels/PID. Before repair it failed specifically on the actual
contextual Button name; after repair both exact forms pass and 30 invalid
role/owner/visibility/name/missing-control variants fail. This does not emulate a
Windows application or qualify UIA itself.

The independent verifier adds a positive panel-Text/contextual-Button fixture
matching the observed shape and rejects wrong roles, hidden/disabled/foreign
controls and near-match labels. Its contextual positive failed with
`Missing meaningful editing controls` before repair. Both focused suites pass.
The unchanged actual failed native receipt was also passed to the repaired
verifier and still rejects with `Startup error or early exit`.

Final verification:

- `WAVEQUAY_TEST_DOTNET=<exact SDK> python3 -m unittest discover -s distribution/tests -v`: all 55 tests pass, including actual Qt/Muse/QML fixture builds and C# predicate/discovery replays.
- The complete production GuiProbe.csproj builds against its locked .NET Framework 4.8 reference package with zero warnings/errors. The first `--no-restore` attempt had no default intermediate assets and correctly reported missing reference assemblies; the normal locked restore into a fresh owned `/private/tmp/waveweft-editor-net48-obj/` then compiled successfully. No target/dependency change was made.
- Actual production onboarding input fixture passes its normal/negative-monitor cases and 21 ownership/focus/geometry mutations. Native display mode/scoping fixtures pass original-mode restoration, failed-test preservation, partial-apply recovery and failure-evidence retention.
- `git diff --check` passes; Muse and muse_deps submodule identities are unchanged.

The exact local SDK is `/Users/hashfunction/workspace/project_app_factory/microsoft-store/apps/filequay/source/.tools/dotnet-10.0.401/dotnet`; the PowerShell fixtures use the sibling `.tools/powershell-7.6.6/pwsh`. Full observer compile:

```sh
<exact SDK> build distribution/windows-gui/GuiProbe.csproj --configuration Release --nologo --verbosity quiet -p:RestoreLockedMode=true -p:BaseIntermediateOutputPath=/private/tmp/waveweft-editor-net48-obj/ -o /private/tmp/waveweft-editor-net48-bin
```

Local logs:
`/private/tmp/waveweft-editor-red.log`, `/private/tmp/waveweft-editor-policy-red.log`,
`/private/tmp/waveweft-editor-green.log`, `/private/tmp/waveweft-editor-policy-green.log`
`/private/tmp/waveweft-editor-distribution.log` and `/private/tmp/waveweft-editor-net48-restored.log`.

## Native qualification remains pending

Independent review and a fresh Windows run of the exact committed/public source
are required. Do not relabel run 34683084553 successful or use its failure image
as completed consumer/marketing evidence. This source change neither expands the
startup-only observer into a consumer workflow nor claims audio/project/export,
MSIX installation or Store acceptance. No public push, website, parent status or
Store edit was performed.
