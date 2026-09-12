# Onboarding accessibility runtime regression

Run from the source root:

```sh
python3 -m unittest distribution.tests.test_onboarding_accessibility -v
```

The fixture builds against the installed Qt (6.10 or newer; verified with 6.11.2),
uses the pinned Muse utfcpp dependency, and uses either the workflow's existing
`.ci-googletest` checkout or an installed GTest CMake package. It opens only
offscreen Quick views and does not write a user profile.

Each process retains the 30-second runtime limit. The launcher forces Qt's
early messages onto stderr; the executable then gives Muse's real logger a
fixture-only, immediately flushed stderr destination. Qt and Muse can otherwise
send Windows messages to `OutputDebugString`, outside the subprocess pipes.
Both executions require every startup/teardown checkpoint on the captured
stderr stream, including messages after Muse takes over Qt logging. Timeouts
still fail and report all captured output.

The build copies the existing Muse drawing-test `FreeSerif.ttf` into its own
temporary font directory. Before loading QML, the probe registers that font and
requires an actual matching font engine with usable glyphs; both the application
and fixture theme use it. Missing or invalid font bytes must fail before QML.
This avoids depending on the host's font database: Qt 6.11.2's Windows offscreen
backend uses FreeType and otherwise searches the absent Qt `lib/fonts` directory.

Windows run `34671040232` reached the Muse provider and verified the first two
pages before timing out. A local Qt fontless `minimal` diagnostic reproduced
that third-page timeout; sampling placed the main thread in Qt event dispatch,
layout polishing and text geometry with `QFontEngineBox`. Enabling fonts alone
completed all assertions, as did registering the existing FreeSerif font under
offscreen with both provider orders. This establishes the local fontless
failure and correction. Windows run `34672540001` subsequently passed both
provider-order tests and the missing/corrupt-font test within their unchanged
bounds, before completing the full app build and reaching the staged GUI probe.

## Production boundary exercised

The executable compiles the real `FirstLaunchSetupModel`, Muse accessible
registry, window/item providers, accessibility controller, navigation types,
navigation controller, and command dispatchers. It loads byte-for-byte copies
of production `FirstLaunchSetupDialog.qml`, `Page.qml`, `FlatButton.qml`, and
`StyledDialogView.qml`. QML disk caching is disabled.

The external interactive and application-settings services use existing test
mocks. The fixture substitutes the native rendering shell and decorative
controls, and the three page bodies supply the exact qualification titles to
the production `Page` type. The real onboarding model selects their URLs,
emits page/button notifications in production order, and writes completion
through its actual settings interface.

Both tests use the app shell's `registerDialogAccessibility` function and the
real Muse registry. The factory callback uses Muse's getter-then-stub dispatch.
A second callback constructs Qt's real native Quick interfaces to exercise
both provider-registration orders deterministically. Qt private interfaces are
used only by this test adapter; production uses Muse's public registration API.

The assertions cover:

- The popup uses the existing Muse window provider even when Qt registers its
  base-window provider later.
- A populated main window retains its own controls and focus without placing
  them in the popup. Child/parent/index round trips and Windows UIA's sibling
  navigation reach the exact surrogate on every page, with hidden nodes skipped.
- Foreign window children and out-of-range indexes are rejected.
- The popup's actual `focusChild()` resolves every exact page/button name as an
  enabled, focused Button, reachable in its accessible tree.
- `resetFocus()` removes the page from accessible focus lookup.
- Neither the page nor Next has a duplicate native press route, including
  retained native adapters invoked while withdrawn, hidden, or disabled.
- The real Next navigation handler refuses disabled/hidden controls, advances
  one page per permitted trigger, and writes completion exactly once.

## Repair and observed failures

The app shell registers `QQuickView`, the concrete class used by `WindowView`,
with a subclass of Muse's existing `AccessibleWindowInterface`. Registration
still requires Muse's `QQuickWindow` provider. The subclass limits child/count,
index and focus lookup to controls belonging to the dialog's own window;
all item providers and action/state behavior remain Muse's implementation.
It does not move native keyboard focus away from existing navigation controls.

Run `34672540001` rendered page 1 but its raw UIA popup tree contained the main
window's List and content Group instead of onboarding controls. Muse's original
popup provider resolves the transient parent's controller and exposes its full
child list. Those main-window children report their own window as parent, so
Windows UIA's parent/index-based sibling navigation escapes the popup tree.
The earlier fixture had an empty main window and traversed child(index) directly.
Adding actual main-window accessible controls reproduced the invalid cross-window
child before the repair. The corrected tests preserve both views, a focused main
control and all existing page/action assertions, and exercise UIA sibling
navigation on the actual providers. Fresh Windows UIA confirmation remains required.

The dialog also keeps `activeButtonTitle` bound to the active button. The real
model emits `currentPageChanged` before `nextButtonTextChanged`; a one-time
assignment captured an empty suffix on the first page and could retain the
previous label on later pages. The runtime test reproduced `Select a theme. `
instead of `Select a theme. Next` before that fix.

The prior candidate's Qt attached press handlers are removed. The existing
Muse reading surrogate and guarded navigation command remain the interaction
route. Counterfactual runs failed on provider selection, the empty first-page
suffix, and each duplicate native press handler before their respective fixes.

This fixture dispatches the real command reached by the Enter navigation
action. It does not synthesize Windows keyboard input, run UI Automation, or
verify a rendered desktop screenshot. The unchanged Windows qualification
probe must still prove the genuine popup, exact identities, foreground and
process ownership, all three interactions, and stable editor before release.
