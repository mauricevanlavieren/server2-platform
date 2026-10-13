"""Fixed-scope mau2 telemetry publisher. Never reads backup passwords or cluster Secrets."""
import json,os,subprocess,time,shutil,urllib.request,socket,struct,ipaddress
from pathlib import Path
if os.uname().nodename!='mau2':raise SystemExit('Wrong host')
def run(args):
 p=subprocess.run(args,capture_output=True,text=True,timeout=8)
 if p.returncode:raise RuntimeError('status command failed')
 return p.stdout
now=time.time();mem={x.split(':')[0]:int(x.split()[1])*1024 for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith(('MemTotal:','MemAvailable:'))}
disks=[]
for target in ('/','/var/lib/rancher/k3s/storage','/var/backups/restic'):
 d=shutil.disk_usage(target);disks.append(dict(path=target,total=d.total,free=d.free,used=d.used,percent=round(100*d.used/d.total,1)))
net={}
for line in Path('/proc/net/dev').read_text().splitlines()[2:]:
 name,values=line.split(':');name=name.strip();v=values.split()
 if name!='lo' and not name.startswith(('veth','cni','flannel')):net[name]={'rx_bytes':int(v[0]),'tx_bytes':int(v[8])}
io={}
for line in Path('/proc/diskstats').read_text().splitlines():
 v=line.split()
 if len(v)>13 and v[2].startswith(('sd','nvme')):io[v[2]]={'read_bytes':int(v[5])*512,'written_bytes':int(v[9])*512}
backup={};p=Path('/var/lib/it-discovery-backup/last-result.json')
if p.exists():
 raw=json.loads(p.read_text());backup={k:raw.get(k) for k in ('status','time','files_restored_verified','sqlite_integrity','git_fsck','same_disk_only')}
for name in ('last-success.json','last-failure.json'):
 p=Path('/var/lib/it-discovery-backup')/name
 if p.exists():
  d=json.loads(p.read_text());backup[name[:-5]]={k:d.get(k) for k in ('status','time','error_type')}
backup['timer_active']=run(['/usr/bin/systemctl','is-active','it-discovery-backup.timer']).strip()=='active';backup['repository']='/var/backups/restic';backup['retention']='7 daily / 4 weekly / 3 monthly'
smart={'status':'UNKNOWN','reason':'smartctl unavailable; not installed automatically'}
if Path('/usr/sbin/smartctl').exists():
 p=subprocess.run(['/usr/sbin/smartctl','-j','-H','-A','/dev/sda'],capture_output=True,text=True,timeout=8)
 try:
  d=json.loads(p.stdout);smart={'status':'PASS' if d.get('smart_status',{}).get('passed') is True else 'FAIL' if d.get('smart_status',{}).get('passed') is False else 'UNKNOWN','temperature':d.get('temperature',{}).get('current'),'exit_code':p.returncode}
 except (ValueError,KeyError):smart={'status':'UNKNOWN','reason':'SMART response unavailable'}
status={'time':now,'host':'mau2','uptime_seconds':float(Path('/proc/uptime').read_text().split()[0]),'memory':mem,'filesystems':disks,'network':net,'disk_io':io,'smart':smart,'backup':backup,'source':'fixed read-only host collector','filesystem_coverage':'fixed paths; no recursive file reads'}
# Preserve only observed success/failure timestamps, never repository credentials.
historyfile=Path('/var/lib/it-discovery-backup/observed-status-history.json')
history=json.loads(historyfile.read_text()) if historyfile.exists() else {}
if backup.get('status') in ('PASS','FAIL'):history['last-success' if backup['status']=='PASS' else 'last-failure']={k:backup.get(k) for k in ('status','time')}
historyfile.write_text(json.dumps(history));backup.update(history)
# Explicit existing services on mau2 only; never follow redirects or scan networks.
class NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,*args,**kwargs):return None
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())
availability={}
k=['/usr/local/bin/k3s','kubectl','--request-timeout=6s','--cache-dir=/var/lib/it-discovery-backup/kube-cache']
for namespace,name,path,hostheader in [('forgejo','forgejo','/api/healthz',None),('dashy','dashy','/',None),('kube-system','traefik','/','dashboard.home.arpa'),('it-discovery','it-discovery','/healthz','127.0.0.1:8080')]:
 label=namespace+'/'+name
 try:
  service=json.loads(run(k+['get','service',name,'-n',namespace,'-o','json']));ip=service['spec']['clusterIP'];assert ipaddress.ip_address(ip) in ipaddress.ip_network('10.43.0.0/16')
  port=next(x['port'] for x in service['spec']['ports'] if x.get('protocol','TCP')=='TCP' and x['port']!=443)
  req=urllib.request.Request('http://'+ip+':'+str(port)+path,headers={'Host':hostheader} if hostheader else {})
  with opener.open(req,timeout=3) as response:availability[label]={'status':'PASS' if response.status==200 else 'FAIL','http_status':response.status,'time':now}
 except Exception:availability[label]={'status':'FAIL','time':now,'reason':'Bounded HTTP check failed; no response content logged'}
try:
 ident=os.getpid()%65536;query=struct.pack('!HHHHHH',ident,256,1,0,0,0)+b''.join(bytes([len(x)])+x.encode() for x in 'kubernetes.default.svc.cluster.local'.split('.'))+b'\0'+struct.pack('!HH',1,1)
 with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as sock:
  sock.settimeout(3);sock.sendto(query,('10.43.0.10',53));answer,_=sock.recvfrom(1024)
 header=struct.unpack('!HHHHHH',answer[:12]);assert header[0]==ident and header[1]&15==0 and header[3]>0
 availability['DNS']={'status':'PASS','time':now,'method':'Actual internal UDP A query'}
except Exception:availability['DNS']={'status':'FAIL','time':now,'reason':'Internal UDP DNS query failed'}
status['availability']=availability

# Dynamic observation data; declarative ConfigMap metadata is owned by Flux.
k=['/usr/local/bin/k3s','kubectl','--request-timeout=10s','--cache-dir=/var/lib/it-discovery-backup/kube-cache']
obj={'apiVersion':'v1','kind':'ConfigMap','metadata':{'name':'kompas-host-status','namespace':'it-discovery'},'data':{'host.json':json.dumps(status)}}
p=subprocess.run(k+['apply','--server-side','--field-manager=kompas-observer','-f','-'],input=json.dumps(obj),capture_output=True,text=True,timeout=20)
if p.returncode:raise SystemExit('Telemetry publish FAIL; no response content logged')
print('Host status published; no credentials collected')
