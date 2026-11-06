# ADV npm glob/minimatch corrections

The qualified Debian 12 / Node 22.23.4 image retains npm 11.21.2 and backports
two upstream fixes without changing the compiler, execution-environment
marker, application dependencies or native-library ABI:

- CVE-2026-118773: stop glob directory traversal after AbortSignal cancellation,
  preserving callback completion and stream pause/resume behavior.
- CVE-2026-118764: bound minimatch level-two pattern expansion using the existing
  `braceExpandMax` option and skip quadratic deduplication above 1000 patterns.

The source references, exact original hashes and replacements are under
`runtime/nodejs/v22/npm-security`. Six executable files change: CJS/ESM raw
glob walkers, standalone minimatch implementations and both minified glob
bundles. The bundles include their own matcher and are npm's default glob
exports; patching only the raw modules would be incomplete. Every input is
verified before the first write and the image includes a six-file receipt.
Original MIT licenses and package versions remain unchanged.

## Qualified candidate

- Image: `localhost/ops-advanced-nodejs:22-20261106-npm-r2`.
- OCI manifest:
  `sha256:4e1430540a366c0f750d122afef304d3076d9c237453b8a46e0e9f26aead5ae4`.
- OCI config / CRI ID:
  `sha256:c858b007a2e17c47b5cfa01d0af47b99686d8d56d93ccd61a01dba862490feb8`.
- Parent: `localhost/ops-advanced-nodejs:22-20261106-json-r2` at
  `sha256:3ea7a16c3e6bcb69966eb6fda9bf9741bee7279c06a922d942b7c2f71f7d992a`.

The incremental lab Dockerfile uses this pinned parent. The canonical runtime
Dockerfile invokes the same installer after the existing JSON/UUID guards.
This batch qualifies the incremental image; a fresh complete image build is
still a separate gate because it also resolves operating-system packages.

## Validation

- Bounded local regressions: original 10 PASS / 16 FAIL; candidate 26 PASS.
  Both default bundled and raw imports, CJS and ESM, are exercised. The tests
  cover cancellation, expansion bounds, large pattern sets and normal matching
  and paused/resumed traversal. No stress payload is sent to shared services.
- Three installer tests pass, including drift in the final source or patch
  context with no earlier file mutation and refusal to patch twice.
- Five offline npm workspace/lock/install/list/pack controls pass on both
  images, including negated workspaces and package file selection.
- Eight local proxy invocations and two invocations of an archive actually
  compiled by the previous image pass.
- A 10,223-file inventory proves exactly six dependency files change. The OS
  package inventory and proxy/compiler/launcher hashes are identical. Prior
  OpenEXR, decoder, JSON and UUID backports remain unchanged.
- On ADV, eight owner/peer/cleanup checks verify normal npm behavior and the
  six-file receipt inside real actions; twelve Alpha/Beta checks and two
  streaming checks pass. The catalog and ConfigMap agree. Controller/invoker
  image and StatefulSet identities are preserved. The baseline is unchanged.

Only `nodejs:22` changed in the runtime catalog. All imported manifest, config
and layer bytes were checked before rollout. The previous catalog/image and
private failure logs remain available on ADV for rollback and diagnosis.

## Limits and retained failures

The first live request after restarting controller and invoker returned 503;
the controller logged no available invokers. A later complete run passed.
Kubernetes Ready alone does not prove action execution is available, and this
batch does not qualify a zero-downtime update. The first final-state verifier
also incorrectly required a completed preload Job to be Ready; the corrected
check distinguishes successful completed preload containers from active
runtime containers. Both attempts are retained.

The same Trivy DB still reports 20 Critical, 475 High, 2020 Medium, 1557 Low
and 46 Unknown package matches in both images. All 4118 normalized advisory/
package/version matches are identical, including these two source-backported
findings. No scanner suppression or invented fixed vendor version is used.
Other Debian/JavaScript findings, action-owned dependency copies, ARM64,
Windows matching, complete upstream suites and production acceptance are not
closed by this qualification. Review and validation were single agent.
