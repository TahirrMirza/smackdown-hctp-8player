#!/usr/bin/env python3
"""Extract SLUS_207.87 from your own game ISO (needed to load it in Ghidra).

    python3 tools/extract_elf.py "WWE SmackDown! Here Comes the Pain (USA).iso" SLUS_207.87

Checks the SHA-1 of the original executable and refuses anything else.
"""
import hashlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
import build  # noqa: E402  (build.py is importable, main() only runs as a script)


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    iso, out = sys.argv[1], sys.argv[2]
    with open(iso, "rb") as f:
        lba, size = build.find_exe_in_iso(f)
        f.seek(lba * build.SECTOR)
        data = f.read(size)
    h = hashlib.sha1(data).hexdigest()
    if h != build.ORIG_SHA1:
        sys.exit("unexpected executable: SHA-1 %s, expected %s" % (h, build.ORIG_SHA1))
    with open(out, "wb") as f:
        f.write(data)
    print("wrote %s (%d bytes, SHA-1 %s)" % (out, size, h))
    print("SHA-256 %s" % hashlib.sha256(data).hexdigest())


main()
