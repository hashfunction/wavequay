# Current preferred-source acquisition and comparison

`source_delivery.py` acquires only the fixed WaveWeft assets named by the
independently verified original publication. It first reuses an exact existing
source cache entry, including the current resolver's owned
`downloads/<component>/<original URL basename>` layout. A changed existing input
fails; it is not silently replaced. Missing sources use anonymous HTTPS, a
fixed-host redirect policy, exact byte/hash limits and exclusive cache creation.
Only the helper's unique incomplete download is removed on failure. No source
archive is executed or extracted into the application tree.

The complete verifier replays all 40 original preferred-source archives, current
consumed recipes and 532 original notices. It then compares every original Qt
source SPDX member with the preferred source, retaining only the already reviewed
explicit metadata exceptions and lossless Windows line-ending form. All five
complete comparisons must equal their original reviewed results. Public source
delivery remains separate from Windows runtime and installed consumer acceptance.

Validation: four new production-boundary tests passed, covering anonymous
download, no-network cache reuse, consumed-cache reuse without copying, changed
cache/source hashes, truncation/size limits, aliases, and foreign or downgraded
HTTP response URLs. All 26 source/archive/catalog/publication tests passed.
The production complete verifier also replayed the existing actual 40 archives,
all 532 original notices and all 47,709 Qt preferred-source members successfully
on macOS in 38.95 seconds. No archive was downloaded or duplicated for that
replay. The complete local result is retained outside the repository as
`/private/tmp/waveweft-corresponding-source/complete-current-source-delivery-proof.json`.
This is a local source proof, not a new Windows build or installed qualification.
