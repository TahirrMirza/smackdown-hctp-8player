import os
import struct
d=open(os.environ.get('HCTP_ELF','SLUS_207.87'),'rb').read()
sym_off,sym_size=0x412d10,0x5f9b0; str_off=0x389950
out=[]
for i in range(sym_size//16):
    n,v,sz,info,oth,sh=struct.unpack_from('<IIIBBH',d,sym_off+16*i)
    s=d[str_off+n:d.index(b'\0',str_off+n)].decode('latin1')
    out.append((v,sz,info&15,s))
out.sort()
with open('symbols.txt','w') as f:
    for v,sz,t,s in out: f.write('%08x %6d %d %s\n'%(v,sz,t,s))
print(len(out))
