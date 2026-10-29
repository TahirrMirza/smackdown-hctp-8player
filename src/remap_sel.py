"""Displacement remapper for SelectWrestlerFrame (0x24D4B0-0x24FBF0) and the frame-pointer accesses
of SelectWrestlerOne (0x24FBF0-0x251760, base loaded by lw r,0x14(this)).
Frame grows 0x2284 -> 0x22F4: entries 6,7 of the copied tagMenuPosition (+0x60 at 0x13C), 8 One pointers
(+8 at 0x17C), 8-entry wresCtrlType copy at the end."""
import struct, os
ELF = open(os.environ['HCTP_ELF'], 'rb').read()
FLO, FHI = 0x24D4B0, 0x24FBF0
OLO, OHI = 0x24FBF0, 0x251760
SKIP = {0x24D778, 0x24D7E0, 0x24D970, 0x24E5FC, 0x24EA20, 0x24EA5C}   # globals / GetCommon fields
MEMOPS = {0x20, 0x21, 0x23, 0x24, 0x25, 0x28, 0x29, 0x2B, 0x37, 0x3F, 0x1E, 0x1F, 0x31, 0x39}
ADDI = {0x09, 0x19}
NEWSIZE = 0x22F4


def fmap(d):
    if d < 0x13C or d >= 0x2300:
        return d
    if d < 0x17C:
        return d + 0x60
    return d + 0x68


def word(a):
    o = a - 0x100000 + 0x80
    return struct.unpack('<I', ELF[o:o + 4])[0]


def remap_patches():
    res = []
    via = {}
    for a in range(FLO, OHI, 4):
        w = word(a)
        op = w >> 26
        rs = (w >> 21) & 31
        rt = (w >> 16) & 31
        imm = w & 0xFFFF
        inone = a >= OLO
        if a == OLO:
            via = {}
        is_mem = op in MEMOPS or (op in ADDI and rs != 0)
        if is_mem and 0x13C <= imm < 0x2300 and rs not in (0, 1, 29) and a not in SKIP:
            if (not inone) or rs in via:
                n = fmap(imm)
                if n != imm:
                    res.append((a, (w & 0xFFFF0000) | n, f'sel frame disp 0x{imm:x} -> 0x{n:x}'))
        # provenance tracking (One methods)
        if inone:
            if op == 0x23 and imm == 0x14 and rs not in via:
                via[rt] = 1
            else:
                wr = None
                if op in (0x20, 0x21, 0x23, 0x24, 0x25, 0x09, 0x19, 0x0F, 0x0D, 0x0C, 0x0A, 0x0B):
                    wr = rt
                elif op == 0:
                    wr = (w >> 11) & 31
                if wr in via and not (op == 0x23 and imm == 0x14):
                    via.pop(wr)
            if (w >> 26) in (2, 3) or (op == 0 and (w & 0x3F) in (8, 9)):
                pass
    # alloc size sites
    for a in (0x24CF74, 0x24CF90, 0x24D384, 0x24D440):
        res.append((a, 0x24040000 | NEWSIZE, 'alloc SelectWrestlerFrame 0x22F4'))
    return res


if __name__ == '__main__':
    r = remap_patches()
    print(len(r))
