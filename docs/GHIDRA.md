# Reverse engineering HCTP with Ghidra

How to load the PlayStation 2 executable of **WWE SmackDown! Here Comes the Pain (USA)** into Ghidra, and how to use what you find to write patches for this project.

Nothing from the game is in this repository, and neither is any Ghidra output (it is derived from the game). You make your own from your own disc.

## 1. Requirements

- Your own dump of the USA disc (ISO)
- Ghidra 12.1.4
- Java JDK 25
- [ghidra-emotionengine-reloaded](https://github.com/chaoticgd/ghidra-emotionengine-reloaded) (adds the PS2 R5900 CPU)
- macOS, Linux or Windows

| Property | Value |
| --- | --- |
| Game ID | SLUS-20787 |
| Executable | `SLUS_207.87` |
| Platform | PlayStation 2 |
| CPU | Emotion Engine (R5900), MIPS, little-endian |

## 2. Extract the executable

```bash
python3 tools/extract_elf.py "WWE SmackDown! Here Comes the Pain (USA).iso" SLUS_207.87
```

The tool checks the file. The expected values are:

```text
size    5,652,964 bytes
SHA-1   d8ef8451378be669184de04478a550c8a46d02d6
SHA-256 790a11772b2df7fe61a96e8c9e1c6f9e01e8dfb6850029499f74c5822f2dbe0f
```

Other regions or revisions have different code and addresses. Every address in this repository is for this exact file.

(Any ISO tool that can extract files works too, as long as the checksums match.)

## 3. Install Ghidra 12.1.4

Download it from <https://github.com/NationalSecurityAgency/ghidra/releases>, unzip it and install a compatible JDK (we used JDK 25).

We used **12.1.4** because the PS2 extension we had was not compatible with Ghidra 12.2. Use the extension build that matches your Ghidra version.

## 4. Install the PS2 Emotion Engine extension

Extension: <https://github.com/chaoticgd/ghidra-emotionengine-reloaded>

We used the archive built for Ghidra 12.1.4:

```text
ghidra_12.1.4_PUBLIC_20261004_ghidra-emotionengine-reloaded.zip
```

1. Open Ghidra.
2. **File → Install Extensions**.
3. Click **+** and select the extension ZIP.
4. Enable the extension if asked.
5. Restart Ghidra.

The language `r5900:LE:32:default:default` should now exist.

## 5. Create a project

1. **File → New Project**.
2. **Non-Shared Project**.
3. Name it `HCTP_PS2`.

## 6. Import the executable

1. **File → Import File**, choose `SLUS_207.87`.
2. Check that Ghidra recognizes the executable format.
3. Select the language `r5900:LE:32:default:default`.
4. Finish the import and double-click the file to open the CodeBrowser.

## 7. Run auto analysis

Answer **Yes** when Ghidra asks to analyze, keep the default analyzers and run it. It takes a while.

Our run found about 14,736 functions, 27,362 symbols and 777,051 instructions. The executable still has its symbol table (24,475 symbols), so most functions have real names such as `SetCommon__…`, `GetDefRule`, `CreateGameChar`. Names are C++ mangled (`AppMainLoop__Fv`).

## 8. Decompiler problems (Intel Mac, some Linux builds)

On our Intel Mac Ghidra's native decompiler and demangler were missing. We built them:

```bash
cd ~/Documents/ghidra_12.1.4_PUBLIC/support/gradle
./gradlew buildNatives
```

Expected: `BUILD SUCCESSFUL`. Restart Ghidra and reopen the project. Only needed if your install lacks binaries for your platform.

## 9. Explore

In the CodeBrowser use:

- **Symbol Tree → Functions**: pick a function, see assembly in *Listing* and C-like code in *Decompiler*.
- **Search → For Strings**: UI text and file names.
- **Search → Memory**: byte patterns, for example the vtable address `0x47F670` to find `SelectWrestlerOne` objects.
- **References → Show References To**: who calls a function or reads a table.
- **Function Graph**: control flow.

Good starting points for this mod: `main`, `AppMainLoop__Fv`, `ExshibitionMenuSequence::SetCommon` (0x130D10), `GetDefRule` (0x12CC90), `SelectWrestlerFrame` methods (0x24D…–0x24E…), `CreateGameChar` (0x1FB150), `StartCharSetup` (0x1FA0B0), `caSd5Game2D` (HUD).

## 10. Export the decompiled C (optional)

A text file is much easier to grep than the GUI:

1. **File → Export Program**.
2. Format **C/C++**.
3. Options: create header (`.h`), create C file (`.c`), emit data-type definitions, emit referenced globals.
4. Export to a folder such as `HCTP_Source/`.

The result is about 15.5 MB (`hctp_decompiled.c` and `.h`). It is Ghidra pseudocode, not the original source, and cannot be compiled back into the game. `HCTP_Source/` is in `.gitignore`.

## 11. Archive the project

**File → Archive Current Project** and save `HCTP_PS2.gar`, so you or a friend can restore the same analysis later with the same extension. `*.gar` is in `.gitignore` too: do not publish it.

## 12. From Ghidra address to patch

Ghidra shows **virtual addresses** (vaddr). This project's patch files use the same:

```text
file offset = vaddr - 0x100000 + 0x80
```

Only the first `0x389880` bytes of the file are loaded as code and data; the rest is symbols.

A patch line is either a word or raw bytes:

```text
00130DF4 w 0C0441A0       # (example values) write 32-bit word at vaddr 0x130DF4
00455DC0 0102030405       # write these bytes
```

Workflow:

1. Find the code in Ghidra (decompiler for meaning, listing for the exact instructions).
2. Put new code in a code cave. The executable has no free space, so this project overwrites **unreferenced library functions** (`sceWrite`, `sceFormat`, …). `tools/deadcode.py` lists them, and `tools/check_patch.py` checks that a patch never touches a function that is still called. See [HOW_IT_WORKS.md](HOW_IT_WORKS.md).
3. Write the change in `src/gen_patch.py` (it has a tiny assembler, `src/asm.py`) and rebuild with `python3 build.py`.
4. Test in PCSX2 and watch memory live through PINE with `tools/pine.py` and `tools/monitors/`. Read only: PINE writes into cave pages crash PCSX2.

Useful helper scripts (all read `$HCTP_ELF`, default `./SLUS_207.87`):

| Script | Use |
| --- | --- |
| `tools/syms.py` | dump the symbol table to `symbols.txt` |
| `tools/dis.py` | quick disassembly of a vaddr range |
| `tools/jal.py` | find every call to a function |
| `tools/deadcode.py` | list unreferenced functions (code caves) |
| `tools/base.py ADDR` | find code that builds the address `ADDR` (lui + addiu pair) |
| `tools/range.py LO HI` | find loads/stores whose computed address lies in `LO`..`HI` |

Tip: when Ghidra disagrees with what the game does, trust the running game. Dump RAM from PCSX2 through PINE and compare.

## 13. Legal

Do not commit or share the executable, the ISO, the Ghidra project, the `.gar` archive or the exported C files. They contain the game's code.
