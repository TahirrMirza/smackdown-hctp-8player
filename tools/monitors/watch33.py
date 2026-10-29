import sys,time,os,re
sys.path.insert(0,os.path.join(os.path.dirname(os.path.abspath(__file__)),'..'))
import pine
log=os.path.expanduser('~/Library/Application Support/PCSX2/logs/emulog.txt')
f=open(log,errors='ignore'); f.seek(0,2)
bad=re.compile(r'unaligned|Unrecognized|exception|crash|Error|Fatal|Jump to|TLB Miss|Bus Error|Reserved',re.I)
skip=re.compile(r'PINE|Pad:|DS2',re.I)
last=None; t0=time.time(); lastpoll=0
while time.time()-t0<900:
    for l in f.readlines():
        if bad.search(l) and not skip.search(l): print('LOG',l.strip()[:200],flush=True)
    if time.time()-lastpoll>2:
        lastpoll=time.time()
        try:
            s=(pine.read32(0x110790),pine.read32(0x110794),tuple(pine.read32(0x526EA0+4*i)!=0 for i in range(8)))
        except Exception as e:
            s=('pine-down',)
        if s!=last: print(time.strftime('%H:%M:%S'),'PASS/HAVE/gchar',s,flush=True); last=s
    time.sleep(0.5)
