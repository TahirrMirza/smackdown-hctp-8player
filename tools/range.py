import os
import struct, sys
d = open(os.environ.get("HCTP_ELF","SLUS_207.87"), "rb").read()
FO, VA, SZ = 0x80, 0x100000, 0x389880
lo_a, hi_a = int(sys.argv[1],16), int(sys.argv[2],16)
w = struct.unpack("<%dI"%(SZ//4), d[FO:FO+SZ])
MEM={0x09,0x20,0x21,0x23,0x24,0x25,0x28,0x29,0x2B,0x37,0x3F,0x1E,0x1F,0x31,0x39,0x27}
for i,x in enumerate(w):
    if x>>26==15:
        rt=(x>>16)&31; hi=(x&0xFFFF)<<16
        for j in range(1,20):
            if i+j>=len(w): break
            y=w[i+j]
            if (y>>26) in MEM and ((y>>21)&31)==rt:
                imm=y&0xFFFF; imm-=0x10000 if imm&0x8000 else 0
                a=(hi+imm)&0xFFFFFFFF
                if lo_a<=a<hi_a: print(hex(VA+(i+j)*4), hex(a))
            if (y>>16)&31==rt and (y>>26) in (0x0F,0x09,0x23,0x24,0x25,0x20,0x21) and ((y>>21)&31)!=rt: break
