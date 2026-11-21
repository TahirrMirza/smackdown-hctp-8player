"""Private controller labels and finisher-progress bars for HUD cards 7/8."""


def add_details_patch(out, assemble, to_patch_lines, clone):
    INIT, LABEL, GAUGE = 0x121700, 0x3AE0E0, 0x3E3470
    FILL = 0x3C3638
    IDFONT, BAR, GLOW = 0x1040, 0x11B0, 0x12C0

    def raw(w):
        return f'        .word 0x{w:08X}'

    def emit(addr, src, size, label):
        words, _ = assemble(addr, src)
        assert len(words) * 4 <= size, (label, len(words) * 4, size)
        out.extend(to_patch_lines(addr, words, label))

    # a0=retail sprite controller, a1=private card, a2=left/right index.
    emit(INIT, f"""
init:   addiu sp,sp,-0x30
        sd ra,0(sp)
        sd s0,8(sp)
        sd s1,0x10(sp)
        sd s2,0x18(sp)
        move s0,a0
        move s1,a1
        sll s2,a2,2
        addu s0,s0,s2
        lw a0,0x44f0(s0)
        addiu a1,s1,{IDFONT}
        jal {clone}
        addiu a2,zero,92
        lui t0,0x3f40
        sw t0,{IDFONT + 0x10}(s1)
        sw t0,{IDFONT + 0x14}(s1)
        lw a0,0xc20(s0)
        addiu a1,s1,{BAR}
        jal {clone}
        addiu a2,zero,68
        lw a0,0xc38(s0)
        addiu a1,s1,{GLOW}
        jal {clone}
        addiu a2,zero,68
        ld ra,0(sp)
        ld s0,8(sp)
        ld s1,0x10(sp)
        ld s2,0x18(sp)
        addiu sp,sp,0x30
        jr ra
        nop
""", 344, 'HUD clone private label and progress sprites')

    # a0=card, a1=slot. Draw the current controller label at retail ID position.
    emit(LABEL, f"""
label:  addiu sp,sp,-0x30
        sd ra,0(sp)
        sd s0,8(sp)
        sd s1,0x10(sp)
        addiu s0,a0,{IDFONT}
        andi s1,a1,1
        sll t0,a1,5
        li t1,0x4921c0
        addu t1,t1,t0
        lbu t0,8(t1)
        addiu a0,zero,102
        bnez t0,gotid
        nop
        lbu t0,0(t1)
        andi t0,t0,7
        addiu a0,t0,96
        slti t1,t0,6
        bnez t1,gotid
        nop
        addiu a0,t0,824
gotid:  jal 0x12fd60
        nop
        sw v0,0x160(s0)
        sw zero,0x164(s0)
        lui t0,0x428c
        beqz s1,idpos
        nop
        lui t0,0x43dd
idpos:
{raw(0x44886000)}
        lui t0,0x4238
{raw(0x44886800)}
{raw(0xC60E0008)}
        move a0,s0
        jal 0x14aee0
        nop
        move a0,s0
        jal 0x162780
        move a1,zero
        ld ra,0(sp)
        ld s0,8(sp)
        ld s1,0x10(sp)
        addiu sp,sp,0x30
        jr ra
        nop
""", 300, 'HUD private controller label including 7P and 8P')

    # a0=card, a1=CChar. Native width = 12 + 68*progress/100.
    emit(GAUGE, f"""
gauge:  addiu sp,sp,-0x30
        sd ra,0(sp)
        sd s0,8(sp)
        sd s1,0x10(sp)
        sd s2,0x18(sp)
        move s0,a0
        lw t0,0x2b4(a1)
        slt t1,t0,zero
        beqz t1,gmax
        nop
        move t0,zero
gmax:   slti t1,t0,101
        bnez t1,gwidth
        nop
        addiu t0,zero,100
gwidth: sll t1,t0,6
        sll t0,t0,2
        addu t0,t0,t1
        addiu t1,zero,100
{raw(0x0109001A)}
{raw(0x00008812)}
        addiu s1,s1,12
        addiu s2,zero,2
        addiu s0,s0,{BAR}
gloop:  move a0,s0
        move a1,s1
        jal {FILL}
        addiu a2,s2,-1
        move a0,s0
        jal 0x15f450
        nop
        addiu s0,s0,0x110
        addiu s2,s2,-1
        bnez s2,gloop
        nop
        ld ra,0(sp)
        ld s0,8(sp)
        ld s1,0x10(sp)
        ld s2,0x18(sp)
        addiu sp,sp,0x30
        jr ra
        nop
""", 272, 'HUD independent live finisher-progress bars')

    # a0=one cloned fill sprite, a1=width, a2=glow/base texture row selector.
    # Rebuild cached right vertex and U endpoint; native left endpoint, scale,
    # Y coordinates, and texture descriptors remain intact.
    emit(FILL, f"""
fill:   addiu sp,sp,-0x20
        sd ra,0(sp)
        sd s0,8(sp)
        move s0,a0
{raw(0x44810000 | (5 << 16))}
{raw(0x46800020)}
{raw(0xE60000A0)}
{raw(0xC6020010)}
{raw(0x46020002)}
        lui t0,0x4180
{raw(0x44881000)}
{raw(0x46020002)}
{raw(0xC60200C0)}
{raw(0x46020000)}
{raw(0xE60000D0)}
        move a3,a1
        sll a2,a2,4
        addiu a2,a2,16
        move t0,a2
        addiu t0,t0,16
        jal 0x15ee00
        move a1,zero
        ld ra,0(sp)
        ld s0,8(sp)
        addiu sp,sp,0x20
        jr ra
        nop
""", 248, 'HUD progress sprite native width and UV update')
    return INIT, LABEL, GAUGE
