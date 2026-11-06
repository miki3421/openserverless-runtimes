# Licensed under the Apache License, Version 2.0. See LICENSE and NOTICE.
"""Synthetic owner/peer checks; explicit lab config, no credentials in output."""
import argparse
import base64
import json
import pathlib
import secrets
import urllib.error
import urllib.request

parser = argparse.ArgumentParser()
parser.add_argument('--config', type=pathlib.Path, required=True)
parser.add_argument('--api', required=True)
args = parser.parse_args()
config = json.loads(args.config.read_text())
assert config.get('scope', {}).get('lab') is True
assert set(config['apps']) == {'alpha', 'beta'}
assert config['apps']['alpha']['namespace'] != config['apps']['beta']['namespace']
assert args.api == 'http://127.0.0.1:30233', 'Run only on the explicitly selected lab host'
code = '''async function main(args) {
const modules=['aws-s3','minio','mongodb','ollama','openai','openwhisk','pg','redis','uuid'];
for(const m of modules)require(m);
const fs=require('node:fs'),path=require('node:path'),{createRequire}=require('node:module');
const consumer=createRequire(require.resolve('query-string'));
const decoder=consumer('decode-uri-component');
const pkg=JSON.parse(fs.readFileSync(path.join(path.dirname(consumer.resolve('decode-uri-component')),'package.json')));
const esm=await import('decode-uri-component');
const query=require('query-string');
const client=new (require('minio').Client)({endPoint:'synthetic.invalid',region:'us-east-1',useSSL:true,accessKey:'synthetic-access',secretKey:'synthetic-secret'});
const signed=new URL(await client.presignedGetObject('synthetic-bucket','folder/a b.txt',300));
return {marker:args.marker,node:process.version,uid:process.getuid(),modules:modules.length,
  decoded:query.parse('q=caff%C3%A8+%2B+%E2%82%AC').q,decoder:pkg.version,
  sameExport:decoder===esm.default,s3:signed.searchParams.has('X-Amz-Signature')};
}'''

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *arguments, **kwargs):
        return None

opener = urllib.request.build_opener(NoRedirect)
rows, created = [], []
def request(tenant, path, method, body=None):
    auth = base64.b64encode(config['apps'][tenant]['auth'].encode()).decode()
    req = urllib.request.Request(args.api + path, method=method,
                                 data=json.dumps(body).encode() if body is not None else None,
                                 headers={'Authorization': 'Basic ' + auth, 'Content-Type': 'application/json'})
    try:
        with opener.open(req, timeout=75) as response:
            return response.status, response.read(65537)
    except urllib.error.HTTPError as error:
        return error.code, error.read(65537)

try:
    for tenant in ['alpha', 'beta']:
        name = 'node-decoder-' + secrets.token_hex(6)
        path = '/api/v1/namespaces/_/actions/' + name
        status, _ = request(tenant, path + '?overwrite=false', 'PUT',
                            {'exec': {'kind': 'nodejs:22', 'code': code}, 'limits': {'timeout': 60000, 'memory': 256}})
        assert status in (200, 201), ('create', tenant, status)
        created.append((tenant, path))
        for n in range(2):
            marker = 'synthetic-' + secrets.token_hex(8)
            status, raw = request(tenant, path + '?blocking=true&result=true', 'POST', {'marker': marker})
            assert status == 200 and len(raw) <= 65536, ('invoke', tenant, status)
            result = json.loads(raw)
            assert result == {'marker': marker, 'node': 'v22.23.4', 'uid': 65534, 'modules': 9,
                              'decoded': 'caffè + €', 'decoder': '0.5.1', 'sameExport': True, 's3': True}, 'unexpected action result'
            rows.append({'tenant': tenant, 'check': 'node-decoder-owner', 'invocation': n + 1, 'status': 'PASS'})
        peer = 'beta' if tenant == 'alpha' else 'alpha'
        target = '/api/v1/namespaces/' + config['apps'][tenant]['namespace'] + '/actions/' + name
        status, _ = request(peer, target + '?blocking=true&result=true', 'POST', {})
        rows.append({'tenant': tenant, 'check': 'peer-denial', 'statusCode': status, 'status': 'PASS' if status == 403 else 'FAIL'})
        assert status == 403
finally:
    for tenant, path in created:
        status, _ = request(tenant, path, 'DELETE')
        rows.append({'tenant': tenant, 'check': 'synthetic-action-cleanup', 'status': 'PASS' if status == 200 else 'FAIL'})
    print(json.dumps({'checks': rows}))
if any(row['status'] != 'PASS' for row in rows):
    raise SystemExit(1)
