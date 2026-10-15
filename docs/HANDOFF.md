# Arbeitsstand & Übergabe (Stand 2026-10-15, Abend)

Kurzreferenz für die nächste Sitzung. Antworten an den Nutzer auf Deutsch.
RAM-Map / Spielmodi: `D:\Reverse Engineering\docs\sc4\analysis.md`.

## Regeln des Nutzers
- Privat & lokal: kein Push (origin/upstream haben Push-URL `DISABLE`). ROM und generierter Code nie ins Repo.
- Installieren/Git ohne Nachfrage erlaubt. Laufendes Spiel darf geschlossen werden.
- Ergänzungen im Spiel müssen **nativ** aussehen (Spielschrift, Tilemap, echter Cursor), keine Overlays.
- Fehlt im Widescreen-Rand Bildinhalt, wird er **selbst gestaltet** (aus den Tiles der Szene), nicht abgeschnitten oder mit Fremdinhalt gelassen.
- Kennzeichnen, was verifiziert (gebaut/ausgeführt/gelesen) vs. Vermutung ist. Token sparen, Qualität halten.

## Git
- Arbeitsbranch `dev` (lokal): … fb05f9f Reset/Savestate/Widescreen-Bind · 0770320 Lua · 777832f async Posen · 6ea1aaa RE-Tools/Handoff · **633733b Widescreen-Ränder** · **aac6d65 natives NEW GAME+** · (+ Handoff-Commit).
- Framework `snesrecomp` = lokaler Branch `sciv` (RetroPortingToolKit main a6be975 + 2 Rasmus-Commits + a4e0d83 Lua-Host). **Nur lokal** in `.git/modules/snesrecomp`; Spiegel-Backup: `D:\Super Castlevania IV Recomp\backup\snesrecomp-sciv.git` (nach Framework-Commits mit `git -C <backup> fetch` aktualisieren). `recomp-ui` = 5ca3df2. Pins in `framework_pins.txt`. In dieser Sitzung **keine** Framework-Änderung.
- Identität repo-lokal: `Gast114 <Gast114@users.noreply.github.com>`.

## Builds (alle gitignored)
| Ordner | Zweck |
|---|---|
| `build/` | Nutzer-Build, **Release** (seine `config.ini`, `characters/`, `saves/`); auf aac6d65 neu gebaut |
| `build-dev/` | Release für Tests |
| `build-lua/` | `-DSNESRECOMP_ENABLE_LUA=ON` für `tools/sciv_play.py` |
| `build-diag/` | `-DSNESRECOMP_ENABLE_PPU_DMA_HISTORY=ON` |
| `build-audit/` | Wegwerf-Ausgaben |

Neu konfigurieren: `cmake -S . -B <dir> -G Ninja -DCMAKE_BUILD_TYPE=Release -DSNESRECOMP_SDL3_SOURCE_DIR="<repo>/build/_deps/sdl3-src"` (kein Download).
Toolchain: retcomm clang 22/CMake/Ninja im PATH; Python 3.15 + Pillow; Rust (`/c/Users/Gaming/.cargo/bin` in Bash-PATH aufnehmen); nativer Analyzer gebaut (`snesrecomp/recompiler-rs/target/release/snesrecomp-analyze.exe`).

## Werkzeuge
- Tests: `python tools/test_<name>.py --rom "Super Castlevania IV (USA).sfc" --build-dir build-dev` (startup, campaign2, character_pack, character_stairs, character_tuning – alle grün auf aac6d65).
- Spielsteuerung: `tools/sciv_play.py start --build-dir build-lua --widescreen --fast`, dann `press Right 30`, `wait N`, `state`, `ppu` (jetzt mit Tile-Basis `tiles`), `shot x.png`, `save/load N`, `reset`, `peek/poke` (peek beliebig lang), `eval`, `stop`. Neu: `dump f.bin` (VRAM+CGRAM+OAM roh), `layers 0x02` (Ebenenfilter für folgende Shots, ohne Argument = alle).
  - Ablauf ohne Savestate: Boot → `wait 300` → `press Start 3` (Titel) → `press Start 3` (Bestätigung) → `wait 200` → `press Start 3` (Name überspringen) → `wait 300` = Tor-Sequenz → `wait 430` = Block 1-1.
- RE: `tools/re/dis65.py <rom> BB:AAAA [n] [m] [x]`; `tools/re/render_map.py dump.bin out.png --map 0x1000 --tiles 0x2000 --wide --tall --grid --scale 2` (ganze BG-Map mit Spaltennummern – zum Gestalten von Rändern); `tools/re/run_mesen.ps1`, `mesen_column_trace.lua`, `contact_sheet.py`.
- 4:3-Bitgleichheit (P16) prüfen: gleiche `.input` headless mit altem und neuem Build, `SNESRECOMP_PRESENT_LOG=<csv>` schreibt CRC32 pro Bild → Frames vergleichen.
- Headless: `SNESRECOMP_RUN_FRAMES`, `SNESRECOMP_SCREENSHOT(_FRAME)`, `SNESRECOMP_SCREENSHOT_DIR/FROM/TO`, `SNESRECOMP_LAYER_MASK`, `--script <file>.input`.

## Erledigt & verifiziert (diese Sitzung)
- **Widescreen-Ränder** (633733b, `src/main.c` `Cv4CurrentScene` + `src/widescreen_fill.c`):
  - Ursache war **nicht** der Ladeabstand: Horizontal-Streamer `$06:A0E6` lädt schon ±48 px (`LDA #$0130` / `#$FFD0` bei `$06:A146/A14D`), Raumaufbau `$06:965F` baut 47 Spalten X−56…X+312. Gemessen: 0 abweichende Pixel in den Rändern beim Laufen durch 1-1 (vor/zurück, BG1). (`$06:A15A/A1F0/A20A` = vertikal, `$06:A22C` = Metatile-Schreiber.)
  - Titel: BG1-Logo-Map 32 Spalten → lief als Kopie in die Ränder; BG1 im Titel (Modus 1, 3, 2/0) auf 256 px geklemmt, BG2-Mauer füllt nahtlos.
  - 1-1 links: links von Welt-X 0 baut das Spiel nie (negativ → Spalte 0); die Parallaxe-BG2 schaute dort hinein. Jetzt BG1+BG2 an Welt-X 0 gespiegelt (`PpuSetWidescreenLayerWorldMirrorBand`, nur Kamera < 512). Der alte „schwarze, wachsende Rand“-Hack ist entfernt.
  - Tor-Sequenz (Modus 4, `$70`=0, `$72`=3, `$02:FEA8`) und Prolog/Grabstein (Modus 2/1): gestaltete Randspalten aus `assets/widescreen_margins.txt` (Tor: gespiegelte Fortsetzung wie das selbst spiegelsymmetrisch gebaute Original; Grabstein: saubere erste Bildkopie statt Fremd-Tiles; Nebel BG1 `follow` = Rand nur in Zeilen, die der Nebel im 4:3-Bild schon erreicht hat). Angewendet auf eine reine Darstellungs-VRAM-Kopie (`ppu->renderVram`), Datei wird im laufenden Spiel bei Änderung neu geladen.
  - P16: 4:3 bitgleich außer Titelmenü (beabsichtigt). Widescreen ändert sich nur in Titel, Tor, Levelanfang.
- **Natives NEW GAME+** (aac6d65, `src/title_menu.c`, 7 Guarded Patches, all-or-nothing): START (Zeile 17), NEW GAME+ (19), CONTINUE (21), OPTION (23); „PLAY SELECT“ auf Wunsch entfernt. Index `$1E02`: 0 START, 1 CONTINUE, 2 OPTION, **3 NEW GAME+**; Navigation per Tabellen in Anzeigereihenfolge. Herz-Cursor (`$27`), Blinken beim Bestätigen nativ. „+“ = neues Tile `$33`, vom Spiel-Loader entpackt. `campaign2.c` macht aus bestätigter 3 → START + Kampagnen-Tag `$11E0=$C402` (Sandbox-Raum wie vorher). Overlay-Menü entfernt. Verifiziert: Navigation, Blinken, Tag/Raum, CONTINUE → Modus 6, OPTION → Modus 5 (Test).

## RE-Notizen (neu, gelesen bzw. ausgeführt)
- Modus 4, `$70`=0: `$72` 1 = Namenseingabe (`$03:8000`), 3 = Tor (`$02:FEA8`), 4 = Spielinit (`$00:94C5`; `$1E02`≠0 behält `$86`).
- Asset-Loader `$02:80E8` Typ 0: `00 00` + Einträge `[VRAM-Wort lo,hi][Quelle lo,hi,bank]`, Ende `FF FF`. Titel-Liste `$01:B5A7` (Font `$07:8DC9`→`$5000`, Satzzeichen `$07:8FF4`→`$5180`).
- LZ-Entpacker `$02:863D`: Kopf u16 Gesamtlänge; `<$80` Rückverweis, `$80–9F` Literal (n=c&31), `$A0–BF` 0/Byte-Wechsel, `$C0–DF` RLE Byte (n+2), `$E0–FF` RLE 0 (n+2); 1-KB-Ringpuffer.
- BG3-Font: `$01–$0A` 0–9, `$0B–$24` A–Z, `$25` =, `$26` -, `$27` Herz-Cursor, `$2E` ©, `$30` „,“, `$31` „.“, ab `$33` frei (`$33` jetzt „+“ im Titel).
- Freier ROM-Platz `$01:FF24–FFFF`: belegt bis `$01:FFDE`, **33 Byte frei** (`$01:FFDF–FFFF`).
- Menü-Routinen (`008607–00BB39`) sind `lle_only` → ROM-Patches wirken; AOT nur laut `src/gen/program_manifest.json`.

## Offene Aufgaben (Priorität)
1. **Savestate-Laden außerhalb des Gameplays defekt**: ein im Titel oder Attract gespeicherter State friert nach dem Laden ein (`$3A` steht, Start ohne Wirkung), auch im selben Prozess. Gameplay-States (Modus 4) laden korrekt. Vermutlich fehlender Bridge-/CPU-Kontext (NMI-Schachtelung bei `$00:8551`) – `GameStateSaveExtra` in `src/game_rtl.c` prüfen.
2. **Widescreen weiter**: andere Stages prüfen (vertikale Schächte, Levelenden rechts, Bossräume, Modus 7), Namenseingabe-/CONTINUE-/OPTION-Bildschirme und Abspann (Modus 7) – ggf. weitere Szenen in `widescreen_margins.txt` gestalten (Ablauf: `dump` → `render_map.py --grid` → Regeln → live prüfen). Prolog-Textphase: kleine Nebellücke links oben. Sprites im Rand: zweites Gate im OAM-Aufbau (`snesrecomp/docs/WIDESCREEN_PATTERNS.md` P8). Option: 1-1-Weltkante statt Spiegelung gestalten, falls der Nutzer das möchte.
3. **NEW GAME+-Inhalt**: startet derzeit den Host-Sandbox-Raum aus `campaign2.c`. Echte NG+-Regeln (z. B. Fortschritt übernehmen) mit dem Nutzer klären.
4. **Code neu generieren** mit nativem Analyzer: `symbols.toml` setzt bei `emit=false` jetzt `force_lle` für Reset/NMI → vorher `emit=true` setzen, um den getesteten AOT-Stand zu halten; Ausgabe mit altem `src/gen` vergleichen, Tests laufen lassen.
5. Idee des Nutzers: Testszenen einspielen → Savestate + Eingaben je Szene, deterministisch abspielen, Bild-/CRC-Vergleich (Framework-Hooks `frame_begin/frame_end`, Upstream `--resume-state`). Hängt an Aufgabe 1.
6. Später: Level-Editor, Gegner-Mods, Zufallsmodus, HD-Pipeline, Android, Mods als Pakete im Launcher.
