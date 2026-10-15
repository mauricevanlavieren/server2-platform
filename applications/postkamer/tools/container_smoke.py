"""Own local Docker resources only. No cluster commands or remote endpoints."""
import json
from pathlib import Path
import subprocess
import sys
import time
import uuid

image=sys.argv[1] if len(sys.argv)>1 else 'postkamer:phase2'
name='postkamer-smoke-'+uuid.uuid4().hex[:12];volume=name+'-data'
report={'image':image,'checks':{},'measurements':{},'healthRetries':[]}
def docker(*args,timeout=45):
    result=subprocess.run(['docker',*args],text=True,capture_output=True,timeout=timeout)
    if result.returncode:raise RuntimeError(f'Docker {args[0]} failed ({result.returncode}): {result.stderr}')
    return result.stdout.strip()
def code(script):return docker('exec',name,'python','-B','-c',script)
def wait_health():
    end=time.monotonic()+60
    while time.monotonic()<end:
        try:
            r=subprocess.run(['docker','exec',name,'python','-B','-m','maildemo.healthcheck'],capture_output=True,text=True,timeout=min(15,max(1,end-time.monotonic())))
            report['healthRetries'].append({'time':time.time(),'exitcode':r.returncode,'stderr':r.stderr})
            if r.returncode==0:return
        except subprocess.TimeoutExpired:
            report['healthRetries'].append({'time':time.time(),'error':'docker exec timeout'})
        time.sleep(1)
    raise RuntimeError('Health deadline exceeded')
created_volume=False
try:
    docker('volume','create',volume);created_volume=True
    docker('run','-d','--name',name,'--label','postkamer.scope=local-smoke','--network','none','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges','--cpus','0.25','--memory','256m','--pids-limit','64','--mount',f'type=volume,src={volume},dst=/data',image)
    wait_health();report['checks']['health']='PASS'
    report['measurements']['runtime']=json.loads(code("import json,os,sys,sqlite3;print(json.dumps({'uid':os.getuid(),'gid':os.getgid(),'python':sys.version.split()[0],'sqlite':sqlite3.sqlite_version}))"))
    assert report['measurements']['runtime']['uid']==10001
    report['checks']['nonroot']='PASS'
    packaging=json.loads(code("import importlib.util,json;from pathlib import Path;print(json.dumps({'pip':importlib.util.find_spec('pip') is None,'ensurepip':importlib.util.find_spec('ensurepip') is None,'wheel':not Path('/usr/local/lib/python3.13/ensurepip/_bundled/pip-26.2.1-py3-none-any.whl').exists(),'entrypoints':not any(Path('/usr/local/bin').glob('pip*'))}))"))
    assert all(packaging.values()),packaging
    report['measurements']['packaging_absent']=packaging
    report['checks']['unused_packaging_removed']='PASS'
    probe="""from pathlib import Path
import json
r={}
for p in ['/app/forbidden','/tmp/forbidden','/data/allowed']:
 try:
  Path(p).write_text('test');r[p]='writable';Path(p).unlink()
 except OSError:r[p]='blocked'
print(json.dumps(r))"""
    writable=json.loads(code(probe));assert writable=={'/app/forbidden':'blocked','/tmp/forbidden':'blocked','/data/allowed':'writable'}
    report['measurements']['directories']=writable;report['checks']['readonly_root']='PASS'
    sockets=code("from pathlib import Path;print(Path('/proc/net/tcp').read_text())");assert '00000000:223D' in sockets
    report['checks']['ipv4_wildcard_binding']='PASS'
    report['measurements']['stats']=json.loads(docker('stats','--no-stream','--format','{{json .}}',name))
    report['measurements']['cgroups']=json.loads(code("from pathlib import Path;import json;print(json.dumps({p:Path('/sys/fs/cgroup/'+p).read_text().strip() for p in ['cpu.max','memory.max','memory.events']}))"))
    assert report['measurements']['cgroups']['memory.max']==str(256*1024*1024)
    quota,period=map(int,report['measurements']['cgroups']['cpu.max'].split());assert quota/period==0.25
    report['checks']['hard_limits']='PASS'
    script="""import urllib.request,json
base='http://127.0.0.1:8765'
with urllib.request.urlopen(base+'/api/messages/1') as r:d=json.load(r)
q=urllib.request.Request(base+'/api/messages/1/draft',data=json.dumps({'text':'Synthetic persisted container draft','version':d['draft_version']}).encode(),method='PATCH',headers={'Content-Type':'application/json','Origin':base})
with urllib.request.urlopen(q) as r:assert json.load(r)['draft']=='Synthetic persisted container draft'
"""
    code(script);docker('stop','--time','10',name)
    state=json.loads(docker('inspect',name))[0]['State'];assert state['ExitCode']==0 and not state['OOMKilled']
    report['checks']['graceful_stop_no_oom']='PASS'
    docker('start',name);wait_health()
    code("import urllib.request,json;d=json.load(urllib.request.urlopen('http://127.0.0.1:8765/api/messages/1'));assert d['draft']=='Synthetic persisted container draft'")
    report['checks']['draft_survives_restart']='PASS'
    docker('rm','-f',name)
    docker('run','-d','--name',name,'--network','none','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges','--cpus','0.25','--memory','256m','--pids-limit','64','--mount',f'type=volume,src={volume},dst=/data',image)
    wait_health();code("import urllib.request,json;d=json.load(urllib.request.urlopen('http://127.0.0.1:8765/api/messages/1'));assert d['draft']=='Synthetic persisted container draft'")
    report['checks']['draft_survives_container_replacement']='PASS'
    info=json.loads(docker('inspect',name))[0]
    assert info['HostConfig']['NetworkMode']=='none' and not info['NetworkSettings']['Ports']
    report['checks']['no_egress_or_published_ports']='PASS'
    report['checks']['docker_healthcheck_configured']='PASS' if info['Config'].get('Healthcheck') else 'FAIL'
    print(json.dumps(report,indent=2))
finally:
    subprocess.run(['docker','rm','-f',name],capture_output=True,timeout=45)
    if created_volume:docker('volume','rm',volume)
