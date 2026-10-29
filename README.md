# WWE SmackDown! Here Comes the Pain — 8-player mod (PS2)

A patch that lets **eight human players** play one match in *WWE SmackDown! Here Comes the Pain* (USA, PS2). The original game stops at six. You need two multitaps and eight pads.

It is made of direct patches to the game executable (`SLUS_207.87`). No emulator-only cheats, so it works the same in PCSX2 and on a real PS2.

> **No game files are in this repository.** You must supply your own legally obtained dump of the USA disc. The build script checks that your executable is the exact expected file and refuses anything else.
> This project is not affiliated with or endorsed by WWE, THQ, Yuke's or Sony.

## What works (patch "s49")

Two new match types, both for 8 human players:

| Menu | Entry | What it is |
| --- | --- | --- |
| Exhibition → **LADDER** (last item) | **4 PLAYER ROYAL BATTLE** | Ladder match with the belt, 4 teams of two |
| Exhibition → **SURVIVAL** (last item) | **8-MAN BATTLE ROYAL** | Battle royal, every wrestler for himself |

Also new:
- The player-count list offers **1 to 8 PLAYERS** (plus ALL COM). Options are enabled only up to the number of pads the console sees.
- A position screen with **8 boxes** where you choose which pad (or COM) plays each box, with new pad labels **7P** / **8P**.
- The wrestler select screen is split into **two 2×2 screens** (slots 1–4, then slots 5–8). Wrestlers picked on screen 1 are removed from the grid on screen 2.
- All eight pads control their own panel, eight wrestlers load and fight.
- All ordinary matches are unchanged (6-man etc. work as before).

Tested by the author: PCSX2 2.8.2 (macOS), an Android PS2 emulator, and a real PS2 with two multitaps (8 pads).

## Known issues — please read

**Only two match types support 8 players, and only with a full 8 human players.** Every other mode is unchanged and limited to 6, as in the original game. Do not expect other modes to work with 8.

| Issue | Status |
| --- | --- |
| **Only LADDER "4 PLAYER ROYAL BATTLE" and SURVIVAL "8-MAN BATTLE ROYAL" are 8-player.** All other match types (tag, triple threat, hardcore, Elimination Chamber, Royal Rumble, …) are not converted. | open, [contributions welcome](https://github.com/TahirrMirza/smackdown-hctp-8player/blob/main/CONTRIBUTING.md) |
| **Fewer than 8 humans or ALL COM is broken** in those two modes. With 1 player or ALL COM only part of the wrestlers get picked; with 6 players the second select screen hangs. Choose **8 PLAYERS**. | open, see [KNOWN_ISSUES](https://github.com/TahirrMirza/smackdown-hctp-8player/blob/main/docs/KNOWN_ISSUES.md) |
| **HUD shows only 6 health cards.** Wrestlers 7 and 8 have none. | open, see below |
| **PLAY summary screen lists only 6 names.** | open |
| **No referee** in the 8-wrestler matches. | by design, see below |
| COM slots 7/8 may get the same default wrestler as slot 6 when not picked. | open |
| The SmackDown-icons page of a panel has no frame. | not a bug: the original game does the same |

### Why only 6 health cards

The in-match HUD (`caSd5Game2D` and `CSpriteCtrlGame2D`) is built for six wrestlers: six fixed plate positions (two columns, top and bottom rows) and many per-plate arrays and loops of size 6. Making it draw eight is not just a table change. What we tried:

- **Scaling the whole HUD** toward the screen corners with a hook on the matrix multiply used by 2D drawing. This works: the six cards shrink to 50–75 % and stay in their corners.
- **A second row for wrestlers 7 and 8**, either by building a second HUD object or by swapping slot data and drawing the HUD twice. Both failed:
  - A second HUD object loaded its own data, which made the wrestlers invisible and the crowd and music disappear.
  - Running the HUD update twice per frame has side effects (pause state, controller removal, timer, ring-out counter), which gave glitches: a stuck "Hit any button repeatedly" prompt, a "DQ" text in the middle of the screen and a ring-out count that stayed on screen.
  - Cards for slots 7 and 8 were never initialised, because the game builds the plates once in the constructor.

So the character layout and the rest of the UI break as soon as the HUD is forced to eight. A clean solution has to extend the HUD arrays, plate position tables and loops properly instead of drawing it twice. Details and addresses are in the [dev log](https://github.com/TahirrMirza/smackdown-hctp-8player/blob/main/docs/DEV_LOG.md) (sections 19, 20, 22) and in [KNOWN_ISSUES](https://github.com/TahirrMirza/smackdown-hctp-8player/blob/main/docs/KNOWN_ISSUES.md).

### Why there is no referee

The game keeps eight character slots: six wrestlers, one referee (slot 6) and one spare. For eight wrestlers the referee slot is used by a wrestler, so there is no referee object. Testing showed this does not stop matches: with the referee flag off, an AI match still ended with a winner by pinfall or finish, and the referee's actions are performed by game rules independently of the referee model. (Count-outs, disqualifications and submissions were not tested exhaustively. A referee model still appears in the post-match cutscene.)

Real PS2: the image is a dual-layer DVD (4.5 GB). Booting it from a drive with a loader such as Open PS2 Loader is the easy way; see [RUNNING.md](https://github.com/TahirrMirza/smackdown-hctp-8player/blob/main/docs/RUNNING.md).

## What you need

- The USA disc dump as an **ISO with 2048-byte sectors** (`WWE SmackDown! Here Comes the Pain (USA).iso`, about 4.5 GB, dual layer). Its executable must be `SLUS_207.87`, SHA-1 `d8ef8451378be669184de04478a550c8a46d02d6`, size 5,652,964 bytes.
- **Python 3.8 or newer.** Nothing else — only the standard library is used.
- About **4.5 GB of free disk space** for the patched ISO (on macOS/APFS the copy is instant and takes no space).
- To play: PCSX2 (v2.x) **or** a softmodded PS2 with OPL, **plus two multitaps and eight pads**.

## Build

```bash
git clone <this repo>
cd smackdown-hctp-8player
python3 build.py --iso "/path/to/WWE SmackDown! Here Comes the Pain (USA).iso" --out smackdown_8p.iso
```

The script
1. finds `SLUS_207.87` inside the ISO,
2. checks its SHA-1 (wrong file → it stops),
3. generates the patch from that executable,
4. writes a copy of the ISO with the patched executable (same size, same sector position, nothing else moves),
5. re-reads it and verifies the result: patched executable SHA-1 must be `6414dd213f03db3350f9801da80415077ae9dbba`.

Other modes:

```bash
python3 build.py --iso game.iso --in-place                 # patch the ISO file itself (keep a backup!)
python3 build.py --elf SLUS_207.87 --out SLUS_207.87.8p    # only the patched executable
python3 build.py --iso game.iso --out x.iso --keep-patch patch.txt   # also keep the generated patch list
python3 tools/check_patch.py SLUS_207.87 patch.txt         # static checks of a patch list
```

Raw `.bin/.cue` images (2352-byte sectors) are not supported: convert them to a plain ISO first.

## Play

Short version (details: [RUNNING.md](https://github.com/TahirrMirza/smackdown-hctp-8player/blob/main/docs/RUNNING.md)):

1. **PCSX2:** Settings → Controllers: enable **Multitap on Port 1 and Port 2**, bind pads 1A–1D and 2A–2D. Boot the patched ISO (System → Start File).
2. **Real PS2:** put the ISO on a USB/SMB/HDD drive and boot with Open PS2 Loader.
3. In the game: Exhibition → **LADDER → 4 PLAYER ROYAL BATTLE**, or **SURVIVAL → 8-MAN BATTLE ROYAL** → choose **8 PLAYERS** → assign the eight pads on the position screen → pick wrestlers on the two select screens → stage → play.

## Documentation

| Document | Contents |
| --- | --- |
| [RUNNING.md](https://github.com/TahirrMirza/smackdown-hctp-8player/blob/main/docs/RUNNING.md) | PCSX2 and real PS2 (Open PS2 Loader) instructions, test list |
| [HOW_IT_WORKS.md](https://github.com/TahirrMirza/smackdown-hctp-8player/blob/main/docs/HOW_IT_WORKS.md) | design of the patch, with addresses |
| [GHIDRA.md](https://github.com/TahirrMirza/smackdown-hctp-8player/blob/main/docs/GHIDRA.md) | load the game in Ghidra, analyse it, turn findings into patches |
| [KNOWN_ISSUES.md](https://github.com/TahirrMirza/smackdown-hctp-8player/blob/main/docs/KNOWN_ISSUES.md) | open problems, causes and ideas |
| [DEV_LOG.md](https://github.com/TahirrMirza/smackdown-hctp-8player/blob/main/docs/DEV_LOG.md) | the full chronological reverse-engineering log |
| [CONTRIBUTING.md](https://github.com/TahirrMirza/smackdown-hctp-8player/blob/main/CONTRIBUTING.md) | how to help, wanted work, Elimination Chamber notes |

## Repository layout

```
build.py              one-command build (ISO in, ISO out)
src/gen_patch.py      the patch generator (assembles the new code, relocates tables, writes the patch list)
src/asm.py            tiny MIPS (R5900 subset) assembler used by the generator
src/remap_*.py        rewrite field offsets in three UI classes whose objects had to grow
src/base_patches.txt  hand-written base patches (player-count menu strings and lists)
src/padlayout_rows.json  672 bytes of UI box coordinates (float bit patterns) recorded from the running game for the pad-select popup; positions only
tools/                reverse-engineering helpers (extractor, disassembler, jal finder, symbol dump, dead-code finder, PINE client, patch checker)
tools/monitors/       scripts that watch a running PCSX2 through PINE
docs/                 the documents listed above
```

## For developers

- Everything is reproducible: `build.py` regenerates the same executable byte for byte (the SHA-1 above is checked on every run).
- The patch uses **unreferenced library functions as code caves** (the executable has no free space). `tools/deadcode.py` finds them, `tools/check_patch.py` checks that no patch touches a function that is still called.
- Debug workflow: patch → build ISO → boot in PCSX2 → watch memory through PINE (`tools/pine.py`, `tools/monitors/`). PINE data writes into the cave pages and live code patching crash PCSX2; use it read-only.
- Tools read the executable from `$HCTP_ELF` (default `./SLUS_207.87`). `tools/syms.py` writes `symbols.txt`, which `tools/deadcode.py` needs. Do not commit these files.
- Ghidra with the EmotionEngine plugin was used for the decompilation (not included, it is derived from the game). How to set it up: [GHIDRA.md](https://github.com/TahirrMirza/smackdown-hctp-8player/blob/main/docs/GHIDRA.md).

## Contributing

**Contributions are welcome**: fixes for the known issues, support for more match types, documentation, and test reports from real hardware. Start with [CONTRIBUTING.md](https://github.com/TahirrMirza/smackdown-hctp-8player/blob/main/CONTRIBUTING.md).

The hardest open item is the **Elimination Chamber**: it has only four pods, and in the original two wrestlers start in the ring and four wait in the pods. Eight wrestlers need a very different layout (for example four in the ring and four in the pods, or two per pod). Ideas on how the layout could look and how to implement it are very welcome; see the notes in [CONTRIBUTING.md](https://github.com/TahirrMirza/smackdown-hctp-8player/blob/main/CONTRIBUTING.md#the-hard-one-elimination-chamber) and open an issue or pull request.

## License

The code in this repository is MIT licensed, see `LICENSE`. The game is the property of its owners and is not included.
