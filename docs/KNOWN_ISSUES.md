# Known issues and ideas

## Open
1. HUD health cards exist natively only for slots 1–6. The six records occupy `caSd5Game2D+0x4894..0x4B7B`; global animation state starts immediately at `+0x4B7C`. The eight-entry map at `+0x4C98` does not provide two more records.
   - **s52 failed:** fake plate 6 overwrote the HUD draw mode at `+0x4B7C`; fake plate 7's `+0x28` field overwrote the count at `+0x4C20`, explaining the missing HUD and repeated `5`.
   - **s62 experimental:** private cloned draw objects render names, synchronized finisher-count textures and retail-timed pulsing limb colors for slots 7/8; private animation state supplies finisher feedback without a second HUD object, data swap or second retail Action. Every cloned card layer uses the same 50% matrix path. The row bias is corrected from s61's mistaken 960 quarter-pixel units to 240 units (60 pixels). Runtime verification is pending.
2. The pre-match summary ("PLAY") screen lists 6 names.
3. No referee in the 8-wrestler matches (slot 6, the referee slot, is a wrestler). Matches still end by pin/finish; count-outs, DQ and submissions not exhaustively tested.
4. Computer slots 7/8 default to the same wrestler as slot 6 when not picked.
5. Elimination Chamber (4 pods, 2 wrestlers start in the ring) needs a new layout, see CONTRIBUTING.md.
6. **SmackDown-icons page of a wrestler panel (panel state 2) has no frame.** Seen in Survival and other modes. We first thought the original game draws it that way, but the maintainer reports it is introduced by this mod. Not investigated yet: compare against an unpatched game, then look at what the select-screen hooks (`scpin`, `cvt`, `cinit`, `cut`) and the grown `SelectWrestlerFrame` entries change for panels drawn by `SelectWrestlerDrawer`.
7. Only two match types use the 8-player flow (records 72 and 85). Two more unused records exist (13, 40).

## Fixed in s53
- ALL COM, 1 PLAYER and 6 PLAYERS now complete both wrestler-select screens in both new modes. COM panels share the lowest available human pad for the original chaining logic; a screen with no humans uses the native ALL-COM path.

## Parked
- Summary screen names: hooks for `CreateRosterTable` / `DrawRoster` did not show the extra names.


