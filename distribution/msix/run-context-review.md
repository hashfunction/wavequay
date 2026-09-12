# Exact original CI attempt binding

`run_context.py` supplies one fixed repository/source/run/attempt contract for
the native collector, Windows runtime observation, package builder and original
installed start/result records. A record from the same source but another
attempt is rejected. The repository and source are exact; run IDs are canonical
decimal strings and attempts are positive integers. Boolean, missing, extra,
stale and noncanonical fields fail independently during interpretation.

The builder rechecks the native record's context before generating a package;
its verifier rechecks the package's context against the current CI environment.
The CLI native collector additionally requires the original Windows runtime
receipt's same context. Lower-level source observation fixtures retain their
existing APIs; only the actual CLI release route requires this runtime context.
The installer gets the current context before any signing or registration work
and retains it in both original installation records. Its lifecycle, ownership,
cleanup and actual consumer predicates are unchanged.

Validation: three new run-context tests passed with nine invalid environments
and nine missing/stale/type-confused original-context cases. The actual builder
test passed both fixed identities, altered SDK refusal and stale package-attempt
refusal. All five runtime/CMake Python tests passed, including missing/stale
original runtime context. The PowerShell production fixtures passed all 10
installation sequences, nine registration ownership cases, 14 runtime-plan
negatives and existing signature/file/timing mutations. These are local tests;
fresh Windows remains required for actual runtime and installed evidence.
