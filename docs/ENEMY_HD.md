# Gegner-PNGs und Live-Werkstatt

`Gegner_Werkstatt_starten.cmd` startet ein eigenes Desktopfenster mit Original
und Redesign nebeneinander. Beide Ansichten verwenden dieselben Bewegungsdaten
des Originalmotors. Bedienung: [ENEMY_WORKSHOP.md](ENEMY_WORKSHOP.md).

## Fertige Skelett-Sammlung

Neben dem Projekt unter `Assets (ausgeschnitten)/Gegner/02_Skelette_Alle_Aktionen`
liegen **5 Körperposen** (2 Gehschritte, Ausholen, Werfen, Ausklang),
**3 Knochen-Drehbilder** und **10 Zerfallseffekte** aus dem nativen Ablauf.
Das erweitert das ältere Zwei-Gehbilder-Startpaket `01_Skelette`.
Die alten Dateien bleiben erhalten. `$11` und `$12` sind Skelettvarianten;
`$12` ist der Knochenwerfer. Die Typnummer allein bezeichnet keine Spielebene.

55 unterschiedliche Arbeits-PNGs: 18 ganze Bilder und 37 optionale Einzelteile.
73 native Zuordnungen teilen sich diese Dateien. Die Kopie `Gegner/Werkstatt`
ist der Standardarbeitsordner der App. Daneben liegt die fertige ZIP
`Skelette_Alle_Aktionen_2026-10-24.zip`. Originalbilder entstehen lokal aus der
eigenen USA-ROM und gehören nicht ins Git.

`VORLAGEN.html` zeigt die Bilder. Nur **artwork** bearbeiten; **references**
und **project.json** aufbewahren. PNGs sind bereits 387×387 Pixel groß:
4,03125× zur nativen 96×96-Fläche. Ganze transparente Leinwand, Proportion und
Dateinamen behalten. Andere proportionale Maße bis 4096×4096 funktionieren
ebenfalls. Es gibt keine Pflicht zu 10×.

## Import ins Spiel

Die Werkstatt lädt gespeicherte PNGs live. **Paket zum Einbauen erstellen**
schreibt einen neuen Ordner unter `artwork-local/enemies`. Nur veränderte PNGs
werden bytegleich übernommen; unbearbeitete vergrößerte Vorlagen bleiben original.

Zum Einbauen `HD_Import_starten.cmd` öffnen, den Werkstatt-Arbeitsordner wählen,
**Fertige PNGs prüfen / Paket erstellen** und anschließend **Paket in beide
Spielversionen einbauen** anklicken. Die bisherige Auswahl wird gesichert.
**Vorbereitete Skelett-Bilder öffnen** bevorzugt jetzt `Gegner/Werkstatt`.
Details: [HD_IMPORT.md](HD_IMPORT.md).

Alternativ: `python tools/enemy_hd.py pack ARBEITSORDNER ZIELORDNER`.
Den neuen Packordner nach `enemy_packs` neben der EXE kopieren und in den
HD-Einstellungen auswählen. Fehlende Posen bleiben original.

Eine geänderte ganze Pose hat Vorrang vor ihren Einzelteilen. Ohne neue ganze
Pose kann jedes erfasste native Teil separat ersetzt werden. Ganze Posen mit
unterschiedlichen nativen Prioritäten/Farbrechenregeln fallen auf Einzelteile
beziehungsweise Originalgrafik zurück. Einzelteil-PNGs behalten dieselbe
Leinwand und Verankerung wie ihre ganze Pose.

## Native Zuordnung

`enemy_packs/PACK/enemies.json` enthält `version: 1` und `frames`, je mit `id`,
`actor_type`, `pose`, `image`, `display_size` und `anchor`. Die IDs erzeugt der
Renderer aus Actor-Typ, nativem Metaspritezeiger und spiegelungsunabhängigen
Farbindex-Pixeln. Einzelteile hängen `__teil-N` an diese ID; N ist der originale
Metasprite-Teilindex, kein wechselnder OAM-Slot. Palette und Quellauflösung
gehören nicht zum Schlüssel. Referenzen behalten den zuerst aufgenommenen
Farbstand; Palettenvarianten und Blitze benötigen für eine farbexakte Vorschau
noch eine zusätzliche Zuordnung.

Die normale Referenzfläche ist 96×96 mit Anker 48×48. Größere erkannte Figuren
erhalten 256×256 mit Anker 128×128, entsprechend 1032×1032 Arbeits-PNGs bei
4,03125×. Bis zu 4096 Zuordnungen und 64 Millionen Quellpixel pro Pack sind
zulässig. Figuren außerhalb dieser Fläche oder mit unvollständiger
OAM-Zuordnung bleiben original.

`src/enemy_pack.cpp` liest Actor-Datensätze `$0580..$0EBF`, Metasprites aus
ROM-Bank `$04` und tatsächlich übertragene OAM. Jedes Teil muss in Position,
Größe und Attributwort exakt passen. Spieler, unbekannte Teile und andere
OAM-Slots werden nicht vom Ersatzbild verdeckt. Im Spiel bleiben native
OBJ-Reihenfolge, Zaun-/Hintergrundpriorität, Fenster und Farbrechnung wirksam.
PNG-Aufnahme und HD-Ersatz schreiben keine Gastdaten.

## Gezielte Prüfungen

- `tools/test_enemy_workshop_native.py`: ROM-Boot, 180 echte Felder, zwei Geh-,
  drei Wurf-, drei Knochen- und zehn Zerfallbilder plus Einzelteile.
- `tools/test_enemy_workshop_live.py --recording AUFNAHMEORDNER`: Live-Speichern,
  unvollständige/fehlende PNGs, Wiederherstellung, globale OAM-Reihenfolge,
  Vorrang ganzer Posen, Einzelteile, Altdaten und bytegleicher Import.
- `tools/test_enemy_hd.py` und `tools/test_enemy_workshop_renderer.py`:
  native Masken, Nachbarteile, Spiegelung, 387-/1032-PNGs, große Leinwand und
  Prioritätsrückfall in unabhängig kompilierten C++-Probes.
- `tools/test_enemy_workshop_live_render.py`: echter Renderer, einzelnes
  Skelettteil, Zaunverdeckung sowie identische 128 KiB WRAM und
  VRAM-/CGRAM-/OAM-Dumps mit und ohne Grafikpaket.
- `tools/test_enemy_catalog_data.py`: 94 eindeutige Profile, 83 sichtbar in
  zwei kurzen nativen Durchläufen; konservative Gegner-/Objektbeschriftung.

Sichtbarkeit beweist weder vollständige Animationen noch einen Spieldurchlauf.
Katalogaudits und Bilder bleiben unter `artwork-local/enemy-catalog-audit`.
