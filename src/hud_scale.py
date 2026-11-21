"""Scale only HUD-card GIF vertices, after the native fast draw emits them.

Cached draw objects, texture UVs and other UI are left untouched. Pointer
membership identifies retail card elements and the private card allocation;
centre-screen timers, prompts and other sprites are excluded.
"""


def add_scale_patch(out, w, assemble, to_patch_lines, state):
    BEGIN = 0x3B8440       # dead ADXM_ShutdownThrdEx, 172 B
    SELECT = 0x3C0BB0      # unused tail of dead ADXT_ExecErrChk, 412 B
    SCALE = 0x3F2458       # dead SFBUF_AringAddWrite, 244 B
    ACTIVE, BASEY, BASEX, HEIGHT = state + 8, state + 0x28, state + 0x2c, state + 0x30

    def emit(addr, src, limit, name):
        words, labels = assemble(addr, src)
        assert len(words) * 4 <= limit, (name, len(words) * 4, limit)
        out.extend(to_patch_lines(addr, words, name))
        return labels

    emit(BEGIN, f"""
begin:  li t0,0x524eb0
        lw t0,0(t0)
        lui t1,1
        addu t1,t0,t1
        li t2,{state}
        lw t3,0x620(t1)
        sw t3,0x28(t2)
        lw t3,0x624(t1)
        sw t3,0x2c(t2)
        addiu t3,zero,7168
        lw t4,0x588(t1)
        beqz t4,bheight
        nop
        lw t4,0x10(t0)
        bnez t4,bheight
        nop
        addiu t3,zero,3584
bheight:sw t3,0x30(t2)
        addiu t3,zero,1
        sw t3,8(t2)
        jr ra
        nop
""", 172, 'HUD 75 percent scale scope and native screen origin')

    labels = emit(SELECT, f"""
sprite: addiu t7,zero,0xb0
        b select
        addiu a3,zero,0x20
rect:   addiu t7,zero,0x80
        addiu a3,zero,0x10
select: li t0,{ACTIVE}
        lw t1,0(t0)
        beqz t1,done
        nop
        lw t1,0x2c(t0)
        beq a0,t1,match
        nop
        lw t1,-8(t0)
        beqz t1,native
        nop
        subu t1,a0,t1
        sltiu t1,t1,0x2800
        bnez t1,match
        nop
native: li t0,0x529300
        lw t0,0(t0)
        beqz t0,done
        nop
        addiu t0,t0,0x50
        subu t1,a0,t0
        addiu t1,t1,-0x16a0
        sltiu t2,t1,0x600
        beqz t2,pointers
        nop
        andi t1,t1,0xff
        beqz t1,match
        nop
pointers:addiu t3,t0,0xc08
        addiu t4,zero,60
        move t6,zero
scan:   lw t5,0(t3)
        beq t5,a0,match
        nop
        addiu t3,t3,4
        addiu t4,t4,-1
        bnez t4,scan
        nop
        addiu t6,t6,1
        addiu t3,t0,0xd34
        addiu t4,zero,36
        addiu t5,zero,1
        beq t6,t5,scan
        nop
        addiu t3,t0,0x44f0
        addiu t4,zero,6
        addiu t5,zero,2
        beq t6,t5,scan
        nop
done:   jr ra
        nop
match:  j {SCALE}
        nop
""", 412, 'HUD card pointer membership and fast packet selection')

    emit(SCALE, f"""
scale:  li t0,{state}
        li t1,0x524eb0
        lw t1,0(t1)
        lui t2,1
        addu t1,t1,t2
        lw t2,0x568(t1)
        lui t1,0x2000
        or t2,t2,t1
        addu t2,t2,t7
        lw t5,0x2c(t0)
        lw t6,0x28(t0)
        lw t3,0(t2)
        subu t3,t3,t5
        slti t3,t3,4096
        bnez t3,xanchor
        nop
        addiu t5,t5,8192
xanchor:lw t8,0x30(t0)
        srl t9,t8,1
        lw t3,4(t2)
        subu t3,t3,t6
        slt t3,t3,t9
        bnez t3,yanchor
        nop
        addu t6,t6,t8
yanchor:addiu t7,zero,2
vertex: lw t3,0(t2)
        subu t3,t3,t5
        sll t4,t3,1
        addu t3,t3,t4
        sra t3,t3,2
        addu t3,t3,t5
        sw t3,0(t2)
        lw t3,4(t2)
        subu t3,t3,t6
        sll t4,t3,1
        addu t3,t3,t4
        sra t3,t3,2
        addu t3,t3,t6
        sw t3,4(t2)
        addu t2,t2,a3
        addiu t7,t7,-1
        bnez t7,vertex
        nop
        jr ra
        nop
""", 244, 'HUD exact three-quarter packet scale about screen corners')

    # Hooks run after native packet generation and register restoration. The
    # existing stack-pop delay slots remain in place. RectDraw normally reuses
    # a0 for Z; keep the object pointer available for membership classification.
    w(0x15F7B8, 0x08000000 | labels['sprite'] >> 2, 'Sprite fast return -> HUD scale')
    w(0x15E7F4, 0x8C980084, 'Rect fast: load Z into t8, preserve object pointer')
    w(0x15E7F8, 0xAC780018, 'Rect fast: store Z from t8')
    w(0x15E804, 0x08000000 | labels['rect'] >> 2, 'Rect fast return -> HUD scale')
    return BEGIN
