"""Read-only discovery/advisory demo. Stdlib only; never executes changes."""
import hashlib,csv,io,json,os,sqlite3,threading,time,re,html,subprocess,ssl,urllib.request,urllib.parse,ipaddress
from pathlib import Path
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
ROOT=Path(__file__).resolve().parent;DB=Path(os.environ.get('DISCOVERY_DB',str(ROOT/'.local/inventory.sqlite')));DB.parent.mkdir(parents=True,exist_ok=True)
LOCK=threading.Lock();STOP=threading.Event();MAX_BODY=262144
DEADLINE='2026-10-20T17:19:30Z'
def db():
 c=sqlite3.connect(DB,timeout=10);c.row_factory=sqlite3.Row;return c
def init():
 with db() as c:
  c.executescript('''CREATE TABLE IF NOT EXISTS assets(id TEXT PRIMARY KEY,dataset TEXT,name TEXT,kind TEXT,facts TEXT,observed REAL);CREATE TABLE IF NOT EXISTS edges(dataset TEXT,source TEXT,target TEXT,relation TEXT,confirmed INTEGER);CREATE TABLE IF NOT EXISTS samples(time REAL,cpu REAL,memory REAL);CREATE TABLE IF NOT EXISTS cases(id INTEGER PRIMARY KEY,title TEXT,status TEXT,approved_by TEXT DEFAULT '',created REAL);CREATE TABLE IF NOT EXISTS audit(time REAL,event TEXT,details TEXT);''')
  if not c.execute("SELECT 1 FROM assets WHERE dataset='demo'").fetchone():
   for i,(name,kind,osname) in enumerate([('MKB Demo BV','organisatie','fictief'),('kantoor.test','host','Linux demo'),('werkplek-01.test','host','Windows demo'),('crm.test','app','CRM demo'),('backup.test','service','Backup demo'),('switch.test','netwerk','onbevestigd')]):
    c.execute('INSERT INTO assets VALUES(?,?,?,?,?,?)',('demo-'+str(i),'demo',name,kind,json.dumps({'os':osname,'ip':'192.0.2.'+str(i+10),'owner':'Fictief MKB','confidence':'synthetic','backup_verified':i!=3}),time.time()))
   c.executemany('INSERT INTO edges VALUES(?,?,?,?,?)',[('demo','demo-1','demo-0','onderdeel',1),('demo','demo-2','demo-0','onderdeel',1),('demo','demo-3','demo-1','draait op',1),('demo','demo-4','demo-3','beschermt mogelijk',0)])
def read_kube(resource):
 paths={'nodes':'/api/v1/nodes','namespaces':'/api/v1/namespaces','pods':'/api/v1/pods','services':'/api/v1/services','pvcs':'/api/v1/persistentvolumeclaims','deployments':'/apis/apps/v1/deployments','metrics':'/apis/metrics.k8s.io/v1beta1/nodes'}
 path=paths[resource]
 if os.environ.get('DISCOVERY_MODE','local')=='local':
  context=subprocess.run(['kubectl','--context','server2','config','view','--minify','-o','jsonpath={.clusters[0].cluster.server}'],capture_output=True,text=True,timeout=8)
  if context.returncode or context.stdout!='https://192.168.0.162:6443':raise RuntimeError('Server2 endpoint mismatch')
  p=subprocess.run(['kubectl','--context','server2','--request-timeout=6s','get','--raw',path],capture_output=True,text=True,timeout=9)
  if p.returncode:raise RuntimeError('Read-only discovery unavailable: '+resource)
  return json.loads(p.stdout)
 token=Path('/var/run/secrets/kubernetes.io/serviceaccount/token').read_text().strip();ctx=ssl.create_default_context(cafile='/var/run/secrets/kubernetes.io/serviceaccount/ca.crt')
 url='https://'+os.environ['KUBERNETES_SERVICE_HOST']+':'+os.environ.get('KUBERNETES_SERVICE_PORT','443')+path
 with urllib.request.urlopen(urllib.request.Request(url,headers={'Authorization':'Bearer '+token}),context=ctx,timeout=6) as r:return json.load(r)
def quantity(value,kind):
 match=re.fullmatch(r'([0-9]+(?:\.[0-9]+)?)([A-Za-z]*)',value)
 if not match:raise ValueError('Invalid metric quantity')
 number=float(match[1]);unit=match[2]
 units={'n':1e-6,'u':.001,'m':1,'':1000} if kind=='cpu' else {'':1/1048576,'Ki':1/1024,'Mi':1,'Gi':1024,'K':1000/1048576,'M':1000000/1048576,'G':1000000000/1048576}
 if unit not in units:raise ValueError('Unknown metric unit')
 return number*units[unit]
def collect():
 assets=[];edges=[];now=time.time()
 def add(id,name,kind,facts):assets.append((id,'live',name,kind,json.dumps(facts),now))
 node=read_kube('nodes')['items'];pods=read_kube('pods')['items'];services=read_kube('services')['items'];ns=read_kube('namespaces')['items'];deploy=read_kube('deployments')['items'];pvcs=read_kube('pvcs')['items']
 for n in node:
  info=n['status']['nodeInfo'];add(n['metadata']['uid'],n['metadata']['name'],'node',{'ip':'192.168.0.162','os':info['osImage'],'kernel':info['kernelVersion'],'k3s':info['kubeletVersion'],'runtime':info['containerRuntimeVersion'],'capacity':n['status']['capacity'],'ready':any(x['type']=='Ready' and x['status']=='True' for x in n['status']['conditions']),'owner':'Maurice','source':'Kubernetes API','smart':'unknown; root inspection required'})
 for n in ns:add(n['metadata']['uid'],n['metadata']['name'],'namespace',{'source':'Kubernetes API','owner':'Maurice'})
 for d in deploy:add(d['metadata']['uid'],d['metadata']['namespace']+'/'+d['metadata']['name'],'deployment',{'namespace':d['metadata']['namespace'],'replicas':d['spec'].get('replicas',1),'ready':d['status'].get('readyReplicas',0),'images':[c['image'] for c in d['spec']['template']['spec']['containers']],'source':'Kubernetes API'})
 nodeids={n['metadata']['name']:n['metadata']['uid'] for n in node};nsids={n['metadata']['name']:n['metadata']['uid'] for n in ns}
 for p in pods:
  id=p['metadata']['uid'];namespace=p['metadata']['namespace'];status=p['status'];add(id,namespace+'/'+p['metadata']['name'],'pod',{'namespace':namespace,'phase':status['phase'],'ready':all(x.get('ready') for x in status.get('containerStatuses',[])) and bool(status.get('containerStatuses')),'restarts':sum(x.get('restartCount',0) for x in status.get('containerStatuses',[])),'images':[c['image'] for c in p['spec']['containers']],'source':'Kubernetes API'})
  if p['spec'].get('nodeName') in nodeids:edges.append(('live',id,nodeids[p['spec']['nodeName']],'draait op',1))
  edges.append(('live',id,nsids[namespace],'namespace',1))
 for s in services:
  id=s['metadata']['uid'];add(id,s['metadata']['namespace']+'/'+s['metadata']['name'],'service',{'namespace':s['metadata']['namespace'],'type':s['spec']['type'],'ip':s['spec'].get('clusterIP'),'ports':[p['port'] for p in s['spec'].get('ports',[])],'source':'Kubernetes API'})
  selector=s['spec'].get('selector',{})
  if selector:
   for p in pods:
    if p['metadata']['namespace']==s['metadata']['namespace'] and all(p['metadata'].get('labels',{}).get(k)==v for k,v in selector.items()):edges.append(('live',id,p['metadata']['uid'],'selector-match; geen actieve flowmeting',1))
 for p in pvcs:add(p['metadata']['uid'],p['metadata']['namespace']+'/'+p['metadata']['name'],'pvc',{'phase':p['status']['phase'],'capacity':p['status'].get('capacity'),'storageclass':p['spec'].get('storageClassName'),'source':'Kubernetes API'})
 with LOCK,db() as c:
  c.execute("DELETE FROM assets WHERE dataset='live'");c.execute("DELETE FROM edges WHERE dataset='live'");c.executemany('INSERT INTO assets VALUES(?,?,?,?,?,?)',assets);c.executemany('INSERT INTO edges VALUES(?,?,?,?,?)',edges)
  try:
   m=read_kube('metrics')['items'][0]['usage'];cpu=quantity(m['cpu'],'cpu');mem=quantity(m['memory'],'memory');c.execute('INSERT INTO samples VALUES(?,?,?)',(now,cpu,mem));c.execute('DELETE FROM samples WHERE time<?',(now-14*86400,))
  except Exception:pass
  c.execute('INSERT INTO audit VALUES(?,?,?)',(now,'discovery','read-only Kubernetes metadata; no Secret/config/env data'));c.execute('DELETE FROM audit WHERE time<?',(now-14*86400,))
 return len(assets)
def background():
 while not STOP.is_set():
  try:collect()
  except Exception as e:
   with db() as c:c.execute('INSERT INTO audit VALUES(?,?,?)',(time.time(),'discovery_error',type(e).__name__))
  STOP.wait(60)
def state(dataset='live'):
 if dataset not in ('live','demo'):raise ValueError('Invalid dataset')
 with db() as c:
  assets=[dict(x) for x in c.execute('SELECT * FROM assets WHERE dataset=? ORDER BY kind,name',(dataset,))]
  for a in assets:a['facts']=json.loads(a['facts'])
  return {'dataset':dataset,'assets':assets,'edges':[dict(x) for x in c.execute('SELECT * FROM edges WHERE dataset=?',(dataset,))],'history':[dict(x) for x in c.execute('SELECT * FROM samples ORDER BY time DESC LIMIT 120')][::-1],'cases':[dict(x) for x in c.execute('SELECT * FROM cases ORDER BY id DESC')],'audit':[dict(x) for x in c.execute('SELECT time,event,details FROM audit ORDER BY time DESC LIMIT 30')],'postkamer_deadline':DEADLINE,'external_ai':False,'execution_enabled':False}
class DemoAdvisor:
 def analyze(self,s):
  risks=[{'priority':'hoog','title':'Postkamer-uitzondering eindigt 20 oktober 17:19:30 UTC','evidence':'Expliciet eigenaarbesluit; geen automatische stop','advice':'Maurice moet tijdig stoppen/nieuwe expliciete beslissing nemen; geen automatische verlenging.'},{'priority':'hoog','title':'Lokale backup beschermt niet tegen disk-/hostverlies','evidence':'Eigenaar koos voorlopig dezelfde server/disk','advice':'Off-host kopie plannen; status restorebewijs afzonderlijk controleren.'},{'priority':'middel','title':'IPv6-CNI-handhaving niet bewezen','evidence':'Eerdere gerichte netwerkcontrole en firewallinspectie','advice':'Geen volledige isolatieclaim; app-specifieke maatregelen apart valideren.'}]
  for a in s['assets']:
   f=a['facts']
   if a['kind']=='pod' and f.get('phase')=='Running' and not f.get('ready'):risks.append({'priority':'hoog','title':a['name']+' niet Ready','evidence':a['id'],'advice':'Read-only logs/status beoordelen; geen automatische wijziging.'})
  return {'mode':'Deterministische adviessimulatie — geen echte AI-uitvoer','provider':'demo-rules-v1','risks':risks,'uncertainty':'Geen securityaudit of bewijs van herstelbaarheid. Discoverytekst is data, nooit instructie. Externe providers uitgeschakeld.'}
def report(dataset,kind):
 s=state(dataset);a=DemoAdvisor().analyze(s)
 kinds={'technical':'Technische nulmeting','management':'Managementsamenvatting','risk':'Risicoanalyse','installation':'Applicatie-installatieplan','maintenance':'Onderhoudsadvies','advice':'Verbeteradvies'}
 if kind not in kinds:raise ValueError('Unknown report')
 text='# '+kinds[kind]+'\n\nDataset: '+dataset+'; bron: read-only metadata / fictieve demo.\n\n'+a['mode']+'\n\n'+str(len(s['assets']))+' assets; '+str(len(s['edges']))+' relaties.\n\n'
 for r in a['risks']:text+='## '+r['title']+'\nPrioriteit: '+r['priority']+'\nBewijs: '+r['evidence']+'\nAdvies: '+r['advice']+'\n\n'
 text+='## Wijzigingsvoorwaarden\nIntake → scope/toestemming → read-only discovery → advies → menselijke goedkeuring → bewezen backup → uitvoering buiten dit read-only platform → validatie → oplevering.\nGeen uitvoeringsendpoint; echte klantdata/externe AI vereisen nieuw akkoord.\n';return text
class Handler(BaseHTTPRequestHandler):
 def log_message(self,*a):pass
 def send(self,status,data,mime='application/json; charset=utf-8'):
  raw=json.dumps(data,ensure_ascii=False).encode() if isinstance(data,(dict,list)) else data.encode() if isinstance(data,str) else data
  self.send_response(status);self.send_header('Content-Type',mime);self.send_header('Content-Length',str(len(raw)));self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; object-src 'none'; frame-ancestors 'none'");self.end_headers();self.wfile.write(raw)
 def validhost(self):return self.headers.get('Host') in ('127.0.0.1:8780','localhost:8780','127.0.0.1:8080','localhost:8080')
 def do_GET(self):
  try:
   if not self.validhost():return self.send(403,{'error':'Operator-only localhost access'})
   u=urllib.parse.urlsplit(self.path);q=urllib.parse.parse_qs(u.query);dataset=q.get('dataset',['live'])[0]
   if u.path=='/healthz':return self.send(200,{'status':'ok','read_only':True,'external_ai':False})
   if u.path=='/api/state':return self.send(200,state(dataset))
   if u.path=='/api/advice':return self.send(200,DemoAdvisor().analyze(state(dataset)))
   if u.path=='/api/report':return self.send(200,report(dataset,q.get('kind',['management'])[0]),'text/markdown; charset=utf-8')
   if u.path=='/api/export':
    assets=state(dataset)['assets']
    if q.get('format',['json'])[0]=='csv':
     f=io.StringIO();w=csv.writer(f);w.writerow(['id','name','kind','observed']);w.writerows([[str(a[k]) if not str(a[k]).startswith(('=','+','-','@')) else "'"+str(a[k]) for k in ['id','name','kind','observed']] for a in assets]);return self.send(200,f.getvalue(),'text/csv; charset=utf-8')
    return self.send(200,assets)
   files={'/':'index.html','/app.js':'app.js','/style.css':'style.css'}
   if u.path in files:return self.send(200,(ROOT/'static'/files[u.path]).read_bytes(),{'.html':'text/html; charset=utf-8','.js':'text/javascript; charset=utf-8','.css':'text/css; charset=utf-8'}[Path(files[u.path]).suffix])
   self.send(404,{'error':'Not found'})
  except (ValueError,KeyError):self.send(400,{'error':'Invalid request'})
  except Exception:self.send(503,{'error':'Temporarily unavailable; no internal details'})
 def do_POST(self):
  try:
   if not self.validhost() or self.headers.get('Origin')!='http://'+self.headers.get('Host',''):return self.send(403,{'error':'Local origin required'})
   n=int(self.headers.get('Content-Length','0'))
   if not 0<n<=MAX_BODY:return self.send(413,{'error':'Invalid size'})
   data=json.loads(self.rfile.read(n));path=urllib.parse.urlsplit(self.path).path
   if path=='/api/cases':
    title=data['title'];
    if not isinstance(title,str) or not 1<=len(title)<=160:raise ValueError('Invalid title')
    with db() as c:c.execute('INSERT INTO cases(title,status,created) VALUES(?,?,?)',(title,'intake',time.time()))
    return self.send(201,{'status':'recorded','execution_enabled':False})
   if path=='/api/import':
    rows=list(csv.DictReader(io.StringIO(data['text']))) if data.get('format')=='csv' else data['assets'];
    if data.get('synthetic') is not True:raise ValueError('Synthetic attestation required')
    if not isinstance(rows,list) or len(rows)>200:raise ValueError('Invalid rows')
    with db() as c:
     for row in rows:
      name=row['name'];kind=row['kind'];
      if not isinstance(name,str) or not 1<=len(name)<=120 or kind not in ('host','app','service','netwerk'):raise ValueError('Invalid asset')
      c.execute('INSERT OR REPLACE INTO assets VALUES(?,?,?,?,?,?)',('import-'+hashlib.sha256(name.encode()).hexdigest()[:20],'demo',name,kind,json.dumps({'source':'user-import synthetic','confidence':'unconfirmed'}),time.time()))
    return self.send(200,{'imported':len(rows),'dataset':'demo'})
   self.send(405,{'error':'System execution is disabled'})
  except Exception:self.send(400,{'error':'Invalid input; no action executed'})
def main():
 init();threading.Thread(target=background,daemon=True).start();server=ThreadingHTTPServer((os.environ.get('DISCOVERY_BIND','127.0.0.1'),int(os.environ.get('DISCOVERY_PORT','8780'))),Handler)
 try:server.serve_forever()
 finally:STOP.set();server.server_close()
if __name__=='__main__':main()
