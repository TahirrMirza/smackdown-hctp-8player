"""Allow a human defender to counter a direct Irish whip during its windup."""

CASE_THROW = 0x1ED4F0
CASE_THROW_CALL = 0x1EA7C0  # TransactionCase, with the original a0 delay slot
REVERSAL = 0x113C58  # Unreferenced sceSifGetIopAddr, 236 bytes
WHIP_MOTION = 800
REVERSED_WHIP_MOTION = 0x321
WINDUP_START = 20  # CaseThrow starts turning the pair here
WINDUP_END = 42  # Stop before CaseThrow's wall-collision check


def add_whip_reversal(out, w, assemble, to_patch_lines):
    words, _ = assemble(REVERSAL, f"""
        lw t0,0xa4(a0)
        addiu t1,zero,{WHIP_MOTION}
        bne t0,t1,retail
        lw t0,0xb0(a0)
        addiu t0,t0,-{WINDUP_START}
        sltiu t0,t0,{WINDUP_END - WINDUP_START}
        beqz t0,retail
        lw a1,0x3c(a0)
        beqz a1,retail
        nop
        lw t0,0x3c(a1)
        bne t0,a0,retail
        lw t0,0xa4(a1)
        bne t0,t1,retail
        lw t0,0xac(a1)
        addiu t1,zero,1
        bne t0,t1,retail
        lhu t0,0x1da(a1)  # Defender's processed button press for this frame
        andi t0,t0,2      # R2
        beqz t0,retail
        nop

        addiu sp,sp,-0x20
        sd ra,0(sp)
        sd a0,8(sp)
        sd a1,16(sp)
        jal 0x1b9b80      # defender->GetComActive()
        move a0,a1
        ld a0,8(sp)
        ld a1,16(sp)
        bnez v0,restore
        nop

        # Play the native reversed-whip animation with its original roles.
        jal 0x1e45d0      # JumpActDouki(attacker, defender, motion)
        addiu a2,zero,{REVERSED_WHIP_MOTION}
        ld a0,8(sp)
        ld a1,16(sp)
        # Match the native reversed-whip initialization in Nage.
        sh zero,0x230(a0)
        addiu t0,zero,1
        sb t0,0x24b(a0)
        addiu t0,zero,15
        sb t0,0x24d(a0)
        addiu t0,zero,60
        sw t0,0x280(a0)
        lbu t0,0x249(a1)
        sb t0,0x249(a0)
        sw zero,0x280(a1)
        ld ra,0(sp)
        jr ra
        addiu sp,sp,0x20

restore:ld ra,0(sp)
        addiu sp,sp,0x20
retail: j {CASE_THROW}
        nop
""")
    assert len(words) * 4 <= 236
    out.extend(to_patch_lines(REVERSAL, words, 'Direct Irish whip: timed R2 counter for human defenders'))
    w(CASE_THROW_CALL, 0x0C000000 | REVERSAL >> 2, 'TransactionCase: check for a direct Irish-whip counter')
