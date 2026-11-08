#!/usr/bin/env python3
# Licensed under the Apache License, Version 2.0. See LICENSE and NOTICE.
"""Compare the installed package, public ABI and runtime contracts, offline."""
import argparse
import json
from pathlib import Path
import subprocess

LIBRARIES = ["libglib-2.0.so.0", "libgio-2.0.so.0", "libgmodule-2.0.so.0",
             "libgobject-2.0.so.0", "libgthread-2.0.so.0", "libsqlite3.so.0"]


def run(image, command):
    return subprocess.check_output([
        "docker", "run", "--rm", "--pull=never", "--network", "none",
        "--read-only", "--memory", "256m", "--cpus", "1", "--pids-limit", "64",
        "--cap-drop=ALL", "--security-opt=no-new-privileges",
        "--entrypoint", "/bin/sh", image, "-ec", command,
    ], text=True, timeout=60)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True)
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    images = [args.base, args.candidate]
    rows = []
    def check(name, condition):
        rows.append({"check": name, "status": "PASS" if condition else "FAIL"})
    inventories = [dict(line.split("\t") for line in run(image, "dpkg-query -W -f='${binary:Package}\\t${Version}\\n'").splitlines()) for image in images]
    changes = {p: [inventories[0].get(p), inventories[1].get(p)] for p in inventories[0].keys() | inventories[1].keys() if inventories[0].get(p) != inventories[1].get(p)}
    expected = {}
    for p in ["libglib2.0-0:amd64", "libglib2.0-bin", "libglib2.0-dev:amd64", "libglib2.0-dev-bin"]:
        expected[p] = ["2.74.6-2+deb12u9", "2.74.6-2+deb12u9+0ops1"]
    for p in ["libsqlite3-0:amd64", "libsqlite3-dev:amd64"]:
        expected[p] = ["3.40.1-2+deb12u2", "3.40.1-2+deb12u2+0ops1"]
    check("only_six_qualified_binary_packages_change", changes == expected)
    command = "sha256sum /usr/local/bin/node /bin/proxy /bin/compile /lib/launcher.js /package.json /package-lock.json"
    check("node_proxy_compiler_launcher_lock_unchanged", run(images[0], command) == run(images[1], command))
    headers = "find /usr/include/glib-2.0 /usr/lib/x86_64-linux-gnu/glib-2.0/include /usr/include/sqlite3.h /usr/include/sqlite3ext.h -type f -exec sha256sum {} + | sort"
    check("public_headers_byte_identical", run(images[0], headers) == run(images[1], headers))
    configs = [json.loads(subprocess.check_output(["docker", "image", "inspect", image], text=True))[0]["Config"] for image in images]
    keys = ["Env", "Entrypoint", "Cmd", "User", "WorkingDir", "ExposedPorts", "Volumes"]
    check("image_runtime_contract_unchanged", all(configs[0].get(k) == configs[1].get(k) for k in keys))
    for library in LIBRARIES:
        command = "readelf -d /usr/lib/x86_64-linux-gnu/" + library + " | grep SONAME; nm -D --defined-only --format=posix /usr/lib/x86_64-linux-gnu/" + library + " | awk '{ print $1, $2 }' | sort"
        check(library + "_soname_and_exported_symbols_unchanged", run(images[0], command) == run(images[1], command))
    command = "python3 -c 'import sqlite3,json; print(json.dumps(sorted(x[0] for x in sqlite3.connect(\":memory:\").execute(\"PRAGMA compile_options\"))))'"
    check("sqlite_compile_options_preserved", run(images[0], command) == run(images[1], command))
    command = "find /usr/share/ops-security/openexr /usr/share/ops-security/node-dependencies /usr/share/ops-security/npm-dependencies -type f -exec sha256sum {} + | sort"
    check("previous_openexr_node_npm_fix_receipts_preserved", run(images[0], command) == run(images[1], command))
    report = {"base": args.base, "candidate": args.candidate, "packageChanges": changes, "checks": rows}
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"checks": rows}))
    raise SystemExit(0 if all(r["status"] == "PASS" for r in rows) else 1)


if __name__ == "__main__":
    main()
