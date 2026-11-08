#!/bin/sh
# Licensed under the Apache License, Version 2.0. See LICENSE and NOTICE.
set -eu
umask 022
export LC_ALL=C.UTF-8
mkdir -p /build/aom /out/aom
cd /build/aom
curl --fail --silent --show-error --proto '=https' \
  'https://deb.debian.org/debian/pool/main/a/aom/aom_3.12.1-1%2Bdeb13u1.dsc' \
  -o aom_3.12.1-1+deb13u1.dsc
curl --fail --silent --show-error --proto '=https' \
  https://deb.debian.org/debian/pool/main/a/aom/aom_3.12.1.orig.tar.gz \
  -o aom_3.12.1.orig.tar.gz
curl --fail --silent --show-error --proto '=https' \
  'https://deb.debian.org/debian/pool/main/a/aom/aom_3.12.1-1%2Bdeb13u1.debian.tar.xz' \
  -o aom_3.12.1-1+deb13u1.debian.tar.xz
sha256sum -c <<'HASHES'
796b09717499ced9d82820fad950a31532d7c193a2a764617df05c9aa68090cb  aom_3.12.1-1+deb13u1.dsc
40c929a41b2a59c24319a699c358351422829b3ae646de31b18cbabed0191962  aom_3.12.1.orig.tar.gz
e94efe3356d69b0056dd95746f3cf29551130766b3f3503365e40e9d1c8f8ee7  aom_3.12.1-1+deb13u1.debian.tar.xz
HASHES
dpkg-source -x aom_3.12.1-1+deb13u1.dsc source
cd source
# Debian 13 links tools against its newer system libwebm. Bookworm's version
# predates that package contract, so retain the source-bundled libwebm used by
# upstream. It is not linked into libaom.so and does not alter its public ABI.
echo '42c8da5c2410d0b0b481e519e4ef131cffee5f4306902920edd998431f02f13a  CMakeLists.txt' | sha256sum -c
patch --batch --fuzz=0 -R -p1 < debian/patches/0003-use-system-libwebm.patch
echo 'e2ce0677526b986aef4d93a24db346f99bef6976b3df72c690bdf35dd0de8f82  aom/exports_com' | sha256sum -c
patch --batch --fuzz=0 -p1 < /security/aom-bookworm-abi.patch
python3 - <<'PY'
from pathlib import Path
p = Path('debian/control')
p.write_text(p.read_text().replace(' libwebm-dev (>= 1.0.0.30-2~),\n', ''))
p = Path('debian/rules')
p.write_text(p.read_text().replace('\trm -rf $(CURDIR)/third_party/libwebm\n', ''))
p = Path('debian/changelog')
p.write_text('''aom (3.12.1-1+deb13u1~bpo12+0ops1) bookworm; urgency=high

  * Rebuild Debian's fixed 3.12.1 source for the Bookworm runtime.
  * Retain upstream's bundled libwebm for tools because Bookworm does not
    provide Debian 13's required system libwebm; libaom3 remains independent.

 -- OpenServerless ADV build <noreply@invalid.example>  Sun, 08 Nov 2026 00:00:00 +0000

''' + p.read_text())
PY
sha256sum CMakeLists.txt common/webmdec.cc common/webmenc.cc test/test.cmake \
  aom/exports_com aom/exports_enc av1/exports_com av1/exports_dec \
  debian/rules debian/control \
  > /out/aom/bookworm-source.sha256
DEB_BUILD_OPTIONS=nocheck DEB_BUILD_PROFILES=nocheck \
  dpkg-buildpackage -B -us -uc -j4

# Execute only the owning upstream regression. The broad suite is intentionally
# excluded because its generic runner downloads external test data.
cmake -S . -B build-regression \
  -DCMAKE_BUILD_TYPE=Release -DENABLE_TESTS=1 -DCONFIG_LIBYUV=0 \
  -DCONFIG_MULTITHREAD=1 -DAOM_TARGET_CPU="$(dpkg-architecture -qDEB_HOST_ARCH_CPU | sed 's/amd64/x86_64/')"
cmake --build build-regression --target test_libaom -j4
build-regression/test_libaom \
  --gtest_filter='ResizeSimpleTest.TemporarySmallerFrameSizeMultiThread*' \
  > /out/aom/resize-regression.log
arch=$(dpkg --print-architecture)
member="/build/aom/libaom3_3.12.1-1+deb13u1~bpo12+0ops1_${arch}.deb"
test "$(dpkg-deb -f "$member" Version)" = '3.12.1-1+deb13u1~bpo12+0ops1'
test "$(dpkg-deb -f "$member" Architecture)" = "$arch"
cp "$member" /out/aom/
cp debian/copyright debian/changelog /out/aom/
cp /security/aom-bookworm-abi.patch /out/aom/
cp /build/aom/*.dsc /out/aom/
printf '%s\n' \
  'AOM Debian 3.12.1-1+deb13u1 rebuilt on Bookworm as 3.12.1-1+deb13u1~bpo12+0ops1.' \
  'Debian records CVE-2023-6879 fixed in 3.12.1-1+deb13u1.' \
  'The libwebm packaging adaptation affects tools only; libaom3 retains SONAME 3.' \
  'Bookworm 3.6 exports remain visible for existing native consumers.' \
  > /out/aom/SOURCE
cd /out/aom
sha256sum ./*.deb > SHA256SUMS
