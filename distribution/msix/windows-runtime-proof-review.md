# Independent Microsoft runtime receipt interpretation

The native CLI collector now requires the already configured Windows observer
receipt and independently rederives its exact nine allowed origins from the
original CMake configuration. It checks all nine current payload byte records,
the exact source revision, typed counts/flags, observed Microsoft signature and
version metadata, and stable original configuration/receipt files. The stage
inventory must remain unchanged across all native archive observations.

This Python interpretation does not perform Authenticode verification on macOS
or fabricate it from filenames. `windows-runtimes.ps1` remains the actual Windows
signature/original-file observer. The receipt preserves its complete signature
facts and is bound by exact size/hash. The previous prefix-only unresolved list
remains intact as that narrower collector's observation; separate exact origin
records will be consumed by the complete source gate.

Validation: four Python production-boundary cases passed, with 23 stale, partial,
foreign/debug origin, signature, payload, SDK, duplicate and typed-field
mutations, plus changed original configuration bytes. These are local fixtures;
all nine actual configured Windows origins/signatures remain pending. No source,
license, installed consumer or public release approval is claimed here.
