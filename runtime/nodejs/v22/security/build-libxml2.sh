#!/bin/sh
# Licensed under the Apache License, Version 2.0. See LICENSE and NOTICE.
set -eu
umask 022
export LC_ALL=C.UTF-8

source_version='2.9.14+dfsg-1.3~deb12u6'
revision='2.9.14+dfsg-1.3~deb12u6+0ops1'
mkdir -p /build/libxml2 /out/libxml2
cd /build/libxml2

for member in \
    "libxml2_${source_version}.dsc" \
    'libxml2_2.9.14+dfsg.orig.tar.xz' \
    "libxml2_${source_version}.debian.tar.xz"; do
    curl --fail --silent --show-error --proto '=https' \
      "https://deb.debian.org/debian/pool/main/libx/libxml2/$member" \
      -o "$member"
done
sha256sum -c <<'HASHES'
d86ce3efb1b75d2781f72f5cdd187474c148a915d610295c85162681bb070a65  libxml2_2.9.14+dfsg-1.3~deb12u6.dsc
4fe913dec8b1ab89d13b489b419a8203176ea39e931eaa0d25b17eafb9c279e9  libxml2_2.9.14+dfsg.orig.tar.xz
f33a99a0018cbb94aadc3bf26661e401cb90dff856aa170faf7239151ee9b9ac  libxml2_2.9.14+dfsg-1.3~deb12u6.debian.tar.xz
HASHES

dpkg-source -x "libxml2_${source_version}.dsc" source
cd source
echo '8465758face958ddab5ed16adcd02a0225f02c01a8707940c9e10dbac07fc815  parser.c' | sha256sum -c
patch --batch --fuzz=0 -p1 < /security/libxml2-cve-2026-6653.patch
echo '2bd24cfd120751a18072f9f6fb1209b8c3f69c511f33bad4979252b30136ddf5  parser.c' | sha256sum -c
sha256sum parser.c > /out/libxml2/patched-source.sha256

python3 - "$revision" <<'PY'
from pathlib import Path
import sys

p = Path('debian/changelog')
p.write_text('''libxml2 (%s) bookworm; urgency=high

  * Stop parameter-entity parsing after recursive expansion accounting halts
    the parser (CVE-2026-6653), retaining Bookworm headers and public ABI.

 -- OpenServerless ADV build <noreply@invalid.example>  Sun, 08 Nov 2026 00:00:00 +0000

''' % sys.argv[1] + p.read_text())
PY

# Preserve Debian's build configuration.  The explicit upstream suite below is
# retained as evidence instead of allowing its output to disappear in the
# package build log.
DEB_BUILD_OPTIONS=nocheck DEB_BUILD_PROFILES=nopython \
  dpkg-buildpackage -B -d -us -uc -j4 -Pnopython

# Debian's DFSG source archive omits most upstream fixture corpora, including
# test/threads, although the 2.9.14 runtest binary still registers those
# groups.  Run the complete verbose runner and accept only the thread group's
# fixture-absence error; any additional error or leak remains fatal.  Then run
# the remaining self-contained test binaries which the makefile's && chain
# would otherwise skip, and compile (but do not claim to execute) the fuzzer.
make -C builddir/main \
  all runtest testrecurse testapi testcatalog testchar testdict runxmlconf \
  > /out/libxml2/test-build.log 2>&1
make -C builddir/main/fuzz testFuzzer >> /out/libxml2/test-build.log 2>&1
test ! -e test/threads
(
  cd builddir/main
  test -e test || ln -s ../../test test
  test -e result || ln -s ../../result result
  set +e
  ./runtest -v > /out/libxml2/runtest.log 2>&1
  runtest_status=$?
  set -e
  test "$runtest_status" -eq 1
)
grep -Fqx 'Total 508 tests, 1 errors, 0 leaks' /out/libxml2/runtest.log
test "$(grep -Ec '^Ran [0-9]+ tests, [1-9][0-9]* errors, [0-9]+ leaks$' /out/libxml2/runtest.log)" -eq 1
awk '/^## Catalog and Threads regression tests$/ { section = 1 } section' \
  /out/libxml2/runtest.log | \
  grep -Eq '^Ran [0-9]+ tests, 1 errors, 0 leaks$'
(
  cd builddir/main
  ./testrecurse
  ASAN_OPTIONS="${ASAN_OPTIONS:-}:detect_leaks=0" ./testapi
  ./testchar
  ./testdict
  ./runxmlconf
) > /out/libxml2/remaining-tests.log 2>&1
grep -Fqx 'Total: 1164 functions, 280912 tests, 0 errors' \
  /out/libxml2/remaining-tests.log
grep -Fqx 'dictionary tests succeeded 20000 strings' \
  /out/libxml2/remaining-tests.log
cat > /out/libxml2/test-summary.txt <<'EOF'
PASS: testapi completed 280912 API tests across 1164 functions with 0 errors.
PASS: recursive, character-range and dictionary tests completed; fuzzer harness compiled.
LIMITATION: Debian's DFSG source omits upstream fixture corpora, including test/threads, fuzz seeds and the XML conformance archive.
EXPECTED: runtest reports only the Catalog and Threads fixture-absence error; no leak or additional error is accepted.
SECURITY REGRESSION: the exact public CVE-2026-6653 reproducer is exercised by tests/node22_libxml2_package_contract.py.
EOF

arch=$(dpkg --print-architecture)
for package in libxml2 libxml2-dev; do
    member="/build/libxml2/${package}_${revision}_${arch}.deb"
    test "$(dpkg-deb -f "$member" Version)" = "$revision"
    test "$(dpkg-deb -f "$member" Architecture)" = "$arch"
    cp "$member" /out/libxml2/
done
cp debian/copyright debian/changelog /out/libxml2/
cp /security/libxml2-cve-2026-6653.patch /out/libxml2/
cp /build/libxml2/*.dsc /out/libxml2/
printf '%s\n' \
  "libxml2 Debian ${source_version}; local binary revision ${revision}." \
  'CVE-2026-6653: halt-state guards backported without public layout changes.' \
  'Upstream 463bbeeca1805b5c4828f50d0fefc4eebaf620df was reviewed but not copied because it changes public structure layouts in this older ABI.' \
  'Tests: testapi completed 280912 cases without errors; recursive, character-range and dictionary tests passed; the fuzzer harness compiled. Debian DFSG omits upstream fixture corpora, so fixture-dependent runner/fuzzer/conformance coverage is explicitly limited. The exact CVE reproducer is exercised by the image package-contract test.' \
  > /out/libxml2/SOURCE
cd /out/libxml2
sha256sum ./*.deb > SHA256SUMS
