"""Four horizontal team bands behind the eight-player position buttons.

PositionVS owns a mode word beyond its retail fields. Ordinary screens keep
the retail VS draw. Eight-player screens replace that draw with opaque row
bands, using a temporary CRectDraw with no extra heap or renderer objects.
"""
import struct


def add_position_rows(out, w, assemble, to_patch_lines):
    CTOR, DRAW, RECT, TABLE = 0x3B2010, 0x3EDDD0, 0x3F2700, 0x3C9480

    def raw(word):
        return f'        .word 0x{word:08X}'

    def emit(addr, src, limit, name):
        words, labels = assemble(addr, src)
        assert len(words) * 4 <= limit, (name, len(words) * 4, limit)
        out.extend(to_patch_lines(addr, words, name))
        return labels

    # This constructor hook's caller holds PositionSelectFrame in s1. Its
    # remapped layout/record fields are +0x240/+0x1a4; preserve that register.
    emit(CTOR, """
ctor:   addiu sp,sp,-0x10
        sd ra,0(sp)
        jal 0x13ae30
        nop
        lw t0,0x240(s1)
        addiu t1,zero,5
        bne t0,t1,save
        move t2,zero
        lw t0,0x1a4(s1)
        addiu t1,zero,72
        beq t0,t1,survival
        nop
        addiu t1,zero,85
        bne t0,t1,save
        nop
        addiu t2,zero,1
        b save
        nop
survival:
        addiu t2,zero,2
save:   sw t2,0x3c(v0)
        ld ra,0(sp)
        addiu sp,sp,0x10
        jr ra
        nop
""", 164, 'Position background: per-instance ordinary/ladder/survival mode')

    emit(DRAW, f"""
draw:   lw t0,0x3c(a0)
        beqz t0,retail
        nop
        addiu sp,sp,-0x140
        sd ra,0x100(sp)
        sd s0,0x108(sp)
        sd s1,0x110(sp)
        sd s2,0x118(sp)
        sd s3,0x120(sp)
        move s0,t0
        jal 0x13b070
        nop
        move s3,v0
        beqz s3,done
        nop
        move s1,sp
        jal 0x15e070
        move a0,s1
        addiu s2,zero,-1
row:    move a0,s1
        move a1,s2
        move a2,s0
        jal {RECT}
        move a3,s3
        addiu s2,s2,1
        slti t0,s2,4
        bnez t0,row
        nop
done:   ld ra,0x100(sp)
        ld s0,0x108(sp)
        ld s1,0x110(sp)
        ld s2,0x118(sp)
        ld s3,0x120(sp)
        addiu sp,sp,0x140
        jr ra
        nop
retail: j 0x13af60
        nop
""", 288, 'Position background: four paired rows instead of VS columns')

    emit(RECT, f"""
rect:   addiu sp,sp,-0x20
        sd ra,0(sp)
        sd s0,8(sp)
        move s0,a0
        addiu t0,a1,1
        sll t1,t0,5
        sll t0,t0,2
        subu t0,t1,t0
        li t1,{TABLE}
        addu t1,t1,t0
        lw t0,8(t1)
        sw t0,0xa0(s0)
        lw t0,12(t1)
        sw t0,0xa4(s0)
        lw t0,16(t1)
        lw t2,20(t1)
        lw t3,24(t1)
        addiu t4,zero,2
        bne a2,t4,color
        nop
        slt t4,a1,zero
        bnez t4,color
        nop
        addiu t0,zero,22
        addiu t2,zero,32
        addiu t3,zero,50
color:  sw t0,0x30(s0)
        sw t2,0x34(s0)
        sw t3,0x38(s0)
        sw a3,0x3c(s0)
{raw(0xC52C0000)}
{raw(0xC52D0004)}
        lui t0,0x4900
{raw(0x44887000)}
        jal 0x14aee0
        move a0,s0
        jal 0x15e0b0
        move a0,s0
        ld ra,0(sp)
        ld s0,8(sp)
        addiu sp,sp,0x20
        jr ra
        nop
""", 240, 'Position background: native rectangle with fade and team color')

    # x, y, width, height, RGB. Background covers the old column/VS artwork;
    # narrow gaps and side margins separate the four paired rows.
    rows = [(320, 246, 640, 312, 8, 12, 18),
            (320, 128, 608, 70, 20, 32, 94),
            (320, 206, 608, 70, 88, 24, 42),
            (320, 284, 608, 70, 20, 70, 42),
            (320, 362, 608, 70, 90, 70, 16)]
    data = b''.join(struct.pack('<ffffIII', *r) for r in rows)
    assert TABLE + len(data) <= 0x3C9478 + 204
    out.append(f'{TABLE:08X} {data.hex()}   # position band geometry and colors')
    w(0x139CE0, 0x24040040, 'PositionVS allocation 0x3c -> 0x40 for private mode')
    w(0x139CEC, 0x0C000000 | CTOR >> 2, 'PositionVS constructor -> mode wrapper')
    w(0x47B59C, DRAW, 'PositionVS draw -> paired-row background for layout 5')
