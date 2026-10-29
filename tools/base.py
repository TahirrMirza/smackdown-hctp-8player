import os
import struct, sys
d = open(os.environ.get("HCTP_ELF","SLUS_207.87"), "rb").read()
FO, VA, SZ = 0x80, 0x100000, 0x389880
t = int(sys.argv[1], 16); hi=(t+0x8000)>>16; lo=t&0xFFFF
w = struct.unpack("<%dI" % (SZ//4), d[FO:FO+SZ])
for i,x in enumerate(w):
    if (x>>26)==9 and (x&0xFFFF)==lo:
        for j in range(1,12):
            p=w[i-j]
            if (p>>26)==15 and (p&0xFFFF)==hi: print(hex(VA+i*4), "base ref, lui", j, "back"); break
