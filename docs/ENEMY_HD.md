# Gegnergrafiken vorbereiten

Der erste unterstützte Gegner ist das laufende Skelett in A02, auf beiden
Spielebenen. Das Spiel sammelt seine tatsächlich sichtbaren Animationsbilder
automatisch. Neue HD-Zeichnungen werden noch nicht mitgeliefert.

Ein fertiger Arbeitsordner mit den zwei Gehschritten liegt unter
`artwork-local/import-workspaces/skelette-2026-10-23`. `VORLAGEN.html` zeigt die
Referenzen als Galerie. Der gemeinsame HD-Import erkennt dessen `project.json`
und erstellt daraus ein Gegnerpaket. Manuelles Bearbeiten der Zuordnung ist
nicht nötig.

## Für die Grafikarbeit

1. In den HD-Einstellungen **Gegner-Referenzen sammeln** einschalten und an den
   Skeletten vorbeispielen. Die Aufnahme läuft im Hintergrund.
2. Die Referenzen liegen im Spielordner unter `enemy_packs/native-template`.
   Daraus erstellt `tools/enemy_hd.py prepare REFERENZEN MEIN_ORDNER` einen
   Arbeitsordner mit `references`, `artwork` und einer kurzen Anleitung.
   Identische Skelettbilder beider Spielebenen werden zusammengefasst: Für die
   beiden Gehschritte genügen `Skelett_Schritt_01.png` und
   `Skelett_Schritt_02.png`. Jede Zeichnung gilt automatisch auf beiden Ebenen.
3. Die PNGs in `artwork` bearbeiten. Das vollständige transparente Bild und die
   Position gegenüber der Referenz beibehalten. Die Arbeitsauflösung ist frei:
   beispielsweise 387 × 387 für eine 96 × 96-Referenz, also 4,03125-fach. Es gibt
   keine Pflicht zu exakt 10-facher Auflösung. Nicht auf sichtbare Pixel trimmen.
4. Mit `tools/enemy_hd.py pack MEIN_ORDNER SPIELORDNER/enemy_packs/MEIN_PACK` einen
   neuen Packordner erstellen und diesen in den HD-Einstellungen auswählen.

Nur tatsächlich geänderte PNGs werden übernommen. Unbearbeitete Posen bleiben
original. Bestehende Arbeitsordner und Packs werden nicht überschrieben. Die
Quell-PNGs behalten ihre exportierte Auflösung; es wird nichts vorab hochskaliert.
Spiegelung, Animationszuordnung und Position übernimmt das Spiel.

Ein geändertes, gültiges PNG wird beim Spielen automatisch neu geladen. Während
Photoshop eine Datei gerade schreibt, bleibt das zuletzt erfolgreich geladene
Bild erhalten. Der HD-Schalter und die OBJ-Ebene gelten auch für Gegner.

## Umfang des ersten Piloten

- Native A02-Skelette: Actor-Typen `$0011` und `$0012`, einschließlich der nativen
  Animationsbeschreibungen `$8AF4` und `$8B05`, soweit tatsächlich aufgenommen.
- Beliebig große PNGs bis 4096 × 4096, freie Sourceauflösung, transparenter Rand,
  getrennte Posen, horizontale und vertikale Spiegelung.
- Vollständige Metasprites: Ein neues Bild ersetzt alle eindeutig zugeordneten
  Teile eines Gegners. Unbekannte oder unvollständig erkannte Bilder bleiben
  vollständig original. Der Spieler und andere Objekte behalten ihre Grafik.
- Native OBJ-Reihenfolge, Hintergrundpriorität, Fenster, Helligkeit und
  Farbrechnung bleiben Teil der Komposition. Mehrere Gegner können gleichzeitig
  ersetzt werden. Es gibt kein pauschales Bild über der gesamten Szene.

Dies ist kein vollständiger Gegnerkatalog. Weitere Gegnerfamilien, Bosse,
aufgeteilte Körper mit unterschiedlichen Prioritäten, Spezialdarstellungen und
native Palettenblitze müssen jeweils untersucht und geprüft werden. Die
Skelettaufnahmen werden bewusst von Kerzen, Zugbrückenteilen, dem Turm und den
kleinen Umgebungsanimationen getrennt. Für neue Gegner müssen Nutzer keine
Tile-Adressen oder OAM-Slots zuordnen; die Erkennung wird im Programm ergänzt.

## Packformat und Zuordnung

`enemy_packs/selected.txt` enthält den ausgewählten lokalen Packnamen.
`enemy_packs/PACK/enemies.json` beschreibt Version 1 und `frames`. Eine Pose:

```json
{
  "id": "skelett-0011_pose-8af4_0123456789abcdef",
  "actor_type": 17,
  "pose": 35572,
  "image": "skelett-0011_pose-8af4_0123456789abcdef.png",
  "display_size": [96, 96],
  "anchor": [48, 48]
}
```

Die Beispiel-ID ist kein aufgenommener Schlüssel. Tatsächliche IDs erzeugt das
Spiel aus Actor-Typ, nativem Metaspritezeiger und einem Fingerabdruck der
unveränderten, von der Blickrichtung unabhängigen Farbindex-Pixel. Die
Bildauflösung steht nicht im Schlüssel. Der komplette transparente Referenzrand
gehört zur Positionszuordnung. Aktuell darf die native Darstellungsfläche bis
96 × 96 Pixel umfassen, das Pack insgesamt bis 64 Millionen Quellpixel.

`src/enemy_pack.cpp` rekonstruiert die native OAM-Erzeugung aus dem Actorbereich
`$0580..$0EBF` mit 64 Bytes pro Datensatz. Es prüft für jedes Teil Position,
Tile-/Attributwort und Größe gegen die tatsächlich übertragene OAM. Auch der
vorherige Actor-Schnappschuss darf nur bei vollständiger exakter Übereinstimmung
verwendet werden, da Spiellogik und OAM unterschiedliche Felder abbilden können.
ROM, RAM, VRAM, CGRAM und OAM werden dabei nur gelesen.

Die PPU erhält Hostbilder samt Masken ausschließlich für deren bestätigte
OAM-Slots. `hostSpriteWinners` benennt pro Pixel den wirklichen Gewinner. Der
HD-Renderer verwendet genau dieses Bild, einschließlich dessen Position,
Spiegelung und frei skalierter Quellpixel. Die Sammlung schreibt höchstens 512
Referenzen asynchron und verändert bereits vorhandene Referenz-PNGs nicht.

## Gezielte Prüfungen

`python tools/test_enemy_hd.py` kompiliert einen kleinen eigenständigen Test
mit künstlichen ROM-/PPU-Daten. Er prüft vollständige Teilezuordnung,
automatische Referenzaufnahme, 387 × 387-PNG auf 96 × 96-Darstellungsfläche,
Anker, Spiegelung, Rückfall bei einem unbekannten Teil und das Abschalten.
Alle Testdateien entstehen in einem neuen Ordner unter
`artwork-local/enemy-hd-2026-10-23`; Spielerprofile bleiben unberührt.

Ein isolierter echter Spielversuch hat die A02-Skelette zusätzlich visuell und
über Actor-Datensätze bestätigt. Die Testszene wird über die native Raumladung
geladen und Simon für reproduzierbares Streaming in die Nähe gesetzt. Das ist
kein vollständiger natürlicher Leveldurchlauf.

`tools/test_enemy_runtime.py --build-dir build-lua --fixture PFAD/ZUR/SKELETT.sav`
prüft die vollständige Strecke von der automatischen Aufnahme bis zur sichtbaren
387 × 387-Testgrafik im laufenden HD-Renderer. An drei identischen Spielfeldern
müssen sämtliche 128 KiB WRAM und die VRAM-/CGRAM-/OAM-Dumps mit und ohne neue
Grafiken identisch sein. Der geprüfte native Skelett-Arbeitsordner benötigt zwei
PNG-Dateien für vier zugeordnete native Posen. Testbilder und Protokoll liegen
lokal unter `artwork-local/enemy-hd-2026-10-23/review`.
