"""Draw 7P/8P text when a human pad occupies any of the six retail HUD cards."""


def add_controller_labels(out, w, assemble, to_patch_lines, clone):
    ENTRY, FONT = 0x3C6650, 0x3C7FA0

    def raw(word):
        return f'        .word 0x{word:08X}'

    def emit(addr, source, size, name):
        words, _ = assemble(addr, source)
        assert len(words) * 4 <= size, (name, len(words) * 4, size)
        out.extend(to_patch_lines(addr, words, name))

    # Hooked DrawSmackGage call: a0=ID sprite, s3=slot, s4=controller,
    # s2=slot*4, t9=original fast draw function. Check actual COM flag.
    emit(ENTRY, f"""
label:  sll t0,s3,5
        li t1,0x4921c0
        addu t1,t1,t0
        lbu t0,8(t1)
        bnez t0,retail
        nop
        lbu t0,0(t1)
        andi t0,t0,7
        slti t1,t0,6
        bnez t1,retail
        nop
        addiu sp,sp,-0x1b0
        sd ra,0x180(sp)
        sd s0,0x188(sp)
        sd s1,0x190(sp)
        sd s2,0x198(sp)
        move s0,a0
        move s1,t0
        addu t1,s4,s2
        lw a0,0x44f0(t1)
        beqz a0,empty
        nop
        move s2,sp
        move a1,s2
        jal {clone}
        addiu a2,zero,92
        j {FONT}
        nop
empty:  move a0,s0
        ld ra,0x180(sp)
        ld s0,0x188(sp)
        ld s1,0x190(sp)
        ld s2,0x198(sp)
        addiu sp,sp,0x1b0
        jr t9
        nop
retail: jr t9
        nop
""", 260, 'Retail HUD: replace false COM labels for human pads 7/8')

    emit(FONT, f"""
font:   addiu a0,s1,824
        jal 0x12fd60
        nop
        sw v0,0x160(s2)
        sw zero,0x164(s2)
        lui t0,0x3f40
        sw t0,0x10(s2)
        sw t0,0x14(s2)
        ld t0,0x30(s0)
        sd t0,0x30(s2)
        ld t0,0x38(s0)
        sd t0,0x38(s2)
{raw(0xC60C0000)}
{raw(0xC60D0004)}
{raw(0xC60E0008)}
        jal 0x14aee0
        move a0,s2
        li t0,0x3b5ff4
        sw s2,0(t0)
        move a0,s2
        jal 0x162780
        move a1,zero
        li t0,0x3b5ff4
        sw zero,0(t0)
        ld ra,0x180(sp)
        ld s0,0x188(sp)
        ld s1,0x190(sp)
        ld s2,0x198(sp)
        addiu sp,sp,0x1b0
        jr ra
        nop
""", 264, 'Retail HUD: native-position 7P/8P text at matching card scale')
    w(0x23D114, 0x0C000000 | ENTRY >> 2, 'DrawSmackGage: controller label wrapper')
