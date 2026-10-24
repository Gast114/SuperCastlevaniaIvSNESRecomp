# Monster-Werkstatt

`Gegner_Werkstatt_starten.cmd` startet die neue Monsteransicht in einem eigenen
Fenster. Die vorhandenen Arbeits-PNGs bleiben erhalten. Original und Redesign
verwenden denselben nativen Bewegungsablauf; Photoshop-Änderungen werden live
neu geladen.

## So benutzt du sie

1. Links einen **Monster-Code** wählen, zum Beispiel **M-0012**. Varianten
   gehören unter denselben Code. Im Feld **Dein Name** kannst du selbst einen
   Namen vergeben und speichern.
2. **Spawnen / neu starten** setzt das Monster in die neutrale Testszene.
   Das Herkunftslevel wird dabei nicht gestartet. Grafiken, Farben und Original-KI
   werden unabhängig davon bereitgestellt.
   **Ziel links/rechts** versetzt das Spielerziel, auf das die Original-KI
   reagiert. Die Vorschau zeigt einen flachen Boden mit echten Kollisionen.
3. Die Reiter **Gehen / Bewegen**, **Springen**, **Angriff** und **Sterben**
   enthalten die zugeordneten Posen. **Aktion abspielen** startet eine geprüfte
   Originalroutine. Der Knochenwurf gehört zum Angriff von M-0012: Körper und
   alle drei Knochen-Drehbilder stehen zusammen.
4. Eine PNG auswählen und **PNG öffnen** anklicken. In Photoshop im selben
   `artwork`-Ordner speichern. Rechts erscheint die Änderung automatisch.
   **PNG ersetzen** übernimmt eine fertige Datei und sichert die vorige Fassung.
5. **Einzelteile** zeigt die Teile einer Pose. **Grafikvarianten** zeigt weitere
   native Grafikfassungen; normalerweise reicht die übersichtliche Standardliste.
   **PNG einzeln ansehen** hält die Laufzeit für die Bildkontrolle an.
6. **Dieses Monster als PNG-Set** exportiert eine ZIP mit Code-Dateinamen,
   Originalen, bearbeitbaren PNGs und der Aktionszuordnung. Das entpackte Projekt
   kann direkt im [HD-Import](HD_IMPORT.md) gepackt werden. **HD-Paket erstellen**
   packt die veränderten Zeichnungen des aktuellen Arbeitsordners.

Arbeitsordner: `D:/Super Castlevania IV Recomp/Assets (ausgeschnitten)/Gegner/Werkstatt`.
Dateinamen bereits vorhandener Arbeitsdateien bleiben erhalten, damit offene
Photoshop-Dateien weiter passen. Neu angelegte Dateien und exportierte Sets
verwenden Codes. Die angezeigten Monster-Namen bestimmst du selbst.

Die PNGs haben eine vollständig transparente Leinwand, meist 387×387 Pixel.
Proportionen und Leinwand beibehalten, nicht auf das Motiv zuschneiden.
Eine neue ganze Pose hat Vorrang vor ihren Einzelteilen. Bei einem unvollständigen
PNG-Speichervorgang bleibt das letzte gültige Bild sichtbar.

## Werte und KI

Im rechten Reiter **Werte** stehen **Normal** und **New Game+** nebeneinander.
Die Tabelle vergleicht Gesundheit beim Spawn und Kontaktschaden. **Vorschau**
wechselt den echten nativen Durchgang und startet das Monster neu. Die Live-Werte
zeigen den gerade laufenden Durchgang und die verbleibende Gesundheit.
**KI / Hinweise** enthält die Verhaltenserklärung und offene Kontexte.

Beispiel M-0012 im frühen Raum: Normal **48**, New Game+ **64** Gesundheit;
Kontaktschaden jeweils **3**. Gesundheit zählt interne Schadenseinheiten,
Kontaktschaden Spieler-Lebenspunkte. Nicht alle Werte werden pauschal erhöht.

Originalberechnung: Grundwert aus `01:AC00 + Typ*2` plus Raumzuschlag aus
`01:A88F + Raum`; New Game+ addiert dazu **16**. Die Gesundheit wird bei
`32767` begrenzt. Spätere Räume haben schon im Normalspiel einen Zuschlag von
16, beispielsweise 64 → 80 statt 48 → 64. Der Wertevergleich verwendet weiterhin
den Originalzuschlag des Herkunftsraums; dieser wird dafür nicht geladen. Der
neutrale Testraum und das Werteprofil sind getrennt. Bei ungeprüfter
Bossgesundheit bleibt die Anzeige leer.

Beleg: `00:D3FA..D40E` berechnet aus Questflag `0088` die Schwierigkeit `0084`;
`00:D74E..D75C` addiert sie zur Spawn-Gesundheit. Der aktuelle Wert steht in
Actor `+06`. Kontaktschaden kommt aus der Byte-Tabelle `01:AF00 + Typ`, angewendet
von `00:DD0A..DD21`; diese Berechnung erhöht ihn nicht für New Game+.
Bosskontakt nutzt `00:DE14..DE33`; bei abweichendem sichtbarem Haupttyp wird ohne
geprüfte Zuordnung kein Schadenwert behauptet.

Die laufende Trefferbox kommt aus `+28/+2A`. Die gespeicherte Geschwindigkeit
kann am Boden weiter nach unten zeigen, obwohl die Kollision Bewegung verhindert.

### Grundlage für spätere eigene Spielmodi

`tools/monster_balance.py` trennt Originalprofile und eine zusätzliche
Überschreibungsebene. `resolve_mode` berechnet: Original → gewähltes Basisprofil
→ Werte für den jeweiligen Monster-Code. Die Originaldaten werden nicht verändert.
Das vorbereitete Format sieht beispielsweise so aus:

```json
{
  "version": 1,
  "name": "Mein späterer Modus",
  "base_profile": "new_game_plus",
  "overrides": {
    "M-0012": {"hp": 80, "contact_damage": 4}
  }
}
```

Ohne Eintrag übernimmt ein Monster die Werte des Basisprofils. Eine Überschreibung
ersetzt den fertigen Startwert; Raum- und Questzuschläge werden nicht erneut addiert.
Bisher vorbereitet
sind `hp` (0–32767, interne Einheiten) und `contact_damage` (0–255). Ungültige
Felder, Codes und Werte werden abgewiesen. Das ist zunächst eine geprüfte
Datengrundlage; Moduseditor, Laden einer solchen Datei und Anwendung im eigentlichen
Spiel folgen später. Die Vorschau verwendet jetzt nur die Originaldurchgänge.

Geprüfte Aktionsauslöser:

| Codes | Gehen | Springen | Angriff | Sterben |
| --- | --- | --- | --- | --- |
| M-0011 | ja | keine eigene Routine | Kontakt | ja |
| M-0012 | ja | ja, gleiche Geh-PNGs | Wurf mit echtem Knochen | ja |
| M-0031 | ja | ja, gleiche Geh-PNGs | native Angriffsfolge | ja |
| M-0056 | ja | ja, gleiche Geh-PNGs | native Angriffsfolge | ja |
| M-0069 | ja | keine eigene Routine | Kontakt | nativer Ablauf |
| übrige normale Codes | natürlicher KI-Ablauf | noch ungeprüft | noch ungeprüft | nativer Todesübergang |

Die KI-Hinweise beschreiben nur belegte Eigenschaften. Für andere Monster zeigt
**Natürlich** den echten Ablauf; ihre noch ungeprüften Posen liegen unter
**Noch zuordnen**. Deaktivierte Aktionsknöpfe bedeuten „ungeprüft“, nicht
„dieses Monster kann das nicht“. Eine native Aktion darf anschließend in die
normale KI zurückkehren. Geteilte Bilder dürfen zu mehreren Aktionen gehören.

## Umfang und verbleibende Kontexte

Der interne Vorrat enthält native Bild-/Teil-Zuordnungen aus gemessenen
Originalabläufen und belegten ROM-Posen. Der aktuelle Umfang steht in
`artwork-local/enemy-library/library.json` unter `summary`; er ist kein Nachweis
eines vollständigen Aktionskatalogs. Die Monsteransicht trennt Körper, Geschosse und
Umgebungsobjekte; die frühere gemischte Sprite-Auswahl ist nicht mehr der Start.

Im kurzen neutralen Start-/Bewegungstest wurden alle 47 normalen Monster-Codes
sichtbar, einschließlich M-007F. Das direkte Laden seiner Ressourcen umgeht den
bisher instabilen vertikalen Herkunftskontext. Die Angriffs-
und Sprungauslöser der weiteren Familien sowie ihre Geschosszuordnungen müssen
noch einzeln geprüft werden. Neue Todesposen werden bei **Sterben** gespeichert.

**Bosse** blendet zwölf vorbereitete Bossprofile ein. Sie laufen ebenfalls im
neutralen Testraum, ohne ihr Herkunftslevel zu laden. Ihre Originalcontroller
laden nur die benötigten Bossressourcen. Die Werkstatt hält die Kamera
und schützt das Spielerziel vor Tod und unbeabsichtigtem Raumwechsel. Beim Spawn
wartet sie auf vollständige Grafikübertragung und das erste sichtbare Teil.
Die Figur wird nicht vom Vorschaurahmen verfolgt; Körper und Geschosse bleiben
im selben Raumbezug. Manche Bossroutinen verwenden feste Weltkoordinaten oder
Bewegungsgrenzen; die Werkstatt berücksichtigt ihren ursprünglichen Ursprung.

M-0081 zeichnet seinen großen Körper als Mode7-Hintergrund. Dieser Körper ist
jetzt in beiden Ansichten in echter Bewegung sichtbar. Seine HD-Texturzuordnung
ist noch offen; die OBJ-Teile lassen sich schon als PNG bearbeiten. M-0082 und
M-008D haben weiterhin keinen vorbereiteten Startablauf. Ungeprüfte Bossposen
liegen unter **Noch zuordnen**, auch bei Hilfsteilen und Geschossen.

Beim nächsten Start aktualisiert der Launcher veraltete Bossaufnahmen automatisch.
Vorhandene Zeichnungen und Original-PNGs werden erhalten. Alte Bosszuordnungen
bleiben im internen Verlauf, werden aber nicht erneut als aktuelle Vorlagen
übernommen. Bossprofile versprechen keinen vollständigen Angriff-/Todeskatalog.

## Grundlage für Monster in anderen Levels

Grafikressourcen sind jetzt vom Herkunftslevel getrennt. `enemy_resources.py`
plant die benötigten Grafikplätze einer Monsterfamilie samt bekannten Kindern,
teilt gleiche Ressourcen und weist eine Überschreitung des nativen Speichers ab.
Der native Import übernimmt ausschließlich deklarierte Grafik- und Farbbereiche.
Damit muss ein späterer Level-Spawner keine fremde Levelszene laden.

Ein Platzierungseditor oder Änderungen an den bestehenden Spiellevels gehören
noch nicht dazu. Für gleichzeitig gemischte Familien müssen Grafikplätze und
Paletten gemeinsam verwaltet werden. Bei Bossen müssen außerdem feste
Bewegungsgrenzen, Spezialeffekte, die gemeinsame Bosssteuerung und der
Levelabschluss pro Verwendung geprüft werden. Normale Monster und Bosse in
anderen Levels sind das Ziel dieser Trennung, kein bereits vollständiger Editor.

## Getrennte Laufzeit und technische Prüfung

Die eigene Lua-EXE und ihre Spielstände liegen unter
`artwork-local/enemy-workshop/session-*`. Die ROM und die Spielstände des
normalen Spiels werden nicht geändert. Die Engine startet einmal mit einer
gemeinsamen Basisszene. Beim Spawn wird diese zurückgesetzt und zum neutralen
Raum eingerichtet: beide privaten 64×64-Kollisionskarten bekommen Luft, Boden
und Seitenwände. Die ursprüngliche Kollisionsroutine `00:CF86` bleibt aktiv.
Die Herkunftsszene eines Monsters wird nicht gestartet. Auch M-0031 und M-007F
brauchen dafür keine Sonderumwege über ihre Levels mehr.

Normale Grafiken werden direkt aus der ROM entpackt (`02:864A..87C5`): Zeiger
`01:A900`, Platzbedarf `01:AA80`, Slotzuordnung `01:A8D4`/`01:A8EA` und
`$13A0` nach `00:D7CC`. Gemeinsame Streams können länger sein als eine Variante
benötigt; geladen wird deren deklarierter Präfix. Der Grafikimport validiert alle
Spannen vor der ersten Änderung und beschränkt sie auf OBJ `$6A00..7FFF`.
Objektfarben werden zugleich im PPU und im nativen Palette-Puffer (`$48`,
normalerweise `$2200`) gesetzt. Hintergrundgrafik, OAM und CPU-Zustand werden
dabei nicht übernommen.

Originalfarben liegen separat unter `artwork-local/enemy-library/resources`.
`prepare_monster_resources.py --ensure` übernimmt vorhandene gemessene Paletten
ohne Emulator. Fehlt ein belegter Farbkontext, wird er einmalig bei der
Vorbereitung erfasst; beim Live-Spawn gibt es dafür keinen Rückfall auf einen
Herkunftslevelstart. Der alte Originalraum-Loader bleibt für solche
Offline-Aufnahmen und den alten internen Client erhalten. Bei eigener
Bibliothek: `--library <Ordner>`.

Auch Bosse starten in der gemeinsamen neutralen Szene. Controller `02:9346`
lädt ihre Grafik unabhängig vom Raum und wartet in `02:93B6`
auf `$1A12 == 0`. `$1A12` ist der Zustand des Grafikladers (DP `$1A00`), kein
Musikflag; vorzeitiges Löschen hatte VRAM-Übertragungen abgebrochen. Die Werkstatt
verkürzt nur den Actor-Countdown. Sprite-Beobachtungen erfolgen nach der nativen
NMI/OAM-Übertragung. Vollständig außerhalb des Bilds liegende Teile dürfen nur
in der Werkstatt aus dem exakten Originaldeskriptor ergänzt werden; fehlende
sichtbare Teile und mehrdeutige OAM-Zuordnungen werden weiter abgewiesen.

`python tools/test_monster_workshop.py` prüft die echten Tk-Bedienfunktionen,
Sprung, Wurf, Tod, Werte, Pause, Live-PNG-Wechsel und Export ohne Bildbetrachter.
`tools/test_enemy_library.py` prüft Quellen, Cache und Erhalt der Arbeits-PNGs.
`python tools/test_enemy_resources.py` vergleicht direkt entpackte ROM-Grafiken
mit zuvor unabhängig aufgenommenem nativem VRAM und prüft Grafikplatzplanung.
`python tools/test_neutral_monsters.py` verbietet Herkunftsraum-Ladevorgänge und
prüft die echten neutralen Spawns, Mode7, Palette-Puffer und atomaren Grafikimport.
`python tools/check_boss_workshop.py --fields 480` prüft die zwölf Bosse über
RAM, native OBJ-Zuordnungen und Mode7-Pixelprüfsummen, ohne Bilder anzusehen.
Gespeicherte Messungen können mit `--verify-existing <Ordner>` geprüft werden.
Andere Arbeitsordner: `python tools/monster_workshop.py --workspace "D:/Mein Ordner"`.
Optional sind `--rom`, `--build` und `--library` verfügbar. ROM und exportierte
Originalbilder bleiben lokal.
