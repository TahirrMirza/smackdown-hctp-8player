"""Displacement remapper for PositionSelectWindowFrame methods (0x13B4F0-0x13BC50): items array 7 -> 9 (+0x10 at 0x1BC)."""
import remap_frame as _r
LO, HI = 0x13B4F0, 0x13BC50
MEMOPS = _r.MEMOPS
ADDI = _r.ADDI


def remap_patches():
    res = []
    for a in range(LO, HI, 4):
        w = _r.word(a)
        op = w >> 26
        rs = (w >> 21) & 31
        imm = w & 0xFFFF
        if (op in MEMOPS or (op in ADDI and rs != 0)) and imm in (0x1BC, 0x1C0):
            res.append((a, (w & ~0xFFFF) | (imm + 0x10), f'win disp {imm:#x}->{imm + 0x10:#x}'))
    return res


if __name__ == '__main__':
    for a, w, c in remap_patches():
        print(f'{a:08X} w {w:08X}   # {c}')
