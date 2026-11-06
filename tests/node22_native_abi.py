# Licensed under the Apache License, Version 2.0. See LICENSE and NOTICE.
import argparse,base64,hashlib,json,pathlib,subprocess
p=argparse.ArgumentParser();p.add_argument('--base',required=True);p.add_argument('--candidate',required=True);p.add_argument('--output',type=pathlib.Path,required=True);p.add_argument('--addon-output',type=pathlib.Path);a=p.parse_args()
flags=['docker','run','--pull=never','--rm','-i','--network','none','--read-only','--tmpfs','/tmp:rw,exec,nosuid,size=64m','--memory','256m','--cpus','1','--pids-limit','128','--cap-drop=ALL','--security-opt=no-new-privileges']
source="""#include <node_api.h>
#include <wand/MagickWand.h>
static napi_value version(napi_env env, napi_callback_info info) {
 size_t n=0; const char *v=MagickGetVersion(&n); napi_value out;
 napi_create_string_utf8(env,v,NAPI_AUTO_LENGTH,&out); return out;
}
static napi_value init(napi_env env,napi_value exports) {
 napi_value fn; napi_create_function(env,"version",NAPI_AUTO_LENGTH,version,0,&fn);
 napi_set_named_property(env,exports,"version",fn); return exports;
}
NAPI_MODULE(NODE_GYP_MODULE_NAME,init)
"""
builder="""import base64,json,pathlib,shlex,subprocess,sys
p=pathlib.Path('/tmp/probe.c');p.write_text(sys.stdin.read())
flags=shlex.split(subprocess.check_output(['pkg-config','--cflags','--libs','MagickWand'],text=True))
subprocess.run(['cc','-shared','-fPIC','-I/usr/local/include/node',str(p),'-o','/tmp/probe.node',*flags],check=True)
print(json.dumps({'bytes':base64.b64encode(pathlib.Path('/tmp/probe.node').read_bytes()).decode(),'linked':subprocess.check_output(['ldd','/tmp/probe.node'],text=True)}))
"""
r=subprocess.run(flags+['--entrypoint','python3',a.base,'-c',builder],input=source,text=True,capture_output=True,timeout=45)
assert r.returncode==0,r.stderr
built=json.loads(r.stdout)
binary=base64.b64decode(built['bytes'],validate=True)
if a.addon_output: a.addon_output.write_bytes(binary)
runner="""const fs=require('fs');const payload=JSON.parse(fs.readFileSync(0,'utf8'));fs.writeFileSync('/tmp/probe.node',Buffer.from(payload.bytes,'base64')); console.log(JSON.stringify({node:process.version,uid:process.getuid(),library:require('/tmp/probe.node').version()}));"""
checks=[]
for label,image in [('prior-image-control',a.base),('candidate-old-compiled-addon',a.candidate)]:
 r=subprocess.run(flags+['--entrypoint','node',image,'-e',runner],input=json.dumps({'bytes':built['bytes']}),text=True,capture_output=True,timeout=30)
 checks.append({'check':label,'image':image,'status':'PASS' if r.returncode==0 else 'FAIL','exitCode':r.returncode,'stdout':r.stdout,'stderr':r.stderr})
 if label=='prior-image-control': assert r.returncode==0,r.stderr
result={'sourceSha256':hashlib.sha256(source.encode()).hexdigest(),'addonSha256':hashlib.sha256(binary).hexdigest(),'linkedLibraries':built['linked'],'checks':checks}
a.output.write_text(json.dumps(result,indent=2)+'\n'); print(json.dumps({'checks':checks}))
raise SystemExit(1 if any(x['status']=='FAIL' for x in checks) else 0)

