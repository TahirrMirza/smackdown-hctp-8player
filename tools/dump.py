import os, socket, struct, sys

SOCK = os.path.join(os.environ.get("TMPDIR", "/tmp"), "pcsx2.sock")
START, END, BATCH = 0x100000, 0x2000000, 8192  # 8 bytes per read64

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
    body = body[1:]
    # each reply is 8 data bytes, no per-command status
    out += body
    addr += n * 8
open(sys.argv[1], "wb").write(out)
print("dumped", len(out), "bytes to", sys.argv[1])
