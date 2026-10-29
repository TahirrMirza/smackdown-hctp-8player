# Known issues and ideas

## Open
1. **Fewer than 8 human players or ALL COM does not work.**
   - Observed: with 1 player or ALL COM only the first four wrestlers get picked, then the match starts with defaults; with 6 players the second select screen hangs after the human panels are done. Only a full eight humans works.
   - Cause (analysis): the game normally lets a human "chain" through the computer-controlled panels of the select screen (`SelectWrestlerFrame::NextSearch`, panels linked by a "type" value computed in `ConvertPositionData`). In the 4+4 split the computer panels of screen 2 (and the two extra slots held in a side buffer) get no human to drive them, so they never start.
   - Idea: when screen 2 contains computer panels, give them the same type value as the lowest human pad on that screen (or hand the first panel to the lowest human pad), and never skip the screen. Needs live inspection of the `SelectWrestlerOne` objects (vtable `0x47F670`: +0x18 idx, +0x1C select type, +0x20 pad, +0x24 type, +0x28 state); `tools/monitors/selmon.py` logs them.
   - An experiment (skip screen 2 when it only holds computer panels, keep slots 7/8 always active) was tried and did **not** fix this, so it is not part of the patch.
2. HUD health cards exist only for slots 1–6. The HUD is built for six plates (fixed position tables at 0x4668F0…0x4669F0, per-plate arrays and `< 6` loops in `CSpriteCtrlGame2D`). Shrinking it works; a second row for slots 7/8 failed (second HUD object breaks character/audio loading; running `caSd5Game2D::Action` twice corrupts game state). See DEV_LOG sections 19, 20, 22.
3. The pre-match summary ("PLAY") screen lists 6 names.
4. No referee in the 8-wrestler matches (slot 6, the referee slot, is a wrestler). Matches still end by pin/finish; count-outs, DQ and submissions not exhaustively tested.
5. Computer slots 7/8 default to the same wrestler as slot 6 when not picked.
6. Elimination Chamber (4 pods, 2 wrestlers start in the ring) needs a new layout, see CONTRIBUTING.md.
7. **SmackDown-icons page of a wrestler panel (panel state 2) has no frame.** Seen in Survival and other modes. We first thought the original game draws it that way, but the maintainer reports it is introduced by this mod. Not investigated yet: compare against an unpatched game, then look at what the select-screen hooks (`scpin`, `cvt`, `cinit`, `cut`) and the grown `SelectWrestlerFrame` entries change for panels drawn by `SelectWrestlerDrawer`.
8. Only two match types use the 8-player flow (records 72 and 85). Two more unused records exist (13, 40).

## Parked
- Health cards for slots 7 and 8: a vertex-transform hook on `CBaseDraw2D::MulMatrix` can scale the whole HUD; a second draw pass showed glitches.
- Summary screen names: hooks for `CreateRosterTable` / `DrawRoster` did not show the extra names.


