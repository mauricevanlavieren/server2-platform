"""AMD64 process-scoped Linux seccomp guard; inherited across exec and threads.
Uses kernel classic BPF through libc; no host profile or privilege changes.
"""
import ctypes,errno,json,os,platform,socket,sys
from pathlib import Path
class Filter(ctypes.Structure):
 _fields_=[('code',ctypes.c_ushort),('jt',ctypes.c_ubyte),('jf',ctypes.c_ubyte),('k',ctypes.c_uint32)]
class Program(ctypes.Structure):
 _fields_=[('length',ctypes.c_ushort),('filters',ctypes.POINTER(Filter))]
def status():
 values=dict(line.split(':',1) for line in Path('/proc/self/status').read_text().splitlines() if ':' in line)
 return {k:values[k].strip() for k in ('NoNewPrivs','Seccomp','Seccomp_filters','CapEff','CapPrm','CapAmb')}
def install():
 if platform.machine()!='x86_64':raise RuntimeError('Unsupported architecture')
 before=status()
 if before['NoNewPrivs']!='1' or before['Seccomp']!='2':raise RuntimeError('Missing base restrictions')
 if any(int(before[k],16) for k in ('CapEff','CapPrm','CapAmb')):raise RuntimeError('Unexpected capabilities')
 if len(os.listdir('/proc/self/task'))!=1:raise RuntimeError('Guard must precede threads')
 for fd in Path('/proc/self/fd').iterdir():
  try:target=os.readlink(fd)
  except FileNotFoundError:continue
  if target.startswith('socket:'):raise RuntimeError('Inherited socket descriptor')
 # seccomp_data: arch at 4, syscall at 0, low 32 bits of args[0] at 16.
 # Reject non-amd64 and x32 ABI; deny AF_INET6 for socket and socketpair.
 rules=[(0x20,0,0,4),(0x15,1,0,0xc000003e),(0x06,0,0,0x80000000),
        (0x20,0,0,0),(0x45,0,1,0x40000000),(0x06,0,0,0x80000000),
        (0x15,1,0,41),(0x15,0,3,53),(0x20,0,0,16),
        (0x15,0,1,10),(0x06,0,0,0x00050000|errno.EAFNOSUPPORT),
        (0x06,0,0,0x7fff0000)]
 array=(Filter*len(rules))(*(Filter(*r) for r in rules));program=Program(len(rules),array)
 libc=ctypes.CDLL(None,use_errno=True);libc.prctl.argtypes=[ctypes.c_int,ctypes.c_ulong,ctypes.c_ulong,ctypes.c_ulong,ctypes.c_ulong];libc.prctl.restype=ctypes.c_int
 if libc.prctl(22,2,ctypes.addressof(program),0,0)!=0:raise RuntimeError('Seccomp load failed')
 after=status()
 if int(after['Seccomp_filters'])<=int(before['Seccomp_filters']):raise RuntimeError('Filter not proven')
 try:s=socket.socket(socket.AF_INET6)
 except OSError as e:
  if e.errno!=errno.EAFNOSUPPORT:raise
 else:s.close();raise RuntimeError('IPv6 denial failed')
 with socket.socket(socket.AF_INET):pass
 return {'before':before,'after':after,'ipv6':'EAFNOSUPPORT','ipv4':'socket allowed'}
if __name__=='__main__':
 if sys.argv[1:] not in ([],['--self-test']):raise SystemExit('Unsupported invocation')
 print(json.dumps({'ipv4_guard':install()}),flush=True)
 if sys.argv[1:]==['--self-test']:raise SystemExit(0)
 os.execv(sys.executable,[sys.executable,'-B',str(Path(__file__).with_name('app.py'))])
