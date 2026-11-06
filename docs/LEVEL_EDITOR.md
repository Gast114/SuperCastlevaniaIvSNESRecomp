# Castlevania Studio – Level- und Monster-Editor

Erste benutzbare Fassung vom 24.10.2026. Der Editor ist eine separate Anwendung
mit Karte und Werkzeugen, angelehnt an den Arbeitsablauf von Lunar Magic.
Beim Ausbau sind bestehende Levels umbauen und neue Levels erstellen gleich wichtig.

## Start und erster Versuch

`Level_Editor_starten.cmd` doppelklicken. Beim ersten Start werden Originaldaten
aus deiner eigenen USA-ROM vorbereitet. Danach werden sie wiederverwendet.
Die vorhandene Python-Umgebung der HD-Werkzeuge wird verwendet.

Level-Editor und Monster-Werkstatt befinden sich jetzt in **einem Fenster**:
**Level & Räume** enthält Karte, Bibliothek und Platzierungen;
**Monster & Animationen** enthält den neutralen Testraum, Original/HD-Vergleich,
Posen, Einzelteile, PNG-Austausch und Export. `Gegner_Werkstatt_starten.cmd`
öffnet dasselbe Studio direkt im Monsterbereich. Die vorhandenen Werkstattdateien
und Redesigns werden weiterverwendet; ein eigenes Levelprojekt bleibt beim
Wechsel geöffnet.

Eine Figur auf der Karte auswählen und rechts unter **Auswahl → Animationen & HD…** drücken:
Die Werkstatt öffnet genau diesen Monster-Code und seine Variante. Über
**Werte der Level-Figur…** lassen sich Gesundheit, Schaden, Trefferfläche und
Bossverhalten dieser Platzierung ändern. Bei Originalen wird dazu eine eigene
Levelkopie angelegt. Die Werteübersicht des neutralen Testraums zeigt weiterhin
die Originalwerte für Normal und New Game+; die Überschreibungen gehören zur
verknüpften Level-Figur. Bei einem anderen Monster-Code ist die Verknüpfung
deaktiviert.

Über **Animationen & HD bearbeiten…** in der Gegnerbibliothek lässt sich deren
ausgewähltes Monster öffnen. **Im Level hinzufügen** setzt den gewählten Code
einschließlich Variante in den sichtbaren Kartenbereich und wechselt zurück
zur Karte. Die Figur ist anschließend ausgewählt und mit der Maus verschiebbar.
Gespeicherte Monsternamen erscheinen auch in Bibliothek und Karte.

Im Monsterbereich speichert **Monster speichern / Strg+S** die Werkstatt;
**F5 / Monster testen** startet das gewählte Monster neu. **Vorschau pausieren**
pausiert die Animation. Der neutrale Test pausiert auch beim Zurückwechseln zur
Karte; ein vorheriger privater Leveltest wird beim Öffnen der Werkstatt beendet.
Beim Schließen werden die Werkstatt gespeichert und die eigenen Testprozesse
beendet. Ein bereits laufendes normales Spielfenster bleibt erhalten.

Der Editor startet im Reiter **Originale** mit allen **68 Originalabschnitten**
R-00 bis R-67. Die bekannten ersten Abschnitte sind zusätzlich als Stage 01 / A01
bis A05 bezeichnet. Beim Auswählen wird eine Vorschau vorbereitet; die Originale
werden dabei nicht bearbeitet. **Dieses Level bearbeiten** oder **Bearbeiten**
öffnet eine eigene Kopie. Auch direktes Ziehen oder Hinzufügen einer Figur erstellt
diese Kopie automatisch. Ein vorhandenes eigenes Projekt mit Änderungen bleibt
erhalten; die Kopie wird als weiterer Raum ergänzt. **Eigenes Level beginnen**
startet leer. **Mein Projekt** wechselt zurück zur eigenen Karte.

Eine bereits vorhandene **Erste_Testwelt** bleibt erhalten und lässt sich über
**Öffnen** laden. Sie wird nicht mehr automatisch gestartet. Projekte liegen
standardmäßig unter `artwork-local/level-editor/projects/` und enden auf
`.sc4level.json`. **Speichern unter** legt eine zusätzliche eigene Fassung an.

**F5 / Spieltest** startet eine eigene Spielinstanz: im Originalkatalog den
ausgewählten Originalabschnitt mit seinen nativen Skripten, unter Mein Projekt
den gerade geöffneten eigenen Raum, auch ohne vorher zu speichern. Der im Projekt
gespeicherte Startraum wird dadurch nicht verändert. Das Originalspiel
lässt sich so auch bei vertikalen und Mode7-Einträgen testen, deren vollständige
2D-Kartenansicht und Kartenimport noch fehlen. **Test beenden** schließt die
Instanz. Nach einer Änderung
F5 erneut drücken. Das Spielfenster muss den Eingabefokus haben, um zu spielen.
Während der Vorbereitung zeigt der Editor ein Ladefenster mit Fortschrittsanzeige
und **Abbrechen**. Das Spielfenster erscheint mit dem fertig geladenen Abschnitt.
Ein geprüfter Ausgangsspeicherstand aus den vorbereiteten Editor-Daten verkürzt
den Start; ist er nicht verwendbar, wird das Spiel vollständig neu gestartet.
Ein abgebrochener Start öffnet später kein zusätzliches Spielfenster. Fehler werden
angezeigt und unter dem genannten Testordner als `startup-error.log` gespeichert.
Horizontale Räume bis 256 Pixel Höhe behalten die ursprüngliche Kamerahöhe,
damit unten kein ungenutzter Kartenrand eingeblendet wird. Höhere eigene Räume
scrollen weiterhin vertikal.
Die Originalsteuerung des privaten Spieltests gilt. Native Speicherstände und
Rewind gehören noch nicht zum Projektformat; nach Tod oder versehentlichem
Verlassen des Tests mit F5 neu starten.
Der Spieltest verwendet Ton, wenn ein Audiogerät verfügbar ist, und startet
sonst automatisch ohne Ton. Run-ahead und Rewind sind nur für diese private
Testinstanz deaktiviert, weil sie den Projektzustand noch nicht mitspeichern.

## Karte bearbeiten

### Steine, Plattformen und Treppen auswählen

Unter **Gelände → Bauteile** findest du große Vorschauen, getrennt nach **Steine**,
**Plattformen**, **Treppen** und **Eigene**. Eine Vorlage anklicken, dann in die
Karte klicken: Das gesamte Bauteil wird im 8-Pixel-Raster gesetzt. Der Rahmen
unter der Maus zeigt seine Größe und Position. Bei Plattformen lässt sich die
Länge über **Plattformlänge · Steine** auf 1 bis 32 Steine einstellen.
Die A02-Vorlage verwendet die Plattformgrafik aus dem F10-Beispiel.

**Umschalt + Rechtsklick** auf eine vorhandene feste Plattform nimmt ihre
zusammenhängende Fläche auf. Nur die aktuelle Zielebene wird berücksichtigt;
andere Kollisionsklassen und Lücken bleiben ausgespart. Mit Linksklick eine
Kopie setzen. Für größere oder frei geformte Ausschnitte weiterhin mit
**Auswahl** ein Rechteck aufziehen.

Einen Namen eintragen und **Auswahl merken** oder **Pinsel merken** drücken,
um das Teil unter **Eigene** abzulegen. Diese Bauteile werden mit dem Projekt
gespeichert und stehen in allen seinen Räumen zur Verfügung. Sie behalten
Grafikquelle, Farben, Masken und Kollision auch auf einer anderen Zielebene.
Mit **Eigenes Bauteil entfernen** wird nur die Vorlage entfernt; bereits
gesetzte Kopien bleiben stehen. Das Entfernen ist rückgängig zu machen.

**Kollision beim Zeichnen übernehmen** muss eingeschaltet sein, wenn auch die
begehbare Fläche gesetzt werden soll. **H/V** spiegelt das ganze Bauteil samt
Maske. Treppenmasken lassen die Wand zwischen den Stufen erhalten.
Die bisherigen Quellen aller Abschnitte, 32px-Blöcke und 8px-Kacheln bleiben
frei zugänglich; eigene Teile können daraus beliebig zusammengesetzt werden.
Die festen Bauteile verändern die Karte. Bewegliche Plattformen werden separat
als native Spielobjekte gesetzt, siehe unten.

### Bewegliche Plattformen und Objektbilder

Unter **Bauteile → Bewegliche Plattformen** oder im Reiter **Objekte** stehen
zwei geprüfte Varianten von **O-0017** bereit: waagerecht und senkrecht. Eine
Variante anklicken und ihren Mittelpunkt in der Karte setzen. Der eingezeichnete
Weg zeigt die native Pendelbewegung über 80 Pixel nach links bzw. nach oben.
Die Plattform kehrt am Ende um. Ihr Weg muss vollständig im Raum liegen.

Nach dem Setzen oder Auswählen lassen sich **Bewegung**, X/Y und Spielebene
unter **Auswahl / Ausgang** ändern und mit **Übernehmen** bestätigen. F5 führt
die Originalroutine aus: Die Plattform bewegt sich pixelgenau, trägt Simon und
erlaubt Abspringen. Die Bewegung ist nicht bloß eine Animation über festen Kacheln.
Andere Objekte sind mit O-Codes und ihrer vorhandenen Originalgrafik auswählbar;
ihre Funktion kann zusätzliche native Levelskripte benötigen.

Monster und Objekte haben jetzt Sprite-Bilder in der Auswahl **und in der Karte**.
Die Bilder verwenden ihre native Größe und ihren Originalanker. Figuren der
hinteren Spielebene werden vor dem Vordergrund gezeichnet, etwa hinter dem Zaun.
**Objektnamen** ist zunächst eingeschaltet und zeigt Codes sowie selbst vergebene
Namen. Ausgewählte Objekte zeigen ihre Beschriftung immer. Vorhandene Originalposen werden nur gelesen. Für unsichtbare
Controller oder fehlende Vorschaubilder wird keine Ersatzgrafik erfunden.

### Grafiken frei aus allen Abschnitten mischen

Unter **Gelände → Grafikquelle** die gewünschte **Quelle**
wählen: R-00 bis R-67, dazu der später geladene Mode7-Grafiksatz aus R-23.
Daneben die Vorder- oder Hintergrundgrafiken dieser Quelle auswählen.
Dann einen Block oder eine Kachel anklicken und in die Karte zeichnen.
Oben legt **Zielebene** fest, wo du zeichnest. Die Quell- und Zielebene
dürfen verschieden sein: etwa ein Hintergrunddetail aus R-15 im Vordergrund
eines Raums mit Grafiken aus R-01.

Ein Raum ist nicht mehr an den Grafiksatz seines Herkunftslevels gebunden.
Du kannst einzelne Kacheln, ganze Blöcke und kleine Ausschnitte aus beliebig
vielen Quellen kombinieren. Jedes Teil behält seine Grafik, Originalfarben,
Transparenz und Priorität. Die native Begrenzung auf acht Hintergrundpaletten
oder einen gemeinsamen Kachelbestand beschränkt diese gemischten Karten nicht.
Die Kollision wird unabhängig gespeichert; beim Zeichnen lässt sie sich aus
der Quelle übernehmen oder anschließend selbst ändern.

Bereiche mit **Gelände → Gelände markieren / kopieren → Strg+C/V** auch zwischen Räumen oder Ebenen kopieren.
Ihre Herkunft bleibt dabei erhalten, ebenso beim Spiegeln, Speichern und Laden.
Auch ältere Projektdateien bleiben lesbar. **Alle Grafikquellen vorbereiten**
legt den vollständigen lokalen Vorrat einmalig an; spätere Zugriffe nutzen ihn.

Grafiken aus vertikalen und Mode7-Abschnitten sind als Bausteine verfügbar,
auch wenn der komplette Kartenimport dieses Abschnitts noch fehlt. Mode7
wird hier als statisches Bildmaterial übernommen; Rotationen und andere
geskriptete Abläufe werden damit nicht automatisch zu platzierbaren Objekten.

### Werkzeuge

- Links Raum auswählen, neu anlegen oder duplizieren. **Als Startraum** legt
  fest, welcher Raum beim nächsten Spieltest beginnt.
- Rechts einen **32px-Block** oder eine **8px-Kachel** wählen. Kacheln können
  mit einer der acht Originalpaletten dargestellt werden.
- **Zeichnen** setzt den Pinsel; **Fläche** füllt ein aufgezogenes Rechteck.
  **H/V** spiegelt den Pinsel, wenn die Karte den Tastaturfokus hat.
- **Gelände markieren / kopieren** zieht einen Bereich auf. **Strg+C**, **Strg+V** und anschließend
  Linksklick kopieren ihn. **Entf** löscht die Auswahl oder das gewählte Objekt.
- Rechtsklick auf eine Figur öffnet Löschen, Duplizieren und Werte. Auf freiem
  Gelände nimmt er eine Kachel auf. Mittlere Maustaste verschiebt die Ansicht.
  Mausrad scrollt, Umschalt+Mausrad horizontal, Strg+Mausrad zoomt.
- **Strg+Z / Strg+Y** macht Bearbeitungen rückgängig bzw. stellt sie wieder her.
  **Strg+S** speichert das Projekt.

Vordergrund (`front`) und Hintergrund (`back`) lassen sich getrennt bearbeiten
und einblenden. **Kollision anzeigen** markiert die Kollision der ausgewählten
Ebene. **Kollision** zeichnet mit **Fest/Frei** unabhängig von der Grafik.
**Kollision beim Zeichnen übernehmen** nutzt die native Bedeutung der Kachel;
Steigungen und andere native Klassen bleiben dabei erhalten.

Unter Raumeigenschaften lassen sich Name, Breite und Höhe ändern. Maße müssen
durch acht teilbar sein. Verkleinerungen, die Gegner oder Ausgangsziele
abschneiden würden, werden abgewiesen. **Eigenschaften…** öffnet den Dialog; **Übernehmen** bestätigt die Werte.

Der Kollisionsmodus **3 · Zwei Spielebenen** hält die Böden vor und hinter dem
Zaun unabhängig. **0/2** verwenden den Vordergrund; **1** kombiniert beide
Kollisionsebenen nach Originalregel. Importierte Räume behalten ihren Modus.

## Monster, Start und Ausgänge

Rechts **Gegner** öffnen, ein Bild auswählen und **＋ Hinzufügen** drücken. Die
Figur erscheint in der sichtbaren Kartenmitte und ist direkt zum Ziehen ausgewählt.
Alternativ ein Bild aus der Bibliothek in die Karte ziehen. **Mit Maus platzieren**
zeigt eine Vorschau am Mauszeiger; mit einem Klick setzen. Danach ist wieder
**Objekte bewegen** aktiv. Umschalt beim Setzen erlaubt mehrere Platzierungen,
Esc beendet den Platzierungsmodus. Unter **Objekte** funktioniert es genauso,
beispielsweise für Kerzen oder bewegliche Plattformen.

Koordinaten, Variante und Spielebene stehen rechts im Reiter **Auswahl**.
Es werden nur die jeweils passenden Eigenschaften angezeigt; Ausgangsfelder
erscheinen erst bei einem Ausgang. Gesundheit, Kontaktschaden und Trefferfläche
lassen sich dort direkt ändern; **Werte speichern** übernimmt die Änderung.
**Werte vergleichen…** öffnet die ausführliche Vergleichstabelle.
Monster werden in der Karte mit einer vorhandenen nativen Pose gezeigt; ihre
echte KI und Animation laufen im Spieltest. Die Codes entsprechen der Monsterwerkstatt.
Geschosse und belegte Hilfsteile bleiben bei ihrem Monster.

Figuren direkt mit der linken Maustaste anklicken und ziehen. Das funktioniert
auch bei aktivem Geländepinsel. **Alt** erlaubt Zeichnen unter einer Figur;
das ausdrückliche Werkzeug **Gelände markieren / kopieren** wählt Gelände.
Ein Doppelklick auf eine Figur öffnet keinen Dialog. **Entf** löscht sie sofort,
**Strg+Z** stellt sie wieder her. Der Greifpunkt bleibt erhalten;
kleine und nicht am Raster ausgerichtete Figuren lassen sich pixelgenau greifen. Die Pfeiltasten verschieben ein ausgewähltes
Objekt um einen Pixel, Umschalt + Pfeiltaste um acht. Strg+C / Strg+V kopiert die
Figur einschließlich Name und eigener Werte; anschließend in die Karte klicken.
Auch **Duplizieren** unter Auswahl kopiert eine ausgewählte Figur samt eigenen Werten.

Ein Raum kann bis zu **4096 Figuren** enthalten. Ihre Grafiken und Paletten
liegen beim eigenen Spieltest getrennt von der Levelgrafik; verschiedene
Gegnerfamilien teilen sich nicht mehr elf Grafikseiten für das gesamte Projekt.
Die Original-KI hat weiterhin **37 aktive Objektplätze**, einschließlich
Geschossen, Hilfsteilen und dynamischen Objekten. Entfernte Platzierungen
belegen diese Plätze nicht dauerhaft: Lebende Gegner werden vor dem nativen
Entfernen ausgelagert und beim Zurückgehen mit ihrem Zustand fortgesetzt.
Sind alle Plätze belegt, warten weitere Platzierungen auf einen freien Platz.
Damit sind viele Figuren im Raum möglich, aber keine unbegrenzt große
gleichzeitig aktive Gruppe. Native OAM-Sichtbarkeits- und Blinkregeln bleiben erhalten.

**Werte vergleichen…** öffnet den Detaildialog. Normal und New Game+
stehen separat neben dem wirksamen Normalwert. Eigene Gesundheit, Kontaktschaden
und halbe Trefferbreite/-höhe gelten pro platziertem Exemplar im F5-Spieltest und
werden im Projekt gespeichert. Ein leeres Feld übernimmt den Originalwert;
**Originalwerte wiederherstellen** leert die Überschreibungen. Bei Bossen stammt
die normale Gesundheit aus der vorbereiteten nativen Initialisierung. Noch nicht
gemessene New-Game+-Bosswerte werden ausdrücklich als Initialisierung angezeigt.
Die Bibliothek zeigt Gesundheit und Schaden für Normal und New Game+ bereits
beim Auswählen. Der Reiter Auswahl zeigt die wirksamen Werte dieses Exemplars;
eigene HP werden nach der nativen Initialisierung gesetzt und nach Treffern
nicht wieder aufgefüllt. Allgemeine KI-Hinweistexte wurden entfernt. Ein
Entscheidungsgraph oder eine editierbare Verhaltenslogik ist noch nicht vorhanden.

Kerzen erscheinen unter **Objekte / O-000E** und werden beim Originalimport
übernommen. Ihre Variante ist das ursprüngliche Inhaltsbyte (dezimal). Die native
Flamme und das Zerstören/Erzeugen des Inhalts übernimmt die Spielengine.
Szenencontroller sind ebenfalls auswählbar. Im freien Spieltest erscheinen ihre
bereits aufgenommenen Bilder als **Kulisse**. Ihre Levelskripte werden dabei
nicht als gewöhnliche Gegner gestartet: Solche Skripte könnten fremde Kamera-,
Grafik- oder Levelwechsel auslösen. Der Startstatus
weisen darauf hin. Ohne vorhandene Grafik bleibt die betreffende Kulisse im
Spieltest unsichtbar; die Bibliothek kennzeichnet fehlende Aufnahmen. Für
interaktive Szenenabläufe fehlen noch eigene geprüfte Adapter.

### Freie Bosse und klassische Begegnungen

M-0080 bis M-008D lassen sich platzieren und verschieben. Neue Platzierungen
verwenden zunächst **Freier Gegner im Level**. Unter **Auswahl → Boss verwenden
als** lässt sich der Modus ändern und mit **Bossmodus speichern** übernehmen.
Bereits gespeicherte Projekte ohne Modusangabe behalten die klassische Begegnung.

Im freien Modus hat jedes Exemplar einen eigenen nativen Zustand mit eigenen
Hilfsteilen, Grafikdaten und HP. Mehrere gleiche oder verschiedene Bosse können
zusammen mit normalen Gegnern aktiv sein. Es gibt keine Begegnungskamera,
Einleitungssequenz oder automatische Levelende-Sequenz; ein besiegter Boss
beendet nur seinen eigenen Ablauf. Simons echte Angriffe und Kontaktschaden
funktionieren weiterhin. Der Mode7-Körper wird mit seiner nativen Transformation
und Transparenz separat dargestellt. Die originale Boss-KI behält ihre
Angriffsmuster und teilweise feste Bewegungsgrenzen; sie wird dadurch nicht
zu einer beliebig programmierbaren KI. Fern liegende Instanzen pausieren.

Beim ersten Spieltest wird sein eigener
nativer Körper samt Hilfsteilen, Original-KI, Grafik- und Rasterkontext vorbereitet
und lokal zwischengespeichert. Der F5-Test muss dafür keinen ursprünglichen
Bosslevel starten.

**Klassische Bossbegegnung** zeigt zusätzlich den Begegnungsbereich. In diesem
Modus gibt es jeweils eine aktive Begegnung.
Andere Gegner und dynamische Objekte pausieren währenddessen und werden anschließend fortgesetzt;
dadurch bleiben ihre Grafikressourcen von den Bossressourcen getrennt.
Die Höhe des Kampfbodens folgt dem Boden unter dem Platzierungspunkt. Viele
Original-Bossdaten beschreiben einen unsichtbaren Szenencontroller; dessen
Höhe darf nicht den Kampf gegen den Boden verschieben. Die Karten-Vorschau
und der Begegnungsrahmen berücksichtigen diese Ausrichtung. Die Y-Angabe
wählt damit den Boden der Begegnung; sie definiert keine neue freie Boss-KI.
Die eigene Levelgrafik bleibt auch während Mode7-Kämpfen sichtbar. HUD und
Mode7-Körper verwenden getrennte Rasterabschnitte und Farben.

Im Detaildialog steuert `direct` einen vorbereiteten Kampfstart, `sequence` den
frühen nativen Bossablauf. Das sind Boss-Einleitungen; vollständige ursprüngliche
Level-Kamerafahrten und Szenenskripte werden damit nicht automatisch nachgebaut.
Diese Start-/Endeinstellungen gelten für klassische Begegnungen.
`continue` führt nach dem Kampf im selben Raum weiter, `exit` benutzt den ersten
Ausgang des Raums (ohne Ausgang bleibt man im Raum). Ein Tod startet die eigene
Karte erneut. Mode7-Körper werden nativ gezeichnet und haben eine eigene
Grafikbehandlung. Originale feste Bewegungsgrenzen und Bossphasen gelten weiterhin;
neue KI oder frei definierbare Angriffsabläufe sind damit noch nicht verbunden.

**Start** setzt Simons Startpunkt im gewählten Raum. **Ausgang** setzt einen
markierten Bereich. Mit **Objekte bewegen** anklicken, Zielraum aus der Liste wählen,
Ziel X/Y und Zielebene einstellen und **Übernehmen** drücken.
`up` verlangt die Hoch-Taste im Bereich; `touch` wechselt beim Betreten.

**Originalkarte importieren** liest einen Originalraum 0–67 als zusätzlichen,
bearbeitbaren Raum ein. Die Zahl bezeichnet den internen Raum, nicht die auf
dem Bildschirm angezeigte Stufe. Vollständig erfasst sind derzeit horizontale
Mode1-Karten. Gegnerplatzierungen werden aus der nativen Liste übernommen,
soweit sie zu den unterstützten Monster-Codes gehören. Für übersprungene
Spezial-/Dekorobjekte erscheint ein Hinweis.

## Grenzen dieser Fassung

- Vertikale Originalkarten und Mode7-Räume lassen sich noch nicht vollständig
  als Karte importieren. Ihre Grafiken stehen in der freien Quellauswahl bereit.
  Eigene hohe Räume und gemischte Grafiken sind bereits spielbar.
- Vollständige Levelskripte für Tore, Brückenanimationen und Treppenverbindungen
  sind noch nicht frei kombinierbar. Die Szenenobjekte lassen sich ansehen und
  bearbeiten; eine eigene Platzierung übernimmt nicht automatisch ihren ganzen
  Original-Levelablauf. Klassische Bosskämpfe laufen als einzelne vorbereitete Begegnungen.
- Die frühere gemeinsame OBJ-Grafik-/Palettengrenze entfällt im eigenen
  Leveltest. Die native Objekt-KI mit 37 aktiven Plätzen sowie jeweils eine
  aktive klassische Bossbegegnung bleiben Grenzen dieser Fassung. Freie Bosse
  haben getrennte Kontexte; die Zahl gleichzeitig aktiver Instanzen wird durch
  Rechenleistung und die jeweiligen nativen Hilfsteilgrenzen beschränkt.
- Es gibt noch keinen Export als fertige Kampagne/Mod oder als ROM-Patch.
  HD-PNGs werden weiterhin in den bestehenden HD-Werkzeugen bearbeitet; die
  Kartenansicht und dieser Spieltest verwenden Originalgrafiken.

Original-ROM, normaler Spielstand und Spielkonfiguration werden nicht
überschrieben. Projektdateien enthalten Karten und Platzierungen; die nativen
Grafikdaten werden lokal aus der eigenen ROM ergänzt. Testinstanzen und Caches
liegen unter `artwork-local/level-editor/`.

## Technischer Nachweis

`tools/test_level_editor.py` prüft Projekttransaktionen und Laden/Speichern,
echte Tk-Bediencallbacks, Originalkartenabgleich, native Bodenkollision und
Bewegung, einen fremden Monster-Code, Raumwechsel, zwei getrennte Spielebenen,
Kamera/Ringpuffer, atomare Fehlerbehandlung und das Schließen während Teststart.
Der Rasterabgleich liest Bildpixel programmgesteuert; es wird kein Bildbetrachter
geöffnet. Beide Buildvarianten werden mit dem inaktiven Standardpfad gebaut.

`tools/test_level_tiles.py` prüft die Quellen im Projektformat, den freien
Grafikpicker, Kopieren zwischen Räumen/Ebenen, Mode7-Dekodierung, unabhängige
Farben, Transparenz und native Sprite-Priorität. Im Spieltest werden 17
Quell-/Palettenkombinationen und ein Raumwechsel geprüft. Ungültige Verweise
in Grafikpaketen werden ohne Änderung der aktiven Szene abgewiesen.

`tools/test_level_parts.py` prüft die Bauteilgalerie über echte Tk-Callbacks,
Längenänderung, 8px-Platzierung, maskierte Treppen, zusammenhängende Auswahl,
Quelltreue zwischen Räumen/Ebenen, Projektablage und Undo/Redo. Native Spieltests
prüfen Stand und Bewegung auf beiden Plattformvorlagen. `--no-native` führt
nur die Daten- und Bedienprüfungen aus. Kein Bildbetrachter wird geöffnet.

`tools/test_level_objects.py` prüft Sprite-Pixel und Anker in der Karte,
Bildauswahl und Plattformparameter, den Startkatalog mit allen 68 Abschnitten,
Originalvorschau/Kopiergrenze und Original-Spieltests. Native Tests prüfen beide
Plattformachsen einschließlich Umkehren, Mitfahren und Abspringen sowie einen
Mode7-Originalabschnitt. Auch hier überspringt `--no-native` die Spieltests.

`tools/test_level_actors.py` prüft Fledermaus-Kontext, Beschriftung, echte
Bedienaktionen, eigene Werte, Duplizieren, Speichern und Kerzenimport. Nativ werden
Gesundheit, tatsächlicher Kontaktschaden und beide Flammenposen geprüft; für alle
14 Boss-Codes werden 90 Felder mit Zustandsänderungen und wirklich gezeichneten
OBJ-/Mode7-Pixeln geprüft. Das ist kein vollständiger Durchlauf aller Angriffs-
und Todesphasen. `tools/test_level_boss_end.py` prüft zusätzlich Einleitung,
Rückkehr, Ausgang, Spielertod und Sturz, einschließlich Wiederherstellung der
gewöhnlichen Objektgrafik und Kerzenflags. Alle Bildprüfungen laufen ohne
Bildbetrachter über die tatsächlichen Pixel.

`tools/test_level_editor_ui.py` sendet echte Tk-Mausereignisse an ein sichtbares
Editorfenster. Geprüft werden Hinzufügen, Platzierungsvorschau, Ziehen kleiner
Fledermäuse, Drag-and-drop aus der Bibliothek, Originalkopie bei der ersten
Änderung, Schutz bestehender ungespeicherter Projekte und Undo. Layout-Prüfungen
bei 1280×900 und 4K-Skalierung prüfen die Erreichbarkeit der Schaltflächen ohne
Bildbetrachter. F5 wird außerdem gegen den aktuell geöffneten Raum geprüft.
Zusätzlich werden Figurenauswahl bei aktivem Geländepinsel, schnelle Klicks ohne
Dialog, direkte Werteänderung, sofortiges Löschen und Undo geprüft.

`tools/test_level_free_bosses.py` prüft eigene HP nach der nativen Initialisierung,
zwei unabhängige Kopien desselben Bosses mit einem normalen Gegner, freie Kamera,
echten Kontaktschaden und Peitschentreffer sowie Boss-Tod ohne Levelwechsel.
Alle 14 Bossgruppen laufen jeweils 180 Felder mit Zustandsänderungen, sichtbaren
Teilen und unveränderter gemeinsamer Bodenfläche. Beim Mode7-Boss wird zusätzlich
der transparente native Körper geprüft. Das ersetzt keinen vollständigen
Durchlauf sämtlicher Phasen aller Bosskämpfe.

`tools/test_level_studio.py` prüft die gemeinsame Fensterverwaltung, verknüpfte
Levelwerte, Namen, Variante und Einfügen sowie 1280×900 und mit `--ui4k` die
4K-Skalierung. `--native` prüft zusätzlich Knochenangriff, New Game+, die beiden
zusätzlichen Bosscontroller und das tatsächliche Pausieren des Hintergrundtests.
Die Tests verwenden eine private Kopie der Werkstatt und prüfen, dass die
Künstlerdaten unverändert bleiben. Die eigenständige Werkstatt wird weiterhin
mit `tools/test_monster_workshop.py` geprüft.

`tools/test_level_isolation.py` prüft 237 Platzierungen einschließlich O-000F,
eine Mischung oberhalb des früheren Grafikbudgets, unabhängig verglichene
Gegnerpixel und unveränderte Levelpixel. Er prüft außerdem das Aktivieren ferner
Gegner, Zustandserhalt beim Zurückgehen, Kerzen hinter dem 128. Eintrag,
Szenenkulissen, den Boden während zweier Bossarten und originale HUD-Glyphen
beim Mode7-Boss. Die Tests lesen Pixel und Speicher ohne Bildbetrachter.
