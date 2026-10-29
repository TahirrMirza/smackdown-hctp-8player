# How the patch works

All addresses are **virtual addresses** in the game executable `SLUS_207.87` (file offset = vaddr − 0x100000 + 0x80). The executable has no free space, so the patch overwrites **unreferenced library functions** (`sceWrite`, `sceFormat`, `sceDopen`…`sceRename`, `sceMount`, `sceDevctl`/`sceSymlink`/`sceReadlink`, `sceSifLoadIopHeap`, `sceSifStopModule`…) with new code and data (code caves). `tools/deadcode.py` lists candidates; `tools/check_patch.py` checks that no patch touches a function that is still called.

The executable's symbol table is intact (24,475 symbols). `python3 tools/syms.py` writes them to `symbols.txt` from your copy; the names below come from it.

## 1. Engine: eight wrestlers

- The game has 8 pad objects and an 8-entry character array (`g_pChar`, 0x526EA0) but is sized for 6 players + referee. Loops that were hard-coded to 6/7 were raised to 8: `MakeGameLoad_Char` (0x1FDF4C), `GameMem::Setup` page loop (0x1FF080, 0x1FF00C, plus a nop at 0x1FF004 so empty slots get a real memory page), character texture buffers (`SetupCharTexBuf` etc., 0x202BB8…0x202D40, 0x1DC710, 0x1BA474), `DrawMarker` loops/guards (0x299xxx), `SetCommon` (0x130D10: slot loops and pad bitmaps).
- Slot 6 (normally the referee) is a wrestler in the 8-player matches, so these matches have **no referee**.

## 2. Match records

- `s_GameTypeTbl` (0x45AF60): 86 records × 32 bytes. +0 group, +1 max players, +2 position layout type, +4 rule type, +8 title string id, +0xC… six (slot, team, extra) byte triples. The table cannot grow, so two **unused records** are reused: **85** (copy of 49, max 8, "4 PLAYER ROYAL BATTLE", teams of two) and **72** (copy of 27, max 8, "8-MAN BATTLE ROYAL", every wrestler its own team).
- Match rules (belt, referee flag…) come from the 64-byte rule table at 0x455DC0, **indexed by record number** (`GetDefRule`, 0x12CC90), so rules 85 and 72 are copies of 49 and 27.
- Menus: sub-menu lists are arrays of 12-byte items referenced by 20-byte descriptors at 0x45AD84…; new item lists live in a cave, descriptors (0x45AE38 LADDER, 0x45ADD4 SURVIVAL) point to them with count 6.
- The 8-player code paths trigger when the record's max-players byte is 8 (`IS8` macro in the generator). Flag `BRF` (0x113568) = group 7 (battle royal) selects the team tables.

## 3. Strings

`GetRCString` (0x12FD60) gets a hook that serves the new ids from a pointer table in a cave: 830 "7P", 831 "8P", 832 "4 PLAYER ROYAL BATTLE", 833 "8-MAN BATTLE ROYAL". The pad label table `s_wresCtrlStrID` (0x468580) is relocated with 9 entries. The player-count list (`PlayerEntryNext`, 0x131D80) gets 7 PLAYERS and 8 PLAYERS lists (`base_patches.txt`); a hook at 0x133C40 narrows the row pitch to 24 px when the list has 8+ rows.

## 4. Position screen

`PositionSelectFrame` (0x1394F0…) and `PositionSelectWindowFrame` (0x13B4F0…) were grown (object size 0x250 → 0x2C8, arrays 7 → 9) by `remap_frame.py` / `remap_win.py`, which rewrite every field displacement in those methods. A new layout (type 5, 8 boxes) replaces the 6-box layouts (`tblPosSelectLayout`, 0x45BD10 + 5×0xC4), the pad popup has 9 choices and the box-to-pad "cycle select" is a hook on `ChangeDecision`.

## 5. Side buffer for slots 7 and 8

The menu sequence struct (0x148 bytes, 6 entries) cannot grow. Slots 7 and 8 live in a **side buffer E** (0x110800…0x110868, same layout as a `tagMenuPosition` entry). Hooks:

| Hook | Where | Role |
| --- | --- | --- |
| `clamp` | `InitPositionInfo` 0x1307E8 | entry count = min(record max, 6) |
| `fix` | `SetCommon` 0x130DF4 | slots 6, 7 are read from E |
| `fwd` | `WrestlerSelectEnd` 0x1321D0 | select screen 1 → screen 2 (state 0x16), then done |
| `cnl` | `WrestlerSelectEnd` 0x1321C8 | cancel on screen 2 → screen 1 |
| `pe` | `PlayerEntryNext` 0x131DB4 | resets the state |
| `cut` | `SelectWrestlerFrame::ChangeIntroduction` 0x24E510 | removes screen-1 picks from the screen-2 grid |
| `scpin` / `scpout` | `SelectWrestlerFrame` ctor 0x24D528 / `ChangeDecision` 0x24EA78 | build the frame struct per screen and copy results back |
| `pmask`, `cvt`, `cinit` | `ConvertPositionData` etc. | pad values 0x16/0x17 (= pads 7, 8) → pad array / label ctrl values 7, 8 |

State flags: `PASS` 0x110790 (0 = screen 1, 1 = screen 2), `HAVE` 0x110794 (E valid), `POS67` 0x11227C (pads chosen for slots 7, 8 on the position screen).

## 6. Wrestler select in two screens

`SelectWrestlerFrame` (0x24D4B0…) was grown from 0x2284 to 0x22F4 bytes (8 entries, 8 `SelectWrestlerOne` pointers; 267 field accesses remapped by `remap_sel.py`; loops 6 → 8). Screen 1 shows entries 0–3, screen 2 shows entries 4, 5 and E0, E1, always as a 2×2 grid (frame type scalar forced to 3).

## 7. Real hardware notes

- No patch writes below 0x100000; every patch is inside the loaded image.
- Data words written at runtime (flags, side buffer, temp copy) never share a 64-byte cache line with executed new code (checked), and nothing writes code at runtime.
- `tools/check_patch.py` verifies delay slots and branch targets of the new code.
- The ISO is a clone of the original; only the executable's sectors change (same size, same LBA 768396 in the USA dump).

## Reproducibility

`build.py` produces an executable with SHA-1 `6414dd213f03db3350f9801da80415077ae9dbba` from the original `d8ef8451378be669184de04478a550c8a46d02d6`. For the full story and the dead ends see `DEV_LOG.md`.
