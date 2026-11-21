"""Native-size names and matching backing geometry for private HUD cards."""
import struct


def add_name_patch(out, assemble, to_patch_lines, font, backing, rect):
    NAME, LAYOUT = 0x3B2908, 0x3C78D8

    def raw(word):
        return f'        .word 0x{word:08X}'

    def lwc(ft, off, base):
        return raw(0xC4000000 | base << 21 | ft << 16 | (off & 0xffff))

    def mtc(rt, fs):
        return raw(0x44800000 | rt << 16 | fs << 11)

    def const(ft, val):
        bits = struct.unpack('<I', struct.pack('<f', val))[0]
        return f'        li t0,{bits}\n{mtc(8, ft)}'

    # s2 retains the scaled name width through the positioning calls.
    src = f"""
name:   addiu sp,sp,-0x30
        sd ra,0(sp)
        sd s0,8(sp)
        sd s1,0x10(sp)
        sd s2,0x18(sp)
        move s0,a0
        andi s1,a1,1
        sll t0,a1,5
        li t1,0x4921ca
        addu t0,t0,t1
        lhu a0,0(t0)
        jal 0x12cf30
        move a1,zero
        sw v0,{font + 0x160}(s0)
        sw zero,{font + 0x164}(s0)
        lui t0,0x3f80
        sw t0,{font + 0x10}(s0)
        addiu a0,s0,{font}
        jal 0x162250
        nop
        move s2,v0
        slti t0,s2,191
        bnez t0,nfit
        nop
{mtc(18, 0)}
{raw(0x46800020)}
{const(2, 190.0)}
{raw(0x46001003)}
{raw(0xE6000000 | (font + 0x10))}
        addiu s2,zero,190
nfit:   jal {LAYOUT}
        nop
        ld ra,0(sp)
        ld s0,8(sp)
        ld s1,0x10(sp)
        ld s2,0x18(sp)
        addiu sp,sp,0x30
        jr ra
        nop
"""
    words, _ = assemble(NAME, src)
    assert len(words) * 4 <= 368, len(words) * 4
    out.extend(to_patch_lines(NAME, words, 'HUD private wrestler name and width'))

    src = f"""
layout: addiu sp,sp,-0x10
        sd ra,0(sp)
        addiu a0,s0,{font}
{const(12, 42.0)}
        beqz s1,nleft
        nop
{const(12, 470.0)}
        li t9,0x14b200
        b npos
        nop
nleft:
        li t9,0x14b090
npos:
{const(13, 20.0)}
{lwc(14, font + 8, 16)}
        jalr t9
        nop
        addiu t1,s2,42
        beqz s1,rwidth
        nop
        addiu t1,t1,2
rwidth:
{mtc(9, 12)}
{raw(0x46806320)}
{raw(0xE60C0000 | (rect + 0xa0))}
        addiu a0,s0,{rect}
{const(12, 0.0)}
        beqz s1,rleft
        nop
{const(12, 512.0)}
rleft:  li t9,0x14b090
        beqz s1,rpos
        nop
        li t9,0x14b200
rpos:
{const(13, 20.0)}
{lwc(14, rect + 8, 16)}
        jalr t9
        nop
        addiu t1,s2,46
        beqz s1,bpos
        nop
        addiu t1,zero,464
        subu t1,t1,s2
bpos:
{mtc(9, 12)}
{raw(0x46806320)}
{const(13, 29.6)}
{lwc(14, backing + 8, 16)}
        addiu a0,s0,{backing}
        jal 0x14aee0
        nop
        ld ra,0(sp)
        addiu sp,sp,0x10
        jr ra
        nop
"""
    words, _ = assemble(LAYOUT, src)
    assert len(words) * 4 <= 344, len(words) * 4
    out.extend(to_patch_lines(LAYOUT, words, 'HUD native left/right name and backing layout'))
    return NAME
