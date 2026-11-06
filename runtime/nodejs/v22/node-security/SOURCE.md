# Bounded Node dependency backports

The build validates the exact original SHA256 of all three files before
modifying any of them. Installed package versions and lockfile remain honest;
`receipt.json` records original and modified bytes. This is not a vendor release.
Original package LICENSE files and copyright notices remain installed.

- stream-json 1.9.1 `Assembler.js`: adapt the upstream own-property write for
  `__proto__` in both ordinary and reviver paths (CVE-2026-104183).
  https://github.com/uhop/stream-json/commit/2f2d35bbb547306991ded6487a279154d865a358
- stream-json 1.9.1 `filters/FilterBase.js`: adapt the upstream `maxDepth`
  guard to the legacy Transform callback contract (CVE-2026-71429). Default
  1024; explicit `Infinity` is available for trusted input as upstream permits.
  Values other than nonnegative safe integers or Infinity are rejected.
  https://github.com/uhop/stream-json/commit/a869fb98aaef9225556f49901a8f55954ff856e6
- nested uuid 3.4.0 `lib/v35.js`: validate an external output buffer range
  before writing through the v3/v5 APIs (CVE-2026-41907); additionally reject
  noninteger offsets. v4 used by short-uuid retains its existing implementation.
  https://github.com/uuidjs/uuid/security/advisories/GHSA-w5hq-g745-h8pq

stream-json and uuid are MIT-licensed. The pinned installed 1.9.1 package has
no JSONC parser/verifier, so CVE-2026-104182's JSONC-specific code is absent.
Plain JSON and JSONL are not evidence of a JSONC entry point.

We preserve stream-json's Node Transform/EventEmitter API required by MinIO and
the legacy uuid/v4 subpath required by short-uuid. Forcing their new major
versions into these dependency contracts would not be a compatible update.
Legitimate filter traversal deeper than 1024 now requires the explicit
trusted-input option. This limit does not bound the plain parser or streamers.

The npm-internal glob/minimatch findings are not changed or suppressed by this
patch. Do not describe this package set as vulnerability-free.
