"""Tiny MIPS (R5900 subset) assembler for cave code.
usage as module: words = assemble(origin, text) -> list of 32-bit ints
Supports labels (name:), comments (# or ;), .word N, and ops:
 nop move li la lui ori addiu addu subu and or andi slt slti sltu sltiu sll srl sra
 lw lh lhu lb lbu sw sh sb  beq bne beqz bnez b j jal jr jalr
Operands: registers by name ($ optional), numbers dec/hex, labels (branch/jump/la), imm(reg).
"""
import re

REG = ['zero', 'at', 'v0', 'v1', 'a0', 'a1', 'a2', 'a3', 't0', 't1', 't2', 't3', 't4', 't5', 't6', 't7',
       's0', 's1', 's2', 's3', 's4', 's5', 's6', 's7', 't8', 't9', 'k0', 'k1', 'gp', 'sp', 'fp', 'ra']
R = {n: i for i, n in enumerate(REG)}
R['s8'] = 30


def reg(s):
    s = s.strip().lstrip('$')
    if s in R:
        return R[s]
    raise ValueError('bad reg ' + s)


def num(s, labels=None):
    s = s.strip()
    if labels and s in labels:
        return labels[s]
    return int(s, 0)


MEM = re.compile(r'^(.*)\((\$?\w+)\)$')

ITYPE = {'addiu': 0x09, 'slti': 0x0A, 'sltiu': 0x0B, 'andi': 0x0C, 'ori': 0x0D, 'xori': 0x0E}
LOADST = {'lb': 0x20, 'lh': 0x21, 'lw': 0x23, 'lbu': 0x24, 'lhu': 0x25, 'sb': 0x28, 'sh': 0x29, 'sw': 0x2B, 'ld': 0x37, 'sd': 0x3F}
RTYPE = {'addu': 0x21, 'subu': 0x23, 'and': 0x24, 'or': 0x25, 'xor': 0x26, 'nor': 0x27, 'slt': 0x2A, 'sltu': 0x2B, 'daddu': 0x2D}


def size_of(op, args):
    if op in ('li', 'la'):
        return 2
    return 1


def assemble(origin, text):
    lines = []
    for l in text.split('\n'):
        l = re.split(r'[#;]', l)[0].strip()
        if l:
            lines.append(l)
    # pass 1: labels
    labels = {}
    pc = origin
    items = []
    for l in lines:
        while True:
            m = re.match(r'^(\w+):\s*(.*)$', l)
            if not m:
                break
            labels[m.group(1)] = pc
            l = m.group(2)
        if not l:
            continue
        parts = l.split(None, 1)
        op = parts[0].lower()
        args = [a.strip() for a in parts[1].split(',')] if len(parts) > 1 else []
        items.append((pc, op, args))
        pc += 4 * size_of(op, args)
    out = []
    for pc, op, a in items:
        def br(t):
            tgt = num(t, labels)
            off = (tgt - (pc + 4)) >> 2
            assert -0x8000 <= off < 0x8000, (op, a)
            return off & 0xFFFF
        if op == 'nop':
            out.append(0)
        elif op == 'move':
            out.append((reg(a[1]) << 21) | (0 << 16) | (reg(a[0]) << 11) | 0x2D)  # daddu rd,rs,zero
        elif op == 'li':
            v = num(a[1], labels) & 0xFFFFFFFF
            rt = reg(a[0])
            out.append(0x3C000000 | (rt << 16) | (v >> 16))
            out.append(0x34000000 | (rt << 21) | (rt << 16) | (v & 0xFFFF))
        elif op == 'la':
            v = num(a[1], labels) & 0xFFFFFFFF
            rt = reg(a[0])
            out.append(0x3C000000 | (rt << 16) | (v >> 16))
            out.append(0x34000000 | (rt << 21) | (rt << 16) | (v & 0xFFFF))
        elif op == 'lui':
            out.append(0x3C000000 | (reg(a[0]) << 16) | (num(a[1], labels) & 0xFFFF))
        elif op in ITYPE:
            out.append((ITYPE[op] << 26) | (reg(a[1]) << 21) | (reg(a[0]) << 16) | (num(a[2], labels) & 0xFFFF))
        elif op in LOADST:
            m = MEM.match(a[1])
            off = num(m.group(1) or '0', labels)
            out.append((LOADST[op] << 26) | (reg(m.group(2)) << 21) | (reg(a[0]) << 16) | (off & 0xFFFF))
        elif op in RTYPE:
            out.append((reg(a[1]) << 21) | (reg(a[2]) << 16) | (reg(a[0]) << 11) | RTYPE[op])
        elif op in ('sll', 'srl', 'sra'):
            f = {'sll': 0, 'srl': 2, 'sra': 3}[op]
            out.append((reg(a[1]) << 16) | (reg(a[0]) << 11) | ((num(a[2]) & 31) << 6) | f)
        elif op == 'beq':
            out.append(0x10000000 | (reg(a[0]) << 21) | (reg(a[1]) << 16) | br(a[2]))
        elif op == 'bne':
            out.append(0x14000000 | (reg(a[0]) << 21) | (reg(a[1]) << 16) | br(a[2]))
        elif op == 'beqz':
            out.append(0x10000000 | (reg(a[0]) << 21) | br(a[1]))
        elif op == 'bnez':
            out.append(0x14000000 | (reg(a[0]) << 21) | br(a[1]))
        elif op == 'b':
            out.append(0x10000000 | br(a[0]))
        elif op == 'j':
            out.append(0x08000000 | ((num(a[0], labels) >> 2) & 0x3FFFFFF))
        elif op == 'jal':
            out.append(0x0C000000 | ((num(a[0], labels) >> 2) & 0x3FFFFFF))
        elif op == 'jr':
            out.append((reg(a[0]) << 21) | 0x08)
        elif op == 'jalr':
            out.append((reg(a[0]) << 21) | (31 << 11) | 0x09)
        elif op == '.word':
            out.append(num(a[0], labels) & 0xFFFFFFFF)
        else:
            raise ValueError('unknown op ' + op)
    return out, labels


CODE_RANGES = []   # (start, end) of every block turned into patch lines; written out as '#@code' markers for check_patch.py


def to_patch_lines(origin, words, comment=''):
    CODE_RANGES.append((origin, origin + 4 * len(words)))
    return [f'{origin + 4 * i:08X} w {w:08X}' + (f'   # {comment}' if comment and i == 0 else '') for i, w in enumerate(words)]


if __name__ == '__main__':
    import sys
    w, lab = assemble(int(sys.argv[1], 16), open(sys.argv[2]).read())
    for i, x in enumerate(w):
        print(f'{int(sys.argv[1], 16) + 4 * i:08x}: {x:08X}')
