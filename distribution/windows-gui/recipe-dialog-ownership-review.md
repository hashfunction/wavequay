# Recipe dialog accessible window ownership

Candidate follows local `d2239b47f7095bd688aa0bf780ab129e3b0f5985` and public
`225649b59f56147d286c0405d90e2b007b0e5930`. Native run `34708545719` completed
the native build and original onboarding/editor observations, then failed in
`configure-wav-recipe`. Import, Reverse and project save had progressed; recipe
application, WAV export and complete consumer acceptance were not established.

## Original evidence

Original qualification artifact `10302474127` is retained privately at
`/private/tmp/waveweft-34708545719-review`. No original bytes were rewritten.

| Original GUI file | Bytes | SHA256 |
| --- | ---: | --- |
| accessibility-graph.jsonl | 1056017 | 2634b03bbe302cc08dc024dfa8a29ee95799096252cc38683a66a2435b08fb13 |
| accessibility-graph-capture.json | 606 | d3eb4b66bb18765141d9a32a5ce695100aec0eda4eefdad498e0d34452e5279c |
| consumer-workflow.json | 134528 | 9271e027a462cb2ea5aee2c7a0328081fd9e922a74d5f2969f49e5540883b080 |
| gui-observations.json | 137907 | 582138fdb5d130c9298ba4e1a51997627bf22294ecc11b62d762035bc5a8b25e |
| failure-window.png | 92701 | ead17e7a87aac220607b6290885ffbb378c52e4b8f587c8fc4651716c702fe8e |

The targeted graph contains 6317 rows and exactly three Export snapshots
(33–35), 46 nodes each. The original collector accepts its schema/byte stream
with no errors and explicitly reports diagnostic-only, accepted=false and
capture-limit truncation. Actual owner is `ExportDialog_QMLTYPE_589`, direct
QObject parent of QQuickView HWND786614, PID5724. All 135 observed edges have
reciprocal parents and all nodes are valid.

UIA's first and last GetFirstChild failures identify the same blank Muse Text
panel, runtime ID `42,786614,4,-2147482852`. The signed final component maps to
QAccessible ID2147484444. Its first visible child is ID2147484446. The original
consumer records 55 E_FAIL provider failures; no graph mutation is inferred.

| Branch | Panel/window | Children/native handles |
| --- | --- | --- |
| Failing panel | 2147484444 / 786614 | 2147484445 disabled Button, 2147484446 enabled Button, 2147484447 enabled ComboBox; all handle0 |
| Following panel | 2147484448 / 786614 | 2147484449–2147484454, six Save dialog controls; all handle0 |

The screenshot shows only Export audio. The two unopened nested recipe dialogs
exist in the production QML but are not visible there. Three Manage controls
and six Save controls match the two observed branches. Native handle0 alone
does not distinguish a null QWindow from a QWindow without a platform handle.

## Source cause and bounded repair

Both recipe dialogs originally declared `property NavigationPanel panel` on
the nonvisual StyledDialogView root. Muse's AccessibleItem::resolveVisualItem
and AbstractNavigation::visualItem walk QObject parents until a QQuickItem.
As nested children of ExportDialog's contentData, these panel roots walk into
the outer Export content item. The controls instead live inside their own
StyledDialogView content item, attached to a separate QQuickView by
WindowView::componentComplete. That view exists before open but has no native
handle. The existing StyledDialogView NavigationSection explicitly documents
that it must be inside a QQuickItem to determine its window.

The actual Qt/Muse regression reproduced this relationship with unchanged
Manage QML: panelIsOuter=true, panelIsNested=false, nestedHasHandle=false; all
three real navigation controls resolve the nested view. After repairing Manage,
its closed/open/closed assertions passed and unchanged Save independently failed
the same assertion with all six controls. This establishes a product QML
ownership defect rather than a consumer timing issue.

Qt6.11.2 Windows UIA `windowForAccessible` returns an accessible's non-null
QWindow before considering its parent. `get_FragmentRoot` resolves that own
window's accessible root. Thus these children cross from the visible Export
panel into an unopened recipe window's fragment. Qt's QueryInterface refuses
IRawElementProviderFragmentRoot with E_NOINTERFACE if that root has no native
handle. The local fixture proves
that incorrect window relationship and its correction. It does not execute
Windows UIA's COM boundary or claim the fresh native E_FAIL is already resolved.
Primary code: [Qt UIA window resolution](https://github.com/qt/qtbase/blob/v6.11.2/src/plugins/platforms/windows/uiautomation/qwindowsuiautils.cpp)
and [Qt UIA navigation/fragment root](https://github.com/qt/qtbase/blob/v6.11.2/src/plugins/platforms/windows/uiautomation/qwindowsuiamainprovider.cpp).

Each repair moves its original NavigationPanel into the existing body
ColumnLayout and exposes the same `root.panel` alias. Names, section, order,
control bindings, recipes, focus requests and actions are preserved. The Muse
dependency, application provider, graph diagnostic, consumer traversal and all
ownership/input/audio/file/cleanup acceptance gates are unchanged.

## Verification

The existing small actual Qt6.11.2 fixture is rebuilt at
`/private/tmp/wave-onboarding-runtime-build/onboarding_accessibility_probe`.
The normal entry point remains:

```sh
python3 -m unittest distribution.tests.test_onboarding_accessibility -v
```

It executes both production recipe QML files with real Muse navigation and
accessible providers plus real QQuickViews. Rendering-only text/dropdown leaves
and the external recipe model are substitutes, documented in the fixture README.
The fixture checks closed/open/closed ownership, all original control counts,
accessible sibling traversal to the input and close button, own-window focus,
and exclusion from the unrelated outer tree. All original onboarding and graph
assertions and the 30-second per-process limit remain.

Original failing fixture logs are retained at
`/private/tmp/wave-recipe-ownership-red.log` and
`/private/tmp/wave-recipe-ownership-save-red.log`.
Fresh green runtime logs are retained under
`/private/tmp/waveweft-recipe-ownership-final`.

Fresh validation passed:

- Four actual Qt6.11.2 provider-order/main-window variants, 14.4–14.7 seconds
  each, with both recipe ownership checks and every original onboarding/graph
  assertion.
- All five actual Python launcher tests, reusing only the already rebuilt
  executable/font paths to avoid another disposable build. This includes the
  four full runtime processes and missing/corrupt-font refusal before QML,
  captured stderr checkpoints and the unchanged 30-second subprocess limit.
- 58 consumer GUI evidence, audio/file and release-input tests.
- All 10 graph collector tests, including the retained actual C++ writer byte
  streams. Direct strict-reader validation of the original native graph also
  returns 6317 records, completed=true and truncated=true.
- CMake fixture compilation and `git diff --check`.

Fresh Windows native/consumer confirmation remains required. No package export,
source publication, Store readiness or hardware audio capability is claimed.
