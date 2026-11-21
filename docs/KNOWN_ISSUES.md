# Known issues and ideas

## Open

- **Rematch ring-exit crash (s72).** User reproduced a crash on Square/J after rematch. The first logged game fault was `PC=0x14B090`, load address `0x1C`, followed by PC 0 faults and a host CPU-thread segmentation fault. s73 adds missing private HUD teardown to prevent stale cache reuse; this is a candidate fix pending the same runtime test.

- **s72 assignment-popup frame and HUD labels need runtime confirmation.** The 1P–8P / COM popup has a taller frame and bounded position. Human pads 7/8 should show the right text on every retail HUD card; real COMs keep COM labels. The mistaken s71 count-menu redesign is reverted. The any-team assignment fix remains.

- **s70 position rows need runtime testing.** Verify the 1–2 / 3–4 / 5–6 / 7–8 ordering, D-pad movement, popups and background layering in both eight-player modes. Ladder now pairs teammates by row; Survival keeps eight singles. Ordinary position screens use the retail VS draw.

1. **s69 HUD refinements need runtime testing.** The user confirmed s68 names and placement, then requested smaller HUDs, closer top rows and removal of translucent pieces above the extra body indicators. s69 scales all cards to 75%, reduces row spacing and omits the private decorative body backdrops. Verify readable names, consistent layer sizes, damage changes and finisher consumption in both eight-player modes.
2. The pre-match PLAY screen is fixed: all eight names and all eight animated wrestlers are visible.
3. No referee in the 8-wrestler matches (slot 6, the referee slot, is a wrestler). Matches still end by pin/finish; count-outs, DQ and submissions not exhaustively tested.
4. Computer slots 7/8 default to the same wrestler as slot 6 when not picked.
5. Elimination Chamber (4 pods, 2 wrestlers start in the ring) needs a new layout, see CONTRIBUTING.md.
6. **SmackDown-icons page of a wrestler panel (panel state 2) has no frame.** Seen in Survival and other modes. We first thought the original game draws it that way, but the maintainer reports it is introduced by this mod. Not investigated yet: compare against an unpatched game, then look at what the select-screen hooks (`scpin`, `cvt`, `cinit`, `cut`) and the grown `SelectWrestlerFrame` entries change for panels drawn by `SelectWrestlerDrawer`.
7. Only two match types use the 8-player flow (records 72 and 85). Two more unused records exist (13, 40).

## Fixed
- ALL COM, 1 PLAYER and 6 PLAYERS now complete both wrestler-select screens in both new modes. COM panels share the lowest available human pad for the original chaining logic; a screen with no humans uses the native ALL-COM path.

- The PLAY screen now uses two compact four-name columns and two private `MatchWrestler` objects for slots 7/8. All eight names and animated wrestlers were confirmed by the user.
- The in-match HUD now supports all eight wrestlers. Cards 7/8 provide live body/damage, finisher-count and finisher-consumption feedback without running a second retail HUD update.


