"""Give the eight-player assignment popup room for 1P–8P and COM."""


def add_position_popup(out, w, assemble, to_patch_lines):
    CAVE = 0x3EAD70  # dead mwPlySetSyncMode, 232 B
    words, _ = assemble(CAVE, """
scale:  .word 0xE4600074
        lw t2,0x15c(s0)
        addiu t3,zero,14
        bne t2,t3,done
        nop
        lw t2,0x154(s0)
        slti t2,t2,7
        bnez t2,done
        nop
        li t2,0x3ff33333
        sw t2,0x74(v1)
done:   jr ra
        nop
""")
    assert len(words) * 4 <= 232
    out.extend(to_patch_lines(CAVE, words, 'Assignment popup: taller frame for 7/8 humans plus COM'))
    # The next scale-Z store remains the call delay slot; preserve v0/v1 and
    # f0 so normal menu-bar initialization proceeds exactly as before.
    w(0x13B8E0, 0x0C000000 | CAVE >> 2, 'Assignment popup: scope frame Y scale to layout 14')
