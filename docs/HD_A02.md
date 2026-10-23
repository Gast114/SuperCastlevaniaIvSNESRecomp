# Stage 01 / A02: installed user artwork

The new collection is `hd_packs/stage-01-user-a02-v2`. It retains the existing
entrance/drawbridge pack and selects A02 automatically using block 1 and the
native BG map addresses `[0,4096]`. The output stays at 10x. Restart the game
after replacing the executable; F2 tests the entrance/fence rise, F3 and Up
test the rotating gate and the two sides of the fence.

## Source registration

Eleven completed RGBA PNGs come from `Assets (ausgeschnitten)/Stage 01/A02/HD`:
front play plane, rear play plane, fence including fixed gate frames, separate
castle/sky scenery, four gate-leaf frames, and three gargoyle eye variants.
The old partial `Stage-01-A02-B01-F-HD.png` is not used by this import.

`assets/hd/stage_01_a02.recipe.json` records the registrations. The delivered
fence spans 8256 source pixels across 2048 native pixels, giving 129/32 source
pixels per native pixel. A small downward resample (128/129) registers working
copies at 4x; no generated art, enlarged source images or original-file edits
are involved. Output density remains 10x independently of source density.

The hidden Photoshop `Original` layer was read without modification. Matching
332 reference features independently recovers a scale of approximately 4.031
and the front origin `[4168,964]`. The exported fence has identical dimensions,
alpha and visible RGB pixels to the current merged Photoshop fence layer.
A clean F3 fence area matches all 7,448 tested opaque source pixels exactly
in the runtime screenshot. Fence proportions have not been altered.

The front PNG starts at the common source origin. The rear plane's source
offset is `[3998,344]`; the fence offset is `[0,120]`. Fractional native origins
become transparent padding on the 4x grid. The castle/sky image has its own BG2
scroll coordinates. These offsets must not be inferred from the trimmed PNGs'
upper-left corners independently.

The native background reference sheet contains a repeated 64-pixel castle bay
which is absent from the streamed runtime map. F3 matches the reference at
x439 exactly, but at the terminal camera position BG2 world x1373 matches sheet
x1437. Intermediate captures confirm this is a repeated bay, not a uniform
scale error. The importer omits `[832,896)` from its working background copy;
all following art moves left 64 native pixels without horizontal compression.
The supplied PNG remains untouched.

The gargoyle's visual source origin is `[6231,321]` after that registration,
preserving its supplied source density rather than fitting it to a native
33x20 box. Its native eye probe is separately registered at `[1551,104]`;
visual placement must not move the native color probe.

Build a new collection with:

```powershell
python tools/hd/build_a02_pack.py --source '../Assets (ausgeschnitten)/Stage 01/A02/HD' --entrance artwork-local/packs/stage-01-user-v4-final --out artwork-local/packs/NEW-FOLDER
```

## Runtime behavior

Collection manifests contain `version:1` and a `scenes` array of child directory
names. Children retain the existing pack format and individual art densities.
All children validate before publication. Selection occurs before frame capture;
native map guards preserve the outgoing scene during fades. Failed reloads keep
the previous collection. Unknown rooms use the entrance pack's guarded shared
objects and otherwise native artwork.

`scene-overlays-v1` adds alpha-composited regions above the normal BG candidates.
The front plane, fence, rear plane and gate leaves retain distinct priorities;
native sprite depth still decides which side of the fence covers Simon. The
rear play plane is distinct from the separately scrolling decorative scenery.

The opt-in `sciv_a02` roles read original video state from immutable scanline
copies: the rise follows actual fence tile pixels, leaf selection follows the
original gate tile IDs, and gargoyle eyes follow native eye-pixel colors.
No gameplay, cartridge, collision, save-state or timing patches are made.
Only overlays intersecting a scanline/viewport and the active animation phase
enter per-pixel sampling.

## Verification and installation

`tools/test_a02_hd.py` uses copies of F2/F3 in an isolated Lua build. It compares
native fields and named game states with HD disabled/enabled, checks the HUD,
checks the depth switch, and compares the entrance's existing HD checksum.
The supplemental diagnostic uses synthetic player relocation for layout views;
it is not a complete naturally played route through the level.

`tools/hd/install_a02_pack.py` installs a new collection and the release executable
into `build-play/game` and `build`, selects 10x HD, and makes an external backup
of the executable/settings and source PNGs. It hashes protected player files
before/after installation. Existing packs remain available. Source PNGs and
the Photoshop file stay unchanged; local artwork and generated packs stay
git-ignored.

Installed on 2026-10-23 in both player folders. Both settings files select
`hd_packs/stage-01-user-a02-v2`, and both executables have the same SHA-256.
The external backup and installation receipt are in
`D:/Super Castlevania IV Recomp/backup/hd-artwork/2026-10-23-stage01-a02-v2`.
The receipt confirms all protected files are unchanged and every copied pack
file matches its source.

Passed checks: `build-lua/a02-hd-check-zbvvar6v` (v2 F2/F3, HUD, native simulation,
gate depth and entrance checksum), `build-lua/a02-hd-check-a1gsw98n`
(v2 terminal gargoyle: 62.6% of opaque artwork pixels exactly visible through
the foreground fence) and `build-lua/a02-hd-check-hbb9iau2`
(v1 synthetic layout views and actual entrance-to-A02 scene transition).
Reports, selected game screenshots and the installation receipt are retained
under `artwork-local/stage01-a02-user-v2/review`. Registration diagnosis,
Photoshop extracts and the native BG2 sweep are in `artwork-local/a02-mapping-fix`.

Performance should be measured with the local AI queue idle. During this import,
a concurrent inference consumed almost all CPU time and left about 1.2 GiB RAM
free; the resulting 35–47 FPS samples do not establish unloaded performance.
