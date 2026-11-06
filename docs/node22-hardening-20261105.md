# Advanced Node.js22 image qualification

The pending decoder finding below is superseded by the separate
[2026-11-06 decoder qualification](node22-decoder-20261106.md). This document
retains the original image's results and limitations.

This personal-branch candidate updates Node22.23.2 to22.23.4, npm to11.21.2,
the proxy compiler to pinned Go1.27.3, Debian packages and crypto-js4.2.0.
Use npm ci with the existing dependency lock. Other runtime kinds are unchanged.
The old OW_EXECUTION_ENV marker is intentionally retained: a security patch must
not invalidate already compiled compatible action ZIPs. process.version reports
22.23.4. Build tools, npm, ImageMagick and GraphicsMagick remain available.

An attempted decode-uri-component0.5.1 override changed the CommonJS contract and
was rejected by an actual action. It is absent from the accepted candidate.
The existing query-string decoder remains a tracked High finding pending a
compatible upstream fix or separately reviewed backport. No finding is suppressed.

Validation:8 local invocations across plain,async,ZIP and old compiled ZIP cases;
query decoding and AWS4 HMAC signing against Node crypto;9 preinstalled libraries;
4 real owner invocations plus2 peer403 checks and2 cleanups; Alpha/Beta12 checks
and streaming2 checks. All passed on the Advanced AMD64 K3s lab. No baseline change.
Use tests/node22_image_smoke.py --image IMAGE --report-dir PRIVATE_DIRECTORY;
run tests/node22_dependencies.js via docker run --rm --network none -i
--entrypoint node IMAGE, supplying the JS on stdin. Synthetic fixtures only.

Trivy0.76.2, identical DB SHA256
080e48d771bffedd68b73c5856c20a0d69793cf9594d9ed57348dd9df6db0a03:
per-image advisory/package/version matches fell from52Critical/830High to
20Critical/469High. Most residual matches are OS/tool libraries; not demonstrated
exploitation. Third-party dependency matches remain, and the complete image is
not vulnerability-free. The rebuilt proxy has no reported vulnerability matches.

The broad go test ./... command includes unbuildable action launcher fixtures and
an empty withreqs test file. The openwhisk package reports34PASS/3FAIL; the three
extractor fixture failures and four broad build/setup failures also reproduce on
the unchanged base using the same Go toolchain. Preserve these limitations; no
whole-suite-green claim. No ARM64 execution or independent review is claimed.

Candidate image localhost/ops-advanced-nodejs:22-20261105-r3,
manifest sha256:ada1bf98368f51627edcf715ecf6fa9b54f5137efd3703fafd80b7e56bebc5d6.
No remote publication. Local image pins require importing the exact artifacts;
they cannot be pulled from a public registry. Pin Node in the runtime catalog and
restart controller/invoker; wait for an actual health activation, not only pod TCP
readiness, before acceptance. Preserve original image/catalog for rollback.
