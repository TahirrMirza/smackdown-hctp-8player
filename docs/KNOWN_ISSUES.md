# Known issues and ideas

## Open
1. **Fewer than 8 human players or ALL COM does not work.**
   - Observed: with 1 player or ALL COM only the first four wrestlers get picked, then the match starts with defaults; with 6 players the second select screen hangs after the human panels are done. Only a full eight humans works.
   - Cause (analysis): the game normally lets a human "chain" through the computer-controlled panels of the select screen (`SelectWrestlerFrame::NextSearch`, panels linked by a "type" value computed in `ConvertPositionData`). In the 4+4 split the computer panels of screen 2 (and the two extra slots held in a side buffer) get no human to drive them, so they never start.
   - Idea: when screen 2 contains computer panels, give them the same type value as the lowest human pad on that screen (or hand the first panel to the lowest human pad), and never skip the screen. Needs live inspection of the `SelectWrestlerOne` objects (vtable `0x47F670`: +0x18 idx, +0x1C select type, +0x20 pad, +0x24 type, +0x28 state); `tools/monitors/selmon.py` logs them.
   - An experiment (skip screen 2 when it only holds computer panels, keep slots 7/8 always active) was tried and did **not** fix this, so it is not part of the patch.
2. HUD health cards exist only for slots 1–6.
3. The pre-match summary ("PLAY") screen lists 6 names.
4. No referee in the 8-wrestler matches.
5. Computer slots 7/8 default to the same wrestler as slot 6 when not picked.
6. Only two match types use the 8-player flow (records 72 and 85). Two more unused records exist (13, 40).

## Parked
- Health cards for slots 7 and 8: a vertex-transform hook on `CBaseDraw2D::MulMatrix` can scale the whole HUD; a second draw pass showed glitches.
- Summary screen names: hooks for `CreateRosterTable` / `DrawRoster` did not show the extra names.

## Not an issue
- The SmackDown-icons page of a panel has no frame: that is how the game draws it.
