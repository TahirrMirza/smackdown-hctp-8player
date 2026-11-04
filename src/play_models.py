"""Two sidecar MatchWrestler objects for the eight-player PLAY scene.

MatchWrestlerCtrl owns only six pointers followed immediately by camera and
edit-wrestler state.  Growing it would require remapping every later field.
Instead, the patch constructs slots 6/7 in two private pointers, starts and
stops them beside the retail controller, and destroys them with the controller.
"""

import struct


def add_play_models(out, w, assemble, to_patch_lines, have_addr, extra_addr):
    SETUP = 0x3B9ED8   # dead ADXSJE_CalcLpInfo, 344 B
    MAKE = 0x3C7508    # dead cvFsGetFreeSize, 320 B
    START = 0x3BE108   # dead ADXT_GetTimeSfreq, 200 B
    STOP = 0x3BEC18    # dead ADXT_GetIbufRemainTime, 228 B
    CLEAN = 0x3C6588   # dead cvFsInit, 196 B
    DATA = 0x3C69B8    # dead cvFsDelDev; data only, separate cache line
    POSTBL = 0x3D2D00  # dead sjx_sndcbf_iop, 272 B; immutable data

    P6, P7 = DATA, DATA + 4

    w(P6, 0, 'PLAY sidecar wrestler pointers')
    w(P7, 0)

    setup_src = f"""
setup:  lw t0,0x30(s4)
        sw t0,0x234(a0)
        addiu sp,sp,-0x30
        sd ra,0(sp)
        sd s0,8(sp)
        sd s1,0x10(sp)
        move s0,a0
        li t0,{have_addr}
        lw t0,0(t0)
        beqz t0,sdone
        nop
        lw t0,0x23c(s0)
        lw t1,0x128(t0)
        addiu t2,zero,72
        beq t1,t2,svalid
        nop
        addiu t2,zero,85
        bne t1,t2,sdone
        nop
svalid: lw t0,0x240(s0)
        move s1,zero
spos:  sll t1,s1,2
        addu t1,s0,t1
        lw t2,0x214(t1)
        beqz t2,sposn
        nop
        addiu t3,s1,7
        sw t3,0x28(t2)
sposn: addiu s1,s1,1
        slti t1,s1,6
        bnez t1,spos
        nop
        lw t0,0x240(s0)
        bnez t0,smake
        nop
        li t1,{extra_addr}
        lw t2,0x1c(t1)
        slti t3,t2,86
        beqz t3,sedit
        nop
        lw t2,0x4c(t1)
        slti t3,t2,86
        bnez t3,smake
        nop
sedit: addiu a0,zero,0x40
        jal 0x1001e0
        nop
        beqz v0,smake
        move a0,v0
        jal 0x1a4dd0
        move a1,zero
        sw v0,0x240(s0)
smake: li s1,{P6}
        move a0,s0
        jal {MAKE}
        addiu a1,zero,6
        sw v0,0(s1)
        move a0,s0
        jal {MAKE}
        addiu a1,zero,7
        sw v0,4(s1)
sdone: ld ra,0(sp)
        ld s0,8(sp)
        ld s1,0x10(sp)
        addiu sp,sp,0x30
        jr ra
        nop
"""
    setup_words, setup_labels = assemble(SETUP, setup_src)
    assert SETUP + 4 * len(setup_words) <= SETUP + 344, hex(SETUP + 4 * len(setup_words))
    out.extend(to_patch_lines(SETUP, setup_words, 'PLAY sidecar wrestler setup'))

    make_src = f"""
make:   addiu sp,sp,-0x40
        sd ra,0(sp)
        sd s0,8(sp)
        sd s1,0x10(sp)
        sd s2,0x18(sp)
        sd s3,0x20(sp)
        move s0,a0
        move s2,a1
        addiu t0,s2,-6
        beqz t0,mfirst
        li s1,{extra_addr + 0x30}
        b mentry
        nop
mfirst:li s1,{extra_addr}
mentry:lw t0,4(s1)
        beqz t0,mfail
        nop
        lw a0,0x1c(s1)
        lw a1,0x20(s1)
        move a2,zero
        move a3,zero
        lw t0,0x14(s1)
        xori t0,t0,2
        sltiu t0,t0,1
        jal 0x12cce0
        move t1,zero
        andi s3,v0,0xffff
        jal 0x1001e0
        addiu a0,zero,0x50
        beqz v0,mfail
        move a0,v0
        move a1,s3
        move a2,s2
        addiu a3,s2,7
        addiu t0,zero,1
        lw t1,0x240(s0)
        jal 0x3452e0
        addiu t2,zero,101
        b mret
        nop
mfail: move v0,zero
mret:  ld ra,0(sp)
        ld s0,8(sp)
        ld s1,0x10(sp)
        ld s2,0x18(sp)
        ld s3,0x20(sp)
        addiu sp,sp,0x40
        jr ra
        nop
"""
    make_words, _ = assemble(MAKE, make_src)
    assert MAKE + 4 * len(make_words) <= MAKE + 320, hex(MAKE + 4 * len(make_words))
    out.extend(to_patch_lines(MAKE, make_words, 'PLAY construct one sidecar wrestler'))

    start_src = f"""
start:  addiu sp,sp,-0x20
        sd ra,0(sp)
        jal 0x346850
        nop
        li t0,{P6}
        lw a0,0(t0)
        beqz a0,st7
        nop
        jal 0x3454b0
        nop
st7:    li t0,{P7}
        lw a0,0(t0)
        beqz a0,stdone
        nop
        jal 0x3454b0
        nop
stdone:ld ra,0(sp)
        addiu sp,sp,0x20
        jr ra
        nop
"""
    start_words, start_labels = assemble(START, start_src)
    assert START + 4 * len(start_words) <= START + 200
    out.extend(to_patch_lines(START, start_words, 'PLAY start sidecar wrestlers'))

    stop_src = f"""
stop:   addiu sp,sp,-0x20
        sd ra,0(sp)
        jal 0x3469c0
        nop
        li t0,{P6}
        lw a0,0(t0)
        beqz a0,sp7
        nop
        jal 0x3454f0
        nop
sp7:    li t0,{P7}
        lw a0,0(t0)
        beqz a0,spdone
        nop
        jal 0x3454f0
        nop
spdone:ld ra,0(sp)
        addiu sp,sp,0x20
        jr ra
        nop
"""
    stop_words, stop_labels = assemble(STOP, stop_src)
    assert STOP + 4 * len(stop_words) <= STOP + 228
    out.extend(to_patch_lines(STOP, stop_words, 'PLAY stop sidecar wrestlers'))

    clean_src = f"""
clean:  addiu sp,sp,-0x30
        sd ra,0(sp)
        sd s0,8(sp)
        sd s1,0x10(sp)
        move s0,a0
        li s1,{P6}
        lw a0,0(s1)
        beqz a0,cl7
        nop
        lw t9,0(a0)
        lw t9,8(t9)
        jalr t9
        addiu a1,zero,1
        sw zero,0(s1)
cl7:    lw a0,4(s1)
        beqz a0,cldone
        nop
        lw t9,0(a0)
        lw t9,8(t9)
        jalr t9
        addiu a1,zero,1
        sw zero,4(s1)
cldone:lw a0,0x240(s0)
        ld ra,0(sp)
        ld s0,8(sp)
        ld s1,0x10(sp)
        addiu sp,sp,0x30
        jr ra
        nop
"""
    clean_words, clean_labels = assemble(CLEAN, clean_src)
    assert CLEAN + 4 * len(clean_words) <= CLEAN + 196
    out.extend(to_patch_lines(CLEAN, clean_words, 'PLAY destroy sidecar wrestlers'))

    # Preserve the seven retail vectors for ordinary modes.  Types 7..14 are
    # an eight-wide layout inside the same X span as the retail six; depth is
    # staggered so adjacent models do not all occupy one plane.
    positions = (
        (-3.75, 0.0, -5.0, 1.0), (8.75, 0.0, -5.0, 1.0),
        (-7.5, 0.0, 5.0, 1.0), (5.0, 0.0, 5.0, 1.0),
        (0.0, 0.0, 15.0, 1.0), (12.5, 0.0, 15.0, 1.0),
        (8.75, 0.0, 15.0, 1.0),
        (-7.5, 0.0, 5.0, 1.0), (-4.64, 0.0, -5.0, 1.0),
        (-1.79, 0.0, 15.0, 1.0), (1.07, 0.0, 5.0, 1.0),
        (3.93, 0.0, -5.0, 1.0), (6.79, 0.0, 15.0, 1.0),
        (9.64, 0.0, 5.0, 1.0), (12.5, 0.0, -5.0, 1.0),
    )
    for i, vec in enumerate(positions):
        for j, value in enumerate(vec):
            bits = struct.unpack('<I', struct.pack('<f', value))[0]
            w(POSTBL + i * 16 + j * 4, bits,
              'PLAY wrestler position table (7 retail + 2 sidecar)' if (i, j) == (0, 0) else '')

    # SetupParam tail, global StartMotion/StopMotion calls and controller dtor.
    w(0x346810, 0x0C000000 | (setup_labels['setup'] >> 2),
      'MatchWrestlerCtrl::SetupParam tail -> sidecar setup')
    w(0x346814, 0x02A0202D, 'delay: a0 = controller (s5)')
    w(0x3461EC, 0x0C000000 | (start_labels['start'] >> 2),
      'StartMotion -> retail + sidecar wrestlers')
    w(0x34621C, 0x0C000000 | (stop_labels['stop'] >> 2),
      'StopMotion -> retail + sidecar wrestlers')
    w(0x346474, 0x0C000000 | (clean_labels['clean'] >> 2),
      'MatchWrestlerCtrl dtor -> destroy sidecar wrestlers')
    w(0x346478, 0x0220202D, 'delay: a0 = controller (s1)')
    w(0x346314, 0x24040008, 'SetupMatchMenuCharTexBuf: 6 -> 8')
    w(0x345E54, 0x3C04003D, 'MatchWrestler position table -> extended table')
    w(0x345E58, 0x24842D00)

