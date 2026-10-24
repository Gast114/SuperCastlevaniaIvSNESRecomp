# Castlevania IV – Level-Editor

Erste benutzbare Fassung vom 24.10.2026. Der Editor ist eine separate Anwendung
mit Karte und Werkzeugen, angelehnt an den Arbeitsablauf von Lunar Magic.
Beim Ausbau sind bestehende Levels umbauen und neue Levels erstellen gleich wichtig.

## Start und erster Versuch

`Level_Editor_starten.cmd` doppelklicken. Beim ersten Start werden Originaldaten
aus deiner eigenen USA-ROM vorbereitet. Danach werden sie wiederverwendet.
Die vorhandene Python-Umgebung der HD-Werkzeuge wird verwendet.

Die **Erste_Testwelt** enthält zwei verbundene Räume, Boden, eine Plattform und
M-0012. Sie wird einmalig angelegt und bei späteren Starts nicht überschrieben.
Mit **Speichern unter** eine eigene Fassung anlegen. Projekte liegen standardmäßig
unter `artwork-local/level-editor/projects/` und enden auf `.sc4level.json`.

**F5 / Spieltest** startet eine eigene Spielinstanz mit der aktuellen Karte,
auch ohne vorher zu speichern. **Test beenden** schließt sie. Nach einer Änderung
F5 erneut drücken. Das Spielfenster muss den Eingabefokus haben, um zu spielen.
Die Originalsteuerung des privaten Spieltests gilt. Native Speicherstände und
Rewind gehören noch nicht zum Projektformat; nach Tod oder versehentlichem
Verlassen des Tests mit F5 neu starten.
Der Spieltest verwendet Ton, wenn ein Audiogerät verfügbar ist, und startet
sonst automatisch ohne Ton. Run-ahead und Rewind sind nur für diese private
Testinstanz deaktiviert, weil sie den Projektzustand noch nicht mitspeichern.

## Karte bearbeiten

### Grafiken frei aus allen Abschnitten mischen

Rechts unter **Grafiken aus allen Abschnitten** die gewünschte **Quelle**
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

Bereiche mit **Auswahl → Strg+C/V** auch zwischen Räumen oder Ebenen kopieren.
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
- **Auswahl** zieht einen Bereich auf. **Strg+C**, **Strg+V** und anschließend
  Linksklick kopieren ihn. **Entf** löscht die Auswahl oder das gewählte Objekt.
- Rechtsklick nimmt eine Kachel auf. Mittlere Maustaste verschiebt die Ansicht.
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
abschneiden würden, werden abgewiesen. **Raumwerte übernehmen** bestätigt die Werte.

Der Kollisionsmodus **3 · Zwei Spielebenen** hält die Böden vor und hinter dem
Zaun unabhängig. **0/2** verwenden den Vordergrund; **1** kombiniert beide
Kollisionsebenen nach Originalregel. Importierte Räume behalten ihren Modus.

## Monster, Start und Ausgänge

Unter **Monster** einen Code wählen und in die Karte klicken. Die Varianten,
Koordinaten und Spielebene lassen sich unter **Auswahl / Ausgang** ändern.
Monster werden in der Karte als beschriftete Marker gezeigt; ihre echte KI
und Animation laufen im Spieltest. Die Codes entsprechen der Monsterwerkstatt.
Geschosse und belegte Hilfsteile bleiben bei ihrem Monster.

**Start** setzt Simons Startpunkt im gewählten Raum. **Ausgang** setzt einen
markierten Bereich. Mit **Auswahl** anklicken, Zielraum aus der Liste wählen,
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
- Geskriptete Tore, Brückenanimationen, Treppenverbindungen, bewegte
  Levelobjekte und Boss-Abschlüsse brauchen eigene Werkzeuge und Adapter.
- Boss-Codes können als Planungsmarker gespeichert werden. Ein Projekt mit
  Bossmarker wird beim Spieltest mit einer Erklärung abgewiesen.
- Monster aus anderen Levels können platziert werden. Derzeit teilen alle
  Räume eines Projekts elf native Grafikseiten. Unpassende Grafikbudgets oder
  kollidierende Originalpaletten werden vor Testbeginn abgewiesen. Eine
  automatische Palettenumlegung fehlt noch.
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
