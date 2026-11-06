#!/usr/bin/env python3
# Licensed under the Apache License, Version 2.0. See LICENSE and NOTICE.
"""Apply source-bound glob/minimatch corrections to every installed npm copy."""
import hashlib
import json
from pathlib import Path


def main():
    root = Path('/usr/local/lib/node_modules/npm/node_modules')
    destination = Path('/usr/share/ops-security/npm-dependencies')
    manifest = json.loads((destination / 'patches.json').read_text())
    prepared = []
    for change in manifest:
        path = root / change['path']
        before = path.read_bytes()
        if hashlib.sha256(before).hexdigest() != change['beforeSha256']:
            raise SystemExit('npm dependency changed: ' + change['path'])
        text = before.decode()
        for replacement in change['replacements']:
            if text.count(replacement['old']) != replacement['count']:
                raise SystemExit('npm patch context changed: ' + change['path'])
            text = text.replace(replacement['old'], replacement['new'])
        prepared.append((path, text.encode(), change))
    # All sources and contexts must match before changing any installed file.
    receipt = []
    for path, content, change in prepared:
        path.write_bytes(content)
        receipt.append({'path': change['path'], 'beforeSha256': change['beforeSha256'],
                        'afterSha256': hashlib.sha256(content).hexdigest()})
    (destination / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')


if __name__ == '__main__':
    main()
