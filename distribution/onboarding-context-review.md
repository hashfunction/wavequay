# WaveWeft settled onboarding-label verification

Prepared 2026-09-12 against source `0ce641e9275e13f4b59fefe80e32d499fe35bb6c` and Windows run [34685414179](https://github.com/hashfunction/wavequay/actions/runs/34685414179), public source `cea8c989103f0f7ab61a2e859b2ba42db0b70379`.

## Actual mismatch

The actual Clip visualization and workspace onboarding PNGs were viewed before editing. They show the expected second and third pages and native Next / Accept & continue buttons. The C# driver completed all three onboarding pages and two editor observations with owned PID 6076, no errors, survival until cleanup, and owned-job/process cleanup recorded. The Python verifier then rejected `Missing real accessible onboarding page`.

The first page already satisfies the plain `Select a theme. Next` Button contract. The other captured page-reading Buttons have exact names:

- `Clip visualization options panel, Clip visualization. Next`
- `Workspace layout options panel, What UI layout (workspace) do you want?. Accept & continue`

Their control type is Button, enabled true, offscreen false and process ID 6076. These are separate from the actual clicked plain `Next` and `Accept & continue` Buttons. Each native click has matching before/final ownership and geometry, exactly two inputs, the recorded cursor point, and the same native/foreground/hit-root HWND 131678.

This shape follows the existing source: `FirstLaunchSetupDialog.qml` starts a one-second accessibility timer; `ClipVisualizationPage.qml` and `WorkspaceLayoutPage.qml` set their navigation-panel names from their page models. `AccessibleItemInterface::text(Name)` prefixes the last focused item's name with its current panel name when panel information should be voiced. `GuiProbe.cs` recognizes the page before its 1.2-second settle wait and captures the subsequent tree. The independent verifier did not allow those two settled forms.

## Change and audit

Only the verifier's page-presence predicate gains the two exact names. Both still require an enabled, visible Button owned by the report PID. No arbitrary prefix/suffix matching, theme alias or plain action-button alias was introduced. Native click authorization still requires the original exact action name, matching input observations, PID/HWND/foreground/hit identity, complete button/window geometry, cursor location and two sent inputs.

The rest of `verify_gui_evidence.py` was read and replayed against the original report, stage inventory, display record and PNG files. With this isolated change, the untouched native evidence passes every existing predicate: source/executable/inventory/module binding, environment and initially absent profile state, exactly five ordered events, page order, PNG hashes/dimensions, all three native clicks, both meaningful editor trees, display restoration, survival and owned cleanup. It records 153 modules and editor observations at 12,298 and 55,271 ms, 42.973 seconds apart. No other current-receipt mismatch was found; no other acceptance predicate was changed.

The captured regression fixture retains nine exact tree nodes (native window, action button and page-reading button for each page), the actual input observations and timing, and original report SHA256 `50e8a29f025aafe2a6c8b118c0d123e76e56cebbbac792058844f1097c2d7d4d`. It was compared directly with the downloaded report. Unit tests put those real metadata rows into the explicitly synthetic policy harness; its fixture PNG is not represented as a Windows screenshot. The full native replay uses the original untouched images separately.

## Verification

- Before implementation, both the full original native receipt and captured-metadata regression fail with `Missing real accessible onboarding page`.
- After implementation, the full native replay passes with original public source `cea8c989103f0f7ab61a2e859b2ba42db0b70379`, original inventory, display and screenshot files.
- All 59 distribution tests pass, including actual Qt/Muse and C# observation fixtures. The GUI policy suite now has 31 tests, with 20 contextual-label mutations, two attempted substitutions of the page-reading node for the native clicked action, and 12 other report-gate mutations. Wrong page/panel/name/role/PID, hidden/disabled nodes, changed source/module/screenshot, partial events/input, shortened or unordered timing, startup errors, early exit and failed cleanup remain rejected.
- Both PowerShell native-input/display fixtures pass, including 21 input ownership/focus/geometry mutations and display test/apply/restore failure paths. Logs are `/private/tmp/waveweft-onboarding-input.log` and `/private/tmp/waveweft-onboarding-display.log`.
- `git diff --check` passes. Product, native observer/input, display, branding, dependencies, package and cleanup source are unchanged.

Reproduction from the source root:

```sh
WAVEQUAY_TEST_DOTNET=/Users/hashfunction/workspace/project_app_factory/microsoft-store/apps/filequay/source/.tools/dotnet-10.0.401/dotnet python3 -m unittest discover -s distribution/tests -p 'test_*.py' -v
python3 distribution/verify_gui_evidence.py --report /private/tmp/waveweft-34685414179-review/WaveWeft-Windows-qualification/build-evidence/gui/gui-observations.json --inventory /private/tmp/waveweft-34685414179-review/WaveWeft-Windows-qualification/build-evidence/stage-inventory.json --source-commit cea8c989103f0f7ab61a2e859b2ba42db0b70379
```

Logs: `/private/tmp/waveweft-onboarding-native-{red,green}.log`, `/private/tmp/waveweft-onboarding-tests-{red,green}.log` and `/private/tmp/waveweft-onboarding-all-python.log`.

This is local replay of a completed but failed CI run, not a new Windows run or a changed historical result. Independent review and a fresh exact-source pipeline remain pending. Evidence scope remains staged onboarding/editor startup, not full audio editing, project/export qualification, licensing closure or public release. No push, dispatch, Store, website or parent status edit was performed.
