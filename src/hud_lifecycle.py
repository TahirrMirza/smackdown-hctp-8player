"""Release private HUD state before the native HUD releases its resources."""


def add_hud_lifecycle(out, w, assemble, to_patch_lines, state, anim_reset):
    CLEAN = 0x3E9630  # dead mwPlyFinishSfdFx, 240 B
    words, _ = assemble(CLEAN, f"""
cleanup:addiu sp,sp,-0x20
        sd ra,0(sp)
        sd a0,8(sp)
        jal {anim_reset}
        nop
        li t0,{state}
        lw a0,0(t0)
        beqz a0,clear
        nop
        jal 0x100200
        nop
clear:  li t0,{state}
        addiu t1,zero,16
zero:   sw zero,0(t0)
        addiu t0,t0,4
        addiu t1,t1,-1
        bnez t1,zero
        nop
        ld a0,8(sp)
        ld ra,0(sp)
        addiu sp,sp,0x20
        j 0x2358d0
        nop
""")
    assert len(words) * 4 <= 240
    out.extend(to_patch_lines(CLEAN, words, 'HUD teardown: destroy private animations, free cards, reset owner/state'))
    # All three native destructor thunks reach caSd5Game2D's main destructor.
    # Its ReleaseAllAnim call now cleans private resources first, then calls
    # the exact original function with the original sprite-controller pointer.
    w(0x233DBC, 0x0C000000 | CLEAN >> 2, 'caSd5Game2D destructor -> private HUD cleanup + retail ReleaseAllAnim')
