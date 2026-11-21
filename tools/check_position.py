"""Check the eight-box position order, teams, navigation and background code.

Usage: python3 tools/check_position.py original.elf patch.txt
Executes the emitted background helpers using the same small MIPS harness as
check_hud.py; actual rendering still needs an emulator or console test.
"""
import struct
import sys
from check_hud import Machine, asfloat, fbits


def main():
    elf, patch = sys.argv[1:]
    data = bytearray(open(elf, 'rb').read())
    for line in open(patch):
        p = line.split('#')[0].split()
        if not p:
            continue
        addr = int(p[0], 16)
        bs = struct.pack('<I', int(p[2], 16)) if p[1] == 'w' else bytes.fromhex(''.join(p[1:]))
        off = addr - 0x100000 + 0x80
        data[off:off + len(bs)] = bs
    words = {0x100000 + off - 0x80: struct.unpack_from('<I', data, off)[0]
             for off in range(0x80, 0x389880, 4)}

    def at(addr, fmt):
        return struct.unpack_from(fmt, data, addr - 0x100000 + 0x80)

    layout = 0x45bd10 + 5 * 0xc4
    entries = [at(layout + i * 28, '<ffiiiii') for i in range(9)]
    slots = [0, 1, 2, 3, 4, 5, 7, 8]
    assert sorted(slots, key=lambda i: (entries[i][1], entries[i][0])) == slots
    for row, pair in enumerate(((0, 1), (2, 3), (4, 5), (7, 8))):
        l, r = pair
        assert entries[l][:2] == (142, 128 + 78 * row)
        assert entries[r][:2] == (498, 128 + 78 * row)
        assert entries[l][3] == ((2, 4, 7, 0)[row])
        assert entries[r][3] == ((3, 5, 8, 1)[row])
        assert entries[l][2] == ((7, 0, 2, 4)[row])
        assert entries[r][2] == ((8, 1, 3, 5)[row])
        if row:
            assert entries[l][4:] == (r, r, (2, 4, 9)[row - 1])
            assert entries[r][4:] == (l, l, (3, 5, 10)[row - 1])
    assert entries[6][:2] == (320, 128)
    popup = 0x112598 + 14 * 0x30
    assert at(popup + 5 * 8, '<ff') == (388, 260)
    assert at(popup + 7 * 8, '<ff') == (252, 276)
    teams = list(at(0x11358c, '<4I') + at(0x1135ac, '<4I'))
    assert teams == [0, 0, 1, 1, 2, 2, 3, 3], teams
    assert at(0x11359c, '<4I') + at(0x1135bc, '<4I') == tuple(range(8))
    rec = 0x45af60 + 85 * 32
    assert [at(rec + 0xd + i * 3, '<B')[0] for i in range(6)] == teams[:6]
    original = open(elf, 'rb').read()
    for recno in (27, 49):
        off = 0x45af60 + recno * 32 - 0x100000 + 0x80
        assert data[off:off + 32] == original[off:off + 32]

    # Confirm 7P/8P in every box through the actual popup wrapper, then copy
    # back to the sequence/side buffer and reopen the position screen.
    popup_entry = words[0x47b614]
    cpout = (words[0x139aa0] & 0x3ffffff) << 2
    cpin = (words[0x1395e4] & 0x3ffffff) << 2
    for pad_value in (7, 8):
        for slot in range(8):
            m = Machine(words)
            frame, popup, ui, vt = 0x1400000, 0x1500000, 0x1600000, 0x1700000
            values = [0, 1, 2, 3, 4, 5, 7, 8]
            m.put(frame + 0x240, 5)
            m.put(frame + 0x1a0, 8)
            m.put(frame + 0x1a4, 85)
            m.put(frame + 0x1ec, slot if slot < 6 else slot + 1)
            m.put(frame + 0x2c4, popup)
            m.put(frame + 0x1c4, ui)
            m.put(popup, vt)
            m.put(vt + 0x2c, 0x1900000)
            m.put(vt + 8, 0x1900100)
            m.put(popup + 0x17c, pad_value - 1)
            for i, value in enumerate(values):
                m.put(frame + 0x20 + i * 0x30, 1)
                m.put(frame + 0x24 + i * 0x30, value)
                m.put(frame + 0x28 + i * 0x30, i)
                index = i if i < 6 else i + 1
                m.put(frame + 0x1c8 + index * 4, 0x1800000 + i * 0x100)
            m.hooks.update({0x1900000: lambda _: 1, 0x1900100: lambda _: 0,
                            0x139f00: lambda _: 0})
            m.run(popup_entry, frame)
            expected = [6 if v == pad_value and i != slot else v for i, v in enumerate(values)]
            expected[slot] = pad_value
            assert [m.get(frame + 0x24 + i * 0x30) for i in range(8)] == expected
            for i, value in enumerate(expected):
                assert m.get(0x1800000 + i * 0x100 + 0x40) == value + (value >= 6)
            assert m.get(frame + 0x2c4) == 0 and m.get(ui + 0x24) == 1
            sequence, reopened = 0x1a00000, 0x1b00000
            m.run(cpout, sequence, frame + 0x1c)
            encoded = [v + 15 if v >= 7 else v for v in expected]
            assert [m.get(sequence + 8 + i * 0x30) for i in range(6)] == encoded[:6]
            assert [m.get(0x110808 + i * 0x30) for i in range(2)] == encoded[6:]
            m.run(cpin, reopened + 0x1c, sequence)
            assert [m.get(reopened + 0x24 + i * 0x30) for i in range(8)] == expected
            cvt = (words[0x24d690] & 0x3ffffff) << 2
            label_frame = 0x1d00000
            m.r[2], m.r[3] = label_frame, pad_value + 15
            m.run(cvt)
            assert m.get(label_frame + 0x22d4) == pad_value
            pmask = (words[0x24e310] & 0x3ffffff) << 2
            stack = m.r[29]
            for i in range(8):
                m.put(stack + 0x50 + i * 4, pad_value + 15)
                m.put(stack + 0x70 + i * 4, pad_value + 15)
            m.run(pmask)
            assert [m.get(stack + 0x50 + i * 4) for i in range(8)] == [pad_value - 1] * 8
            assert [m.get(stack + 0x70 + i * 4) for i in range(8)] == [pad_value] * 8
            selector = (words[0x24d528] & 0x3ffffff) << 2
            select_out = (words[0x24ea78] & 0x3ffffff) << 2
            for page in range(2):
                select_frame = 0x1c00000
                m.put(0x110790, page)
                m.run(selector, select_frame, sequence)
                assert [m.get(select_frame + 8 + i * 0x30) for i in range(4)] == encoded[page * 4:page * 4 + 4]
                m.run(select_out, sequence, select_frame)
            m.run(cpin, reopened + 0x1c, sequence)
            assert [m.get(reopened + 0x24 + i * 0x30) for i in range(8)] == expected

    # Constructor mode selection and register preservation.
    for layout_type, record, mode in ((5, 85, 1), (5, 72, 2), (5, 49, 0), (10, 85, 0)):
        m = Machine(words)
        obj, frame = 0x1400000, 0x1500000
        m.r[17] = frame
        m.put(frame + 0x240, layout_type)
        m.put(frame + 0x1a4, record)
        m.hooks[0x13ae30] = lambda _: obj
        m.run(0x3b2010, obj, 11)
        assert m.r[2] == obj and m.r[17] == frame
        assert m.get(obj + 0x3c) == mode

    for mode in (0, 1, 2):
        for alpha in (0, 128, 255):
            m = Machine(words)
            obj = 0x1400000
            m.put(obj + 0x3c, mode)
            draws, fallback = [], []

            def ctor(machine):
                rect = machine.r[4]
                machine.fp(rect + 0x10, 1)
                machine.fp(rect + 0x14, 1)
                return rect

            def draw(machine):
                rect = machine.r[4]
                draws.append((machine.fl(rect), machine.fl(rect + 4),
                              machine.fl(rect + 0xa0), machine.fl(rect + 0xa4),
                              tuple(machine.get(rect + 0x30 + i * 4) for i in range(4))))
                return 0

            m.hooks.update({0x13b070: lambda _: alpha, 0x15e070: ctor,
                            0x15e0b0: draw,
                            0x13af60: lambda _: fallback.append(True) or 0})
            m.run(0x3eddd0, obj)
            assert bool(fallback) == (mode == 0)
            assert len(draws) == (5 if mode and alpha else 0)
            if draws:
                assert draws[0][:4] == (320, 246, 640, 312)
                assert [d[1] for d in draws[1:]] == [128, 206, 284, 362]
                assert all(d[2:4] == (608, 70) for d in draws[1:])
                assert all(d[4][3] == alpha for d in draws)
                colors = [d[4][:3] for d in draws[1:]]
                assert len(set(colors)) == (4 if mode == 1 else 1)
    # The accidental count-menu redesign is fully reverted.
    for addr in (0x133c68, 0x47b15c):
        assert words[addr] == struct.unpack_from("<I", original, addr - 0x100000 + 0x80)[0]

    for layout_type, humans in ((14, 8), (14, 7), (14, 6), (11, 8)):
        m = Machine(words)
        frame, bar = 0x1400000, 0x1500000
        m.r[16], m.r[3], m.r[2] = frame, bar, 0x3f800000
        m.f[0] = fbits(1.34)
        m.put(frame + 0x15c, layout_type)
        m.put(frame + 0x154, humans)
        m.run(0x3ead70)
        expected = 1.9 if layout_type == 14 and humans >= 7 else 1.34
        assert abs(m.fl(bar + 0x74) - expected) < 1e-5
        assert m.r[2] == 0x3f800000 and m.r[3] == bar

    print('OK: 7P/8P in all eight boxes, deduplication, labels/pads, reopening, both select pages, row teams/background, expanded assignment popup and reverted count menu, and retail fallbacks')


if __name__ == '__main__':
    main()
