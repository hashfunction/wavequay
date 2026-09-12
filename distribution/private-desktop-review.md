# WaveWeft private Desktop repair

Candidate base: `37f573fef1affddcd623c58014d8503501542aeb`.
This changes the external qualification fixture only. No application, version,
preference namespace, native input predicate, audio oracle, module, lifecycle,
source-publication or Store/site state changed. No push or dispatch was made.

## Observed Windows cause

Actual run `34691748383`, public source
`1822f36aef96fc2941423f695b8d2098f1f1b8c9`, built/staged the product and passed
native recipe tests. Its original three onboarding and two stable editor
observations are retained at 4686, 6899, 9074, 10152 and 18515 milliseconds.
They belong to PID 5188 and the actual `WaveWeft 1.0.1` editor. The later consumer
failure prevents the pipeline from marking the complete GUI qualification passed.

The sole consumer input was the owned Ctrl+Shift+I import shortcut, with all six
native key events sent and its before/final foreground/native/UIA focus checks
passing. It opened native `Open`, HWND 131472, owned by PID 5188. Before filename
input, Windows displayed its child `Location is not available` HWND 66254:

`D:\a\wavequay\wavequay\build-evidence\gui\private-environment\Desktop is unavailable.`

The real `consumer-failure.png` was viewed. It shows that exact error over the
Open picker. `consumer-workflow.json.lastPicker.tree` independently records the
same text, the enabled error dialog and disabled `Open` root. The strict click
policy consequently rejected `Consumer target is not unique, visible and exact`
in `ConsumerSession.Picker`/`ClickElement`; it did not type a filename or click
through the unexpected dialog. This is a fixture-directory omission, not evidence
of a native ValuePattern, import, audio or save failure.

The producer in `GuiProbe.Run` redirects `USERPROFILE` to the private environment
but creates only that root, `Roaming`, `Local` and `Temp` before starting WaveWeft.
The original full stopped-process cleanup inventory confirms that `Desktop` is
absent. Documents/AppData descendants created during execution do exist. The
actual Windows message identifies which missing shell directory caused this run.
There is no need to infer another picker topology or relax ownership to proceed.

Evidence in `/private/tmp/waveweft-34691748383-review/WaveWeft-Windows-qualification/build-evidence/gui`:

| File | Bytes | SHA-256 |
| --- | ---: | --- |
| consumer-workflow.json | 94645 | ad4a3cb028c00ad4ac17d2ccb8f535b4730a191f04f5c480540b974626d670fa |
| consumer-failure.png | 25384 | 4122eb5b40b528fe94ae45f0c936dac81eb9e4fbc18e72a99156957ef9b7cb5d |
| consumer-validation.json | 9981 | d6e0bfbd8c0a1d043a950548185cf872b4544e441c3e004599a2fc3b9667275e |

The actual consumer ended after 1930ms with `completed=false` and no normal-close
exit code. Owned process/job stop and cleanup were proved; independent validation
remained false. Those historical receipts are unchanged.

## Narrow preparation change

After the existing six compatibility-profile/registry claims and private owner
marker succeed, the observer checks the private root's no-reparse ancestry and
calls the production `PrivateEnvironment.PrepareDesktop` helper. It validates the
exact existing 36-byte owner token, rejects redirected roots/markers and any
existing Desktop destination, then creates one empty `Desktop` child. It records
that exact path as `privateDesktop` before starting the product.

The helper creates no settings, shell registry state, media, shortcut or fake UI.
It accepts no alternate shell-folder destination. The environment variables,
product arguments, native Open selector/focus/hit/filename/readback checks,
remaining Reverse/save/recipe/export/reopen sequence and normal-close requirements
are unchanged. The original independent full-tree inventory and snapshot-checked
cleanup already cover this new child; no cleanup allowlist was widened.

The portable helper is a small separate compilation unit so its actual filesystem
behavior can run in fixtures without substituting a mock for the Windows UI
observer. Both the existing C# project and Windows PowerShell 5.1 source list
include it. Its fixture runs before the expensive native build in qualification.

## Regression and verification

- `test_private_environment.ps1` first failed because production Desktop
  preparation was absent. It recreates the existing four-directory setup,
  confirms Desktop is absent, then invokes the real new helper. It checks the
  empty Desktop, exact returned path, unchanged existing private bytes/marker,
  and five refusal cases: repeated preparation, absent/changed owner marker,
  existing file and existing directory, retaining their original bytes.
- The added Python case uses the actual `profile_inventory` and `remove_snapshot`
  functions. Desktop appears in the complete inventory. A later file addition
  rejects cleanup before any deletion; a fresh valid inventory removes only
  the claimed private tree and preserves the outside Desktop sibling.
- Full distribution suite: **77 tests passed**, 75.187s, including audio reversal,
  unchanged/partial/invalid output rejection, SQLite lifetime, normal-stop,
  recipe/profile cleanup, Qt/accessibility and original GUI evidence policies.
  Log: `/private/tmp/waveweft-desktop-python.log`.
- Five PowerShell production-helper fixture scripts passed: private environment,
  consumer input, text readback, onboarding input and display modes. All
  distribution PowerShell files parsed. Log:
  `/private/tmp/waveweft-desktop-powershell.log`.
- Full observer compiled as C# 5 against the existing locked .NET Framework 4.8
  references: **zero warnings, zero errors**, 1.38s. No dependency pin changed.
  Log: `/private/tmp/waveweft-desktop-net48.log`.
- `git diff --check` passed. The runtime was the existing read-only PowerShell
  7.6.6 at
  `/Users/hashfunction/workspace/project_app_factory/microsoft-store/apps/filequay/source/.tools/powershell-7.6.6/pwsh`.

These are macOS managed/filesystem/Qt fixtures and a reference-assembly compiler
check. They do not execute a Windows file picker or establish a successful
WaveWeft import, reverse, project save, recipe, audio export, reopen or normal
close. Root independent review and a fresh actual Windows run remain required.
