# Contributing

Contributions are welcome: bug fixes, new 8-player match types, documentation, test reports.

## Getting started

1. Build the patch and play it: [README](README.md), [docs/RUNNING.md](docs/RUNNING.md).
2. Read how the patch works: [docs/HOW_IT_WORKS.md](docs/HOW_IT_WORKS.md).
3. Set up Ghidra on your own copy of the game: [docs/GHIDRA.md](docs/GHIDRA.md).
4. Pick something from [docs/KNOWN_ISSUES.md](docs/KNOWN_ISSUES.md) or the list below.

Rules:
- **Never commit game data**: no ISO, no `SLUS_207.87`, no Ghidra project or exported C, no generated patch lists. `.gitignore` already blocks them.
- Changes go into the generator (`src/gen_patch.py`), not into hand-edited patch files. `build.py` must still produce a deterministic executable. If your change alters the output, update the expected SHA-1 in `build.py` and say so in the pull request.
- Run `python3 tools/check_patch.py SLUS_207.87 patch.txt` (patch from `--keep-patch`) before opening a pull request. It checks that no patch touches a live library function.
- Say in the pull request **where you tested**: PCSX2 version, other emulator, or real PS2. Say what you did **not** test.

## Wanted work

| Area | What | Difficulty |
| --- | --- | --- |
| Select screens | Make fewer than 8 humans and ALL COM work in the two 8-player modes ([details](docs/KNOWN_ISSUES.md)) | medium |
| HUD | Health cards for wrestlers 7 and 8 | hard |
| PLAY summary | List all 8 names | medium |
| Referee | Optional referee in 8-wrestler matches | medium |
| More modes | Other match types with 8 wrestlers (tag, triple threat, hardcore…): each needs a free match record, a rule entry and a menu item | easy–medium |
| Elimination Chamber | See below | very hard |
| Testing | Real PS2 reports, other emulators, other loaders | easy |

## Adding a simple mode

A new mode is: a free record in `s_GameTypeTbl` (unused ones: 13, 40), a copy of the source mode's entry in the rule table (indexed by record number, otherwise belts and other props are missing), a title string id, and a menu item list. The 8-player code triggers on "record max players == 8". Look at how records 85 and 72 are made in `src/gen_patch.py` and in the HOW_IT_WORKS document. Modes whose group or team logic differs from LADDER (teams of two) and SURVIVAL (everyone alone) may need another entry in the team tables (`BRF` flag).

## The hard one: Elimination Chamber

This is the biggest open question. It has not been investigated yet, so what follows are **ideas and things to check, not findings**.

### The problem

The Chamber is built around four pods and a small ring. In the original game two wrestlers start in the ring and the others wait in the pods until a timer releases them one by one. Eight wrestlers do not fit that: there are only four pods. That needs three kinds of change:

1. **Layout**: where do the extra wrestlers start and wait?
2. **Match logic**: who is released when, and how elimination order, pinfall and the winner work with 8.
3. **Everything the other 8-player modes already needed**: 8 characters, 8 pads, select screens, cameras, HUD.

### Layout ideas (suggestions welcome)

- **A. 4 in the ring, 4 in the pods.** Two teams of two (or four singles) start in the ring, the four pods hold the rest. Fewest new places to invent: the pod logic stays at four. Ring start positions need a new row in the start-position tables.
- **B. 2 in the ring, 4 in pods, 2 outside waiting.** Closest to the original. The last two wait outside the cage or behind the pods and enter when pods are empty (like a royal rumble entry). Needs a new waiting state and an entrance path.
- **C. Two wrestlers per pod.** Eight wrestlers, four pods, two per pod. The pod opens with both inside and they come out together as a tag. Needs the pod to hold two characters (collision, camera, door animation).
- **D. Elimination Chamber for 6 plus spectators.** Keep the original 6 and let players 7 and 8 enter later as replacements. Least work, but not really an 8-man match.

### What to look at first

- The match record and rule entry of the Elimination Chamber in `s_GameTypeTbl` and the rule table, to find the game type that handles pods and release timing.
- `SetGameStartPos`: start positions are looked up per team in rows of three slots (a fourth member of a team reads the next team's row, see the dev log).
- The pod/cage objects in the stage: how many, how a wrestler is bound to a pod, how the release is triggered.
- How the Survival / battle royal modes bring wrestlers in and out, as a model for a waiting list (search the decompile for "Royalrumble"; the one function we know by that name, `CSpriteCtrlGame2D::EntryRoyalrumbleAtCom`, is HUD code).
- Camera and `DrawMarker` code that assumes a fixed number of players.

If you try something, please write it up in an issue, even if it fails: a negative result saves the next person days.

## Reporting bugs

Open an issue with: build used, emulator or console, match type, number of humans, and what you saw. For select-screen problems the monitor `tools/monitors/selmon.py` (PCSX2 with PINE enabled) produces a log that makes bugs much easier to find.
