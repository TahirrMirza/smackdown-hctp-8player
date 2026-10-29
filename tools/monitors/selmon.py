"""Log SelectWrestlerOne panels + SelectWrestlerFrame entries while the user plays (PINE, read only).
usage: python3 selmon.py out.log [seconds]"""
import os, socket, struct, sys, time

SOCK = os.path.join(os.environ.get("TMPDIR", "/tmp"), "pcsx2.sock")
START, END, BATCH = 0x100000, 0x2000000, 8192


def dump():
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.settimeout(10)
    s.connect(SOCK)

    def recvn(n):
        b = b""
        while len(b) < n:
            c = s.recv(n - len(b))
            if not c:
                raise RuntimeError("closed")
            b += c
        return b

    out = bytearray()
    addr = START
    while addr < END:
        n = min(BATCH, (END - addr) // 8)
        cmds = b"".join(bytes([3]) + struct.pack("<I", addr + i * 8) for i in range(n))
        s.sendall(struct.pack("<I", len(cmds) + 4) + cmds)
        size = struct.unpack("<I", recvn(4))[0]
        body = recvn(size - 4)
        if body[0] != 0:
            raise RuntimeError("PINE error")
        out += body[1:]
        addr += n * 8
    s.close()
    return bytes(out)


def w(d, a):
    o = a - START
    return struct.unpack_from("<I", d, o)[0] if 0 <= o <= len(d) - 4 else None


def snap(d):
    res = []
    pat = struct.pack("<I", 0x47F670)
    i = d.find(pat)
    objs = []
    while i != -1:
        if i % 4 == 0:
            objs.append(START + i)
        i = d.find(pat, i + 1)
    frames = {}
    for a in objs:
        f = w(d, a + 0x14)
        row = (a, f, w(d, a + 0x18), w(d, a + 0x1C), w(d, a + 0x20), w(d, a + 0x24), w(d, a + 0x28), w(d, a + 0x2C))
        res.append(row)
        if f and START <= f < END - 0x2300:
            frames[f] = 1
    txt = []
    for f in frames:
        hd = [w(d, f + o) for o in (0x13C, 0x140, 0x144, 0x148, 0x2260, 0x2264, 0x2268)]
        txt.append("FRAME %x hum13c/140=%s/%s rec144=%s type148=%s f2260=%s f2264=%s main2268=%s" % ((f,) + tuple("%x" % v if v is not None else "?" for v in (hd[0], hd[1], hd[2], hd[3], hd[4], hd[5], hd[6]))))
        for e in range(8):
            b = f + 0x1C + 0x30 * e
            ent = [w(d, b + o) for o in (0, 4, 8, 0xC, 0x10, 0x14, 0x18)]
            txt.append("  ent%d idx/act/pad/b0/b1/b2/x18=%s" % (e, "/".join("%x" % v if v is not None else "?" for v in ent)))
    for r in sorted(res):
        txt.append("  one@%x frame=%x idx=%x seltype=%x pad=%x type=%x state=%x +2c=%x" % tuple(0 if v is None else v for v in r))
    flags = "PASS=%s HAVE=%s POS67=%s,%s" % (w(d, 0x110790), w(d, 0x110794), w(d, 0x11227C), w(d, 0x112280))
    return flags + "\n" + "\n".join(txt)


def main():
    out = open(sys.argv[1], "a")
    secs = int(sys.argv[2]) if len(sys.argv) > 2 else 3600
    last = None
    t0 = time.time()
    while time.time() - t0 < secs:
        try:
            d = dump()
            s = snap(d)
        except Exception as e:
            s = "pine-down %s" % e
        if s != last:
            out.write("=== %s\n%s\n" % (time.strftime("%H:%M:%S"), s))
            out.flush()
            last = s
        time.sleep(1.0)


main()
