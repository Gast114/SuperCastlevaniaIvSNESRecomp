# Technische Anschlussplanung für die Sprite-Produktion

Stand: 21.10.2026. Recherche und vorbereitete Metadaten; noch kein neuer Renderer oder getesteter 3D-/2D-Rig-Import.

Die Empfehlung und Herstellerquellen stehen in [SPRITE_ANIMATION.md](../SPRITE_ANIMATION.md). Diese Datei hält unsere projektspezifischen Vorgaben fest.

## Ausgabe aus dem Animationsprogramm

- Fertige RGBA-PNGs in gewünschter HD-Auflösung, mit erhaltenen weichen Alphakanten. Kein Video als Endformat für das Spiel.
- Feste Kamera, orthografisch für den 3D-Kandidaten, feste Beleuchtung, feste Körpergröße über einen Clip. Rechtsansicht genügt für die derzeitige automatische Spiegelung.
- Gemeinsames Koordinatensystem für alle Posen. Der Bezugspunkt der Figur muss unabhängig von der jeweiligen Bildbegrenzung erhalten bleiben.
- Arbeitsfläche kann beispielsweise960×960 für eine native96×96-Zelle bei10× sein. Für die Installation leere Ränder verlustfrei beschneiden und den Ausschnittsversatz separat erhalten. Nicht hunderte größtenteils leere960×960-Bilder samt vier Spiegelkopien im Runtime-Speicher halten.
- Eine Animation auf der Stelle verwenden. Horizontale Root-Motion und zusätzliche Sprungbahn aus einem 3D-Clip dürfen nicht nochmals zur Bewegung des Spiels addiert werden.
- Posen mit Bein-/Körperbewegung relativ zum Ursprung erhalten. Nicht jedes Bild unabhängig auf Fußunterkante oder Bildmitte normalisieren: Das würde Sprung- und Angriffsposen verschieben.
- Kamera-/Bildseitenverhältnis nicht aus den wechselnden Begrenzungsrechtecken neu bestimmen.

## Zuordnung an die originale Spiellogik

Der aktuelle Character-Renderer ersetzt ein vollständig erkanntes natives Körperbild durch ein PNG. Er spielt keine beliebige neue Animation mit eigener Uhr ab. Die vorhandenen sechs Laufphasen erhalten ihr Timing aus dem Spiel. Eine Bibliotheksbewegung muss an diesen Posen abgetastet und bei Bedarf angepasst werden; sechs gleichmäßig ausgewählte Bilder sind nicht automatisch passend.

Die normalisierten Körper-Fingerprints sind die Zuordnungsschlüssel. Zusätzliche Metasprite-IDs derselben Pixelgruppe werden seit `8c00d77` bei eindeutiger Zuordnung abgedeckt. Unterschiedliche Bilder nicht per Ähnlichkeit automatisch zusammenlegen. Palette, Kameraposition und Blickrichtung sind keine neuen Körperposen.

Bei Simon bleibt die native Peitsche separat. Handposition und Schlagrichtung der Ersatzbilder müssen deshalb zur Peitsche passen. Eine beliebige, gut aussehende Bibliotheks-Angriffsanimation genügt dafür nicht. Die ursprünglichen Bewegungs-, Kollisions- und Trefferzeiten sollen erhalten bleiben.

Das aktuelle vollständige Figurenpaket-System betrifft Simon. Die Bilderzeugung für Gegner kann dieselben Exportkonventionen verwenden; eine ebenso vollständige dynamische Gegner-Ersetzung samt Besitz-/Frame-Zuordnung ist dadurch noch nicht eingebaut.

## Vorhandenen Bedarf ohne neue Generierung erfassen

```powershell
python tools/character_pose_inventory.py --template build-play/game/characters/simon-template --character artwork-local/characters/simon-user-hd-three-poses-v1 --out artwork-local/animation-research-2026-10-21/simon-inventory
```

Zielordner muss neu sein. Das Werkzeug verändert keine Quelle und schreibt nur `inventory.json` und `poses.csv`. CSV enthält vollständige native Alias-IDs und die Zellen im vorhandenen `body.png`. Die Reihenfolge ist Erfassungsreihenfolge, nicht die Reihenfolge einer Bewegung.

Aufnahme vom21.10.:83 Einträge,77 Körper-Hashes,9 bereits HD,68 noch ohne HD. Kein vollständiger Pose-Katalog. Für weitere Figuren und für vollständige Clipzeiten werden eigene native Aufnahmen benötigt.

## Begrenzter Pilot statt Produktionsumstellung

Abnahme an einem Laufzyklus und wenigen Angriffsposen: Figur/Outfit bleiben erkennbar, keine zusätzlichen Gliedmaßen, kein Rutschen des Körperursprungs, klare Alphakanten, schlüssiger Loop, Hand zur nativen Peitsche passend. Danach eine zweite ähnlich gebaute Figur mit derselben Bewegung versuchen. Erst damit lässt sich die behauptete Wiederverwendung für unseren Stil bewerten.

Noch offen: konkretes Modell/Rig, Güte der automatischen Gewichtung, Materialstil, Verdeckung bei Angriffen, Renderzeiten auf Radeon890M und tatsächlicher Nacharbeitsbedarf. Bei dieser Recherche wurden keine Generierungscredits eingesetzt und keine Modelle/Programme installiert.
