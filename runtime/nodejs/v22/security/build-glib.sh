#!/bin/sh
# Licensed under the Apache License, Version 2.0. See LICENSE and NOTICE.
set -eu
umask 022
export LC_ALL=C.UTF-8
mkdir -p /build/glib /out/glib
cd /build/glib
for member in glib2.0_2.74.6-2+deb12u9.dsc glib2.0_2.74.6.orig-unicode-data.tar.xz glib2.0_2.74.6.orig.tar.xz glib2.0_2.74.6-2+deb12u9.debian.tar.xz; do
    curl --fail --silent --show-error --proto '=https' \
      "https://deb.debian.org/debian/pool/main/g/glib2.0/$member" -o "$member"
done
sha256sum -c <<'HASHES'
bd8e8cd8d251c2365a02258bf4d6c44721289ac44c3a2477c140ce253bdb4b41  glib2.0_2.74.6-2+deb12u9.dsc
dabcaff9298aa111a94e580561d2f29371f3e61b356c925ec5e0792df2b11ff2  glib2.0_2.74.6.orig-unicode-data.tar.xz
069cf7e51cd261eb163aaf06c8d1754c6835f31252180aff5814e5afc7757fbc  glib2.0_2.74.6.orig.tar.xz
ccfe76a05463099331f31fc2fde1677ce3c5e0d054112890541b511c0b3321ff  glib2.0_2.74.6-2+deb12u9.debian.tar.xz
HASHES
dpkg-source -x glib2.0_2.74.6-2+deb12u9.dsc source
cd source
echo '0f56750fa95ecbce86f7eff41d946e614b5d69cb4802f4c14ed350fd8babbd67  gio/gdbusintrospection.c' | sha256sum -c
patch --batch --fuzz=0 -p1 < /security/glib-introspection.patch
echo '37268cc2beed92ccd035c09a760a641449ee1dfd6e8c03e8d6a198866b13166b  gio/gdbusintrospection.c' | sha256sum -c
sha256sum gio/gdbusintrospection.c > /out/glib/patched-source.sha256
python3 - <<'PY'
from pathlib import Path
p = Path('debian/changelog')
p.write_text('''glib2.0 (2.74.6-2+deb12u9+0ops1) bookworm; urgency=high

  * Backport upstream c9da977c: reject invalid introspection node nesting
    (CVE-2026-58016), without changing public headers or ABI.

 -- OpenServerless ADV build <noreply@invalid.example>  Sun, 08 Nov 2026 00:00:00 +0000

''' + p.read_text())
PY
# Build architecture packages with Debian's configuration. Installed-test and
# installer packages are excluded; targeted installed-library tests run later.
DEB_BUILD_OPTIONS=nocheck dpkg-buildpackage -B -d -us -uc -j4 -Pnoudeb,noinsttest
arch=$(dpkg --print-architecture)
for package in libglib2.0-0 libglib2.0-bin libglib2.0-dev libglib2.0-dev-bin; do
    member="/build/glib/${package}_2.74.6-2+deb12u9+0ops1_${arch}.deb"
    test "$(dpkg-deb -f "$member" Version)" = '2.74.6-2+deb12u9+0ops1'
    test "$(dpkg-deb -f "$member" Architecture)" = "$arch"
    cp "$member" /out/glib/
done
cp debian/copyright /out/glib/copyright
cp debian/changelog /out/glib/changelog
cp /security/glib-introspection.patch /out/glib/
cp /build/glib/*.dsc /out/glib/
printf '%s\n' 'GLib Debian 2.74.6-2+deb12u9; local revision 2.74.6-2+deb12u9+0ops1' \
  'CVE-2026-58016: c9da977c178fbfc0e4caf99f9fdf5dc433d6fcc2' \
  'libglib2.0-data is unchanged translation data; it contains no GDBus parser.' > /out/glib/SOURCE
cd /out/glib
sha256sum ./*.deb > SHA256SUMS
