# ADV runtime native-package security qualification — 2026-11-09

The AMD64 ADV Node 22 runtime removes `openssh-client`: managed actions have no
supported SSH client contract and no runtime source caller requires `ssh`,
`scp` or `sftp`.  The exact-parent overlay is
`Dockerfile.openssh-removal`; the canonical Dockerfile applies the same change.

The Python 3.12 runtime installs the previously qualified SQLite
CVE-2025-7458 and libxml2 CVE-2026-6653 backports from the digest-pinned
`ops-advanced-bookworm-security:20261109-r1` carrier.  Tenant code can import
`sqlite3` and can reach libxml2 through installed XML bindings, so these fixes
are treated as reachable.  The overlay installs runtime libraries only and
retains source, patch, checksum and test receipts under
`/usr/share/ops-security`.

Qualified release identities:

- Node: `ops-advanced-nodejs:22-20261109-no-openssh-r1`, manifest
  `sha256:6681bdf2d99e482f6a699e657c41936c9f835c9ea29db7ca7eb5ba6e9dc0fb1f`.
- Python: `ops-advanced-python:3.12-20261109-native-r1`, manifest
  `sha256:d808617099c9860b20b0f557db2014aa22a6596db934608032f486d47008ebd6`.
- Package carrier: `ops-advanced-bookworm-security:20261109-r1`, manifest
  `sha256:65c238b1d8e0463e350c1bb815fcbd830f175f0991247a6b59b9ca226e39c582`.

The differential contract confirms the exact package delta, unchanged OCI
runtime configuration, clean `dpkg --audit`, functioning Git/Mercurial,
SQLite control and regression vectors, and repeated libxml2 control/rejection
vectors.  Node action-loop smoke and Python source/archive compatibility also
pass.  Trivy 0.76.2 with its database updated at
`2026-11-09T06:57:06Z` still reports custom `+0ops1` versions by Debian package
version; those raw occurrences are retained and are not used as evidence that
the source backports are absent.

