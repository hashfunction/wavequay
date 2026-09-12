# Exact Windows export encoding label

Native run 34711728628, public `f7b46345e676e138745b371e362998e4c6f464f8`,
completed its build and progressed past the repaired recipe-panel accessibility
tree. Original artifact 10303997054 retains import, Reverse and project-save
observations. The failure at `configure-wav-recipe` is
`Choice navigation wrapped without exact expected item: Signed 16 bit PCM`.

The original owned UIA ListItem is named **Signed 16-bit PCM**. Its focus PID is
3104, popup HWND 918004 and runtime identity `42,918004,4,-2147482833`. The driver
observed all 15 encoding options and correctly refused to replay navigation
after wrap. `fixtures/encoding-options-34711728628.json` preserves those original
names and the original consumer-workflow SHA256. The complete originals remain
in the private review directory; none were rewritten.

The PCM export plugin obtains encoding names via `sf_encoding_index_name`
(`au3/modules/import-export/mod-pcm/ExportPCM.cpp`), which reads the actual
libsndfile subtype name using `SFC_GET_FORMAT_SUBTYPE`
(`au3/libraries/au3-file-formats/FileFormats.cpp`). The unhyphenated string in
ImportPCM and old translation catalogs is a different input-label source.

The correction changes only the driver's expected literal and the independent
release action validator's corresponding exact literal. Native ownership,
foreground, focus, uniqueness, bounded navigation, exact matching, single
acceptance input and all recipe/file/audio/close gates remain intact.

`test_consumer_encoding.ps1` compiles and executes the actual production
Settings, Choose and FocusedChoice methods with only their native leaves
doubled. Against the retained real option names it reproduced the original
wrap failure before the correction. Afterward it accepts the exact observed
first item with one Enter and zero navigation, while three near-match labels
still wrap/refuse with zero acceptance inputs. The existing Windows entry point
now runs this regression. All five consumer release-input tests also passed.

No real WAV export, saved recipe application or normal consumer close is claimed
from this failed run. A fresh Windows run remains required.
