# Node 22: Debian 12 OpenEXR backport

This historical qualification is followed by the separately selected
[dual Debian runtime contract](node22-dual-debian.md). The newer contract
retains the compatible default and adds an explicit Debian 13 opt-in kind.

This ADV image keeps Node 22.23.4, Debian 12, ImageMagick 6, the common proxy,
compiler/launcher, npm lock and the existing archive compatibility marker.
It rebuilds the Debian OpenEXR source `3.1.5-5` with two upstream IDManifest
input checks as local package revision `3.1.5-5+0ops1`:

- CVE-2026-42216: check the encoded string contains its one/two-byte prefix
  before indexing it; upstream commit `48e5f65a7de405e77c74c2a01bd228ef35d18118`.
- CVE-2026-42217: reject a variable-length integer requiring a shift of 64 or
  more bits before performing that shift; upstream commit
  `21eaa33bcbbb0c83a5fc42f6b6d65b70a996e63c`.

Both raw and compressed IDManifest constructors use the shared parser. This is
a narrow source backport, not a claim that all OpenEXR vulnerabilities are fixed.
CVE-2023-5841 and the other library findings remain outside this patch.
All four Debian source files and the original/patched C++ file are SHA256-bound.
The patch applies without fuzz. Runtime and development packages are installed
together, with their source/patch/license receipt under
`/usr/share/ops-security/openexr`. The `+0ops1` revision sorts below a future
official `+deb...` revision. Unexpected vendor revisions stop the build.

## Compatibility decision

A prior isolated Debian 13 candidate passed plain JavaScript tests but could
not load a real synthetic Node addon previously compiled against
`libMagickWand-6.Q16.so.6`. Debian 13 provides ImageMagick 7. That candidate was
rejected and never deployed on ADV. The operator selected targeted Debian 12
corrections. No new runtime kind or silent distribution upgrade is introduced.

## Exact qualified artifact

- Image: `localhost/ops-advanced-nodejs:22-20261106-openexr-r2`.
- OCI manifest: `sha256:285f9a66a7f642e3d8f4455be2399b271e5c0a20f879653f495a710d1b29ab29`.
- OCI configuration / CRI ID: `sha256:4112ec7968528a231afd3d0eb273f92f33c4e84632919e14b3b12f8ca4b0ab9c`.
- Prior decoder image manifest: `sha256:516fcd8d6c585c1bfcc6844541f877b9fa74b6bfc887a296f1bb04295edd223d`.

This image is imported into the AMD64 ADV lab, not published to a registry.
Only `nodejs:22` changed in the runtime catalog. Controller and invoker workload
UIDs and images are retained; their restart refreshes the runtime catalog.
The paired task catalog also retains the separately qualified activation
retention operator; it must not revert to the older operator pin.

## Verification

Single agent, bounded local malformed-input tests and ordinary synthetic lab
actions only. No malformed OpenEXR input was sent to shared services.

| Check | Result |
| --- | --- |
| Installed-library public API, before patch | Five malformed-input failures; three existing valid/truncation controls pass |
| Same eight cases, final image | Eight pass, including overlong encodings, both prefix widths, valid serialized/compressed round trips |
| Upstream `OpenEXRTest testIDManifest` during final build | Pass; explicitly run because Debian disables `dh_auto_test` |
| Public headers | 139 unchanged |
| Compared library SONAMEs and exported symbols | Unchanged across six OpenEXR/Imath-family libraries |
| Debian package inventory | Only OpenEXR runtime/dev revisions change |
| Old compiled native addon | Loads on prior and candidate images as UID 65534, using ImageMagick 6 |
| Decoder regression / packaging / dependency checks | 5 / 6 / 1 pass |
| Proxy plain, async, ZIP and compatibility-marker invocations | 8 pass |
| Archive actually compiled using prior image | 2 pass on candidate |
| ADV owner, peer denial and cleanup | 8 pass; owner actions also load the old native addon and convert valid EXR to PNG |
| Alpha/Beta application, persistence and API isolation | 12 pass |
| Streaming delivery | 2 pass |

The installed candidate image chain, ready runtime pods, matching guest/catalog
configuration and invoker health (`1/1`) were verified. Source and regression
tests are in `runtime/nodejs/v22/security/` and `tests/openexr_idmanifest.cpp`,
`tests/node22_native_abi.py`, and the extended `tests/node22_live.py`.

## Scanner and qualification limits

The same Trivy database was used before/after: SHA256
`7520aa80bfb8db4a230514baa510ec6b1d7de9099b74f7879be65450407a6f1f`,
updated 2026-11-06T12:55:02.577403897Z. No exclusions, suppressions or forged
version bumps were used. Version-based Debian reporting still lists the two
backported CVEs; the proof of correction is the bound source and actual parser
execution, not disappearance from the scanner.

The counts remain 20 Critical / 475 High / 2007 Medium across the image:
Debian contributes 2001 Medium and Node packages six Medium. Other Debian and
OpenEXR findings remain open. No whole-library or whole-platform clean claim,
ARM64, production, full fresh-install, load, or independent-review qualification
is made. Earlier Go and other broad-suite failures retain their existing status.

The Debian 13 rejection and failed preliminary harness attempts are preserved
separately from final results. The original native-addon control proves the
rejection was a compatibility failure, not a broken fixture. Current and prior
qualified images/catalog receipts remain available for reviewed rollback.

## Rebuild

Use the normal Node 22 Dockerfile with the same qualified common proxy:

```sh
docker build --build-arg COMMON=localhost/ops-advanced-proxy:20261105 \
  -t localhost/ops-advanced-nodejs:22-20261106-openexr-r2 runtime/nodejs/v22
```

The source packages are pinned, but apt repositories and build packaging can
change; a rebuild is a new artifact requiring verification and a fresh scan.
Replay the decoder/proxy checks documented in `node22-decoder-20261106.md`,
then compile/run `tests/openexr_idmanifest.cpp` against the installed library.
`tests/node22_native_abi.py` accepts `--base`, `--candidate`, `--output`, and an
optional `--addon-output` for the synthetic previously compiled module.

Primary references: [prefix advisory](https://security-tracker.debian.org/tracker/CVE-2026-42216),
[integer advisory](https://security-tracker.debian.org/tracker/CVE-2026-42217),
[prefix fix](https://github.com/AcademySoftwareFoundation/openexr/commit/48e5f65a7de405e77c74c2a01bd228ef35d18118),
[integer fix](https://github.com/AcademySoftwareFoundation/openexr/commit/21eaa33bcbbb0c83a5fc42f6b6d65b70a996e63c).
