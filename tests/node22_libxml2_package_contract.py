#!/usr/bin/env python3
# Licensed under the Apache License, Version 2.0. See LICENSE and NOTICE.
"""Check the libxml2-only image delta, ABI and bounded parser behavior."""
import argparse
import base64
import json
from pathlib import Path
import subprocess

POC_SHA256 = "1e1b97af5d7c617b2b33f65cf44e3154daef357cf261b82fe7012ac438a65439"
POC = (
    "PD94bWwgdmVyc2lvbj0iSS4wIj8+DQo8IURPQ1RZUEUgYmlsbGlvbiBbDQo8IUVMRU1FTlQgYmlsbGlvbiAoI1BDREFUQSk+DQo8IUVOVElUWSBsYXVnaDAgImhhIj4NCjwhRU5USVRZIGxhdWdoMSAiJmxhdWdoMDsmbGF1Z2gwOyI+DQo8IUVOVElUWSBsYXVnaDIgIiZsXnVnaDE7JmxhdWdoMTsiPg0KPCFFTlRJVFkgbGF1Z2gzICINCjwhRU5USVRZYXVnaDI7Ij4NCjwhRU5USVRZIGxhdWdoNCAiJmxhdWdoMzsmbGF1Z2gzOyI+DQo8IUVOVElUWSBsYXVnaDUgIiZsYXVnaDQ7JmxhdWdoNDsiPg0KPCFFTlRJVFkgbGF1Z2g2ICImbFF1Z2g1OyZsYXVnaDU7Ij4NCjwhRU5USVRZIGxhdWdoNyAiJmxhdWdoNjsmbGF1Z2g2OyI+DQo8IUVOVElUWSBsYXVnaDggIiZsYXVnaDc7JmxhdWdoNzsiPg0KPCFFTlRJVFkgbGF1Z2g5ICImbGF1Z2g4OyZsYXVnaDg7Ij4NCjwhRU5USVRZIGxhdWdoMTAgIiZsU3VnaDk7JmxhdWdoOTsiPg0KPCFFTlRJVFkgbGF1Z2gxMQ0KIiZsYXVnaDEwOyZsYXVnaDEwOyZsYXVnaDEwOyZsYXVnaDEwOyZsYXVnaDEwOyZsYXVnaDEwOyZsYXVnaDEwOyZsYXVnaDEwOyZsYXVnaDEwOyZsYXVnaDEwOyZsYXVnaDEwOyZsYXVnaDEwOyZsYXVnaDEwOyZsYXVnaDEwOyZsYXVnaDEwOyZsYXVnaDEwOyZsYXVnaDEwOyZsYXVnaDEwOyZsYXVnaDEwOyZsYXVnaDEwOyZsYXVnaDEwOyZsYXVnaDEwOyZsYWJjXzIiPgo8IUFUVExJU1QgZGxjIG9rMiBJRFJFRiAidWdoMTA7JmxhdWdra2gxMDsmbGF1Z2gxMDsmbGF1Z2gxMDsmbGF1Z2gxMDsmbGF1Z2gxMDsmbGF1Z2gxMDsmbGF1Z2gxME9DVFlQRSB0ZXN0IFsKPCFFTEVNRU5UIHRlc3QgKCNQQ0RBVEEpID4KPCFFTlRJVFkgJSB4eCAnJiMzNzt6ejsNPCFbSU5DTFVERVsNJiMzNzt6IGxhdWdoOSAiJmxhdWdoODsmbGF1Z2g4OyI+DQo8ejs8IUVMRU1FTlREKCYjMzc7TUVOVCYjMzg7TUVOVEQmIzM3NztNRU5URCYjMzc7eiZsYXVnaDQ7JmxhdWdoNDsiPg0KPCFFTlRJVFkgbGF1Z2g2ICImbGF1Z2g1OyZsYXVnaDU7Ij4NCjwhRU5USVRZIGxhdWdoNyAiJmxhdWdoNjsmbGF1Z2g2OyI+DQo8IUVOVElUWSBsYXVnaDggIiZsYXVnaDc7JmxhTk1UOUtF9lNNWVNZU1RFTTtNRU5UOSYjMzc7eno7Jz4KPCFFTlRJVFkgJSB6eiAnJiM2MDshRU5USVRZPD94RE9DVFlQRW1+Pz4nID4KJXh4OwP/Z2dLRU5TTVlOVCYjMzU7TUUzNzJ6ejsnPgo8IUVOQklUWQElIHp6ICcmIzYwOyFFTiMzJiMjMzc7YXVnaDExOyZsYXVnaDExOyZsYXVnaDExOyZsYXVnaDExOyZsYXVnaDExOyZsYXVnaDExOyZsYXVnaDExOyZsYXVnaDExOyZsYXVnaDExOyZsYXVnaDExOyZsYXVnaDExOyb4YXVnaDExOyZsYXVnaDExOyZsYXVnaDExOyZsYXVnaDExOyZsYXVnaDExOyZsYXVnaDExOyZsYXVnaDExOyZsYXVnaDExOyZsYXVnaDExOyZsYXVnaDExOyZsYXVnaDExOyZsYXVnaDExOyZsYXVnaDExOyZsYXVnaDExOyZsYXVnaDExOyI+DQo8IUVOVElUWSBsYXVnaDEzDQoiJmxhdWdoMTI7JmxhdWdoMTI7JmxhdWdoMTI7JmxhdWdoMTI7JmxhdWdoMTI7JmxhdWdoMTI7JmxhdWdoMTI7JmxhdWdoMTI7JiYmJiYmJiYmJmxhdWdoMTI7JmxhdWdoMTI7JmxhdWdoMTI7JmxhdWdoMTI7JmxhdWdoMTI7JmxhdWdoMTI7JmxhdWdoMTI7Jmxhdf+AMTI7JmxhdWdoMTI7JmxhdWdoMTI7JmxhdWdoMTI7JmxhdWdoMTI7JmxhdWdoMTI7JmxhdWdoMTI7JmxhdWdoMTI7JmxhdWdoMTI7JmxhdWdoMTI7JmxhdWdoMTI7JmxhdWdoMTI7JmxhdWdoMTI7JmxhdWdoMTI7TEUmbGF1Z2gxMjsmbGF1Z2gxMjsmbGF1Z2gxMjsmbGF1Z2gxMjsmbHVnaDEyOyZsYXVnaDEyOyZsYXVnaDEyOyZsYWF1Z2gxMjsmbGF1Z2gxMjsmbGF1Z2gxMjsmbGF1Z2gxMjsmbGF1Z2gxMjsiPg0KXT4NCjxiaWxsaW9uIGxvY2F0aW9uPSImbGF1Z2gxMzsiPnRleHQ8L2JpbGxpb24+DQoNCg=="
)
# Restore the single repeated entity token at its exact byte position.  Keeping
# this explicit avoids reformatting the otherwise verbatim public fixture.
POC = POC[:2320] + "JmxhdWdoMTI7" + POC[2320:]
CONTROL = base64.b64encode(
    b'<?xml version="1.0"?><!DOCTYPE catalog [<!ENTITY product "ADV">]>'
    b'<catalog><item id="1">&product;</item></catalog>'
).decode()

DRIVER = r'''import base64,ctypes,json,os,sys
p=json.loads(sys.stdin.read());data=base64.b64decode(p['data'],validate=True)
os.dup2(os.open(os.devnull,os.O_WRONLY),2)
lib=ctypes.CDLL('libxml2.so.2')
lib.xmlReadMemory.argtypes=[ctypes.c_void_p,ctypes.c_int,ctypes.c_char_p,ctypes.c_char_p,ctypes.c_int]
lib.xmlReadMemory.restype=ctypes.c_void_p;lib.xmlFreeDoc.argtypes=[ctypes.c_void_p]
buf=ctypes.create_string_buffer(data);doc=lib.xmlReadMemory(buf,len(data),b'case.xml',None,0)
accepted=bool(doc)
if doc:lib.xmlFreeDoc(doc)
ok=accepted==p['accepted'];print(json.dumps({'accepted':accepted,'ok':ok}));sys.exit(0 if ok else 1)
'''


def inside(image, command, timeout=90):
    return subprocess.check_output([
        "docker", "run", "--rm", "--pull=never", "--network", "none",
        "--read-only", "--memory", "256m", "--cpus", "1", "--pids-limit", "64",
        "--cap-drop=ALL", "--security-opt=no-new-privileges",
        "--entrypoint", "/bin/sh", image, "-ec", command,
    ], text=True, timeout=timeout)


def parse_case(image, data, accepted):
    result = subprocess.run([
        "docker", "run", "--rm", "--pull=never", "-i", "--network", "none",
        "--read-only", "--memory", "128m", "--cpus", "1", "--pids-limit", "32",
        "--ulimit", "core=0", "--cap-drop=ALL", "--security-opt=no-new-privileges",
        "--entrypoint", "python3", image, "-c", DRIVER,
    ], input=json.dumps({"data": data, "accepted": accepted}), text=True,
       capture_output=True, timeout=20)
    return result.returncode, result.stdout[:1024], result.stderr[:1024]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True)
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    checks = []

    def check(name, passed, evidence=None):
        row = {"check": name, "status": "PASS" if passed else "FAIL"}
        if evidence is not None:
            row["evidence"] = evidence
        checks.append(row)

    decoded = base64.b64decode(POC, validate=True)
    import hashlib
    check("poc_fixture_identity", hashlib.sha256(decoded).hexdigest() == POC_SHA256)

    inventories = []
    for image in (args.base, args.candidate):
        rows = inside(image, "dpkg-query -W -f='${binary:Package}\\t${Version}\\n'")
        inventories.append(dict(row.split("\t", 1) for row in rows.splitlines()))
    changes = {name: [inventories[0].get(name), inventories[1].get(name)]
               for name in inventories[0].keys() | inventories[1].keys()
               if inventories[0].get(name) != inventories[1].get(name)}
    expected = {
        "libxml2:amd64": ["2.9.14+dfsg-1.3~deb12u6", "2.9.14+dfsg-1.3~deb12u6+0ops1"],
        "libxml2-dev:amd64": ["2.9.14+dfsg-1.3~deb12u6", "2.9.14+dfsg-1.3~deb12u6+0ops1"],
    }
    check("only_libxml2_runtime_and_devel_packages_change", changes == expected, changes)

    stable = "sha256sum /usr/local/bin/node /bin/proxy /bin/compile /lib/launcher.js /package.json /package-lock.json"
    check("node_proxy_launcher_lock_unchanged",
          inside(args.base, stable) == inside(args.candidate, stable))
    headers = "find /usr/include/libxml2 -type f -exec sha256sum {} + | sort"
    check("libxml2_public_headers_byte_identical",
          inside(args.base, headers) == inside(args.candidate, headers))
    abi = ("readelf -d /usr/lib/x86_64-linux-gnu/libxml2.so.2 | grep SONAME; "
           "nm -D --defined-only --format=posix /usr/lib/x86_64-linux-gnu/libxml2.so.2 "
           "| awk '{print $1, $2}' | sort")
    check("libxml2_soname_and_exported_symbols_unchanged",
          inside(args.base, abi) == inside(args.candidate, abi))

    prior = ("find /usr/share/ops-security/openexr /usr/share/ops-security/glib "
             "/usr/share/ops-security/sqlite /usr/share/ops-security/aom "
             "/usr/share/ops-security/node-dependencies /usr/share/ops-security/npm-dependencies "
             "-type f ! -name distinct-test.log -exec sha256sum {} + | sort")
    check("previous_security_receipts_unchanged",
          inside(args.base, prior) == inside(args.candidate, prior))
    sqlite_log = ("sed -E 's/on [^ ]+ Linux/on CONTAINER Linux/' "
                  "/usr/share/ops-security/sqlite/distinct-test.log")
    check("previous_sqlite_test_semantics_unchanged",
          inside(args.base, sqlite_log) == inside(args.candidate, sqlite_log))
    receipt = inside(args.candidate,
        "test -s /usr/share/ops-security/libxml2/test-build.log; "
        "test -s /usr/share/ops-security/libxml2/runtest.log; "
        "test -s /usr/share/ops-security/libxml2/remaining-tests.log; "
        "grep -Fqx 'PASS: testapi completed 280912 API tests across 1164 functions with 0 errors.' "
        "/usr/share/ops-security/libxml2/test-summary.txt; "
        "test -s /usr/share/ops-security/libxml2/libxml2-cve-2026-6653.patch; "
        "dpkg-query -W -f='${Version}' libxml2")
    check("libxml2_receipt_and_package_version",
          receipt.strip() == "2.9.14+dfsg-1.3~deb12u6+0ops1")

    base_control = [parse_case(args.base, CONTROL, True) for _ in range(3)]
    candidate_control = [parse_case(args.candidate, CONTROL, True) for _ in range(20)]
    candidate_poc = [parse_case(args.candidate, POC, False) for _ in range(20)]
    check("base_legitimate_xml_control", all(row[0] == 0 for row in base_control), base_control)
    check("candidate_legitimate_xml_control_20x",
          all(row[0] == 0 for row in candidate_control), candidate_control)
    check("candidate_cve_2026_6653_fixture_rejected_20x",
          all(row[0] == 0 for row in candidate_poc), candidate_poc)

    report = {"base": args.base, "candidate": args.candidate,
              "packageChanges": changes, "checks": checks}
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"checks": checks}))
    raise SystemExit(0 if all(row["status"] == "PASS" for row in checks) else 1)


if __name__ == "__main__":
    main()
