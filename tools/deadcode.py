import os
"""List ELF functions (from symbols.txt) that nothing references: no jal/j target, no word in the file equal to the address,
no lui/addiu or lui/ori pair building it. Usable as code/data caves. usage: python3 tools/deadcode.py [minsize]"""
import struct,sys
d=open(os.environ.get('HCTP_ELF','SLUS_207.87'),'rb').read()
BASE=0x100000; OFF=0x80; END=BASE+0x389800
n=(END-BASE)//4
words=struct.unpack_from('<%dI'%n,d,OFF)
syms=[]
for l in open('symbols.txt'):
    p=l.split()
    if len(p)>=4 and p[2]=='2':
        try: syms.append((int(p[0],16),int(p[1]),p[3]))
        except: pass
syms.sort()
targets=set(); ptrs=set(); hi={}
for i,w in enumerate(words):
    a=BASE+4*i
    if w>>26 in(2,3): targets.add((w&0x3ffffff)<<2)
    if BASE<=w<END: ptrs.add(w)
    op=w>>26
    if op==0xf: hi[(w>>16)&31]=((w&0xffff)<<16,i)
    elif op in(9,0xd) and ((w>>21)&31) in hi:
        v=hi[(w>>21)&31]
        if i-v[1]<8:
            t=v[0]+(w&0xffff if op==0xd else (w&0xffff)-(0x10000 if w&0x8000 else 0))
            ptrs.add(t&0xffffffff)
min_sz=int(sys.argv[1]) if len(sys.argv)>1 else 64
tot=0
for a,s,name in syms:
    if s>=min_sz and a not in targets and a not in ptrs and not name.startswith(('.','@','__')) :
        print('%08x %6d %s'%(a,s,name)); tot+=s
print('total',tot)
