# Die separate Gegner-Werkstatt

Im Projekt `Gegner_Werkstatt_starten.cmd` doppelklicken. Das Werkzeug verwendet
die bestehende lokale Python-Umgebung und baut bei Bedarf seine Lua-Laufzeit.
Die eigene ungeheaderte USA-ROM liegt wie bisher im Projekt.

## Gestalten und vergleichen

1. Figur auswählen und **Spawnen / neu starten** anklicken. Normale Figuren
   lassen sich mehrfach erzeugen, Bosse einzeln. Original und Redesign laufen
   nebeneinander mit denselben echten Bewegungsdaten.
2. Beim Skelett **Vollständige Skelett-Aktionen sammeln** anklicken. Gehen,
   Knochenwurf und Zerfallen werden durch Originalroutinen ausgeführt.
   Die vorbereitete Sammlung enthält diese Bilder bereits vollständig.
3. **Pause**, **Ein Feld weiter** oder 25/50/100% verwenden. Links/Rechts
   versetzt das native Spielerziel auf die entsprechende Seite; die Figur
   reagiert nach ihrer ursprünglichen KI.
4. Eine Pose auswählen und **PNG … öffnen** anklicken. Windows verwendet das
   zugeordnete Programm, beispielsweise Photoshop. Das PNG im Ordner
   `artwork` speichern; rechts erscheint die Änderung automatisch.
5. **Einzelteile anzeigen / austauschen** blendet Teilbilder ein. Alternativ
   über **PNG ersetzen** ein fertiges Bild auswählen. Dabei wird die vorige
   Arbeitsdatei in `history` gesichert.
6. **PNG-Sammlung als ZIP exportieren** gibt Vorlagen, Zuordnung und Galerie
   zusammen. **Paket zum Einbauen erstellen** packt fertige Bilder.
   Installation über den HD-Import: [ENEMY_HD.md](ENEMY_HD.md).

Standardarbeitsordner: `D:/Super Castlevania IV Recomp/Assets (ausgeschnitten)/
Gegner/Werkstatt`. Neue Aufnahmen überschreiben keine vorhandenen Zeichnungen.
Identische Bilder teilen sich eine Datei. **Nur aktuelle Figur und zugeordnete
Geschosse** hält die Liste übersichtlich.

Bei einer vorübergehend unvollständigen PNG bleibt das letzte gültige Bild
sichtbar. Leinwand und Proportionen beibehalten; nicht auf das Motiv zuschneiden.
Eine neue ganze Pose hat Vorrang vor ihren neuen Einzelteilen.

## Umfang und offene Kontexte

Skelett: fünf Körperposen, drei Knochenbilder, zehn Zerfallseffekte und 37
optionale Einzelteile. Der Originalmotor führt die Abläufe tatsächlich aus.

Der weitere Katalog kommt aus originalen Platzierungs-/Grafikressourcentabellen.
94 normale Figuren- und Objektprofile wurden zweimal kurz geprüft; 83 waren
sichtbar. 39 davon sind als Gegner beschrieben, 17 als Objekte, 8 als Gefahren,
5 als Effekte; 14 sichtbare Figuren bleiben unbestimmt. Beschriftungen sind
visuelle Beschreibungen. Ungeprüfte Initialisierungen tragen **Kontext offen**.

Neue sichtbare Posen werden während des Ablaufs gesammelt. Für weitere
Familien sind gezielte Aktions- und Projektilprofile noch auszubauen; ein kurzer
sichtbarer Ablauf ist kein vollständiger Nachweis aller Aktionen.

Bossprofile führen den originalen Szenencontroller `$2A` aus, der Grafiken lädt
und den Boss erzeugt. Die Musikwartezeit wird in der privaten Szene übersprungen.
Diese Profile bleiben **experimentell**, weil manche zusätzliche Raumskripte
brauchen. `$81` verwendet unter anderem BG/Mode7 statt einer gewöhnlichen
OBJ-Figur. `$8B` erzeugt seinen sichtbaren Körper als Actor `$09`, der separat
zugeordnet ist. `$82` und `$8D` haben noch keinen vorbereiteten Ablauf.
Boss `$80` nutzt den belegten experimentellen Raum 4; sein Originalraum 7
braucht noch zusätzliche Szeneninitialisierung. Kein Bossprofil verspricht
vollständige Angriffs- und Todesanimationen.

Der Vergleich verwendet eine neutrale Bühne. Kollisionen und Raumskripte laufen
in der privaten Originalszene weiter. Spezielle Palettenwechsel, Blitzfarben
und BG/Mode7-Darstellungen sind noch nicht farbgetreu in der neutralen OBJ-
Vorschau abgebildet. Die native Zaunverdeckung im Spiel ist separat geprüft.

## Getrennte Laufzeit

Die App startet eine eigene Lua-fähige EXE unter
`artwork-local/enemy-workshop/session-*`. ROM-Boot, Raumladung, Actor-Startwerte,
Pause und Einzelbilder werden über eine lokale Lua-Schnittstelle gesteuert.
Spielstände und Einstellungen des Spielers werden nicht geöffnet. Beim
Schließen werden PNG-Aufnahmen gespeichert und der eigene Prozess beendet.

Andere Arbeitsordner: `python tools/enemy_workshop.py --workspace "D:/Mein Ordner"`.
Optional `--rom` und `--build` für eine eigene USA-ROM beziehungsweise einen
Lua-fähigen Build verwenden. ROM und daraus exportierte Bilder bleiben lokal.
