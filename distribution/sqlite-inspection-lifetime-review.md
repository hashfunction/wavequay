# Close the independent project-inspection connection

Windows run [34691151828](https://github.com/hashfunction/wavequay/actions/runs/34691151828),
public source `80cba72f0e53ae0e196dfafd530cd4ddead56ee8`, failed before its GUI
workflow. Two of 75 Python cases could not remove their temporary
`Dawn-thread.aup4` files: Windows returned `WinError 32` during test cleanup.
No actual consumer workflow ran in that attempt.

The independent inspector and two fixture writers used a SQLite connection as a
context manager. That context controls transactions; it does not close the
connection. This behavior is documented in Python's
[connection-context guide](https://docs.python.org/3/library/sqlite3.html#how-to-use-the-connection-context-manager).
On Windows, the retained open connection prevented the required file cleanup.

The inspector now wraps the real connection in `contextlib.closing`. Its
immutable, read-only URI, all structural checks, error conversion and before/
after file hashes are unchanged. Test writers nest their transaction context
inside `closing`, committing or rolling back before closing the file handle.

A regression retains a strong reference to the actual SQLite connection and
requires subsequent SQL to fail as a closed connection after success, a failed
application-ID check, and a SQLite parse error. All three cases reproduced the
missing close before the production change. With the fix, all 17 focused tests
pass. An independent reviewer reran them and found no issues. No garbage
collection, deletion retry, ignored cleanup error or changed product behavior is
used. A fresh Windows run must establish the full native consumer workflow.

Local logs: `/private/tmp/waveweft-sqlite-close-red.log` and
`/private/tmp/waveweft-sqlite-close-green.log`.
