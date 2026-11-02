"""Isolated two-card HUD sidecar for slots 6 and 7.

The retail caSd5Game2D object has eight slot-to-position entries but only six
0x7c-byte plate records. The bytes immediately after plate 5 are global HUD
animation state, so treating those bytes as plates corrupts the HUD.

This prototype never extends or swaps the retail object. Once GAME2D has
finished loading, it shallow-clones the configured draw objects for the two
top cards into a private heap block. Texture/font tables remain shared
read-only. The cloned font strings, health pips and body/damage layers read
slots 6 and 7 directly. All private card layers use their normal Show path so
the HUD-scoped 50% matrix transform applies uniformly. The private row uses
the renderer's quarter-pixel bias (240 units = 60 pixels). Damage alpha
follows the retail 90-frame pulse period.
"""
import struct


def add_hud_patch(out, w, assemble, to_patch_lines, have_addr):
    PULSE = 0x111F38     # sceSync, 408 B
    MMW = 0x3C0B00       # ADXT_ExecErrChk, 588 B
    INIT = 0x3B8288      # ADXM_SetupThrdEx, 436 B
    CARD = 0x121538      # sceMcSetFileInfo, 456 B
    WRAP = 0x408878      # sfxzmv_MakeOrgZ32TblByCCIR, 536 B
    DMG = 0x3E7F08       # mwPlyGetHdrInf, 404 B
    ANIM = 0x3F22B0      # SFBUF_AringGetWrite, 424 B
    AHELP = 0x3F2550     # SFBUF_AringGetRead, 432 B
    DATA = 0x3B5FC0      # ADX_EncodeHeader, 128 B (data only)

    PTR, OWNER, GACT = DATA, DATA + 4, DATA + 8
    ANIMP, ANIMS = DATA + 0x0C, DATA + 0x14
    PREV = DATA + 0x1C
    FRAME = DATA + 0x24
    PRM = DATA + 0x40
    GSD, GCH, REC, RENDER = 0x529300, 0x526EA0, 0x4921C0, 0x524EB0

    RECT = 0x000
    GAUGE = 0x100
    NAMEBK = 0x210
    FONT = 0x320
    PIPS = 0x490
    BODY = 0x9E0
    CARD_SIZE = 0x1040
    BLOCK_SIZE = CARD_SIZE * 2

    def fb(value):
        return struct.unpack('<I', struct.pack('<f', float(value)))[0]

    for a in range(DATA, PRM, 4):
        w(a, 0, 'HUD sidecar state' if a == DATA else '')
    params = (fb(0.50), fb(640 * 16 * 0.50), fb(448 * 16 * 0.50),
              300, 340, 110, 300)
    for i, value in enumerate(params):
        w(PRM + i * 4, value, 'HUD 50% vertex transform' if i == 0 else '')

    def c1(op, rs, rt, imm):
        return (op << 26) | (rs << 21) | (rt << 16) | (imm & 0xFFFF)

    def lwc1(ft, off, base): return c1(0x31, base, ft, off)
    def swc1(ft, off, base): return c1(0x39, base, ft, off)
    def mul_s(fd, fs, ft): return 0x46000002 | (ft << 16) | (fs << 11) | (fd << 6)
    def add_s(fd, fs, ft): return 0x46000000 | (ft << 16) | (fs << 11) | (fd << 6)
    def cvt_ws(fd, fs): return 0x46000024 | (fs << 11) | (fd << 6)
    def mfc1(rt, fs): return 0x44000000 | (rt << 16) | (fs << 11)
    def mtc1(rt, fs): return 0x44800000 | (rt << 16) | (fs << 11)
    def cvt_sw(fd, fs): return 0x46800020 | (fs << 11) | (fd << 6)
    def raw(word): return f'        .word 0x{word:08X}'

    mmw_src = f"""
mmw:    addiu sp,sp,-0x20
        sd ra,0(sp)
        sd a1,8(sp)
        sd a0,0x10(sp)
        jal 0x14b500
        nop
        ld a1,8(sp)
        ld a0,0x10(sp)
        li t0,{GACT}
        lw t1,0(t0)
        beqz t1,mdone
        nop
        li t0,{PRM}
{raw(lwc1(2, 0, 8))}
{raw(lwc1(4, 4, 8))}
{raw(lwc1(6, 8, 8))}
        lw t3,0xc(t0)
        lw t4,0x10(t0)
        lw t5,0x14(t0)
        lw t6,0x18(t0)
{raw(lwc1(0, 0, 4))}
{raw(cvt_ws(8, 0))}
        nop
{raw(mfc1(8, 8))}
        move t9,zero
        slt t1,t8,t3
        bnez t1,mxl
        nop
        slt t1,t4,t8
        beqz t1,mxc
        nop
        addiu t9,zero,1
        b mxc
        nop
mxl:   addiu t9,zero,-1
mxc:
{raw(lwc1(0, 4, 4))}
{raw(cvt_ws(8, 0))}
        nop
{raw(mfc1(8, 8))}
        move t7,zero
        slt t1,t8,t5
        bnez t1,myl
        nop
        slt t1,t6,t8
        beqz t1,myc
        nop
        addiu t7,zero,1
        b myc
        nop
myl:   addiu t7,zero,-1
myc:
        addiu t2,zero,4
mlp:
{raw(lwc1(0, 0, 5))}
        beqz t9,mxn
        nop
        slt t8,t9,zero
        bnez t8,mxs
        nop
{raw(mul_s(0, 0, 2))}
{raw(add_s(0, 0, 4))}
{raw(swc1(0, 0, 5))}
        j mxn
        nop
mxs:
{raw(mul_s(0, 0, 2))}
{raw(swc1(0, 0, 5))}
mxn:
{raw(lwc1(0, 4, 5))}
        beqz t7,myn
        nop
        slt t8,t7,zero
        bnez t8,mys
        nop
{raw(mul_s(0, 0, 2))}
{raw(add_s(0, 0, 6))}
{raw(swc1(0, 4, 5))}
        j myn
        nop
mys:
{raw(mul_s(0, 0, 2))}
{raw(swc1(0, 4, 5))}
myn:   addiu a1,a1,16
        addiu t2,t2,-1
        bnez t2,mlp
        nop
mdone: ld ra,0(sp)
        addiu sp,sp,0x20
        jr ra
        nop

clone:  lw t0,0(a0)
        sw t0,0(a1)
        addiu a0,a0,4
        addiu a1,a1,4
        addiu a2,a2,-1
        bnez a2,clone
        nop
        jr ra
        nop

clones: addiu sp,sp,-0x30
        sd ra,0(sp)
        sd s4,8(sp)
        sd s5,0x10(sp)
        sd s6,0x18(sp)
        move s4,a0
        move s5,a1
        move s6,a2
csloop:lw a0,0(s4)
        move a1,s5
        addiu a2,zero,68
        jal clone
        nop
        addiu s4,s4,4
        addiu s5,s5,0x110
        addiu s6,s6,-1
        bnez s6,csloop
        nop
        ld ra,0(sp)
        ld s4,8(sp)
        ld s5,0x10(sp)
        ld s6,0x18(sp)
        addiu sp,sp,0x30
        jr ra
        nop
"""
    mmw_words, mmw_labels = assemble(MMW, mmw_src)
    assert MMW + 4 * len(mmw_words) <= MMW + 588

    pulse_src = f"""
pulse: addiu t0,zero,90
{raw(0x0308001B)}
{raw(0x0000C010)}
        slti t0,t8,45
        bnez t0,plo
        nop
        addiu t0,zero,90
        subu t8,t0,t8
plo:    sll t0,t8,1
        srl t1,t8,3
        addu t8,t0,t1
        addiu t8,t8,64
        jr ra
        nop
"""
    pulse_words, pulse_labels = assemble(PULSE, pulse_src)
    assert PULSE + 4 * len(pulse_words) <= PULSE + 408

    init_src = f"""
init:   addiu sp,sp,-0x40
        sd ra,0(sp)
        sd s0,8(sp)
        sd s1,0x10(sp)
        sd s2,0x18(sp)
        sd s3,0x20(sp)
        sd s4,0x28(sp)
        move s0,a0
        li t0,{GSD}
        lw s4,0(t0)
        li t0,{OWNER}
        lw t1,0(t0)
        bne t1,s4,inew
        nop
        li t0,{PTR}
        lw v0,0(t0)
        b iend
        nop
inew:  jal {ANIM}
        nop
        li t0,{PTR}
        lw a0,0(t0)
        beqz a0,ialloc
        nop
        jal 0x100200
        nop
ialloc: addiu a0,zero,{BLOCK_SIZE}
        jal 0x1001e0
        nop
        beqz v0,iend
        nop
        move s1,v0
        li t0,{PTR}
        sw s1,0(t0)
        li t0,{OWNER}
        sw s4,0(t0)
        move s2,zero
        move s3,s1
iloop: sll t0,s2,8
        addu a0,s0,t0
        addiu a0,a0,0x16a0
        addiu a1,s3,{RECT}
        jal {mmw_labels['clone']}
        addiu a2,zero,64
        sll t0,s2,2
        addu t1,s0,t0
        lw a0,0xc08(t1)
        addiu a1,s3,{GAUGE}
        jal {mmw_labels['clone']}
        addiu a2,zero,68
        lw a0,0xc50(t1)
        addiu a1,s3,{NAMEBK}
        jal {mmw_labels['clone']}
        addiu a2,zero,68
        lw a0,0x44f0(t1)
        addiu a1,s3,{FONT}
        jal {mmw_labels['clone']}
        addiu a2,zero,92
        sll t2,s2,4
        sll t3,s2,2
        addu t2,t2,t3
        addu t1,s0,t2
        addiu s4,t1,0xc80
        addiu t3,s3,{PIPS}
        move a0,s4
        move a1,t3
        jal {mmw_labels['clones']}
        addiu a2,zero,5
        nop
        sll t2,s2,4
        sll t3,s2,3
        addu t2,t2,t3
        addu s4,s0,t2
        addiu s4,s4,0xd34
        addiu t3,s3,{BODY}
        move a0,s4
        move a1,t3
        jal {mmw_labels['clones']}
        addiu a2,zero,6
        addiu s2,s2,1
        addiu s3,s3,{CARD_SIZE}
        slti t0,s2,2
        bnez t0,iloop
        nop
        move v0,s1
iend:  ld ra,0(sp)
        ld s0,8(sp)
        ld s1,0x10(sp)
        ld s2,0x18(sp)
        ld s3,0x20(sp)
        ld s4,0x28(sp)
        addiu sp,sp,0x40
        jr ra
        nop
"""
    init_words, init_labels = assemble(INIT, init_src)
    assert INIT + 4 * len(init_words) <= INIT + 436, hex(INIT + 4 * len(init_words))

    damage_src = f"""
setcol: sw a1,0x30(a0)
        sw a2,0x34(a0)
        sw a3,0x38(a0)
        jr ra
        sw t8,0x3c(a0)

damage:addiu sp,sp,-0x30
        sd ra,0(sp)
        sd s0,8(sp)
        sd s1,0x10(sp)
        sd s2,0x18(sp)
        move s0,a0
        addiu a0,a1,0x1b4
        lui a1,0x43
        jal 0x13c640
        ori a1,a1,0x4850
        beqz v0,ddone
        nop
        lw s1,0x10(v0)
        beqz s1,ddone
        nop
        move s2,zero
dloop: sll t0,s2,1
        addu t1,s1,t0
        lh t2,0x20(t1)
        lh t3,0x28(t1)
        addiu t4,zero,255
        addiu t5,zero,20
        addiu t6,zero,20
        addiu t9,zero,1
        slt t7,zero,t2
        beqz t7,dtarget
        nop
        sll t7,t2,1
        addu t7,t7,t2
        sll t8,t3,1
        slt t9,t7,t8
        beqz t9,dblue
        nop
        slt t9,t7,t3
        bnez t9,dorange
        nop
        addiu t5,zero,240
        addiu t6,zero,10
        addiu t9,zero,1
        b dtarget
        nop
dorange:addiu t4,zero,252
        addiu t5,zero,114
        addiu t6,zero,51
        b dtarget
        nop
dblue: move t4,zero
        addiu t5,zero,150
        addiu t6,zero,255
        move t9,zero
dtarget:beqz t9,dsteady
        addiu t8,zero,255
        li t0,{FRAME}
        lw t8,0(t0)
        jal {pulse_labels['pulse']}
        nop
dsteady:sll t0,s2,8
        sll t1,s2,4
        addu t0,t0,t1
        addu a0,s0,t0
        addiu a0,a0,{BODY + 0x110}
        addiu t0,zero,3
        bne s2,t0,dprimary
        nop
        addiu a0,a0,0x110
dprimary:move a1,t4
        move a2,t5
        jal setcol
        move a3,t6
        addiu t0,zero,2
        bne s2,t0,dnext
        nop
        addiu a0,a0,0x110
        move a1,t4
        move a2,t5
        jal setcol
        move a3,t6
dnext: addiu s2,s2,1
        slti t0,s2,4
        bnez t0,dloop
        nop
ddone: ld ra,0(sp)
        ld s0,8(sp)
        ld s1,0x10(sp)
        ld s2,0x18(sp)
        addiu sp,sp,0x30
        jr ra
        nop
"""
    damage_words, damage_labels = assemble(DMG, damage_src)
    assert DMG + 4 * len(damage_words) <= DMG + 404, hex(DMG + 4 * len(damage_words))

    anim_help_src = f"""
pose:   addiu sp,sp,-0x40
        sd ra,0(sp)
        sd s0,8(sp)
        sd s1,0x10(sp)
        sd s2,0x18(sp)
        sd s3,0x20(sp)
        move s0,a0
        move s1,a1
        move s2,a2
        move s3,a3
        move a0,s1
        move a1,s3
        lw t9,0(s1)
        lw t9,0x34(t9)
        jalr t9
        nop
        move a0,s0
        jal 0x23b0c0
        move a1,s2
        addiu v0,v0,68
{raw(mtc1(2, 0))}
        nop
{raw(cvt_sw(0, 0))}
        sw zero,0x60(s1)
{raw(swc1(0, 0x64, 17))}
        li t0,0x4670e8
        lw t0,0(t0)
        sw t0,0x68(s1)
        li t0,0x3f800000
        sw t0,0x6c(s1)
        move v0,s1
        ld ra,0(sp)
        ld s0,8(sp)
        ld s1,0x10(sp)
        ld s2,0x18(sp)
        ld s3,0x20(sp)
        addiu sp,sp,0x40
        jr ra
        nop

start:  addiu sp,sp,-0x40
        sd ra,0(sp)
        sd s0,8(sp)
        sd s1,0x10(sp)
        sd s2,0x18(sp)
        sd s3,0x20(sp)
        move s0,a0
        move s1,a1
        move s3,a2
        addiu s2,s0,0x45c8
        jal 0x1a7fe0
        move a0,s2
        beqz v0,sfail
        nop
        jal 0x1001e0
        addiu a0,zero,0xa0
        beqz v0,sfail
        move a0,v0
        addiu a1,zero,4
        jal 0x196c90
        addiu a2,zero,7
        move s2,v0
        addiu a0,s0,0x45c8
        jal 0x1a80a0
        addiu a1,zero,0x271e
        move s0,v0
        addiu a0,s3,0x45c8
        jal 0x1a8060
        addiu a1,zero,0xe
        move a2,v0
        move a0,s2
        jal 0x196e30
        move a1,s0
        move a0,s3
        move a1,s2
        move a2,s1
        jal pose
        sll a3,s1,1
        b sret
        move v0,s2
sfail: move v0,zero
sret:  ld ra,0(sp)
        ld s0,8(sp)
        ld s1,0x10(sp)
        ld s2,0x18(sp)
        ld s3,0x20(sp)
        addiu sp,sp,0x40
        jr ra
        nop
"""
    anim_help_words, anim_help_labels = assemble(AHELP, anim_help_src)
    assert AHELP + 4 * len(anim_help_words) <= AHELP + 432, hex(AHELP + 4 * len(anim_help_words))

    anim_src = f"""
reset:  addiu sp,sp,-0x20
        sd ra,0(sp)
        sd s0,8(sp)
        sd s1,0x10(sp)
        li s0,{ANIMP}
        addiu s1,zero,2
rloop: lw a0,0(s0)
        beqz a0,rnext
        nop
        lw t9,0(a0)
        lw t9,8(t9)
        jalr t9
        nop
rnext: sw zero,0(s0)
        sw zero,8(s0)
        addiu s0,s0,4
        addiu s1,s1,-1
        bnez s1,rloop
        nop
        li t0,{PREV}
        sw zero,0(t0)
        sw zero,4(t0)
        ld ra,0(sp)
        ld s0,8(sp)
        ld s1,0x10(sp)
        addiu sp,sp,0x20
        jr ra
        nop

anim:   addiu sp,sp,-0x40
        sd ra,0(sp)
        sd s0,8(sp)
        sd s1,0x10(sp)
        sd s2,0x18(sp)
        sd s3,0x20(sp)
        move s0,a0
        move s1,zero
        li s2,{GCH + 24}
        li s3,{ANIMP}
aloop: lw t0,0(s2)
        beqz t0,anext
        nop
        lh t1,0x236(t0)
        beqz t1,aoff
        nop
        lw t2,8(s3)
        bnez t2,arun
        nop
        move a0,s0
        move a1,s1
        jal {anim_help_labels['start']}
        move a2,s0
        sw v0,0(s3)
        beqz v0,anext
        addiu t2,zero,2
        sw t2,8(s3)
        b anext
        nop
arun:   addiu t3,zero,2
        bne t2,t3,anext
        nop
        lw t4,0(s3)
        lbu t5,0x89(t4)
        beqz t5,anext
        nop
        move a0,s0
        move a1,t4
        move a2,s1
        sll a3,s1,1
        jal {anim_help_labels['pose']}
        addiu a3,a3,1
        lw t4,0(s3)
        addiu t5,zero,1
        sb t5,0x88(t4)
        addiu t2,zero,3
        sw t2,8(s3)
        b anext
        nop
aoff:  lw a0,0(s3)
        beqz a0,azero
        nop
        lw t9,0(a0)
        lw t9,8(t9)
        jalr t9
        nop
azero: sw zero,0(s3)
        sw zero,8(s3)
anext: addiu s1,s1,1
        addiu s2,s2,4
        addiu s3,s3,4
        slti t0,s1,2
        bnez t0,aloop
        nop
        ld ra,0(sp)
        ld s0,8(sp)
        ld s1,0x10(sp)
        ld s2,0x18(sp)
        ld s3,0x20(sp)
        addiu sp,sp,0x40
        jr ra
        nop
"""
    anim_words, anim_labels = assemble(ANIM, anim_src)
    assert ANIM + 4 * len(anim_words) <= ANIM + 424, hex(ANIM + 4 * len(anim_words))

    card_src = f"""
show:   lw t9,0xb0(a0)
        lw t9,0x0c(t9)
        jr t9
        nop

card:   addiu sp,sp,-0x40
        sd ra,0(sp)
        sd s0,8(sp)
        sd s1,0x10(sp)
        sd s2,0x18(sp)
        sd s3,0x20(sp)
        move s0,a0
        move s1,a1
        sll t0,s1,5
        li t1,{REC + 0xA}
        addu t0,t0,t1
        lhu a0,0(t0)
        li t1,0x639c
        beq a0,t1,cdone
        nop
        sll t0,s1,2
        li t1,{GCH}
        addu t0,t0,t1
        lw s2,0(t0)
        beqz s2,cdone
        nop
        move a0,s0
        jal {damage_labels['damage']}
        move a1,s2
        sll t0,s1,5
        li t1,{REC + 0xA}
        addu t0,t0,t1
        lhu a0,0(t0)
        jal 0x12cf30
        move a1,zero
        sw v0,{FONT + 0x160}(s0)
        sw zero,{FONT + 0x164}(s0)
        addiu a0,s0,{RECT}
        jal show
        nop
        addiu s3,s0,{BODY}
        addiu s1,zero,6
cbody: move a0,s3
        jal show
        nop
        addiu s3,s3,0x110
        addiu s1,s1,-1
        bnez s1,cbody
        nop
        addiu a0,s0,{GAUGE}
        jal show
        nop
        addiu a0,s0,{NAMEBK}
        jal show
        nop
        lw s1,0x2ac(s2)
        lw s3,0x2b0(s2)
        slt t1,s3,s1
        beqz t1,cmax
        nop
        move s3,s1
cmax:
        slti t0,s3,6
        bnez t0,cpos
        nop
        addiu s3,zero,5
cpos:  slt t0,zero,s3
        beqz t0,cfont
        nop
        addiu s2,s0,{PIPS}
        li t2,{GSD}
        lw t2,0(t2)
        addiu t2,t2,0x50
        lw t2,0x45bc(t2)
        move t0,zero
cpip:  slt t1,t0,s1
        beqz t1,cpempty
        nop
        ld t3,0x10(t2)
        b cptex
        nop
cpempty:ld t3,0x30(t2)
cptex: sd t3,0x100(s2)
        move a0,s2
        jal show
        nop
        addiu s2,s2,0x110
        addiu t0,t0,1
        addiu s3,s3,-1
        bnez s3,cpip
        nop
cfont: addiu a0,s0,{FONT}
        jal 0x132a10
        nop
cdone: ld ra,0(sp)
        ld s0,8(sp)
        ld s1,0x10(sp)
        ld s2,0x18(sp)
        ld s3,0x20(sp)
        addiu sp,sp,0x40
        jr ra
        nop
"""
    card_words, card_labels = assemble(CARD, card_src)
    assert CARD + 4 * len(card_words) <= CARD + 456, hex(CARD + 4 * len(card_words))

    wrap_src = f"""
track:  addiu sp,sp,-0x30
        sd ra,0(sp)
        sd s0,8(sp)
        sd s1,0x10(sp)
        sd s2,0x18(sp)
        li s0,{GCH + 24}
        li s1,{PREV}
        li t6,{FRAME}
        lw t7,0(t6)
        addiu t7,t7,1
        sw t7,0(t6)
        addiu s2,zero,2
tloop:  lw t0,0(s0)
        beqz t0,tnext
        nop
        lw t1,0x2ac(t0)
        lw t2,0(s1)
        sw t1,0(s1)
        slt t3,t1,t2
        beqz t3,tnext
        nop
        li t4,{GSD}
        lw a0,0(t4)
        beqz a0,tnext
        nop
        addiu a0,a0,0x47a0
        li t4,0x527ad8
        jal 0x298f00
        lw a1,0(t4)
        li t4,{GSD}
        lw t4,0(t4)
        lw t5,0x4bf0(t4)
        beqz t5,tnext
        addiu t5,zero,3
        sw t5,0x4bf0(t4)
tnext: addiu s0,s0,4
        addiu s1,s1,4
        addiu s2,s2,-1
        bnez s2,tloop
        nop
        ld ra,0(sp)
        ld s0,8(sp)
        ld s1,0x10(sp)
        ld s2,0x18(sp)
        addiu sp,sp,0x30
        jr ra
        nop

wrap:   addiu sp,sp,-0x40
        sd ra,0(sp)
        sd s0,8(sp)
        sd s1,0x10(sp)
        move s0,a0
        li t0,{have_addr}
        lw t1,0(t0)
        beqz t1,wplain
        nop
        li t0,{GACT}
        addiu t1,zero,1
        sw t1,0(t0)
        jal track
        nop
        addiu a0,s0,-0x20
        jal {anim_labels['anim']}
        nop
wplain: move a0,s0
        jal 0x23dc90
        nop
        li t0,{have_addr}
        lw t1,0(t0)
        beqz t1,wdone
        nop
        addiu s1,s0,-0x20
        lbu t0,0x34(s1)
        beqz t0,wdone
        nop
        move a0,s1
        jal {init_labels['init']}
        nop
        beqz v0,wdone
        nop
        move s1,v0
        li t0,{RENDER}
        lw t0,0(t0)
        lui t1,1
        addu t0,t0,t1
        lw t2,0x620(t0)
        addiu t2,t2,240
        sw t2,0x620(t0)
        move a0,s1
        jal {card_labels['card']}
        addiu a1,zero,6
        addiu a0,s1,{CARD_SIZE}
        jal {card_labels['card']}
        addiu a1,zero,7
        li t0,{RENDER}
        lw t0,0(t0)
        lui t1,1
        addu t0,t0,t1
        lw t2,0x620(t0)
        addiu t2,t2,-240
        sw t2,0x620(t0)
        jal 0x10bea0
        move a0,zero
wdone: li t0,{GACT}
        sw zero,0(t0)
        ld ra,0(sp)
        ld s0,8(sp)
        ld s1,0x10(sp)
        addiu sp,sp,0x40
        jr ra
        nop
"""
    wrap_words, wrap_labels = assemble(WRAP, wrap_src)
    assert WRAP + 4 * len(wrap_words) <= WRAP + 536, hex(WRAP + 4 * len(wrap_words))

    for addr, words, label in ((PULSE, pulse_words, 'HUD retail-timing damage pulse'),
                               (MMW, mmw_words, 'HUD vertex scale'),
                               (INIT, init_words, 'HUD sidecar clone init'),
                               (DMG, damage_words, 'HUD sidecar damage colors'),
                               (ANIM, anim_words, 'HUD sidecar finisher animation'),
                               (AHELP, anim_help_words, 'HUD finisher animation helpers'),
                               (CARD, card_words, 'HUD sidecar card draw'),
                               (WRAP, wrap_words, 'HUD sidecar draw wrapper')):
        out.extend(to_patch_lines(addr, words, label))

    for caller in (0x15E0CC, 0x15E88C, 0x15EF08, 0x15FF0C,
                   0x160A8C, 0x16147C, 0x161C8C):
        w(caller, 0x0C000000 | (mmw_labels['mmw'] >> 2),
          'MulMatrix caller -> HUD scale wrapper')
    w(0x47F05C, wrap_labels['wrap'],
      'CSpriteCtrlGame2D CDraw vtable[3] -> isolated sidecar wrapper')
