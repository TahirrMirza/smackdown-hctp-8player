# How the patch works

All addresses are **virtual addresses** in the game executable `SLUS_207.87` (file offset = vaddr − 0x100000 + 0x80). The executable has no free space, so the patch overwrites **unreferenced library functions** (`sceWrite`, `sceFormat`, `sceDopen`…`sceRename`, `sceMount`, `sceDevctl`/`sceSymlink`/`sceReadlink`, `sceSifLoadIopHeap`, `sceSifStopModule`…) with new code and data (code caves). `tools/deadcode.py` lists candidates; `tools/check_patch.py` checks that no patch touches a function that is still called.

The executable's symbol table is intact (24,475 symbols). `python3 tools/syms.py` writes them to `symbols.txt` from your copy; the names below come from it.

## 1. Engine: eight wrestlers

- The game has 8 pad objects and an 8-entry character array (`g_pChar`, 0x526EA0) but is sized for 6 players + referee. Loops that were hard-coded to 6/7 were raised to 8: `MakeGameLoad_Char` (0x1FDF4C), `GameMem::Setup` page loop (0x1FF080, 0x1FF00C, plus a nop at 0x1FF004 so empty slots get a real memory page), character texture buffers (`SetupCharTexBuf` etc., 0x202BB8…0x202D40, 0x1DC710, 0x1BA474), `DrawMarker` loops/guards (0x299xxx), `SetCommon` (0x130D10: slot loops and pad bitmaps).
- Slot 6 (normally the referee) is a wrestler in the 8-player matches, so these matches have **no referee**.

## 2. Match records

- `s_GameTypeTbl` (0x45AF60): 86 records × 32 bytes. +0 group, +1 max players, +2 position layout type, +4 rule type, +8 title string id, +0xC… six (slot, team, extra) byte triples. The table cannot grow, so two **unused records** are reused: **85** (copy of 49, max 8, "FATAL 4-WAY TORNADO TAG", teams of two) and **72** (copy of 27, max 8, "8-MAN BATTLE ROYAL", every wrestler its own team).
- Match rules (belt, referee flag…) come from the 64-byte rule table at 0x455DC0, **indexed by record number** (`GetDefRule`, 0x12CC90), so rules 85 and 72 are copies of 49 and 27.
- Menus: sub-menu lists are arrays of 12-byte items referenced by 20-byte descriptors at 0x45AD84…; new item lists live in a cave, descriptors (0x45AE38 LADDER, 0x45ADD4 SURVIVAL) point to them with count 6.
- The 8-player code paths trigger when the record's max-players byte is 8 (`IS8` macro in the generator). Flag `BRF` (0x113568) = group 7 (battle royal) selects the team tables.

## 3. Strings

`GetRCString` (0x12FD60) gets a hook that serves the new ids from a pointer table in a cave: 830 "7P", 831 "8P", 832 "FATAL 4-WAY TORNADO TAG", 833 "8-MAN BATTLE ROYAL". The pad label table `s_wresCtrlStrID` (0x468580) is relocated with 9 entries. The player-count list (`PlayerEntryNext`, 0x131D80) gets 7 PLAYERS and 8 PLAYERS lists (`base_patches.txt`); a hook at 0x133C40 narrows the row pitch to 24 px when the list has 8+ rows.

## 4. Position screen

`PositionSelectFrame` (0x1394F0…) and `PositionSelectWindowFrame` (0x13B4F0…) were grown (object size 0x250 → 0x2C8, arrays 7 → 9) by `remap_frame.py` / `remap_win.py`, which rewrite every field displacement in those methods. A new layout (type 5, 8 boxes) replaces the 6-box layouts (`tblPosSelectLayout`, 0x45BD10 + 5×0xC4), the pad popup has 9 choices and the box-to-pad "cycle select" is a hook on `ChangeDecision`.

The position layout orders the visible slots as 1–2, 3–4, 5–6, 7–8. Layout indices 5 and 7 trade positions, with directional links and popup anchors updated. Ladder's record-85 team bytes and `RT1` restoration table now pair slots 0/1, 2/3, 4/5 and 6/7; the display-only wrestler-select `FTAB` remains alternating for its native 2×2 containers. Survival retains eight separate teams.

The assignment helper removes the old popup guard rejecting player values 7/8 in slots 0–5. The existing eight-slot assignment helper still removes duplicate pad assignments. The position copy-in path now decodes `0x16/0x17` in all six sequence entries, as it already did for the extra two. Copy-out, wrestler-selector pad masks and label conversions already handle these encoded values in every slot. Execution checks move 7P/8P into each of the eight boxes, reopen positions, traverse both selection pages and verify the physical pad/label mapping.

`position_rows.py` grows `PositionVS` from `0x3C` to `0x40` bytes, storing a per-instance mode at `+0x3C`. Ordinary records use the original VS drawer. Records 85/72 with layout 5 replace that draw with a dark panel and four horizontal bands, using a stack-local native `CRectDraw` and the existing VS fade alpha. Ladder bands have four team colors; Survival bands are neutral. `tools/check_position.py` checks emitted geometry/navigation/team data and executes the constructor/draw helpers, including the ordinary-screen fallback.

The player-count menu retains its retail constructor and shared Show path. `position_popup.py` patches the assignment-popup frame scale at `0x13B8E0`. For custom popup layout 14 with seven/eight humans, the bar animation's Y scale is 1.9 instead of 1.34. Other popup frames retain native scale. The matching text/frame anchors are clamped to y=224–276, keeping the expanded popup away from the title and help bar while preserving the existing text, input and fades.

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

## 7. Eight-wrestler HUD

The retail HUD has only six `0x7C` plate records. Its eight-entry slot map does not allocate two more: indexing a seventh/eighth plate aliases global HUD state, including the count overlay. The patch therefore leaves all retail plate records untouched and allocates a private two-card sidecar for slots 7 and 8.

The sidecar shallow-clones already-loaded top-card draw objects while sharing texture resources read-only. Each private card occupies `0x1400` bytes and includes a name, matching backing, controller label, two progress sprites, five finisher-count sprites and six cloned body/damage layers. The draw helper draws the five colored body-part masks and omits the decorative base sprite to remove the extra translucent body backing. Names come from each slot's own model ID; width is capped at the native 190 units and backing geometry is recomputed for each side. Filled/empty finisher textures, progress and limb colors come directly from `g_pChar[6]` and `g_pChar[7]`. Two private animation objects provide finisher-ready feedback, and a decrease tracker restores the large center SmackDown effect when either extra wrestler consumes a finisher.

The `CSpriteCtrlGame2D` draw vtable entry at `0x47F05C` runs the retail draw once, then draws the two private cards. Retail matrix callers are untouched. Private sprites and fonts use the native fast draw paths. The private row is offset by 64 native units before scaling (`+1024` renderer units in frame mode or `+512` in interlaced fields). The exact incoming renderer offset is saved and restored. The finisher loop reloads its texture pointer and preserves its counter across draw calls, preventing an invalid read at `0x121688`.

`hud_scale.py` applies 75% scaling to the final two-vertex fast sprite/rectangle packets. A HUD-scoped flag and object-pointer membership checks identify card sprites, fonts, inline name rectangles and the private allocation. Other UI, timers and prompts are excluded. Both vertices are transformed about their screen corner using the original renderer origin and field-aware height; cached objects and UVs stay unchanged, preventing cumulative shrinking or the earlier normal/fast coordinate mismatch. Hooks at the native fast-draw return sites preserve the original stack-pop delay slots. Ordinary match cards are scaled too.

The retail controller-ID texture atlas only contains 1P–6P and COM. `hud_controller_labels.py` intercepts its draw at `0x23D114`: a genuine COM record uses the original sprite, while human pads 7/8 draw text in a temporary clone of the loaded card font at the native ID position. The scaler temporarily recognizes that stack font through `0x3B5FF4`; the pointer is cleared afterward. Input, COM flags and controller indices are not changed. This corrects the misleading COM labels after moving 7P/8P onto retail HUD cards.

`hud_lifecycle.py` hooks the native HUD destructor's ReleaseAllAnim call at `0x233DBC`. It destroys private animations, frees the private card block and clears owner/cache/draw state before tail-calling native ReleaseAllAnim with the original controller pointer. This prevents an address-reused HUD on rematch from accepting cached objects from the preceding match. Generated-code tests cover teardown, exact address reuse and repeated cleanup. Initial PCSX2 testing after this change was successful; this does not establish coverage of every rematch path or platform.

Damage colors follow the retail health thresholds and a 90-frame alpha triangle. State lives at `0x3B5FC0`; implementation and bounded cave assignments are isolated in `src/hud_patch.py`, `src/hud_names.py`, `src/hud_details.py` and `src/hud_scale.py`. `tools/check_hud.py` executes generated helpers with draw stubs that deliberately clobber temporary registers. It checks both cards, long names, body-layer selection, renderer-offset restoration, scaling of native/private packets in both field modes, and exclusion of unrelated UI. It does not verify actual graphics output.

## 8. Real hardware notes

- No patch writes below 0x100000; every patch is inside the loaded image.
- Data words written at runtime (flags, side buffer, temp copy) never share a 64-byte cache line with executed new code (checked), and nothing writes code at runtime.
- `tools/check_patch.py` verifies delay slots and branch targets of the new code.
- The ISO is a clone of the original; only the executable's sectors change (same size, same LBA 768396 in the USA dump).

## Reproducibility

The default generator produces an executable with SHA-1 `8bb216bb6e3ee37e184239a1b93d657b4b0eec9f` from the original `d8ef8451378be669184de04478a550c8a46d02d6`. Its PLAY-summary wrapper builds two compact four-name columns. Two private `MatchWrestler` pointers add slots 7/8 to the animated scene without growing the retail six-pointer `MatchWrestlerCtrl`; setup, motion start/stop and destruction are hooked explicitly. The maintainer has tested the current source in PCSX2, including the HUD presentation and a rematch session after the cleanup fix. Broader platform and regression testing remains welcome. Set `HCTP_HUD_PROTOTYPE=0` when running the generator to omit the sidecar HUD module for debugging. For chronological experiments and dead ends, see `DEV_LOG.md`.
