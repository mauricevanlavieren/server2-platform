"""Managed Kompas loopback fallback; target verification before connecting."""
import os,subprocess,sys
kubectl='/usr/local/bin/kubectl'
p=subprocess.run([kubectl,'--context','server2','config','view','--minify','-o','jsonpath={.clusters[0].cluster.server}'],capture_output=True,text=True,timeout=8)
if p.returncode or p.stdout!='https://192.168.0.162:6443':raise SystemExit('STOP: server2 context verification failed')
if sys.argv[1:]==['--verify-only']:print('PASS: exact server2 target');raise SystemExit(0)
if sys.argv[1:]:raise SystemExit('Unsupported arguments')
os.execv(kubectl,[kubectl,'--context','server2','-n','it-discovery','port-forward','--address','127.0.0.1','service/it-discovery','8780:8080','--pod-running-timeout=30s'])
