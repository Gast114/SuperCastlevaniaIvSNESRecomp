# Super Castlevania IV Enhanced

An unofficial enhanced version of **Super Castlevania IV** (USA), with native
desktop play, widescreen, optional HD artwork, save states, rewind, and tools
for editing levels, monsters and character graphics.

The original game logic remains the foundation. The project uses a native
recompilation built on [snesrecomp](https://github.com/RetroPortingToolKit/snesrecomp),
combining generated C with the framework's correctness interpreter. The level
and monster tools share a separate desktop application called **Castlevania Studio**.

The repository and executable retain the technical name
`SuperCastlevaniaIvSNESRecomp`. The project-specific framework dependencies are
pinned in [Gast114/snesrecomp-sciv](https://github.com/Gast114/snesrecomp-sciv)
and [Gast114/recomp-ui](https://github.com/Gast114/recomp-ui).

> **You must legally own a copy of the game.** No ROM data is distributed with
> this project, in the repository or in any release. The recompiled C is
> generated locally from your own copy and is never committed.

## Current status — 8 November 2026

**Playable development version, with Windows as the actively used desktop
environment.** The game boots from the original USA ROM. The editor supports
building and playing custom rooms. A complete HD conversion and a packaged
public release are still in progress.

`main` is the primary branch for the current usable project. Work in progress
can use separate branches; completed changes should reach `main`. The existing
`dev` branch is retained for continuity.

| Component | Available now | Current limits |
|---|---|---|
| Desktop game | Native video, audio, keyboard/controller input, fullscreen and settings | Full-campaign validation is ongoing; other desktop platforms are not claimed as validated |
| Widescreen | Optional 16:9 scene rendering at 342×224 with the original HUD safe area | Mode7 rooms, bosses and scripted camera boundaries need continued full-game checking |
| Saves and convenience | Save slots with browser, rewind, pause and fast-forward | Run-ahead is unsupported and falls back to normal execution |
| New Game+ | The original harder second quest, selectable from the title menu | Uses the original quest rules |
| HD graphics | Switchable artwork packs, separate layer controls and 2×/4×/6×/10× rendering | Artwork coverage is partial; missing replacements use original graphics; artwork packs stay local |
| Character workshop | Collect/edit complete poses, live PNG reload, anchors and movement/damage settings | Complete pose coverage across the game is unverified; Simon's HD artwork experiments are paused |
| Level editor | Catalog of 68 original sections, supported map imports, custom rooms, mixed graphics, terrain, collision, objects, exits and F5 playtests | Full vertical/Mode7 map import, arbitrary original scene scripts and finished campaign/mod export remain open |
| Monster workshop | Native previews, editable PNGs, Normal/NG+ comparisons and placement-linked values; integrated with the level editor | Action and pose assignments are incomplete; a general AI behavior editor is not implemented |
| Boss placement | Independent free boss instances and prepared classic encounters; original attacks and sound effects | Native movement constraints remain; classic encounters allow one active encounter; additional instances cost processing time |

The latest code changes fix free-boss sound effects, preserve audio while
switching boss contexts, and improve editor selection and playtest startup.
These are targeted fixes, not a claim that every original room, boss and custom
combination has been fully tested.

### What this public repository contains

The repository contains source code, editor tools, HD import/build recipes and
documentation. **There is currently no published GitHub Release or ready-to-play
download.** Build the game locally with your own ROM using the instructions below.
The release workflow is manually triggered; the presence of that workflow does
not mean a release build has been run or validated.

ROMs, generated game code, local builds, saves, collected graphics and local
artwork packs are excluded from Git. The locally installed Stage 01 HD work
therefore does not arrive with a clone of this repository.

Additional work exists outside the committed source: a WebAssembly browser
version with touch controls has been deployed on a private home-network server,
and local landscape-AI tools are experimental. **Their source and setup are not
yet published in this repository.** The landscape tools have not reached the
intended artwork quality. The browser version has not had complete campaign or
physical controller/touch-device validation.

### Tools and documentation

| Task | Entry point | Guide |
|---|---|---|
| Edit levels and place monsters/bosses | `Level_Editor_starten.cmd` | [Level editor](docs/LEVEL_EDITOR.md) |
| Preview monsters and edit their graphics | `Gegner_Werkstatt_starten.cmd` | [Monster workshop](docs/ENEMY_WORKSHOP.md) |
| Import replacement artwork | `HD_Import_starten.cmd` | [HD import](docs/HD_IMPORT.md) |
| Understand gameplay and convenience features | In-game Escape menu | [Gameplay tools](docs/GAMEPLAY_TOOLS.md) |
| Find everyday instructions in German | `MERKHILFE.md` | [User notes](MERKHILFE.md) |

Some detailed guides record earlier experiments and settings. This overview
describes the current scope; artwork examples in older guides do not imply
that a complete replacement pack is distributed.

## Desktop features and shortcuts

| Feature | Default shortcut |
|---|---|
| Quick-load slot 1 | `F1` |
| Quick-save slot 1 | `Shift+F1` |
| Load slots | `F1`–`F6`, `F11`–`F12`, `F9`–`F10` |
| Save slots 1–10 | `Shift+F1`–`Shift+F10` |
| Save-state browser | `F7` |
| Rewind browser | `F8` |
| Fast-forward | `Tab` |
| Pause | `P` |
| Pause/settings menu | `Escape` |
| Fullscreen | `Alt+Enter` |

The launcher exposes widescreen, SNES display aspect, renderer, shader,
frame-blending, audio, controls and run-ahead settings. Shortcuts can be
changed in `config.ini`; controller bindings live in `keybinds.ini`.
During play, `Escape` opens a controller-friendly menu for resuming, changing
the view mode or volume, quick-saving/loading slot 1, and resetting the game.

Run-ahead is currently unsupported for this port: its execution continuation
is not yet included in rollback snapshots. A saved nonzero preference now
safely falls back to normal execution instead of speculating with incomplete
state and hanging at startup.

### NEW GAME+ title entry

The native title menu offers **START**, **NEW GAME+**, **CONTINUE** and
**OPTION**, using the game's font, heart cursor and confirmation blink.
Use Up/Down and Start to select an entry.

NEW GAME+ starts the original game's harder second playthrough, the same quest
flag the cartridge sets after its ending. Native difficulty and additional
enemy spawns apply from the first room. START begins the ordinary first quest.
The quest follows save states, rewind and the game's own continue/password
logic. Reset from Escape to return to the title.

Regression test (Lua build required):
`python tools/test_campaign2.py --build-dir build-lua --rom PATH`.
It compares START and NEW GAME+ against the native ending restart, including
room difficulty, enemy spawning, save/load and reset.

### Switchable HD graphics

The current skeleton replacement pilot and resolution-independent Photoshop
import window are described in [docs/ENEMY_HD.md](docs/ENEMY_HD.md) and
[docs/HD_IMPORT.md](docs/HD_IMPORT.md). Start `HD_Import_starten.cmd` for pose
templates, previews and installation in both local player folders. The latest
rewind, native second-quest and bridge fixes are recorded in
[docs/GAMEPLAY_TOOLS.md](docs/GAMEPLAY_TOOLS.md).

**Escape > HD graphics > HD graphics enabled** switches between original
and replacement artwork. Backgrounds, text/HUD and sprites have separate
switches. Choose a pack and 2x/4x/6x/10x output; missing artwork falls back to
native pixels. 10x accepts 80x80 replacements per original 8x8 tile for a 4K
output target. Pack artwork resolution and output resolution are independent.
The current renderer preserves native silhouettes; this is an initial HD
replacement path, not a complete remaster.

**Collect graphics while playing** exports to `hd_dump/`. After playing,
`python tools/hd/hd_pipeline.py --build build` builds a replacement pack.
`tools/hd/hd_tiles.py` exports editable tiles and builds separate art variants.
`tools/hd/hd_motifs.py` imports painted crops with tile-neighborhood guards;
the local Block 1-1 material pilot is `pilot-1-1-painted-v2` in the pack menu.
It contains partial masonry, stairs and rock/foliage studies, not the entire stage.
Setup, controls, limitations and local sprite-sheet sources:
[docs/HD_PIPELINE.md](docs/HD_PIPELINE.md).

### Character workshop: editable complete body frames

**Escape > Character workshop > Character gameplay** exposes settings for the
selected character: walk/crouch speed, jump strength, gravity, air speed and
steering, maximum fall speed, each whip tier's attack/dangling damage, dagger,
axe, holy-water and cross damage, whip link counts, and subweapon heart costs.
Changes take effect when play resumes. Click **Save gameplay** to keep them in
that character's `character.json`; **Reset to Simon defaults** resets the live
values (save afterwards to keep the reset). Disabling the pack restores native
gameplay. Existing manifests without a `gameplay` object use native defaults.

Speeds/strength/gravity use percentages of Simon's original values. Damage uses
internal attack points, not HUD health bars. Whip length is limited to the
native 1–7-link range; ring-swing rope length is unchanged. Crouch speed also
affects the native slow movement used in mud. No PNG edits or ROM-file writes
are involved. Byte-checked overrides target the runtime cartridge copy.

Regression test: `python tools/test_character_tuning.py --rom PATH` compares
default, tuned and disabled character profiles in isolated folders.

Play to collect poses, then open **Escape > Character workshop** and click
**Create character copy**. Edit `characters/custom-1/body.png` under the game's
working directory (normally beside the executable). Save as RGBA PNG without
resizing: the sheet is 768 x 3072, with eight 96 x 96 cells per row. Each cell
is a complete, independent body pose. Changes reload while playing.

The workshop previews poses, mirrors the preview, overlays the original Simon,
and adjusts each pose's origin. Green marks the engine origin, not the feet;
gold is a hand-placement guide. **Save anchors** persists these adjustments.
The whip, attacks, hitboxes and movement still use the original game logic;
the hand guide does not move the whip. This is a visual character-pack system,
not a new gameplay-character system.

Walking, jumping, attacking and stairs collect additional poses into
`characters/simon-template`. Click **Add newly collected poses** to copy only
missing poses into your character, preserving existing artwork. Back up your
custom folder before editing. Do not edit the automatically generated template.
The preview's playback cycles collected poses, not the game's animation timing.

`character.json` maps stable exact pose IDs to cells and anchors. Keep IDs and
cell assignments intact; the display name and pose labels can be edited.
Packs are selected in the workshop. Untick **Use character pack** to restore
native Simon immediately. Older `simon_spritesheet.png` / `simon_full_frames.png`
files are preserved but no longer loaded by this system.

The renderer replaces only exactly identified body sprites, using normal scene
priority, windows and brightness. It never writes edited pixels back to shared
SNES tiles. Arbitrary RGB colors are supported; SNES color-math effects still
use 5-bit channels. Alpha below 128 is transparent; fractional alpha is not
blended. Use the new renderer. Screen-edge clipping happens after replacement,
so jumping partly above the screen does not disable the character. Unknown
poses or missing sprite entries fall back to native Simon rather than guessing.
The atlas supports 256 poses;
full-game pose coverage is not yet verified. Generated art stays local and is
git-ignored; no ROM-derived artwork is distributed.

## ROM identity

| | |
|---|---|
| File | `org - Copy.sfc` |
| Publisher | — |
| Developer | — |
| Year | — |
| Mapping | lorom |
| Region | USA (North America) |
| Coprocessor | none |
| CRC32 | `b64ffb12` |
| SHA-256 | `0ef6f4cce5a2273fa49fe1ce724e0048a8e39c91da6b00dbb693fe1ba909177d` |

`tools/regen.sh` refuses to run against anything else, so a mismatched
revision fails immediately instead of producing subtly wrong output.

## Build

```sh
git submodule update --init --recursive
bash tools/regen.sh --rom /path/to/org - Copy.sfc
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build -j
```

The ROM does not have to live in the repository — keeping it on your own
drive is the better habit, and `SNESRECOMP_ROM` sets the path once for a
shell. `tools/regen.sh` also finds `org - Copy.sfc` at the repo root if you
prefer that; `.gitignore` blocks it from ever being committed either way.

`tools/regen.sh` verifies the ROM, generates `src/gen/*.c`, and re-syncs
`recomp/funcs.h`. Re-run it whenever you change anything under `recomp/`.

## Run

```sh
./build/SuperCastlevaniaIvSNESRecomp                     # launcher picks the ROM
./build/SuperCastlevaniaIvSNESRecomp /path/to/org - Copy.sfc # or name it and skip the launcher
```

With no ROM on the command line the build opens the recomp-ui launcher: a ROM
picker with a verification badge, plus display / audio / input settings. Your
choice is cached in `rom.cfg` beside the executable, so the next launch opens
on it and "Skip launcher on boot" makes it immediate. If the launcher is not
built in (`--no-recomp-ui`), the host falls back to a native file picker.

Either way the ROM is checked against the digests above before anything boots
— a dump that could not have produced this build is refused at the door rather
than mis-executing ten frames in.

## Regression tests

The tests in `tools/` need your ROM and Pillow. They run the game hidden in
throwaway folders under the build directory and never touch your config,
saves or character packs:

```sh
python tools/test_campaign2.py --rom PATH --build-dir build
```

`--build-dir` accepts a single-config (Ninja) build directory or a
multi-config one containing `Release/`; it defaults to `build/Release`, then
`build`. The other suites (`test_startup`, `test_character_pack`,
`test_character_stairs`, `test_character_tuning`) take the same arguments.

## Automation (Lua over TCP)

A build configured with `-DSNESRECOMP_ENABLE_LUA=ON` serves the framework's
BizHawk-style Lua bridge (`snesrecomp/docs/LUA_TCP.md`) when
`SNESRECOMP_LUA_PORT` is set. `tools/sciv_play.py` drives such a build: it
starts an isolated, paused session and advances the game only on command,
so every step is reproducible.

```sh
cmake -S . -B build-lua -G Ninja -DCMAKE_BUILD_TYPE=Release -DSNESRECOMP_ENABLE_LUA=ON
cmake --build build-lua
python tools/sciv_play.py start --build-dir build-lua --widescreen
python tools/sciv_play.py press Start 2      # hold buttons for N frames
python tools/sciv_play.py wait 240           # advance N frames
python tools/sciv_play.py state              # JSON: frame and named RAM fields
python tools/sciv_play.py shot frame.png     # last rasterized field
python tools/sciv_play.py save 1 / load 1 / reset / stop
```

The game commands behind `shot`, `save`, `load` and `reset` live in
`src/lua_commands.c`. Ordinary builds compile none of this.

## Layout

| Path | What lives there |
|---|---|
| `recomp/` | Analysis input: `bank*.cfg`, `symbols.toml`, generated `funcs.h` |
| `rom_identity.txt` | ROM digests — read by the build, `tools/regen.sh` and CI |
| `src/` | Host code you own: `main.c`, `game_rtl.c` |
| `src/gen/` | Generated C. Never committed — regenerate locally |
| `snesrecomp/` | Framework submodule (owns `lib/recomp-net`, `lib/retcomm-rbengine`) |
| `tools/` | `regen.sh` — the ROM → C pipeline |
| `scripts/` | `package_release.sh` — player-facing zip |
| `framework_pins.txt` | Exact framework commits this project was scaffolded against |

## Development

The game already boots and runs; this is beyond the initial port scaffold.
Current work focuses on gameplay correctness, HD artwork integration and
the level/monster tools. See the status table above for remaining limitations.

Game-specific execution code lives in `src/game_rtl.c`; analysis inputs and
symbols live under `recomp/`. Never edit generated `src/gen/` files by hand.
Fix the analysis/configuration or framework and regenerate from your own ROM.
Generated game code and ROM-derived artwork must stay out of commits and releases.

## Multiplayer

Single player.

## License

This project's own source is under the license in `LICENSE`. The framework
carries its own terms — see `snesrecomp/LICENSE` and
`snesrecomp/THIRD_PARTY_ATTRIBUTION.md`. Neither covers the game data, which
is not distributed here.
