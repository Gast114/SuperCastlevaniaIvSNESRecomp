# Technische Anschlussplanung für die Sprite-Produktion

Stand: 21.10.2026. Recherche, Pose-Inventar und vorbereitetes Blender-Exportstudio.

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

## Ausführbares Blender-Studio

Der Nutzer hat den Pilot inzwischen beauftragt. Blender4.5.14LTS ist als offizielle,
SHA-256-geprüfte und gültig signierte Portable-Version eingerichtet unter
`C:/Users/Gaming/AppData/Local/Programs/Blender-4.5.14/blender.exe`.
Installationsbeleg lokal: `artwork-local/blender-pilot-2026-10-21/blender-install.json`.
Die obige Aussage über keine Installation beschreibt nur die vorausgehende Recherche.

`tools/blender/sprite_pilot.py` importiert GLB/GLTF/FBX oder erstellt ohne Modell nur
ein Studio mit gepackter, nicht gerenderter Bildreferenz. Ausgabe immer in einen
neuen Ordner; vorhandene Blender-Projekte oder Spielpakete werden nicht verändert.
Orthografische Kamera, +X als Bildrichtung rechts, Z oben, Blick von-Y; Standard-Yaw90°
für Modelle mit Vorderseite-Y. Modellhöhe einmal aus der Ruhepose auf1,8Welteinheiten
normalisiert,49native Pixel/490Ausgabepixel. Boden77,35native Pixel, Zellursprung48/48.
Diese Werte entsprechen der bestehenden Simon-Probe als Ausgangspunkt; der tatsächliche
neue Körper und sein Handpunkt müssen noch mit Originalposen verglichen werden.

Beispiel mit einem tatsächlich animierten Modell (Pfade anpassen):

```powershell
& 'C:/Users/Gaming/AppData/Local/Programs/Blender-4.5.14/blender.exe' --background --disable-autoexec --python-exit-code 1 --python tools/blender/sprite_pilot.py -- --model artwork-local/blender-pilot-2026-10-21/models/Simon-Three-Motions-Rig.glb --surface artwork-local/blender-pilot-2026-10-21/models/Simon-Textured.glb --action Walking --out artwork-local/blender-pilot-2026-10-21/walk-next --samples 6 --render
python tools/blender/package_preview.py artwork-local/blender-pilot-2026-10-21/walk-next/scene.json --out artwork-local/blender-pilot-2026-10-21/walk-preview-next
```

Ohne`--render` wird nur importiert, die vorhandenen Actions/Knochen werden in
`scene.json` verzeichnet. Mit`--action`, `--start`, `--end` lässt sich die Auswahl
präzisieren. Standardmäßig wird eine gefundene Hips-/Pelvis-/Root-Bewegung horizontal
kompensiert; ohne passenden Knochen kein stillschweigender Root-Motion-Fix.
`--root-bone` erlaubt eine explizite Wahl. `--lock-root-z` nur bei absichtlich komplett
fixiertem Ursprung verwenden, sonst vertikale Körperbewegung erhalten.
Ein nicht animiertes Modell wird für mehrere Renderbilder ausdrücklich abgelehnt.

`package_preview.py` benötigt Pillow. Es beschneidet nur vollständig transparente
Ränder, rundet nach außen auf10px und erhält Größe und Zelloffset. Ein abgeschnittener
Körper am Canvasrand oder ein leeres Renderbild wird abgelehnt. `placement.json`
enthält passende HD-Bildmaße/Offsets, jedoch **noch keine nativen Körper-IDs**.
`Vorschau.html` zeigt die Bilder einzeln oder als Loop; deren frei einstellbare Zeit
gilt nur für die Vorschau. Kein automatischer Import ins aktive Spielpaket.

Eine neutrale A-Pose aus dem bestehenden Simon-Entwurf wurde einmal mit dem
eingebauten Imagegen erzeugt, um die kostenpflichtige Meshy-Posenfunktion nicht
zu benötigen. Quelle/Prompt unter`artwork-local/blender-pilot-2026-10-21/reference/`.
Dies ist die Modellreferenz, keine Einzelbild-Animationsproduktion.

## Ergebnis des ersten Piloten

Meshy6Lite: ein geometrisches Modell10Credits, eine Bildtextur10Credits. Beim
ersten erfolgreichen Erzeugen wurden automatisch30Check-in-Credits gutgeschrieben;
Stand nach dem Pilot110Credits. Der erste Rigging-Versuch war frei, ein zweiter
öffnete eine Abo-Sperre. Kein Abo/Kauf. Vier reguläre Downloads: Textur-GLB,
Running-GLB, Running+Walking-GLB und schließlich Running+Walking+Attack-GLB.
Meshy-Quellen und Referenzen bleiben lokal; Lizenz im Web warCCBY4.0.

`--surface` überträgt die vorhandenen Knochengewichte auf die lokal importierte
Farbgeometrie desselben Modells. Texturkoordinaten und Materialien bleiben am
Farbmesh. Vergleich nach einheitlicher Ruhehöhe/-mitte: maximaler nächster
Vertexabstand nur8,68e-7der Körperhöhe. Abweichung über0,005wird abgelehnt;
kein allgemeiner Auto-Rigger für andere Figuren. Der vom glTF-Importer erzeugte
Icosphere als Knochen-Widget wird ausdrücklich aus der Körpergeometrie ausgeschlossen.

Abgenommene Arbeitsausgabe: `walk-final/Simon_Pilot.blend` mit drei Actions
`Walking`, `Running`, `Attack`; die Knochenliste steht im Bericht `scene.json`.
Das Modell hat119.656Dreiecke und66.815texturierte Vertices; für offline gerenderte
Sprites, keine neue Echtzeit-3D-Laufzeit. Alle Bilder/Materialien sind gepackt.
SechsWalking-PNGs, dreiAttack-PNGs; Alpha vollständig erhalten. Ein typisches
Bild brauchte nach Initialisierung lautBlender-Log etwa0,5sauf diesem Rechner.

Vorschauen: `walk-preview/Vorschau.html` und `attack-preview/Vorschau.html`,
jeweils mit Einzelbildschritt und frei einstellbarer Vorschauzeit. Lossless
`Animation.webp` verwendet über alle Posen denselben gemeinsamen Ausschnitt.
Keine eigenständige Skalierung je Pose. Beim Rendern wird horizontale Hips-Bewegung
kompensiert; die unbearbeiteten Actions im Blender-Projekt enthalten weiterhin
ihre Originalbewegung. Das Exportwerkzeug muss für erneute Spielframes verwendet werden.

Sichtprüfung: konsistente Figur/Materialien, vollständige Ränder, rechter Seitenblick.
Look sichtbar plastischer und glatter als der gemalte Entwurf. Bibliotheksangriff
ist ein Überkopfangriff; noch kein passender Peitschenschlag. Auch die sechs
gleichmäßig gesampelten Gehbilder sind eine Produktionsprobe, keine freigegebene
Zuordnung zu den sechs nativen Simon-Posen. Kein aktives Figurenpaket, EXE,
Spielprofil oder Spielstand geändert. Keine Gameplay-/Performance-Testmatrix.
