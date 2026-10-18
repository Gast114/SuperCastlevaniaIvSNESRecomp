# Super Castlevania IV Recomp

A native recompilation of **Super Castlevania IV** (USA), built on
[snesrecomp](https://github.com/RetroPortingToolKit/snesrecomp).

This repository pins a project-specific framework branch in
[`RasmusKarlsson/snesrecomp-sciv`](https://github.com/RasmusKarlsson/snesrecomp-sciv)
for the native widescreen and Dear ImGui host integration that has not yet
been upstreamed.

The original 65816 program runs through a hybrid of generated native C and
the framework's correctness interpreter, with native desktop video, audio,
input, saves, save states, rewind and optional 16:9 rendering.

> **You must legally own a copy of the game.** No ROM data is distributed with
> this project, in the repository or in any release. The recompiled C is
> generated locally from your own copy and is never committed.

## Status

Playable from a clean boot. Reset/NMI scheduling, including SCIV's nested NMI
semaphore, is supported and the generated native execution path is enabled by
default. The 16:9 path renders real 342x224 PPU scene data while retaining the
authored 256-pixel HUD safe area. Full-game widescreen validation—especially
Mode 7 rooms, bosses and scripted camera boundaries—is ongoing.

## Desktop features and shortcuts

| Feature | Default shortcut |
|---|---|
| Quick-load slot 1 | `F1` |
| Quick-save slot 1 | `Shift+F1` |
| Load slots 1–10 | `F1`–`F10` |
| Save slots 1–10 | `Shift+F1`–`Shift+F10` |
| Save-state browser | `F11` |
| Rewind browser | `F12` |
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

NEW GAME+ is intended to select the original game's harder second playthrough
after completion. Wiring that second-quest state is still pending: the current
entry continues to load the earlier single-room sandbox from `src/campaign2.c`.
START launches the original campaign. Reset from Escape to return to the title.

Regression test (requires Pillow): `python tools/test_campaign2.py --rom PATH`.
It checks both START choices, OPTION, empty-room rendering and jumping/landing.

### Switchable HD graphics

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

## Porting from here

The scaffold stops where the game-specific work starts. In rough order:

1. **Make it boot.** `src/game_rtl.c` holds the frame driver. The generic
   LLE-first shape is there; a real title usually needs a frame boundary and
   NMI delivery that understand its own main loop. This is the bulk of the
   work.
2. **Name things.** Add entries to `recomp/symbols.toml` as you identify
   routines, then re-run `tools/regen.sh`. Set `emit = true` to promote one
   into ahead-of-time codegen; leave it false to keep it interpreted.
3. **Resolve dispatch misses.** After every run, deal with unresolved
   indirect targets before anything else — they are the reason a port
   diverges, and they are cheap to fix early.
4. **Never synthesise a result** to get past uncovered code, and never edit
   `src/gen/` by hand. Fix the config or the framework and regenerate.

## Multiplayer

Single player.

## License

This project's own source is under the license in `LICENSE`. The framework
carries its own terms — see `snesrecomp/LICENSE` and
`snesrecomp/THIRD_PARTY_ATTRIBUTION.md`. Neither covers the game data, which
is not distributed here.
