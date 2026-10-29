#!/usr/bin/env python3
"""Build the 8-player patched game from YOUR OWN dump of WWE SmackDown! Here Comes the Pain (USA, SLUS-20787).

    python3 build.py --iso game.iso --out game_8p.iso        patched copy of your ISO (4.5 GB free space needed)
    python3 build.py --iso game.iso --in-place               patch the ISO file itself (no copy; keep a backup!)
    python3 build.py --elf SLUS_207.87 --out SLUS_207.87.8p  only the patched executable (for ISO tools / OPL tricks)

Nothing from the game is stored in this repository. The tool reads the game executable from your dump,
checks that it is the exact expected file (SHA-1), generates the patch from it and writes the result.
Only the Python 3 standard library is used.
"""
import argparse
import hashlib
import os
import shutil
import struct
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
EXE_NAME = "SLUS_207.87"
EXE_SIZE = 5652964
ORIG_SHA1 = "d8ef8451378be669184de04478a550c8a46d02d6"      # original SLUS_207.87 (USA)
PATCHED_SHA1 = "6414dd213f03db3350f9801da80415077ae9dbba"   # expected result
SECTOR = 2048
LOAD_VADDR, LOAD_OFF, LOAD_SIZE = 0x100000, 0x80, 0x389800   # program header 0: only this part of the file is loaded


def die(msg):
    print("ERROR: " + msg, file=sys.stderr)
    sys.exit(1)


def sha1(b):
    return hashlib.sha1(b).hexdigest()


def find_exe_in_iso(f):
    """Minimal ISO9660 reader: returns (lba, size) of SLUS_207.87 in the root directory."""
    f.seek(16 * SECTOR)
    pvd = f.read(SECTOR)
    if pvd[1:6] != b"CD001":
        die("not an ISO9660 image with 2048-byte sectors (raw 2352-byte BIN/CUE images are not supported; convert to ISO first)")
    root_lba = struct.unpack_from("<I", pvd, 156 + 2)[0]
    root_size = struct.unpack_from("<I", pvd, 156 + 10)[0]
    f.seek(root_lba * SECTOR)
    d = f.read(root_size)
    pos = 0
    while pos < len(d):
        n = d[pos]
        if n == 0:                       # records never straddle a sector: skip to the next one
            pos = (pos // SECTOR + 1) * SECTOR
            continue
        lba = struct.unpack_from("<I", d, pos + 2)[0]
        size = struct.unpack_from("<I", d, pos + 10)[0]
        name = d[pos + 33:pos + 33 + d[pos + 32]].decode("latin1").split(";")[0]
        if name.upper() == EXE_NAME:
            return lba, size
        pos += n
    die(EXE_NAME + " not found in the ISO root directory. Is this the USA version (SLUS-20787)?")


def generate_patch(elf_bytes):
    """Run src/gen_patch.py against the original executable; returns the patch text."""
    with tempfile.TemporaryDirectory() as tmp:
        elf_path = os.path.join(tmp, EXE_NAME)
        out_path = os.path.join(tmp, "patch.txt")
        with open(elf_path, "wb") as fh:
            fh.write(elf_bytes)
        env = dict(os.environ, HCTP_ELF=elf_path, HCTP_PATCH_OUT=out_path)
        r = subprocess.run([sys.executable, os.path.join(HERE, "src", "gen_patch.py")], env=env, capture_output=True, text=True)
        if r.returncode != 0:
            die("patch generator failed:\n" + r.stdout + r.stderr)
        return open(out_path).read()


def apply_patch(elf_bytes, patch_text):
    elf = bytearray(elf_bytes)
    count = 0
    for line in patch_text.splitlines():
        t = line.split("#")[0].split()
        if not t:
            continue
        va = int(t[0], 16)
        data = struct.pack("<I", int(t[2], 16)) if t[1] == "w" else bytes.fromhex("".join(t[1:]))
        off = va - LOAD_VADDR + LOAD_OFF
        if not (LOAD_OFF <= off and off + len(data) <= LOAD_OFF + LOAD_SIZE):
            die("patch outside the loaded part of the executable: %08x" % va)
        elf[off:off + len(data)] = data
        count += 1
    return bytes(elf), count


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--iso", help="your game image (ISO, 2048-byte sectors)")
    src.add_argument("--elf", help="the extracted SLUS_207.87 file")
    ap.add_argument("--out", help="output file")
    ap.add_argument("--in-place", action="store_true", help="with --iso: modify the ISO itself instead of writing a copy")
    ap.add_argument("--keep-patch", metavar="FILE", help="also save the generated patch list (for inspection)")
    a = ap.parse_args()
    if a.in_place and not a.iso:
        die("--in-place needs --iso")
    if not a.in_place and not a.out:
        die("give --out FILE (or --in-place)")

    lba = None
    if a.iso:
        with open(a.iso, "rb") as f:
            lba, size = find_exe_in_iso(f)
            if size != EXE_SIZE:
                die("%s in the ISO has %d bytes, expected %d" % (EXE_NAME, size, EXE_SIZE))
            f.seek(lba * SECTOR)
            elf = f.read(size)
    else:
        elf = open(a.elf, "rb").read()
    h = sha1(elf)
    if h == PATCHED_SHA1:
        die("this executable is already patched")
    if h != ORIG_SHA1:
        die("wrong executable: SHA-1 %s, expected %s (USA, SLUS-20787, unmodified)" % (h, ORIG_SHA1))

    print("generating patch ...")
    patch = generate_patch(elf)
    if a.keep_patch:
        open(a.keep_patch, "w").write(patch)
    new, n = apply_patch(elf, patch)
    print("applied %d patch entries" % n)
    if len(new) != len(elf):
        die("internal error: size changed")
    h2 = sha1(new)
    if h2 != PATCHED_SHA1:
        die("result SHA-1 %s differs from the expected %s (generator or Python version problem?)" % (h2, PATCHED_SHA1))

    if a.elf:
        open(a.out, "wb").write(new)
        print("wrote", a.out)
        return

    if a.in_place:
        if input("This overwrites %s directly. Type YES to continue: " % a.iso) != "YES":
            die("aborted")
        out = a.iso
    else:
        out = a.out
        if os.path.abspath(out) == os.path.abspath(a.iso):
            die("--out must differ from --iso (use --in-place to modify the ISO)")
        print("copying the ISO (this takes a while) ...")
        if sys.platform == "darwin":                                    # APFS clone: instant, no extra space
            if subprocess.call(["cp", "-c", a.iso, out]) != 0:
                shutil.copyfile(a.iso, out)
        else:
            shutil.copyfile(a.iso, out)
    with open(out, "r+b") as f:
        f.seek(lba * SECTOR)
        f.write(new)
    with open(out, "rb") as f:
        f.seek(lba * SECTOR)
        if sha1(f.read(len(new))) != PATCHED_SHA1:
            die("verification of the written file failed")
    print("done: %s  (executable SHA-1 %s)" % (out, PATCHED_SHA1))


if __name__ == "__main__":
    main()
