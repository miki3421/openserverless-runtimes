#!/usr/bin/env python3
# Licensed under the Apache License, Version 2.0. See LICENSE and NOTICE.
"""Check the AOM-only image delta and legitimate media behavior, offline."""
import argparse
import json
from pathlib import Path
import subprocess


def inside(image, command, *, memory="512m", timeout=120):
    return subprocess.check_output([
        "docker", "run", "--rm", "--pull=never", "--network", "none",
        "--read-only", "--tmpfs", "/tmp:rw,nosuid,size=64m",
        "--memory", memory, "--cpus", "2", "--pids-limit", "128",
        "--cap-drop=ALL", "--security-opt=no-new-privileges",
        "--entrypoint", "/bin/sh", image, "-ec", command,
    ], text=True, timeout=timeout)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True)
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    images = [args.base, args.candidate]
    checks = []

    def check(name, passed):
        checks.append({"check": name, "status": "PASS" if passed else "FAIL"})

    inventories = []
    for image in images:
        lines = inside(image, "dpkg-query -W -f='${binary:Package}\\t${Version}\\n'")
        inventories.append(dict(line.split("\t", 1) for line in lines.splitlines()))
    changes = {name: [inventories[0].get(name), inventories[1].get(name)]
               for name in inventories[0].keys() | inventories[1].keys()
               if inventories[0].get(name) != inventories[1].get(name)}
    check("only_libaom3_package_changes", changes == {
        "libaom3:amd64": ["3.6.0-1+deb12u3", "3.12.1-1+deb13u1~bpo12+0ops1"]})

    image_config = [json.loads(subprocess.check_output(
        ["docker", "image", "inspect", image], text=True))[0]["Config"]
        for image in images]
    keys = ["Env", "Entrypoint", "Cmd", "User", "WorkingDir", "ExposedPorts", "Volumes"]
    check("runtime_image_contract_unchanged", all(
        image_config[0].get(key) == image_config[1].get(key) for key in keys))

    stable = "sha256sum /usr/local/bin/node /bin/proxy /bin/compile /lib/launcher.js /package.json /package-lock.json"
    check("node_proxy_launcher_lock_unchanged",
          inside(images[0], stable) == inside(images[1], stable))

    soname = "readelf -d /usr/lib/x86_64-linux-gnu/libaom.so.3 | grep SONAME"
    check("aom_soname_unchanged", inside(images[0], soname) == inside(images[1], soname))
    exports = ("nm -D --defined-only --format=posix /usr/lib/x86_64-linux-gnu/libaom.so.3 "
               "| awk '{ print $1, $2 }' | sort")
    symbol_sets = [set(inside(image, exports).splitlines()) for image in images]
    removed_symbols = symbol_sets[0] - symbol_sets[1]
    # This was never part of the installed AOM API headers. Upstream removed
    # the implementation; supported and installed consumers do not import it.
    check("only_removed_legacy_internal_export",
          removed_symbols == {"av1_resize_frame420 T"})
    imported = set(inside(images[0],
        "nm -D --undefined-only /usr/lib/x86_64-linux-gnu/libheif.so.1 "
        "| awk '{print $2}' | grep '^aom_' | sort -u").splitlines())
    candidate_names = {row.split()[0] for row in symbol_sets[1]}
    check("installed_libheif_aom_imports_retained", imported <= candidate_names)

    old_receipts = ("find /usr/share/ops-security/openexr /usr/share/ops-security/glib "
                    "/usr/share/ops-security/sqlite /usr/share/ops-security/node-dependencies "
                    "/usr/share/ops-security/npm-dependencies -type f -exec sha256sum {} + | sort")
    check("previous_security_receipts_unchanged",
          inside(images[0], old_receipts) == inside(images[1], old_receipts))

    media = ("convert -size 4x4 xc:'#123456' /tmp/synthetic.avif; "
             "convert /tmp/synthetic.avif /tmp/synthetic.png; "
             "identify -format '%m %wx%h' /tmp/synthetic.png")
    for label, image in zip(["base", "candidate"], images):
        check(label + "_valid_avif_roundtrip", inside(image, media, memory="768m").strip() == "PNG 4x4")

    receipt = inside(images[1],
                     "test -f /usr/share/ops-security/aom/SOURCE; "
                     "test -f /usr/share/ops-security/aom/resize-regression.log; "
                     "dpkg-query -W -f='${Version}' libaom3")
    check("aom_receipt_and_package_version",
          receipt.strip() == "3.12.1-1+deb13u1~bpo12+0ops1")

    report = {"base": args.base, "candidate": args.candidate,
              "packageChanges": changes,
              "removedLegacyInternalExports": sorted(removed_symbols),
              "checks": checks}
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"checks": checks}))
    raise SystemExit(0 if all(row["status"] == "PASS" for row in checks) else 1)


if __name__ == "__main__":
    main()
