# npm glob/minimatch source backports

These corrections retain npm 11.21.2, glob 13.0.6 and minimatch 10.2.5 rather
than forcing new major dependencies into npm. Installed upstream MIT licenses
are retained unchanged. No vendor version is invented and scanner matches are
not suppressed.

- glob cancellation, CVE-2026-118773:
  <https://github.com/isaacs/node-glob/commit/4682e8c9babee1b385202ede36389634e12076d7>
- minimatch optimization bounds, CVE-2026-118764:
  <https://github.com/isaacs/minimatch/commit/77a0f5c4b80bdc641c3c930a1d9edf5ad2db57f8>

`patches.json` binds all six installed executable copies by their original
SHA256 and exact replacement counts. Four raw CJS/ESM files receive the source
equivalent edits. Both minified glob bundles receive the same edits to their
walker and embedded minimatch implementation. npm's default glob exports point
to those bundles; changing only the raw files would leave the default path
uncorrected. All other bundled bytes and dependencies remain unchanged.
The installed npm package contains no sourcemaps for these modules.

The upstream changes stop traversal after abort while preserving callback
completion, cap level-two pattern splitting at the existing `braceExpandMax`
option, and bypass pairwise deduplication for more than 1000 patterns. Defaults
remain the upstream values: 100000 for minimatch and 10000 when called by glob.
This limits optimization, not the set of paths accepted by a valid pattern.

The installer validates every original file and context before any write and
records original/final hashes in `receipt.json`. A different npm package build
fails closed and requires review. This is a build-time operation; it does not
rewrite application archives or user-bundled dependency copies.

`Dockerfile.lab` qualifies an incremental layer over the pinned prior runtime.
The canonical runtime Dockerfile applies the same installer after npm and the
previous JSON/UUID guards. Debian libraries, Node, native addons, compiler,
launcher and execution-environment compatibility marker are unchanged.
