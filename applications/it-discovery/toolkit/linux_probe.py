"""Whitelisted Linux facts only. No process args, users, env, files or network scan."""
import os,json,platform,time,shutil
from pathlib import Path
if platform.system()!='Linux':raise SystemExit('Linux required')
osrelease={}
for line in Path('/etc/os-release').read_text().splitlines():
 if '=' in line:
  k,v=line.split('=',1)
  if k in ('NAME','VERSION_ID','PRETTY_NAME'):osrelease[k]=v.strip('"')
d=shutil.disk_usage('/');m={}
for line in Path('/proc/meminfo').read_text().splitlines():
 if line.startswith(('MemTotal:','MemAvailable:')):m[line.split(':')[0]]=int(line.split()[1])*1024
print(json.dumps({'schema':'kompas.discovery.v1','source_host':platform.node(),'observed':time.time(),'read_only':True,'assets':[{'name':platform.node(),'kind':'host','facts':{'os':osrelease,'kernel':platform.release(),'architecture':platform.machine(),'cpu_count':os.cpu_count(),'memory':m,'root_filesystem':{'total':d.total,'free':d.free},'source':'explicit Linux probe; unverified import'}}]}))
