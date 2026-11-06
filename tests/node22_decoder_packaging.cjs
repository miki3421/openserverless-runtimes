// Licensed under the Apache License, Version 2.0. See LICENSE and NOTICE.
'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const {spawnSync} = require('node:child_process');
const helper = path.resolve(__dirname, '../runtime/nodejs/v22/bin/prepare-dependencies.cjs');
const decoderPath = 'node_modules/decode-uri-component';
const results = [];
for (const mode of ['fresh', 'idempotent', 'source-drift', 'old-lock', 'unknown-export', 'bad-nested-copy']) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'ops-decoder-'));
  try {
    fs.copyFileSync('/package.json', path.join(root, 'package.json'));
    const lock = JSON.parse(fs.readFileSync('/package-lock.json'));
    fs.cpSync('/node_modules/decode-uri-component', path.join(root, decoderPath), {recursive: true});
    fs.cpSync('/node_modules/query-string', path.join(root, 'node_modules/query-string'), {recursive: true});
    const metadata = path.join(root, decoderPath, 'package.json');
    const pkg = JSON.parse(fs.readFileSync(metadata));
    if (mode !== 'idempotent') {
      delete pkg.exports.require;
      fs.rmSync(path.join(root, decoderPath, 'index.cjs'));
    }
    if (mode === 'source-drift') fs.appendFileSync(path.join(root, decoderPath, 'index.js'), '\n// drift\n');
    if (mode === 'old-lock') lock.packages[decoderPath].version = '0.2.2';
    if (mode === 'unknown-export') pkg.exports.import = './other.js';
    if (mode === 'bad-nested-copy') {
      const nested = 'node_modules/query-string/node_modules/decode-uri-component';
      fs.cpSync(path.join(root, decoderPath), path.join(root, nested), {recursive: true});
      lock.packages[nested] = {...lock.packages[decoderPath], version: '0.2.2'};
    }
    fs.writeFileSync(metadata, JSON.stringify(pkg));
    fs.writeFileSync(path.join(root, 'package-lock.json'), JSON.stringify(lock));
    const before = fs.readFileSync(metadata);
    const result = spawnSync(process.execPath, [helper, root], {encoding: 'utf8', timeout: 5000});
    if (['fresh', 'idempotent'].includes(mode)) {
      assert.equal(result.status, 0, result.stderr);
      const again = spawnSync(process.execPath, [helper, root], {encoding: 'utf8', timeout: 5000});
      assert.equal(again.status, 0, again.stderr);
    } else {
      assert.equal(result.status, 1, result.stderr);
      assert.deepEqual(fs.readFileSync(metadata), before, 'failed verification mutated the first package');
      assert(!fs.existsSync(path.join(root, decoderPath, 'index.cjs')), 'failed verification wrote an adapter');
    }
    results.push({check: mode, status: 'PASS'});
  } finally { fs.rmSync(root, {recursive: true, force: true}); }
}
console.log(JSON.stringify({checks: results}));
