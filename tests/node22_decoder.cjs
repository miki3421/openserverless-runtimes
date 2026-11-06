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
const {createRequire} = require('node:module');
const {pathToFileURL} = require('node:url');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const rootRequire = createRequire('/package.json');
const query = rootRequire('query-string');
const consumer = createRequire(rootRequire.resolve('query-string'));
const decoderFile = consumer.resolve('decode-uri-component');
const decoderDirectory = path.dirname(decoderFile);
const decode = consumer('decode-uri-component');
const results = [];

async function main() {
  const pkg = JSON.parse(fs.readFileSync(path.join(decoderDirectory, 'package.json')));
  assert.equal(pkg.version, '0.5.1');
  assert.equal(typeof decode, 'function');
  const esm = await import(pathToFileURL(path.join(decoderDirectory, 'index.js')));
  assert.equal(decode, esm.default);
  assert.equal(crypto.createHash('sha256').update(fs.readFileSync(path.join(decoderDirectory, 'index.js'))).digest('hex'),
    '6a86ac891edf15c5efa0841ebb31935e3669d58b98318b57d7b08a4530317cb0');
  results.push({check: 'fixed-source-and-cjs-esm-identity', status: 'PASS'});

  for (const value of ['', 'a+b', 'caffè + €', '中文 / 😀', '\u0000', 'percent %25']) {
    assert.equal(decode(encodeURIComponent(value)), value);
    assert.equal(query.parse(query.stringify({q: value})).q, value);
  }
  assert.equal(decode('a+b'), 'a+b');
  assert.equal(query.parse('q=a+b').q, 'a b');
  assert.deepEqual(query.parse('a=1&a=2').a, ['1', '2']);
  assert.deepEqual(query.parse('a[]=1&a[]=2', {arrayFormat: 'bracket'}).a, ['1', '2']);
  assert.equal(query.parse('nil&empty=').nil, null);
  assert.equal(query.parse('nil&empty=').empty, '');
  assert.equal(query.parseUrl('/hello?q=caff%C3%A8#fragment').query.q, 'caffè');
  results.push({check: 'query-public-api-and-unicode', status: 'PASS'});

  for (let point = 0; point < 4096; point += 7) {
    const value = String.fromCodePoint(point) + '😀%+';
    assert.equal(decode(encodeURIComponent(value)), value);
  }
  for (const [input, expected] of [
    ['%', '%'], ['%zz', '%zz'], ['%FE%FF', '\uFFFD\uFFFD'],
    ['%C2', '\uFFFD'], ['%C2%B5', 'µ'], ['%41%FF%42', 'A%FFB'],
    ['%C0%AF', '%C0%AF'], ['%ED%A0%80', '%ED%A0%80'],
    ['%F4%90%80%80', '%F4%90%80%80']
  ]) assert.equal(decode(input), expected);
  assert.throws(() => decode(null), TypeError);
  results.push({check: 'valid-corpus-and-malformed-utf8', status: 'PASS'});

  // Count full-input replacement work instead of relying on a noisy clock or
  // generating an expensive DoS payload. The old installed decoder fails this.
  const nativeReplace = String.prototype.replace;
  const counts = [];
  for (const n of [128, 256, 512]) {
    const input = Array.from({length: n}, (_, i) =>
      '%' + Math.floor(i / 256).toString(16).padStart(2, '0') +
      '%' + (i % 256).toString(16).padStart(2, '0')).join('|') + '%zz';
    let scanned = 0;
    String.prototype.replace = function (...args) {
      scanned += String(this).length;
      return nativeReplace.apply(this, args);
    };
    try { assert.equal(typeof query.parse('data=' + input).data, 'string'); }
    finally { String.prototype.replace = nativeReplace; }
    assert(scanned <= 12 * (input.length + 5), 'unbounded repeated full-input scans');
    counts.push({n, bytes: input.length, scanned});
  }
  // Alternate malformed class: a single long encoded run; no recursive split
  // or stack failure. This is bounded local execution, never a live request.
  assert.equal(decode('%FF'.repeat(4096)), '%FF'.repeat(4096));
  results.push({check: 'bounded-malformed-decoding', status: 'PASS', counts});

  const {Client} = rootRequire('minio');
  const client = new Client({endPoint: 'synthetic.invalid', useSSL: true,
    region: 'us-east-1', accessKey: 'synthetic-access', secretKey: 'synthetic-secret'});
  const signed = new URL(await client.presignedGetObject('synthetic-bucket',
    'folder/caffè + €.txt', 300, {'response-content-disposition': 'attachment; filename="a b.txt"'}));
  assert.equal(signed.hostname, 'synthetic.invalid');
  assert.equal(decodeURIComponent(signed.pathname), '/synthetic-bucket/folder/caffè + €.txt');
  assert.equal(signed.searchParams.get('response-content-disposition'), 'attachment; filename="a b.txt"');
  assert.equal(signed.searchParams.get('X-Amz-Expires'), '300');
  assert.match(signed.searchParams.get('X-Amz-Signature'), /^[a-f0-9]{64}$/);
  results.push({check: 'minio-presigned-url-offline', status: 'PASS'});
  console.log(JSON.stringify({checks: results}));
}
main().catch(error => { console.error(error); process.exitCode = 1; });
