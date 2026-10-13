# Kompas portable Linux toolkit
Python standard library only, Linux or laptop with Python3/OpenSSH. Fixed permitted SSH target: mau2/server2 (192.168.0.162). No LAN scan, remote target strings or sudo. Windows/WinRM, Kubernetes, Proxmox and network-device adapters are interfaces for later approval, not implemented.

`python3 -B kompas.py --target server2 --consent --output ./mau2.json --csv ./mau2.csv --import-local`

Local-only discovery: `--target local --consent --output ./local.json`. This reads your own machine; imports outside mau2 are refused. Existing output files are never overwritten. Files are private mode0600. Keep real host exports outside Git. Review results before sharing.

Schema: `kompas.discovery.v1`, source_host, observed Unix timestamp, read_only=true, assets[{name,kind,facts}]. Facts are whitelisted OS/kernel/CPU count/RAM/root-filesystem capacity; no credentials, users, process arguments, SSH keys, environment variables or full file reads. Import is marked unverified, never a trusted live discovery assertion. Adapter contract: collect approved explicit target → validate → export → human review → import; no execution methods. CSV is a summary; JSON preserves structured facts. Authentication or timeout errors never trigger escalation.
