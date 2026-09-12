# Exact original native archive members

This chunk compares the resolver's current native files and installed notices with their exact original prebuilt archive. The prior collector established prefix ownership and archive hashes; it did not establish that the resolved bytes were members of that archive. Source and license closure remain explicitly false.

The production helper uses the already configured CMake executable, retains its size/hash, checks it and the fixed archive before and after each bounded command, reads the entire bounded archive directory, rejects ambiguous paths and link/special members, and extracts only the named regular members into an owned temporary directory. It compares the complete extracted file set and each size/hash to the current resolved inputs. Nothing from the archive executes.

Actual local comparison used original metadata from Windows run 34694396308, not synthetic DLL hashes:

- FLAC original `flac-1.4.3-windows-x86_64-0b2bfbb431a5.7z`: 222,201 bytes, SHA-256 `d55b6d1221f163b67cfb0ec94d80f29bc6f9124e93a4ee6c440d77a8a89d2c45`. Both staged FLAC DLLs matched original members.
- Qt SVG original `6.11.2-0-202608131017qtsvg-Windows-Windows_11_24H2-MSVC2022-Windows-Windows_11_24H2-X86_64.7z`: 684,353 bytes, SHA-256 `417f44499c835b2303f3ff78043179bb23442f33d5d2816fbf7e8dbf275b1c89`. `Qt6Svg.dll`, `qsvgicon.dll` and `qsvg.dll` matched all three staged files. The Qt-specific collector is still pending.

The original public archive URLs come from the pinned Muse dependency release and Qt's exact online SDK package. Local proof JSON is retained under `/private/tmp/waveweft-corresponding-source`; no binary or source archive is added to Git or uploaded by this chunk.

Verification: five production archive tests passed (real CMake 7zip and ZIP extraction, changed native/notice hashes, substituted archive, absent member, link/traversal/case aliases, and archive replacement across a real command); five existing native-source tests passed. The four initial archive tests failed before the helper existed. `git diff --check` passed. macOS CMake was used for these tests and the two original archive comparisons; fresh Windows remains necessary for the complete consumed set.
