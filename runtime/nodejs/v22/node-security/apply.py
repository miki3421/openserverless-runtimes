#!/usr/bin/env python3
# Licensed under the Apache License, Version 2.0. See LICENSE and NOTICE.
"""Backport bounded guards without replacing legacy CommonJS dependencies."""
import hashlib
import json
from pathlib import Path

ROOT = Path('/node_modules')
CHANGES = [
    ('stream-json/Assembler.js',
     'a341b21d86a9c005e5433eadb6c33d4708d611c8bc624ee383463c0fb6d2e32b', [
        ('this.current[this.key] = value;',
         "if (this.key === '__proto__') {\n"
         '          Object.defineProperty(this.current, this.key, {value, writable: true, enumerable: true, configurable: true});\n'
         '        } else {\n'
         '          this.current[this.key] = value;\n'
         '        }', 2),
     ]),
    ('stream-json/filters/FilterBase.js',
     '4c63caeb52939e2c2eb77c593f6e62fe679186836976abda6da39ae810c81312', [
        ('    this._stack = [];',
         '    this._stack = [];\n'
         '    this._maxDepth = options?.maxDepth ?? 1024;\n'
         '    if (!(this._maxDepth === Infinity || (Number.isSafeInteger(this._maxDepth) && this._maxDepth >= 0))) {\n'
         "      throw new RangeError('filter: invalid maxDepth');\n"
         '    }', 1),
        ('    // check, if we allow a chunk',
         '    // Bound path construction before invoking any filter.\n'
         '    if (this._stack.length > this._maxDepth) {\n'
         '      return callback(new RangeError(`filter: JSON nesting depth exceeds maxDepth (${this._maxDepth})`));\n'
         '    }\n'
         '    // check, if we allow a chunk', 1),
     ]),
    ('short-uuid/node_modules/uuid/lib/v35.js',
     '7993b5e5a3854534aa7fab6e91f108d984aae88d73abd562d7ce2f1a58780923', [
        ('    var off = buf && offset || 0;',
         '    var off = buf && offset || 0;\n'
         '    if (buf && (!Number.isInteger(off) || off < 0 || off + 16 > buf.length)) {\n'
         "      throw new RangeError('UUID byte range is out of bounds');\n"
         '    }', 1),
     ]),
]


def main():
    prepared = []
    # Validate every input first. An upstream package change requires review.
    for name, expected, replacements in CHANGES:
        path = ROOT / name
        original = path.read_bytes()
        if hashlib.sha256(original).hexdigest() != expected:
            raise SystemExit('Node dependency source changed: ' + name)
        text = original.decode()
        for old, new, count in replacements:
            if text.count(old) != count:
                raise SystemExit('Node dependency patch context changed: ' + name)
            text = text.replace(old, new)
        prepared.append((path, text.encode(), expected))
    receipt = []
    for path, content, before in prepared:
        path.write_bytes(content)
        receipt.append({'path': str(path.relative_to(ROOT)), 'beforeSha256': before,
                        'afterSha256': hashlib.sha256(content).hexdigest()})
    destination = Path('/usr/share/ops-security/node-dependencies')
    destination.mkdir(parents=True, exist_ok=True)
    (destination / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')


if __name__ == '__main__':
    main()
