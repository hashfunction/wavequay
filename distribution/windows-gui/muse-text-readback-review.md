# Muse editable-text readback

Run **34725528186**, public source `f55ce1db2c1ea924b3f9eb1c44b304b9ded8fe50`,
artifact **10308320787**, failed in the staged GUI. Native build/recipe tests,
import, Reverse, AUP4 save, exact `44100 Hz` lookup and Stereo input succeeded.
No installed qualification or final unsigned export was reached.

The first error is `Queued control text did not converge within five seconds`
at `ConsumerSession.Field` while configuring the Folder field. All 58 Unicode
characters were sent through the existing per-character ownership/focus checks.
All **77** completed readbacks returned empty text, from elapsed 15 ms through
4979 ms. PID 5208, Export HWND 262594 and runtime identity
`42,262594,4,-2147482862` remained the same in the retained before/after checks.
The failure screenshot shows the edited path ending in `consumer-fixture`; its
horizontally scrolled rendering does not prove the complete input independently.
The original consumer validator reports cleanup true and workflow/close unproved.

`fixtures/folder-readback-34725528186.json` retains the exact original first/last
read objects, expected text, failure, identity and count. Full original
`consumer-workflow.json` SHA256:
`97f6c8341ac1fa3898f6d5b1ab3f12c47eca14e01d9793b27af43578c9494b2c`.
Original screenshot SHA256:
`56673053fe45284eb37f6e8c60bd0d0f37151658b9bebf33c66c7db5343f5f8b`.

## Source-backed cause and correction

The observer preferred ValuePattern whenever present. Qt 6.11.2 exposes that
pattern for every non-StaticText role, and its getter returns
`QAccessibleInterface::text(QAccessible::Value)`.
[Original Qt main provider](https://raw.githubusercontent.com/qt/qtbase/v6.11.2/src/plugins/platforms/windows/uiautomation/qwindowsuiamainprovider.cpp),
[original Qt value provider](https://raw.githubusercontent.com/qt/qtbase/v6.11.2/src/plugins/platforms/windows/uiautomation/qwindowsuiavalueprovider.cpp).

Muse's `AccessibleItemInterface::text(QAccessible::Text)` does not implement
Value and returns an empty QString. Its `QAccessibleTextInterface` instead
forwards character count and text to the actual `AccessibleItem` text property.
Production `TextInputField.qml` binds that property to `valueInput.text`. This
applies to Folder, File name and Recipe name fields; accessible Name is a
separate label and can include a spoken panel prefix or an uncommitted model
value. Name cannot be used as text proof.

Qt's TextPattern DocumentRange covers `[0, characterCount())`, using this text
interface. [Original Qt text provider](https://raw.githubusercontent.com/qt/qtbase/v6.11.2/src/plugins/platforms/windows/uiautomation/qwindowsuiatextprovider.cpp).

The only production change reverses the existing read-pattern priority in
`ConsumerSession.TextValue`: prefer the bounded 4096-character TextPattern
read, then ValuePattern only when TextPattern is absent. Empty, wrong or throwing
Text results never fall back to another pattern. Existing CR/LF handling,
exact string comparison, read-only five-second/101-observation bounds,
ownership/focus revalidation and recorded values remain unchanged. No input is
replayed, no screenshot/name is accepted as text, and native picker WM_GETTEXT
remains unchanged. Product code and every release/consumer oracle are untouched.

The source route explains the original consistently empty Value read. The
failed Windows run did not query TextPattern, so the new Windows TextPattern
result and full remaining consumer workflow still require a fresh native run.

## Focused verification

- Extended the existing `test_consumer_text_readback.ps1` to extract and execute
  production `TextValue` with private UIA interface doubles. The initial replay
  failed on the unchanged producer: `Muse editable text was hidden by empty
  ValuePattern`; the same case passes after priority correction.
- The retained original Folder sample plus filename and recipe values are read
  exactly. Empty/wrong/throwing Text cannot use a convenient Value fallback;
  Value-only and absent-pattern behavior, 4096 bound and existing CR/LF handling
  are checked. Existing native packets, convergence, timeout and ownership cases
  also pass in the same invocation.
- Added one small actual Muse provider check to the existing Qt executable. The
  registered real provider returns empty generic Value while its text interface
  returns the complete current Folder, filename and recipe strings. This sets
  the same AccessibleItem property used by the production QML binding; it does
  not simulate a Windows TextPattern or claim a rendered field interaction.
- Incremental build and both existing Qt-last/Muse-last probe orders passed,
  each with the original 30-second subprocess limit. Existing navigation and
  recipe dialog checks also completed. No broad suite or source archive scan.

Commands from source root:

```sh
../../filequay/source/.tools/powershell-7.6.6/pwsh -NoLogo -NoProfile -File distribution/windows-gui/test_consumer_text_readback.ps1
cmake --build /private/tmp/wave-onboarding-runtime-build --target onboarding_accessibility_probe -j 2
```

Bounded probe invocations (Python subprocess, timeout=30 each):
`/private/tmp/wave-onboarding-runtime-build/onboarding_accessibility_probe` and
the same executable with `--muse-factory-last`. Original local outputs are
`/private/tmp/waveweft-34725528186-provider-0.log` and `-1.log`.
