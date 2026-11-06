#!/bin/sh
# Licensed under the Apache License, Version 2.0. See LICENSE and NOTICE.
set -eu
umask 022
export LC_ALL=C.UTF-8
mkdir -p /build /out
cd /build

# Exact Debian source; verify all members before extraction or compilation.
for member in openexr_3.1.5-5.dsc openexr_3.1.5.orig.tar.gz openexr_3.1.5.orig.tar.gz.asc openexr_3.1.5-5.debian.tar.xz; do
    curl --fail --silent --show-error --proto '=https' \
        "https://deb.debian.org/debian/pool/main/o/openexr/$member" -o "$member"
done
sha256sum -c <<'HASHES'
86abb11e85a2f651a6d6a84f757ae5d506f34daad74709492b44ab985dd6e3cb  openexr_3.1.5-5.dsc
93925805c1fc4f8162b35f0ae109c4a75344e6decae5a240afdfce25f8a433ec  openexr_3.1.5.orig.tar.gz
a2c4ac5151789903ca8ab3093a2798491463ccf2abfd003a20f96453e505dd5f  openexr_3.1.5.orig.tar.gz.asc
e5f9ac594255c35fac27e12c5b8af5d175c8f5fed90dd5b4530fe3437777d54f  openexr_3.1.5-5.debian.tar.xz
HASHES
dpkg-source -x openexr_3.1.5-5.dsc source
cd source
echo '89a970508b35e352632fb96b67bc67e508bfdf5a140e6a00d933c5896f64e372  src/lib/OpenEXR/ImfIDManifest.cpp' | sha256sum -c
patch --batch --fuzz=0 -p1 < /security/openexr-idmanifest.patch
echo 'c8c278f9c498095f20e9445f6196000cbc69e15ae935cfb934208bc2bbb9e349  src/lib/OpenEXR/ImfIDManifest.cpp' | sha256sum -c

# +0ops sorts below a future +deb vendor release. Preserve Debian packaging,
# headers and SONAME; do not masquerade as an upstream version bump.
python3 - <<'PY'
from pathlib import Path
p=Path('debian/changelog')
p.write_text('''openexr (3.1.5-5+0ops1) bookworm; urgency=high

  * Backport upstream CVE-2026-42216 and CVE-2026-42217 input validation.

 -- OpenServerless ADV build <noreply@invalid.example>  Fri, 06 Nov 2026 00:00:00 +0000

'''+p.read_text())
PY
# Build arch packages only. Documentation-only build dependencies are deliberately
# excluded; Debian's DOCS=OFF path remains unchanged. Tests run separately below.
dpkg-buildpackage -B -d -us -uc -j4
# Debian disables dh_auto_test; run the upstream test for the changed parser.
./build/bin/OpenEXRTest testIDManifest
arch=$(dpkg --print-architecture)
for package in libopenexr-3-1-30 libopenexr-dev; do
    member="/build/${package}_3.1.5-5+0ops1_${arch}.deb"
    test "$(dpkg-deb -f "$member" Version)" = '3.1.5-5+0ops1'
    test "$(dpkg-deb -f "$member" Architecture)" = "$arch"
    cp "$member" /out/
done
cd /out
sha256sum ./*.deb > SHA256SUMS
# Keep exact patch and source identity visible in the final runtime image.
cp /security/openexr-idmanifest.patch .
cp /security/openexr-LICENSE.md .
cp /build/source/debian/changelog ./changelog
printf '%s\n' 'openexr Debian source 3.1.5-5; local binary revision 3.1.5-5+0ops1' \
  'CVE-2026-42216: 48e5f65a7de405e77c74c2a01bd228ef35d18118' \
  'CVE-2026-42217: 21eaa33bcbbb0c83a5fc42f6b6d65b70a996e63c' > SOURCE
