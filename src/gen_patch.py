"""Generator for the 8-player patch (build s49).

Reads the ORIGINAL SLUS_207.87 (path in $HCTP_ELF), writes a patch list (path in $HCTP_PATCH_OUT) with lines
    <vaddr hex> w <word hex>      one 32-bit word
    <vaddr hex> <hex bytes>       raw bytes
    # ...                         comment ('#@code <start> <end>' marks assembled code blocks for check_patch.py)
vaddr -> file offset: off = vaddr - 0x100000 + 0x80.  build.py runs this and applies the list; run it directly only for debugging.

What the patch does: see docs/HOW_IT_WORKS.md.  Two new match types use the 8-player flow:
LADDER "4 PLAYER ROYAL BATTLE" (record 85, teams of two) and SURVIVAL "8-MAN BATTLE ROYAL" (record 72, every wrestler alone).
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from asm import assemble, to_patch_lines

HERE = os.path.dirname(os.path.abspath(__file__))
ELF_PATH = os.environ['HCTP_ELF']
PATCH_OUT = os.environ.get('HCTP_PATCH_OUT', 'patch.txt')
base = open(os.path.join(HERE, 'base_patches.txt')).read().split('\n')
drop = {0x130FA4, 0x45B581}   # old cave call (forced wrestlers in slots 6,7); record 49 keeps its original 6 players (s45: the 8-player mode is record 85)
out = []
for l in base:
    p = l.split('#')[0].split()
    if p and int(p[0], 16) in drop:
        continue
    out.append(l)
out.append('')
out.append('# ---- two-pass 8-player flow ----')

PASS, HAVE, ZERO, E, BACKUP = 0x110790, 0x110794, 0x1107A0, 0x110800, 0x110C98
POS67 = 0x11227C
CAVE = 0x111210   # dead sceFormat (620 B)
# s47: the 8-player hooks apply to every record whose max-players byte is 8 (records 85 and 72); BRF = 1 when that record
# is in group 7 (battle royal: every wrestler is its own team), 0 for the LADDER mode (teams of two)
BRF = 0x113568
FTAB, RT1, RT2 = 0x11356C, 0x11358C, 0x1135AC     # per mode (BRF * 16): frame teams, real teams of entries 0..3, real teams of entries 4..7


def IS8(rec, w1, w2):
    """asm: w1 = max players of record `rec` (a register), w2 = 8; the caller adds the bne. Clobbers w1, w2 (rec is only read)."""
    return f"""        sll {w1},{rec},5
        lui {w2},0x46
        addiu {w2},{w2},-0x50a0
        addu {w1},{w1},{w2}
        lb {w1},1({w1})
        addiu {w2},zero,8"""


def w(addr, val, c=''):
    out.append(f'{addr:08X} w {val & 0xFFFFFFFF:08X}' + (f'   # {c}' if c else ''))


# data
for a in (PASS, HAVE):
    w(a, 0, 'flag')
for a in range(ZERO, ZERO + 0x60, 4):
    w(a, 0)
for a in range(E, E + 0x60, 4):
    w(a, 0)

copy = """
copy:   lw t6,0(t3)
        sw t6,0(t4)
        addiu t3,t3,4
        addiu t4,t4,4
        addiu t5,t5,-1
        bnez t5,copy
        nop
"""

src = f"""
# ---------- clamp: InitPositionInfo count = min(record[1], 6) ----------
clamp:  lb a1,1(s2)
        sltiu at,a1,7
        bnez at,c1
        nop
        addiu a1,zero,6
c1:     sw a1,0x138(a0)
        lb a1,2(s2)
        jr ra
        nop

# ---------- WrestlerSelectEnd forward hook (s0 = sequence): 4+4 flow, screen 1 -> screen 2 ----------
fwd:    lw a1,0x140(s0)
{IS8('a1', 't2', 't3')}
        bne t2,t3,normal
        nop
        li t0,{PASS}
        lw t1,0(t0)
        bnez t1,done2
        nop
        addiu t1,zero,1
        sw t1,0(t0)
        addiu v0,zero,0x16
        j 0x1322c8
        nop
done2:  sw zero,0(t0)
        li t0,{HAVE}
        addiu t1,zero,1
        sw t1,0(t0)
normal: addiu v0,zero,0xd
        jr ra
        nop

# ---------- WrestlerSelectEnd cancel hook (entered by j at 0x1321C8, v0 = confirmed flag): cancel on screen 2 -> back to screen 1 ----------
cnl:    bnez v0,cgo
        nop
        li t0,{PASS}
        lw t1,0(t0)
        beqz t1,cn2
        nop
        lw t4,0x140(s0)
{IS8('t4', 't2', 't3')}
        bne t2,t3,cn2
        nop
        sw zero,0(t0)
        addiu v0,zero,0x16
        j 0x1322c8
        nop
cn2:    j 0x132258
        nop
cgo:    j 0x1321d0
        nop

# ---------- ConvertPositionData: pad array mask (0x16/0x17 -> pads 6/7); a0 = s0 afterwards ----------
pmask:  addiu t0,sp,0x50
        addiu t2,zero,8
pml:    lw t1,0(t0)
        sltiu t3,t1,0x10
        bnez t3,pmn
        nop
        andi t1,t1,7
        sw t1,0(t0)
pmn:    addiu t0,t0,4
        addiu t2,t2,-1
        bnez t2,pml
        nop
        addiu t0,sp,0x70
        addiu t2,zero,8
pwl:    lw t1,0(t0)
        sltiu t3,t1,0x10
        bnez t3,pwn
        nop
        andi t1,t1,7
        addiu t1,t1,1
        sw t1,0(t0)
pwn:    addiu t0,t0,4
        addiu t2,t2,-1
        bnez t2,pwl
        nop
        jr ra
        daddu a0,s1,zero

# ---------- PlayerEntryNext hook (s4 = sequence): reset the 4+4 state ----------
pe:     li t0,{PASS}
        sw zero,0(t0)
        li t0,{POS67}
        addiu t1,zero,-1
        sw t1,0(t0)
        sw t1,4(t0)
        li t0,{HAVE}
        sw zero,0(t0)
        lw a1,0x140(s4)
        lui a0,0x46
        jr ra
        nop

# ---------- SetCommon entry-address hook: slots 6,7 read from E (or an all-zero block) ----------
fix:    sll v1,a0,4
        sltiu t0,s2,6
        bnez t0,fdone
        nop
        lw t4,0x140(s5)
{IS8('t4', 't1', 't2')}
        li t3,{ZERO}
        bne t1,t2,fuse
        nop
        li t4,{HAVE}
        lw t4,0(t4)
        beqz t4,fuse
        nop
        li t3,{E}
fuse:   addiu t5,s2,-6
        sll t6,t5,1
        addu t6,t6,t5
        sll t6,t6,4
        addu t3,t3,t6
        addiu t3,t3,-0x18
        subu v1,t3,s5
fdone:  jr ra
        nop

# ---------- SelectWrestlerFrame::ChangeIntroduction hook (s2 = frame): on screen 2 cut the screen-1 wrestlers from the grid ----------
cut:    li t0,{PASS}
        lw t0,0(t0)
        beqz t0,cdone
        nop
        addiu sp,sp,-0x20
        sd ra,0(sp)
        sd s0,8(sp)
        sd s1,0x10(sp)
        lw s0,0x18(s2)
        addiu s0,s0,0x1c
        addiu s1,zero,4
cl:     lw a1,0(s0)
        li t1,0x639c
        beq a1,t1,cn
        nop
        addiu a0,s2,0x1e4
        jal 0x2be260
        addiu a2,zero,6
cn:     addiu s0,s0,0x30
        addiu s1,s1,-1
        bnez s1,cl
        nop
        ld ra,0(sp)
        ld s0,8(sp)
        ld s1,0x10(sp)
        addiu sp,sp,0x20
cdone:  lw a0,0x227c(s2)
        beqz a0,cskip
        nop
        jr ra
        nop
cskip:  j 0x24e520
        nop

# ---------- DrawMarker: plate-active test forced on for slots >= 6 while an 8-player match is set up ----------
blk:    sll a2,s3,2
        lw a1,-0x6d00(at)
        addu v1,a1,a2
        lw a0,0x4c98(v1)
        sll v1,a0,5
        subu v1,v1,a0
        sll v1,v1,2
        addu v1,a1,v1
        lw v1,0x48b4(v1)
        sltiu t0,s3,6
        bnez t0,bdone
        nop
        li t0,{HAVE}
        lw t0,0(t0)
        beqz t0,bdone
        nop
        addiu v1,zero,1
bdone:  j 0x29945c
        nop

# ---------- DrawMarker: marker model index clamp (models exist for HUD slots 0..6) ----------
clx:    lw a0,0x390(s0)
        sltiu at,a0,7
        bnez at,clk
        nop
        addiu a0,zero,6
clk:    jr ra
        nop
"""
words, lab = assemble(CAVE, src)
for l in to_patch_lines(CAVE, words, 'two-pass cave code in dead sceFormat'):
    out.append(l)
end = CAVE + 4 * len(words)
assert end <= CAVE + 1000, hex(end)
print('cave bytes', 4 * len(words), 'labels', {k: hex(v) for k, v in lab.items() if k in ('clamp', 'fwd', 'pe', 'fix')})

# hooks
w(0x1307E8, 0x0C000000 | (lab['clamp'] >> 2), 'InitPositionInfo: jal clamp')
w(0x1321D0, 0x0C000000 | (lab['fwd'] >> 2), 'WrestlerSelectEnd: jal fwd')
w(0x131DB4, 0x0C000000 | (lab['pe'] >> 2), 'PlayerEntryNext: jal pe')
w(0x130DF4, 0x0C000000 | (lab['fix'] >> 2), 'SetCommon: jal fix (entry address for slots>=6)')
w(0x24E510, 0x0C000000 | (lab['cut'] >> 2), 'SelectWrestlerFrame::ChangeIntroduction: jal cut')
w(0x299438, 0x0C000000 | (lab['blk'] >> 2), 'DrawMarker: jal blk (plate active override)')
w(0x2994E0, 0x0C000000 | (lab['clx'] >> 2), 'DrawMarker: jal clx (clamp marker model index)')
w(0x299760, 0x2A630008, 'DrawMarker loop over 8 slots')
# (s45: string id 29 keeps its original text TRIPLE THREAT TORNADO TAG; the 8-player mode has its own title string id 832)
# slot 6 is a wrestler now: full-height (0xc0) character texture buffer/readback
w(0x1DC710, 0x241100C0, 'UpdateBloodTex: slot 6 height 0xc0')
w(0x1BA474, 0x241400C0, 'char tex upload: slot 6 height 0xc0')
w(0x202C40, 0x240300C0, 'SetupCharTexBuf: slot 6 buffer 192 KB')
# SetCommon: 8 slots, 8 pad numbers
w(0x130DDC, 0x2E420008, 'sltiu v0,s2,8 (first test)')
w(0x130F80, 0x2E420008, 'sltiu v0,s2,8 (loop test)')
w(0x130D4C, 0x2C620008, 'pad bitmap clear <8')
w(0x130D84, 0x28410008, 'human pad < 8')
w(0x130E64, 0x2C820008, 'pad search <8')
w(0x130E8C, 0x2C820008, 'pad search <8')
w(0x130F94, 0x00000000, 'nop: do not wipe slot 6 id')
w(0x130FA4, 0x00000000, 'nop: do not wipe slot 7 id')

# ======================= Position screen, stage 2: 8 boxes (layout 5) for record 49, cycle-select instead of popup =======================
from remap_frame import remap_patches
import remap_frame as _r
import struct as _st
PCAVE = 0x1115C0
TMPOLD = 0x1120D0            # 0x148-byte old-layout copy of the struct for PositionSelectWindowFrame
TBLSTR = 0x112220            # tblstrPlayerNo (10 entries)
TBLPNO = 0x112248            # tblPlayerNo (9 entries)
GSPTR = 0x1134E0             # string pointers for ids 830, 831, 832 (s45: moved, 3 entries)
STR7P, STR8P = 0x112274, 0x112278
LAYOUT5 = 0x45BD10 + 5 * 0xC4
NEWTBL = 0x112598            # relocated tbltagPadSelectLayout (14 rows x 0x30) + row 14 for layout 5
import json as _json
import remap_win as _rw


def cp(label, src, dst):
    return f"""
{label}:  lw t3,0({src})
        sw t3,0({dst})
        addiu {src},{src},4
        addiu {dst},{dst},4
        addiu t2,t2,-1
        bnez t2,{label}
        nop
"""


psrc = f"""
# xl: t6 = address of an E pos value; translate 0x16/0x17 -> 7/8, validate against humans t5
xl:     lw t7,0(t6)
        addiu t8,zero,0x16
        bne t7,t8,xl1
        nop
        addiu t7,zero,7
xl1:    addiu t8,zero,0x17
        bne t7,t8,xl2
        nop
        addiu t7,zero,8
xl2:    sltiu t8,t7,9
        beqz t8,xlc
        nop
        addiu t8,zero,6
        beq t7,t8,xls
        nop
        move t8,t7
        sltiu at,t7,6
        bnez at,xlp
        nop
        addiu t8,t7,-1
xlp:    sltu at,t8,t5
        bnez at,xls
        nop
xlc:    addiu t7,zero,6
xls:    sw t7,0(t6)
        jr ra
        nop

# xr: t6 = address of a pos value; 7/8 -> 0x16/0x17
xr:     lw t7,0(t6)
        addiu t8,zero,7
        bne t7,t8,xr1
        nop
        addiu t7,zero,0x16
        sw t7,0(t6)
xr1:    addiu t8,zero,8
        bne t7,t8,xr2
        nop
        addiu t7,zero,0x17
        sw t7,0(t6)
xr2:    jr ra
        nop

# copy src struct (a1) into frame struct (a0): entries 0..5, E entries as 6,7, scalars (+0x120) moved to +0x180
cpin:   move a3,ra
        move t9,a0
        move t0,a0
        move t1,a1
        addiu t2,zero,72
{cp('ci1', 't1', 't0')}
        li t1,{E}
        addiu t2,zero,24
{cp('ci2', 't1', 't0')}
        addiu t1,a1,0x120
        addiu t2,zero,10
{cp('ci3', 't1', 't0')}
        lw t6,0x188(t9)
{IS8('t6', 't3', 't4')}
        bne t3,t4,cid
        nop
        addiu t4,zero,5
        sw t4,0x224(t9)
        lw t5,0x184(t9)
        li t3,{POS67}
        lw t4,0(t3)
        addiu t8,zero,-1
        beq t4,t8,dd1
        nop
        sw t4,0x128(t9)
        addiu t6,t9,0x128
        jal xl
        nop
        j dd1e
        nop
dd1:    addiu t4,zero,6
        sltiu at,t5,7
        bnez at,dd1s
        nop
        addiu t4,zero,7
dd1s:   sw t4,0x128(t9)
dd1e:   li t3,{POS67}
        lw t4,4(t3)
        addiu t8,zero,-1
        beq t4,t8,dd2
        nop
        sw t4,0x158(t9)
        addiu t6,t9,0x158
        jal xl
        nop
        j cid
        nop
dd2:    addiu t4,zero,6
        sltiu at,t5,8
        bnez at,dd2s
        nop
        addiu t4,zero,8
dd2s:   sw t4,0x158(t9)
cid:    jr a3
        nop

# copy frame struct (a1) back into the sequence struct (a0); entries 6,7 -> E; 7/8 become pads 0x16/0x17
cpout:  move a3,ra
        move t9,a0
        move t0,a0
        move t1,a1
        addiu t2,zero,72
{cp('co1', 't1', 't0')}
        li t0,{E}
        addiu t2,zero,24
{cp('co2', 't1', 't0')}
        addiu t0,t9,0x120
        addiu t2,zero,10
{cp('co3', 't1', 't0')}
        move t5,zero
cox:    sll t6,t5,1
        addu t6,t6,t5
        sll t6,t6,4
        addu t6,t9,t6
        addiu t6,t6,8
        jal xr
        nop
        addiu t5,t5,1
        sltiu at,t5,6
        bnez at,cox
        nop
        li t6,{E + 8}
        jal xr
        nop
        li t6,{E + 0x38}
        jal xr
        nop
        li t3,{E}
        li t4,{POS67}
        lw t5,8(t3)
        sw t5,0(t4)
        lw t5,0x38(t3)
        sw t5,4(t4)
        jr a3
        nop

# PositionSelectWindowFrame ctor hook: a2 = frame struct -> old-layout temp copy
wfh:    li t0,{TMPOLD}
        move t1,a2
        addiu t2,zero,72
{cp('wf1', 't1', 't0')}
        addiu t1,a2,0x180
        addiu t2,zero,10
{cp('wf2', 't1', 't0')}
        li a2,{TMPOLD}
        j 0x13b4f0
        nop

# ChangeDecision hook (entered with a0 = frame; delay slot was 'lui a3,0x46'): layout 5 -> open the player popup
cyc:    lw t0,0x240(a0)
        addiu t1,zero,5
        bne t0,t1,cynorm
        nop
        lw t0,0x1ec(a0)
        addiu t1,zero,6
        beq t0,t1,cynorm
        nop
        lw t1,0x2c4(a0)
        bnez t1,cyret
        nop
        addiu sp,sp,-0x40
        sd ra,0x30(sp)
        sd s0,0x20(sp)
        sd s1,0x10(sp)
        move s0,a0
        move s1,t0
        move t2,t0
        sltiu at,t0,6
        bnez at,cs1
        nop
        addiu t2,t0,-1
cs1:    sll t3,t2,1
        addu t3,t3,t2
        sll t3,t3,4
        addu t3,s0,t3
        lw t4,0x24(t3)
        lw t5,0x1a0(s0)
        move t6,t4
        addiu t7,zero,6
        bne t4,t7,ix1
        nop
        move t6,t5
        j ix2
        nop
ix1:    sltiu at,t4,6
        bnez at,ix2
        nop
        addiu t6,t4,-1
ix2:    sd t6,0x08(sp)
        li t0,{TMPOLD}
        addiu t1,s0,0x1c
        addiu t2,zero,72
{cp('cy1', 't1', 't0')}
        addiu t1,s0,0x19c
        addiu t2,zero,10
{cp('cy2', 't1', 't0')}
        li t0,{TMPOLD}
        ld t6,0x08(sp)
        sw t6,8(t0)
        addiu t1,zero,14
        sw t1,0x12c(t0)
        jal 0x1001e0
        addiu a0,zero,0x1d4
        beqz v0,cywz
        nop
        move a0,v0
        move a1,zero
        li a2,{TMPOLD}
        ld a3,0x08(sp)
        jal 0x13b4f0
        move t0,zero
        sw s1,0x180(v0)
        lw t0,0x1cc(v0)
        beqz t0,cywp
        nop
        sw s1,0x184(t0)
cywp:   sll t1,s1,3
        li t2,{NEWTBL + 14 * 0x30}
        addu t1,t1,t2
        lw t3,0(t1)
        sw t3,0x28(v0)
        lw t3,4(t1)
        sw t3,0x2c(v0)
cywz:   sw v0,0x2c4(s0)
        ld ra,0x30(sp)
        ld s0,0x20(sp)
        ld s1,0x10(sp)
        addiu sp,sp,0x40
cyret:  jr ra
        nop
cynorm: addiu sp,sp,-0x30
        j 0x139a38
        nop

# apply: a0 = frame, t2 = slot, t6 = value. Assign, dedupe, refresh plate labels.
apply:  sll t3,t2,1
        addu t3,t3,t2
        sll t3,t3,4
        addu t3,a0,t3
        sw t6,0x24(t3)
        addiu t7,zero,6
        beq t6,t7,cref
        nop
        move t8,zero
cdd:    beq t8,t2,cdn
        nop
        sll t9,t8,1
        addu t9,t9,t8
        sll t9,t9,4
        addu t9,a0,t9
        lw t7,0x24(t9)
        bne t7,t6,cdn
        nop
        addiu t7,zero,6
        sw t7,0x24(t9)
cdn:    addiu t8,t8,1
        sltiu at,t8,8
        bnez at,cdd
        nop
cref:   move t8,zero
crl:    addiu t7,zero,6
        beq t8,t7,crn
        nop
        sll t9,t8,2
        addu t9,a0,t9
        lw t9,0x1c8(t9)
        beqz t9,crn
        nop
        move t7,t8
        sltiu at,t8,6
        bnez at,crs
        nop
        addiu t7,t8,-1
crs:    sll t0,t7,1
        addu t0,t0,t7
        sll t0,t0,4
        addu t0,a0,t0
        lw t0,0x24(t0)
        sltiu at,t0,6
        bnez at,cre
        nop
        addiu t0,t0,1
cre:    sw t0,0x40(t9)
crn:    addiu t8,t8,1
        sltiu at,t8,9
        bnez at,crl
        nop
        jr ra
        nop

# InputAction wrapper (vtable slot 17): finish the popup, then run the original
iaw:    lw t0,0x240(a0)
        addiu t1,zero,5
        bne t0,t1,iawo
        nop
        lw t1,0x2c4(a0)
        beqz t1,iawo
        nop
        addiu sp,sp,-0x40
        sd ra,0x30(sp)
        sd s0,0x20(sp)
        sd s1,0x10(sp)
        move s0,a0
        move s1,t1
        move a0,s1
        lw t2,0(s1)
        lw t9,0x2c(t2)
        jalr t9
        nop
        beqz v0,iawx
        nop
        lw t5,0x1a0(s0)
        lw t4,0x17c(s1)
        addiu t6,zero,6
        beq t4,t5,iv
        nop
        move t6,t4
        sltiu at,t4,6
        bnez at,iv
        nop
        addiu t6,t4,1
iv:     lw t0,0x1ec(s0)
        move t2,t0
        sltiu at,t0,6
        bnez at,iv2
        nop
        addiu t2,t0,-1
iv2:    sltiu at,t6,7
        bnez at,iok
        nop
        sltiu at,t2,6
        bnez at,iskip
        nop
iok:    move a0,s0
        jal apply
        nop
iskip:  move a0,s1
        addiu a1,zero,1
        lw t2,0(a0)
        lw t9,8(t2)
        jalr t9
        nop
        sw zero,0x2c4(s0)
        lw t0,0x1c4(s0)
        addiu t1,zero,1
        sw t1,0x24(t0)
iawx:   move a0,s0
        ld ra,0x30(sp)
        ld s0,0x20(sp)
        ld s1,0x10(sp)
        addiu sp,sp,0x40
iawo:   j 0x139f00
        nop

# PositionPlayerSelectDrawer::Draw label hook: items 6,7 -> string ids 830/831 ("7P"/"8P")
lblh:   sltiu at,s1,6
        bnez at,lblg
        nop
        addiu a0,s1,824
lblg:   j 0x12fd60
        nop

# AllEntryplayerDecision hook (entered with a0 = frame; delay slot executed 'addiu sp,sp,-0x20')
aed:    lw t0,0x240(a0)
        addiu t1,zero,5
        bne t0,t1,aedn
        nop
        lw t5,0x1a0(a0)
        move t2,zero
al:     sltu at,t2,t5
        beqz at,aok
        nop
        move t3,t2
        sltiu at,t2,6
        bnez at,av
        nop
        addiu t3,t2,1
av:     move t4,zero
as1:    sll t6,t4,1
        addu t6,t6,t4
        sll t6,t6,4
        addu t6,a0,t6
        lw t6,0x24(t6)
        beq t6,t3,af
        nop
        addiu t4,t4,1
        sltiu at,t4,8
        bnez at,as1
        nop
        addiu sp,sp,0x20
        move v0,zero
        jr ra
        nop
af:     addiu t2,t2,1
        j al
        nop
aok:    addiu sp,sp,0x20
        addiu v0,zero,1
        jr ra
        nop
aedn:   lui a2,0x41
        j 0x139998
        nop

# WaitAction: after the Continue plate is stored, create plates for layout indices 7,8 (slots 6,7)
xpl:    sw v0,0x1e0(s1)
        lw t0,0x240(s1)
        addiu t1,zero,5
        bne t0,t1,xpd
        nop
        addiu sp,sp,-0x30
        sd ra,0x20(sp)
        addiu s0,zero,7
xp1:    addiu s2,s0,-1
        sll v1,s2,1
        addu v1,v1,s2
        sll v1,v1,4
        addu s3,s1,v1
        lw v1,0x24(s3)
        sll v1,v1,2
        li v0,{TBLPNO}
        addu v0,v0,v1
        lw s2,0(v0)
        jal 0x1001e0
        addiu a0,zero,0xb0
        beqz v0,xp2
        nop
        lw t1,0x30(s3)
        move t2,s2
        lw a1,0x240(s1)
        move a0,v0
        move a2,s0
        move a3,zero
        jal 0x13a3b0
        addiu t0,zero,0xb
xp2:    sll v1,s0,2
        addu v1,s1,v1
        sw v0,0x1c8(v1)
        addiu s0,s0,1
        sltiu at,s0,9
        bnez at,xp1
        nop
        ld ra,0x20(sp)
        addiu sp,sp,0x30
xpd:    lw t9,0(s1)
        jr ra
        nop

# PositionSelectUI ctor: item count 9 for layout 5
uih:    addiu at,zero,5
        bne s0,at,uihg
        nop
        addiu t1,zero,9
uihg:   j 0x12e800
        nop

# GetPlateColor(index): indices >= 7 get fixed colours
gpc:    sltiu at,a0,7
        beqz at,gpx
        nop
        lui v0,0x46
        addiu v0,v0,-0x4400
        sll v1,a0,2
        addu v0,v0,v1
        jr ra
        lw v0,0(v0)
gpx:    addiu v1,zero,7
        beq a0,v1,gp7
        nop
        addiu v0,zero,4
        jr ra
        nop
gp7:    addiu v0,zero,5
        jr ra
        nop

# string getter: ids 830/831 -> "7P"/"8P"
gsh:    slti v0,a2,0x33e
        bne v0,zero,gsgo
        nop
        slti v0,a2,0x342
        beqz v0,gserr
        addiu v1,a2,-830
        sll v1,v1,2
        li v0,{GSPTR}
        addu v0,v0,v1
        lw v0,0(v0)
        j 0x12fdac
        nop
gserr:  j 0x12fd7c
        nop
gsgo:   lui v0,0x41
        j 0x12fd9c
        nop
"""
pw, pl = assemble(PCAVE, psrc)
out.append('')
out.append('# ---- position screen stage 2 ----')
for l in to_patch_lines(PCAVE, pw, 'position frame cave code (dead sceDopen..sceRename)'):
    out.append(l)
pend = PCAVE + 4 * len(pw)
assert pend <= 0x111F18, hex(pend)
print('pos cave bytes', 4 * len(pw), 'end', hex(pend))

# data tables
for i, v in enumerate((96, 97, 98, 99, 100, 101, 91, 102, 830, 831)):
    w(TBLSTR + 4 * i, v, 'tblstrPlayerNo' if i == 0 else '')
for i, v in enumerate((0, 1, 2, 3, 4, 5, 7, 8, 9)):
    w(TBLPNO + 4 * i, v, 'tblPlayerNo' if i == 0 else '')
w(GSPTR, STR7P, 'string ptr 830')
w(GSPTR + 4, STR8P, 'string ptr 831')
STR9, STR10 = 0x1134F0, 0x113508
w(GSPTR + 8, STR9, 'string ptr 832')
w(GSPTR + 12, STR10, 'string ptr 833')
out.append(f'{STR9:08X} {b"4 PLAYER ROYAL BATTLE".ljust(24, bytes(1)).hex()}   # string id 832')
out.append(f'{STR10:08X} {b"8-MAN BATTLE ROYAL".ljust(24, bytes(1)).hex()}   # string id 833')
out.append(f'{STR7P:08X} {b"7P".ljust(4, bytes(1)).hex()}   # "7P"')
out.append(f'{STR8P:08X} {b"8P".ljust(4, bytes(1)).hex()}   # "8P"')
w(POS67, 6)
w(POS67 + 4, 6)
for a in (0x110860, 0x110864):
    w(a, 0, 'E tail')


# layout type 5 (entries 0..5 boxes, 6 continue, 7,8 boxes for slots 6,7): x,y,up,down,left,right,id
def ent(x, y, u, d, l, r, i):
    return _st.pack('<ffiiiii', float(x), float(y), u, d, l, r, i)


YA, YB, YC, YD = 128, 206, 284, 362
L5 = [ent(142, YA, 5, 2, 1, 6, 0), ent(498, YA, 8, 3, 6, 0, 1),
      ent(142, YB, 0, 4, 3, 3, 2), ent(498, YB, 1, 7, 2, 2, 3),
      ent(142, YC, 2, 5, 7, 7, 4), ent(142, YD, 4, 0, 8, 8, 5),
      ent(320, YA, -1, -1, 0, 1, 6),
      ent(498, YC, 3, 8, 4, 4, 9), ent(498, YD, 7, 1, 5, 5, 10)]
out.append(f'{LAYOUT5:08X} {b"".join(L5).hex()}   # tblPosSelectLayout type 5 (9 entries, spills into unused type 6)')


def pair(lui_a, addi_a, new):
    lw_ = _r.word(lui_a)
    aw = _r.word(addi_a)
    w(lui_a, (lw_ & ~0xFFFF) | (new >> 16), 'reloc hi')
    w(addi_a, (aw & ~0xFFFF) | (new & 0xFFFF), 'reloc lo')


pair(0x13A8D0, 0x13A8D4, TBLSTR)          # FontInit tblstrPlayerNo
pair(0x13ABBC, 0x13ABC4, TBLSTR)          # Draw tblstrPlayerNo
pair(0x139D48, 0x139D50, TBLPNO)          # WaitAction tblPlayerNo

for _a, _w, _c in remap_patches():
    w(_a, _w, _c)
for _a in (0x139600, 0x139728, 0x139840, 0x139964, 0x139B1C, 0x139C84):   # plate loops 7 -> 9
    w(_a, (_r.word(_a) & ~0xFFFF) | 9, 'plate loop 9')
w(0x139614, 0x24050048, 'ctor: clear 9 UI items (0x48)')
w(0x1395E4, 0x0C000000 | (pl['cpin'] >> 2), 'frame ctor: AMemCopy -> cpin')
w(0x139AA0, 0x0C000000 | (pl['cpout'] >> 2), 'ChangeDecision: AMemCopy -> cpout')
w(0x139B8C, 0x0C000000 | (pl['wfh'] >> 2), 'ChangeDecision: WindowFrame ctor -> wfh')
w(0x139A30, 0x08000000 | (pl['cyc'] >> 2), 'ChangeDecision: j cyc')
w(0x139990, 0x08000000 | (pl['aed'] >> 2), 'AllEntryplayerDecision: j aed')
w(0x139DEC, 0x0C000000 | (pl['xpl'] >> 2), 'WaitAction: jal xpl (extra plates)')
w(0x13B270, 0x0C000000 | (pl['uih'] >> 2), 'PositionSelectUI ctor: jal uih')
w(0x1394D0, 0x08000000 | (pl['gpc'] >> 2), 'GetPlateColor: j gpc')
w(0x12FD70, 0x08000000 | (pl['gsh'] >> 2), 'GetRCString: j gsh')
w(0x12FD74, 0x00000000, 'delay slot nop')
w(0x132090, 0x24040000 | 0x2C8, 'PositionSelectNext: alloc 0x250 -> 0x2c8')


# ---- real popup for layout 5 ----
_rows = _json.load(open(os.path.join(HERE, 'padlayout_rows.json')))
for _t, _row in enumerate(_rows):
    for _i, _v in enumerate(_row):
        w(NEWTBL + _t * 0x30 + 4 * _i, _v, 'popup position table' if (_t, _i) == (0, 0) else '')
_P = {0: (252, 180), 1: (388, 180), 2: (252, 215), 3: (388, 215), 4: (252, 260), 5: (252, 290), 6: (0, 0), 7: (388, 260), 8: (388, 290)}
for _i in range(9):
    _x, _y = _P[_i]
    w(NEWTBL + 14 * 0x30 + 8 * _i, _st.unpack('<I', _st.pack('<f', float(_x)))[0], 'popup pos row 14' if _i == 0 else '')
    w(NEWTBL + 14 * 0x30 + 8 * _i + 4, _st.unpack('<I', _st.pack('<f', float(_y)))[0])
pair(0x13B7BC, 0x13B7C8, NEWTBL)
pair(0x13B7C4, 0x13B7CC, NEWTBL + 4)
pair(0x13BE94, 0x13BEA4, NEWTBL)
pair(0x13BE9C, 0x13BEAC, NEWTBL + 4)
for _a, _w, _c in _rw.remap_patches():
    w(_a, _w, _c)
w(0x13B594, 0x24020009, 'WindowFrame ctor: max items 7 -> 9')
w(0x13B6D4, 0x24050048, 'WindowFrame::Init: clear 9 items')
w(0x13C00C, 0x0C000000 | (pl['lblh'] >> 2), 'Drawer::Draw: label hook (1)')
w(0x13C0A4, 0x0C000000 | (pl['lblh'] >> 2), 'Drawer::Draw: label hook (2)')
w(0x47B614, pl['iaw'], 'PositionSelectFrame vtable[17] InputAction -> iaw')

# ---------------- stage 1: SelectWrestlerFrame grown to 8 entries (behaviour unchanged) ----------------
import remap_sel as _rs
SCAVE = 0x112880
_ssrc = f"""
# scpin: a0 = frame struct (dest), a1 = sequence struct (src).
# Record 49 (4+4 flow): screen 1 shows entries 0..3, screen 2 shows entries 4,5 + E0,E1 (teams -2) in frame entries 0..3; type scalar = 3 (2x2 layout)
scpin:  move t9,a0
        lw t5,0x128(a1)
        move t8,t5
{IS8('t5', 't6', 't7')}
        bne t6,t7,sstd
        nop
        sll t6,t8,5
        lui t7,0x46
        addiu t7,t7,-0x50a0
        addu t6,t6,t7
        lb t6,0(t6)
        addiu t6,t6,-7
        sltiu t6,t6,1
        li t7,{BRF}
        sw t6,0(t7)
        li t7,{PASS}
        lw t7,0(t7)
        bnez t7,sp1
        nop
        addiu t1,a1,0xF0
        li t0,{E}
        addiu t2,zero,12
{cp('sa', 't1', 't0')}
        addiu t1,a1,0xF0
        li t0,{E + 0x30}
        addiu t2,zero,12
{cp('sb', 't1', 't0')}
        li t0,{E}
        addiu t1,zero,6
        sw t1,0(t0)
        sw t1,0xc(t0)
        addiu t1,zero,7
        sw t1,0x30(t0)
        sw t1,0x3c(t0)
        addiu t1,zero,1
        sw t1,4(t0)
        sw t1,0x34(t0)
        li t3,{BRF}
        lw t3,0(t3)
        sll t3,t3,4
        li t4,{RT2}
        addu t4,t4,t3
        lw t1,8(t4)
        sw t1,0x10(t0)
        lw t1,0xc(t4)
        sw t1,0x40(t0)
        li t3,{POS67}
        addiu t8,zero,-1
        lw t4,0(t3)
        bne t4,t8,pa
        nop
        lw t6,0x124(a1)
        addiu t4,zero,6
        sltiu t7,t6,7
        bnez t7,pa
        nop
        addiu t4,zero,0x16
pa:     sw t4,8(t0)
        lw t4,4(t3)
        bne t4,t8,pb
        nop
        lw t6,0x124(a1)
        addiu t4,zero,6
        sltiu t7,t6,8
        bnez t7,pb
        nop
        addiu t4,zero,0x17
pb:     sw t4,0x38(t0)
        lw t1,8(t0)
        addiu t1,t1,-6
        sltu t1,zero,t1
        sw t1,4(t0)
        lw t1,0x38(t0)
        addiu t1,t1,-6
        sltu t1,zero,t1
        sw t1,0x34(t0)
        move t0,t9
        move t1,a1
        addiu t2,zero,48
{cp('sc', 't1', 't0')}
        jal ftw
        nop
        addiu t0,t9,0xC0
        addiu t2,zero,48
z1:     sw zero,0(t0)
        addiu t0,t0,4
        addiu t2,t2,-1
        bnez t2,z1
        nop
        j sscal
        nop
sp1:    move t0,t9
        addiu t1,a1,0xC0
        addiu t2,zero,24
{cp('sd', 't1', 't0')}
        li t1,{E}
        addiu t2,zero,24
{cp('se', 't1', 't0')}
        sw zero,0(t9)
        addiu t1,zero,1
        sw t1,0x30(t9)
        addiu t1,zero,2
        sw t1,0x60(t9)
        addiu t1,zero,3
        sw t1,0x90(t9)
        jal ftw
        nop
        addiu t0,t9,0xC0
        addiu t2,zero,48
z2:     sw zero,0(t0)
        addiu t0,t0,4
        addiu t2,t2,-1
        bnez t2,z2
        nop
sscal:  addiu t1,a1,0x120
        addiu t0,t9,0x180
        addiu t2,zero,10
{cp('sf', 't1', 't0')}
        addiu t1,zero,3
        sw t1,0x18c(t9)
        jr ra
        nop
sstd:   move t0,a0
        move t1,a1
        addiu t2,zero,72
{cp('si1', 't1', 't0')}
        addiu t2,zero,24
sz:     sw zero,0(t0)
        addiu t0,t0,4
        addiu t2,t2,-1
        bnez t2,sz
        nop
        addiu t1,a1,0x120
        addiu t2,zero,10
{cp('si3', 't1', 't0')}
        jr ra
        nop

# scpout: a0 = sequence struct (dest), a1 = frame struct (src)
scpout: lw t5,0x128(a0)
{IS8('t5', 't6', 't7')}
        bne t6,t7,sostd
        nop
        li t7,{PASS}
        lw t7,0(t7)
        bnez t7,sox
        nop
        move t0,a0
        move t1,a1
        addiu t2,zero,48
{cp('sa2', 't1', 't0')}
        li t3,{BRF}
        lw t3,0(t3)
        sll t3,t3,4
        li t4,{RT1}
        addu t4,t4,t3
        lw t1,0(t4)
        sw t1,0x10(a0)
        lw t1,4(t4)
        sw t1,0x40(a0)
        lw t1,8(t4)
        sw t1,0x70(a0)
        lw t1,0xc(t4)
        sw t1,0xA0(a0)
        jr ra
        nop
sox:    addiu t0,a0,0xC0
        move t1,a1
        addiu t2,zero,24
{cp('sb2', 't1', 't0')}
        li t0,{E}
        addiu t2,zero,24
{cp('sc2', 't1', 't0')}
        addiu t1,zero,4
        sw t1,0xC0(a0)
        addiu t1,zero,5
        sw t1,0xF0(a0)
        li t0,{E}
        addiu t1,zero,6
        sw t1,0(t0)
        addiu t1,zero,7
        sw t1,0x30(t0)
        li t3,{BRF}
        lw t3,0(t3)
        sll t3,t3,4
        li t4,{RT2}
        addu t4,t4,t3
        lw t1,0(t4)
        sw t1,0xD0(a0)
        lw t1,4(t4)
        sw t1,0x100(a0)
        li t0,{E}
        lw t1,8(t4)
        sw t1,0x10(t0)
        lw t1,0xc(t4)
        sw t1,0x40(t0)
        jr ra
        nop
sostd:  move t0,a0
        move t1,a1
        addiu t2,zero,72
{cp('so1', 't1', 't0')}
        addiu t1,t1,0x60
        addiu t0,a0,0x120
        addiu t2,zero,10
{cp('so3', 't1', 't0')}
        jr ra
        nop
"""
# code size: the inlined word-copy loops are replaced by one shared routine (cpw, t1 = src, t0 = dst, t2 = words);
# scpin/scpout keep their return address in a3 because they now call cpw
for _l in ('sa', 'sb', 'sc', 'sd', 'se', 'sf', 'si1', 'si3', 'sa2', 'sb2', 'sc2', 'so1', 'so3'):
    assert cp(_l, 't1', 't0') in _ssrc, _l
    _ssrc = _ssrc.replace(cp(_l, 't1', 't0'), '        jal @CPW@\n        nop')
_ssrc = _ssrc.replace('        jr ra\n        nop', '        jr a3\n        nop')
assert _ssrc.count('scpin:  move t9,a0') == 1 and _ssrc.count('scpout: lw t5,0x128(a0)') == 1
_ssrc = _ssrc.replace('scpin:  move t9,a0', 'scpin:  move a3,ra\n        move t9,a0')
_ssrc = _ssrc.replace('scpout: lw t5,0x128(a0)', 'scpout: move a3,ra\n        lw t5,0x128(a0)')
_part_in, _part_out = _ssrc.split("# scpout:")
_part_out = "# scpout:" + _part_out
_part_in += f"""
ftw:    li t3,{BRF}
        lw t3,0(t3)
        sll t3,t3,4
        li t4,{FTAB}
        addu t4,t4,t3
        lw t1,0(t4)
        sw t1,0x10(t9)
        lw t1,4(t4)
        sw t1,0x40(t9)
        lw t1,8(t4)
        sw t1,0x70(t9)
        lw t1,0xc(t4)
        sw t1,0xA0(t9)
        jr ra
        nop
cpw:    lw t3,0(t1)
        sw t3,0(t0)
        addiu t1,t1,4
        addiu t0,t0,4
        addiu t2,t2,-1
        bnez t2,cpw
        nop
        jr ra
        nop
"""
_part_in = _part_in.replace('@CPW@', 'cpw')
SCAVE2 = 0x112D88
_sw, _sl1 = assemble(SCAVE, _part_in)
_part_out = _part_out.replace('@CPW@', hex(_sl1['cpw']))
_sw2, _sl2 = assemble(SCAVE2, _part_out)
_sl = {**_sl1, **_sl2}
for _l in to_patch_lines(SCAVE, _sw, 'select frame copy hook (scpin)'):
    out.append(_l)
for _l in to_patch_lines(SCAVE2, _sw2, 'select frame copy hook (scpout)'):
    out.append(_l)
assert SCAVE + 4 * len(_sw) <= 0x112B78, hex(SCAVE + 4 * len(_sw))
assert SCAVE2 + 4 * len(_sw2) <= 0x113040, hex(SCAVE2 + 4 * len(_sw2))
_clash = {int(l.split('#')[0].split()[0], 16) for l in out if l.split('#')[0].split() and not l.startswith('#')}
for _a, _w, _c in _rs.remap_patches():
    assert _a not in _clash, hex(_a)
    w(_a, _w, _c)
w(0x24D528, 0x0C000000 | (_sl['scpin'] >> 2), 'SelectWrestlerFrame ctor: struct copy -> scpin')
w(0x24EA78, 0x0C000000 | (_sl['scpout'] >> 2), 'SelectWrestlerFrame::ChangeDecision: copy back -> scpout')
w(0x1321C8, 0x08000000 | (lab['cnl'] >> 2), 'WrestlerSelectEnd: j cnl (cancel on screen 2 -> screen 1)')
w(0x24E310, 0x0C000000 | (lab['pmask'] >> 2), 'ConvertPositionData: jal pmask (pad 6/7 mask, type 7/8)')
# pad label strings: s_wresCtrlStrID relocated with 9 entries (1P..6P, COM, 7P = id 830, 8P = id 831)
STRTBL = 0x112C70
for _i, _v in enumerate((96, 97, 98, 99, 100, 101, 102, 830, 831)):
    w(STRTBL + 4 * _i, _v, 'wresCtrlStrID' if _i == 0 else '')
w(0x288628, 0x3C030011, 'DrawChara: lui v1,0x11 (new wresCtrlStrID)')
w(0x28862C, 0x24630000 | (STRTBL & 0xFFFF), 'DrawChara: addiu v1,v1,low(new wresCtrlStrID)')

# ---------------- stage 2: entry loops 6 -> 8 in SelectWrestlerFrame (behaviour unchanged while entries 6,7 are inactive) ----------------
_cinit_src = """
cinit:  sw s3,0x68(sp)
        sw s3,0x6c(sp)
        jr ra
        daddu v0,zero,zero
"""
CINIT = SCAVE2 + 4 * len(_sw2)
_cw, _cl = assemble(CINIT, _cinit_src)
for _l in to_patch_lines(CINIT, _cw, 'ConvertPositionData: init entries 6,7 of pad array to -1'):
    out.append(_l)
assert CINIT + 4 * len(_cw) <= 0x113040, hex(CINIT + 4 * len(_cw))
w(0x24E0D0, 0x0C000000 | (_cl['cinit'] >> 2), 'ConvertPositionData: jal cinit')
# frame ctor: the per-panel ctrl value (frame +0x226c array, from entry +8) must be 7/8 for pads 6/7 (label table index)
_cvt_src = """
cvt:    sltiu t0,v1,0x10
        bnez t0,cvn
        nop
        andi v1,v1,7
        addiu v1,v1,1
cvn:    jr ra
        sw v1,0x22d4(v0)
"""
CVT = CINIT + 4 * len(_cw)
_vw, _vl = assemble(CVT, _cvt_src)
for _l in to_patch_lines(CVT, _vw, 'SelectWrestlerFrame ctor: ctrl value 0x16/0x17 -> 7/8'):
    out.append(_l)
assert CVT + 4 * len(_vw) <= 0x113040, hex(CVT + 4 * len(_vw))
_old = [x for x in out if x.startswith('0024D690 w')]
assert _old and 'AC4322D4' in _old[0], _old
out.remove(_old[0])
w(0x24D690, 0x0C000000 | (_vl['cvt'] >> 2), 'SelectWrestlerFrame ctor: jal cvt (store ctrl value)')
w(0x24E0BC, 0x24050020, 'ConvertPositionData: clear 8 entries')
w(0x24DD3C, 0x24020020, 'MakeOnes: clear 8 entries')
import struct as _s2
_ELF = open(ELF_PATH, 'rb').read()
def _wd(a):
    o = a - 0x100000 + 0x80
    return _s2.unpack('<I', _ELF[o:o + 4])[0]
for _a in (0x24D5AC, 0x24D698, 0x24DA80, 0x24DF74, 0x24E048, 0x24E1B8, 0x24E24C, 0x24E25C, 0x24E2F4, 0x24E304,
           0x24E3EC, 0x24E500, 0x24E708, 0x24E7E8, 0x24E854, 0x24EA64, 0x24EBA4, 0x24EF10, 0x24F088, 0x24F1B8,
           0x24F434, 0x24F500, 0x24F580, 0x24F5D4, 0x24F9BC):
    _o = _wd(_a)
    assert _o >> 26 == 0x0A and (_o & 0xFFFF) == 6, hex(_a)
    w(_a, (_o & 0xFFFF0000) | 8, 'select frame loop 6 -> 8')
w(0x24F20C, 0x24060007, 'NextSearch: reverse loop start 5 -> 7')
w(0x24F324, 0x24020007, 'ReverseSearch: loop start 5 -> 7')

# ---------------- LADDER list: restore TRIPLE THREAT TORNADO TAG (record 49) and add 4 PLAYER ROYAL BATTLE (record 85) ----------------
# record 85 (unused TIME LIMIT record at the end of s_GameTypeTbl) = copy of record 49 with max players 8 and title string id 832
_ELF2 = open(ELF_PATH, 'rb').read()
_o49 = 0x45AF60 + 49 * 32 - 0x100000 + 0x80
_rec = bytearray(_ELF2[_o49:_o49 + 32])
_rec[1] = 8
_rec[8:12] = (832).to_bytes(4, 'little')
out.append(f'0045BA00 {bytes(_rec).hex()}   # record 85 = 4 PLAYER ROYAL BATTLE (copy of record 49, max 8, title 832)')
# new item list for the LADDER sub-menu: 5 original items + (20, 85, 832); the descriptor at 0x45AE38 points to it
LITEMS = 0x113498
for _i, _t in enumerate(((20, 47, 8), (20, 48, 21), (20, 49, 29), (20, 50, 30), (20, 51, 31), (20, 85, 832))):
    for _j, _v in enumerate(_t):
        w(LITEMS + 12 * _i + 4 * _j, _v, 'LADDER item list' if (_i, _j) == (0, 0) else '')
# the per-record rule data (referee flag, ladder / belt setup ...) is read from the 64-byte rule table at 0x455DC0 indexed by the
# RECORD number (GetDefRule 0x12CC90 is called with seq+0x140 = record): entry 85 = copy of entry 49 with its own id byte
_e49 = bytearray(_ELF2[0x455DC0 + 49 * 64 - 0x100000 + 0x80:0x455DC0 + 50 * 64 - 0x100000 + 0x80])
_e49[0] = 85
out.append(f'{0x455DC0 + 85 * 64:08X} {bytes(_e49).hex()}   # rule table entry 85 = copy of entry 49 (4 PLAYER ROYAL BATTLE)')
# SURVIVAL list: add 8-MAN BATTLE ROYAL after 6-MAN BATTLE ROYAL (record 27) using the unused record 72:
# record 72 = copy of record 27 (group 7, pos 0x13, flags) with max players 8 and title string id 833; rule entry 72 = copy of entry 27
_o27 = 0x45AF60 + 27 * 32 - 0x100000 + 0x80
_rec2 = bytearray(_ELF2[_o27:_o27 + 32])
_rec2[1] = 8
_rec2[8:12] = (833).to_bytes(4, 'little')
out.append(f'{0x45AF60 + 72 * 32:08X} {bytes(_rec2).hex()}   # record 72 = 8-MAN BATTLE ROYAL (copy of record 27, max 8, title 833)')
_e27 = bytearray(_ELF2[0x455DC0 + 27 * 64 - 0x100000 + 0x80:0x455DC0 + 28 * 64 - 0x100000 + 0x80])
_e27[0] = 72
out.append(f'{0x455DC0 + 72 * 64:08X} {bytes(_e27).hex()}   # rule table entry 72 = copy of entry 27')
SITEMS = 0x113520
for _i, _t in enumerate(((20, 23, 30), (20, 24, 31), (20, 25, 33), (20, 26, 34), (20, 27, 35), (20, 72, 833))):
    for _j, _v in enumerate(_t):
        w(SITEMS + 12 * _i + 4 * _j, _v, 'SURVIVAL item list' if (_i, _j) == (0, 0) else '')
w(0x45ADD4, SITEMS, 'SURVIVAL menu descriptor: item list pointer')
w(0x45ADD8, 6, 'SURVIVAL menu descriptor: item count 5 -> 6')
# team tables for the 8-player flow: index = BRF*16 (mode 0 = LADDER teams of two, mode 1 = battle royal)
w(BRF, 0, 'BRF flag')
for _tab, _vals in ((FTAB, ((0, 1, 0, 1), (0, 2, 1, 3))), (RT1, ((0, 1, 0, 1), (0, 1, 2, 3))), (RT2, ((2, 2, 3, 3), (4, 5, 6, 7)))):
    for _m in range(2):
        for _k in range(4):
            w(_tab + 16 * _m + 4 * _k, _vals[_m][_k], 'team table' if (_m, _k) == (0, 0) else '')
w(0x45AE38, LITEMS, 'LADDER menu descriptor: item list pointer')
w(0x45AE3C, 6, 'LADDER menu descriptor: item count 5 -> 6')

# player-count list (GeneralSelectMenu ctor 0x133BC0): the row pitch is 32 px; with 9 rows (8 PLAYERS + ALL COM) the last row
# runs into the bottom bar, so for 8+ rows use a 24 px pitch (the 9th row then ends where the 7th row of the original list did)
PITCH = 0x1135D0
_psrc = """
pitch:  slti t0,s3,8
        lui v0,0x4200
        bnez t0,pd
        nop
        lui v0,0x41c0
pd:     jr ra
        nop
"""
_pw, _pl = assemble(PITCH, _psrc)
for _l in to_patch_lines(PITCH, _pw, 'player-count list row pitch (24 px for 8+ rows)'):
    out.append(_l)
w(0x133C40, 0x0C000000 | (_pl['pitch'] >> 2), 'GeneralSelectMenu ctor: jal pitch (replaces lui v0,0x4200)')

import asm as _asm
for _a, _b in sorted(_asm.CODE_RANGES):
    out.append(f'#@code {_a:08X} {_b:08X}')
open(PATCH_OUT, 'w').write('\n'.join(out).rstrip('\n') + '\n')
print('lines', len(out))
