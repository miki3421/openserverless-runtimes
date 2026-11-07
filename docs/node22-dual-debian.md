# Node 22 Debian runtime variants for ADV

The personal ADV catalog exposes two explicit kinds:

| Kind | Distribution | Native image library | Archive identity |
| --- | --- | --- | --- |
| `nodejs:22` (default) | Debian 12 | ImageMagick 6 | `apacheopenserverless/nodejs-22.23.2` |
| `nodejs:22-trixie` (opt-in) | Debian 13 | ImageMagick 7 | `apacheopenserverless/nodejs-22.23.4-trixie` |

Both use Node 22.23.4, the same common proxy/compiler/launcher, npm 11.21.2,
the same dependency lock and existing decoder, JSON, UUID and npm backports.
The new distribution is not an automatic migration of existing actions.
Select it explicitly in an OPS IDE action's `index.js`:

```javascript
//--kind nodejs:22-trixie
function main(args) { return {hello: args.name}; }
```

Rebuild native dependencies against the selected distribution and regenerate
compiled action archives. An ImageMagick 6 addon cannot be reused with the
ImageMagick 7 runtime. Do not edit an old archive's compatibility marker to
make it load: the distinct marker lets the proxy reject it before execution.
Keep ordinary dependencies in the project's action dependency manifest and use
the existing OPS IDE build/deployment path.

## Narrow Debian 12 correction

The existing Dockerfile retains Debian 12 and all its supported build/media
tools. Its OpenEXR packages are rebuilt as `3.1.5-5+0ops2`. In addition to the
previous IDManifest checks, it carries the full upstream RB-3.1 correction
`df4d77471f2722025011da2e699d581d1e757f6b` for CVE-2023-5841, including the
shared deep-sample validator, unpacking and file-check paths. Public headers
and SONAMEs are not changed. This does not claim to fix every OpenEXR or Debian
finding.

`Dockerfile.trixie` uses a pinned Node/Debian 13 base and Debian OpenEXR
`3.1.13-2`, which already includes the deep-sample vendor correction. It adds
the same two IDManifest checks as local revision `3.1.13-2+0ops1`.
The shared source builder verifies the Debian source inputs and exact patched
files for each distribution; unknown profiles and vendor revisions fail the
build. Receipts, patches and license are installed under
`/usr/share/ops-security/openexr`. These local revisions do not impersonate
new upstream releases and still permit future vendor security updates.

## Build and focused qualification

Use the qualified common proxy image as `COMMON`. From the repository root:

```sh
docker build --build-arg COMMON=localhost/ops-advanced-proxy:20261105 \
  -t local/node22-bookworm runtime/nodejs/v22
docker build --build-arg COMMON=localhost/ops-advanced-proxy:20261105 \
  -f runtime/nodejs/v22/Dockerfile.trixie \
  -t local/node22-trixie runtime/nodejs/v22
```

APT build dependencies are not snapshot repositories: every rebuilt artifact
needs a fresh receipt, compatibility tests and scan. Published image digests
belong in the personal operator's `tools/registry-release/release-images.json`;
the paired task catalog selects the corresponding release tags.

Focused tests are `openexr_deep_samples.cpp`, `openexr_idmanifest.cpp`,
`node22_native_abi.py`, `node22_image_smoke.py`, `node22_legacy_archive.py` and
the existing dependency/decoder/JSON/npm checks. Keep before-patch malformed
input failures and valid controls. The deep-sample test uses the installed
public API with bounded generated files. Its individual-count variant uses
the documented transcode callback to populate its separate buffer; it does
not qualify the default uncompressed individual-count transport path.

For the modern proxy smoke test pass
`--execution-env apacheopenserverless/nodejs-22.23.4-trixie`. For an archive
actually compiled by the modern runtime pass the same value as
`node22_legacy_archive.py --expected-marker`. Use `--expect-incompatible` only
for a deliberately mismatched archive or ImageMagick 6 native addon; this
asserts the specific rejection rather than accepting an arbitrary failure.

`node22_dual_action.js` is a synthetic private OPS IDE fixture. Bind its
namespace/distribution/native ABI/marker using a local `deployment.json` and
compile `probe.node` with the appropriate runtime. Deploy only to explicitly
authorized synthetic tenants; check owner cold/warm invocations and peer 403,
then remove only that fixture package. Follow with application/persistence,
backend isolation, streaming and scheduler acceptance on both tenants.

Qualification is scoped to the AMD64 ADV lab. No baseline change, ARM64,
production, independent review or whole-platform security-clean claim follows
from these source changes. Version-based scanners can continue listing
backported vulnerabilities; retain bound source and executable regression
evidence instead of suppressing results or changing version labels.

Primary references:
[Debian deep-sample advisory](https://security-tracker.debian.org/tracker/CVE-2023-5841),
[upstream maintenance-branch fix](https://github.com/AcademySoftwareFoundation/openexr/commit/df4d77471f2722025011da2e699d581d1e757f6b).
