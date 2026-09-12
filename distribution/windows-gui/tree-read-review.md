# Complete consumer tree observations during dialog transitions

Original Windows run 34697625639 used public source `02f1de135dbe2fe02d06889b462df8bfa46dcfe1`. Its 512,763-byte metadata artifact is retained at `/private/tmp/waveweft-34697625639-review`; the failed log is adjacent. The source/export work remains separately committed in `c259548d89604a87ffe4d6e6a2341357012da050` and `07b7f9a44b8798d733e7ec116e37662528d8c9f3`.

The real consumer reached import, the guarded Effect → Special hover → Reverse click, and the save-project UI/file creation. Those three original screenshots exist. At 6.446 seconds, immediately after the single guarded Ctrl+Shift+E, `Settings` called `Target`, whose complete raw-tree enumeration threw COM `E_FAIL` (`0x80004005`) at `TreeWalker.GetFirstChild`. No export-setting input was sent. Original PID 2784 remained alive, with export HWND 655790 foreground. UIA focus identified the enabled, visible `Export panel, Type: Export full project audio` ComboBox. The screenshot shows a populated Export audio dialog.

The failure diagnostic tree hit the same error. This does not establish whether the provider error persists after the dialog transition; there was no complete retained export tree. Consumer completion, normal close and the final audio/project oracle remained unproved. Owned cleanup succeeded. The original screenshot is `failure-window.png`, SHA-256 `d90d189f88e7431208985e2b128a985a8cb8140db6c7cc071101aaf66046bb44`.

The repair keeps the existing single 10-second read budget and 150-ms interval. Only real UIA `ElementNotAvailableException` and COM `E_FAIL` from read-only observation can discard an entire incomplete list and requery. Each attempt reacquires the same retained native root and verifies its PID, native PID, owner, HWND, role, runtime identity, title, class, enabled and offscreen state. The original process/lifetime check runs before every read. A complete traversal and exact unique target match are required before returning; completing after the original deadline is also rejected. Ambiguous, foreign, changed-identity and other errors stay fatal.

No input method is inside the retry boundary. All input, focus, module, audio, project, recipe, display and cleanup gates remain in place. The first provider exception is retained as the timeout's inner exception. Bounded first/last diagnostics record the actual traversal step, last node, ancestry, visited-node count and error. Secondary diagnostic failures do not replace the primary failure. They are evidence, not readiness signals.

Verification:

- The production polling fixture first failed before implementation. It now proves that matching nodes seen before a traversal failure cannot pass, a fresh complete observation can pass, persistent/alternating failure uses only the original budget, the first error survives timeout, and late completion fails. Ten retained-root mutations and eight fatal/timeout cases pass.
- The complete observer and the production fixture compile for .NET Framework 4.8 / C# 5 with zero warnings or errors. The pure fixture ran in local PowerShell 7; it does not claim Windows UIA execution. The existing Windows 5.1 pre-build self-test now runs the fixture against the actual production exception classifier with a real `ElementNotAvailableException`; that execution is pending Windows.
- All 104 distribution Python tests passed in 79.812 seconds. Existing native pointer/keyboard/filename policy fixtures passed. All distribution PowerShell scripts parsed, and `git diff --check` passed.

Actual Windows must determine whether this is a transient provider boundary or expose a persistent failing node. The change does not claim a completed export workflow or alter a product runtime file.
