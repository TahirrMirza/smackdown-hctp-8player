"""Displacement remapper for PositionSelectFrame methods (0x1394F0-0x13A3B0).
Frame object grows 0x250 -> 0x2C8: +0x60 inserted at 0x13C (entries 6,7 of the copied tagMenuPosition),
+8 inserted at 0x184 (plates array 7 -> 9), +16 inserted at 0x1C0 (UI item array 7 -> 9).
usage: from remap_frame import remap_patches -> list of (addr, newword, comment)"""
import struct, os
ELF = open(os.environ['HCTP_ELF'], 'rb').read()
LO, HI = 0x1394F0, 0x13A3B0
FOREIGN = {0x139F60}          # lw a1,0x17c(v1): field of the PositionSelectWindowFrame
MEMOPS = {0x20, 0x21, 0x23, 0x24, 0x25, 0x28, 0x29, 0x2B, 0x37, 0x3F, 0x1E, 0x1F, 0x31, 0x39}
ADDI = {0x09, 0x19}


def fmap(d):
    if d < 0x13C or d >= 0x250:
        return d
    if d < 0x184:
        return d + 0x60
    if d < 0x1C0:
        return d + 0x68
    return d + 0x78


def word(a):
    o = a - 0x100000 + 0x80
    return struct.unpack('<I', ELF[o:o + 4])[0]


def remap_patches():
    res = []
    for a in range(LO, HI, 4):
        if a in FOREIGN:
            continue
        w = word(a)
        op = w >> 26
        rs = (w >> 21) & 31
        imm = w & 0xFFFF
        if op in MEMOPS or (op in ADDI and rs != 0):
            if 0x13C <= imm < 0x250:
                n = fmap(imm)
                res.append((a, (w & ~0xFFFF) | n, f'disp {imm:#x}->{n:#x}'))
    return res


if __name__ == '__main__':
    for a, w, c in remap_patches():
        print(f'{a:08X} w {w:08X}   # {c}')
