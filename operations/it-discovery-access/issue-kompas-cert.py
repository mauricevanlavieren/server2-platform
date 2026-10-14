"""Owner terminal only: issue a NEW Kompas leaf with existing encrypted CA.
Never runs CA bootstrap, exports CA key, prints key data or modifies old certificates.
"""
import os,secrets,subprocess,stat
from pathlib import Path
os.umask(0o077)
base=Path('/home/mau/.local/share/server2-security')
expected='B594E1A7B63480355A40BBDA1BC114E04D9F8C20F274E9F9FA11344BC7AB7588'
def run(args,**kwargs):return subprocess.run(args,check=True,**kwargs)
for name in ('ca.key.pem','ca.crt.pem'):
 p=base/name;s=p.lstat()
 if not stat.S_ISREG(s.st_mode) or p.is_symlink() or s.st_uid!=os.getuid() or s.st_mode&0o077:raise SystemExit('Unsafe CA metadata; STOP')
fp=subprocess.check_output(['openssl','x509','-in',str(base/'ca.crt.pem'),'-noout','-fingerprint','-sha256'],text=True).strip().split('=')[1].replace(':','')
if fp!=expected:raise SystemExit('CA fingerprint mismatch')
folder=base/'kompas-ssh'
if folder.exists() or folder.is_symlink():raise SystemExit('STOP: Kompas certificate directory already exists; no overwrite')
folder.mkdir(mode=0o700)
profile=folder/'kompas.cnf';profile.write_text('''[req]
prompt=no
distinguished_name=subject
req_extensions=request_extensions
[subject]
CN=kompas.home.arpa
[request_extensions]
subjectAltName=DNS:kompas.home.arpa
[leaf_extensions]
basicConstraints=critical,CA:false
keyUsage=critical,digitalSignature
extendedKeyUsage=serverAuth
subjectKeyIdentifier=hash
authorityKeyIdentifier=keyid,issuer
subjectAltName=DNS:kompas.home.arpa
''')
key=folder/'kompas.key.pem';csr=folder/'kompas.csr.pem';cert=folder/'kompas.crt.pem'
run(['openssl','genpkey','-algorithm','EC','-pkeyopt','ec_paramgen_curve:P-256','-out',str(key)])
run(['openssl','req','-new','-sha256','-key',str(key),'-config',str(profile),'-out',str(csr)])
print('Enter EXISTING CA passphrase only at the OpenSSL hidden terminal prompt. Do not share it.',flush=True)
run(['openssl','x509','-req','-sha256','-days','90','-in',str(csr),'-CA',str(base/'ca.crt.pem'),'-CAkey',str(base/'ca.key.pem'),'-set_serial','0x'+secrets.token_hex(16),'-extfile',str(profile),'-extensions','leaf_extensions','-out',str(cert)])
run(['openssl','verify','-CAfile',str(base/'ca.crt.pem'),'-purpose','sslserver','-verify_hostname','kompas.home.arpa',str(cert)])
run(['openssl','x509','-in',str(cert),'-checkend','604800','-noout'])
run(['openssl','x509','-in',str(cert),'-noout','-subject','-issuer','-dates','-fingerprint','-sha256'])
print('PASS: NEW Kompas leaf issued and chain/hostname/validity verified. No Kubernetes, trust-store or existing certificate changes. Private material remains outside Git.')
