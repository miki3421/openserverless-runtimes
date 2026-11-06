// Licensed under the Apache License, Version 2.0. See LICENSE and NOTICE.
// Exercise npm workspace selection and packaging entirely offline.
const assert = require('node:assert/strict')
const fs = require('node:fs')
const os = require('node:os')
const path = require('node:path')
const { spawnSync } = require('node:child_process')
const root = fs.mkdtempSync(path.join(os.tmpdir(), 'ops-npm-workspaces-'))
let checks = 0
function pass(name) { checks++; console.log(JSON.stringify({ check: name, status: 'PASS' })) }
function json(file, value) { fs.writeFileSync(path.join(root, file), JSON.stringify(value)) }
function npm(...args) {
  const run = spawnSync(process.execPath,
    ['/usr/local/lib/node_modules/npm/bin/npm-cli.js', ...args], {
      cwd: root, encoding: 'utf8', timeout: 20000, maxBuffer: 2 * 1024 * 1024,
      env: { ...process.env, HOME: root, npm_config_cache: path.join(root, '.cache'),
        npm_config_offline: 'true', npm_config_audit: 'false', npm_config_fund: 'false',
        npm_config_ignore_scripts: 'true', npm_config_update_notifier: 'false' },
    })
  assert.equal(run.status, 0, run.error?.message || run.stderr)
  return JSON.parse(run.stdout)
}
try {
  json('package.json', { name: 'ops-synthetic-root', version: '1.0.0', private: true,
    workspaces: ['packages/*', '!packages/excluded'] })
  for (const name of ['alpha', 'beta', 'excluded']) {
    fs.mkdirSync(path.join(root, 'packages', name), { recursive: true })
    json('packages/' + name + '/package.json', { name: '@ops-synthetic/' + name,
      version: '1.0.0', main: 'index.js', files: ['*.js'],
      ...(name === 'alpha' ? { dependencies: { '@ops-synthetic/beta': '1.0.0' } } : {}) })
    fs.writeFileSync(path.join(root, 'packages', name, 'index.js'), 'module.exports = "synthetic";\n')
    fs.writeFileSync(path.join(root, 'packages', name, 'unlisted.txt'), 'not packaged\n')
  }
  npm('install', '--package-lock-only', '--json')
  const lock = JSON.parse(fs.readFileSync(path.join(root, 'package-lock.json')))
  assert(lock.packages['packages/alpha'] && lock.packages['packages/beta'])
  assert(!lock.packages['packages/excluded'])
  pass('offline_lock_respects_workspace_negation')
  npm('ci', '--json')
  assert(fs.lstatSync(path.join(root, 'node_modules/@ops-synthetic/alpha')).isSymbolicLink())
  assert(fs.lstatSync(path.join(root, 'node_modules/@ops-synthetic/beta')).isSymbolicLink())
  pass('offline_ci_links_local_workspaces')
  const list = npm('ls', '--all', '--json')
  assert(list.dependencies['@ops-synthetic/alpha'] && list.dependencies['@ops-synthetic/beta'])
  assert(!list.dependencies['@ops-synthetic/excluded'])
  pass('dependency_tree_has_no_excluded_workspace')
  const packed = npm('pack', '--dry-run', '--workspaces', '--json')
  assert.equal(packed.length, 2)
  for (const pkg of packed) {
    assert(pkg.files.some(file => file.path === 'index.js'))
    assert(!pkg.files.some(file => file.path === 'unlisted.txt'))
  }
  pass('pack_preserves_files_allowlist')
  const selected = npm('pack', '--dry-run', '--workspace=@ops-synthetic/alpha', '--json')
  assert.equal(selected.length, 1)
  assert.equal(selected[0].name, '@ops-synthetic/alpha')
  pass('named_workspace_selection')
} finally { fs.rmSync(root, { recursive: true, force: true }) }
console.log(JSON.stringify({ checks, status: 'PASS', offline: true, ownedFilesRemoved: true }))
