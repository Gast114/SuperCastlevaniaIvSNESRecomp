# HD-Grafik umschalten und bearbeiten

Stand: 2026-10-20. **Escape → HD graphics → HD graphics enabled** schaltet
zwischen Original und dem geladenen HD-Paket um. Die Simulation läuft beim
Fortsetzen an derselben Stelle weiter. Originalgrafiken bleiben jederzeit
verfügbar; fehlende Ersatztiles erscheinen automatisch im Original.

## Aktueller Import: fertige Nutzerbilder für Stage 01 (20.10.)

Der Nutzer erstellt alle Grafiken selbst. Codex generiert keine weiteren Bilder
und bereitet keine neuen Ausschnitt-/Promptserien vor. Vollständige HD-Motive
werden zusammen mit ihren nativen SD-Referenzen importiert. Die folgenden
älteren Material-/Tilepiloten bleiben historische, optionale Werkzeuge.

Installiert und ausgewählt: **`build/hd_packs/stage-01-user-v1`**, HD an, 10×.
Finales Paket: `artwork-local/packs/stage-01-user-final`. Quellen unverändert
in `artwork-local/stage01-user-v1/source`, aus
`D:\Super Castlevania IV Recomp\Assets (ausgeschnitten)\Stage 01` kopiert;
`source-checksums.json` hält SHA-256 aller 21 Dateien fest. Kein Resizing, keine
Farbänderung am HD-Original. Technische Ebenen-/Animationsausschnitte verändern
nur die importierte Kopie. Das Rezept ist versioniert:
`assets/hd/stage_01.recipe.json`.

| Motiv | native Registrierung | Behandlung |
|---|---|---|
| Land/Treppe 6970×1800 | Welt −54,44; 697×180 | komplette Fläche inklusive linker Erweiterung |
| Brücke/Burg 4350×1930 | Welt 643,31; 435×193 | rechte Erweiterung, getrennte Spielkomponenten |
| Felsen 2850×1920 | BG2-Karte 0,0; Wiederholung 512×256 | echte Parallaxen-/Zeilenregister |
| Mond 190×190 | Bildschirm 54,46 | ganze RGBA-Form, vier originale OBJ-Schlüssel maskiert |
| Fledermäuse 260×60 | originale OBJ-Schlüssel und Posen | sechs 80×80-Tiles |
| Wasser 1400×980 | BG2 y200; Inhalt x12…140, 128×24 | vier ganze Phasen, originale Palette 80 als Schutz |

Brückendeck und Scharnier sind Mode 7, Burg und Kette sind native Sprites.
Darum wird das Deck separat aus dem gelieferten Bild entnommen und mit der
Originalmatrix gedreht. Die Burg bleibt fest; ihr gebundener Originalbereich
mit OBJ-Palette 240 wird maskiert. Grasinseln bleiben ebenfalls fest und hinter
dem Deck. Beim isolierten Grasstreifen entfernt eine Alpha-Komponentenmaske die
am oberen Schnittrand anliegenden Deck-/Plattformfragmente. Das Rohbild bleibt
unverändert. Kette und Fledermäuse folgen den nativen OBJ-Posen und behalten
noch deren Rasterkontur; an der Kette sind Segmentkanten sichtbar.

Das Wasser verwendet einen **kosmetischen Spielzähler-Takt**: vier Phasen à
16 Frames aus WRAM `$3A`, 64-Frame-Schleife, somit ohne Sprung beim 8-bit-Wrap.
Pausieren/State-Laden bleibt reproduzierbar. Dies behauptet keine exakte
Synchronisation mit den Original-Wasserphasen. Die HDMA-Zeilenverschiebungen und
native Farbmathematik wirken weiterhin auf die dargestellte Wasserfläche.

Reproduzierbarer Neubau in ein **neues, leeres** Ziel:

```powershell
python tools/hd/hd_scene.py --recipe assets/hd/stage_01.recipe.json --source artwork-local/stage01-user-v1/source --dump artwork-local/stage01-user-v1/pilot-keys --dump artwork-local/stage01-user-v1/capture --video artwork-local/stage01-user-v1/water-video.bin --out artwork-local/packs/stage-01-next
```

`scene-receipt.json` enthält Rezept, Builder-/Quell-/SD-/Aufnahme-Prüfsummen,
Zuordnungen und mehrdeutige Tilevarianten. 36 Schlüsselbilder (Mond 4,
Fledermäuse 6, Wasser 15, Kette 11) ergänzen 13 Bildblöcke. Bilder über 4096 Pixel
Breite werden an nativen Pixelgrenzen geteilt; der Loader verbindet passende
benachbarte Blöcke wieder zu durchgehenden CPU-Ebenen (hier 11 Regionen), auch
für affine Abtastung. Eine Quelle versorgt ihre wiederholten Vorkommen.

### Szenenformat und Laufzeit

`requires: ["scene-regions-v1"]` verlangt `scene_block`, `regions` und optional
`tiles`. Unterstützte Layer sind BG1=0, BG2=1 und registrierte feste OBJ=4.
Regionen benennen lokale PNGs, native `x/y`, `coordinates` (`world`, `map`,
`screen`), `wrap_x/y`; optional Modi 1/7, feste BG1-Flächen, OBJ-Schlüsselmaske,
Priorität und Animationsselektor. Pro Paket maximal 16 Dateiregionen und
256 MiB decodierte Bilddaten; einzelne PNGs maximal 4096×4096. Kontexttiles
und Szenenregionen dürfen nicht im selben Paket stehen. Ungültiger Reload
behält das letzte gültige Paket. Szene ist auf Spielmodus 4, Ladephase 5 und
den benannten Block begrenzt; Text/HUD bleiben nativ.

Der Opt-in-Pfad sammelt read-only Kandidaten auch für transparente/verdeckt
liegende BG-Pixel. RGBA wird vor der Sichtbarkeit mit nativen Prioritäten,
Fenstern, Main/Subscreen, Farbmathematik und Helligkeit komponiert. Er kopiert
pro Zeile den PPU-Zustand einschließlich Darstellungs-VRAM, Kamera und Zähler;
Worker lesen diese unveränderlichen Kopien. Keine Zugriffe der Worker auf
laufende CPU/PPU-Zustände und keine Änderungen an Spielkollisionen/-simulation.
Nicht unterstützte Modi, Mosaic-/Hosttransformationen, Interlace/Hires oder
Direct Color fallen auf Original zurück; Mode 7 ist hier nur für den tatsächlich
geprüften Brückenfall verifiziert. Kein allgemeiner HD-Ersatz aller SNES-Effekte
oder vollständiger bewegter Sprite-Stapel.

Szenenpakete im laufenden Spiel mit `sciv_play.py hdshot` ansehen.
`hd_preview.py` und `hd_tiles.py export` lehnen sie ausdrücklich ab, damit beim
alten Tile-Export keine ganzen Ebenen stillschweigend verloren gehen.

**Noch fehlend:** eigene linke Erweiterung des Felsen-Hintergrunds; dort bleibt
Spiegelung, während die gelieferte FG-Erweiterung bereits eingebaut ist.
Simon, HUD, Kerzen und Gegner haben weiterhin Originalgrafik. Weitere Blöcke
benötigen passende Nutzerbilder und eine eigene Szenen-/Bewegungsprüfung.

### Nachweis für dieses Paket

`test_hd_scene.py` prüft echte Alpha-Konturen, Nearest-Identität bei 2×/4×/10×,
Kategorien/falsche Szene und native Bilder/Zustände beim Start, Scrollen, auf der
Brücke, in einer weiteren Wasserphase und bei echter Brückenrotation.
Parallel (8) und seriell (1) liefern 33 bytegleiche gemeinsame PNGs. Zusätzlich
elf Bewegungs-Checkpoints in `test_hd_route.py`, bestehender Tile-/Kontexttest
und `test_hd_ppu.py`. Berichte und Bilder dauerhaft unter
`artwork-local/stage01-user-v1/review`. Nutzer-Release-Menütest (Klick/Persistenz/Marker) und Startup mit RunAhead 0/1
sind ebenfalls grün. Finale Messung über `sciv_play.py`, je 240 ungedrosselte
Frames bei 10×: ca.60,8 FPS am Start, 58,0 FPS auf der Brücke auf diesem Rechner.
Kein allgemeines 60-FPS-Versprechen und kein vollständiger Frame-CRC-Test des
ganzen Spiels. Für Fortschritt und Quellen gilt HANDOFF.md.

```powershell
python tools/test_hd_scene.py --rom "Super Castlevania IV (USA).sfc" --build-dir build-lua --pack artwork-local/packs/stage-01-user-final
python tools/test_hd_route.py --rom "Super Castlevania IV (USA).sfc" --build-dir build-lua --pack artwork-local/packs/stage-01-user-final --fixture artwork-local/fixtures/block-1-1/state.sav
```

## Umschalten und 4K-Ziel

- Ein Klick auf **HD graphics enabled** aktiviert/deaktiviert HD.
- **Backgrounds**, **Text / HUD**, **Sprites** lassen sich unabhängig umschalten.
  Die Gruppierung folgt BG1/2, BG3/4 und OBJ; sie ist keine Objekterkennung.
- **Graphics pack** wählt `hd_pack` oder einen Unterordner von `hd_packs/`
  mit `pack.json`. **Reload graphics pack** übernimmt gespeicherte Änderungen.
  Ungültige Pakete werden abgelehnt; das letzte gültige bleibt geladen.
- Änderungen an Paket, Kategorien und Auflösung greifen beim Fortsetzen.
  Auswahl und Schalter stehen in `hd_settings.json` neben der EXE.
- **2× / 4× / 6× / 10× (4K target)** bestimmt die interne Auflösung.
  10× ergibt bei aktuellem Widescreen 3420×2240, im Originalformat 2560×2240.
  Der Presenter passt das Seitenverhältnis an den Bildschirm an. Auf einem
  3840×2160-Display wird daraus die entsprechende 4K-Darstellung. Es erfolgt
  kein automatischer Wechsel der Windows-Bildschirmauflösung.
- Für diese Qualität sollte ein ursprüngliches **8×8-Tile 80×80 echte
  Bildpixel** erhalten. Ein 16×32-Motiv entspricht dann 160×320 Pixeln.
  DPI-Metadaten spielen für Bildschirmgrafik keine Rolle. Ein 4×-Paket bleibt
  auch bei 10× Ausgabe inhaltlich 4×; größere Ausgabe erfindet keine Details.
- Das lokale Probepaket `build/hd_pack` enthält 446 bereits mit Real-ESRGAN
  bearbeitete 4×-Tiles (Mauerwerk/Treppen in 1-1 und Teile der Tor-Szene).
  Es dient dem Umschaltvergleich und ist **kein fertiger 4K-Grafiksatz**.
  Die unveränderten Sprite-Bögen unter Downloads sind weiterhin zusätzliche
  Quellen; deren Zuschneiden und Zuordnung ist offen.

## Eigene Grafikvarianten

### Historischer Materialpilot Block 1-1

Lokales Paket **`build/hd_packs/pilot-1-1-painted-v2`** im Menü auswählen,
HD aktivieren, 10× wählen. Drei mit dem eingebauten Imagegen neu ausgearbeitete
Motive: Mauerwerk, rote Treppe und Fels/Vegetation. **Eine partielle Stil- und
Technikprobe**, kein vollständig ersetzter Abschnitt. Simon, HUD, der größte
Teil des Bodens und weitere Mauern bleiben original. Übergänge zwischen neuem
und unbearbeitetem Material sowie native Außenkonturen sind noch sichtbar.

Die Vorlagen sind exakt zugeordnete Ebenenaufnahmen aus der eigenen ROM.
Downloads-Bögen wurden nicht verändert. Quellaufnahmen, beschnittene Referenzen,
unveränderte KI-Ausgaben und lokale Arbeitsrezeptur liegen unter
`build/hd_work/pilot-1-1-v1/`. Die finale Prompt-Sammlung und Schnittkoordinaten
stehen versioniert in `assets/hd/pilot_1_1.recipe.json`.

| Motiv | Originalausschnitt | KI-Ausgabe | Detailfaktor vor Import |
|---|---:|---:|---:|
| Mauerwerk | 96×64 | 1536×1024 | 16× |
| Treppe | 96×96 | 1254×1254 | 13,06× |
| Fels/Vegetation | 96×144 | 1024×1536 | 10,67× |

Der Import verkleinert diese Vorlagen auf **80×80 pro Tile**; er skaliert
unzureichende Bilder nicht künstlich hoch. Die Auflösung allein bestätigt
keine geometrische Passung: Diese wird im laufenden Spiel beurteilt.

Ein erster globaler Tile-Ersatz setzte Felsfragmente an unpassenden Stellen ein,
weil mehrere Motive dieselben kleinen Spiel-Tiles verwenden. Dieser verworfene
Versuch liegt nur noch im Arbeitsordner (`rejected-global-tiles-v1`). Das
auswählbare Paket enthält deshalb **312 kontextgebundene Bildstücke für 178
Originalschlüssel**. Ein Bildstück greift nur, wenn die im Rezept erfassten
Nachbar-Tiles und Spiegelungen passen. Es gibt 134 wiederholte Vorkommen;
deren Farbabweichungen stehen im Prüfbericht `motifs.json`.

```powershell
# Rezept + source/bg1.png/.tsv + source/bg2.png/.tsv + generated/*.png
# liegen zusammen in einem Arbeitsordner. Immer ein neues Ausgabeziel wählen.
python tools/hd/hd_motifs.py --recipe build/hd_work/pilot-1-1-v1/recipe.json --out build/hd_packs/my-pilot-v3
```

Nur vollständige, im TSV verzeichnete Tiles innerhalb des Ausschnitts werden
importiert. Die generierte Transparenz bleibt erhalten, begrenzt durch die
Originalmaske. Alle Referenzen und Bilder erhalten SHA-256 im Prüfbericht.
Der Import prüft Maße, Seitenverhältnis, Spiegelung und Referenzkonsistenz vor
dem Schreiben. Ein belegtes Ausgabeziel wird abgelehnt.

`editable/` enthält die 80×80-Bildstücke und **`contexts.json`**. Diese Datei
beim Bearbeiten behalten! `hd_tiles.py export/build` erhält sie automatisch.
Die PNG-Dateinamen identifizieren hier ein bestimmtes Bildstück, nicht direkt
den Originalschlüssel. Die Zuordnung steht in `motifs.json` und `pack.json`.
Die alte Standbildvorschau unterstützt Kontextpakete nicht und verweist auf
`sciv_play.py hdshot`; der Live-Renderer und Debug-Marker unterstützen sie.

Nächster Qualitätsschritt: zusammenhängende Motive vollständig abdecken,
KI-Abweichungen an Trittflächen und Materialübergängen korrigieren, danach
Komposition mit echter HD-Transparenz und Simon-Animationsprobe. Die vorliegenden
Bildstudien sind **noch keine Freigabe für die gesamte Spielgrafik**.

### Einzelne Tiles bearbeiten

Ein Paket lässt sich in einzelne `SCHLUESSEL.png` exportieren. Originale
behalten, Motive in einer neuen Variante bearbeiten, anschließend als eigenes
Paket bauen. Die Bilddateien behalten den Schlüssel im Dateinamen und werden
unverkippt gespeichert; die Laufzeit übernimmt Spiegelungen und Scrollen.

```powershell
python tools/hd/hd_tiles.py export --pack build/hd_pack --out build/hd_work/editable
# Für 10× die Motive als 80×80 RGBA-PNG ausarbeiten.
python tools/hd/hd_tiles.py build --tiles build/hd_work/my-80px-tiles --pack build/hd_packs/my-4k --scale 10
```

Der Export verlangt ein leeres Ziel, damit bereits bearbeitete Bilder erhalten
bleiben. Der Paketbauer prüft alle Dateinamen und Maße vor dem Schreiben und
ändert keine Bildgröße. Für unabhängige Varianten unterschiedliche Paketordner
benutzen. Man kann auch nur wenige Tiles ersetzen; der Rest bleibt original.

## Benutzung

1. Das Spiel aus `build/` starten. **Escape → HD graphics → Collect graphics
   while playing** aktivieren, zurück ins Spiel und die gewünschten Abschnitte
   spielen. Die Sammlung bleibt beim nächsten Start eingeschaltet.
2. An interessanten Stellen **Strg+D** drücken und einen Debug-Marker speichern.
   Neue Marker enthalten zusätzlich `lines.bin` mit den PPU-Registern jeder
   Bildzeile. Ältere Marker haben diese Daten noch nicht.
3. Das Spiel regulär schließen, damit ausstehende Bilder fertig geschrieben
   werden. Im Projektordner ausführen:

   ```powershell
   python -m pip install -r tools/hd/requirements.txt
   python tools/hd/hd_pipeline.py --build build
   ```

   Standard ist Real-ESRGAN ncnn-vulkan, Modell `realesrgan-x4plus-anime`, 4×.
   Die vorhandene lokale Installation liegt außerhalb des Repos:
   `D:\Super Castlevania IV Recomp\tools-external\realesrgan\`.
   Der Ordner muss die EXE, ihre DLLs und `models/` enthalten. Das Werkzeug
   benötigt einen Vulkan-fähigen Grafiktreiber; Modelle und EXE gehören nicht
   ins Spiel-Repo. Es werden nur die lokalen exportierten Bilder verarbeitet.

4. Ergebnis: `build/hd_pack/pack.json` und `atlas_NNN.png`.
   Wenn ein neuer Marker vorliegt, erzeugt das Skript darin `hd_preview.png`
   (links rekonstruierte Originalgrafik, rechts HD), `hd_preview_hd.png` und
   `hd_preview_native.png`.

Weitere Abschnitte sammeln und denselben Befehl erneut ausführen. Frühere
Aufnahmen bleiben erhalten. Unveränderte Aufnahmen mit denselben Einstellungen
werden beim Hochskalieren übersprungen. Geänderte Quellbilder werden über ihren
SHA-256 erkannt; `--force` erzwingt eine Neuberechnung.

Zum Prüfen ohne KI-Hochskalierer:

```powershell
python tools/hd/hd_pipeline.py --build build --method nearest
```

`nearest` vergrößert Originalpixel unverändert. Es prüft Erfassung, Ausschnitte,
Spiegelung und Paketzuordnung. Es erzeugt keine neuen Bilddetails.

Einzelne Schritte:

```powershell
python tools/hd/hd_upscale.py --dump build/hd_dump --work build/hd_work
python tools/hd/hd_build_pack.py --dump build/hd_dump --work build/hd_work --pack build/hd_pack
python tools/hd/hd_preview.py MARKER-ORDNER --pack build/hd_pack
```

Ein anderer lokaler Hochskalierer kann mit `--method command --command
'tool --input "{input}" --output "{output}" --scale {scale}'` angebunden werden.
Er erhält einen Ordner mit RGB- und Maskenbildern und muss PNG-Dateien mit
denselben Namen und exakt der gewählten Vergrößerung (1–10) ausgeben. Es wird
keine Shell gestartet; Platzhalter werden pro Argument ersetzt.

## Vorhandene Grafikbögen

In `C:\Users\Gaming\Downloads\assets` liegen 33 PNG-Bögen: Simon, Gegner,
Bosse, Menügrafik und Hintergründe. Hintergrundbögen für Stages 1–8, 10 und
11 sind vorhanden; ein Hintergrundbogen für Stage 9 liegt dort derzeit nicht.
Die Quellen bleiben unverändert außerhalb des Repos. Ein lokaler Katalog mit
Abmessungen, Dateinamen und SHA-256 lässt sich so erneuern:

```powershell
python tools/hd/hd_sources.py
```

Ergebnis ist `build/hd_work/source_sheets.json`. Die Bögen sind hilfreiche
Quellen für vollständige Motive und Nachbarschaften beim Hochskalieren. Sie
enthalten jedoch auch Beschriftungen, Credits und farbige Trennflächen.
Ein automatischer Import dieser Bögen ist noch nicht implementiert. Dazu
müssen Bildregionen und Transparenz ausgewählt und den Spiel-Tiles zugeordnet
werden. Die aktuelle Paketkette verarbeitet die bereits zugeordneten
256×224-Ebenenbilder des Sammlers.

## Formate und Zuordnung

- `hd_dump/collect.txt`: gespeicherter Sammelschalter. Im Menü deaktivieren
  oder bei geschlossenem Spiel löschen. Für Tests überschreibt
  `SNESRECOMP_HD_COLLECT=0|1` den gespeicherten Wert.
- `hd_dump/tiles.tsv`: Schlüssel, Farbtiefe, Palette als 16-Bit-Hexwerte und
  64 Farbindex-Pixel je Tile. Jeder Schlüssel enthält die unveränderten
  Pixelindizes und Palette (außer transparenter Farbe 0), keine VRAM-Adresse.
  Dadurch bleibt die Zuordnung bei DMA-Umladungen und Tilemap-Spiegelungen
  stabil. Identische Schlüssel können in mehreren Sitzungen vorkommen.
- `hd_dump/captures/<szene>_b<block>/<ebene>_<sitzung>_<frame>.png`: einzelne
  Ebene in 256×224, RGBA. `.tsv` daneben enthält `x, y, Schlüssel, Spiegelung`
  (tabgetrennt; Spiegelung Bit 0 horizontal, Bit 1 vertikal). Eine Bilddatei
  wird nur gespeichert, wenn sie noch benötigte vollständige Tiles enthält.
- `hd_work/up/`: hochskalierte Ebenen, RGB und Alpha separat verarbeitet;
  `upscale.json` und `sources.json` halten Einstellungen und Quellprüfsummen.
- `hd_pack/pack.json`: Version 1, Faktor, Tilegröße, Atlasgröße,
  Verarbeitungseinstellungen und Zuordnung `Schlüssel → [Atlas, Zelle]`.
  Atlanten sind 2048×2048 RGBA, zeilenweise belegt. Ein Tile ist bei 4× 32×32, bei 10× 80×80.
  `hd_common.py` und `src/hd_render.cpp` lesen dasselbe Format.
- Optional `requires: ["tile-context-v1"]` und `contexts`: Originalschlüssel
  → Liste `{image, flip, neighbors}`. `image` referenziert ein Bildstück in
  `tiles`; jeder Nachbar ist `[dx, dy, Originalschlüssel, flip]`, Abstand in
  8×8-Tiles. Unterstützt BG1–3; Prüfung unter den tatsächlichen Zeilenregistern,
  auch hinter Vordergrundobjekten und an transparenten Stellen. Globale
  Spiegelung wird mitgeführt. Keine passende Nachbarschaft bedeutet Original.
  Höchstens 16.384 Kontexte, 32 Nachbarn je Kontext, Abstand ±16 Tiles.
  Unbekannte benötigte Funktionen und ungültige Kontexte lehnt der Loader ab,
  wobei das zuletzt gültige Paket aktiv bleibt. Der Cache verwendet Tile-Zelle,
  Originalschlüssel und Spiegelung. Register-/HDMA-, VRAM- und Palettenänderungen
  sowie relevante Zeilenbandgrenzen verwerfen ihn. Bei unveränderter Zuordnung
  wird das Ergebnis über die Zeilen eines Tiles wiederverwendet.
- `lines.bin`: 225 Datensätze à 32 Byte, little-endian; Datensatz `i`
  gehört zu PPU-Zeile `i`, Bildschirmzeile `i−1`. Layout in `hd_collect.h`.

Der Hochskalierer sieht ganze Ebenenbilder und damit die Nachbartiles.
`hd_build_pack.py` schneidet vollständige 8×8-Vorkommen daraus aus, spiegelt
sie zurück und kombiniert pro Schlüssel standardmäßig bis zu 24 Kandidaten
per Median. Die Schärfe und der Stil bleiben gestalterisch zu beurteilen;
unterschiedliche Nachbarschaften können trotzdem sichtbare Tile-Nähte erzeugen.

## Grenzen dieser Stufe

- Sammlung: BG1–BG3 in Modus 0/1 (2/4 bpp), 8×8/16×16-Tiles und native
  Sprites. HDMA-Scroll wird pro Zeile erfasst. Überlappte Sprite-Tiles und
  Teilstücke an Bildrändern werden nicht als vollständige Vorkommen verwendet.
- Die Sammlung liest VRAM/CGRAM/OAM am Ende des Felds. Änderungen dieser
  Speicher mitten im Bild, Mosaic, Fenster und Farbmathematik sind nicht in
  `lines.bin` enthalten. Die Ebenenbilder zeigen rohe Palette und Transparenz,
  nicht alle Effekte des fertigen Bilds. Benutzerdefinierte Charakterbilder
  und die gestalteten Widescreen-Randspalten sind nicht enthalten.
- Die Standbild-Vorschau unterstützt zunächst **Modus 1** im nativen
  256×224-Feld mit Prioritäten und Helligkeit. Fenster, Farbmathematik,
  Sprite-Limits/-Rotation und Mode 7 fehlen. Fehlende HD-Tiles werden aus den
  Originalpixeln vergrößert. Andere Modi werden mit einer Fehlermeldung abgelehnt.
- Die Aufnahmen sammeln Spielgrafik aus der eigenen ROM. Alle Exporte,
  Modelle, Pakete und Vorschauen bleiben lokal und gitignored.

PNG-Schreiben läuft in einem Hintergrundthread mit begrenzter Warteschlange.
Bei Schreibfehlern stoppt die Sammlung und meldet dies im Menü und `game.log`.
Bei einem erzwungenen Prozessende können noch ausstehende Bilder fehlen.

## Tile-/Kontext-Renderer: Umfang und Grenzen (älterer Paketpfad)

`src/hd_render.cpp` ordnet nach jeder nativen PPU-Zeile Ersatztiles anhand
von Pixeln und Palette zu. Dadurch berücksichtigt er die tatsächliche
Zeilenpalette, HDMA-Scroll und VRAM-Änderungen. Die Bildberechnung erhält
unveränderliche Zeilendaten und läuft anschließend auf bis zu acht CPU-Threads;
`SNESRECOMP_RENDER_WORKERS=1` erzwingt den seriellen Vergleichspfad.

- BG1–3- und Sprite-Details in Modus 0/1, 8×8/16×16-BG-Tiles,
  horizontale/vertikale Spiegelung, normale Sprite-Prioritäten/-Limits,
  Fenster, Weltkanten-Spiegelung und Darstellungs-VRAM der Randkorrekturen.
- **Die Sichtbarkeit und Silhouetten bleiben auf dem Originalpixelraster.**
  HD verändert die Details innerhalb sichtbarer Originalpixel. Teiltransparentes
  Ersatzmaterial wird dort mit der ursprünglichen Farbe gemischt. Es kann
  keine neue hochauflösende Kontur außerhalb der alten Silhouette erzeugen.
  Dafür muss künftig jede Ebene vor ihrer Transparenzentscheidung in HD
  zusammengesetzt werden. Das ist besonders für sauber neu gezeichnete Figuren
  wichtig und noch offen.
- Helligkeit und aktivierte Farbmathematik werden auf die Ersatzfarben in
  RGB8 angewendet. Unveränderte Samples bleiben bitgenau wie die native PPU;
  neue Farben sind absichtlich nicht auf die SNES-5-Bit-Palette beschränkt.
- Mode 7, Modi 2–6, Mosaic-Ebenen, Interlace, Hires/Direct Color sowie nicht
  unterstützte Host-Transformationen fallen auf Originalgrafik zurück.
  Benutzerdefinierte Character-Workshop-Körper bleiben ihr bisheriges Bild.
- Pack-Limits: Faktor 1–10, Atlas maximal 4096×4096, höchstens 256 MiB
  entpackte Tile-Pixel. Ein Ladefehler ersetzt kein laufendes gültiges Paket.
- **Strg+D** speichert zusätzlich `hd_screen.png`, wenn ein HD-Feld vorliegt,
  und HD-Einstellungen in `marker.json`. `screen.png`, Spielzustand und
  Thumbnail bleiben für reproduzierbare Vergleiche nativ.
- Die Standbild-Rekonstruktion `hd_preview.py` hat die oben genannten engeren
  Grenzen; für tatsächliche Live-Bilder `sciv_play.py hdshot` verwenden.

```powershell
python tools/sciv_play.py hd pack build/hd_pack
python tools/sciv_play.py hd on
python tools/sciv_play.py hd scale 10
python tools/sciv_play.py wait 1
python tools/sciv_play.py hdshot build-audit/live-hd.png
python tools/sciv_play.py hd off
```

Test-Overrides: `SNESRECOMP_HD_ENABLED`, `SNESRECOMP_HD_PACK`,
`SNESRECOMP_HD_SCALE`, `SNESRECOMP_HD_LAYERS`. Keine Änderungen an ROM,
Simulation, Kollisionen oder Savestate-Format. Der Originalpfad behält seine
native Ausgabegröße und Pixel.

Noch auszuarbeiten: hochwertige 80×80-Motive mit konsistentem Stil und
sauberen Nähten, vollständige Figurenanimationen, echte HD-Silhouetten,
Mode-7-Ersatzgrafiken und eine Szenenprüfung über das gesamte Spiel.

## Historische gemeinsame Tile-Bibliothek und Vergleichsstrecke (19.10.)

Wiederkehrende Bausteine werden einmal gestaltet und referenziert. Der Katalog
erkennt Originalschlüssel über mehrere Aufnahmen hinweg und zählt ihre
Vorkommen. H/V-Spiegelungen benötigen keine zusätzlichen Quellbilder.
Palettenvarianten werden als Familie angezeigt, bleiben aber getrennte Schlüssel.
Die Zählung beschreibt die Aufnahmen, nicht die Anzahl eindeutiger Weltpositionen.

```powershell
python tools/hd/hd_catalog.py --dump artwork-local/captures/pilot --out artwork-local/library --scale 10
```

`native/<Originalschlüssel>.png` dient als Referenz. Die zugehörige neue Grafik
liegt unter `shared/<Originalschlüssel>.png`: 80×80 echte RGBA-Pixel, in der
ungespiegelten Orientierung. Nach dem Kataloglauf enthält `shared_tiles.json`
die verfügbaren Quellen. Vorhandene Quellbilder werden niemals überschrieben.
Aktuell: 2.958 Originalschlüssel, 48.354 aufgezeichnete Vorkommen, 1.985
Palettenfamilien und **47 gemeinsame HD-Quellen** für Mauerwerk/Treppe.
Sie sind ein testbarer Stilpilot; sichtbare Nähte, wechselnder Steinmaßstab und
die rote Treppen-/Reliefstruktur benötigen noch Überarbeitung. Die weiteren
gemalten Felsmotive bleiben kontextgebundene Varianten.

Ein Motiv-Rezept kann auf dieselbe Bibliothek verweisen:

```json
{
  "version": 1,
  "scale": 10,
  "shared_library": "../library/shared_tiles.json",
  "motifs": [
    {"name": "masonry", "reference": "source/bg1.png", "rect": [0, 128, 96, 64], "artwork": "generated/masonry.png"}
  ]
}
```

Bibliothekspfade gelten relativ zur Indexdatei. Optionales `shared_tiles` direkt
im Rezept überschreibt einzelne Einträge; dessen Pfade gelten relativ zum Rezept.
Gemeinsame Quellen ersetzen passende Originalschlüssel in allen registrierten
Motiven. Das Motivbild liefert noch nicht abgedeckte Bausteine; es darf entfallen,
wenn sämtliche eingeschlossenen Schlüssel in der Bibliothek vorliegen.
Die bisherigen Nachbarschaftsprüfungen bleiben erhalten: Eine Wiederholung in
einer neuen Nachbarschaft muss zunächst registriert werden.

Der Import speichert pixelidentische Bildstücke nur einmal, auch wenn mehrere
Platzierungen darauf zeigen. `motifs.json.reuse` zeigt die tatsächliche Ersparnis.
Eine Änderung der gemeinsamen Quelle und erneuter Paketbau aktualisiert alle
Referenzen. Unterschiedliche gemalte Varianten werden nicht automatisch
vereinheitlicht: Der bestehende Pilot hat weiterhin 312 unterschiedliche Bilder
für 178 Originalschlüssel. Sein Neubau unter `artwork-local/packs/pilot-reuse-v1`
erhält alle 312 Platzierungen pixelgenau. Globale Zuordnung unpassender
Motivfragmente würde die bereits beobachteten Flickstellen zurückbringen.

Originalquellen, Prompts, Aufnahmen und Startzustände liegen dauerhaft unter
`artwork-local/` (gitignored), zusätzlich mit SHA-256-geprüfter Kopie unter
`D:\Super Castlevania IV Recomp\backup\hd-artwork\2026-10-19-hd-library`.
Der Nutzer-Build enthält das bisherige Pilotpaket zum Vergleich und zusätzlich
`hd_packs/pilot-1-1-shared-v5` (HD aktivieren, 10×).

### Gemeinsame Bögen importieren und registrieren

`assets/hd/shared_blocks_1_1.recipe.json` enthält die vollständigen Prompts,
Originalreferenzen und die Schlüsselbelegung der fünf mit dem eingebauten
Imagegen erzeugten Bögen. Quellen liegen in
`artwork-local/shared-blocks-v1/generated/`; der finale Extrakt liegt in
`artwork-local/shared-blocks-v1/library-expanded/`. Pro Originalschlüssel gibt
es eine ungespiegelte 80×80-Datei. Die Bögen liefern mindestens 256 echte Pixel
pro Zelle und werden heruntergerechnet. `null` im Raster bezeichnet eine
unbenutzte Zelle. Exaktes Rasterseitenverhältnis ist erforderlich; gebrochene
Zellgrenzen werden vor dem Ausschneiden auf das Zielraster registriert.

```powershell
# Immer einen neuen Ausgabeordner verwenden; vorhandene Dateien bleiben erhalten.
python tools/hd/hd_shared.py extract --recipe assets/hd/shared_blocks_1_1.recipe.json --dump artwork-local/captures/pilot --out artwork-local/shared-blocks-v1/library-rebuild
python tools/hd/hd_shared.py pack --library artwork-local/library/shared_tiles.json --dump artwork-local/captures/pilot --dump artwork-local/captures/upper-stairs --scene level_b00 --layers bg1 --base artwork-local/packs/pilot-reuse-v1 --out artwork-local/packs/shared-rebuild
python tools/hd/hd_catalog.py --dump artwork-local/captures/pilot --dump artwork-local/captures/upper-stairs --out artwork-local/library --scale 10
```

Der erste Befehl importiert separat; neue geprüfte Quellen anschließend gezielt
nach `library/shared/` übernehmen und den Katalog erneuern. Bestehende Quellen
vor einer beabsichtigten Überarbeitung sichern. Der Paketbau liest den zentralen
Index und setzt alle darin enthaltenen Schlüssel voraus: Jeder muss mindestens
eine passende Aufnahme in der gewählten Szene/Ebene haben. Für spätere größere
Bibliotheken einen Index mit der gewünschten Teilmenge verwenden.

Die Referenzprüfung erkennt versehentlich gespiegelte/falsche Zellen; zu kleine
Bilder werden abgelehnt. `opaque_material: true` verlangt deckende Bögen, bevor
die Originalmaske aufgetragen wird. Das ist beim jetzigen Renderer wichtig:
Halbtransparentes Material blendet sonst Originalpixel ein. Transparente
Originalbereiche bleiben erhalten, glatte Außenkonturen entstehen dadurch nicht.

`pack` erhält andere Motive eines kontextgebundenen Basispakets gleicher Skala;
alte Varianten der gewählten gemeinsamen Schlüssel werden ersetzt. Identische
Bilder werden nach Inhalt nur einmal gespeichert. Nachbarschaften bleiben
geschützt, einschließlich Spiegelungen. Regelvereinfachung entfernt nur eine
stärkere Regel, wenn eine bereits vorhandene schwächere Regel für dasselbe Bild
und dieselbe Spiegelung sie vollständig abdeckt; die Menge erlaubter Umgebungen
bleibt gleich. Unterschiedliche Motivbilder werden nicht so vereinfacht.

Finaler Pilot: 47 Quellen, 2.361 erfasste Verwendungen, 659 unterschiedliche
Nachbarschaften und 375 verbleibende Regeln, 255 Bilder einschließlich der
erhaltenen Felsmotive. `shared-receipt.json` enthält Quellen-/Aufnahme-/Basispaket-
Prüfsummen und Zählungen. Eine neue Umgebung braucht eine neue Aufnahme, keine
neue KI-Grafik für einen bereits vorhandenen Schlüssel. Die rechte Mauer wurde
so durch `captures/upper-stairs` ergänzt. Acht Frames ab
`fixtures/block-1-1-upper-stairs/state.sav` in einem frischen Sammelprozess
(`SNESRECOMP_HD_COLLECT=1`) lieferten die zusätzlichen Original-Zuordnungen.
Der Sammler nimmt bereits häufig gesehene Schlüssel nicht unbegrenzt erneut auf.

Aktuelles Quellen-/Paket-Backup mit SHA-256-Prüfung:
`D:\Super Castlevania IV Recomp\backup\hd-artwork\2026-10-19-shared-blocks`.
Finale Route, Bilder und Messung: `artwork-local/shared-blocks-v1/review/v5/`.
Elf native Prüfpunkte unverändert; HD-Bilder vor/nach Regelvereinfachung identisch.
240 ungedrosselte Frames bei Kamera146/10×: ca.58 FPS auf diesem Rechner,
noch kein Nachweis stabiler 60 FPS für die gesamte Strecke.

```powershell
python tools/test_hd_route.py --rom "Super Castlevania IV (USA).sfc" --build-dir build-lua --pack artwork-local/packs/pilot-reuse-v1 --fixture artwork-local/fixtures/block-1-1/state.sav
python tools/test_hd_contours.py --marker artwork-local/fixtures/contour-reference
```

Die versionierte Strecke `assets/hd/block_1_1.route.json` prüft elf Punkte:
Start, linker Rand, Anlauf, zwei Treppenpositionen, Abstieg, Sprung, Landung,
Peitsche, Erholung und Rückweg. Zustands-/Höhenprüfungen stellen sicher, dass die
Aktionen tatsächlich stattfinden. Abstieg endet durch gehaltenes Down geduckt
(Y=177); im Stehen ist Y=165. Drei Durchläufe vom selben Savestate vergleichen
Original → HD → Original: native Bilder und benannte RAM-Felder müssen gleich
bleiben. Bericht enthält ROM-/Build-/Paket-/Strecken-/State-Prüfsummen.
Das ist ein Checkpoint-Test, kein vollständiger Frame-CRC-Vergleich oder Recorder.
Ohne `--fixture` erzeugt das Werkzeug den Startzustand aus dem Boot-Skript.

`test_hd_contours.py` beweist im **Offline-Referenzrenderer** Subpixel-Alpha,
Konturen außerhalb der nativen Silhouette, Durchsicht auf BG2, Sprite-Priorität
und Spiegelungen. Ein echter Marker wird zunächst nativ pixelgenau rekonstruiert.
Das cyanfarbene Diagnosebild ist kein Artwork. Die damalige Offline-Probe ist inzwischen durch den oben beschriebenen
Live-Szenenpfad ergänzt. Allgemeine bewegte Sprite-Stapel bleiben offen.

Für die Fortsetzung gilt der aktuelle Nutzerbild-Import oben; diese älteren
Materialversuche werden nicht automatisch weiter erzeugt.

## Tests

```powershell
python tools/test_hd_ppu.py
python tools/test_hd_motifs.py
python tools/test_hd_catalog.py
python tools/test_hd_shared.py
python tools/test_sciv_state.py
python tools/test_hd_contours.py
python tools/test_hd_render.py --rom "Super Castlevania IV (USA).sfc" --build-dir build-lua
python tools/test_hd_ui.py --rom "Super Castlevania IV (USA).sfc" --build-dir build-dev --pack build/hd_pack
python tools/test_hd_pipeline.py --build-dir build-dev
python tools/test_hd_pipeline.py --rom "Super Castlevania IV (USA).sfc" --build-dir build-dev
```

Ohne ROM: Spiegelungen, Alpha, Paket-Roundtrip, Cache und ungültige Bildmaße.
Mit ROM zusätzlich: Sammlung gegen unveränderte Bild-CRCs, jedes gespeicherte
Tile-Vorkommen, exakter Wiederaufbau eines 1-1-Markers, Nearest-HD-Identität
und Erhalt früherer Aufnahmen nach einem zweiten Spielstart.
