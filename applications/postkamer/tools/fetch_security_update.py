"""Fetch checksum-pinned stable APKs; apk verifies trusted signatures during build.
No package DB removal, untrusted packages, mixed distributions, or build networking.
"""
import hashlib
from pathlib import Path
import urllib.request

PACKAGES = [{'filename': 'zlib.apk', 'url': 'https://dl-cdn.alpinelinux.org/alpine/v3.23/main/x86_64/zlib-1.3.2-r1.apk', 'sha256': 'ee62e1864c235901e2aa4d1868c7ae8f7cc5d0740a98c48a2525332eb4bfda73', 'version': '1.3.2-r1'}, {'filename': 'libseccomp.apk', 'url': 'https://dl-cdn.alpinelinux.org/alpine/v3.23/main/x86_64/libseccomp-2.6.1-r0.apk', 'sha256': '40132d53050deddad00d74ec304ae766b75a1df967ed10369f5e6736b8f4ac74', 'version': '2.6.1-r0'}]

def verify(data, expected):
    if len(data) > 2 * 1024 * 1024 or hashlib.sha256(data).hexdigest() != expected:
        raise ValueError("Security build input hash/size mismatch; STOP")
    return data

def main():
    directory = Path(__file__).resolve().parents[1] / "vendor"
    directory.mkdir(exist_ok=True)
    for package in PACKAGES:
        target = directory / package["filename"]
        if target.exists():
            verify(target.read_bytes(), package["sha256"])
        else:
            with urllib.request.urlopen(package["url"], timeout=45) as response:
                if response.geturl() != package["url"]:
                    raise ValueError("Unexpected package redirect; STOP")
                data = verify(response.read(2 * 1024 * 1024 + 1), package["sha256"])
            temporary = target.with_suffix(".tmp")
            try:
                temporary.write_bytes(data)
                temporary.replace(target)
            finally:
                temporary.unlink(missing_ok=True)
        print("Verified pinned stable input:", package["filename"], package["version"])

if __name__ == "__main__":
    main()
