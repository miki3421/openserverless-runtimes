# Licensed under the Apache License, Version 2.0. See LICENSE and NOTICE.
"""Check all-input validation using private copies from the original image."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1] / 'runtime/nodejs/v22/npm-security'
INSTALLED = Path('/usr/local/lib/node_modules/npm/node_modules')


class InstallerTests(unittest.TestCase):
    def exercise(self, mode):
        with tempfile.TemporaryDirectory(prefix='ops-npm-installer-') as tmp:
            root = Path(tmp) / 'modules'
            receipt = Path(tmp) / 'receipt'
            receipt.mkdir()
            changes = json.loads((SOURCE / 'patches.json').read_text())
            for change in changes:
                p = root / change['path']
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes((INSTALLED / change['path']).read_bytes())
            if mode == 'last-source-drift':
                with (root / changes[-1]['path']).open('ab') as file:
                    file.write(b'\n// synthetic drift\n')
            if mode == 'last-context-drift':
                changes[-1]['replacements'][-1]['count'] += 1
            (receipt / 'patches.json').write_text(json.dumps(changes))
            before = {c['path']: (root / c['path']).read_bytes() for c in changes}
            spec = importlib.util.spec_from_file_location('npm_backport', SOURCE / 'apply.py')
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            def redirect(value):
                return {str(INSTALLED): root,
                        '/usr/share/ops-security/npm-dependencies': receipt}[value]

            with patch.object(module, 'Path', redirect):
                if mode != 'valid':
                    with self.assertRaises(SystemExit):
                        module.main()
                    self.assertFalse((receipt / 'receipt.json').exists())
                    for name, data in before.items():
                        self.assertEqual((root / name).read_bytes(), data)
                else:
                    module.main()
                    rows = json.loads((receipt / 'receipt.json').read_text())
                    self.assertEqual(len(rows), 6)
                    for row in rows:
                        self.assertEqual(hashlib.sha256((root / row['path']).read_bytes()).hexdigest(),
                                         row['afterSha256'])
                    with self.assertRaises(SystemExit):
                        module.main()
                    self.assertEqual(json.loads((receipt / 'receipt.json').read_text()), rows)

    def test_valid_receipt_and_repeat_refusal(self):
        self.exercise('valid')

    def test_last_source_drift_changes_nothing(self):
        self.exercise('last-source-drift')

    def test_last_context_drift_changes_nothing(self):
        self.exercise('last-context-drift')


if __name__ == '__main__':
    unittest.main()
