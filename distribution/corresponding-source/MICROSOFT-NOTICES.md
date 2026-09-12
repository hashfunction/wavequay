# Microsoft runtime components

The original Microsoft documents in `microsoft-notices/` apply to the Microsoft
runtime components identified by `microsoft-notice-inputs.json`. WaveWeft and its
open-source components retain their own original licenses and corresponding
source; the Microsoft terms do not relicense that code.

The eight release VC143 CRT files are covered by the VS 2022 Enterprise and
Professional distributable-code terms/list, with the separate runtime terms
retained for recipients. The runtime EULA alone is not the redistribution grant.
The VS list permits unmodified release runtimes from `VC/Redist`, excludes debug
redistributables and is subject to the applicable licensed-toolchain terms.

The SDK list explicitly names the unmodified x64 `d3dcompiler_47.dll` under
`Windows Kits/10/Redist/D3D` for Classic Windows applications. WaveWeft's package
is the existing native Win32 executable with `Windows.Desktop` and
`Windows.FullTrustApplication`; it is not a Universal Windows application.
The original SDK terms and distributable list are both retained.

These original documents include distribution and recipient conditions, copyright
and trademark protections, platform restrictions and applicable exceptions.
They are not a grant to relicense Microsoft object code as open source. Only the
nine named unmodified runtime DLLs are covered by this supplemental index. The
application's original license and the complete open-source notice catalog stay
separate. Store certification and actual installed qualification remain separate
requirements.

Original documents were retrieved from Microsoft's HTTPS license directory and
Learn's official Markdown representation on 2026-09-12. The runtime DOCX is an
unchanged previously retained Microsoft original, explicitly marked in the
index; no claim is made that it was fetched again. Exact sizes/hashes and source
URLs are independently checked. Five original documents total 176,604 bytes.
No historical source catalog or source-publication receipt was altered.

Validation: four production-boundary tests passed, covering the real five
documents/nine-file scope, altered/missing/untracked terms and five coherent
owner/hash/URL/schema mutations and Git's explicit no-conversion attributes for
the original catalog, publication receipts and Microsoft terms. All four
publication tests also passed with unchanged original hashes. Actual configured Windows runtime signatures
and byte equality remain mandatory observations, not conclusions from these
document names. This supplement alone leaves source/license closure false.
