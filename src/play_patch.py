"""PLAY-summary extensions for the two eight-wrestler modes.

The MatchMenuFrame object already owns three six-entry name arrays.  Retail
The native table builder only sees the six entries in tagMenuPosition.  This
wrapper adds the two side-buffer entries and normalizes both modes to two
four-name columns.  A compact drawer keeps all four rows above the PLAY / MATCH
RULES bar; ordinary matches still call the retail DrawRoster unchanged.
"""

import struct


def add_play_patch(out, w, assemble, to_patch_lines, have_addr, extra_addr):
    CAVE = 0x3B6040  # dead ADXT_GetHdrInfo, 360 bytes; begins on a cache line
    DRAW = 0x3F2CC0  # dead SFD_GetTimePerFile, 344 bytes
    SHOW = 0x3BD678  # dead adxt_disp_rna_stat, 252 bytes
    POS = DRAW + 0x110

    def c1(op, rs, rt, imm):
        return (op << 26) | (rs << 21) | (rt << 16) | (imm & 0xFFFF)

    def lwc1(ft, off, base):
        return c1(0x31, base, ft, off)

    def mtc1(rt, fs):
        return 0x44800000 | (rt << 16) | (fs << 11)

    def raw(word):
        return f'        .word 0x{word:08X}'

    src = f"""
names:  addiu sp,sp,-0x20
        sd ra,0(sp)
        sd s0,8(sp)
        move s0,a0
        jal 0x2de5f0
        nop
        li t0,{have_addr}
        lw t0,0(t0)
        beqz t0,done
        nop
        lw t0,0x34(s0)
        lw t1,0x128(t0)
        addiu t2,zero,72
        beq t1,t2,survival
        nop
        addiu t2,zero,85
        bne t1,t2,done
        nop

# LADDER record 85: retail produced 2 left + 2 right + 2 bottom.
# Move the bottom pair into row 3 and put side-buffer slots 6/7 in row 4.
ladder: lw t0,0x14c(s0)
        sw t0,0x124(s0)
        lw t0,0x150(s0)
        sw t0,0x13c(s0)
        li t0,{extra_addr}
        lw t1,0x1c(t0)
        sw t1,0x128(s0)
        lw t1,0x4c(t0)
        sw t1,0x140(s0)
        addiu t1,zero,4
        sw t1,0x164(s0)
        sw t1,0x168(s0)
        sw zero,0x16c(s0)
        addiu t2,zero,3
        sw t2,0xb4(s0)
        b done
        nop

# SURVIVAL record 72: retail put all six visible entries in the special list.
# Redistribute them into alternating columns, then use side-buffer slots 6/7
# as the fourth row.
survival:
        lw t0,0x14c(s0)
        sw t0,0x11c(s0)
        lw t0,0x150(s0)
        sw t0,0x134(s0)
        lw t0,0x154(s0)
        sw t0,0x120(s0)
        lw t0,0x158(s0)
        sw t0,0x138(s0)
        lw t0,0x15c(s0)
        sw t0,0x124(s0)
        lw t0,0x160(s0)
        sw t0,0x13c(s0)
        li t0,{extra_addr}
        lw t1,0x1c(t0)
        sw t1,0x128(s0)
        lw t1,0x4c(t0)
        sw t1,0x140(s0)
        addiu t1,zero,4
        sw t1,0x164(s0)
        sw t1,0x168(s0)
        addiu t2,zero,3
        sw t2,0xb4(s0)
        sw zero,0x16c(s0)

done:   move v0,s0
        ld ra,0(sp)
        ld s0,8(sp)
        addiu sp,sp,0x20
        jr ra
        nop
"""
    words, labels = assemble(CAVE, src)
    assert CAVE + 4 * len(words) <= CAVE + 360, hex(CAVE + 4 * len(words))
    out.extend(to_patch_lines(CAVE, words, 'PLAY summary: native 3+3+2 eight-name layout'))
    w(0x2DC320, 0x0C000000 | (labels['names'] >> 2),
      'MatchMenuFrame ctor: CreateRosterTable -> eight-name wrapper')

    draw_src = f"""
draw:   li t0,{have_addr}
        lw t0,0(t0)
        beqz t0,retail
        nop
        lw t0,0x34(a0)
        lw t1,0x128(t0)
        addiu t2,zero,72
        beq t1,t2,custom
        nop
        addiu t2,zero,85
        bne t1,t2,retail
        nop
custom: addiu sp,sp,-0x40
        sd ra,0(sp)
        sd s0,8(sp)
        sd s1,0x10(sp)
        sd s2,0x18(sp)
        sd s3,0x20(sp)
        move s0,a0
        li t0,0x526718
        lw t0,0(t0)
        lw s1,0x1b8(t0)
        beqz s1,finish
        nop
        lui t0,0x3f80
        sw t0,0x10(s1)
        sw t0,0x14(s1)
        sw t0,0x18(s1)
        lw t0,0x100(s0)
        sw t0,0x3c(s1)
        sw t0,0x12c(s1)
        move s2,zero
column: move s3,zero
row:    sll t0,s3,2
        beqz s2,left
        nop
        addiu t1,s0,0x134
        b gotbase
        nop
left:   addiu t1,s0,0x11c
gotbase:addu t1,t1,t0
        lw a0,0(t1)
        move a1,s1
        move a2,s2
        jal {SHOW}
        move a3,s3
        addiu s3,s3,1
        slti t0,s3,4
        bnez t0,row
        nop
        addiu s2,s2,1
        slti t0,s2,2
        bnez t0,column
        nop
finish: ld ra,0(sp)
        ld s0,8(sp)
        ld s1,0x10(sp)
        ld s2,0x18(sp)
        ld s3,0x20(sp)
        addiu sp,sp,0x40
        jr ra
        nop
retail: j 0x2dd890
        nop
"""
    draw_words, draw_labels = assemble(DRAW, draw_src)
    assert DRAW + 4 * len(draw_words) <= POS, hex(DRAW + 4 * len(draw_words))
    out.extend(to_patch_lines(DRAW, draw_words, 'PLAY summary: compact two-column name drawer'))

    show_src = f"""
show:   addiu sp,sp,-0x30
        sd ra,0(sp)
        sd s0,8(sp)
        sd s1,0x10(sp)
        sd s2,0x18(sp)
        move s0,a1
        move s1,a2
        move s2,a3
        jal 0x12cde0
        move a1,zero
        sw v0,0x160(s0)
        sw zero,0x164(s0)
        li t0,{POS}
        sll t1,s1,2
        addu t1,t0,t1
{raw(lwc1(12, 0, 9))}
        sll t1,s2,2
        addu t1,t0,t1
{raw(lwc1(13, 8, 9))}
        li t0,0x4b7fffff
{raw(mtc1(8, 14))}
        move a0,s0
        lw t9,0xb0(s0)
        lw t9,0x18(t9)
        jalr t9
        nop
        lw t9,0xb0(s0)
        move a0,s0
        addiu a1,zero,1
        move a2,zero
        addiu a3,zero,-1
        lw t9,0x44(t9)
        jalr t9
        addiu t0,zero,2
        lw t9,0xb0(s0)
        move a0,s0
        addiu a1,zero,1
        move a2,zero
        addiu a3,zero,-1
        lw t9,0x44(t9)
        jalr t9
        move t0,zero
        ld ra,0(sp)
        ld s0,8(sp)
        ld s1,0x10(sp)
        ld s2,0x18(sp)
        addiu sp,sp,0x30
        jr ra
        nop
"""
    show_words, _ = assemble(SHOW, show_src)
    assert SHOW + 4 * len(show_words) <= SHOW + 252, hex(SHOW + 4 * len(show_words))
    out.extend(to_patch_lines(SHOW, show_words, 'PLAY summary: draw one compact name'))
    for i, value in enumerate((160.0, 480.0, 276.0, 298.0, 320.0, 342.0)):
        bits = struct.unpack('<I', struct.pack('<f', value))[0]
        w(POS + i * 4, bits, 'PLAY name positions' if i == 0 else '')
    w(0x2DCB60, 0x0C000000 | (draw_labels['draw'] >> 2),
      'MatchMenuFrame::Draw: DrawRoster -> compact eight-name wrapper')

