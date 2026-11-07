#!/bin/sh
# Licensed under the Apache License, Version 2.0. See LICENSE and NOTICE.
set -eu
umask 022
export LC_ALL=C.UTF-8
mkdir -p /build /out
cd /build

profile=${1:-bookworm}
case "$profile" in
bookworm) source_version=3.1.5-5; upstream=3.1.5; revision=3.1.5-5+0ops2 ;;
trixie) source_version=3.1.13-2; upstream=3.1.13; revision=3.1.13-2+0ops1 ;;
*) echo 'Unsupported OpenEXR source profile' >&2; exit 1 ;;
esac

# Exact Debian source; verify all members before extraction or compilation.
for member in "openexr_${source_version}.dsc" "openexr_${upstream}.orig.tar.gz" "openexr_${source_version}.debian.tar.xz"; do
    curl --fail --silent --show-error --proto '=https' \
        "https://deb.debian.org/debian/pool/main/o/openexr/$member" -o "$member"
done
if [ "$profile" = bookworm ]; then
curl --fail --silent --show-error --proto '=https' \
    https://deb.debian.org/debian/pool/main/o/openexr/openexr_3.1.5.orig.tar.gz.asc \
    -o openexr_3.1.5.orig.tar.gz.asc
sha256sum -c <<'HASHES'
86abb11e85a2f651a6d6a84f757ae5d506f34daad74709492b44ab985dd6e3cb  openexr_3.1.5-5.dsc
93925805c1fc4f8162b35f0ae109c4a75344e6decae5a240afdfce25f8a433ec  openexr_3.1.5.orig.tar.gz
a2c4ac5151789903ca8ab3093a2798491463ccf2abfd003a20f96453e505dd5f  openexr_3.1.5.orig.tar.gz.asc
e5f9ac594255c35fac27e12c5b8af5d175c8f5fed90dd5b4530fe3437777d54f  openexr_3.1.5-5.debian.tar.xz
HASHES
else
sha256sum -c <<'HASHES'
a44f8572a8018ce8b51a35fd2e8a90492b2358b434b8e2beba66f4dd6dd944f8  openexr_3.1.13-2.dsc
26d265d8cf8df4dad115b066ba209118ca8832cda076ec704ce1a57f827c75c6  openexr_3.1.13.orig.tar.gz
5e0e5768b1577dd604bb410666d3420566ac1f8858e69a234633259c3efb52a3  openexr_3.1.13-2.debian.tar.xz
HASHES
fi
dpkg-source -x "openexr_${source_version}.dsc" source
cd source
if [ "$profile" = bookworm ]; then
echo '89a970508b35e352632fb96b67bc67e508bfdf5a140e6a00d933c5896f64e372  src/lib/OpenEXR/ImfIDManifest.cpp' | sha256sum -c
patch --batch --fuzz=0 -p1 < /security/openexr-deep.patch
fi
patch --batch --fuzz=0 -p1 < /security/openexr-idmanifest.patch
if [ "$profile" = bookworm ]; then
echo 'c8c278f9c498095f20e9445f6196000cbc69e15ae935cfb934208bc2bbb9e349  src/lib/OpenEXR/ImfIDManifest.cpp' | sha256sum -c
sha256sum -c <<'HASHES'
b5b21f07559c0abd4ff981cbb80a689f3a56a096c61b63f5f14c576b41bca143  src/lib/OpenEXRCore/decoding.c
7c6ac00d1b27efe7cfa56f848a20e29e5bc6881a27d90469498e4798365d84dc  src/lib/OpenEXRCore/unpack.c
d6eb217e022c753a76b63447bcc4d51430a29c7be87484774a57e1d1da954eb5  src/lib/OpenEXRUtil/ImfCheckFile.cpp
HASHES
else
sha256sum -c <<'HASHES'
41972bfdf1b7316c6c216358662f2603a68f629fca052481d9d5f7fd0938378f  src/lib/OpenEXR/ImfIDManifest.cpp
5fab738adf28d7c38a8979bb155d6ce7a0830b7ca8e9f856135ac1a542ece014  src/lib/OpenEXRCore/decoding.c
77f2e6204045d98cdb08416ef66d1124859c587e21a054ee4448a9250753527f  src/lib/OpenEXRCore/unpack.c
fbb31b6914774838afe0f5c1676c43fff74f5e1dd716e7ce2f4c2a1ae8e8a022  src/lib/OpenEXRUtil/ImfCheckFile.cpp
HASHES
fi

# +0ops sorts below a future +deb vendor release. Preserve Debian packaging,
# headers and SONAME; do not masquerade as an upstream version bump.
python3 - "$revision" "$profile" <<'PY'
from pathlib import Path
import sys
p=Path('debian/changelog')
p.write_text('''openexr (%s) %s; urgency=high

  * Backport upstream CVE-2026-42216 and CVE-2026-42217 input validation.
  * On bookworm, also backport CVE-2023-5841 deep sample validation.

 -- OpenServerless ADV build <noreply@invalid.example>  Sat, 07 Nov 2026 00:00:00 +0000

''' % (sys.argv[1], sys.argv[2])+p.read_text())
PY
# Build arch packages only. Documentation-only build dependencies are deliberately
# excluded; Debian's DOCS=OFF path remains unchanged. Tests run separately below.
dpkg-buildpackage -B -d -us -uc -j4
# Debian disables dh_auto_test; run the upstream test for the changed parser.
./build/bin/OpenEXRTest testIDManifest
arch=$(dpkg --print-architecture)
for package in libopenexr-3-1-30 libopenexr-dev; do
    member="/build/${package}_${revision}_${arch}.deb"
    test "$(dpkg-deb -f "$member" Version)" = "$revision"
    test "$(dpkg-deb -f "$member" Architecture)" = "$arch"
    cp "$member" /out/
done
cd /out
sha256sum ./*.deb > SHA256SUMS
# Keep exact patch and source identity visible in the final runtime image.
cp /security/openexr-idmanifest.patch .
cp /security/openexr-deep.patch .
cp /security/openexr-LICENSE.md .
cp /build/source/debian/changelog ./changelog
printf '%s\n' "openexr Debian source ${source_version}; local binary revision ${revision}" \
  'CVE-2023-5841: bookworm backport df4d77471f2722025011da2e699d581d1e757f6b; trixie vendor fix' \
  'CVE-2026-42216: 48e5f65a7de405e77c74c2a01bd228ef35d18118' \
  'CVE-2026-42217: 21eaa33bcbbb0c83a5fc42f6b6d65b70a996e63c' > SOURCE
