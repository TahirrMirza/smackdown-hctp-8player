#!/usr/bin/env python3
"""Static sanity checks for a generated patch list (no emulator needed).

    python3 build.py --elf SLUS_207.87 --out /dev/null --keep-patch patch.txt
    python3 tools/check_patch.py SLUS_207.87 patch.txt

Checks:
  1. every entry lies inside the loaded part of the executable, words are 4-byte aligned
  2. no entry overwrites a library function that is still called (the patch uses unreferenced library functions as code caves)
  3. in every '#@code' block: each branch/jump has a delay slot that is not itself a branch, branch targets stay in the block,
     jump targets stay in the block or inside the executable's text
  4. no entry below 0x100000 (no use of low RAM)
"""
import struct
import sys

LOAD_VA, LOAD_OFF, LOAD_SIZE = 0x100000, 0x80, 0x389800
LIB_LO, LIB_HI = 0x110000, 0x114000          # the sce* library block that holds the caves
SYM_OFF, SYM_SIZE, STR_OFF = 0x412D10, 0x5F9B0, 0x389950


def main(elf_path, patch_path):
    d = open(elf_path, "rb").read()
    problems = []

    funcs = []
    for i in range(SYM_SIZE // 16):
        n, v, sz, info, _o, _s = struct.unpack_from("<IIIBBH", d, SYM_OFF + 16 * i)
        if info & 15 == 2 and LIB_LO <= v < LIB_HI:
            nm = d[STR_OFF + n:d.index(b"\0", STR_OFF + n)].decode("latin1")
            funcs.append((v, max(sz, 4), nm))
    funcs.sort()

    def fn(va):
        for a, s, nm in funcs:
            if a <= va < a + s:
                return a, s, nm
        return None

    # live library functions = reachable by jal/j from outside the block (transitively through the block)
    word = lambda va: struct.unpack_from("<I", d, va - LOAD_VA + LOAD_OFF)[0]
    live, todo = set(), []
    for off in range(LOAD_OFF, LOAD_OFF + LOAD_SIZE, 4):
        va = off - LOAD_OFF + LOAD_VA
        if LIB_LO <= va < LIB_HI:
            continue
        w = struct.unpack_from("<I", d, off)[0]
        if w >> 26 in (2, 3):
            t = (w & 0x3FFFFFF) << 2
            f = fn(t)
            if f and f[0] == t:
                todo.append(t)
    while todo:
        a = todo.pop()
        if a in live:
            continue
        live.add(a)
        f = fn(a)
        for va in range(f[0], f[0] + f[1], 4):
            w = word(va)
            if w >> 26 in (2, 3):
                t = (w & 0x3FFFFFF) << 2
                g = fn(t)
                if g and g[0] == t and t not in live:
                    todo.append(t)

    entries, code = {}, []
    for line in open(patch_path):
        if line.startswith("#@code"):
            _, a, b = line.split()
            code.append((int(a, 16), int(b, 16)))
            continue
        t = line.split("#")[0].split()
        if not t:
            continue
        va = int(t[0], 16)
        if t[1] == "w":
            if va % 4:
                problems.append("unaligned word entry %08x" % va)
            data = struct.pack("<I", int(t[2], 16))
        else:
            data = bytes.fromhex("".join(t[1:]))
        off = va - LOAD_VA + LOAD_OFF
        if va < 0x100000:
            problems.append("entry below 0x100000: %08x" % va)
        if not (LOAD_OFF <= off and off + len(data) <= LOAD_OFF + LOAD_SIZE):
            problems.append("entry outside the loaded image: %08x" % va)
        for k in range(0, len(data), 4):
            entries[va + k] = int.from_bytes(data[k:k + 4].ljust(4, b"\0"), "little") if t[1] == "w" else None
            f = fn(va + k)
            if f and f[0] in live:
                problems.append("entry %08x overwrites live library function %s" % (va + k, f[2]))

    def isbr(w):
        op = w >> 26
        return op in (2, 3, 4, 5, 6, 7, 1, 0x14, 0x15, 0x16, 0x17) or (op == 0 and (w & 0x3F) in (8, 9))

    for a, b in code:
        for va in range(a, b, 4):
            w = entries.get(va)
            if w is None:
                problems.append("code block %08x-%08x has a hole at %08x" % (a, b, va))
                continue
            if isbr(w):
                nx = entries.get(va + 4)
                if va + 4 >= b or nx is None or isbr(nx):
                    problems.append("branch at %08x has no valid delay slot" % va)
                op = w >> 26
                if op in (4, 5, 6, 7, 1):
                    imm = w & 0xFFFF
                    imm -= 0x10000 if imm & 0x8000 else 0
                    t = va + 4 + imm * 4
                    if not any(x <= t < y for x, y in code):
                        problems.append("branch at %08x leaves the patched code (%08x)" % (va, t))
                if op in (2, 3):
                    t = (w & 0x3FFFFFF) << 2
                    if not (any(x <= t < y for x, y in code) or LOAD_VA <= t < LOAD_VA + LOAD_SIZE):
                        problems.append("jump at %08x goes to %08x (outside text)" % (va, t))

    print("entries: %d words, %d code blocks, %d live library functions found" % (len(entries), len(code), len(live)))
    if problems:
        print("PROBLEMS:")
        for p in problems:
            print("  " + p)
        sys.exit(1)
    print("OK")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
