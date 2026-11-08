#!/usr/bin/env python3
# Licensed under the Apache License, Version 2.0. See LICENSE and NOTICE.
"""Bounded installed-library regression cases; local Docker images only.

Malformed introspection vectors derive from GLib MR 5156. Each vector gets a
separate restricted process, so a parent crash cannot hide the other results.
No malformed input is sent to a cluster, application or external service.
SQLite vectors derive from upstream 12ad822d9b827777 (distinct.test 10.1/10.2).
"""
import argparse
import json
from pathlib import Path
import subprocess

GLIB_CASES = [
    ("root", "<node/>", True),
    ("nested_nodes", '<node><node name="child"><node name="grandchild"/></node></node>', True),
    ("method_and_signal", '<node><interface name="org.example.Test"><method name="Read"><arg name="value" type="s" direction="out"/></method><signal name="Changed"><arg type="s"/></signal></interface></node>', True),
    ("property", '<node><interface name="org.example.Test"><property name="Name" type="s" access="read"/></interface></node>', True),
    ("annotation", '<node><annotation name="org.example.Note" value="synthetic"/></node>', True),
    ("node_in_method", '<node><interface name="I"><method name="M"><node><interface name="I2"/></node></method></interface></node>', False),
    ("node_in_signal", '<node><interface name="I"><signal name="S"><node><interface name="I2"><signal name="S2"/></interface></node></signal></interface></node>', False),
    ("node_in_property", '<node><interface name="I"><property name="P" type="s" access="read"><node><interface name="I2"/></node></property></interface></node>', False),
    ("node_in_arg", '<node><interface name="I"><method name="M"><arg type="s"><node><interface name="I2"><method name="M2"/></interface></node></arg></method></interface></node>', False),
    ("node_in_interface", '<node><interface name="I"><node name="child"/></interface></node>', False),
    ("node_in_annotation", '<node><annotation name="org.example.Note" value="synthetic"><node/></annotation></node>', False),
    ("truncated_invalid_method", '<node><interface name="I"><method name="M"><node><interface name="I2"/></node></method>', False),
]

GLIB_DRIVER = '''import ctypes,json,sys
gio=ctypes.CDLL('libgio-2.0.so.0'); glib=ctypes.CDLL('libglib-2.0.so.0')
class Error(ctypes.Structure):
 _fields_=[('domain',ctypes.c_uint),('code',ctypes.c_int),('message',ctypes.c_char_p)]
gio.g_dbus_node_info_new_for_xml.argtypes=[ctypes.c_char_p,ctypes.POINTER(ctypes.c_void_p)]
gio.g_dbus_node_info_new_for_xml.restype=ctypes.c_void_p
gio.g_dbus_node_info_unref.argtypes=[ctypes.c_void_p]
glib.g_error_free.argtypes=[ctypes.c_void_p]
payload=json.loads(sys.stdin.read());error=ctypes.c_void_p()
node=gio.g_dbus_node_info_new_for_xml(payload['xml'].encode(),ctypes.byref(error))
valid=bool(node) and not error.value
invalid=not node and bool(error.value)
code=ctypes.cast(error,ctypes.POINTER(Error)).contents.code if error.value else None
if node:gio.g_dbus_node_info_unref(node)
if error.value:glib.g_error_free(error)
ok=valid if payload['valid'] else invalid and code==5
print(json.dumps({'accepted':valid,'structuredError':invalid,'errorCode':code,'ok':ok}))
sys.exit(0 if ok else 1)
'''

SQLITE_CASES = [
    ("ordinary_distinct_order", "SELECT DISTINCT x FROM (SELECT 2 x UNION ALL SELECT 1 UNION ALL SELECT 2) ORDER BY x", [[1], [2]], False),
    ("bound_parameters", "SELECT ? || ?", [["synthetic-alpha"]], False),
    ("json_function", "SELECT json_extract('{\"value\":3}', '$.value')", [[3]], False),
    ("transaction_rollback", "transaction", [[1]], False),
    ("distinct_65_results_64_order_terms", "SELECT DISTINCT " + ",".join(["1"] * 65) + " ORDER BY " + ",".join(["'x'"] * 64), [[1] * 65], True),
    ("distinct_66_results_63_order_terms", "SELECT DISTINCT " + ",".join(["7"] * 66) + " ORDER BY " + ",".join(["'other'"] * 63), [[7] * 66], True),
    ("explain_distinct_order", "EXPLAIN SELECT DISTINCT " + ",".join(["1"] * 65) + " ORDER BY " + ",".join(["'x'"] * 64), "explain", True),
    ("create_table_distinct_order", "CREATE TABLE regression AS SELECT DISTINCT " + ",".join(["'synthetic'"] * 65) + " ORDER BY " + ",".join(["'x'"] * 64), "created_table", True),
]

SQLITE_DRIVER = '''import json,sqlite3,sys
p=json.loads(sys.stdin.read());db=sqlite3.connect(':memory:')
assert sqlite3.sqlite_version=='3.40.1'
if p['sql']=='transaction':
 db.execute('CREATE TABLE t(value)');db.execute('INSERT INTO t VALUES (1)');db.commit()
 db.execute('INSERT INTO t VALUES (2)');db.rollback();rows=[list(r) for r in db.execute('SELECT value FROM t')]
else:
 params=('synthetic-','alpha') if p['name']=='bound_parameters' else ()
 rows=[list(r) for r in db.execute(p['sql'],params)]
if p['expected']=='created_table':rows=[list(r) for r in db.execute('SELECT count(*) FROM regression')];ok=rows==[[1]]
elif p['expected']=='explain':ok=bool(rows) and rows[0][1]=='Init'
else:ok=rows==p['expected']
assert db.execute('PRAGMA integrity_check').fetchone()==('ok',)
db.close();print(json.dumps({'ok':ok,'rows':len(rows),'version':sqlite3.sqlite_version}));sys.exit(0 if ok else 1)
'''


def run_case(image, name, code, payload):
    result = subprocess.run([
        "docker", "run", "--rm", "--pull=never", "-i", "--network", "none",
        "--read-only", "--tmpfs", "/tmp:rw,nosuid,noexec,size=16m",
        "--memory", "128m", "--cpus", "1", "--pids-limit", "64",
        "--ulimit", "core=0", "--cap-drop=ALL",
        "--security-opt=no-new-privileges", "--entrypoint", "python3",
        image, "-c", code,
    ], input=json.dumps(payload), text=True, capture_output=True, timeout=30)
    return {"case": name, "status": "PASS" if result.returncode == 0 else "FAIL",
            "exitCode": result.returncode, "stdout": result.stdout[:4096],
            "stderr": result.stderr[:4096]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True)
    parser.add_argument("--candidate")
    parser.add_argument("--library", choices=["glib", "sqlite", "all"], default="all")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = {"scope": "local bounded native GLib/SQLite tests, no cluster operations", "images": {}}
    accepted = True
    for image in dict.fromkeys(i for i in [args.base, args.candidate] if i):
        rows, controls, triggers = [], [], []
        if args.library in ("glib", "all"):
            for name, xml, valid in GLIB_CASES:
                row = run_case(image, "glib_" + name, GLIB_DRIVER, {"xml": xml, "valid": valid})
                rows.append(row); (controls if valid else triggers).append(row)
        if args.library in ("sqlite", "all"):
            for name, sql, expected, regression in SQLITE_CASES:
                row = run_case(image, "sqlite_" + name, SQLITE_DRIVER, {"name": name, "sql": sql, "expected": expected})
                rows.append(row); (triggers if regression else controls).append(row)
        report["images"][image] = rows
        if image == args.base:
            accepted &= all(r["status"] == "PASS" for r in controls)
            for prefix in ("glib_", "sqlite_"):
                group = [r for r in triggers if r["case"].startswith(prefix)]
                if group:
                    accepted &= any(r["status"] == "FAIL" for r in group)
        if args.candidate and image == args.candidate:
            accepted &= all(r["status"] == "PASS" for r in rows)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({image: {"pass": sum(r["status"] == "PASS" for r in rows), "fail": sum(r["status"] == "FAIL" for r in rows)} for image, rows in report["images"].items()}))
    raise SystemExit(0 if accepted else 1)


if __name__ == "__main__":
    main()
