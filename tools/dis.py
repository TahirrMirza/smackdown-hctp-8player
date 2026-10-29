import os
import struct,sys
d=open(os.environ.get('HCTP_ELF','SLUS_207.87'),'rb').read()
def w(a):
    o=a-0x100000+0x80; return struct.unpack('<I',d[o:o+4])[0]
R=['zero','at','v0','v1','a0','a1','a2','a3','t0','t1','t2','t3','t4','t5','t6','t7','s0','s1','s2','s3','s4','s5','s6','s7','t8','t9','k0','k1','gp','sp','fp','ra']
def s16(x): return x-0x10000 if x&0x8000 else x
def dis(a):
    x=w(a); op=x>>26; rs=(x>>21)&31; rt=(x>>16)&31; rd=(x>>11)&31; im=x&0xffff; sa=(x>>6)&31
    if x==0: return 'nop'
    if op==0:
        f=x&63
        n={0x21:'addu',0x2d:'daddu',0x25:'or',0x24:'and',0x2a:'slt',0x2b:'sltu',0x23:'subu',0x26:'xor',0x27:'nor'}.get(f)
        if n: return f'{n} {R[rd]},{R[rs]},{R[rt]}'
        if f==0: return f'sll {R[rd]},{R[rt]},{sa}'
        if f==2: return f'srl {R[rd]},{R[rt]},{sa}'
        if f==3: return f'sra {R[rd]},{R[rt]},{sa}'
        if f==8: return f'jr {R[rs]}'
        if f==9: return f'jalr {R[rs]}'
        return f'special {f:#x}'
    if op==2: return f'j {((x&0x3ffffff)<<2):#x}'
    if op==3: return f'jal {((x&0x3ffffff)<<2):#x}'
    if op in(4,5,6,7,0x14,0x15): return f'{ {4:"beq",5:"bne",6:"blez",7:"bgtz",0x14:"beql",0x15:"bnel"}[op]} {R[rs]},{R[rt]},{a+4+s16(im)*4:#x}'
    if op==1: return f'regimm{rt} {R[rs]},{a+4+s16(im)*4:#x}'
    n={8:'addi',9:'addiu',0xa:'slti',0xb:'sltiu',0xc:'andi',0xd:'ori',0xe:'xori',0xf:'lui',0x19:'daddiu'}.get(op)
    if n: return f'{n} {R[rt]},{R[rs]},{s16(im):#x}' if op!=0xf else f'lui {R[rt]},{im:#x}'
    n={0x20:'lb',0x21:'lh',0x23:'lw',0x24:'lbu',0x25:'lhu',0x28:'sb',0x29:'sh',0x2b:'sw',0x37:'ld',0x3f:'sd',0x39:'swc1',0x31:'lwc1',0x1e:'lq',0x1f:'sq'}.get(op)
    if n: return f'{n} {R[rt]},{s16(im):#x}({R[rs]})'
    return f'op{op:#x} {x:08x}'
lo=int(sys.argv[1],16); hi=int(sys.argv[2],16)
for a in range(lo,hi,4): print(f'{a:x}: {w(a):08X}  {dis(a)}')
