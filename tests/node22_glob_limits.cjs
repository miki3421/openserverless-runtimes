// Licensed under the Apache License, Version 2.0. See LICENSE and NOTICE.
// Bounded local regression probes for npm's installed glob/minimatch copies.
// No network. Each subprocess has a timeout; fixtures stay in its temporary dir.
const assert = require('node:assert/strict')
const fs = require('node:fs')
const os = require('node:os')
const path = require('node:path')
const { pathToFileURL } = require('node:url')
const { spawnSync } = require('node:child_process')
const npmRoot = process.env.OPS_NPM_ROOT || '/usr/local/lib/node_modules/npm'

async function load(name, format, bundled) {
  const file = path.join(npmRoot, 'node_modules', name, 'dist', format,
    bundled ? 'index.min.js' : 'index.js')
  return format === 'commonjs' ? require(file) : import(pathToFileURL(file).href)
}

async function worker(format, test, bundled) {
  const temp = fs.mkdtempSync(path.join(os.tmpdir(), 'ops-glob-'))
  try {
    if (test.startsWith('minimatch')) {
      const { Minimatch } = await load('minimatch', format, false)
      if (test === 'minimatch_bound') {
        // Eight repetitions are bounded even on the original uncorrected copy.
        const p = Array(8).fill('**/../a/b').join('/')
        const mm = new Minimatch(p, { optimizationLevel: 2, braceExpandMax: 16 })
        assert.equal(mm.set.length, 16)
      } else if (test === 'minimatch_large_set') {
        const mm = new Minimatch('{x,*}/{0..999}', { optimizationLevel: 2 })
        assert.equal(mm.set.length, 2000)
        assert.equal(mm.match('x/5'), true)
        assert.equal(mm.match('y/999'), true)
        assert.equal(mm.match('.y/5'), false)
      } else {
        const mm = new Minimatch('**/../a/b/**/../c/d', { optimizationLevel: 2 })
        assert.equal(mm.set.length, 4)
        assert.equal(mm.match('../a/b/../c/d'), true)
        assert.equal(mm.match('x/a/b/y/c/d'), true)
        assert.equal(mm.match('.x/a/b/y/c/d'), false)
      }
      return
    }
    const api = await load('glob', format, bundled)
    if (test === 'glob_bound' || test === 'glob_large_set') {
      const bounded = test === 'glob_bound'
      const pattern = bounded ? Array(8).fill('**/../a/b').join('/') : '{x,*}/{0..999}'
      const walker = new api.Glob(pattern, { cwd: temp, ...(bounded ? { braceExpandMax: 16 } : {}) })
      assert.equal(walker.patterns.length, bounded ? 16 : 2000)
      return
    }
    function tree(dir, depth) {
      fs.mkdirSync(dir, { recursive: true })
      fs.writeFileSync(path.join(dir, 'f.txt'), 'synthetic')
      if (depth) for (const name of ['a', 'b']) tree(path.join(dir, name), depth - 1)
    }
    tree(temp, 3)
    if (test === 'normal_walk') {
      const expected = api.globSync('**/*.txt', { cwd: temp }).sort()
      assert.equal(expected.length, 15)
      assert.deepEqual((await api.glob('**/*.txt', { cwd: temp })).sort(), expected)
      const stream = api.globStream('**/*.txt', { cwd: temp })
      await new Promise(r => setTimeout(r, 30))
      const found = []
      for await (const item of stream) found.push(item)
      assert.deepEqual(found.sort(), expected)
      return
    }
    const ac = new AbortController()
    const reason = new Error('synthetic cancellation')
    let calls = 0
    const abortFirst = () => { if (++calls === 1) ac.abort(reason) }
    const counted = { ...fs,
      readdir: (...args) => { abortFirst(); return fs.readdir(...args) },
      readdirSync: (...args) => { abortFirst(); return fs.readdirSync(...args) },
    }
    if (test === 'async_cancel') {
      await assert.rejects(api.glob('**', { cwd: temp, signal: ac.signal, fs: counted }),
        error => error === reason)
      const atReject = calls
      await new Promise(r => setTimeout(r, 100))
      assert.equal(calls, atReject, 'directory reads continued after cancellation')
    } else if (test === 'sync_stream_cancel') {
      await new Promise((resolve, reject) => {
        const stream = api.globStreamSync('**', { cwd: temp, signal: ac.signal, fs: counted })
        stream.on('error', error => {
          try { assert.equal(error, reason); resolve() } catch (e) { reject(e) }
        })
        stream.resume()
      })
      await new Promise(r => setTimeout(r, 30))
      assert.equal(calls, 1, 'sync traversal continued after cancellation')
    } else throw new Error('Unknown test')
  } finally { fs.rmSync(temp, { recursive: true, force: true }) }
}

if (process.argv[2] === '--worker') {
  worker(process.argv[3], process.argv[4], process.argv[5] === 'bundled')
    .catch(error => { console.error(error.message); process.exitCode = 1 })
} else {
  const results = []
  for (const format of ['commonjs', 'esm']) {
    const cases = ['minimatch_bound', 'minimatch_large_set', 'minimatch_control'].map(test => [test, 'raw'])
    for (const variant of ['raw', 'bundled'])
      for (const test of ['glob_bound', 'glob_large_set', 'async_cancel', 'sync_stream_cancel', 'normal_walk']) cases.push([test, variant])
    for (const [test, variant] of cases) {
      const run = spawnSync(process.execPath, [__filename, '--worker', format, test, variant],
        { encoding: 'utf8', timeout: 4000, maxBuffer: 1024 * 1024 })
      const row = { format, test, variant, status: run.status === 0 ? 'PASS' : 'FAIL',
        error: run.error?.code || run.stderr.trim().slice(0, 300) || undefined }
      results.push(row)
      console.log(JSON.stringify(row))
    }
  }
  const failed = results.filter(r => r.status === 'FAIL').length
  console.log(JSON.stringify({ checks: results.length, passed: results.length - failed, failed,
    scope: 'bounded local synthetic fixtures; no live service calls' }))
  process.exitCode = failed ? 1 : 0
}
