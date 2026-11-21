# Running the patched game

You need the patched ISO from `build.py` (see the README), two multitaps and eight pads.

## PCSX2 (Windows / macOS / Linux)

Tested with PCSX2 v2.8.2 on macOS.

1. **Settings → Controllers.** Set the controller type of Port 1 and Port 2 to a **Multitap** (enable "Multitap" on both ports). You get slots 1A–1D and 2A–2D = 8 pads. Bind all eight to real gamepads. (Keyboard-only: you can bind the extra pads to any keys, but you need a way to press buttons on eight pads.)
2. System → Start File → choose your patched ISO. (Use *Shut Down Without Saving*, then start the file, if PCSX2 keeps resuming an old save state.)
3. In the player-count list, 8 PLAYERS is enabled only if the game sees eight pads.

Debug extras: Settings → Advanced → enable **PINE** if you want to use the scripts in `tools/` (`pine.py`, `monitors/`). The socket is `$TMPDIR/pcsx2.sock` on macOS.

## Android emulators

The patched ISO also ran in an Android PS2 emulator (tested by the author). Multitap support and eight connected controllers are needed for 8 PLAYERS to be selectable.

## Real PS2

The patch is plain executable changes; no emulator features are used. It was tested on a real PS2 with two multitaps.

- The disc image is a **dual-layer DVD (DVD9, about 4.5 GB)**. Easiest way to boot it: **Open PS2 Loader (OPL)** on a softmodded console, image on USB, SMB share or an internal HDD, in the `DVD` folder, named like `SLUS_207.87.WWE SmackDown Here Comes the Pain.iso`.
- Burning it to a DVD+R DL is not recommended: it needs the original layer-break position and a way to boot burned discs.
- Plug a multitap in **both** controller ports and four pads into each. The player-count list enables options only up to the number of pads found.

## Playing an 8-player match

1. Exhibition → pick the category **LADDER** and choose the last item **FATAL 4-WAY TORNADO TAG**, or pick **SURVIVAL** and choose the last item **8-MAN BATTLE ROYAL**.
2. Choose **1–8 PLAYERS** or **ALL COM**. ALL COM, 1, 6 and 8 players are confirmed working in both new modes. The temporary s71 player-count redesign was reverted in s72.
3. **Position screen:** eight boxes. In s70, read rows left to right: 1–2, 3–4, 5–6, 7–8. Assign which pad plays each box. Ladder has four colored team rows (one pair per row); Survival has neutral row bands and eight separate competitors. The new row presentation awaits runtime confirmation.

   s71 allows 7P/8P in any box. Moving a pad clears its old box to COM; assign displaced pads before choosing Continue. The assignments are preserved across both wrestler-selection pages and when reopening the position screen.

   s72 expands the assignment popup frame for seven/eight human players so the 1P–8P and COM choices have room. Popup anchors stay below the title and above the help bar. This appearance needs runtime confirmation.
4. **Wrestler select, screen 1:** slots 1–4 pick. Confirm.
5. **Wrestler select, screen 2:** slots 5–8 pick. Wrestlers chosen on screen 1 are not in the grid anymore. Cancel on screen 2 goes back to screen 1.
6. Stage, rules, play.

On the PLAY screen, the current patch should show all eight animated wrestlers and all eight names in two compact columns.

The confirmed s68 layout places complete private cards for wrestlers 7 and 8 below the top two HUDs, including names, controller labels, body/damage, finisher progress and counts. The s69 candidate makes all cards 75% size, tightens the top-row spacing and removes the extra body backdrops. s72 fixes the false COM text for human controllers 7/8 in retail cards; control assignments are unchanged. These refinements await runtime testing; the eight-name PLAY screen remains unchanged.

## If something breaks

- Tell which screen it happened on, the repository commit, which emulator/console you used, and whether the ISO was built from the unmodified dump. The s73 build prints executable SHA-1 `8bb216bb6e3ee37e184239a1b93d657b4b0eec9f`.
- s73 includes a candidate fix for a crash when leaving the ring after rematch. Boot it fresh, rematch, then test Square/J to exit the ring. Runtime confirmation is pending.
- Try `python3 tools/check_patch.py` on your generated patch (needs `--keep-patch`).
