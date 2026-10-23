# PNG-Import ohne feste Arbeitsauflösung

`HD_Import_starten.cmd` öffnet das lokale Importfenster für Simon und Gegner.
Der vorbereitete Werkstatt-Arbeitsordner ist direkt über einen Button erreichbar.
Mit `Gegner_Werkstatt_starten.cmd` lassen sich Gegner separat bewegen und
Original/Redesign live vergleichen; siehe [ENEMY_WORKSHOP.md](ENEMY_WORKSHOP.md).
Die Spielausgabe bleibt 10×;
deine Photoshop-Dateien können beispielsweise mit 4,03125× arbeiten.
PNG-Dateien werden bytegleich kopiert. Ihr Inhalt, ihre Maße und ihre
Transparenz werden beim Import nicht verändert.

## Einfacher Ablauf

1. **Vorlagenordner anlegen** anklicken. Das Werkzeug exportiert die bereits
   im Spiel aufgenommenen Posen nach `Original`. Die Zuordnung ist gespeichert;
   du musst keine Tiles oder Körperteile zuordnen. `VORLAGEN.html` zeigt alle
   Posen als Bilderübersicht mit direktem Link zur passenden PNG-Datei.
2. Ein Original in Photoshop proportional vergrößern und das Redesign darüber
   erstellen. Die Leinwand und transparente Ränder proportional beibehalten.
   Ganze Pixel werden beim Export berücksichtigt; beispielsweise sind
   32×64 native Pixel bei 4,03125× genau 129×258 PNG-Pixel.
3. Das fertige PNG mit **demselben Namen** in `HD` speichern. Nur fertige Posen
   liefern. `Original` und `workspace.json` unverändert aufbewahren.
4. **Fertige PNGs prüfen / Paket erstellen** anklicken. Ein neues Paket unter
   `artwork-local/characters/simon-import-<Zeitpunkt>` und ein HTML-Prüfbericht
   entstehen. Darin stehen Quelldatei, Arbeitsmaße, native Darstellungsgröße
   und Position. Gleiche Pose und Verankerung gelten auch für die Gegenrichtung.
5. Nach Sichtprüfung **Paket in beide Spielversionen einbauen** anklicken.
   Das gerade erstellte Paket wird in die beiden Spielordner kopiert und dort
   ausgewählt. Die vorherige Charakterauswahl wird unter
   `artwork-local/install-backups/character-<Zeitpunkt>` gesichert. Anschließend
   das Spiel vollständig neu starten. Der Button ist vor dem Paketbau gesperrt.

Vorlagenexport und Prüfung verändern keine Spielprofile. Erst der ausdrücklich
angeklickte Installationsbutton wählt das neue Paket aus. Er prüft beide Ziele
vorher und bricht bei bestehenden gleichnamigen Paketen ab. Eine fehlgeschlagene
Installation setzt die bisherige Auswahl zurück. Andere Charakterpakete,
Spieleinstellungen und Spielstände bleiben erhalten. Alternativ lässt sich das
neue Paketverzeichnis nach `characters` neben der gewünschten Spiel-EXE kopieren
und unter **Character workshop** auswählen. Den Ordnernamen unverändert lassen.
Fehlende Posen verwenden weiterhin Originalgrafik. Der Import kann keine neuen
Animationsposen aus einem einzelnen Bild erfinden.

## Gegner im gleichen Fenster

**Vorbereitete Skelett-Bilder öffnen** zeigt bevorzugt den Arbeitsordner
`Assets (ausgeschnitten)/Gegner/Werkstatt` neben dem Projekt. Darin sind
die fünf Körperposen, drei Knochenbilder, zehn Zerfallseffekte und optionale
Einzelteile vorbereitet. Die separate Sammlung `02_Skelette_Alle_Aktionen`
und `Skelette_Alle_Aktionen_2026-10-24.zip` liegen daneben. Die passenden
PNGs aus `artwork` sind schon 387×387 Pixel groß und können direkt in Photoshop
bearbeitet werden;
`references` bleibt als Original erhalten. Die ganze transparente Bildfläche
proportional beibehalten, beispielsweise 387×387 Pixel statt nativen 96×96.
Ein Bild kann automatisch mehreren Spielzuständen zugeordnet sein.

Danach **Fertige PNGs prüfen / Paket erstellen** anklicken. Das Fenster erkennt
den Gegnertyp am Arbeitsordner und verwendet den passenden Import. Nur geänderte
Bilder werden gepackt; bei unveränderten Originalen meldet es, dass zuerst ein
Bild überarbeitet werden muss. Der Prüfbericht zeigt die fertigen Bilder mit
lesbaren Namen. Nach Sichtprüfung installiert derselbe Installationsbutton das
Paket nach `enemy_packs` in beiden Spielversionen und sichert die bisherige
Gegnerauswahl unter `artwork-local/install-backups/enemy-<Zeitpunkt>`. Simons
ausgewähltes Paket wird dabei nicht gewechselt.

Für neue Gegner-Vorlagen beim Feld **Aufgenommene Spielvorlage** den im Spiel
erzeugten `enemy_packs/native-template`-Ordner auswählen. **Vorlagenordner anlegen**
erstellt dann automatisch einen Gegner-Arbeitsordner. Für Simon bleibt der
Voreintrag `characters/simon-template` passend. Technische Details und der
aktuelle Umfang der Gegnerunterstützung stehen in [ENEMY_HD.md](ENEMY_HD.md).

## Bereits vorhandene PNG-Paare

Zwei Ordner mit gleichen Dateinamen funktionieren ebenfalls. Keine Endung
`_HD_10x` und keine 10×-PNG-Maße sind erforderlich:

```powershell
python tools/import_character_hd.py --template build-play/game/characters/simon-template --native "D:/Meine Bilder/Original" --source "D:/Meine Bilder/HD" --out artwork-local/characters/mein-neues-paket
```

Der Import erkennt die native Pose anhand ihrer vollständigen Silhouette und
übernimmt die Verankerung aus der Spielaufnahme. Bei mehrdeutigen Posen hält
er mit einer Fehlermeldung an. Der vorbereitete Vorlagenordner löst diese Fälle,
weil er die exakte aufgenommene Pose zusätzlich kennt. Unterschiedlich
beschnittene Leinwände werden nicht automatisch geraten oder gestreckt.

Die alte Schreibweise `Standing.png` und
`Standing_HD_10x_320x640.png` im gleichen Ordner funktioniert weiterhin mit
`--source`. Der vorhandene Aufruf wird nicht geändert.

Vorlagen und Paket lassen sich auch direkt erstellen:

```powershell
python tools/import_character_hd.py --template build-play/game/characters/simon-template --create-workspace --out artwork-local/meine-simon-vorlagen
python tools/import_character_hd.py --template build-play/game/characters/simon-template --workspace artwork-local/meine-simon-vorlagen --out artwork-local/characters/mein-neues-paket
```

## Technische Grenzen

Die native Referenz muss in die aufgenommene 96×96-Zelle passen. Der Loader
akzeptiert beliebige PNG-Maße bei explizitem `hd.display_size` in nativen Pixeln.
`hd.scale:10` beschreibt weiterhin das interne Raster des Character-Compositors,
nicht die Arbeitsauflösung. Ohne `display_size` gelten für alte Pakete weiterhin
die bisherigen exakten 10×-Maße. Die Anzeige tastet das unveränderte PNG beim
Laden auf das Ausgaberaster ab. Die Samplingmethode bestehender Pakete bleibt
erhalten. Extrem große PNGs über 8192 Pixel je Achse oder 32 Megapixel werden
abgewiesen.

Landschaften mit mehreren Ebenen benötigen zusätzlich deren gemeinsame
Photoshop-Positionen und Scrollzuordnung. Dieses Werkzeug ist ein Posenimport;
es errät keine Landschaftsebenen aus einzelnen zugeschnittenen Dateien.
Gegner verwenden den eigenen Workflow aus [ENEMY_HD.md](ENEMY_HD.md).
