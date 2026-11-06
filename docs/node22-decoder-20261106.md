# Node 22 decoder compatibility and qualification

This ADV candidate replaces `decode-uri-component` 0.2.2 with the fixed upstream
0.5.1 implementation. It supersedes the pending decoder finding in
[the previous qualification](node22-hardening-20261105.md). Other Node runtime
kinds and action-bundled dependencies are outside this change.

`query-string` 7.1.3 expects `require('decode-uri-component')` to return a
function. Version 0.5.1 is ESM, so a bare npm override breaks this contract.
The build adds a conditional CommonJS export that returns the unchanged ESM
default through Node 22's supported synchronous `require(ESM)`. ESM imports still
use the upstream export. There is no global loader hook or decoder algorithm fork.

The preparation helper validates every locked decoder copy before editing any
package metadata: version, npm integrity, source SHA256, original exports and
existing adapter bytes. Unexpected layouts or contents stop the build. The exact
upstream `index.js` SHA256 is
`6a86ac891edf15c5efa0841ebb31935e3669d58b98318b57d7b08a4530317cb0`.
The npm archive integrity is recorded in the lockfile. LICENSE and NOTICE identify
the upstream version and the adapter.

## Scope and finding

The runtime supplies `query-string.parse`, which can receive untrusted query
text from an action. The old decoder repeats full-string replacements with
quadratic aggregate work. A bounded local reproduction through that real consumer
failed the linear-work bound on the previous image and passed on this candidate.
This is not evidence of a cluster compromise. The inspected MinIO 8.0.7 calls
`query-string.stringify`; a remote MinIO decoding attack was not demonstrated.

References: [upstream advisory](https://github.com/SamVerschueren/decode-uri-component/security/advisories/GHSA-qr28-fpjm-wq7f),
[0.5.1 source](https://github.com/SamVerschueren/decode-uri-component/tree/v0.5.1),
[Node require(ESM)](https://nodejs.org/docs/latest-v22.x/api/modules.html#loading-ecmascript-modules-using-require).

## Image identity

- Candidate: `localhost/ops-advanced-nodejs:22-20261106-decoder-r1`.
- OCI manifest: `sha256:516fcd8d6c585c1bfcc6844541f877b9fa74b6bfc887a296f1bb04295edd223d`.
- OCI config / lab CRI ID: `sha256:a9c4c8ffcf480dca464dfaf9eb49f84981229258923b382d3f337174003c8b70`.
- Previous manifest: `sha256:ada1bf98368f51627edcf715ecf6fa9b54f5137efd3703fafd80b7e56bebc5d6`.
- Common proxy image: `localhost/ops-advanced-proxy:20261105`, manifest
  `sha256:d1817317d421200b1eb119f2b581255477b4f3adeb4fe18cd978475a81058c18`.

Node 22.23.4, npm 11.21.2, proxy/compiler/launcher bytes, execution options and
the `apacheopenserverless/nodejs-22.23.2` archive compatibility marker are
unchanged. Actions continue to run as UID 65534. The manifest-to-config chain
was independently hash-checked against the imported lab image and running pods.
These are imported local images, not public registry releases.

## Focused checks on Linux AMD64

All checks below passed; these counts describe this batch only.

| Check | Result |
| --- | --- |
| Decoder source, CJS/ESM identity, query API, Unicode/malformed input, bounded work and offline MinIO signing | 5 grouped checks |
| Packaging: fresh, idempotent, source drift, old lock, unknown exports, bad nested copy | 6 checks |
| Existing dependency query/signature test | 1 test |
| Actual proxy plain, async, ZIP and compatibility-marker invocations | 8 invocations |
| Archive actually compiled with the previous image, executed on the candidate | 2 invocations |
| ADV owner invocations, peer 403 denials and synthetic action cleanup | 8 checks |
| Alpha/Beta workflow, persistence and authorization | 12 checks |
| Alpha/Beta streaming | 2 checks |

The local bounded work witness counts characters submitted to string replacements,
not wall-clock timing. Distinct encoded runs at input lengths 898/1794/3586
produce old counts 87322/354970/1430810 and new counts 2704/5392/10768. Tests also
cover malformed UTF-8 and a bounded repeated-invalid-byte input. Malformed-input
checks ran only in constrained local containers. Live requests used ordinary
synthetic data and the existing authorized test tenants.

The runtime ConfigMap and guest task catalog agree, controller/invoker rollouts
completed, and invoker health reports 1/1. Completed image-preloader jobs were
checked for exit code zero separately from running-pod readiness. The baseline
installation was not changed.

## Replay

From the repository root, with the exact existing common image available:

```sh
docker build --build-arg COMMON=localhost/ops-advanced-proxy:20261105 \
  -t localhost/ops-advanced-nodejs:22-20261106-decoder-r1 runtime/nodejs/v22
```

The Dockerfile still uses live Debian package repositories. A fresh rebuild is a
new artifact requiring a new scan and qualification; this command does not promise
the historical digest. The recorded build reused the existing OS/proxy layers.

Set `NODE_DECODER_IMAGE` to the selected image and `NODE_DECODER_REPORT_DIR` to a
private evidence directory. Run the tests in order:

```sh
docker run --rm --network none --read-only --tmpfs /tmp:rw,nosuid,size=64m \
  --memory 256m --cpus 1 --cap-drop=ALL --security-opt=no-new-privileges \
  -i --entrypoint node "$NODE_DECODER_IMAGE" < tests/node22_decoder.cjs
docker run --rm --network none --read-only --tmpfs /tmp:rw,nosuid,size=64m \
  --memory 256m --cpus 1 --cap-drop=ALL --security-opt=no-new-privileges \
  -v "$PWD:/src:ro" --entrypoint node "$NODE_DECODER_IMAGE" \
  /src/tests/node22_decoder_packaging.cjs
docker run --rm --network none -i --entrypoint node "$NODE_DECODER_IMAGE" \
  < tests/node22_dependencies.js
python3 tests/node22_image_smoke.py --image "$NODE_DECODER_IMAGE" \
  --report-dir "$NODE_DECODER_REPORT_DIR/smoke"
python3 tests/node22_legacy_archive.py \
  --base-image localhost/ops-advanced-nodejs:22-20261105-r3 \
  --candidate-image "$NODE_DECODER_IMAGE" --report-dir "$NODE_DECODER_REPORT_DIR/legacy"
```

`tests/node22_live.py` requires an explicit protected Alpha/Beta lab configuration
and the local lab API. It creates and deletes its own synthetic actions; run it
only on an authorized lab. Its assertions require ordinary Python execution,
not `python -O`. Application and streaming runners are maintained separately in
the validation application.

## Scanner result and limits

Trivy 0.76.2 scanned both immutable images using the same database, updated
2026-11-06T12:55:02.577403897Z, SHA256
`7520aa80bfb8db4a230514baa510ec6b1d7de9099b74f7879be65450407a6f1f`.
No findings were ignored or suppressed. It removed CVE-2026-118664 (High) and
CVE-2026-45822 (Medium), with no added vulnerability/package/version matches.

Whole-image counts changed from 20 Critical / 476 High / 2008 Medium to
20 Critical / 475 High / 2007 Medium. Debian counts are unchanged; Node package
matches fall from 1 High / 7 Medium to 0 High / 6 Medium. These are scanner
matches, not demonstrated exploitation. The whole image is not vulnerability-free.

No ARM64, fresh-cluster, production, load, full backend write-isolation or
independent review qualification is claimed. Earlier broad Go suite failures
documented in the previous qualification remain separate and were not rerun or
reclassified. This single-agent batch made no Go source changes and verified the
unchanged proxy bytes. Retain the previous local image and private catalog backup
for rollback; the source/catalog branches do not themselves distribute image bytes.
