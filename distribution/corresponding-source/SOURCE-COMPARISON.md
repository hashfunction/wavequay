# Original Qt source comparison

The fixed input JSON records the exact original Windows SDK archives and their original binary/source SPDX metadata, observed with native run 34694396308. It records dependency inputs, not application installation or release approval. No source or binary archive is committed here.

All five preferred complete Qt 6.11.2 source archives were compared with the source file hashes in those original Windows SDK inventories by the production `qt_source_proof.py` helper on macOS:

| Module | Files compared | Exact bytes | Observed LF to CRLF | Explicit metadata exceptions |
| --- | ---: | ---: | ---: | ---: |
| Qt Base | 22,490 | 6,976 | 15,514 | 403 |
| Qt Declarative | 22,877 | 4,520 | 18,357 | 13 |
| Qt 5 Compatibility | 1,409 | 1,101 | 308 | 0 |
| Qt Shader Tools | 305 | 1 | 304 | 0 |
| Qt SVG | 628 | 78 | 550 | 10 |

The source archive bytes are unchanged. The alternative comparison permits only a lossless insertion of CR before LF when the source contains no CR. It reports that transformation separately; no whitespace trimming, Unicode normalization or arbitrary patching is accepted. The original SHA-1 inventory is bound by the original source SPDX's SHA-256 and the original binary archive's SHA-256. Preferred source archives also have exact SHA-256/size pins.

Every metadata exception is listed individually in the fixed JSON. They are omitted `.gitignore`/`.gitattributes` control files or the root `.tag` generated when creating a release archive. The comparison requires the exact reviewed exception set and refuses missing or changed implementation, build and license files. Both present and missing additional exceptions fail. No exception covers code or license terms.

Qt Declarative illustrates why version labels alone are insufficient: its original binary SPDX package references `4e3399c26ec57246c08de019cfcbda8d23604cfa`, while the complete release source archive's generated `.tag` contains `40f29cb023c69ba60fee18c320b18bfd79a200d9`. Both the exact public Git archive for `4e3399c` and the preferred complete release archive produce the same original source-file comparisons above. The complete release archive additionally retains the ECMAScript test-suite material that a Git repository archive does not populate from its test submodule. The different revision labels are retained explicitly; they are not rewritten into a false identical-revision claim.

The original Qt SVG binary archive already passed the separate production native member comparison for all three shipped DLLs. Complete five-module native archive comparisons and current Windows collector integration remain separate work; this file does not claim those checks have run.

Four production Qt comparison tests passed after first failing for the absent implementation. They cover exact and observed Windows line endings, changed/missing implementation and CMake files, generalized/hidden-source/extra exceptions, duplicate paths/checksums/source members and traversal. Three preferred-source member tests passed after first failing for the absent reader: actual tar/ZIP notices and exact source-header excerpts, changed archive/member/notice hashes and bounds, missing/duplicate/link members, and no extraction of source trees. These local fixtures are not Windows installed evidence.
