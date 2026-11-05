"""Local Docker compatibility checks for an explicit Python action-loop image.

No cluster access. All HTTP endpoints bind loopback; fixture compilation uses
network-disabled containers. Pass --base-image to exercise real old archives.
"""
import argparse
import base64
import io
import json
from pathlib import Path
import subprocess
import time
import urllib.error
import urllib.request
import zipfile

CODE = '''import os, sys, importlib, json, datetime
from bson import BSON
import yaml, dns.name, requests, urllib3, virtualenv
from pg8000 import dbapi
from minio import Minio

def main(args):
    names = ['boto3', 'minio', 'pg8000', 'redis', 'pymongo', 'kafka', 'bcrypt',
             'requests', 'httplib2', 'dateutil', 'yaml', 'virtualenv']
    for name in names: importlib.import_module(name)
    value = {'marker': args['marker'], 'unicode': 'caffè ☕', 'number': 42}
    assert BSON.encode(value).decode() == value
    assert yaml.safe_load(yaml.safe_dump(value, allow_unicode=True)) == value
    assert dns.name.from_text('fixture.invalid.').to_text() == 'fixture.invalid.'
    assert requests.Request('GET', 'https://fixture.invalid/', params={'a': 'a b'}).prepare().url.endswith('a=a+b')
    Minio('localhost:9000', access_key='synthetic', secret_key='synthetic', secure=False)
    return {'marker': args['marker'], 'python': '.'.join(map(str,sys.version_info[:3])), 'uid': os.getuid(), 'unicode': value['unicode']}
'''
EXTENDED = '''from nltk.stem import PorterStemmer
from bs4 import BeautifulSoup
import plotly.graph_objects as go
import langchain, openai, ollama, feedparser, joblib, langdetect

def main(args):
    assert PorterStemmer().stem('running') == 'run'
    assert BeautifulSoup('<p>fixture</p>', 'html.parser').p.text == 'fixture'
    assert go.Figure(data=go.Bar(y=[1, 2])).to_dict()['data'][0]['y'] == [1, 2]
    return {'marker': args['marker'], 'extended': True}
'''

# Build an offline virtualenv with the supplied image's actual tooling, then
# package a synthetic module. The launcher must activate it after extraction.
VENV_FIXTURE = r'''
import pathlib, subprocess, tempfile, zipfile, io, sys
with tempfile.TemporaryDirectory() as tmp:
    root = pathlib.Path(tmp)
    venv = root/'virtualenv'
    subprocess.run([sys.executable, '-m', 'virtualenv', '--no-download',
                    '--no-periodic-update', '--app-data', str(root/'cache'),
                    str(venv)], check=True, stdout=sys.stderr)
    subprocess.run([str(venv/'bin/python'), '-m', 'pip', '--version'], check=True, stdout=sys.stderr)
    site = next((venv/'lib').glob('python*/site-packages'))
    (site/'ops_fixture.py').write_text('VALUE = "bundled-virtualenv"\n')
    data = io.BytesIO()
    with zipfile.ZipFile(data, 'w', zipfile.ZIP_DEFLATED) as out:
        out.writestr('__main__.py', 'import ops_fixture\ndef main(args):\n    assert ops_fixture.VALUE == "bundled-virtualenv"\n    return {"marker": args["marker"], "venv": True}\n')
        for path in venv.rglob('*'):
            if path.is_file() and not path.is_symlink():
                out.write(path, str(path.relative_to(root)))
    sys.stdout.buffer.write(data.getvalue())
'''


def archive(files):
    data = io.BytesIO()
    with zipfile.ZipFile(data, 'w') as out:
        for name, value in files.items():
            out.writestr(name, value)
    return data.getvalue()


def request(base, path, obj):
    req = urllib.request.Request(base+path, data=json.dumps(obj).encode(), headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=60) as response:
        return json.load(response)


def exercise(image, name, code, binary, output, expected_python, negative=False):
    cid = subprocess.check_output(['docker', 'run', '-d', '--rm', '--cap-drop=ALL',
                                  '--security-opt=no-new-privileges', '-p', '127.0.0.1::8080', image], text=True).strip()
    rows = []
    try:
        port = json.loads(subprocess.check_output(['docker', 'inspect', cid]))[0]['NetworkSettings']['Ports']['8080/tcp'][0]['HostPort']
        base = 'http://127.0.0.1:'+port
        for _ in range(50):
            try:
                request(base, '/init', {'value': {'name': 'synthetic', 'main': 'main', 'code': code, 'binary': binary}})
                break
            except urllib.error.HTTPError as error:
                if negative:
                    assert error.code == 502
                    logs = subprocess.check_output(['docker', 'logs', cid], stderr=subprocess.STDOUT)
                    assert b'execution environment version mismatch' in logs, logs
                    return [{'case': name, 'status': 'PASS', 'oracle': 'wrong_environment_rejected_at_init'}]
                raise
            except (urllib.error.URLError, ConnectionError):
                time.sleep(.2)
        else:
            raise RuntimeError('runtime_not_ready')
        for invocation in range(2):
            marker = name+'-'+str(invocation)
            if negative:
                try:
                    result = request(base, '/run', {'value': {'marker': marker}})
                except urllib.error.HTTPError as error:
                    assert error.code >= 400
                else:
                    assert result.get('error'), result
                rows.append({'case': name, 'status': 'PASS', 'oracle': 'wrong_environment_rejected'})
                break
            result = request(base, '/run', {'value': {'marker': marker}})
            assert result['marker'] == marker, result
            if 'python' in result:
                assert result['python'] == expected_python and result['uid'] == 65534, result
                assert result['unicode'] == 'caffè ☕', result
            rows.append({'case': name, 'invocation': invocation+1, 'status': 'PASS'})
    finally:
        (output/(name+'.log')).write_bytes(subprocess.check_output(['docker', 'logs', cid], stderr=subprocess.STDOUT))
        subprocess.run(['docker', 'stop', cid], check=True, stdout=subprocess.DEVNULL)
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--image', required=True)
    parser.add_argument('--base-image', required=True)
    parser.add_argument('--python', required=True)
    parser.add_argument('--marker', default='apacheopenserverless/runtime-python-v3.12.14')
    parser.add_argument('--cross-minor-image')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--extended', action='store_true')
    args = parser.parse_args()
    # Missing build outputs are a harness precondition, never an implicit pull.
    for image in {args.image, args.base_image, args.cross_minor_image} - {None}:
        subprocess.run(['docker', 'image', 'inspect', image], check=True, stdout=subprocess.DEVNULL)
    args.output.mkdir(parents=True, exist_ok=True)
    rows = []
    fixtures = [('plain', CODE, False), ('source-zip', base64.b64encode(archive({'__main__.py': CODE})).decode(), True)]
    compiled = subprocess.run(['docker', 'run', '--rm', '-i', '--network', 'none', args.base_image, '-compile', 'main'], input=CODE.encode(), capture_output=True, check=True)
    (args.output/'old-compile.log').write_bytes(compiled.stderr)
    with zipfile.ZipFile(io.BytesIO(compiled.stdout)) as z:
        members = {name:z.read(name) for name in z.namelist()}
    assert members['exec.env'] == args.marker.encode()
    compiled_label = 'same-minor-compiled' if args.image == args.base_image else 'actual-old-compiled'
    fixtures.append((compiled_label, base64.b64encode(compiled.stdout).decode(), True))
    for label, image in [('old', args.base_image), ('current', args.image)]:
        result = subprocess.run(['docker', 'run', '--rm', '--network', 'none',
                                 '--entrypoint', 'python', image, '-c', VENV_FIXTURE],
                                capture_output=True, check=True)
        (args.output/(label+'-virtualenv-build.log')).write_bytes(result.stderr)
        fixtures.append((label+'-virtualenv', base64.b64encode(result.stdout).decode(), True))
    if args.extended:
        fixtures.append(('extended-modules', EXTENDED, False))
    for name, code, binary in fixtures:
        rows += exercise(args.image, name, code, binary, args.output, args.python)
    members['exec.env'] = b'intentionally-incompatible-fixture'
    rows += exercise(args.image, 'wrong-environment', base64.b64encode(archive(members)).decode(), True, args.output, args.python, negative=True)
    if args.cross_minor_image:
        foreign = subprocess.run(['docker', 'run', '--rm', '-i', '--network', 'none',
                                  args.cross_minor_image, '-compile', 'main'],
                                 input=CODE.encode(), capture_output=True, check=True)
        rows += exercise(args.image, 'cross-minor-archive', base64.b64encode(foreign.stdout).decode(),
                         True, args.output, args.python, negative=True)
    subprocess.run(['docker', 'run', '--rm', '--network', 'none', '--entrypoint', 'python', args.image, '-m', 'pip', 'check'], check=True)
    (args.output/'results.json').write_text(json.dumps(rows, indent=2)+'\n')
    print(json.dumps(rows))


if __name__ == '__main__':
    main()
