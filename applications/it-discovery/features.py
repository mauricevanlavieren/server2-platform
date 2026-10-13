"""Kompas v1: persistent fictional projects, telemetry alerts and evidence reports."""
import json,time,html,urllib.parse,threading,hashlib
from pathlib import Path
STEPS=['Nieuwe opdracht','Intake','Scope & toestemming','Discovery','Inventarisatie','Visualisatie','Risicoanalyse','Advies','Verbeterplan','Menselijke goedkeuring','Uitvoering (registratie)','Validatie','Opleverrapport','Nazorg']
STATUSES=['Nog niet begonnen','Bezig','Wacht op goedkeuring','Afgerond','Geblokkeerd']
KINDS={'technical':'Technische nulmeting','inventory':'IT-inventarisatie','risk':'Security-risicoanalyse','advice':'Verbeteradvies','installation':'Implementatieplan','management':'Managementsamenvatting','delivery':'Opleverrapport'}
FIELDS=('customer','description','scope','consent','assets','findings','risks','recommendations','approved_by','execution_plan','rollback_plan','report','aftercare')
def setup(a):
 global app
 app=a
 with app.db() as c:c.executescript('CREATE TABLE IF NOT EXISTS projects(id INTEGER PRIMARY KEY, content TEXT NOT NULL, updated REAL);CREATE TABLE IF NOT EXISTS alerts(id TEXT PRIMARY KEY,bad INTEGER,good INTEGER,active INTEGER,message TEXT,observed REAL);CREATE TABLE IF NOT EXISTS telemetry(time REAL,content TEXT);')
def validate_project(data):
 if not isinstance(data,dict) or data.get('synthetic') is not True:raise ValueError('Only fictional projects')
 if set(data)-set(FIELDS)-{'synthetic','steps','id'}:raise ValueError('Unknown project field')
 p={k:data.get(k,'') for k in FIELDS}
 if any(not isinstance(v,str) or len(v)>6000 for v in p.values()) or not 1<=len(p['customer'])<=120:raise ValueError('Invalid project')
 steps=data.get('steps',[STATUSES[0]]*len(STEPS))
 if not isinstance(steps,list) or len(steps)!=len(STEPS) or any(x not in STATUSES for x in steps):raise ValueError('Invalid steps')
 if any(x==STATUSES[3] for x in steps[2:]) and not p['consent'].strip():raise ValueError('Recorded consent required')
 if any(x==STATUSES[3] for x in steps[9:]) and not p['approved_by'].strip():raise ValueError('Named human decision required')
 if steps[10]==STATUSES[3] and (steps[9]!=STATUSES[3] or not p['execution_plan'].strip() or not p['rollback_plan'].strip()):raise ValueError('Approval, execution and rollback plan required')
 p.update(synthetic=True,steps=steps);return p
def projects():
 with app.db() as c:return [dict(json.loads(r['content']),id=r['id'],updated=r['updated']) for r in c.execute('SELECT * FROM projects ORDER BY id DESC')]
def save_project(data):
 p=validate_project(data);id=data.get('id')
 with app.db() as c:
  if id is None:id=c.execute('INSERT INTO projects(content,updated) VALUES(?,?)',(json.dumps(p),time.time())).lastrowid
  else:
   if not isinstance(id,int) or c.execute('UPDATE projects SET content=?,updated=? WHERE id=?',(json.dumps(p),time.time(),id)).rowcount!=1:raise ValueError('Unknown project')
  c.execute('INSERT INTO audit VALUES(?,?,?)',(time.time(),'project_saved','Fictional project '+str(id)+'; human decisions recorded, never executed'))
 return id
def host():
 path=Path('/status/host.json')
 try:
  d=json.loads(path.read_text());assert d['host']=='mau2' and isinstance(d['time'],(int,float));return d
 except (OSError,ValueError,KeyError,AssertionError):return {'status':'UNKNOWN','reason':'Host telemetry not yet installed/available','time':0,'backup':{},'filesystems':[],'smart':{'status':'UNKNOWN'}}
def evaluate(signals,now=None):
 now=now or time.time()
 with app.db() as c:
  for key,(bad,message) in signals.items():
   r=c.execute('SELECT * FROM alerts WHERE id=?',(key,)).fetchone();b=(r['bad'] if r else 0)+1 if bad else 0;g=0 if bad else (r['good'] if r else 0)+1;active=bool(r['active']) if r else False
   if b>=3:active=True
   if g>=2:active=False
   c.execute('INSERT OR REPLACE INTO alerts VALUES(?,?,?,?,?,?)',(key,b,g,int(active),message,now))
def sample():
 h=host();s=app.state('live');now=time.time();signals={'host_stale':(now-h.get('time',0)>180,'Hostmetingen ontbreken of zijn ouder dan 3 minuten')}
 for name,result in h.get('availability',{}).items():signals['availability:'+name]=(result.get('status')!='PASS','HTTP/DNS beschikbaarheidscontrole mislukt: '+name)
 for fs in h.get('filesystems',[]):signals['disk:'+fs['path']]=(fs['percent']>=85,'Disk ≥85% gebruikt: '+fs['path'])
 b=h.get('backup',{});signals['backup']=(b.get('status')!='PASS' or now-b.get('time',0)>36*3600,'Backup mislukt, onbekend of ouder dan 36 uur')
 signals['node']=(not any(a['kind']=='node' and a['facts'].get('ready') and now-a['observed']<180 for a in s['assets']),'Node niet Ready of discovery ontbreekt')
 for a in s['assets']:
  if a['kind']=='deployment':signals['app:'+a['name']]=(a['facts'].get('ready',0)<a['facts'].get('replicas',1),'Applicatie niet Ready: '+a['name']+' (Kubernetes-status, geen end-to-end bereikbaarheidstest)')
 history=s['history'];last=history[-1] if history else {};signals['cpu']=(last.get('cpu',0)>3400,'CPU langdurig boven 85% van vier cores')
 mem=h.get('memory',{});signals['ram']=(bool(mem) and mem.get('MemAvailable',0)<mem.get('MemTotal',1)*.15,'Beschikbaar RAM langdurig onder 15%')
 if h.get('smart',{}).get('status')=='FAIL':signals['smart']=(True,'SMART meldt diskproblemen')
 evaluate(signals,now)
 with app.db() as c:
  c.execute('INSERT INTO telemetry VALUES(?,?)',(now,json.dumps(h)));c.execute('DELETE FROM telemetry WHERE time<?',(now-14*86400,))
def monitor():
 h=host();now=time.time()
 with app.db() as c:
  alerts=[dict(r) for r in c.execute('SELECT * FROM alerts ORDER BY active DESC,id')];history=[{'time':r['time'],**json.loads(r['content'])} for r in c.execute('SELECT * FROM telemetry ORDER BY time DESC LIMIT 120')][::-1]
 return {'host':h,'stale':now-h.get('time',0)>180,'alerts':alerts,'history':history,'notifications':'PENDING: externe telefoonprovider/token vereist','hysteresis':'3 opeenvolgende minuutmetingen voor alarm; 2 voor herstel','availability_scope':'Host HTTP/DNS checks zijn begrensde echte controles; Kubernetes Ready blijft afzonderlijk bewijs','pvc_usage':'UNKNOWN: capaciteit bekend, werkelijk gebruik nog niet gemeten'}
def report(dataset,kind,project_id=None):
 if kind not in KINDS:raise ValueError('Unknown report')
 s=app.state(dataset);p=next((p for p in projects() if str(p['id'])==str(project_id)),None) if project_id else None
 if project_id and p is None:raise ValueError('Unknown project')
 lines=['# Kompas · '+KINDS[kind],'','Datum: '+time.strftime('%Y-%m-%d %H:%M UTC',time.gmtime()),'','> Deterministische rapportage; geen echte AI. Menselijke verificatie vereist.','', '## Scope en toestemming',p['scope'] if p else 'Alleen mau2 read-only metadata / afgescheiden fictieve demo.',p['consent'] if p else 'Geen toestemming voor wijzigingen afgeleid uit dit rapport.','','## Vastgestelde feiten','| Asset | Type | Bron / zekerheid |','|---|---|---|']
 def cell(v):return str(v).replace('|','\\|').replace('\n',' ')
 for a in s['assets'][:100]:lines.append('| '+ ' | '.join(cell(x) for x in (a['name'],a['kind'],a['facts'].get('source',a['facts'].get('confidence','onbekend'))))+' |')
 sections={'technical':['Technische bevindingen','Capaciteit en continuïteit'],'inventory':['Inventaris en eigenaar','Afhankelijkheden'],'risk':['Risicoprioriteiten','Mitigaties'],'advice':['Aanbevelingen','Prioriteit en vervolgstappen'],'installation':['Uitvoeringsplan','Rollbackplan','Validatiecriteria'],'management':['Managementbeeld','Beslissingen en prioriteiten'],'delivery':['Uitgevoerde werkzaamheden (registratie)','Validatie','Nazorg']}
 for title in sections[kind]:
  key={'Uitvoeringsplan':'execution_plan','Rollbackplan':'rollback_plan','Nazorg':'aftercare','Aanbevelingen':'recommendations','Risicoprioriteiten':'risks','Validatie':'report'}.get(title,'findings')
  lines+=['','## '+title,p.get(key,'') if p and p.get(key) else 'Nog te verifiëren / vast te leggen; geen conclusie zonder bewijs.']
 lines+=['','## Afgeleide conclusies']
 for risk in app.DemoAdvisor().analyze(s)['risks']:lines+=['- **'+risk['priority']+'** '+risk['title']+' — bron: '+risk['evidence']]
 lines+=['','## Aannames','Geen automatische risicoacceptatie. Metadatarelaties bewijzen geen netwerkflows.','','## Nog te verifiëren','SMART/hostbronversheid, end-to-end beschikbaarheid, off-host herstel en klantisolatie afzonderlijk beoordelen.','','## Menselijke beslissing',p.get('approved_by','Niet vastgelegd') if p else 'Niet vastgelegd','Geen uitvoeringsfunctie. Goedkeuring is uitsluitend registratie, nooit automatische systeemwijziging.']
 return '\n'.join(lines)+'\n'
def print_html(markdown):
 return '<!doctype html><html lang="nl"><meta charset="utf-8"><title>Kompas rapport</title><style>body{font:12pt system-ui;max-width:900px;margin:40px auto;color:#182540}pre{white-space:pre-wrap;font:inherit;line-height:1.6}@media print{body{margin:15mm}a{display:none}}</style><a href="#">Gebruik browser Afdrukken → Opslaan als PDF</a><pre>'+html.escape(markdown)+'</pre></html>'
def handler(base):
 class V1Handler(base):
  def do_GET(self):
   if not self.validhost():return self.send(403,{'error':'Local operator access only'})
   u=urllib.parse.urlsplit(self.path);q=urllib.parse.parse_qs(u.query)
   try:
    if u.path=='/api/projects':return self.send(200,{'projects':projects(),'steps':STEPS,'statuses':STATUSES})
    if u.path=='/api/monitoring':return self.send(200,monitor())
    if u.path=='/api/report':
     text=report(q.get('dataset',['demo'])[0],q.get('kind',['management'])[0],q.get('project',[None])[0]);printing=q.get('format',[''])[0]=='print'
     return self.send(200,print_html(text) if printing else text,'text/html; charset=utf-8' if printing else 'text/markdown; charset=utf-8')
    if u.path=='/api/runbook':return self.send(200,'# Restore\nGeen live data overschrijven. Herstel eerst geïsoleerd met root-only Restic-toegang; verifieer hashes, SQLite en Git. Volg docs/server/it-discovery/README.md in server2-platform. Off-host kopie en wachtwoordescrow vereist voor hostverlies.','text/markdown; charset=utf-8')
   except (ValueError,KeyError):return self.send(400,{'error':'Invalid request'})
   return super().do_GET()
  def do_POST(self):
   path=urllib.parse.urlsplit(self.path).path
   if path not in ('/api/projects','/api/toolkit'):return super().do_POST()
   try:
    if not self.validhost() or self.headers.get('Origin')!='http://'+self.headers.get('Host',''):return self.send(403,{'error':'Local origin required'})
    size=int(self.headers.get('Content-Length','0'))
    if not 0<size<=app.MAX_BODY:return self.send(413,{'error':'Invalid size'})
    data=json.loads(self.rfile.read(size))
    if path=='/api/toolkit':
     if data.get('schema')!='kompas.discovery.v1' or data.get('source_host')!='mau2' or data.get('consent') is not True or data.get('read_only') is not True:raise ValueError('Unapproved scope')
     rows=data['assets']
     if not isinstance(rows,list) or len(rows)>50:raise ValueError('Invalid rows')
     with app.db() as c:
      for row in rows:
       if row.get('kind')!='host' or row.get('name')!='mau2' or not isinstance(row.get('facts'),dict):raise ValueError('Unexpected host')
       allowed={'os','kernel','architecture','cpu_count','memory','root_filesystem','source'}
       if set(row['facts'])-allowed:raise ValueError('Unexpected facts')
       facts=dict(row['facts'],source='Operator-import; unverified facts',confidence='unverified-import')
       c.execute('INSERT OR REPLACE INTO assets VALUES(?,?,?,?,?,?)',('toolkit-mau2','toolkit','mau2','host',json.dumps(facts),time.time()))
     return self.send(200,{'imported':len(rows),'dataset':'toolkit','verified':False})
    id=save_project(data);return self.send(200,{'id':id,'execution_enabled':False})
   except (ValueError,TypeError,KeyError):return self.send(400,{'error':'Invalid fictional project or missing approval/scope'})
   except Exception:return self.send(503,{'error':'Save unavailable; retry safely'})
 return V1Handler
