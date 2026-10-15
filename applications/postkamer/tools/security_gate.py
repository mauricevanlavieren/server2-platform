"""Fail on any High/Critical; no ignore-unfixed or implicit risk acceptance."""
import json
import sys

def assess(report):
    if not isinstance(report,dict) or not report.get('Results') or not report.get('Metadata',{}).get('OS'):raise ValueError('Missing mandatory scan evidence')
    if not any(r.get('Class')=='os-pkgs' and r.get('Packages') for r in report['Results']):raise ValueError('Missing OS inventory')
    return [v for r in report['Results'] for v in r.get('Vulnerabilities',[]) if v.get('Severity') not in ('LOW','MEDIUM')]

def main():
    try:
        with open(sys.argv[1]) as source:findings=assess(json.load(source))
        print(json.dumps({'status':'FAIL' if findings else 'PASS','blockingFindings':len(findings)}));return 1 if findings else 0
    except Exception:
        print('FAIL: invalid or missing scan evidence',file=sys.stderr);return 2
if __name__=='__main__':sys.exit(main())
