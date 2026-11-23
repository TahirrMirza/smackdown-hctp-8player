"""Give wrestler slot 8 its own white player and target marker models."""

LOAD = 0x10E950     # sceSifGetOtherData, 344 bytes
TINT = 0x121368     # sceMcDelete, 280 bytes
CLEANUP = 0x400418  # SFD_GetTmrInf, 264 bytes
DRAW = 0x405460     # SFX_CnvFrmARGB8888FromDivField, 232 bytes
STATE = 0x407680    # Data in dead SFX_CnvFrmRGB8888FromDivField


def add_player_marker(out, w, assemble, to_patch_lines, have):
    # The native load-end function has both the model archive and its texture
    # group in scope. Make private copies of entries 1015/1016 before it
    # restores the previous memory page. It restores s0/s1/s2/s5 on return.
    load, _ = assemble(LOAD, f"""
        beqz s3,restore_page
        nop
        li t0,{have}
        lw t0,0(t0)
        beqz t0,restore_page
        nop
        li t0,{STATE}
        lw t1,0(t0)
        bnez t1,restore_page
        nop
        addiu sp,sp,-0x20
        sd ra,0(sp)
        sd a0,8(sp)
        move s5,t0
        sw s4,0(s5)
        move s0,zero

next_model:
        addiu a0,sp,0x90  # native stack-local CData
        jal 0x15d740     # Search
        addiu a1,s0,1015
        addiu t0,zero,-1
        beq v0,t0,advance
        move a1,v0
        jal 0x15da70      # GetAdr, these model entries are uncompressed
        addiu a0,sp,0x90
        beqz v0,advance
        nop
        lw t0,4(v0)
        addiu t1,zero,0x770
        beqz s0,check_size
        nop
        addiu t1,zero,0x960
check_size:
        bne t0,t1,advance
        move a0,v0
        move a1,zero
        move a2,zero
        jal 0x15def0      # ReadChunkData, including pointer relocation
        move a3,zero
        beqz v0,advance
        move s2,v0
        move a0,s2
        jal {TINT}
        move a1,s0
        jal 0x1001e0      # new CSkinModel
        addiu a0,zero,0x110
        beqz v0,free_chunk
        move a0,v0
        move a1,s2
        lui t0,0x3f80
        .word 0x44886000  # mtc1 t0,f12
        jal 0x14f930
        nop
        move s1,v0
        lw t0,0(s3)
        move a0,s1
        jal 0x150390      # SetTexture with the native marker atlas
        lw a1,0(t0)
        sll t0,s0,3
        addu t0,t0,s5
        sw s1,4(t0)
        b advance
        sw s2,8(t0)

free_chunk:
        jal 0x100200
        move a0,s2
advance:
        addiu s0,s0,1
        sltiu t0,s0,2
        bnez t0,next_model
        nop
        ld a0,8(sp)
        ld ra,0(sp)
        addiu sp,sp,0x20
restore_page:
        j 0x140be0
        nop
""")

    # Each copy contains one mesh. Replace only the stock orange vertex
    # triplets in the verified vertex range. Keep alpha, outline, and UVs.
    tint, _ = assemble(TINT, """
        addiu t0,a0,0x3f8
        addiu t1,a0,0x6f8
        beqz a1,colors
        nop
        addiu t0,a0,0x488
        addiu t1,a0,0x8e8
colors: li t2,0x3f70f0f1  # stock orange red, reused for white
        li t3,0x3ee4e4e5  # stock orange green
vertex: lw t4,0(t0)
        bne t4,t2,step
        lw t4,4(t0)
        bne t4,t3,step
        lw t4,8(t0)
        bnez t4,step
        nop
        sw t2,4(t0)
        sw t2,8(t0)
step:   addiu t0,t0,0x20
        bne t0,t1,vertex
        nop
        jr ra
        nop
""")

    cleanup, _ = assemble(CLEANUP, f"""
        li t0,{STATE}
        lw t1,0(t0)
        bne t1,s1,retail
        nop
        sw zero,0(t0)
        addiu sp,sp,-0x10
        sd ra,0(sp)
        move s2,t0  # native destructor restores s2 after this call
        move s3,zero
free:   lw a0,4(s2)
        beqz a0,chunk
        sw zero,4(s2)
        jal 0x14fad0  # CSkinModel destructor, native archive owner frees chunk
        addiu a1,zero,1
chunk:  lw a0,8(s2)
        beqz a0,advance
        sw zero,8(s2)
        jal 0x100200
        nop
advance:addiu s3,s3,1
        sltiu t0,s3,2
        bnez t0,free
        addiu s2,s2,8
        ld ra,0(sp)
        addiu sp,sp,0x10
retail: addiu a0,s1,0x2c
        j 0x13e490
        move a1,zero
""")

    # Reuse the native transform and draw commands for both markers.
    draw, entries = assemble(DRAW, f"""
player: lw t0,0x390(s0)
        addiu t1,zero,7
        bne t0,t1,native_player
        nop
        li t0,{STATE}
        lw t1,0(t0)
        bne t1,s4,player_ready
        lw s2,0x74(s4)
        lw t1,4(t0)
        beqz t1,player_ready
        nop
        b player_ready
        move s2,t1
native_player:
        lw s2,0x44(v1)
player_ready:
        beqz s2,skip
        nop
        j 0x299540
        .word 0x7e420040  # sq v0,0x40(s2)

target: addiu t0,zero,7
        bne a0,t0,native_target
        nop
        li t0,{STATE}
        lw t1,0(t0)
        bne t1,s4,skip
        nop
        b target_ready
        lw s0,12(t0)
native_target:
        lw s0,0x44(v1)
target_ready:
        beqz s0,skip
        nop
        j 0x2995c0
        .word 0x7e020040  # sq v0,0x40(s0)
skip:   j 0x29975c
        nop
""")

    for addr, words, maximum, label in (
        (LOAD, load, 344, 'Load private slot-8 marker models'),
        (TINT, tint, 280, 'White slot-8 marker vertices'),
        (CLEANUP, cleanup, 264, 'Release private slot-8 marker models'),
        (DRAW, draw, 232, 'Choose the slot-8 player and target models'),
    ):
        assert len(words) * 4 <= maximum
        out.extend(to_patch_lines(addr, words, label))
    for offset in range(0, 20, 4):
        w(STATE + offset, 0, 'Marker owner, models and chunks' if offset == 0 else '')
    w(0x298E90, 0x0C000000 | LOAD >> 2, 'Load slot-8 markers before the game restores its memory page')
    w(0x298C34, 0x0C000000 | CLEANUP >> 2, 'Release slot-8 markers before native action/base teardown')
    for addr, label in ((0x299538, 'player'), (0x2995B8, 'target')):
        w(addr, 0x08000000 | entries[label] >> 2, f'DrawMarker: resolve {label} model')
        w(addr + 4, 0, 'The model selector executes the displaced transform store')
