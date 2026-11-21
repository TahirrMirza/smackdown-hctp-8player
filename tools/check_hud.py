"""Execute generated HUD helpers with hostile caller-saved register clobbers.

This small R5900-subset harness checks pointer/counter survival, independent
names, native backing geometry, bar progress, and renderer-offset restoration.
It is not a substitute for rendering the build in PCSX2.
Usage: python3 tools/check_hud.py original.elf patch.txt
"""
import math
import struct
import sys


def signed(v, bits=32):
    v &= (1 << bits) - 1
    return v - (1 << bits) if v >> (bits - 1) else v


def fbits(v):
    return struct.unpack('<I', struct.pack('<f', v))[0]


def asfloat(v):
    return struct.unpack('<f', struct.pack('<I', v & 0xffffffff))[0]


class Machine:
    def __init__(self, words):
        self.mem = {}
        self.words = words
        self.r, self.f = [0] * 32, [0] * 32
        self.r[29] = 0x1ff0000
        self.lo = 0
        self.draws, self.text, self.uv = [], {}, []
        self.hooks = {}

    def put(self, a, v, size=4):
        for i in range(size):
            self.mem[(a + i) & 0xffffffff] = (v >> (8 * i)) & 255

    def get(self, a, size=4):
        a &= 0xffffffff
        assert a >= 0x100000, f'invalid memory read {a:#x}'
        return sum(self.mem.get(a + i, (self.words.get((a + i) & ~3, 0)
                                       >> (((a + i) & 3) * 8)) & 255) << (8 * i)
                   for i in range(size))

    def fp(self, a, v):
        self.put(a, fbits(v))

    def fl(self, a):
        return asfloat(self.get(a))

    def clobber(self):
        for r in (*range(4, 16), 24, 25):
            self.r[r] = 5

    def native(self, pc):
        a0, a1, a2, a3 = self.r[4:8]
        ret = 0
        if pc in self.hooks:
            ret = self.hooks[pc](self)
        elif pc == 0x12cf30:
            ret = 0x1900000 + a0 * 32
            self.text[ret] = 'A' * (30 if a0 == 800 else 8)
        elif pc == 0x12fd60:
            ret = 0x1950000 + a0 * 32
            self.text[ret] = str(a0)
        elif pc == 0x162250:
            ret = int(len(self.text[self.get(a0 + 0x160)]) * 10 * self.fl(a0 + 0x10))
        elif pc in (0x14b090, 0x14b200, 0x14aee0):
            x, y = map(asfloat, self.f[12:14])
            if a0 & 0xffff == 0xdead:
                raise AssertionError('bad draw object')
            is_font = self.get(a0 + 0xb0) == 0x1801000
            width = (len(self.text[self.get(a0 + 0x160)]) * 10 * self.fl(a0 + 0x10)
                     if is_font else self.fl(a0 + 0xa0) * self.fl(a0 + 0x10))
            height = 18 * self.fl(a0 + 0x14) if is_font else self.fl(a0 + 0xa4) * self.fl(a0 + 0x14)
            if pc == 0x14b090:
                x, y = x + width / 2, y + height / 2
            elif pc == 0x14b200:
                x, y = x - width / 2, y + height / 2
            self.fp(a0, x)
            self.fp(a0 + 4, y)
            self.fp(a0 + 0xc0, (x - width / 2) * 16)
            self.fp(a0 + 0xd0, (x + width / 2) * 16)
        elif pc == 0x15ee00:
            self.uv.append((a0, a1, a2, a3, self.r[8]))
        elif pc in (0x15f450, 0x162780):
            self.draws.append((a0, pc, self.get(a0 + 0x100, 8)))
        elif pc == 0x13c640:
            ret = 0  # No CHHP link: damage helper must safely return.
        else:
            raise AssertionError(f'unexpected native call {pc:#x}')
        self.clobber()
        self.r[2] = ret
        return self.r[31]

    def run(self, pc, *args):
        self.r[31] = 0xffffffff
        for i, a in enumerate(args):
            self.r[4 + i] = a
        pending = None
        for _ in range(25000):
            if pc == 0xffffffff:
                return
            if pc in self.hooks or pc in (0x12cf30, 0x12fd60, 0x162250, 0x14b090, 0x14b200,
                      0x14aee0, 0x15ee00, 0x15f450, 0x162780, 0x13c640):
                assert pending is None
                pc = self.native(pc)
                continue
            w = self.get(pc)
            op, rs, rt, rd, sa = w >> 26, w >> 21 & 31, w >> 16 & 31, w >> 11 & 31, w >> 6 & 31
            imm, fn = signed(w & 65535, 16), w & 63
            target, after = None, pending
            pending = None
            addr = (self.r[rs] + imm) & 0xffffffff
            if not w:
                pass
            elif op == 0:
                if fn == 0: self.r[rd] = self.r[rt] << sa & 0xffffffff
                elif fn == 2: self.r[rd] = (self.r[rt] & 0xffffffff) >> sa
                elif fn == 3: self.r[rd] = signed(self.r[rt]) >> sa
                elif fn in (0x21, 0x2d): self.r[rd] = (self.r[rs] + self.r[rt]) & 0xffffffffffffffff
                elif fn == 0x23: self.r[rd] = (self.r[rs] - self.r[rt]) & 0xffffffffffffffff
                elif fn == 0x25: self.r[rd] = self.r[rs] | self.r[rt]
                elif fn == 0x2a: self.r[rd] = int(signed(self.r[rs]) < signed(self.r[rt]))
                elif fn == 0x2b: self.r[rd] = int((self.r[rs] & 0xffffffff) < (self.r[rt] & 0xffffffff))
                elif fn == 0x12: self.r[rd] = self.lo
                elif fn == 0x1a: self.lo = int(signed(self.r[rs]) / signed(self.r[rt]))
                elif fn in (8, 9):
                    target = self.r[rs]
                    if fn == 9: self.r[rd] = pc + 8
                else: raise AssertionError((hex(pc), hex(w)))
            elif op in (2, 3):
                target = (w & 0x3ffffff) << 2
                if op == 3: self.r[31] = pc + 8
            elif op in (4, 5):
                eq = self.r[rs] == self.r[rt]
                target = pc + 4 + imm * 4 if eq == (op == 4) else pc + 8
            elif op == 9: self.r[rt] = self.r[rs] + imm & 0xffffffffffffffff
            elif op == 10: self.r[rt] = int(signed(self.r[rs]) < imm)
            elif op == 11: self.r[rt] = int((self.r[rs] & 0xffffffff) < (imm & 0xffffffff))
            elif op == 12: self.r[rt] = self.r[rs] & (w & 65535)
            elif op == 13: self.r[rt] = self.r[rs] | (w & 65535)
            elif op == 15: self.r[rt] = (w & 65535) << 16
            elif op in (0x20, 0x23, 0x24, 0x25, 0x37):
                size = {0x20: 1, 0x23: 4, 0x24: 1, 0x25: 2, 0x37: 8}[op]
                self.r[rt] = self.get(addr, size)
                if op == 0x20: self.r[rt] = signed(self.r[rt], 8)
            elif op in (0x2b, 0x3f): self.put(addr, self.r[rt], 4 if op == 0x2b else 8)
            elif op == 0x31: self.f[rt] = self.get(addr)
            elif op == 0x39: self.put(addr, self.f[rt])
            elif op == 0x11:
                fs, ft, fd = rd, rt, sa
                if rs == 4: self.f[fs] = self.r[rt] & 0xffffffff
                elif rs == 20 and fn == 32: self.f[fd] = fbits(float(signed(self.f[fs])))
                elif rs == 16:
                    x, y = asfloat(self.f[fs]), asfloat(self.f[ft])
                    value = {0: lambda: x + y, 2: lambda: x * y, 3: lambda: x / y}[fn]()
                    self.f[fd] = fbits(value)
                else: raise AssertionError((hex(pc), hex(w)))
            else: raise AssertionError((hex(pc), hex(w)))
            self.r[0] = 0
            if after is not None:
                assert target is None, f'branch in delay slot at {pc:#x}'
                pc = after
            else:
                pc, pending = pc + 4, target
        raise AssertionError('HUD helper did not terminate')


def main():
    original, patch = sys.argv[1:]
    data = open(original, 'rb').read()
    words = {0x100000 + off - 0x80: struct.unpack_from('<I', data, off)[0]
             for off in range(0x80, 0x389880, 4)}
    code = []
    for line in open(patch):
        if line.startswith('#@code'):
            _, a, b = line.split()
            code.append((int(a, 16), int(b, 16)))
        p = line.split('#')[0].split()
        if p:
            a = int(p[0], 16)
            bs = struct.pack('<I', int(p[2], 16)) if p[1] == 'w' else bytes.fromhex(''.join(p[1:]))
            for i in range(0, len(bs), 4):
                words[a + i] = int.from_bytes(bs[i:i + 4].ljust(4, b'\0'), 'little')
    for (a, b), (c, d) in zip(sorted(code), sorted(code)[1:]):
        assert b <= c, f'code-cave overlap {a:#x}..{b:#x}, {c:#x}..{d:#x}'
    assert words[0x15f7bc] == 0x27bd0030  # original sprite stack-pop delay slot
    assert words[0x15e808] == 0x27bd0010  # original rect stack-pop delay slot
    assert words[0x15e7f4] == 0x8c980084 and words[0x15e7f8] == 0xac780018
    m = Machine(words)
    hud, ctrl, block = 0x1600000, 0x1600050, 0x1400000
    m.put(0x529300, hud)
    allocations = []

    def allocate(machine):
        allocations.append(machine.r[4])
        return block

    m.hooks.update({0x1001e0: allocate, 0x3f22b0: lambda _: 0})
    for side in range(2):
        for j in range(64):
            m.put(ctrl + 0x16a0 + side * 0x100 + j * 4, side + 7)
        for offset, count in ((0xc08, 1), (0xc20, 1), (0xc38, 1),
                              (0xc50, 1), (0x44f0, 1),
                              (0xc80, 5), (0xd34, 6)):
            stride = 20 if offset == 0xc80 else 24 if offset == 0xd34 else 4
            for k in range(count):
                source = 0x1800000 + side * 0x10000 + offset * 16 + k * 0x200
                m.put(ctrl + offset + side * stride + k * 4, source)
                for j in range(92):
                    m.put(source + j * 4, side + 7)
    m.run(0x3b8288, ctrl)
    assert allocations == [0x2800], allocations
    assert m.r[2] == block
    for side in range(2):
        for off in (0, 0x100, 0x210, 0x320, 0x490, 0x9e0, 0x1040, 0x11b0, 0x12c0):
            assert m.get(block + side * 0x1400 + off) == side + 7, (side, off)
    # Rematch: tear down, invalidate the freed block, and recreate the HUD at
    # exactly the same address with fresh source draw objects/resources.
    cleanup_entry = (words[0x233dbc] & 0x3ffffff) << 2
    released, resets, retail = [], [], []
    m.hooks.update({0x100200: lambda machine: released.append(machine.r[4]) or 0,
                    0x3f22b0: lambda _: resets.append(True) or 0,
                    0x2358d0: lambda machine: retail.append(machine.r[4]) or 0})
    m.put(0x3b5fcc, 0x1900000)
    m.put(0x3b5fe4, 12345)
    m.put(0x3b5ff4, 0x1ff0000)
    m.run(cleanup_entry, ctrl)
    assert released == [block] and resets == [True] and retail == [ctrl]
    assert all(m.get(a) == 0 for a in range(0x3b5fc0, 0x3b6000, 4))
    for side in range(2):
        for j in range(64):
            m.put(ctrl + 0x16a0 + side * 0x100 + j * 4, side + 17)
        for offset, count in ((0xc08, 1), (0xc20, 1), (0xc38, 1),
                              (0xc50, 1), (0x44f0, 1), (0xc80, 5), (0xd34, 6)):
            stride = 20 if offset == 0xc80 else 24 if offset == 0xd34 else 4
            for k in range(count):
                source = m.get(ctrl + offset + side * stride + k * 4)
                for j in range(92): m.put(source + j * 4, side + 17)
    for off in range(0, 0x2800, 4): m.put(block + off, 0)
    m.run(0x3b8288, ctrl)
    assert allocations == [0x2800, 0x2800], allocations
    assert m.get(0x3b5fc4) == hud
    for side in range(2):
        for off in (0, 0x100, 0x210, 0x320, 0x490, 0x9e0, 0x1040, 0x11b0, 0x12c0):
            assert m.get(block + side * 0x1400 + off) == side + 17, (side, off)
    # Repeated teardown after state was cleared must not free the block twice.
    m.run(cleanup_entry, ctrl)
    m.run(cleanup_entry, ctrl)
    assert released == [block, block]
    assert retail == [ctrl, ctrl, ctrl]
    # Locate the card entry by its unique stack prologue after the show thunk.
    card_entry = 0x121548
    for slot in (6, 7):
        for current, maximum in ((0, 0), (0, 5), (1, 5), (3, 5), (5, 5), (1, 9)):
            m = Machine(words)
            card, char, hud, tex = 0x1400000, 0x1500000, 0x1600000, 0x1700000
            m.put(0x526ea0 + slot * 4, char)
            m.put(0x529300, hud)
            m.put(hud + 0x460c, tex)
            m.put(tex + 0x10, 0x1234567887654321, 8)
            m.put(tex + 0x30, 0x8765432112345678, 8)
            rec = 0x4921c0 + slot * 32
            m.put(rec, slot, 1)
            m.put(rec + 0xa, 800 if slot == 6 else 801, 2)
            m.put(char + 0x2ac, current)
            m.put(char + 0x2b0, maximum)
            m.put(char + 0x2b4, 50)
            for off in (0, 0x100, 0x210, *range(0x490, 0x9e0, 0x110),
                        *range(0x9e0, 0x1040, 0x110), 0x11b0, 0x12c0):
                m.put(card + off + 0xb0, 0x1800000)
                m.fp(card + off + 0x10, -1.69 if slot == 7 else 1.69)
                m.fp(card + off + 0x14, 1.0)
                m.fp(card + off + 0xa4, 19.0)
                m.fp(card + off + 0xc0, 7712 if slot == 7 else 416)
            m.fp(card + 0x10, 1.0)
            for off in (0x320, 0x1040):
                m.put(card + off + 0xb0, 0x1801000)
                m.fp(card + off + 0x10, 1.0)
                m.fp(card + off + 0x14, 1.0)
            m.put(0x1800038, 0x15f450)
            m.run(card_entry, card, slot)
            pips = [d for d in m.draws if card + 0x490 <= d[0] < card + 0x9e0]
            parts = [d for d in m.draws if card + 0x9e0 <= d[0] < card + 0x1040]
            assert [d[0] for d in parts] == [card + 0xaf0 + i * 0x110 for i in range(5)]
            assert len(pips) == min(max(current, maximum), 5), (slot, current, maximum, pips)
            for i, (_, _, texvalue) in enumerate(pips):
                assert texvalue == (0x1234567887654321 if i < current else 0x8765432112345678)
            assert m.get(card + 0x11a0) == 0x1950000 + (830 + slot - 6) * 32
            assert math.isclose(m.fl(card + 0xa0), 232 if slot == 6 else 124), m.fl(card + 0xa0)
            assert [u[3] for u in m.uv] == [46, 46], m.uv
            expected = m.fl(card + 0x11b0 + 0xc0) + 46 * (-1.69 if slot == 7 else 1.69) * 16
            assert math.isclose(m.fl(card + 0x11b0 + 0xd0), expected, abs_tol=0.001)
    # The renderer bias must follow field/frame mode, affect both private
    # cards equally, and restore the exact incoming renderer value.
    for interlace, frame, expected in ((0, 0, 1024), (1, 0, 512), (1, 1, 1024)):
        m = Machine(words)
        render, hud, block = 0x1700000, 0x1600000, 0x1400000
        ctrl = hud + 0x50
        m.put(0x524eb0, render)
        m.put(0x529300, hud)
        m.put(0x110794, 1)
        m.put(ctrl + 0x34, 1, 1)
        m.put(render + 0x10620, 28672)
        m.put(render + 0x10588, interlace)
        m.put(render + 0x10, frame)
        draws = []

        def draw_card(machine):
            draws.append((machine.r[4], machine.r[5], machine.get(render + 0x10620)))
            return 0

        m.hooks.update({0x23dc90: lambda _: 0, 0x10bea0: lambda _: 0,
                        0x3b8288: lambda _: block, 0x3f22b0: lambda _: 0,
                        card_entry: draw_card})
        m.run(words[0x47f05c], ctrl + 0x20)
        assert draws == [(block, 6, 28672 + expected), (block + 0x1400, 7, 28672 + expected)], draws
        assert m.get(render + 0x10620) == 28672
        assert m.get(0x3b5fc8) == 0

    # Run the exact emitted-packet helpers for every retail card, private
    # sprites, font glyphs, and inline name rectangles in both field modes.
    for field in (False, True):
        for kind in ('sprite', 'rect'):
            for source in ('private', 'native', 'font', 'inline', 'temporary', 'unrelated', 'disabled'):
                for side in range(2):
                    for row in range(4):
                        m = Machine(words)
                        originx, originy = 28672, 28672
                        height = 3584 if field else 7168
                        hud, render, block, packet = 0x1600000, 0x1700000, 0x1400000, 0x21900000
                        ctrl = hud + 0x50
                        m.put(0x529300, hud)
                        m.put(0x524eb0, render)
                        m.put(render + 0x10568, packet & 0x1fffffff)
                        m.put(0x3b5fc0, block)
                        m.put(0x3b5fc8, 0 if source == 'disabled' else 1)
                        m.put(0x3b5fe8, originy)
                        m.put(0x3b5fec, originx)
                        m.put(0x3b5ff0, height)
                        obj = block + 0x1400 * side + 0x320
                        if source == 'native':
                            obj = 0x1800000
                            m.put(ctrl + 0xd34 + (row % 3 * 2 + side) * 24, obj)
                        elif source == 'font':
                            obj = 0x1801000
                            m.put(ctrl + 0x44f0 + (row % 3 * 2 + side) * 4, obj)
                        elif source == 'inline':
                            obj = ctrl + 0x16a0 + (row % 3 * 2 + side) * 0x100
                        elif source == 'unrelated':
                            obj = 0x1802000
                        elif source == 'temporary':
                            obj = 0x1fee000
                            m.put(0x3b5ff4, obj)
                        offset, stride = (0xb0, 0x20) if kind == 'sprite' else (0x80, 0x10)
                        x0, x1 = ((10, 80) if not side else (482, 412))
                        y0 = (20, 84, 344, 370)[row]
                        points = [(originx + x * 16, originy + int(y * (8 if field else 16)))
                                  for x, y in ((x0, y0), (x1, y0 + 32))]
                        for i, (x, y) in enumerate(points):
                            m.put(packet + offset + stride * i, x)
                            m.put(packet + offset + stride * i + 4, y)
                            m.put(packet + offset + stride * i + 8, 0xABCDEF)
                        entry = (words[0x15f7b8 if kind == 'sprite' else 0x15e804] & 0x3ffffff) << 2
                        m.run(entry, obj)
                        for i, (x, y) in enumerate(points):
                            if source not in ('unrelated', 'disabled'):
                                ax = originx + (8192 if side else 0)
                                ay = originy + (height if row >= 2 else 0)
                                x, y = ax + (x - ax) * 3 // 4, ay + (y - ay) * 3 // 4
                            assert m.get(packet + offset + stride * i) == x
                            assert m.get(packet + offset + stride * i + 4) == y
                            assert m.get(packet + offset + stride * i + 8) == 0xABCDEF
    # Retail ID sprites lack 7P/8P atlas cells. Verify only human pad 7/8
    # labels become text, without changing the controller/COM records.
    label_entry = (words[0x23d114] & 0x3ffffff) << 2
    for slot in range(6):
        for pad, com, has_font in ((22, 0, True), (23, 0, True), (22, 1, True),
                                   (0, 0, True), (22, 0, False)):
            m = Machine(words)
            ctrl, sprite, font = 0x1400000, 0x1500000, 0x1600000
            m.r[19], m.r[20], m.r[18], m.r[25] = slot, ctrl, slot * 4, 0x15f450
            m.put(0x4921c0 + slot * 32, pad, 1)
            m.put(0x4921c8 + slot * 32, com, 1)
            m.put(ctrl + 0x44f0 + slot * 4, font if has_font else 0)
            m.put(font + 0xb0, 0x1801000)
            m.fp(font + 0x10, 1)
            m.fp(font + 0x14, 1)
            m.fp(sprite, 70 if slot % 2 == 0 else 442)
            m.fp(sprite + 4, (46, 338, 394)[slot // 2])
            for i in range(4): m.put(sprite + 0x30 + i * 4, 255)
            calls = []

            def text(machine):
                obj = machine.r[4]
                assert machine.get(0x3b5ff4) == obj
                calls.append(('text', machine.get(obj + 0x160), machine.fl(obj), machine.fl(obj + 4)))
                return 0

            m.hooks.update({0x162780: text,
                            0x15f450: lambda machine: calls.append(('sprite', machine.r[4])) or 0})
            m.run(label_entry, sprite)
            if pad in (22, 23) and not com and has_font:
                assert calls[0][0:2] == ('text', 0x1950000 + (830 + pad - 22) * 32)
                assert calls[0][2:] == (70 if slot % 2 == 0 else 442, (46, 338, 394)[slot // 2])
            else:
                assert calls == [('sprite', sprite)]
            assert m.get(0x4921c0 + slot * 32, 1) == pad
            assert m.get(0x4921c8 + slot * 32, 1) == com
            assert m.get(0x3b5ff4) == 0
            assert m.r[18] == slot * 4
    print('OK: rematch teardown/address reuse, repeat cleanup, HUD labels/COM fallback, damage/finishers, 75% scaling, renderer state, and cave separation')


if __name__ == '__main__':
    main()
