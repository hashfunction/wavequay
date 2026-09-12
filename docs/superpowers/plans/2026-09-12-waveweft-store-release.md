# WaveWeft Store release implementation plan

> For agentic workers: use superpowers:executing-plans for the approved inline execution and independent root-agent review after each commit.

**Goal:** Build and qualify the assigned WaveWeft 1.0.1 MSIX with exact native source/notices and an independently gated unsigned Store artifact.

**Architecture:** Keep the existing staged qualification. Build fixed disposable and Store packages from the same inventoried stage, run the existing real consumer driver through owned package activation in separate processes, then independently verify source, payload, installed evidence and source delivery before export. Packaging and observation never become product runtime behavior.

**Tech stack:** Python standard library, CMake, Windows SDK MakeAppx/SignTool, Windows PowerShell 5.1 UI Automation, PowerShell 7 orchestration and existing C# native input/audio workflow.

**Spec:** Root approved the four-step read-only audit plan in this task on 2026-09-12. This document preserves its implementation boundaries.

## Constraints

- Store identity `1659hashfunction.WaveQuay`, publisher `CN=B6A2631A-FD32-45CC-AE12-82466975F528`, publisher display `hashfunction`, family `1659hashfunction.WaveQuay_r3hxytd7jt6c4`.
- Application.Id remains the documented `WaveQuay` contract; executable `bin/WaveWeft.exe`, version `1.0.1.0`, x64, Windows.Desktop, runFullTrust.
- Preserve data/settings namespaces and all actual onboarding, native input, audio/project/recipe oracle, normal-close, process/module/display/profile cleanup checks.
- Never treat a staged process as installed qualification, or a source URL alone as complete provenance. Do not rewrite historical receipts.
- No source push, public binary/source upload, Store or site mutation before independent root review.

## Reviewable steps

### 1. Current native inputs and packaging contract

- [ ] Add `distribution/msix/files.py` for regular-file inventory, canonical Windows paths and bounded archive verification, derived with retained MIT attribution from the already reviewed Scriblark helper.
- [ ] Add `distribution/RecordConsumedDependencies.cmake` to record the resolver's actual consumed components and owned recipes without fetching unused platform dependencies.
- [ ] Add `distribution/msix/native_sources.py`: inventory exact resolved runtime members, current source/archive pins and original notices; record unresolved inputs explicitly. Do not claim source closure until independently complete.
- [ ] Add `distribution/msix/package.py`: two fixed identities, exact generated manifest/artwork, byte-bound payload, unsigned container and SDK-unpack verification. No installer or release claim in this first chunk.
- [ ] Write and run tests first for alias/link/traversal/signing rejection, identity confusion and manifest mutation, unknown native owners, changed source/archive/member/notice hashes. Run existing focused distribution checks, review diff, commit.

### 2. Installed activation and existing consumer flow

- [ ] Add fixed-mode package installation orchestration and exact registration/process/certificate ownership. Refuse existing same-name registration and foreign process adoption.
- [ ] Add a C# installed launch boundary using real ApplicationActivationManager; retain package name/family/AUMID, PID/start time/executable/hash and package identity from the opened process.
- [ ] Reuse onboarding and `ConsumerDriver` unchanged after launch. Claim source-defined initially absent host profiles; record broker environment as unmodified, not the staged private environment. Treat actual Windows profile virtualization as evidence to verify, not an assumed redirect.
- [ ] Independently verify installed payload and modules, normal close, exact uninstall, certificate/profile/display cleanup. Test wrong identity/PID/reused process, unowned profile/registry, failed cleanup and incomplete observations.

### 3. Source delivery and package notices

- [ ] Resolve only consumed native/source inputs. Reuse existing exact public source assets and archives; retain original build metadata and component licenses for Qt, Muse dependencies, static/vendored sources and shipped Microsoft/Mesa files.
- [ ] Package a full indexed notice tree and current source/rebuild instructions. Keep permissive/proprietary notice obligations distinct from required corresponding source; no arbitrary rebuild gate.
- [ ] Validate current payload-owner/source/notice coverage, pinned submodules/recipes and actual reachable complete source delivery. Source publication remains a separately reviewed action.

### 4. Independent Store export and Windows integration

- [ ] Add an independent exporter requiring exact current source/run/attempt, regenerated payload/manifest, unsigned container, standalone/embedded receipt equality, two complete installed workflows and source publication.
- [ ] Reject coherent substituted payloads, staged-only receipts, partial input/oracle evidence, stale source/module hashes and signing material through meaningful negative fixtures.
- [ ] Run the fixed disposable and Store installed qualifications after existing staged qualification. Export only the unsigned Store MSIX and JSON receipt on complete success; retain bounded failure metadata separately.
- [ ] Run focused/full appropriate tests, PowerShell parse/runtime fixtures and C# compilation. Commit and report limits; only actual fresh Windows can establish installed success.
