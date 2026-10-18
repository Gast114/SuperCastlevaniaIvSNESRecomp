# HD-Grafik vorbereiten

Stand: 2026-10-18. Die erste Stufe sammelt Spielgrafiken, skaliert sie offline
und baut ein Grafikpaket samt Vorschau. **Das Paket wird noch nicht live im
Spiel dargestellt.** Der Schalter im Menü aktiviert die Sammlung.

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
denselben Namen und exakt der gewählten Vergrößerung (1–4) ausgeben. Es wird
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
  Atlanten sind 2048×2048 RGBA, zeilenweise belegt. Ein Tile ist bei 4× 32×32.
  `hd_common.py` liest das Format auch für den späteren Renderer.
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

## Nächste Stufe: Darstellung im Spiel

Der Desktop-Presenter rendert derzeit mit Faktor 1; das vorhandene
`PpuBindMode7HdSurface` behandelt Mode 7, aber keine HD-Ersatzgrafik für
normale BG-/Sprite-Tiles. Für echte HD-Grafik im Spiel fehlen noch:

1. Paket laden und dessen Schlüssel im PPU-Zeilenrenderer zuordnen.
2. HD-Ausgabefläche an Presenter, Screenshot, eingefrorenes Bild und
   Debug-Marker anbinden.
3. Prioritäten, transparente Kanten, Fenster, Farbmathematik und Widescreen
   pro HD-Pixel komponieren; mit unveränderten Originaltiles zurückfallen.
4. Mit Marker-Szenen, Sprite-Überdeckungen, Kamerabewegung und Mode 7 prüfen.

Die Spielsimulation und gespeicherte ROM bleiben dabei unabhängig von den
gewählten Ersatzgrafiken.

## Tests

```powershell
python tools/test_hd_pipeline.py --build-dir build-dev
python tools/test_hd_pipeline.py --rom "Super Castlevania IV (USA).sfc" --build-dir build-dev
```

Ohne ROM: Spiegelungen, Alpha, Paket-Roundtrip, Cache und ungültige Bildmaße.
Mit ROM zusätzlich: Sammlung gegen unveränderte Bild-CRCs, jedes gespeicherte
Tile-Vorkommen, exakter Wiederaufbau eines 1-1-Markers, Nearest-HD-Identität
und Erhalt früherer Aufnahmen nach einem zweiten Spielstart.
