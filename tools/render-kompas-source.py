"""Offline source ConfigMap generator; no cluster/network operations."""
from pathlib import Path
import json,hashlib
root=Path(__file__).resolve().parents[1];app=root/'applications/it-discovery';base=root/'kubernetes/apps/it-discovery'
data={p.name:p.read_text() for p in app.glob('*.py') if not p.name.startswith('test_')};data.update({p.name:p.read_text() for p in (app/'static').glob('*') if p.is_file()})
name='it-discovery-source-'+hashlib.sha256(json.dumps(data,sort_keys=True).encode()).hexdigest()[:12]
s=json.loads((base/'source.yaml').read_text());s['data']=data;s['metadata']['name']=name;(base/'source.yaml').write_text(json.dumps(s,indent=2)+'\n')
p=base/'deployment.yaml';d=json.loads(p.read_text());v=next(v for v in d['spec']['template']['spec']['volumes'] if v['name']=='source');v['configMap']['name']=name;v['configMap']['items']=[{'key':k,'path':'static/'+k if k.endswith(('.js','.css','.html')) else k} for k in data];p.write_text(json.dumps(d,indent=2)+'\n');print(name)
