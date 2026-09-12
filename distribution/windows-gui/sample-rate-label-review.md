# Exact Windows sample-rate label and remaining consumer selectors

Run **34723127574**, public source `02a8dbae9d0937bb535b33502502729734de97cb`,
artifact **10308015874**, completed the native build and staged import, Reverse,
and AUP4 save. The previous `Signed 16-bit PCM` choice succeeded. The first
failure is the existing 10-second exact-control lookup for `Format: 44100` at
`configure-wav-recipe`. Neither installed lifecycle nor unsigned export was reached.

The original complete Export audio tree and failure screenshot show
`Format: 44100 Hz`, a visible enabled ComboBox owned by PID 3544, Export HWND
786932. `fixtures/export-settings-34723127574.json` retains the original
interactive control rows without changing their names, roles, states or bounds.
The full original `consumer-workflow.json` SHA256 is
`bbef133026c6d994f2db37130f40a0f25012a95184306aa713036b2789dd7e2a`.

`ExportPreferencesModel::exportSampleRateList()` in
`src/importexport/export/view/exportpreferencesmodel.cpp` explicitly appends
` Hz` to each standard rate. `ExportDialog.qml` uses
`formatLabel.text + ": " + currentText` for this dropdown. The observer now
requires exactly `Format: 44100 Hz`. Product behavior, ownership, input,
selection, readback, audio and lifecycle acceptance are unchanged.

## Remaining label and value audit

The following audit covers every remaining named control/window and supplied
value in `ConsumerSession::Run`, `Settings`, `Choose`, `Field`, `ExportNew`,
`ExportDialog` and `WaitClosedProject`. Rows marked source-only were not reached
in this run and are not reported as native success.

| Selector or value | Original observation and exact source basis |
| --- | --- |
| `Export audio` Window | Original complete owned window. `ExportDialog.qml` title and completion handler retain this dialog until export succeeds. |
| `Format: WAV (Microsoft)` ComboBox | Exact original row; format dropdown uses format label plus current text. |
| `Encoding ` prefix and `Signed 16-bit PCM` ListItem | Current original row is `Encoding Signed 16-bit PCM`; this run accepted the exact encoding. Earlier original encoding-options fixture retains the real popup items. |
| `Format: 44100 Hz` ComboBox | Exact original row and model suffix, corrected here. Other rates/units remain refused. |
| `Stereo` / `Mono` RadioButton | Both exact original rows are enabled and visible. `ExportDialog.qml` binds each to its corresponding channel enum and `RoundedRadioButton.qml` exposes that text and checked state. Actual post-click and post-recipe selection proof remains required. |
| `Folder: ` Edit; exclusive fixture directory | Exact original row uses that prefix. `dirField` names itself with folder label/current text; editing-finished calls `setFilePickerPath`, which treats the existing owned fixture as a directory. `Field` retains exact text readback and Tab to finish editing. |
| `File name: ` Edit; `reversed`, later `reopened` | Original `File name: Dawn-thread` row confirms prefix/role. QML calls `setFilename` on text change; model retains the supplied base name. `exportData` adds the chosen format extension only when absent, yielding the required `reversed.wav` and `reopened.wav`. Both must be new owned files and pass original independent byte oracles. |
| `Save recipe` Button on Export dialog | Exact original enabled row; its handler refreshes recipes and opens `SaveExportRecipeDialog.qml`. |
| `Save export recipe` Window; `Recipe name` Edit | Source-only next dialog: those exact QML title/accessibility literals are present. `TextInputField.qml` exposes EditableText and actual input text separately from its name. No runtime dialog success is inferred. |
| `Dawn thread stereo`; dialog `Save recipe` Button | Source-only: controller trims the supplied name, which has no leading/trailing whitespace; model returns stored name unchanged. The save button has this exact label when no duplicate exists. The exclusive prepared profile and new name retain the no-duplicate path; duplicate/update UI is not bypassed. |
| `Spoken-audio export recipe` ComboBox; `Dawn thread stereo` ListItem | Exact original ComboBox name is fixed independently of its selected text. QML uses recipe model `name` role; `refreshRecipes` preserves stored name. `StyledDropdownView.qml` exposes that text through ListItemBlank's ListItem role. Applying dispatches directly to `applyRecipe(id)`; there is no separate apply-dialog selector. `applyValidated` restores saved channel/rate/encoder settings. Actual Mono-before/Stereo-after assertions remain mandatory. |
| `Export` Button | Exact original row. Its normal handler verifies settings, applies them and exports. Successful `exportCompleted` accepts the Export dialog; unknown error/overwrite dialogs cannot satisfy the remaining producer gates. |
| Home title `WaveWeft 1.0.1`, reopened project titles | `mainwindowtitleprovider.cpp` returns app display name with no project and `%1 %2 - %3` with project title/modified marker. Original saved title is `Dawn-thread  - WaveWeft 1.0.1`, including two spaces. Existing selectors already match those rules. |
| Native `Open`, `Dawn-thread.aup4`; `Clip: Dawn-thread` Button | The original import/save already exercised exact native-picker ownership/readback and the clip name. Reopen retains the same saved file and clip identifier; no alternate picker or title route was added. |

No other literal discrepancy was found. Future modal focus, actual recipe
persistence/application, both audio exports and normal close remain unproved
until a fresh full Windows run.

## Focused verification

The existing `test_consumer_encoding.ps1` now extracts and executes production
`Match` as well as `Settings`, `Choose` and `FocusedChoice`, with only native
leaves doubled. Original UIA PIDs are explicitly mapped to the replay process;
original names, roles, enabled/offscreen states are retained. It first failed
against the unchanged producer with `Exact observed control absent or ambiguous:
Format: 44100`, then passed after the literal correction. It retains the three
nonexact encoding refusals, adds four wrong rate/unit/case refusals and duplicate
rate refusal, and proves no later settings actions follow rate rejection. It
also matches the remaining original Export controls. This is a producer replay,
not a replacement for native qualification.

Commands from source root:

```sh
../../filequay/source/.tools/powershell-7.6.6/pwsh -NoLogo -NoProfile -File distribution/windows-gui/test_consumer_encoding.ps1
python3 -m unittest discover -s distribution/tests -p test_consumer_release_inputs.py
```
