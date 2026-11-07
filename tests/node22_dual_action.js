// Licensed under the Apache License, Version 2.0. See LICENSE and NOTICE.
// Synthetic private action, deployed through OPS IDE in the authorized lab.
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const cp = require('node:child_process');
async function main(args) {
  const fixture = JSON.parse(fs.readFileSync('./deployment.json', 'utf8'));
  if (process.env.__OW_NAMESPACE !== fixture.namespace) return {error: 'fixture_namespace_mismatch'};
  const native = require('./probe.node').version();
  const modules = ['aws-s3','minio','mongodb','ollama','openai','openwhisk','pg','redis','uuid'];
  for (const name of modules) require(name);
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'ops-node-dual-'));
  let media;
  try {
    cp.execFileSync('convert', ['-size','2x2','xc:red',path.join(dir,'synthetic.exr')], {timeout:10000, stdio:'pipe'});
    cp.execFileSync('convert', [path.join(dir,'synthetic.exr'),path.join(dir,'synthetic.png')], {timeout:10000, stdio:'pipe'});
    media = cp.execFileSync('identify', ['-format','%m %wx%h',path.join(dir,'synthetic.png')], {encoding:'utf8',timeout:10000});
  } finally { fs.rmSync(dir, {recursive:true, force:true}); }
  const debian = fs.readFileSync('/etc/debian_version','utf8').trim().split('.')[0];
  const marker = process.env.__OW_EXECUTION_ENV;
  return {ok: process.version === 'v22.23.4' && process.getuid() === 65534 &&
      debian === fixture.debian && native.startsWith('ImageMagick '+fixture.magickMajor+'.') &&
      marker === fixture.marker && media === 'PNG 2x2',
    node:process.version, uid:process.getuid(), debian, native, marker, media,
    modules:modules.length, echo:args.nonce};
}
