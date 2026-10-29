import sys,time; sys.path.insert(0,os.path.join(os.path.dirname(os.path.abspath(__file__)),'..'))
import pine
pp=pine.read32(0x4ffa00)
last=None; t0=time.time()
while time.time()-t0<240:
    try:
        s=tuple((pine.read32(pp+i*0xC0+4)&0xFFFF, pine.read32(pp+i*0xC0+0xa8)&0xFFFF) for i in range(8))
    except Exception as e:
        s=None
    if s and s!=last and any(x[0] or x[1] for x in s):
        print(time.strftime('%H:%M:%S'),' '.join('p%d:%04x/%04x'%(i,a,b) for i,(a,b) in enumerate(s) if a or b),flush=True)
    last=s
    time.sleep(0.05)
