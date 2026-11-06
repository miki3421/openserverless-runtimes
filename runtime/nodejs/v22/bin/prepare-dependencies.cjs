// Licensed to the Apache Software Foundation (ASF) under one or more
// contributor license agreements. See the NOTICE file distributed with
// this work for additional information regarding copyright ownership.
// The ASF licenses this file to You under the Apache License, Version 2.0
// (the "License"); you may not use this file except in compliance with
// the License. You may obtain a copy of the License at
// http://www.apache.org/licenses/LICENSE-2.0
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const {createRequire} = require('node:module');

// query-string 7 remains CommonJS. Delegate to the unmodified fixed ESM
// implementation using Node 22's supported synchronous require(ESM).
// This is a package export adapter, never a decoder or global loader patch.
assert(process.features.require_module, 'Node must support synchronous require(ESM)');
const root = path.resolve(process.argv[2] || '.');
const lock = JSON.parse(fs.readFileSync(path.join(root, 'package-lock.json')));
const entries = Object.entries(lock.packages).filter(([name]) =>
  /(^|\/)node_modules\/decode-uri-component$/.test(name));
assert(entries.length > 0, 'Missing locked decoder');
const sourceHash = '6a86ac891edf15c5efa0841ebb31935e3669d58b98318b57d7b08a4530317cb0';
const integrity = 'sha512-vWHQkXgg2cE3BB4rR0c+PYw9BCQzLoNIRMI7AunIkZst74tw/vpPp7VLoYtsR/cy1f55g3XDWUslfeCZjiZJyA==';
const adapter = "'use strict';\nmodule.exports = require('./index.js').default;\n";

// Validate every installed copy before changing any export metadata.
const packages = entries.map(([name, locked]) => {
  assert.equal(locked.version, '0.5.1');
  assert.equal(locked.integrity, integrity);
  const directory = path.resolve(root, name);
  assert(directory.startsWith(root.endsWith(path.sep) ? root : root + path.sep));
  const metadata = path.join(directory, 'package.json');
  const pkg = JSON.parse(fs.readFileSync(metadata));
  assert.equal(pkg.name, 'decode-uri-component');
  assert.equal(pkg.version, '0.5.1');
  assert.equal(pkg.type, 'module');
  const source = fs.readFileSync(path.join(directory, 'index.js'));
  assert.equal(crypto.createHash('sha256').update(source).digest('hex'), sourceHash);
  const original = {types: './index.d.ts', default: './index.js'};
  const adapted = {types: './index.d.ts', require: './index.cjs', default: './index.js'};
  const alreadyAdapted = Object.hasOwn(pkg.exports, 'require');
  assert.deepEqual(pkg.exports, alreadyAdapted ? adapted : original);
  if (alreadyAdapted) assert.equal(fs.readFileSync(path.join(directory, 'index.cjs'), 'utf8'), adapter);
  return {directory, metadata, pkg, adapted};
});

for (const {directory, metadata, pkg, adapted} of packages) {
  fs.writeFileSync(path.join(directory, 'index.cjs'), adapter, {mode: 0o644});
  pkg.exports = adapted;
  fs.writeFileSync(metadata, JSON.stringify(pkg, null, 2) + '\n');
}

// Exercise the actual consumer resolution, including nested npm layouts.
const consumer = createRequire(createRequire(path.join(root, 'package.json')).resolve('query-string'));
assert.equal(typeof consumer('decode-uri-component'), 'function');
console.log(`Prepared ${packages.length} verified decoder export(s); upstream code unchanged`);
