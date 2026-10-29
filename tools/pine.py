import os, socket, struct

SOCK = os.path.join(os.environ.get("TMPDIR", "/tmp"), "pcsx2.sock")


def _call(payload):
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.settimeout(3)
    s.connect(SOCK)
    s.sendall(struct.pack("<I", len(payload) + 4) + payload)
    n = struct.unpack("<I", s.recv(4))[0]
    buf = b""
    while len(buf) < n - 4:
        buf += s.recv(n - 4 - len(buf))
    s.close()
    if buf[0] != 0:
        raise RuntimeError("PINE error")
    return buf[1:]


def read32(addr):
    return struct.unpack("<I", _call(bytes([2]) + struct.pack("<I", addr)))[0]


def write32(addr, val):
    _call(bytes([6]) + struct.pack("<II", addr, val))


def status():
    return struct.unpack("<I", _call(bytes([0x0F])))[0]  # 0 running, 1 paused, 2 shutdown


def title():
    r = _call(bytes([0x0B]))
    return r[4:].split(b"\0")[0].decode()


if __name__ == "__main__":
    print("title", title(), "status", status())
    print("elf entry word @0x100008:", hex(read32(0x100008)))


def read8(addr):
    return _call(bytes([0]) + struct.pack("<I", addr))[0]


def write8(addr, val):
    _call(bytes([4]) + struct.pack("<IB", addr, val))
