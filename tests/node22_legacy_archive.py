# Licensed under the Apache License, Version 2.0. See LICENSE and NOTICE.
"""Compile with the prior image, then execute that exact archive on the candidate."""
import argparse
import hashlib
import json
import pathlib
import subprocess
import time
import urllib.error
import urllib.request

parser = argparse.ArgumentParser()
parser.add_argument('--base-image', required=True)
parser.add_argument('--candidate-image', required=True)
parser.add_argument('--report-dir', required=True)
args = parser.parse_args()
report = pathlib.Path(args.report_dir)
report.mkdir(parents=True, exist_ok=True)
builder = '''import base64, io, json, os, pathlib, subprocess, tempfile, zipfile
root=pathlib.Path(tempfile.mkdtemp()); src=root/'src'; dst=root/'dst'; src.mkdir(); dst.mkdir()
(src/'index.js').write_text("function main(a){return {q:require('query-string').parse(a.query).q,uid:process.getuid()};}")
os.environ['__OW_EXECUTION_ENV']=os.environ['OW_EXECUTION_ENV']
subprocess.run(['/bin/compile','main',str(src),str(dst)],check=True)
archive=io.BytesIO()
with zipfile.ZipFile(archive,'w') as z:
 for p in dst.iterdir(): z.write(p,p.name)
print(json.dumps({'archive':base64.b64encode(archive.getvalue()).decode(),'marker':(dst/'exec.env').read_text()}))
'''
compiled = json.loads(subprocess.check_output([
    'docker', 'run', '--rm', '-i', '--network', 'none', '--read-only',
    '--tmpfs', '/tmp:rw,nosuid,size=64m', '--cpus', '1', '--memory', '256m',
    '--cap-drop=ALL', '--security-opt=no-new-privileges', '--entrypoint', 'python3',
    args.base_image, '-'], input=builder.encode()))
assert compiled['marker'] == 'apacheopenserverless/nodejs-22.23.2'
cid = subprocess.check_output([
    'docker', 'run', '--rm', '-d', '--cpus', '1', '--memory', '256m',
    '--cap-drop=ALL', '--security-opt=no-new-privileges',
    '-p', '127.0.0.1::8080', args.candidate_image], text=True).strip()
checks = []
try:
    port = json.loads(subprocess.check_output(['docker', 'inspect', cid]))[0]['NetworkSettings']['Ports']['8080/tcp'][0]['HostPort']
    def request(route, body):
        req = urllib.request.Request('http://127.0.0.1:' + port + route,
                                     data=json.dumps(body).encode(), headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=15) as response:
            return json.load(response)
    for attempt in range(30):
        try:
            request('/init', {'value': {'name': 'synthetic-legacy', 'main': 'main',
                                      'code': compiled['archive'], 'binary': True}})
            break
        except urllib.error.HTTPError:
            raise
        except (urllib.error.URLError, ConnectionError):
            time.sleep(.2)
    else:
        raise RuntimeError('proxy unavailable')
    for query, expected in [('q=caff%C3%A8+%2B+%E2%82%AC', 'caffè + €'), ('q=one&q=two', ['one', 'two'])]:
        result = request('/run', {'value': {'query': query}})
        assert result == {'q': expected, 'uid': 65534}, result
        checks.append({'check': 'actual-prior-compiled-archive', 'status': 'PASS'})
finally:
    (report/'proxy.log').write_bytes(subprocess.check_output(['docker', 'logs', cid], stderr=subprocess.STDOUT))
    subprocess.run(['docker', 'stop', cid], check=True, stdout=subprocess.DEVNULL)
result = {'baseImage': args.base_image, 'candidateImage': args.candidate_image,
          'archiveSha256': hashlib.sha256(compiled['archive'].encode()).hexdigest(),
          'archiveHashEncoding': 'base64-text', 'checks': checks}
(report/'results.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result))
