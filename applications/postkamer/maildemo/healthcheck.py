"""Local container/Kubernetes exec healthcheck; no external network."""
import json
import sys
import urllib.request
from .config import load_config

def main():
    try:
        config=load_config()
        opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(f'http://127.0.0.1:{config.port}/healthz',timeout=3) as response:
            body=json.load(response)
        if body.get('status')!='ok' or body.get('messages')!=40 or body.get('fts5') is not True or body.get('sending') is not False or body.get('external_ai') is not False:raise ValueError('Invalid health')
    except Exception:
        print('Postkamer healthcheck failed',file=sys.stderr);return 1
    return 0

if __name__=='__main__':sys.exit(main())
