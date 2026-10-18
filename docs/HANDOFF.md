# Arbeitsstand & Übergabe (Stand 2026-10-18)

Kurzreferenz für die nächste Sitzung. Antworten an den Nutzer auf Deutsch. Aktueller Nutzerfokus: jederzeit umschaltbare, austauschbare HD-Grafik mit 4K-Ziel.
RAM-Map / Spielmodi: `D:\Reverse Engineering\docs\sc4\analysis.md`.

## Regeln des Nutzers
- Privat & lokal: kein Push (origin/upstream haben Push-URL `DISABLE`). ROM und generierter Code nie ins Repo.
- Installieren/Git ohne Nachfrage erlaubt. Laufendes Spiel darf geschlossen werden.
- Ergänzungen im Spiel müssen **nativ** aussehen (Spielschrift, Tilemap, echter Cursor), keine Overlays.
- Fehlt im Widescreen-Rand Bildinhalt, wird er **selbst gestaltet** (aus den Tiles der Szene), nicht abgeschnitten oder mit Fremdinhalt gelassen.
- Kennzeichnen, was verifiziert (gebaut/ausgeführt/gelesen) vs. Vermutung ist. Token sparen, Qualität halten.
- Klarstellung des Nutzers: **NEW GAME+ bedeutet den originalen schwereren zweiten Durchgang nach dem Durchspielen** (wie START 2), nicht den Sandbox-Raum. Umsetzung noch offen, Bedeutung bereits geklärt.

## Git
- Arbeitsbranch `dev` (lokal): … 633733b Widescreen-Ränder · aac6d65 natives NEW GAME+ · c81539d Handoff · **57b62dc Savestate-Ausführungszustand** · **6570042 Debug-Marker** · (+ Handoff-Commit).
- Framework `snesrecomp` = lokaler Branch `sciv` (RetroPortingToolKit main a6be975 + 2 Rasmus-Commits + a4e0d83 Lua-Host). **Nur lokal** in `.git/modules/snesrecomp`; Spiegel-Backup: `D:\Super Castlevania IV Recomp\backup\snesrecomp-sciv.git` (nach Framework-Commits mit `git -C <backup> fetch` aktualisieren). `recomp-ui` = 5ca3df2. Pins in `framework_pins.txt`. Framework aktuell **d837790** (HD-Provenienz + Presenter-Hooks), davor **9cd151c** (Debug-Marker). Pin und lokales Spiegel-Backup sind aktualisiert.
- Identität repo-lokal: `Gast114 <Gast114@users.noreply.github.com>`.

## Builds (alle gitignored)
| Ordner | Zweck |
|---|---|
| `build/` | Nutzer-Build, **Release** (seine `config.ini`, `characters/`, `saves/`, `debug_markers/`); Live-HD-Umschaltung vom 18.10. neu gebaut |
| `build-dev/` | Release für Tests |
| `build-lua/` | `-DSNESRECOMP_ENABLE_LUA=ON` für `tools/sciv_play.py` |
| `build-diag/` | `-DSNESRECOMP_ENABLE_PPU_DMA_HISTORY=ON` |
| `build-audit/` | Wegwerf-Ausgaben |

Neu konfigurieren: `cmake -S . -B <dir> -G Ninja -DCMAKE_BUILD_TYPE=Release -DSNESRECOMP_SDL3_SOURCE_DIR="<repo>/build/_deps/sdl3-src"` (kein Download).
Toolchain: retcomm clang 22/CMake/Ninja im PATH; Python 3.15 + Pillow; Rust (`/c/Users/Gaming/.cargo/bin` in Bash-PATH aufnehmen); nativer Analyzer gebaut (`snesrecomp/recompiler-rs/target/release/snesrecomp-analyze.exe`).

## Debug-Marker (vom Nutzer gesetzte Problemstellen – zuerst ansehen!)
- Im Spiel **Strg+D** bzw. Pad **Select+L3** (`config.ini [KeyMap] DebugMarker`, `[Controller] DebugGesture`): Spiel friert ein, Notizfenster; Strg+Enter/A speichert, Esc/B verwirft.
- Ablage: `build/debug_markers/<Datum>_<Uhrzeit>_<Szene>/` mit `note.md` (Beschreibung), `marker.json` (Szene, Frame, Modus/Block/Kamera/Spieler, PPU-Ebenen), `screen.png` (Bild inkl. Ränder), `state.sav`, `video.bin` (VRAM+CGRAM+OAM, für `render_map.py`), `wram.bin`. Neue Marker zusätzlich `lines.bin` (225×32 Byte Zeilenregister für die HD-Vorschau); bei HD auch `hd_screen.png` und Einstellungen unter `marker.json.hd`.
- Auswerten: `python tools/debug_markers.py` (Liste, neueste zuerst), `... show <id-Präfix>`; nachstellen: `sciv_play.py start --build-dir build-lua --widescreen --fast` → `sciv_play.py loadfile build/debug_markers/<id>/state.sav` → `layers`/`shot`/`dump`/`press`.
- Code: `src/debug_marker.cpp` (Aufnahme + ImGui-Panel), `src/debug_capture.c` (gemeinsam mit Lua-Befehlen), Framework-Hooks in `host_main.c` (`RunDebugMarkerLoop`). Selbsttest: `SNESRECOMP_DEBUG_MARKER_AT=<frame>` + `_NOTE=<text>` oder `_TYPE=<text>` (tippt über SDL-Ereignisse).

## Werkzeuge
- **HD:** [HD_PIPELINE.md](HD_PIPELINE.md). Escape → HD graphics → **HD graphics enabled** schaltet live Original/HD um; unabhängige Backgrounds/Text/Sprites-Schalter, Paketauswahl und 2×/4×/6×/10×. Sammlung separat: Collect graphics while playing. Nach regulärem Beenden `python tools/hd/hd_pipeline.py --build build` (Real-ESRGAN) bzw. `--method nearest` (Identitätsprüfung). Ergebnis `build/hd_pack/`, Vorschau im neuesten Marker mit `lines.bin`. **Live-Detailersatz implementiert; Original-Silhouetten bleiben erhalten.**
- **Grafikquellen des Nutzers:** 33 PNG-Bögen in `C:\Users\Gaming\Downloads\assets`; `python tools/hd/hd_sources.py` schreibt den Katalog nach `build/hd_work/source_sheets.json`. Originale unverändert, noch kein automatischer Sheet-Import. Stage-9-Hintergrundbogen fehlt in diesem Ordner.
- Tests: `python tools/test_<name>.py --rom "Super Castlevania IV (USA).sfc" --build-dir build-dev` (startup, campaign2, character_pack, character_stairs, character_tuning, debug_marker, hd_pipeline – alle sieben am 18.10. erneut grün). Neu: `test_hd_ppu.py` ohne ROM, `test_hd_render.py` mit `--build-dir build-lua`, `test_hd_ui.py` mit `--pack build/hd_pack`; ebenfalls grün.
- Spielsteuerung: `tools/sciv_play.py start --build-dir build-lua --widescreen --fast`, dann `press Right 30`, `wait N`, `state`, `ppu` (jetzt mit Tile-Basis `tiles`), `shot x.png`, `save/load N`, `loadfile <state.sav>`, `reset`, `peek/poke` (peek beliebig lang), `eval`, `stop`. Neu: `dump f.bin` (VRAM+CGRAM+OAM roh), `layers 0x02` (Ebenenfilter für folgende Shots, ohne Argument = alle).
  - Ablauf ohne Savestate: Boot → `wait 300` → `press Start 3` (Titel) → `press Start 3` (Bestätigung) → `wait 200` → `press Start 3` (Name überspringen) → `wait 300` = Tor-Sequenz → `wait 430` = Block 1-1.
- RE: `tools/re/dis65.py <rom> BB:AAAA [n] [m] [x]`; `tools/re/render_map.py dump.bin out.png --map 0x1000 --tiles 0x2000 --wide --tall --grid --scale 2` (ganze BG-Map mit Spaltennummern – zum Gestalten von Rändern); `tools/re/run_mesen.ps1`, `mesen_column_trace.lua`, `contact_sheet.py`.
- 4:3-Bitgleichheit (P16) prüfen: gleiche `.input` headless mit altem und neuem Build, `SNESRECOMP_PRESENT_LOG=<csv>` schreibt CRC32 pro Bild → Frames vergleichen.
- Headless: `SNESRECOMP_RUN_FRAMES`, `SNESRECOMP_SCREENSHOT(_FRAME)`, `SNESRECOMP_SCREENSHOT_DIR/FROM/TO`, `SNESRECOMP_LAYER_MASK`, `--script <file>.input`.

## Erledigt & verifiziert (diese Sitzung)
- **Live-HD / 4K-Grundlage (18.10., nach 2cf6d09):** `src/hd_render.cpp` lädt austauschbare Tile-Pakete; Schalter in Escape → HD graphics, Kategorien Backgrounds/Text-HUD/Sprites, Paketauswahl (`hd_pack`, `hd_packs/*`), Reload und Faktor 2/4/6/10. Persistenz `hd_settings.json`. Paketfehler erhalten das vorherige gültige Paket. Pakete bleiben gitignored.
  - 10× = 3420×2240 intern mit Widescreen, Presenter korrigiert Seitenverhältnis auf dem Zielmonitor. **80×80 reale Pixel pro Original-8×8-Tile** als 4K-Artworkziel; DPI ist irrelevant. Windows-Auflösung wird nicht verändert.
  - Lokales `build/hd_pack/`: 446 bereits zuvor mit Real-ESRGAN bearbeitete 4×-Probetiles für Mauerwerk/Treppen und Teile des Schlosstors. Noch **kein kompletter 4K-Grafiksatz**, keine neuen vollständigen Figurenanimationen. Original standardmäßig an, HD per Klick aktivieren.
  - Framework: optionale `presentation_scale`/`draw_hd_frame`-Hooks, native Thumbnails, HD unter Pause-Menü; PPU-Tileprovenienz (inkl. echter OAM-Gewinner), Farbfensterflags. Ersatzfarben werden anhand der tatsächlichen Zeilenregister/-palette/-VRAM zugeordnet, dann in unveränderlichen Pixelbeschreibungen auf bis zu 8 Render-Threads komponiert. Worker-Pool aus bestehendem Framework, Override `SNESRECOMP_RENDER_WORKERS=1` für seriell.
  - Grenzen: native Sichtbarkeit/Silhouetten bleiben erhalten; Ersatzalpha wird innerhalb nativer sichtbarer Pixel mit Originalfarbe gemischt. **Echte glatte HD-Konturen erfordern später Komposition vor der Transparenzentscheidung.** Modi 2–7, Mosaic, Interlace/Hires und unsupported Host-Transforms fallen auf Original zurück; Character-Workshop-Körper bleiben nativ. RGB8-Farbmathematik für neue Farben; unveränderte Samples exakt Original.
  - Werkzeuge: `sciv_play.py hd on|off`, `hd scale 10`, `hd layers 0x13`, `hd pack ORDNER`, `hdshot DATEI`. `hd_tiles.py export/build` für einzelne editierbare Schlüssel-PNGs und getrennte Grafikvarianten; Paket-/Custom-Upscale-Skalen bis 10×, bestehendes Real-ESRGAN-x4-Modell weiterhin nur 4×.
  - Verifiziert: `test_hd_ppu.py` (BG/OBJ-Flips, 16×16-BG, Weltspiegelung, Mosaic/Window-Fallback); `test_hd_render.py` gegen Lua-Build (2/4/10× pixelidentisches Nearest, native Simulation unverändert, echte 80×80-Testmuster, alle Kategorien unabhängig, ungültiger Reload, Persistenz); `test_hd_ui.py` (echter Checkbox-Klick an/aus über Neustart, HD-Marker 3420×2240 plus Original 342×224). UI-Screenshot `build-audit/hd-menu-final.png` geprüft.
  - Messung über `sciv_play.py`, 240 ungedrosselte Frames in festem 1-1-Zustand: ca. **88 FPS** mit 446-4×-Probetiles bei 10× Ausgabe; ca. **70 FPS** mit 2944 echten 80×80-Diagnosetiles. `build-audit/hd-performance.json`. Kein Leistungsversprechen für alle Stages/Computer.
  - Originalpfad zusätzlich gegen den Vor-HD-Build geprüft: **alle 1320 Bild-CRCs unverändert**. Finaler Exporttest `build-dev/hd-check-1o_z_3ml`: 31.508 Vorkommen, 1320 Frames, Marker-Roundtrip und Session-Erhalt grün.
  - Hauptartefakte: `build-lua/hd-live-check-zh_k8ytn`, `build/hd-ui-check-w7kr6pgo`, `build-audit/hd-live-final.png`. Nutzer-Build und Lua-Build aktualisiert; finale UI-Klicktests auf dem Nutzer-Build und Startup mit RunAhead 0/1 grün (`build/startup-check-hws4lyp2`). Nutzer-Saves/Charaktere/Downloads unverändert.
- **HD-Vorbereitung (18.10.):** Claudes uncommittierten Stand übernommen und fertiggestellt: `hd_collect.cpp` erfasst BG1–3/Sprites, PNGs und Tile-Zuordnung im Hintergrund; eindeutige Sitzungsnamen erhalten frühere Aufnahmen, Warteschlange begrenzt, Schreibfehler werden gemeldet. Debug-Marker erhalten Zeilenregister; Werkzeuge unter `tools/hd/` skalieren, bauen Atlanten und rekonstruieren Marker. Quellprüfsummen verhindern veraltete Upscale-Caches. Exporte sind gitignored. Grenzen: Dokumentation lesen, insbesondere Modus 7, Effekte und Widescreen fehlen in der Vorschau.
  - Verifiziert mit `test_hd_pipeline.py --rom ...`: **31.508 Tile-Vorkommen korrekt, 1320 Bild-CRCs mit/ohne Sammlung gleich**, 1-1-Marker pixelgenau rekonstruiert; Nearest-Paket identisch, zweiter Spielstart erhält alte Aufnahmen. Tests für Flips, Alpha, Cache und ungültige Maße ebenfalls grün.
  - Real-ESRGAN lokal auf Radeon 890M ausgeführt: zwei Ebenenbilder → 446 HD-Tiles, teilweise HD-Vorschau in `build-audit/hd-realesrgan-review/`. Kein fertiges Vollspiel-Grafikpaket.
  - `build-lua` gebaut, Titel mit `sciv_play.py` angefahren und Screenshot geprüft/gespeichert (`build-audit/hd-current-title.png`).
  - Nutzer-Build `build/` war im Cache auf Debug gestellt; wieder als **Release** konfiguriert und gebaut, wie hier dokumentiert. Nutzerdateien bleiben erhalten.
- **Widescreen-Ränder** (633733b, `src/main.c` `Cv4CurrentScene` + `src/widescreen_fill.c`):
  - Ursache war **nicht** der Ladeabstand: Horizontal-Streamer `$06:A0E6` lädt schon ±48 px (`LDA #$0130` / `#$FFD0` bei `$06:A146/A14D`), Raumaufbau `$06:965F` baut 47 Spalten X−56…X+312. Gemessen: 0 abweichende Pixel in den Rändern beim Laufen durch 1-1 (vor/zurück, BG1). (`$06:A15A/A1F0/A20A` = vertikal, `$06:A22C` = Metatile-Schreiber.)
  - Titel: BG1-Logo-Map 32 Spalten → lief als Kopie in die Ränder; BG1 im Titel (Modus 1, 3, 2/0) auf 256 px geklemmt, BG2-Mauer füllt nahtlos.
  - 1-1 links: links von Welt-X 0 baut das Spiel nie (negativ → Spalte 0); die Parallaxe-BG2 schaute dort hinein. Jetzt BG1+BG2 an Welt-X 0 gespiegelt (`PpuSetWidescreenLayerWorldMirrorBand`, nur Kamera < 512). Der alte „schwarze, wachsende Rand“-Hack ist entfernt.
  - Tor-Sequenz (Modus 4, `$70`=0, `$72`=3, `$02:FEA8`) und Prolog/Grabstein (Modus 2/1): gestaltete Randspalten aus `assets/widescreen_margins.txt` (Tor: gespiegelte Fortsetzung wie das selbst spiegelsymmetrisch gebaute Original; Grabstein: saubere erste Bildkopie statt Fremd-Tiles; Nebel BG1 `follow` = Rand nur in Zeilen, die der Nebel im 4:3-Bild schon erreicht hat). Angewendet auf eine reine Darstellungs-VRAM-Kopie (`ppu->renderVram`), Datei wird im laufenden Spiel bei Änderung neu geladen.
  - P16: 4:3 bitgleich außer Titelmenü (beabsichtigt). Widescreen ändert sich nur in Titel, Tor, Levelanfang.
- **Natives NEW GAME+** (aac6d65, `src/title_menu.c`, 7 Guarded Patches, all-or-nothing): START (Zeile 17), NEW GAME+ (19), CONTINUE (21), OPTION (23); „PLAY SELECT“ auf Wunsch entfernt. Index `$1E02`: 0 START, 1 CONTINUE, 2 OPTION, **3 NEW GAME+**; Navigation per Tabellen in Anzeigereihenfolge. Herz-Cursor (`$27`), Blinken beim Bestätigen nativ. „+“ = neues Tile `$33`, vom Spiel-Loader entpackt. `campaign2.c` macht aus bestätigter 3 → START + Kampagnen-Tag `$11E0=$C402` (Sandbox-Raum wie vorher). Overlay-Menü entfernt. Verifiziert: Navigation, Blinken, Tag/Raum, CONTINUE → Modus 6, OPTION → Modus 5 (Test).

- **Savestates** (57b62dc): Chunk „CV4S“ speichert zusätzlich den Ausführungszustand (`RtlSaveExecutionState`, angewendet in `on_state_loaded`). Verifiziert: Titel-State aus Prozess A läuft in Prozess B weiter; Gameplay-State in neuem Prozess spielt bitgenau gleich weiter. Alte „CV4R“-States laden wie bisher (nur gleicher Prozess zuverlässig). Rollback/Run-Ahead bleibt abgelehnt (`exec_state_bound` = 0).
- **Debug-Marker** (6570042 + Framework 9cd151c), siehe oben. Verifiziert: Test, sichtbarer Lauf mit getipptem Text, Laden des Marker-States in `sciv_play`. 4:3 und Widescreen über 1500 Frames bitgleich zum Stand davor.

## RE-Notizen (neu, gelesen bzw. ausgeführt)
- Modus 4, `$70`=0: `$72` 1 = Namenseingabe (`$03:8000`), 3 = Tor (`$02:FEA8`), 4 = Spielinit (`$00:94C5`; `$1E02`≠0 behält `$86`).
- Asset-Loader `$02:80E8` Typ 0: `00 00` + Einträge `[VRAM-Wort lo,hi][Quelle lo,hi,bank]`, Ende `FF FF`. Titel-Liste `$01:B5A7` (Font `$07:8DC9`→`$5000`, Satzzeichen `$07:8FF4`→`$5180`).
- LZ-Entpacker `$02:863D`: Kopf u16 Gesamtlänge; `<$80` Rückverweis, `$80–9F` Literal (n=c&31), `$A0–BF` 0/Byte-Wechsel, `$C0–DF` RLE Byte (n+2), `$E0–FF` RLE 0 (n+2); 1-KB-Ringpuffer.
- BG3-Font: `$01–$0A` 0–9, `$0B–$24` A–Z, `$25` =, `$26` -, `$27` Herz-Cursor, `$2E` ©, `$30` „,“, `$31` „.“, ab `$33` frei (`$33` jetzt „+“ im Titel).
- Freier ROM-Platz `$01:FF24–FFFF`: belegt bis `$01:FFDE`, **33 Byte frei** (`$01:FFDF–FFFF`).
- Menü-Routinen (`008607–00BB39`) sind `lle_only` → ROM-Patches wirken; AOT nur laut `src/gen/program_manifest.json`.

## Offene Aufgaben (Priorität)
1. **Widescreen weiter** – am besten anhand der Debug-Marker des Nutzers: andere Stages (vertikale Schächte, Levelenden rechts, Bossräume, Modus 7), Namenseingabe/CONTINUE/OPTION, Abspann; Sprites am Rand (zweites Gate im OAM-Aufbau, `snesrecomp/docs/WIDESCREEN_PATTERNS.md` P8); Prolog-Nebellücke links oben; optional 1-1-Weltkante gestalten statt spiegeln. Ablauf für neue Szenen: `dump` → `render_map.py --grid` → Regeln in `widescreen_margins.txt` → live prüfen.
2. **NEW GAME+ korrekt anschließen:** Nutzer hat Bedeutung geklärt: originaler schwererer zweiter Durchgang. Retail-Abschluss-/Schwierigkeitsflag reverse-engineeren und den Menüeintrag daran anschließen; aktuell startet er weiterhin den Host-Sandbox-Raum aus `campaign2.c`.
3. **Szenen-Regressionstests** (Idee des Nutzers): Marker-State + aufgezeichnete Eingaben deterministisch abspielen, CRC/Bild vergleichen (`SNESRECOMP_PRESENT_LOG`). Seit 57b62dc möglich; Eingabeaufzeichnung fehlt noch (Framework-Hooks `frame_begin/frame_end`, Upstream `--resume-state`).
4. **Code neu generieren** mit nativem Analyzer: `symbols.toml` setzt bei `emit=false` jetzt `force_lle` für Reset/NMI → vorher `emit=true` setzen, um den getesteten AOT-Stand zu halten; Ausgabe mit altem `src/gen` vergleichen, Tests laufen lassen.
5. **HD-Artwork und vollständige HD-Komposition:** 80×80-Motive/ganze Figuren in konsistentem Stil ausarbeiten; Downloads-Bögen zuschneiden/zuordnen. Live-Detailersatz und Umschalter sind fertig, aber glatte HD-Konturen über die nativen Silhouetten hinaus, Mode-7-Ersatz und spielweite Szenenprüfung fehlen. Details/Workflow: HD_PIPELINE.md.
6. Später: Level-Editor, Gegner-Mods, Zufallsmodus, Android, Mods als Pakete im Launcher.
