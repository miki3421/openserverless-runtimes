# Advanced Python runtimes — 2026-11-05 qualification

The existing Advanced AMD64 laboratory offers two application runtimes:

| Action kind | Interpreter | Default | Compilation identity |
| --- | --- | --- | --- |
| `python:3.12` | 3.12.16 | Yes | Existing `runtime-python-v3.12.14` |
| `python:3.15` | 3.15.2 | No, explicit selection | New `runtime-python-v3.15.2` |
| `python:sys` | 3.12.16 | Internal system runtime | Existing `runtime-python-v3.12.14` |

Select `python:3.15` explicitly as an action's kind. Existing actions retain their kinds. Rebuild source and native dependencies when moving an application from 3.12 to 3.15; changing the kind of a compiled 3.12 archive is not a supported migration. The proxy rejects that archive's compilation identity. The 3.12 patch refresh retains its old identity and was tested with archives genuinely compiled by the previous image.

## Build and dependencies

Build the repository's common proxy Dockerfile first with its pinned Go 1.27.3 builder, then pass that image as `COMMON` when building each `runtime/python/<version>` context. The lab used the existing common proxy artifact `localhost/ops-advanced-proxy:20261105`, manifest `sha256:d1817317d421200b1eb119f2b581255477b4f3adeb4fe18cd978475a81058c18`, from runtime source base `61ee8139eb6e8d2e48d1fc56fbb9f5d4657156d7`.

Python base images are versioned and digest-pinned. The 3.12/sys images use Bookworm; 3.15 uses Trixie to meet the glibc floor of available native wheels. Requirements are exact dependency sets with security floors in requirements.in. Python/compiler libraries are retained rather than removed to lower scanner counts. Debian updates remain repository-dependent; a later rebuild needs its own artifact verification and scan.

The 3.12 changes include certifi 2026.10.23, dnspython 2.9.2, pymongo 4.18.3, urllib3 2.8.0, virtualenv 21.15.5, filelock 4.2.9 and pip 26.3; the full runtime also updates NLTK to 3.10.4. Other runtime libraries remain pinned.

Python 3.15 additionally selects compatible native dependencies: orjson 3.13.0, ormsgpack 1.13.0, pydantic 2.14.3/core 2.50.4, pymongo 4.19.0 and uuid-utils 0.19.0. PyYAML, langdetect and zstandard wheels are built in a separate stage. The runtime installs from that wheel set without network and does not contain GCC. No package is excluded to obtain a passing build.

Compiler and launcher sources remain unchanged. All three builds use the GIL and have no available/enabled JIT. No throughput, cold-start or memory improvement is claimed: those require workload benchmarks. The newer interpreter alone is not proof of a safer container.

## Qualification

Local Docker checks use `tests/python_runtime_compat.py` with explicit image/base/output arguments. They cover source actions, source ZIPs, real compiled archives, bundled virtualenvs, library behavior, repeated invocations, UID 65534, Unicode and rejection of incompatible compilation identities. Virtualenv creation and fixture compilation are tested without network.

- Previous 3.12/sys images: 24 PASS; updated 3.12/sys: 24 PASS.
- New 3.15: 14 PASS, including rejection of an actual 3.12-compiled archive.
- All three installed package sets pass `pip check`.
- ADV: 24 real checks across Alpha/Beta and all three kinds, covering owner invocations, peer 403 denial and synthetic action cleanup.
- Existing Alpha/Beta application/persistence/authentication suite: 12 PASS on updated 3.12. Streaming: 2 PASS.
- Live catalog/default and image manifests/config digests were checked against imported artifacts. Controller/invoker recovered, active pods were ready, and the original images remain available for rollback.

These results do not migrate the entire Alpha/Beta application to 3.15, qualify arbitrary application packages, ARM64, production, a fresh complete cluster install or the full repository suite. Earlier unrelated operator/proxy fixture failures remain open; this batch does not reclassify them.

### python:sys SQLite backport — 2026-11-10

The AMD64 `python:sys` runtime now has a qualified SQLite-only overlay built from the exact `sys-20261105-r1` parent. It installs only `libsqlite3-0` `3.40.1-2+deb12u2+0ops1` from the digest-pinned Bookworm security carrier; `libsqlite3-dev`, libxml2, Python packages, proxy, compiler, launcher, release metadata and OCI runtime configuration are unchanged. The canonical Dockerfile contains the same correction so a normal rebuild does not reintroduce the vulnerable package.

The exact parent reproduced the CVE-2025-7458 DISTINCT/ORDER BY regression and an `EXPLAIN` case exited with signal status 139. The candidate passed all eight SQLite controls/regressions, `dpkg --audit`, `pip check`, system-library linkage checks and 11 runtime compatibility checks covering old compiled archives and old/current bundled virtualenvs. In the private ADV cluster, tenant-selected `python:sys` cold, warm and post-invoker-restart calls all passed as UID 65534. The `whisk-system/nuv/login` smoke, Alpha/Beta health checks, cross-tenant denial and the post-restart invoker health action also passed. The temporary validation action was deleted.

Qualified image: `docker.io/miki3421/ops-advanced-python:sys-20261110-sqlite-r1@sha256:c70050c3fca2254b895014d59ee8777a781e88d0bc3e5265a7ca2dc16ca35485`. It was first imported into the private target node and was published to Docker Hub on 2026-11-10 with the same manifest digest. The prior image and ConfigMap snapshot are retained for rollback. This qualification is AMD64-only because the retained `.deb` is architecture-specific.

The full 33-image Trivy rescan used the same Trivy 0.76.2 database identity as the preceding checkpoint (`UpdatedAt` `2026-11-10T13:03:09.93195248Z`, database SHA256 `c6512d0a28df88bc2d796b48792987f54a3e9a28704b35bb976bfab5460ee706`). Raw totals remain 51 Critical / 1,729 High overall and 3 / 101 for `python:sys`: the advisory feed cannot recognize the local `+0ops1` source backport. Applicability is separate: the SQLite occurrence is remediated, the residual libxml2 occurrence is not applicable to the current managed Python path, and no known applicable Critical remains pending.

The runtime ConfigMap watcher initially restarted Controller and Invoker but could not recreate the completed preload job because the prior operator image lacked the runtime deployment assets. The follow-up operator `20261110-preloader-r2@sha256:50563fce3d60a5ed338d0db99de7042cc893380840b685493c749486ec30ec93` packages those assets, deletes the fixed-name job without depending on mutable render state and propagates reconcile failures. A live metadata-only ConfigMap update recreated and completed the job with this `python:sys` image; Controller/Invoker returned Ready and a temporary `python:sys` action passed before cleanup.

## Scanner results

Trivy 0.76.2, same database for all images (updated 2026-11-05T19:01:45Z, SHA256 `2ce29bda5b2483d84da3f4365398addcf03a7decf5c79e29dc73db8f0fa454ed`), no exclusions. Counts are unique advisory/package/installed-version tuples per image, not demonstrated exploitable paths.

| Image | Critical | High |
| --- | ---: | ---: |
| Previous Python 3.12 | 9 | 138 |
| Updated Python 3.12 | 3 | 57 |
| Previous python:sys | 9 | 136 |
| Updated python:sys | 3 | 57 |
| New Python 3.15 | 1 | 80 |

All candidates have zero Critical/High Go-proxy matches. One Python High remains in pip's vendored setuptools 70.3.0 metadata (CVE-2025-47273); other remaining Critical/High findings are in Debian packages. They are retained, not suppressed. The 3.15 base is a different Debian release, so these counts do not isolate interpreter security. Vulnerability reachability was not established by this scan.

## Artifacts and rollback

| Local image | OCI manifest |
| --- | --- |
| `localhost/ops-advanced-python:3.12-20261105-r1` | `sha256:1b935970f83b0cf15c9e0d807f830e653f25c7d87ef26182cc41f9fa3447c011` |
| `localhost/ops-advanced-python:sys-20261105-r1` | `sha256:a457cce7c40888898c98dcf8709bff77d3470f6ec10474536e633912404dc412` |
| `localhost/ops-advanced-python:3.15-20261105-r1` | `sha256:e60c0ff5ee71471003a58a046e93fab1e75d66702ae63791d01c299b66ad96e9` |

The task catalog selects these local images; distribution requires explicit publication/import. No push or PR occurred. Baseline was unchanged.

Raw tests, scanner reports, pre-change catalog/ConfigMap and image proofs remain outside Git. Initial evidence includes the 3.15 build failing without native build tooling, a test attempted before its image build finished, and a negative fixture initially expecting rejection during run instead of init. Those attempts are not counted as successful tests. An initial live-readiness wrapper returned nonzero without preserving its detailed stderr; subsequent retained read-only checks passed.

Rollback restores the previous catalog and live ConfigMap together and restarts controller/invoker after ensuring the old images remain present. Remove the new kind only after confirming no actions reference it. No datastore formats or tenant credentials were changed.

References: [Python 3.12.16](https://www.python.org/downloads/release/python-31216/), [Python 3.15.2](https://www.python.org/downloads/release/python-3152/), [Python support status](https://devguide.python.org/versions/).
