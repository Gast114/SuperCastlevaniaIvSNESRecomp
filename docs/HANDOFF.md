# Arbeitsstand & Übergabe (Stand 2026-10-15)

Kurzreferenz für die nächste Sitzung. Antworten an den Nutzer auf Deutsch.
RAM-Map / Spielmodi: `D:\Reverse Engineering\docs\sc4\analysis.md`.

## Regeln des Nutzers
- Privat & lokal: kein Push (origin/upstream haben Push-URL `DISABLE`). ROM und generierter Code nie ins Repo.
- Installieren/Git ohne Nachfrage erlaubt. Laufendes Spiel darf geschlossen werden.
- Ergänzungen im Spiel müssen **nativ** aussehen (Spielschrift, Tilemap, echter Cursor), keine Overlays.
- Kennzeichnen, was verifiziert (gebaut/ausgeführt/gelesen) vs. Vermutung ist. Token sparen, Qualität halten.

## Git
- Arbeitsbranch `dev` (lokal): e0c822a Framework-Update · b70585b Tests · fb05f9f Reset/Savestate/Widescreen-Bind · 0770320 Lua-Schnittstelle · (+ Commit für async Posen-Speichern, siehe unten).
- Framework `snesrecomp` = lokaler Branch `sciv` (RetroPortingToolKit main a6be975 + 2 Rasmus-Commits + a4e0d83 Lua-Host). **Nur lokal** in `.git/modules/snesrecomp`. `recomp-ui` = 5ca3df2. Pins in `framework_pins.txt`.
- Identität repo-lokal: `Gast114 <Gast114@users.noreply.github.com>`.

## Builds (alle gitignored)
| Ordner | Zweck |
|---|---|
| `build/` | Nutzer-Build, jetzt **Release** (enthält seine `config.ini`, `characters/`, `saves/`) |
| `build-dev/` | Release für Tests |
| `build-lua/` | `-DSNESRECOMP_ENABLE_LUA=ON` für `tools/sciv_play.py` |
| `build-diag/` | `-DSNESRECOMP_ENABLE_PPU_DMA_HISTORY=ON` (DMA-Ring im `last_run_report.json`) |
| `build-audit/` | Wegwerf-Ausgaben |

Neu konfigurieren: `cmake -S . -B <dir> -G Ninja -DCMAKE_BUILD_TYPE=Release -DSNESRECOMP_SDL3_SOURCE_DIR="<repo>/build/_deps/sdl3-src"` (kein Download).
Toolchain: retcomm clang 22/CMake/Ninja im PATH; Python 3.15 + Pillow; Rust (`/c/Users/Gaming/.cargo/bin` in Bash-PATH aufnehmen); nativer Analyzer gebaut (`snesrecomp/recompiler-rs/target/release/snesrecomp-analyze.exe`).

## Werkzeuge
- Tests: `python tools/test_<name>.py --rom "Super Castlevania IV (USA).sfc" --build-dir build-dev` (startup, campaign2, character_pack, character_stairs, character_tuning – alle grün).
- Spielsteuerung: `tools/sciv_play.py start --build-dir build-lua --widescreen --fast`, dann `press Right 30`, `wait N`, `state`, `ppu`, `shot x.png`, `save/load N`, `reset`, `peek/poke`, `eval`, `stop`. Startet pausiert, deterministisch.
- RE: `tools/re/dis65.py <rom> BB:AAAA [n] [m] [x]` (lineare Disassembly, verfolgt REP/SEP); `tools/re/run_mesen.ps1 -Script <lua>` (Mesen headless, Lua mit `emu.addMemoryCallback`); `tools/re/mesen_column_trace.lua` (Beispiel: wer schreibt `$7E:2C00`); `tools/re/contact_sheet.py`.
- Headless-Lauf ohne Lua: Umgebungsvariablen `SNESRECOMP_RUN_FRAMES`, `SNESRECOMP_SCREENSHOT(_FRAME)`, `SNESRECOMP_SCREENSHOT_DIR/FROM/TO`, `SNESRECOMP_HOST_PROFILE=1` (+`_START_FRAME`), `SNESRECOMP_LAYER_MASK` (Bit0=BG1…), `--script <file>.input`.

## Erledigt & verifiziert
- Framework-Update: Bilder pixelgleich, alle Tests grün.
- Reset (Hook `hardware_reset`) → bootet sauber; Savestates speichern Resume-PC (Titel-Chunk).
- Widescreen-Objekt-/Eventgrenzen jetzt auf `cart->rom` gebunden (wirkt beim Umschalten zur Laufzeit).
- **Ruckeln = Posen-Speichern**: `body.png` (768×3072) wurde bei jeder neuen Pose synchron geschrieben (0,3–1,4 s Hänger, trat beim Peitschen/Springen auf). Jetzt Hintergrund-Thread, max. 1×/s, Flush beim Beenden. Gemessen: max. 3,3 ms statt 1383 ms.
- Monitor läuft mit 60 Hz (3840×2160, Radeon 890M); Entkoppeln der Ausgabe verworfen (verschlechterte Takt).

## Offene Aufgaben (Priorität)
1. **Widescreen-Ränder** (Nutzer-Screenshots: Block 1-1 Müll links; Weg zum Schlosstor: rechts nur Nebel verschmiert; Titelbild: Logo wiederholt sich).
   - BG1 Tilemap `$4000`, **64 Spalten breit**; BG2 `$4800` 64 breit; BG3 `$5800` (HUD). BG mode 9. BG1/BG2 hScroll = `$1C`−1, vScroll = `$1E`−1 (Block 1-1).
   - Spalten-Upload: VRAM-Queue-Puffer `$7E:2C00`, DMA nach `$4000+Spalte` (28 Wörter, VMAIN+32) und `$4B00+Spalte` (4 Wörter).
   - Spaltenbauer: `$06:A20A…` (Direct Page = Ebenen-Struktur, nicht 0! `STX $FC/STY $FE`, `JMP $A19C`), Schreibschleife `$06:A266/A26D/A274/A27B` (4 Einträge × 7). **Nächster Schritt:** `$06:A19C` und Aufrufer von `$06:A20A` disassemblieren, Stelle finden, an der die Spalte relativ zur Kamera gewählt wird (Vorlauf nur 1 Spalte außerhalb 256 px) → per Guarded Patch auf ±48 px erweitern (wie Objektgrenzen in `src/main.c`). Auch Initial-Aufbau beim Raumstart prüfen.
   - Fallback: Framework-Modul `snesrecomp/runner/src/snes/ws_shadow.h` (`WsShadowSetWorld`, `SetRetainHistory`, `WsShadowFrame` in `begin_sim_frame`).
   - Sprites im Rand: zweites Gate im OAM-Aufbau suchen (Doku `snesrecomp/docs/WIDESCREEN_PATTERNS.md` P8).
2. **Natives Titelmenü „NEW GAME+“** (ersetzt START-2-Overlay in `src/campaign2.c`; Position: unter START).
   - Textdeskriptoren Bank `$01`: `[VRAM-Adr lo,hi][Zeichen…]`, `FE`=nächste Adresse, `FF`=Ende. A=`$0B`…Z=`$24`, Leer=`$00`, Ziffer 1=`$02`, `>`=`$27`, ©=`$2E`. `+` prüfen (Font-Tiles), ggf. eigenes Tile.
   - Init `$00:9385`: `JSL $009051` mit X=`$8531` (PLAY SELECT, Zeile 17 + Copyright Zeile 25), `$8577` START (Zeile 19, VRAM `$5A6C`), `$857F` CONTINUE (`$5AAC`), `$858A` OPTION (`$5AEC`). Abstand 2 Zeilen (`+$40`).
   - Eingabe `$00:93EC`: Auswahl `$1E02`, Umlauf `LDA #$0002` bei `$00:940C`, `CMP #$0003` bei `$00:941A`; Cursor-Tabelle `$01:8B2B` → Deskriptoren `$01:8593/859F/85AB` (`>` in einer Zeile, Rest leer).
   - Bestätigung Modus 3: Blinken `$00:86F4` über Tabelle `$01:82C6`; Verzweigung `$00:8715`: 0=Spiel, 2=Optionen, sonst Continue.
   - Plan: PLAY SELECT 2 Zeilen hoch, 4 Einträge im Originalabstand, neue Tabellen in freiem Platz `$01:FF24–$01:FFFF` (220 Byte `FF`), Index 3 → Spielstart + Kampagnen-Tag (`$11E0=$C402`). Alle Routinen laufen im Interpreter → Guarded Patches auf `cart->rom` wirken.
3. **Code neu generieren** mit nativem Analyzer: `symbols.toml` setzt bei `emit=false` jetzt `force_lle` für Reset/NMI → vorher `emit=true` setzen, um den getesteten AOT-Stand zu halten; Ausgabe mit altem `src/gen` vergleichen, Tests laufen lassen.
4. Idee des Nutzers (später): Er spielt Testszenen ein → je Szene Savestate am Anfang + aufgezeichnete Eingaben (Framework-Hooks `frame_begin/frame_end` in `RtlGameInfo`, Upstream `--resume-state`), die ich deterministisch abspiele und per Bild-/Checksummen-Vergleich prüfe (Szenen-Regressionstests).
5. Später: Level-Editor, Gegner-Mods, Zufallsmodus, HD-Pipeline (automatischer Export/Import der Grafiken für KI-Upscaling), Android, Mods als Pakete im Launcher.
