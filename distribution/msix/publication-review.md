# WaveWeft preferred-source publication binding

The original 40-archive catalog remains byte-identical to the independently
published catalog. The original release manifest maps those exact owner/part,
origin, size and SHA-256 records to the WaveWeft release URLs, retaining the
previous delivery URLs as historical observations. Neither historical record
is rewritten to imply a new application or Windows result.

`source_publication.py` pins the four retained originals before parsing and
independently checks every archive and all 43 anonymous HTTPS asset readbacks,
including exact URLs, sizes, hashes, typed counts and flags, TLS/credential
facts and observation times. Dependency tag commit `753e3cf724ad05e565a6f055921083a5bd090759`
is explicitly separate from the later application source being built.

The parent independently published and anonymously streamed the 43 assets on
2026-09-12: 40 preferred-source archives (254,427,730 bytes), original catalog,
release manifest and source README. The retained readback has SHA-256
`29775e987a9633e0dd9027be3308d8dd0d54eb7f0178eb275748a155e233456f`.

Validation: four Python production-boundary tests replay the real 40/43
publication, reject 22 partial/duplicate/owner/hash/URL/typed-flag/time mutations,
and reject byte changes to each pinned original. Source/license closure stays
false: these records establish exact dependency delivery; current native
ownership, Microsoft terms, current application source and actual installed
consumer qualification still require their separate checks.
