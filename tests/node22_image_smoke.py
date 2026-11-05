import subprocess,json,time,urllib.request,urllib.error,pathlib,base64,io,zipfile
import argparse,tempfile
parser=argparse.ArgumentParser()
parser.add_argument('--image',default='localhost/ops-advanced-nodejs:22-20261105-r3')
parser.add_argument('--report-dir',required=True)
options=parser.parse_args()
root=pathlib.Path(options.report_dir);root.mkdir(parents=True,exist_ok=True)
source=pathlib.Path(__file__).resolve().parents[1]
rows=[]
cases=[('plain','function main(a){return {value:a.value+1,node:process.version,uid:process.getuid()};}',False,{'value':41},lambda x:x['value']==42 and x['node']=='v22.23.4' and x['uid']==65534),('async','async function main(a){return {echo:await Promise.resolve(a.text)};}',False,{'text':'synthetic'},lambda x:x=={'echo':'synthetic'})]
b=io.BytesIO()
with zipfile.ZipFile(b,'w') as z:
 z.writestr('index.js','const helper=require("./helper"); function main(a){return helper(a)}; exports.main=main;')
 z.writestr('helper.js','module.exports=a=>({echo:a.text,aws:typeof require("aws-s3")});')
cases.append(('zip',base64.b64encode(b.getvalue()).decode(),True,{'text':'zip-fixture'},lambda x:x['echo']=='zip-fixture'))
b=io.BytesIO()
with zipfile.ZipFile(b,'w') as z:
 z.writestr('exec', '#!/bin/bash\ncd "$(dirname "$0")"\n[ "$__OW_EXECUTION_ENV" = "$(cat exec.env)" ] || exit 42\nnode exec__.js\n')
 z.writestr('exec.env','apacheopenserverless/nodejs-22.23.2')
 z.writestr('exec__.js',(source/'runtime/nodejs/v22/lib/launcher.js').read_text())
 z.writestr('index__.js','module.exports=a=>({echo:a.text});')
cases.append(('legacy-compiled',base64.b64encode(b.getvalue()).decode(),True,{'text':'compiled-fixture'},lambda x:x=={'echo':'compiled-fixture'}))
for name,code,binary,args,check in cases:
 cid=subprocess.check_output(['docker','run','-d','--rm','--cap-drop=ALL','--security-opt=no-new-privileges','-p','127.0.0.1::8080',options.image],text=True).strip()
 try:
  port=json.loads(subprocess.check_output(['docker','inspect',cid]))[0]['NetworkSettings']['Ports']['8080/tcp'][0]['HostPort'];base='http://127.0.0.1:'+port
  def request(path,obj):
   req=urllib.request.Request(base+path,data=json.dumps(obj).encode(),headers={'Content-Type':'application/json'})
   with urllib.request.urlopen(req,timeout=30) as r:return json.load(r)
  for i in range(30):
   try:
    request('/init',{'value':{'name':'synthetic','main':'main','code':code,'binary':binary}});break
   except ConnectionError:time.sleep(.2)
   except urllib.error.URLError as e:
    if isinstance(e,urllib.error.HTTPError):raise
    time.sleep(.2)
  else:raise RuntimeError('init unavailable')
  for n in range(2):
   result=request('/run',{'value':args});assert check(result),result
   rows.append({'case':name,'invocation':n+1,'status':'PASS'})
 finally:
  (root/('node-'+name+'.log')).write_bytes(subprocess.check_output(['docker','logs',cid],stderr=subprocess.STDOUT));subprocess.run(['docker','stop',cid],check=True,stdout=subprocess.DEVNULL)
(root/'node-local-test.json').write_text(json.dumps(rows,indent=2)+'\n')
print(json.dumps(rows))
