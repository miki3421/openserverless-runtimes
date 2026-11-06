# Node 22 legacy JSON and UUID dependency guards

This ADV candidate keeps the qualified Debian 12 / Node 22.23.4 runtime and
OpenEXR backport. It changes three installed dependency files, without forcing
new major APIs into the MinIO and short-uuid dependency contracts:

- `stream-json/Assembler.js` writes `__proto__` as an own property, matching
  JSON.parse, in both ordinary and reviver paths (CVE-2026-104183).
- `stream-json/filters/FilterBase.js` bounds path construction before filter
  evaluation, reporting excessive nesting through the stream callback
  (CVE-2026-71429). Default `maxDepth` is 1024; a trusted-input caller can
  explicitly select `Infinity`. Legitimate deeper filtered documents now
  require that explicit option. The plain parser and streamers are unchanged.
- Nested uuid 3.4.0 v3/v5 APIs check buffer bounds before writing
  (CVE-2026-41907). Noninteger offsets are rejected too. UUID v4 used by
  short-uuid and the top-level uuid 14 package remain unchanged.

Canonical source and upstream attribution are in
`runtime/nodejs/v22/node-security/`. All original files are SHA256-checked before
any write. Package versions and the npm lock remain unchanged; the image keeps
the exact before/after receipt and original MIT licenses. No vendor version is
invented. Custom dependencies bundled in individual action archives are not
rewritten or implicitly repaired by this image.

## Qualified image

- Tag: `localhost/ops-advanced-nodejs:22-20261106-json-r2`.
- OCI manifest: `sha256:3ea7a16c3e6bcb69966eb6fda9bf9741bee7279c06a922d942b7c2f71f7d992a`.
- OCI config / CRI ID: `sha256:acce1b51730419be8597781805736a4b6e5ddffe30f6bafa4783311cacc2e175`.
- Prior qualified OpenEXR image manifest:
  `sha256:285f9a66a7f642e3d8f4455be2399b271e5c0a20f879653f495a710d1b29ab29`.

The image is imported on the AMD64 ADV lab, not published to a registry. Only
the Node 22 runtime entry changed. Prior catalog and image are retained for
rollback. Controller/invoker identities and images are unchanged. Baseline
was not modified.

## Evidence

The thirteen bounded local tests in `tests/node22_json_guards.cjs` produce
nine failures and four passes against the prior runtime, and thirteen passes
against the final candidate. Negative tests never contact shared services.
They cover both assembler write paths, all four filter classes, explicit and
default limits, unchanged buffer on rejection, and valid legacy API behavior.

The final image comparison covers 10,224 files: only those three dependency
files differ. The OS package inventory, npm internals, proxy, compiler,
launcher and sampled OpenEXR binary are identical. Other local checks pass:
five decoder, six packaging, one signing/decoding, eight proxy invocations and
two invocations of an archive actually compiled by the previous runtime.

ADV passes eight focused owner/peer/cleanup checks (including normal JSON,
UUID, old native addon and valid EXR/PNG conversion), twelve Alpha/Beta
checks and two streaming checks. Exact runtime image IDs, workload readiness,
catalog agreement and invoker health are verified. These are single-agent
results, not an independent review or ARM64/production qualification.

Preliminary tests launched before image completion and a read-only temporary
directory packaging-harness failure are preserved separately. Corrected
harness runs are recorded; no production code was changed for those failures.

## Remaining scanner findings

Using the same Trivy DB as the OpenEXR qualification, advisory/package/version
findings are unchanged: 20 Critical, 475 High, 2007 Medium. The three source
backports remain version-flagged; none is suppressed. The JSONC-only
CVE-2026-104182 path is absent from the actual stream-json 1.9.1 tree.

The two npm-internal glob/minimatch findings remain open. npm 12.2.2 metadata
still declares glob ^13.0.6 and minimatch ^10.2.5, so updating npm alone is not a
fix. Replacing its internal major dependencies is a separate compiler-toolchain
qualification, not an automatic override. This is not risk acceptance, a claim
of zero vulnerabilities or a correction of other Debian library findings.

The exact upstream references are included in the installed `SOURCE.md`:
[assembler correction](https://github.com/uhop/stream-json/commit/2f2d35bbb547306991ded6487a279154d865a358),
[depth guard](https://github.com/uhop/stream-json/commit/a869fb98aaef9225556f49901a8f55954ff856e6),
[UUID advisory](https://github.com/uuidjs/uuid/security/advisories/GHSA-w5hq-g745-h8pq).
