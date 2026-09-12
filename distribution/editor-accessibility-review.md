# WaveQuay editor accessibility provider — run 34679180285

Base source: `056d18288b09e0fc48148e96a877e941c10bbbce`; public snapshot
`e590725a2bc4d28d1633dbe598b2c9f3f6f7086d`. This candidate repairs the
ApplicationWindow provider selection reproduced with the actual Qt/Muse
integration. Fresh Windows editor qualification remains pending. It does not
establish native project, audio/export, package installation or Store acceptance.

## Actual Windows evidence

Evidence lives under
`/private/tmp/wavequay-34679180285-review/WaveQuay-Windows-qualification/build-evidence/gui`.
The retained app PID was 6732. All three expected onboarding pages and their
exact owned native button inputs passed. The subsequent title was exactly
`WaveQuay 4.0`. The latest tree identifies main HWND 197018, class
`Main_QMLTYPE_548`, and only the window/title-bar/system menu/minimize/restore/
close nodes. No Playback toolbar or Add track control was exposed. The genuine
failure screenshot shows the complete empty editor and visible Add track button;
the helper correctly refused to infer accessible editor success from pixels.

- `gui-observations.json` SHA-256:
  `44374b3a9dd8299dbb7b2f024572205880dd40bf5210be49ffb5de72f55f25a2`
- `latest-ui-tree.json` SHA-256:
  `05e389c4923da853b949059e1fa2016c4fc1f23eb7bc10c5f8f1e27f77576008`
- `failure-window.png` SHA-256:
  `4746e8058ac05a5060005aab9545caa238d45c3eb530ac47e432553abab55e87`

The 90-second observation failed with no main-window acceptance events.
`survivedUntilCleanup` remains false; exact owned-job closure and process exit
were recorded. The retained snapshot is evidence of visible startup, not a
completed consumer workflow.

## Reproduced cause and bounded repair

The Windows Main.qml inherits AppWindow.qml, whose Qt root is
`QtQuick.Controls.ApplicationWindow`. Its concrete Qt base is
`QQuickApplicationWindow`. The previous provider regression fixture used
`QQuickView` for both main and popup windows, so it did not cover this main-window
class. The app's existing concrete QQuickView registration repaired the popup
but left the main window dependent on Muse's base `QQuickWindow` getter.

Qt 6.11.2's [Quick accessibility factory](https://github.com/qt/qtdeclarative/blob/v6.11.2/src/quick/accessible/qquickaccessiblefactory.cpp)
handles QQuickWindow. Its [Templates module initialization](https://github.com/qt/qtdeclarative/blob/v6.11.2/src/quicktemplates/qtquicktemplates2global.cpp)
also installs a stock QQuickApplicationWindow provider. A same-class registry
entry still loses when that Qt factory is installed later. This was reproduced:
both new ApplicationWindow cases failed before repair, while existing popup
cases passed; registering only QQuickApplicationWindow left the Qt-last case
failing. The failure was the actual main interface's provider type, before
control lookup, rather than a guessed label or screenshot assertion.

The final app-side factory resolves only requests for the object's actual
most-derived metaobject when it inherits QQuickApplicationWindow and that
metaobject differs from the Qt base. It does not hardcode generated QML type
numbers, intercept unrelated objects/classes, or replace Qt's base getter. This
selects the existing Muse window provider before factory traversal reaches Qt's
competing base class, independently of the later Qt factory. Registration is
enabled only when the existing Muse QQuickWindow provider is present.

The provider's existing per-window children, parent/index round trips and focus
filter are reused unchanged. There is no Qt/submodule edit, cached-interface
deletion, delayed forced activation, new input route, QML behavior change or
helper-only application flag. The production change is an eleven-line factory
and its registration in `src/appshell/internal/dialogaccessibility.h`.

## Regression and verification

The native fixture now creates a real QML ApplicationWindow with the installed
Qt 6.11.2 and actual pinned Muse controllers/accessibility providers. It keeps
the QQuickView popup, real onboarding QML/model, existing guarded navigation
transitions and completion-write checks. Both factory-order modes must select
Muse for the main window, preserve main/popup separation, and expose main
controls/focus through the parent/index sibling traversal used by Windows UIA.
Those routes must survive destruction of onboarding. Null objects, popup objects
and unrelated class requests are rejected by the new factory.

- Initial red: two ApplicationWindow cases fail; three existing cases pass.
  Log: `/private/tmp/wavequay-application-window-red.log`.
- Intermediate same-class entry: Qt-last case still fails. This explains why
  the final change targets the real derived metaobject.
  Log: `/private/tmp/wavequay-application-window-green.log`.
- Final focused Qt/Muse suite: all five tests pass, with successful real
  ApplicationWindow provider and post-onboarding traversal checks.
  Log: `/private/tmp/wavequay-application-window-green2.log`.
- Full `python3 -m unittest discover -s distribution/tests -v`: 47 tests pass,
  including actual Qt/C++ builds, original QML runtime cases, compiled C# window
  discovery replay, exact title/compiler binding, and missing/disabled editor
  evidence rejection.
  Log: `/private/tmp/wavequay-main-accessibility-distribution.log`.
- The actual production onboarding input guard passes its normal/negative-monitor
  cases and 21 ownership/focus/geometry mutations. Display mode/scoping tests
  pass, including original-mode restoration, partial apply and failure evidence.
- `git diff --check` passes. Pinned Muse and dependency submodules are unchanged.

The local .NET replay used
`/Users/hashfunction/workspace/project_app_factory/microsoft-store/apps/filequay/source/.tools/dotnet-10.0.401/dotnet`;
PowerShell checks used that same FileQuay source's
`.tools/powershell-7.6.6/pwsh`. The GUI observer, onboarding input implementation,
exact expected title, independent GUI verifier and display helper are all
byte-for-byte identical to the base. Required Playback toolbar/Add track,
three-second editor stability, staged module provenance, strict ownership,
onboarding and cleanup gates remain intact.

Independent review and a fresh Windows run must confirm the actual exposed
editor tree. No current screenshot, native acceptance flag, branding, version,
Store identity, preference path, data format, website, parent status or public
branch was changed. WaveWeft branding remains a separate change.
