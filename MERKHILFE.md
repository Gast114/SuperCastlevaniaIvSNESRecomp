# Meine Merkhilfe zum Spiel

Hier stehen kurze Anleitungen für dich.
Ich ergänze diese Datei, wenn neue wichtige Hinweise dazukommen.
Stand: 27. Oktober 2026.

## HD-Hintergrund hinter der HUD-Anzeige

Die Landschaft wird jetzt auch oben hinter der Lebens-/Punkteanzeige in HD
gezeichnet. Zuvor wurden die oberen 32 Bildzeilen pauschal ausgespart.
Schrift und Balken behalten ihre korrekte Darstellung.

Die Korrektur ist in beiden Windows-Spielordnern installiert. Das Spiel einmal
vollständig schließen und neu starten, damit die neue Version geladen wird.

## Simon wieder im Original – HD-Projekt pausiert

Der neue HD-Simon ist ausgeschaltet. Im Spiel erscheint wieder die Originalfigur.
Das gilt für beide Windows-Spielordner und für das Browser-Spiel.
Im Browser bitte die Spielseite vollständig neu laden.

Die bisherigen Bilder und Versuche bleiben erhalten. Die entfernten Spielpakete
liegen sicher unter `artwork-local\simon-pausiert-2026-10-27\spielpakete`.
Eine kurze Übersicht steht dort im übergeordneten Ordner in `PAUSIERT.md`.

Wir arbeiten erst weiter an den Sprites, wenn du es ausdrücklich möchtest.
Es läuft keine Sprite-Berechnung. Die älteren HD-Simon-Anleitungen weiter unten
beschreiben den Stand vor dieser Pause.

## Level-Editor: eigene Räume bauen

**Grafiken frei mischen:** Rechts unter **Grafiken aus allen Abschnitten**
eine Quelle R-00 bis R-67 wählen, daneben deren Vorder-/Hintergrund.
Einen Block oder eine Kachel wählen und in deine Karte zeichnen. Oben ist
**Zielebene** die Ebene deines eigenen Raums. Quelle und Ziel sind unabhängig.
Auch kleine Ausschnitte aus verschiedenen Levels lassen sich zusammen verwenden.
Originalfarben bleiben erhalten. **Auswahl → Strg+C/V** funktioniert auch
zwischen Räumen und Ebenen. **Alle Grafikquellen vorbereiten** lädt den Vorrat
einmalig; die Quellen sind auf diesem Rechner bereits vorbereitet.
Mode7-Grafiken gibt es ebenfalls, als statische Bausteine ohne die ursprüngliche
Rotation/Animation. Beide Wege bleiben gleich wichtig: alte Levels umbauen
und neue Levels von Grund auf erstellen.

`Level_Editor_starten.cmd` doppelklicken. Eine bearbeitbare Testwelt mit zwei
Räumen, Boden, Plattform und M-0012 wird einmalig angelegt.

Rechts einen Block wählen und in die Karte zeichnen. Oben zwischen Vordergrund
und Hintergrund wechseln. **Kollision anzeigen** zeigt begehbare/feste Bereiche.
**Kollision → Fest/Frei** bearbeitet sie unabhängig von der Grafik.
Für getrennte Böden vor/hinter dem Zaun gibt es **3 · Zwei Spielebenen**.

**Monster**: Code wählen und platzieren. **Start** setzt Simon.
**Ausgang** setzt eine Verbindung; unter **Auswahl / Ausgang** Zielraum,
Zielkoordinaten und Zielebene einstellen. `up` = Hoch drücken, `touch` = berühren.

**F5 / Spieltest** startet die aktuelle Karte in einem eigenen Spielfenster.
Nach Änderungen erneut F5 drücken. **Test beenden** schließt dieses Fenster.
**Strg+S** speichert, **Strg+Z/Y** macht Änderungen rückgängig/wiederholt sie.
Mit Auswahl und **Strg+C/V** kopierst du Kartenbereiche. Rechtsklick nimmt
eine Kachel auf; Mitteltaste verschiebt, Strg+Mausrad zoomt.

Projekte: `artwork-local/level-editor/projects/`, Dateiendung `.sc4level.json`.
Original-ROM und normale Spielstände bleiben erhalten. Originalkartenimport
zunächst für horizontale Mode1-Räume; Bosse sind noch Planungsmarker.
Weitere Grenzen und Bedienung: [LEVEL_EDITOR.md](docs/LEVEL_EDITOR.md).

## Monster-Werkstatt: Codes, Aktionen und eigene Namen

`Gegner_Werkstatt_starten.cmd` startet die neue Monsteransicht.
Links einen **Code** wählen, zum Beispiel **M-0012**, dann **Spawnen / neu starten**.
Einen eigenen Namen kannst du bei **Dein Name** eintragen und speichern.

Beim Spawnen wird jetzt kein Herkunftslevel mehr gestartet. Monster und Bosse
laufen im gemeinsamen neutralen Testraum. Die Originalfarben werden beim ersten
Start einmalig vorbereitet und danach wiederverwendet.

Original und Redesign laufen nebeneinander auf neutralem Boden. **Ziel links/rechts**
beeinflusst die Original-KI. Rechts stehen Gesundheit, Kontaktschaden, Trefferbox
und weitere Live-Werte. Unter Gehen, Springen, Angriff und Sterben findest du die
zugeordneten PNGs. Der Knochen gehört beim Werfer mit unter **Angriff**.
**Aktion abspielen** startet den geprüften Ablauf; ungeprüfte Knöpfe sind grau.
Viele weitere Aktionszuordnungen sind noch offen. **Natürlich** zeigt ihre echte KI.

Rechts unter **Werte** stehen **Normal** und **New Game+** nebeneinander.
Über **Vorschau** kannst du den Durchgang wechseln; das Monster wird neu gestartet.
Beispiel M-0012: Gesundheit 48 → 64, Kontaktschaden weiterhin 3.
Eigene Spielmodi mit eigenen Werten sind als spätere Erweiterung vorbereitet.

PNG auswählen, **PNG öffnen**, in Photoshop im gleichen `artwork`-Ordner speichern:
Das Redesign aktualisiert sich live. **Einzelteile** zeigt optionale Teile,
**Grafikvarianten** weitere native Fassungen. Vorhandene Dateinamen bleiben erhalten.
Arbeitsordner: `D:\Super Castlevania IV Recomp\Assets (ausgeschnitten)\Gegner\Werkstatt`.

**Dieses Monster als PNG-Set** exportiert die Vorlagen mit Code-Namen und Zuordnung.
PNGs meist 387×387 Pixel: ganze transparente Leinwand behalten, nicht zuschneiden.
Die ZIP entpacken und später im HD-Import als Gegnerprojekt verwenden.

Alle 47 aktuell auswählbaren normalen Codes wurden in der neutralen Szene sichtbar geprüft.
Auch M-007F funktioniert jetzt ohne seinen bisherigen Level-Umweg.
Die alte Skelett-Sammlung unter `Gegner\02_Skelette_Alle_Aktionen` bleibt erhalten.
Weitere Hinweise: `docs\ENEMY_WORKSHOP.md`.

### Bosse in der Werkstatt

Werkstatt schließen und über `Gegner_Werkstatt_starten.cmd` neu starten.
**Bosse** einschalten und einen Boss-Code auswählen.
Die Bossgrafiken werden vollständig geladen; Kamera und Spielerziel bleiben
stabil. Beim ersten Start werden die alten Bossvorlagen automatisch aktualisiert.
Deine schon bearbeiteten PNGs bleiben erhalten.

Bei **M-0081** ist der große Mode7-Körper jetzt in Bewegung sichtbar.
Sein HD-Körperbild ist noch nicht austauschbar; die anderen PNG-Teile schon.
Einzelne Bossaktionen sind noch nicht zugeordnet und stehen bei **Noch zuordnen**.

Monster später in anderen Levels zu verwenden, ist durch diese Trennung
vorbereitet. Ein Platzierungseditor und der Einbau in die Spiellevels folgen
separat; deine bestehenden Level wurden dafür noch nicht geändert.

## Menügröße auf deinem 4K-Bildschirm

Spiel neu starten und mit Escape das Menü öffnen. Schrift und Knöpfe werden
jetzt automatisch größer; auf 4K ist die Voreinstellung 200%.

Oben bei **Menu size** kannst du **Automatic** oder **100% bis 250%** wählen.
Die Auswahl wird gespeichert. Bei kleinen Fenstern wird die Größe begrenzt,
damit die Bedienung erreichbar bleibt.

Unter **Shortcuts**: im Feld **Filter actions** suchen, auf das Tastenkürzel
klicken und die neue Kombination drücken. **Clear** löscht, Escape bricht die
Eingabe ab. Controller-Kürzel stehen zum Aufklappen unter der Liste.

## Rewind, NEW GAME+ und neue HD-Werkzeuge

F8 öffnet Rewind. Mit Links/Rechts einen Zeitpunkt aussuchen, mit Enter oder
Leertaste dort weiterspielen. Escape oder Rücktaste bricht ab. Der Fehler,
bei dem das Menü sofort wieder aufging, ist behoben.

NEW GAME+ startet den originalen schwereren zweiten Durchgang, wie nach dem
Durchspielen. START bleibt der normale erste Durchgang.

`HD_Import_starten.cmd` öffnet das Importfenster. Vorlagen als Bilderübersicht
ansehen, fertige PNGs im vorbereiteten Ordner ablegen, Paket erstellen und
anschließend mit dem Einbauen-Knopf in beide Spielversionen übernehmen.
4,x-fache Arbeitsauflösung ist möglich; du musst nicht auf 10× vergrößern.
Anleitung: `docs\HD_IMPORT.md`.

Die erste Gegner-Unterstützung ist für die Skelette vorbereitet. Unter
Escape → HD graphics → Enemy graphics werden ihre Posen automatisch gesammelt.
Spiegelung und Zuordnung übernimmt das Spiel; du musst keine Tiles auswählen.
Neue Gegner-HD-Zeichnungen sind noch nicht enthalten. Anleitung: `docs\ENEMY_HD.md`.

Der Debug-Marker vom 22. Oktober an der Zugbrücke ist korrigiert: Die
Hintergrundkulisse beginnt rechts nicht erneut. Das neue Paket heißt
`hd_packs/stage-01-user-a02-v3`. Nach den Änderungen das Spiel neu starten.

## A02: neue Landschaft eingebaut

Deine elf neuen Bilder sind in beiden Spielordnern eingebaut. Das ausgewählte
Paket heißt `hd_packs/stage-01-user-a02-v3` und wechselt automatisch zwischen
dem bisherigen Eingang mit Zugbrücke und dem neuen zweiten Abschnitt.

Das Spiel einmal vollständig schließen und neu starten. Mit F2 siehst du den
Eintritt und den hochfahrenden Zaun. Mit F3 und Hoch prüfst du die Drehtür und
den Wechsel vor/hinter den Zaun. Diese Abläufe sind im Spiel geprüft.

Deine Arbeitsauflösung von rund 4,031 Pixeln pro Originalpixel ist passend.
Du musst die Bilder nicht auf 10× vergrößern. Die Photoshop-Proportionen des
Zauns bleiben erhalten. Die Hintergrundzuordnung am Ende und die Position des
Gargoyles sind korrigiert; die Statue ist in der Spielaufnahme sichtbar.

Die gespeicherte Datei `Assets (ausgeschnitten)\Stage 01\Komplett HD.psd`
kann direkt ausgelesen werden, einschließlich Ebenennamen und Positionen.
Du brauchst die vielen Einzelteile nicht von Hand auszuschneiden.

F2 zeigt den Eintritt mit hochfahrendem Zaun. F3 zeigt die erste Drehtür;
mit Hoch wechselt Simon auf die andere Seite des Zauns. Es gibt eine begehbare
Spielebene vor dem Zaun und eine begehbare Spielebene dahinter. Die hintere
Spielebene nicht mit einer rein dekorativen Hintergrundkulisse verwechseln.
Für den Einbau die vordere und die hintere Spielebene getrennt halten.
Gitter und feste Türrahmen dürfen in Photoshop verknüpft/gruppiert werden
und gemeinsam in eine eigene PNG. Die einzelnen bearbeitbaren Ebenen in der
Photoshop-Datei behalten. Die frühere Empfehlung, den Rahmen zwingend separat
zu liefern, war nicht erforderlich. Das bewegliche Türblatt bleibt separat:
vier Ansichten. Die drei Gargoyle-Bilder zeigen unterschiedliche Augenvarianten.
Diese Animationsbilder nicht fest in die Landschaft hineinmalen.

Falls du selbst PNGs exportierst: RGB mit echtem Alphakanal, unveränderte
Arbeitsauflösung und Positionen. Vordere Spielebene und Gitter mit Türrahmen
mit demselben A02-Ausschnitt und derselben Arbeitsfläche exportieren. Die
hintere Spielebene im selben Weltbezug halten. Die separate Burg-/Himmelskulisse
hat ihre eigene Fläche und scrollt langsamer. Türansichten auf einer gemeinsamen
Arbeitsfläche oder als vorhandenen Streifen behalten; nicht einzeln zentrieren.
Die Ebene Original, Hilfsrechtecke und Muster außerhalb der Szene ausblenden.
Transparente Zaunlücken erhalten; echten schwarzen Himmel schwarz lassen.
Die genaue Registrierung und die technische Aufteilung übernimmt der Import.

Deine fertigen Exporte vom 23. Oktober liegen unter `Stage 01\A02\HD`:
`Spielbebene-vorne.png`, `Spielebene-Hintergrund.png`, `Gitter.png`,
`Stage-01-A02-BG-HD.png`, `Tür-01.png` bis `Tür-04.png` und
`Gargoyle-01.png` bis `Gargoyle-03.png`. Das sind elf neue Bilder mit echtem
Alphakanal. Die vier Türbilder haben alle dieselbe Arbeitsfläche (153×162).
Die Landschaften wurden unterschiedlich eng zugeschnitten; beim Import ihre
Positionen wiederherstellen, nicht ihre linken oberen Ecken gleichsetzen.
Die Burg-/Himmelskulisse ist eine zusätzliche Ebene neben den zwei Spielebenen.
Sicherung vor der Installation:
`D:\Super Castlevania IV Recomp\backup\hd-artwork\2026-10-23-stage01-a02-v2`.
Spielstände, Steuerung und Charakterbilder wurden bei der Installation geprüft
und sind unverändert. Technische Details stehen in `docs\HD_A02.md`.

## Das Spiel starten

Dein Projekt liegt hier:

```text
D:\Super Castlevania IV Recomp\SuperCastlevaniaIvSNESRecomp
```

Öffne darin diesen Ordner:

```text
build-play\game
```

Starte dort `SuperCastlevaniaIvSNESRecomp.exe`.

Es gibt auch eine Spielversion im Ordner `build`.
Die beiden Spielordner haben eigene Einstellungen und eigene Bilder.
Änderungen werden nicht automatisch zwischen ihnen kopiert.

## Die Simon-Bilder austauschen

Öffne im Projekt diesen Ordner:

```text
build-play\game\characters\simon-user-hd-three-poses-v1
```

Dort kannst du diese Bilder ersetzen:

| Pose | Dateiname | Größe in Pixeln |
| --- | --- | --- |
| Stehen | `Idle-01_HD_10x_240x460.png` | 240 × 460 |
| Ducken | `Ducking-01_HD_10x_230x350.png` | 230 × 350 |
| Springen | `Jumping-01_HD_10x_200x450.png` | 200 × 450 |
| Laufen 1 | `Walking-01_HD_10x.png` | 330 × 510 |
| Laufen 2 | `Walking-02_HD_10x.png` | 330 × 510 |
| Laufen 3 | `Walking-03_HD_10x.png` | 330 × 510 |
| Laufen 4 | `Walking-04_HD_10x.png` | 330 × 510 |
| Laufen 5 | `Walking-05_HD_10x.png` | 330 × 510 |
| Laufen 6 | `Walking-06_HD_10x.png` | 330 × 510 |

1. Bewahre eine Kopie des alten Bildes auf.
2. Speichere dein neues Bild als PNG mit durchsichtigem Hintergrund.
3. Behalte den Dateinamen und die Bildgröße bei.
4. Ersetze die Datei im oben genannten Spielordner.

Das laufende Spiel lädt die Bilder normalerweise von selbst neu.
Falls du noch das alte Bild siehst: Drücke **Esc**.
Öffne **Character workshop** und klicke auf **Reload**.

Für diesen Austausch brauchst du `character.json` und `body.png` nicht zu ändern.
Die Größe der Figur im Spiel und ihre Position bleiben dabei erhalten.

**Wichtig:** Der Ordner `Assets (ausgeschnitten)\Simon Belmont` enthält deine
Vorlagen. Das Spiel liest seine Bilder aus dem Ordner `characters`.
Eine neue Vorlage allein ändert deshalb noch nicht das Bild im Spiel.

Wenn du die Spielversion unter `build` benutzt, ersetze die Bilder dort:

```text
build\characters\simon-user-hd-three-poses-v1
```

## Deine in Photoshop verbesserten Laufbilder

Die sechs überarbeiteten Bilder sind seit dem 23. Oktober im Spiel eingebaut.
Sie sind in beiden Spielordnern und im lokalen Quellpaket gespeichert.
Deine ausgeschnittenen Vorlagen bleiben hier erhalten:

```text
artwork-local\lora-pilot-2026-10-21\walking-neural-edit-2026-10-22\review-v1\frames
```

Für das Spiel haben alle sechs Laufbilder jetzt **330 × 510 Pixel**.
Nur die transparente Arbeitsfläche wurde ergänzt. Deine Zeichnung wurde
nicht gestreckt, verkleinert oder neu von der KI gemalt.

Wenn du direkt ein Spielbild in Photoshop bearbeitest, behalte diese ganze
Arbeitsfläche bei. Bitte nicht wieder eng auf die Figur zuschneiden.
Die Position der Figur auf der Arbeitsfläche soll beim Speichern gleich bleiben.
Dann kannst du das PNG im Spielordner direkt ersetzen.

Falls das laufende Spiel noch die alten Bilder zeigt:
**Esc → Character workshop → Reload**.

Vorherige Spielbilder und deine neuen Vorlagen sind gesichert unter:
`D:\Super Castlevania IV Recomp\backup\hd-artwork\2026-10-23-simon-photoshop-walk`.

## Weitere Animationen als einzelne Bilder vorbereiten

Ein PNG pro Frame ist am einfachsten. Für die Treppe zum Beispiel:
`going-upstairs-01.png` bis `going-upstairs-06.png`.
Die sechs Original-Vorlagen liegen jetzt unter
`D:\Super Castlevania IV Recomp\Assets (ausgeschnitten)\Simon Belmont`.

Bei den späteren HD-Bildern bitte für eine Animation immer dieselbe transparente
Arbeitsfläche verwenden. Die Bilder nicht einzeln zentrieren oder eng zuschneiden.
Ein fester Bezugspunkt hilft bei der Zuordnung im Spiel. Die Beine dürfen sich
natürlich innerhalb der Fläche bewegen. Wir verwenden weiter nur **10x**.

## HD ein- und ausschalten

- **Strg + H:** Zwischen HD und Original wechseln.
- **Esc → HD graphics:** Das Menü für die HD-Bilder öffnen.
- Für HD verwenden wir **10×**. Kleinere Stufen werden im Menü nicht angeboten.
- **Esc → Character workshop → Use character pack:** Nur die neue Simon-Figur ein- oder ausschalten.

Bisher gibt es neun HD-Posen für Simon: Stehen, Ducken, Springen und sechs Laufbilder.
Die Laufbilder funktionieren in beide Richtungen.
Bei noch fehlenden Posen, zum Beispiel beim Angriff, erscheint die Originalfigur.
Der Bilderordner heißt weiterhin `simon-user-hd-three-poses-v1`.
Du musst deshalb keinen neuen Ordner auswählen.

## Ein Bild nach dem anderen ansehen

1. Gehe im Spiel zu der Stelle, die du genau ansehen möchtest.
2. Drücke **Strg + P**. Das Spiel hält an. Das Bild bleibt hell.
3. Drücke **Strg + N** für genau ein weiteres Bild.
4. Halte dabei eine Richtung oder eine Aktion gedrückt, wenn Simon sich bewegen soll.
5. Drücke wieder **Strg + P**, um normal weiterzuspielen.

In einem kleinen Fenster siehst du die Bildnummer und zwei Knöpfe:
**Next frame** zeigt das nächste Bild. **Resume** setzt das Spiel fort.
Du kannst das Fenster am Titel verschieben. Der kleine Pfeil klappt es ein.
Du kannst den Modus auch unter **Esc → Performance → Inspect frames** einschalten.
Während du einzelne Bilder ansiehst, bleibt der Ton aus.

Die beiden Tasten kannst du unter **Esc → Shortcuts** ändern.
Suche dort nach **Frame by frame**.
Du kannst auch in diesem Modus mit **Strg + D** einen Fehler festhalten.

## Ein Problem festhalten

1. Gehe im Spiel zu der Stelle mit dem Problem.
2. Drücke **Strg + D**.
3. Schreibe kurz auf, was falsch aussieht oder nicht funktioniert.
4. Speichere die Notiz mit **Strg + Enter**.

Die Aufnahme enthält ein Bild und den Spielzustand.
Du findest sie hier:

```text
build-play\game\debug_markers
```

Jede Aufnahme bekommt einen eigenen Unterordner.
Sag mir den Namen des Ordners, damit ich die richtige Stelle finde.

## Tasten ändern und Speicherstände finden

Öffne **Esc → Shortcuts**.
Dort siehst du die Tastenkürzel und kannst sie ändern.
Wenn du eine Taste geändert hast, gilt deine neue Belegung.

Deine Speicherstände liegen hier:

```text
build-play\game\saves
```

## Weitere HD-Posen vorbereiten

Bei vielen Figuren wollen wir künftig eine Vorlage wiederverwenden.
Aktuell versuchen wir das mit einer LoRA und Vorlagen für die Körperhaltung.
Du musst dann nicht jedes Bild einzeln von einer Bild-KI erstellen lassen.
Die recherchierten Wege und meine Empfehlung stehen in [SPRITE_ANIMATION.md](SPRITE_ANIMATION.md).

Wenn du fertige Einzelbilder lieferst, gilt weiter:

- Gib mir die kleinen Originalvorlagen und die passenden HD-PNGs.
- Das HD-Bild hat die zehnfache Breite und Höhe der Vorlage.
  Beispiel: 24 × 46 Pixel werden zu 240 × 460 Pixeln.
- Behalte den durchsichtigen Hintergrund bei.
- Schneide Haare, Hände und Schuhe nicht ab.
- Halte Figur, Kleidung, Farben und Licht zwischen den Bildern gleich.
- Eine Blickrichtung nach rechts reicht. Die andere Seite spiegelt das Spiel.
- Du brauchst keinen großen Bildbogen zu bauen. Einzelne PNGs reichen.

Die DPI-Zahl ist hier egal. Entscheidend sind die Pixelmaße.
Neue Posen müssen zusätzlich zugeordnet werden. Das übernehme ich.

## Blender für neue Bewegungen

Blender ist jetzt auf diesem PC eingerichtet. Du findest es im Startmenü als
**Blender 4.5 LTS**. Es kostet nichts.

Die Programmdatei liegt hier:

```text
C:\Users\Gaming\AppData\Local\Programs\Blender-4.5.14\blender.exe
```

Unser erster Arbeitsordner liegt im Projekt unter:

```text
artwork-local\blender-pilot-2026-10-21
```

Dort gibt es eine Verknüpfung **Simon-Exportstudio**. Sie öffnet das vorbereitete
Blender-Projekt. Kamera, Licht und Bildgröße sind schon eingestellt.
Das Studio allein enthält noch keine bewegliche 3D-Figur.

**Die fertige erste Probe öffnest du mit „Simon-Pilot“.** Dort ist die Farbfigur
mit Skelett und Bewegungen enthalten. Die eigentliche Datei liegt unter
`walk-final\Simon_Pilot.blend`. Mit der Leertaste startest und stoppst du die
Wiedergabe in Blender. Speichere eigene Änderungen unter einem neuen Namen.

Zum schnellen Ansehen brauchst du Blender gar nicht:

- Öffne `walk-preview\Vorschau.html` im Arbeitsordner.
- **Abspielen** zeigt die sechs Laufbilder als Bewegung.
- **Nächstes Bild** zeigt jeweils ein einzelnes Bild.
- Mit der Zahl daneben stellst du nur das Tempo der Vorschau ein.
- In `attack-preview\Vorschau.html` gibt es zusätzlich drei Angriffsbilder.
  Sie zeigen eine fertige Bibliotheksbewegung. Simons Peitschenangriff muss noch
  passend zum Original gestellt werden.

Die PNGs in den Vorschauordnern haben einen durchsichtigen Hintergrund.
Die Datei `placement.json` merkt sich Größe und Position.
Diese Bilder werden noch nicht automatisch im Spiel benutzt.

Für diesen Versuch wurden 20 kostenlose Meshy-Credits verwendet.
Der erste Skelett-Aufbau war kostenlos. Beim nächsten wollte Meshy ein Abo.
Wir haben die Farbfigur deshalb lokal in Blender mit dem vorhandenen Skelett
verbunden. Es wurde kein Abo gekauft.

**Deine Rückmeldung: Das 3D-Modell sieht zu schlecht aus.** Diese Probe ist
deshalb als Ersatz abgelehnt. Die Dateien bleiben zum Nachsehen erhalten.

Ein 2D-Skelett war danach als Alternative vorgeschlagen. Du möchtest jetzt zuerst
LoRA ausprobieren. Dieser neue Versuch ist im nächsten Abschnitt beschrieben.

Das Ziel bleibt: Eine Figur einmal aufbauen. Danach können wir sie für viele
Bewegungen verwenden. Das Animationsprogramm macht daraus durchsichtige PNGs in 10×.
Die Bilder brauchen danach noch die passende Zuordnung zu den Originalposen.
Das Tempo und die Bewegung im Spiel bestimmt weiter das Originalspiel.

Deine bisherigen neun HD-Posen bleiben bis zur Auswahl einer fertigen neuen
Probe aktiv. Das Blender-Studio ändert die Figur im Spiel nicht.

## Simon mit LoRA gleich aussehen lassen

Eine **LoRA** ist eine kleine Trainingsdatei für ein Bildmodell. Sie soll lernen,
wie dein Simon aussieht: Gesicht, Haare, Kleidung und Malstil.
Eine **Posenvorlage** zeigt zusätzlich, wo Arme und Beine sein sollen.
So müssen wir die Körperhaltung nicht bei jedem Bild neu in Worten erklären.
Ob die Probe gut genug ist, müssen wir an den fertigen Bildern beurteilen.

Du möchtest das lokal machen. Deshalb läuft der Versuch auf diesem PC.
Deine Bilder werden dafür nicht zu einem Trainingsdienst hochgeladen.
Es gibt keine kostenpflichtigen Cloud-Aufrufe.

Der Arbeitsordner liegt im Projekt hier:

```text
artwork-local\lora-pilot-2026-10-21
```

In diesem Ordner findest du drei Dateien zum Doppelklicken:

- **Status.cmd:** Zeigt, wie weit der Auftrag ist, und eine grobe Restzeit.
- **Anhalten.cmd:** Hält nach dem aktuellen Lernschritt an und speichert einen Zwischenstand.
- **Fortsetzen.cmd:** Macht vom letzten gespeicherten Zwischenstand aus weiter.

Der erste Versuch ist fertig: **600 Lernschritte und drei Probe-Bilder**.
Das Lernen auf der CPU dauerte etwa 93 Minuten. Die Bilder brauchten zusammen
weitere 14 Minuten. Neue Bilder werden künftig mit der GPU berechnet.

Die Probe trifft den gemalten Schwarz-Gold-Look. Die Posen sind noch nicht genau
genug: In einem Bild sollte der Arm waagerecht sein, hängt aber nach unten.
Auch kleine Details der Rüstung ändern sich. Es sind noch keine fertigen
Animationsbilder für das Spiel.

Lass den PC währenddessen eingeschaltet. Der Auftrag hält den automatischen
Ruhezustand während seiner Arbeit fern. Manuelles Ausschalten oder Neustarten
unterbricht ihn. Dann hilft der letzte gespeicherte Zwischenstand.
Regulär wird alle 100 Schritte gespeichert. Über **Anhalten.cmd** wird auch
zwischen diesen festen Punkten gespeichert.

Das Training benutzt acht deiner vorhandenen HD-Bilder.
Das neunte Bild wird nicht mittrainiert. Es dient zum Vergleich.
Die fertige Trainingsdatei liegt hier:

```text
training-local\final\pytorch_lora_weights.safetensors
```

Die ersten drei neuen Bilder liegen unter **review-local**.
Sie zeigen einen Schritt, einen nach vorn gestreckten Arm und einen gehobenen Arm.
Es sind zunächst Bilder mit Hintergrund für die Beurteilung.
Freistellen und Zuordnen zu den Originalposen im Spiel kommen danach.

Diese LoRA gehört zu **SDXL**. Sie passt nicht einfach in ein anderes Modell wie
FLUX. Im Spiel selbst wird die LoRA nicht geladen. Dort werden weiterhin PNGs
verwendet. Deine bisherige HD-Figur bleibt während des Versuchs aktiv.

## Den Bosgame für die Bilder nutzen

Dein Rechner hat einen **Ryzen AI 9 HX 370**, die **Radeon 890M** und **32 GB RAM**.
Davon sind schon **8 GB für die Grafik reserviert**. Die GPU kann zusätzlich
gemeinsamen Speicher nutzen. Für unsere bisherigen Aufgaben reicht das.
Du brauchst die RAM-Aufteilung im BIOS vorerst nicht zu ändern.

Die GPU ist jetzt eingerichtet und hat auch echtes LoRA-Training geschafft.
Ein Lernschritt nach dem ersten Aufwärmen dauerte bei der kurzen Prüfung etwa
**1,3 Sekunden**. Auf der CPU waren es meist **6 bis 11 Sekunden**.
Der erste GPU-Schritt dauerte länger, weil Rechenprogramme vorbereitet wurden.
Ein längerer Lauf kann andere Zeiten ergeben.

Die GPU rechnet am Bild. Die CPU bereitet Daten vor.
Neue Aufträge können alle **24 CPU-Threads** verwenden.
Der zusätzliche **NPU-KI-Chip** wird von diesem LoRA-Ablauf nicht verwendet.
Er braucht andere, dafür vorbereitete Programme und Modelle.

Für die GPU gibt es im Projekt einen eigenen Programmordner:

```text
artwork-local\lora-rocm-runtime
```

Der ältere CPU-Ordner heißt `artwork-local\lora-runtime`.
Die GPU-Werkzeuge müssen mit dem Python aus dem GPU-Ordner gestartet werden.
Nur den alten CPU-Befehl aufzurufen schaltet die GPU nicht ein.
Die genauen Befehle stehen für die Weiterarbeit in `docs\LOCAL_LORA.md`.

Die neue einzelne Arm-Probe liegt unter **review-gpu-2026-10-22-fixed**.
Der Arm zeigt jetzt nach vorn. Der Ellenbogen ist aber noch gebeugt.
Die Pose muss für einen genauen Peitschenangriff noch verbessert werden.
Die ersten drei Bilder unter **review-local** bleiben zum Vergleichen erhalten.

Hier kannst du die Bilder öffnen:

- [Neue Arm-Probe von der GPU](artwork-local/lora-pilot-2026-10-21/review-gpu-2026-10-22-fixed/arm-forward.png)
- [Erste Lauf-Probe](artwork-local/lora-pilot-2026-10-21/review-local/walk-holdout.png)
- [Erste Probe mit Arm nach vorn](artwork-local/lora-pilot-2026-10-21/review-local/arm-forward.png)
- [Erste Probe mit Arm nach oben](artwork-local/lora-pilot-2026-10-21/review-local/arm-up.png)

## Simons gewünschtes Aussehen

- Die braunen Haare sollen nur bis zu den Schultern reichen.
- Der einzelne hervorstehende Knieschoner soll weg.
- Die schwarze Rüstung mit Gold und die Schienbeinrüstung bleiben erhalten.

Die [korrigierte Bildvorlage](artwork-local/lora-pilot-2026-10-21/design-corrections-2026-10-22/Simon_Schulterhaare_ohne_einzelnen_Knieschoner_v1.png)
ist separat gespeichert. Das ist eine gezielte Bildbearbeitung mit Imagegen.
Die LoRA wurde dadurch noch nicht neu trainiert. Die Beschreibung für neue
lokale Bilder enthält jetzt ebenfalls Schulterhaare und keine Knieschoner.

## Die erste Gehserie ist noch nicht passend

Die erste Serie wurde wegen falscher Schulter-, Arm- und Beinbewegungen
abgelehnt. Sie ist nur zum Vergleichen aufgehoben. Nicht als fertige Animation
ins Spiel einbauen. Der feste Oberkörper war ein Fehler: Auch Schultern und
Arme müssen sich in jeder Gehphase ändern.

Die neue Arbeit liegt unter `walking-native-2026-10-22` im LoRA-Pilotordner.
Hier kommen die Formen direkt aus den kleinen Original-Sprites. Alle Bilder
behalten denselben Standpunkt. Die HD-Vorlage gibt nur das Aussehen vor.

### Die verworfene erste Serie ansehen

Die neue Serie liegt hier:

```text
artwork-local\lora-pilot-2026-10-21\walking-2026-10-22\packaged-final
```

- Öffne [Vorschau.html](artwork-local/lora-pilot-2026-10-21/walking-2026-10-22/packaged-final/Vorschau.html).
- **Abspielen** zeigt die Bewegung. **Nächstes Bild** zeigt einen einzelnen Schritt.
- Mit dem Regler änderst du nur das Tempo der Vorschau.
- [Alle_Gehposen.png](artwork-local/lora-pilot-2026-10-21/walking-2026-10-22/packaged-final/Alle_Gehposen.png) zeigt alle sechs Bilder nebeneinander.
- **Animation.webp** ist die bewegte Vorschau als Datei.
- Im Unterordner **frames** liegen die sechs PNGs mit durchsichtigem Hintergrund.
- **Gehposen_10x.zip** enthält die sechs PNGs und die Vorschau zusammen.

Die Bilder wurden lokal mit der Radeon erstellt. Für das Aussehen wurde deine
korrigierte Bildvorlage mit Schulterhaaren verwendet. Die Körperhaltungen kamen
aus sechs festen Posenvorlagen. Unerwünschte zusätzliche Knieschoner wurden an
den betreffenden Bildern lokal nachbearbeitet.
Gesicht und obere Rüstung wurden aus derselben Phase übernommen. Dadurch
fehlte die richtige Bewegung im Oberkörper. Diesen Aufbau verwenden wir nicht
für die neue Serie.

Alle sechs PNGs haben dieselbe Bildfläche. Die Datei **placement.json** merkt
sich den gemeinsamen Ausschnitt und die Position. Hebe diese Datei mit auf.
Die Serie ist noch eine Vorschau. Im Spiel sind weiterhin deine bisherigen
Bilder aktiv. Vor einem Einbau müssen Größe, Standpunkt und Übergänge zu den
anderen Posen geprüft werden.

## Neue Gehserie mit den Original-Bewegungen

Die neue Vorschau liegt hier:

```text
artwork-local\lora-pilot-2026-10-21\walking-native-2026-10-22\packaged
```

- **Originalvergleich.webp** zeigt Original und HD gleichzeitig in Bewegung.
- **Originalvergleich.png** zeigt alle sechs Vergleiche als ein großes Bild.
- Öffne **Vorschau.html** per Doppelklick im Datei-Ordner. Mit **Nächstes Bild**
  oder **Zurück** kannst du jeden Schritt einzeln ansehen.
- Unter **frames** liegen sechs durchsichtige PNGs. Alle sind **320 × 510 Pixel**.
- **Gehposen_10x.zip** enthält die Bilder und die Vorschau zusammen.

Diesmal geben die kleinen Original-Sprites die Formen vor. Das betrifft auch
die Schultern, die Arme und die beiden Beine. Der Oberkörper wird nicht mehr
aus einem einzigen Bild kopiert. Das Aussehen kommt aus der HD-Vorlage und
der lokal gelernten Figur. Es wurden keine Bilder hochgeladen.

Die Bewegung passt so deutlich besser. Bei der Rüstung ändern sich noch kleine
Details zwischen den Bildern. Die Serie bleibt deshalb ein **Entwurf**.
Sie ist noch nicht im Spiel eingebaut. Deine bisherigen Spielbilder sind aktiv.
Hebe **placement.json** mit auf. Darin stehen der gemeinsame Standpunkt und
die Größe für einen späteren Einbau.

Eine geprüfte Sicherheitskopie liegt auch im Backup-Ordner:
`D:\Super Castlevania IV Recomp\backup\hd-artwork\2026-10-21-local-lora\2026-10-22-walking-native-shapes`.

## Gehposen: neue lokale KI-Korrektur

Die Bewegung der letzten Serie bleibt die Vorlage. Die alte Korrektur mit
verzogenen Muskeln und ausgeschnittenen Rocksäumen ist verworfen.
Sie liegt noch unter `walking-identity-2026-10-22`. Bitte nicht einbauen.

Die lokale KI zeichnet die fehlerhaften Stellen neu. Bild 01 bleibt die
Vorlage für das Gesicht. Das runde Rücken-Zeichen aus Bild 02 ist die Vorlage
für die fehlenden Zeichen in 01 und 06. Hautteile werden nicht mehr verzogen.
Fehlerhafte Teile werden für die KI markiert und teilweise in ihrer Vorlage
ausgeblendet. Die KI zeichnet die sichtbaren Ränder und Muskeln neu.

Die neue Vorschau liegt hier:

```text
artwork-local\lora-pilot-2026-10-21\walking-neural-edit-2026-10-22\review-v1
```

- **Vorschau.html:** Beide Fassungen einzeln oder in Bewegung vergleichen.
- **Alle_Gehposen.png:** Alle sechs neuen Bilder nebeneinander sehen.
- **Animation.webp:** Die neue Gehbewegung ansehen.
- **frames:** Die sechs transparenten PNGs in 10x.
- **Gehposen_10x.zip:** Bilder und Vorschau zusammen mitnehmen.
- **placement.json:** Größe und gemeinsamen Standpunkt aufheben.

Die KI-Ausgabe war zunächst nur eine Vorschau. Du hast die sechs Einzelbilder
danach in Photoshop verbessert. Diese bearbeitete Fassung ist jetzt im Spiel
eingebaut. Die älteren Kontaktbilder und ZIPs zeigen noch den KI-Zwischenstand.

Für die Korrekturen gibt es zusätzlich **FLUX.2 Klein** auf deinem Rechner.
Die bisherigen Modelle und Python-Umgebungen wurden nicht geändert.
Es wurden keine Bilder hochgeladen und keine Cloud-Bilder bezahlt.
Beim ersten Versuch gab es einen Fehler mit der AMD-Grafikkarte. Deshalb
laufen diese Korrekturen auf der CPU. Das braucht viel Arbeitsspeicher.

Sprites und Landschaften laufen nacheinander über dieselbe Warteschlange in
ComfyUI. Während ein solcher Auftrag rechnet, soll die andere Aufgabe warten.
Es gibt dafür keinen zweiten KI-Server. Die alten Versuche mit **-cpu** im
Namen wurden abgebrochen. Diese Ordner enthalten keine fertigen Ergebnisse.

Die Berechnung ist fertig. Die Modelle wurden aus dem Arbeitsspeicher entladen.
Die Landschafts-Arbeit kann wieder rechnen.

Geprüfte Sicherheitskopie:
`D:\Super Castlevania IV Recomp\backup\hd-artwork\2026-10-21-local-lora\2026-10-23-walking-neural-repair`.
Die großen Grundmodelle sind dort nicht noch einmal gespeichert.

## Unsere Arbeitsweise

- Nur notwendige, gezielte Prüfungen. Keine unnötigen Testreihen.
- Neue Figuren und Bewegungen entstehen zuerst als Vorschau. Danach folgt der Einbau ins Spiel.
- Neue Alltagshinweise ergänze ich hier in einfacher Sprache.
- Technische Einzelheiten für die Weiterarbeit stehen in `docs/HANDOFF.md`.
