import os
import struct, sys
d = open(os.environ.get("HCTP_ELF","SLUS_207.87"), "rb").read()
FO, VA, SZ = 0x80, 0x100000, 0x389880
t=int(sys.argv[1],16)
w=struct.unpack("<%dI"%(SZ//4), d[FO:FO+SZ])
for i,x in enumerate(w):
    if x>>26==3 and ((x&0x3FFFFFF)<<2)==t: print(hex(VA+i*4))
