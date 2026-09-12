# Original software renderer archive

The release collector now independently compares `bin/opengl32sw.dll` with the
single original regular member of Qt's pinned historical Mesa 11.2.2 archive.
The exact archive, member, deployed path, version and preferred-source owners
are explicit. An equal hash under a foreign filename cannot acquire ownership.
The existing Qt prefix match remains an observation, not the archive proof.

The actual retained archive is 5,474,526 bytes, SHA-256
`59a086716cfd4bdec035698d501ba45526f8d2ecb5c0c428a356d8be0b5d2c79`.
The current fixed production helper compared its original 20,639,888-byte member
against the original run 34697625639 stage receipt, SHA-256
`b04de4541863bc7d8879040a78889c4849c1b1da2784c4630f734c146c2998ce`.
The real CMake/LibArchive comparison passed on macOS. This is original byte
membership evidence; it does not assert reproducibility of the historical
build, a new Windows run or license closure.

Three new production-helper tests passed, including actual archive reading,
fixed-input binding and ten missing/changed/foreign owner/member/archive cases.
All 13 native collector and Qt/platform archive tests passed; diff check passed.
Mesa and historical LLVM source/notices remain in the original published
40-archive catalog, with their original terms. The collector's source/license
flag remains false pending the separate complete release gate.
