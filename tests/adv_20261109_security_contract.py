#!/usr/bin/env python3
# Licensed under the Apache License, Version 2.0. See LICENSE and NOTICE.
"""Validate the bounded 2026-11-09 ADV native-package image overlays."""
import argparse
import json
from pathlib import Path
import subprocess

from node22_libxml2_package_contract import CONTROL, POC, parse_case
from node22_native_libraries import SQLITE_CASES, SQLITE_DRIVER, run_case


def run(image, command):
    return subprocess.check_output([
        "docker", "run", "--rm", "--pull=never", "--network", "none",
        "--read-only", "--tmpfs", "/tmp:rw,nosuid,noexec,size=16m",
        "--memory", "256m", "--cpus", "1", "--pids-limit", "64",
        "--cap-drop=ALL", "--security-opt=no-new-privileges",
        "--entrypoint", "/bin/sh", image, "-ec", command,
    ], text=True, timeout=90)


def inventory(image):
    rows = run(image, "dpkg-query -W -f='${binary:Package}\\t${Version}\\n'")
    return dict(row.split("\t", 1) for row in rows.splitlines())


def image_config(image):
    raw = json.loads(subprocess.check_output(["docker", "image", "inspect", image], text=True))[0]["Config"]
    return {key: raw.get(key) for key in (
        "User", "ExposedPorts", "Env", "Entrypoint", "Cmd", "WorkingDir",
        "StopSignal", "Healthcheck", "Shell",
    )}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kind", required=True, choices=("node", "python", "operator", "admin"))
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

    base, candidate = inventory(args.base), inventory(args.candidate)
    changes = {name: [base.get(name), candidate.get(name)]
               for name in base.keys() | candidate.keys()
               if base.get(name) != candidate.get(name)}
    expected = {
        "node": {"openssh-client": ["1:9.2p1-2+deb12u10", None]},
        "python": {
            "libsqlite3-0:amd64": ["3.40.1-2+deb12u2", "3.40.1-2+deb12u2+0ops1"],
            "libxml2:amd64": ["2.9.14+dfsg-1.3~deb12u6", "2.9.14+dfsg-1.3~deb12u6+0ops1"],
        },
        "operator": {"libsqlite3-0:amd64": ["3.40.1-2+deb12u2", "3.40.1-2+deb12u2+0ops1"]},
        "admin": {"libsqlite3-0:amd64": ["3.40.1-2+deb12u2", "3.40.1-2+deb12u2+0ops1"]},
    }[args.kind]
    check("exact_package_delta", changes == expected, changes)
    check("runtime_configuration_preserved", image_config(args.base) == image_config(args.candidate))
    check("dpkg_audit_clean", run(args.candidate, "dpkg --audit").strip() == "")

    if args.kind == "node":
        run(args.candidate, "! command -v ssh; ! command -v scp; ! command -v sftp; "
                            "test -s /usr/share/ops-security/openssh-removal/SOURCE; "
                            "git --version; hg --version >/dev/null")
        check("ssh_clients_absent_and_developer_tools_work", True)
    else:
        version = run(args.candidate,
                      "test -s /usr/share/ops-security/sqlite/distinct-test.log; "
                      "dpkg-query -W -f='${Version}' libsqlite3-0").strip()
        check("sqlite_receipt_and_version", version == "3.40.1-2+deb12u2+0ops1", version)
        sqlite_rows = []
        for name, sql, expected_rows, _ in SQLITE_CASES:
            sqlite_rows.append(run_case(args.candidate, "sqlite_" + name, SQLITE_DRIVER,
                               {"name": name, "sql": sql, "expected": expected_rows,
                                "version": "3.40.1"}))
        check("sqlite_controls_and_cve_regressions", all(row["status"] == "PASS" for row in sqlite_rows), sqlite_rows)

    if args.kind == "python":
        version = run(args.candidate,
                      "test -s /usr/share/ops-security/libxml2/test-summary.txt; "
                      "dpkg-query -W -f='${Version}' libxml2").strip()
        check("libxml2_receipt_and_version", version == "2.9.14+dfsg-1.3~deb12u6+0ops1", version)
        controls = [parse_case(args.candidate, CONTROL, True) for _ in range(5)]
        triggers = [parse_case(args.candidate, POC, False) for _ in range(5)]
        check("libxml2_control_accepted", all(row[0] == 0 for row in controls), controls)
        check("cve_2026_6653_fixture_rejected", all(row[0] == 0 for row in triggers), triggers)

    report = {"kind": args.kind, "base": args.base, "candidate": args.candidate,
              "packageChanges": changes, "checks": checks}
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"kind": args.kind, "checks": checks}))
    raise SystemExit(0 if all(row["status"] == "PASS" for row in checks) else 1)


if __name__ == "__main__":
    main()
