#!/bin/sh
# Licensed under the Apache License, Version 2.0. See LICENSE and NOTICE.
set -eu
umask 022
export LC_ALL=C.UTF-8
mkdir -p /build/sqlite /out/sqlite
cd /build/sqlite
for member in sqlite3_3.40.1-2+deb12u2.dsc sqlite3_3.40.1.orig.tar.xz sqlite3_3.40.1.orig-www.tar.xz sqlite3_3.40.1-2+deb12u2.debian.tar.xz; do
    curl --fail --silent --show-error --proto '=https' \
      "https://deb.debian.org/debian/pool/main/s/sqlite3/$member" -o "$member"
done
sha256sum -c <<'HASHES'
ee3459ae9d00939741c7708fc1b8ce1bde12d8c3fb1dfa005bbbc8651d884e23  sqlite3_3.40.1-2+deb12u2.dsc
aaa776260ab4dc976db34aa7891819484c8676b5b2783123ebc6301e2ca5d655  sqlite3_3.40.1.orig.tar.xz
a5e95a18d1b59729278860559ded78751b9163ffb5bb906c5cd24c015f71d5fd  sqlite3_3.40.1.orig-www.tar.xz
0843bc12e4364076477935ce313a6d0796fd899a989ff18ebb6545540e10e4ca  sqlite3_3.40.1-2+deb12u2.debian.tar.xz
HASHES
dpkg-source -x sqlite3_3.40.1-2+deb12u2.dsc source
cd source
echo '7ef061e8cb2d2bcfda2cb7153536f7b47bae055bb6c42e2f7de7e5292e12d991  src/where.c' | sha256sum -c
patch --batch --fuzz=0 -p1 < /security/sqlite-distinct-order.patch
sha256sum src/where.c test/distinct.test > /out/sqlite/patched-source.sha256
python3 - <<'PY'
from pathlib import Path
p = Path('debian/changelog')
p.write_text('''sqlite3 (3.40.1-2+deb12u2+0ops1) bookworm; urgency=high

  * Backport upstream 12ad822d9b827777 DISTINCT / ORDER BY bound
    (CVE-2025-7458), retaining Debian configuration and SQLite ABI.

 -- OpenServerless ADV build <noreply@invalid.example>  Sun, 08 Nov 2026 00:00:00 +0000

''' + p.read_text())
PY
DEB_BUILD_OPTIONS=nocheck dpkg-buildpackage -B -d -us -uc -j4
# Debian's broad build tests are not this qualification. Explicitly execute
# the owning upstream regression suite, including the backported cases.
# The non-amalgamated 3.40 testfixture target lists fts3_term.c twice. Use the
# supported amalgamation target for the test harness only. The installed Debian
# library above remains the normal non-amalgamated build.
make -j4 USE_AMALGAMATION=1 testfixture
./testfixture test/distinct.test > /out/sqlite/distinct-test.log
arch=$(dpkg --print-architecture)
for package in libsqlite3-0 libsqlite3-dev; do
    member="/build/sqlite/${package}_3.40.1-2+deb12u2+0ops1_${arch}.deb"
    test "$(dpkg-deb -f "$member" Version)" = '3.40.1-2+deb12u2+0ops1'
    test "$(dpkg-deb -f "$member" Architecture)" = "$arch"
    cp "$member" /out/sqlite/
done
cp debian/copyright /out/sqlite/copyright
cp debian/changelog /out/sqlite/changelog
cp /security/sqlite-distinct-order.patch /out/sqlite/
cp /build/sqlite/*.dsc /out/sqlite/
printf '%s\n' 'SQLite Debian 3.40.1-2+deb12u2; local revision 3.40.1-2+deb12u2+0ops1' \
  'CVE-2025-7458: 12ad822d9b827777526ca5ed5bf3e678d600294fc9b5c25482dfff2a021328a4' > /out/sqlite/SOURCE
cd /out/sqlite
sha256sum ./*.deb > SHA256SUMS
