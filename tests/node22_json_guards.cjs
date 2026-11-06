// Licensed under the Apache License, Version 2.0. See LICENSE and NOTICE.
// Local bounded fixtures only; no server or external endpoint is contacted.
const test = require('node:test');
const assert = require('node:assert/strict');
const {Readable} = require('node:stream');
const {pipeline} = require('node:stream/promises');
const {parser} = require('/node_modules/stream-json');
const Assembler = require('/node_modules/stream-json/Assembler');
const {streamValues} = require('/node_modules/stream-json/streamers/StreamValues');

async function assemble(text, options) {
  const p = parser(), a = Assembler.connectTo(p, options);
  await pipeline(Readable.from([text]), p);
  return a.current;
}
for (const reviver of [false, true]) {
  test('JSON.parse parity including special own keys, reviver=' + reviver, async () => {
    for (const text of [
      '{"__proto__":{"synthetic":true},"name":"fixture"}',
      '{"__proto__":null,"name":"fixture"}',
      '{"nested":{"__proto__":{"toString":1}},"array":[1,true,null]}',
      '{"__proto__":1,"__proto__":{"value":2}}',
    ]) {
      const value = await assemble(text, reviver ? {reviver: (_k, v) => v} : undefined);
      assert.deepEqual(value, JSON.parse(text));
      assert.equal(Object.getPrototypeOf(value), Object.prototype);
      assert.equal({}.synthetic, undefined);
    }
  });
}
test('reviver omission and number-as-string still work', async () => {
  assert.deepEqual(await assemble('{"keep":1,"omit":2}', {reviver: (k,v) => k === 'omit' ? undefined : v}), {keep:1});
  assert.deepEqual(await assemble('{"id":9007199254740993}', {numberAsString:true}), {id:'9007199254740993'});
});
for (const kind of ['Pick','Ignore','Filter','Replace']) {
  test(kind + ' rejects over-depth traversal through stream error', async () => {
    const Filter = require('/node_modules/stream-json/filters/' + kind);
    const f = new Filter({filter:'missing', maxDepth:8});
    f.resume();
    await assert.rejects(pipeline(Readable.from(['{"a":'.repeat(20)+'1'+'}'.repeat(20)]), parser(), f), RangeError);
  });
}
test('default depth is finite and an explicit trusted-input override remains available', async () => {
  const Pick = require('/node_modules/stream-json/filters/Pick');
  const input = '{"a":'.repeat(1100)+'1'+'}'.repeat(1100);
  const bounded = new Pick({filter:'missing'}); bounded.resume();
  await assert.rejects(pipeline(Readable.from([input]), parser(), bounded), RangeError);
  const trusted = new Pick({filter:'missing',maxDepth:Infinity}); trusted.resume();
  await pipeline(Readable.from([input]), parser(), trusted);
  for (const value of [-1, NaN, '8', 1.5]) assert.throws(() => new Pick({filter:'x',maxDepth:value}), RangeError);
});
test('normal pick and MinIO-style streamValues remain compatible', async () => {
  const Pick = require('/node_modules/stream-json/filters/Pick');
  const f = new Pick({filter:'data',maxDepth:8}), values=streamValues(), rows=[];
  values.on('data', x=>rows.push(x.value));
  await pipeline(Readable.from(['{"data":{"value":7},"ignore":0}']), parser(), f, values);
  assert.deepEqual(rows,[{value:7}]);
});
for (const kind of ['v3','v5']) {
  test('legacy UUID ' + kind + ' bounds and deterministic output', () => {
    const uuid=require('/node_modules/short-uuid/node_modules/uuid/' + kind);
    const expected=uuid('fixture',uuid.DNS);
    for (const [length,offset] of [[8,0],[16,1],[16,-1],[16,0.5]]) {
      const buf=Buffer.alloc(length,0xab), copy=Buffer.from(buf);
      assert.throws(()=>uuid('fixture',uuid.DNS,buf,offset),RangeError);
      assert.deepEqual(buf,copy);
    }
    const buf=Buffer.alloc(20,0xab);
    assert.equal(uuid('fixture',uuid.DNS,buf,2),buf);
    assert.equal(buf.subarray(2,18).toString('hex'),expected.replaceAll('-',''));
    assert.deepEqual([...buf.subarray(0,2),...buf.subarray(18)],[171,171,171,171]);
  });
}
test('short-uuid public API remains compatible', () => {
  const short=require('/node_modules/short-uuid');
  const codec=short(), id=codec.uuid();
  assert.equal(codec.toUUID(codec.fromUUID(id)),id);
  assert.match(short.uuid(),/^[a-f0-9-]{36}$/);
  assert.equal(typeof codec.new(),'string');
});
test('JSONC-only vulnerable entry points are absent from installed 1.9.1', () => {
  const fs=require('node:fs');
  assert.equal(fs.existsSync('/node_modules/stream-json/jsonc'),false);
});
