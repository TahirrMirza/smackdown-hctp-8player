# Known issues and ideas

## Open

- No referee in the 8-wrestler matches (slot 6, the referee slot, is a wrestler). Matches still end by pin/finish; count-outs, DQ and submissions not exhaustively tested.
- Computer slots 7/8 default to the same wrestler as slot 6 when not picked.
- Elimination Chamber (4 pods, 2 wrestlers start in the ring) needs a new layout, see CONTRIBUTING.md.
- **SmackDown-icons page of a wrestler panel (panel state 2) has no frame.** Seen in Survival and other modes. We first thought the original game draws it that way, but the maintainer reports it is introduced by this mod. Not investigated yet: compare against an unpatched game, then look at what the select-screen hooks (`scpin`, `cvt`, `cinit`, `cut`) and the grown `SelectWrestlerFrame` entries change for panels drawn by `SelectWrestlerDrawer`.
- Only two match types use the 8-player flow (records 72 and 85). Two more unused records exist (13, 40).

## Fixed in the current source

- Private HUD resources are released on native HUD destruction to prevent stale objects across rematches. An earlier implementation crashed when leaving the ring after rematch; initial maintainer testing after the cleanup fix was successful. Further repeated-rematch testing on other emulators and real hardware is welcome.
- All eight HUD cards use 75% scale, with compact top-row spacing and complete names, damage and finisher displays. Human pads 7/8 show their actual controller labels in every card.
- Position rows read 1–2 / 3–4 / 5–6 / 7–8. Controllers 7/8 can be assigned to any box, and the assignment popup fits all nine choices.
- ALL COM, 1 PLAYER and 6 PLAYERS now complete both wrestler-select screens in both new modes. COM panels share the lowest available human pad for the original chaining logic; a screen with no humans uses the native ALL-COM path.

- The PLAY screen now uses two compact four-name columns and two private `MatchWrestler` objects for slots 7/8. All eight names and animated wrestlers were confirmed by the user.
- The in-match HUD now supports all eight wrestlers. Cards 7/8 provide live body/damage, finisher-count and finisher-consumption feedback without running a second retail HUD update.


