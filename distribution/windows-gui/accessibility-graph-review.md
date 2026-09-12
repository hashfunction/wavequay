# WaveWeft Export accessibility graph diagnostic

This change adds observations. It does not claim to repair or qualify the
Windows Export dialog.

## Original evidence

Run **34700392536**, public source
`753e3cf724ad05e565a6f055921083a5bd090759`, completed genuine import, Reverse,
and AUP4 save. Its retained screenshot shows a fully rendered Export audio
dialog. The original workflow then failed while finding the exact Format combo.

All 55 bounded reads failed in `RawViewWalker.GetFirstChild` on the same node:
PID 5220, Export HWND 655738, runtime ID `42,655738,4,-2147482852`, depth 1,
30 visited nodes. The unsigned Qt ID is **2147484444**. The separately retained
focused combo has Qt ID 2147484439. There is no evidence of a successful recipe
or audio export in this run.

Qt 6.11.2 `QWindowsUiaMainProvider::Navigate` selects the first valid,
non-invisible child and returns its provider. Its normal returns do not explain
the observed E_FAIL. UIA also obtains fragment roots, runtime IDs and properties
after navigation. Muse's controller independently supplies child, parent and
index lookups; its item provider falls back to the current interactive window
when the item's own accessible window is null. The original external UIA
receipt cannot establish these internal relationships. No malformed edge is
assumed, and Text nodes remain fully traversed.

## Observation and boundaries

`src/appshell/internal/accessibilitygraphdiagnostics.*` runs only with the exact
`CI=true` and `WAVEWEFT_ACCESSIBILITY_GRAPH` environment opt-in. Ordinary mode
allocates no reader or timer and performs no graph inspection. Audio-plugin
registration still returns before this hook.

The output must be the exact `Temp/accessibility-graph.jsonl` beneath a canonical
`private-environment` directory with its existing UUID owner marker. Qt opens
the file with `NewOnly`; existing output, redirection, missing/changed ownership
and noncanonical paths are refused. The original staged observer supplies this
path after its existing exclusive profile claim. Installed/broker diagnostics
are explicitly unsupported, so this option cannot change installed launch
environment or package acceptance.

A GUI-thread QTimer samples once per second. It observes visible windows only
when they already have a platform handle. `winId()` is never called to create a
window. No provider factory, accessibility update handler, focus route or UIA
callback is replaced. The reader never pumps the event loop, requests focus,
invokes actions, or calls name/text/value/rectangle queries. It records numeric
IDs/roles, validity, disabled/invisible/ignored states, bounded QObject class
metadata, child indexes, reciprocal parents/indexes, provider/item/parent
windows, and the provider window's actual accessible root.

Every snapshot starts a fresh visited set. Repeated edges remain in the record
but are not followed recursively. Limits are 256 nodes, 32 levels, 90 seconds
and 8 MiB. Per-query begin/end markers are flushed before/after the actual public
read, leaving a bounded last-query observation if the process stops there.
Started, snapshot boundaries, truncation reasons and a final end marker are
explicit. An abruptly terminated process can produce an incomplete trace;
collection labels it incomplete and does not claim success.
The elapsed deadline stops issuing further reads; it cannot preempt a single
blocked provider call. Such a call leaves its flushed begin marker and remains
subject to the unchanged outer observer/job cleanup deadlines.

`collect_accessibility_graph.py` runs after the existing owned job/process stop
and before existing private-profile cleanup. It verifies original ownership,
retained PID/source, byte/row bounds, field/type allowlists and duplicate JSON
keys, then copies the exact bytes with exclusive creation. It does not modify
the original GUI error or graph. Its metadata always says `accepted: false`.
Capture errors remain secondary, including thrown command failures.

`diagnosticAccessibilityGraph` is an explicit Boolean in the raw GUI and
top-level result. Normal runs emit false; the independent GUI verifier requires
exact false. A diagnostic run cannot mark GUI acceptance, consumer validation
or package export successful even if all original interactions happen to pass.
All original module, process, foreground, input, file, recipe and cleanup gates
remain in place.

For this explicit diagnostic only, new runtime/source collector errors are
retained in `diagnosticProvenanceErrors` (at most eight exceptions of 8192
characters, with truncation indicated), allowing the same owned staged observer
to collect the graph before the run is rejected. Normal runs retain immediate
failure at the original provenance step. No missing provenance receipt or
acceptance is manufactured. The final exporter must require exact false for
`diagnosticAccessibilityGraph` and an empty `diagnosticProvenanceErrors` list.

## Verification

The first native fixture failed before implementation because the reader was
absent. The new acceptance-refusal fixture failed against the old verifier.
A duplicate-key fixture also failed before the collector was tightened.

Fresh local verification:

- Actual Qt **6.11.2** / Muse fixture: all four existing provider-order and main
  window variants pass, each retaining the 30-second process deadline and all
  three original page/action assertions. The new fixture executes the real
  GUI-thread QTimer/native-window entry point and reader, plus malformed
  parent/cycle/duplicate graphs, fresh visited sets, depth/node/byte caps,
  dormant mode, existing-file and ownership refusal, no native-window creation,
  and no user names/titles. No Muse provider is substituted in the normal graph.
- 60 focused Python tests pass (`test_accessibility_graph`,
  `test_gui_evidence`, `test_consumer_audio`), including the actual C++ writer's
  JSONL replay through the production validator, original primary-error
  retention, abrupt-stop metadata, PID/mode/owner refusals and exact byte copy.
- The actual PowerShell production helper and extracted production collection
  boundary pass: dormant mode; both installed-mode refusals; missing/changed
  owner; existing file/directory preservation; nonzero and thrown collector
  failures; normal immediate provenance failure; bounded diagnostic provenance
  retention without acceptance.
- Complete net48 `GuiProbe.csproj` builds with locked, existing reference
  packages, zero warnings/errors. PowerShell parsing and `git diff --check`
  pass.

Commands:

```text
cmake --build /private/tmp/wave-onboarding-runtime-build --parallel 2
/private/tmp/wave-onboarding-runtime-build/onboarding_accessibility_probe
/private/tmp/wave-onboarding-runtime-build/onboarding_accessibility_probe --muse-factory-last
/private/tmp/wave-onboarding-runtime-build/onboarding_accessibility_probe --application-window
/private/tmp/wave-onboarding-runtime-build/onboarding_accessibility_probe --application-window --muse-factory-last
pwsh -NoProfile -File distribution/windows-gui/test_accessibility_graph.ps1
dotnet build distribution/windows-gui/GuiProbe.csproj -p:RestoreLockedMode=true
```

The full Python test launcher configures this same native fixture itself under
`distribution/tests/test_onboarding_accessibility.py`. Local verification reused
the existing build directory and independently ran each executable with the
same 30-second timeout, avoiding another source download/build cache.

## Native dispatch and interpretation

Dispatch `windows.yml` with **`capture_accessibility_graph=true`**. The native
package, source hashes and output IDs must come from that fresh run; do not pin
the old runtime ID as an expected ID. Retained files are
`build-evidence/gui/accessibility-graph.jsonl`,
`accessibility-graph-capture.json`, the unchanged GUI/consumer receipts, and
`build-evidence/result.json`.

Correlate the new failure's retained HWND/PID and final signed runtime-ID
component with the graph's unsigned Qt ID (`signed_id & 0xffffffff`). Inspect
the matching node and its edge records across snapshots, including reciprocal
parent/index and window-root IDs. If these are consistent, the record narrows
the next investigation to the Qt/UIA handoff; it does not establish that
conclusion in advance. This host cannot reproduce Windows UIA E_FAIL. No
Windows qualification, native fix or Store-ready output is claimed.

## Export-target refinement after run 34704945851

The original run's graph is 8,387,748 bytes, SHA256
`5487862a2d4e8d415f2209c1ac5244e3ac4a8a187e678c588552c69a7f56e62e`.
It contains 50,404 rows and ends at the byte limit after 6,073 ms. Its 48,178
query rows concern pre-export windows. The later consumer failure concerns
Export HWND 721104 and signed Qt identity -2147482850, which is unsigned
2147484446 (`0x8000031e`). That identity is absent from the original graph.
The original graph remains unchanged and still passes the bounded collector.
No export-provider cause can be inferred from this pre-export trace.

The timer now records bounded class/handle metadata for visible windows with
an existing platform handle, but queries a graph only when the actual window
class is `QQuickView` and its **direct QObject parent's** generated class is
exactly `ExportDialog_QMLTYPE_<decimal digits>`. The producer is
`WindowView::initView` in `muse/framework/uicomponents/qml/Muse/UiComponents/windowview.cpp`:
it creates a QQuickView and calls `m_view->QObject::setParent(this)`.
`src/importexport/export/qml/Export/ExportDialog.qml` supplies the export
controller. `QWindow::parent()` is the native-window relationship and must not
be substituted for QObject ownership.

Each observed window row retains `objectClass`, `ownerClass`, up to eight
`ownerClassChain` entries, and a Boolean `selected`. Unknown owners are recorded
without accessibility queries; titles, object names, user text and values
are never used as a fallback. `selected` describes target selection; the
existing flushed `window-root` begin/end pair records the actual query.

Only the first three snapshots containing a selected export target are read.
The reader then records **`truncated: capture-limit`** followed by `end` and
stops its timer. This is a capture limit, not a success result. The original
8 MiB, 90-second, 256-node and 32-depth limits still apply first, including when
the export target never appears or its provider blocks. The collector's
`completed` means the JSONL stream contains a final `end`; its independent
`truncated` flag remains true and `accepted` remains false. Original consumer,
source, package, module, input, output and cleanup gates are unchanged.

### Focused evidence and verification

The new actual Qt fixture first failed against the prior production reader:
`pre-export and similarly named windows must not query accessibleRoot`.
The new collector fixture independently failed on `Unexpected graph fields`
before the bounded metadata schema was extended.

The fixture executes the actual timer and production graph reader. Its
300-node pre-export graph exhausts the unchanged byte cap when read directly
within eight snapshots. With window selection enabled, eight real timer ticks
retain only small window metadata and zero graph/root queries. A later actual
Muse popup receives the same QObject controller-parent relationship as the
production WindowView, then is read exactly three times. Qt itself creates
the controller's class from an `ExportDialog.qml` component URL. It is not a
handwritten class-name mock. Similarly named controllers, a title/object-name
lookalike, an exact-owner window with the wrong Qt window class, hidden windows
and windows without native handles remain unqueried. No platform window is
created by the reader. The previous malformed/cycle/duplicate, direct byte,
node/depth, fresh-visited-set, dormant-mode and ownership tests remain.

This tests actual Qt generated-class semantics and the production parenting
statement with the real Muse providers. The lightweight component body is a
QtObject fixture; it does **not** load the full production export QML/services
or reproduce Windows UIA. The fresh Windows record must still establish the
actual controller class and capture the failing export graph. A different
actual owner class will produce metadata only and must be investigated, not
silently accepted.

Local Qt 6.11.2 verification reused the existing small build directory. All
four provider-order/main-window variants passed within the unchanged 30-second
per-process deadline (approximately 15 seconds each), including all original
onboarding interactions. The retained first variant's target graph is
167,858 bytes and 1,001 rows; its first query is snapshot 9 and its three target
captures end at snapshot 11 with `capture-limit`. Its actual generated owner
class was `ExportDialog_QMLTYPE_17`; this number is evidence, not a pin.

Fresh focused validation also passed:

- 10 graph collector tests, including both actual C++ writer byte streams,
  bounded owner-chain/type refusals, original-file preservation and explicit
  capture-limit metadata without acceptance.
- 33 GUI evidence and 20 audio/file workflow tests, including diagnostic-mode
  rejection and original independent file/recipe/cleanup gates.
- The actual PowerShell graph preparation/ownership and collection-boundary
  fixture, preserving the original error for nonzero and thrown collection.
- C++ fixture rebuild and `git diff --check`.

Retained private review evidence is under
`/private/tmp/waveweft-target-graph-final` (four original fixture logs,
`variants.json`, direct and targeted writer JSONL). The original failing
fixture log is `/private/tmp/waveweft-target-graph-red.log`.
The replay command for these exact writer outputs is:

```text
WAVE_GRAPH_TEST_RECORD=/private/tmp/waveweft-target-graph-final/direct.jsonl \
WAVE_GRAPH_TARGET_TEST_RECORD=/private/tmp/waveweft-target-graph-final/target.jsonl \
python3 -m unittest discover -s distribution/tests -p test_accessibility_graph.py -v
```

The next reviewed native diagnostic still requires explicit
`capture_accessibility_graph=true`. No Windows export repair, consumer success,
installed qualification or Store readiness is claimed by this refinement.
