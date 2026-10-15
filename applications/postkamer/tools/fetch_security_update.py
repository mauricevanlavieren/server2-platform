"""Fetch the immutable official Debian update before a network-free build."""
import hashlib
from pathlib import Path
import urllib.request
URL='https://security.debian.org/debian-security/pool/updates/main/x/xz-utils/liblzma5_5.8.1-1+deb13u2_amd64.deb'
SHA256='b38acab30f295bf1066a6632e31cbd0a1980f2924b38040cda131d5dea5384ec'
def verify(data):
    if hashlib.sha256(data).hexdigest()!=SHA256:
        raise ValueError('liblzma package SHA256 mismatch; STOP')
    return data
def main():
    target=Path(__file__).resolve().parents[1]/'vendor/liblzma.deb'
    with urllib.request.urlopen(URL,timeout=45) as response:
        if response.geturl()!=URL: raise ValueError('Unexpected package redirect; STOP')
        data=verify(response.read(2*1024*1024+1))
    target.parent.mkdir(exist_ok=True)
    temporary=target.with_suffix('.tmp')
    try:
        temporary.write_bytes(data)
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)
    print('Verified official liblzma5 5.8.1-1+deb13u2')
if __name__=='__main__':main()
