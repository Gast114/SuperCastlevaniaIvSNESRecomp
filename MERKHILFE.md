# Meine Merkhilfe zum Spiel

Hier stehen kurze Anleitungen für dich.
Ich ergänze diese Datei, wenn neue wichtige Hinweise dazukommen.
Stand: 27. Oktober 2026.

## Level-Editor: Originalkatalog, Sprite-Bilder und bewegliche Plattformen (04.11.)

Editor über Level_Editor_starten.cmd neu starten. Er öffnet jetzt „Originalspiel“
mit allen 68 Originalabschnitten. F5 spielt den gewählten Abschnitt nativ.
„Als eigene Kopie bearbeiten“ übernimmt eine unterstützte 2D-Karte in ein eigenes
Projekt; „Neues eigenes Level“ beginnt leer. Vorhandene Projektdateien bleiben
über „Öffnen“ erreichbar. Die alte Testwelt startet nicht mehr automatisch.
Vertikale/Mode7-Abschnitte sind per F5 spielbar; ihre vollständige Kartenansicht
und ihr Kartenimport sind noch nicht umgesetzt. Die Einträge bleiben aufgelistet.

Monster und Objekte haben Sprite-Bilder in Auswahl und Karte. Mit „Objektnamen“
lassen sich zusätzlich die Codes einblenden; Auswahlrahmen/Codes erscheinen beim
Anklicken. Hintere Figuren stehen auch in der Vorschau hinter dem Vordergrund.
Die Sprite-Bilder sind vorhandene Originalposen, keine neue Bildgenerierung.

Unter „Bauteile → Bewegliche Plattformen“ und „Objekte“: O-0017 waagerecht oder
senkrecht wählen, dann den Mittelpunkt setzen. Die Originalbewegung pendelt
80 Pixel nach links bzw. oben und zurück. Der Weg wird angezeigt und muss im
Raum liegen. Nach Auswahl lässt sich die Richtung unter „Bewegung“ ändern.
Beide Varianten tragen Simon und erlauben Abspringen; das ist im echten
Spieltest geprüft. Andere O-Objekte können zusätzliche Levelskripte benötigen.
Persönliche Spielstände, HD-Dateien und die installierte Spiel-EXE unverändert.

## Level-Editor: Steine und Plattformen bequem auswählen (04.11.)

Den Editor über Level_Editor_starten.cmd neu starten. Rechts öffnet sich
„Bauteile“ mit großen Vorschauen für Steine, Plattformen und Treppen.
Vorlage anklicken, dann in der Karte setzen. Plattformlänge: 1 bis 32 Steine.
Das Werkzeug „Bauteil“ setzt mit einem Klick ein ganzes Teil im 8px-Raster;
ein Rahmen zeigt vor dem Setzen seine Größe. H/V spiegelt das Teil.

Umschalt + Rechtsklick auf eine feste Fläche nimmt die zusammenhängende
Plattform auf. Mit Linksklick kopieren. Für freie Ausschnitte „Auswahl“ nutzen.
Namen eintragen und „Auswahl merken“ oder „Pinsel merken“: eigene Bauteile
werden mit dem Projekt gespeichert und funktionieren auch in anderen Räumen
und Zielebenen. Alle Grafikquellen bleiben zugänglich.
„Kollision beim Zeichnen übernehmen“ einschalten, damit die Plattform begehbar ist.
Treppenmasken erhalten die Wand zwischen den Stufen. Die Vorlagen sind feste
Landschaftsteile; bewegliche Plattformen sind weiterhin eigene Spielobjekte.
Bedienung, Speichern/Undo und echte Bodenkollision beider Plattformvorlagen geprüft.

## Breitbild: Gegner warten auf ihre Kollisionsdaten (04.11.)

Der F10-Fehler ist behoben und in beiden Windows-Spielordnern installiert.
Bitte Spiel neu starten und F10 laden. Das Skelett erscheint wieder auf seiner
Plattform. Die Korrektur gilt für die ursprüngliche Ereignisverarbeitung aller
Abschnitte, nicht nur für dieses eine Skelett.

Die alte Breitbild-Anpassung hatte Gegner zu früh erzeugt: Im F10-Vergleich
38 Frames früher, bevor die Plattform in den Kollisionsring geladen war.
Jetzt bleibt der Aktivierungsbereich wie im Original. Die breitere Darstellung
und das längere Sichtbarbleiben bereits erzeugter Objekte bleiben erhalten.

Geprüft: Skelett erscheint in 4:3 und 16:9 bei Frame 74 an (1120,136),
Bewegung über 161 Frames gleich, 4:3 gegenüber alter EXE unverändert.
Rückwärtslauf erzeugt keine doppelten Gegner; Treppenausgang und Abschnittswechsel
funktionieren. A04-Abgrundkorrektur aus F6 ebenfalls erneut geprüft.
Spielstände, Einstellungen und HD-Paket v9 sind unverändert.
Sicherung: backup\hd-artwork\2026-11-04-Breitbild-Gegner-Spawn.

## A04-Abgrund: kein vorzeitiges A03-Bild mehr (04.11.)

Der Fehler aus F6 ist behoben und in beiden Windows-Spielordnern installiert.
Das Spiel neu starten, damit die neue EXE verwendet wird.
Beim Sturz setzt das Original bereits während Todesphase 12 den Wiederbeginn
auf A03. Der HD-Renderer hält jetzt A04 während dieser Phase und des Ausblendens
fest. Erst beim tatsächlichen Neuladen erscheint A03.
F6 mit Stillhalten und Rechtsbewegung geprüft: ausgehendes A04 pixelgenau,
Neustart in A03 korrekt; native Spielzustände mit/ohne HD identisch.
Grafikpaket bleibt v9. Spielstände, Quellgrafiken und Einstellungen unverändert.
Sicherung: backup\hd-artwork\2026-11-04-A04-Abgrund.

## HD-Mond aus A01 übernommen (04.11.)

Aktiv ist jetzt `hd_packs/stage-01-user-grid-v9` in beiden Windows-Spielordnern.
Das Spiel neu starten. A03, A04 und A05 verwenden den HD-Mond aus A01.
Die Quelle `HD\04_MOND_HD_190x190.png` bleibt unverändert.
Neue gemeinsame 4×-Fassung: Exporte-4x\HD\Gemeinsame-Teile\Mond.png.
Die 20 Pixel transparenten Quellränder wurden entfernt; das sichtbare Motiv
bleibt 15×15 Originalpixel groß, also 60×60 HD-Pixel in einer 64×64-Canvas.
Position, Bewegung und Sichtbarkeit stammen weiterhin vom ursprünglichen
Spielobjekt. Die anderen Grafiken, Spielstände und EXE sind unverändert.
Bildvergleich in allen drei Abschnitten beim Stehen und Gehen bestanden.
Sicherung: backup\hd-artwork\2026-11-04-A01-Mond-v9.

## A03: fehlende Steine und Stufen ergänzt (04.11.)

Aktiv ist jetzt `hd_packs/stage-01-user-grid-v8` in beiden Windows-Spielordnern.
Das Spiel neu starten. Der Import ergänzt auch in A03 die separaten Steine und
Treppen an ihren Originalpositionen: 126 vollständige Steine, 16 Stufen und
16 Teilstücke. A03 war zuvor fälschlich von dieser Platzierung ausgenommen.
Die Wandgrafik und alle Quell-PNGs bleiben erhalten. Spielebene.png allein
ist keine vollständige Vorschau der separat ergänzten Spielblöcke.
Ein zusätzlicher Test prüft die A03-Bauteile und ihre tatsächlichen Bildpixel.
Die übrigen Abschnitte sind gegenüber v7 unverändert. Spieltests bestanden.
Sicherung: backup\hd-artwork\2026-11-04-A03-Steine-v8.

## Exaktes 4×-Raster für A03/A04/A05 (04.11.)

Aktiv ist `hd_packs/stage-01-user-grid-v7` in beiden Windows-Spielordnern.
Zum Laden das Spiel neu starten. Der Grafikmaßstab bleibt 4×.
Die EXE wurde nicht verändert.

Neue bearbeitbare Quellen: `Assets (ausgeschnitten)\Stage 01\Exporte-4x`.
Dort Abschnitt\HD\Spielebene.png und HD\Gemeinsame-Teile verwenden.
Maße der Spielebenen einschließlich beider 16:9-Ränder:
A03: 5464×896, A04: 4440×896, A05: 3416×896 Pixel.
Ursprung: x=-43 Originalpixel, y=0. Je Seite sind 43 Originalpixel bzw.
172 HD-Pixel Rand bereits enthalten. Nicht erneut anfügen.
Stein und Block/Treppen-Anschluss: 64×64; Stufe: 32×32 Pixel.
Der linke Anschluss ist gespiegelt.

Die bisherigen PNGs und PSDs sind unverändert und bleiben im alten Raster.
Ein erneuter Export daraus braucht wieder die registrierte Umrechnung.
Nicht alte und exakte 4×-Dateien ungeprüft mischen. Die PNGs unter Exporte-4x
werden im Import nicht erneut skaliert. raster.json definiert Spielmaße,
Quellauflösung und Ursprung; Details stehen in Exporte-4x\LIES_MICH.txt.
Der Generator tools/hd/prepare_stage01_grid.py verlangt einen neuen Ausgabeordner
und überschreibt nichts. Er registriert bekannte Abschnittsgrenzen.
Bei A03 entfällt eine zusätzliche untere Randzeile außerhalb der Originalhöhe
(175 sichtbare Pixel am linken Rand). Die alte Quelle bleibt vollständig erhalten.
Falsch gezeichnete Details innerhalb eines Motivs werden dadurch nicht korrigiert.

8× ist als Quellformat vorbereitet: ein 16×16-Stein bekommt 128×128 Pixel,
eine 8×8-Stufe 64×64 Pixel. source_scale in raster.json kann für Einzelmotive
8 sein. Der aktuelle Importer verkleinert diese einmal auf den 4×-Pack.
Gemischte echte 8×-Detailausgabe im Landschaftsrenderer ist noch nicht umgesetzt.

Der Bildvergleich aller drei Spielebenen im Spiel ist pixelgenau. Gehen, Angriff,
Tod, Neuladen und Wasseranimation wurden geprüft; Spiellogik unverändert.
A05 beim Gehen und Angreifen: etwa 60,1 FPS ohne Logikwiederholungen im privaten
Test (ohne Ton, CPU-Timing 2).
Sicherung: backup\hd-artwork\2026-11-04-exaktes-4x-raster-v7.

## Wiederholbarer A03-HD-Ablauf

Vorbereitet unter Assets (ausgeschnitten)\Stage 01\A03\ChatGPT-Vorlagen-v1.
Für A03_02 bis A03_05 gibt es jeweils zwei feste PNGs und ausgefüllte Prompts.
Die Quellen2.png bis5.png sind bereits vergrößerte Original-Pixelart in RGBA
mit echter Transparenz. Nicht erneut4× oder10× vergrößern. Zielmaße:
A03_02:1032×903, A03_03:1161×903, A03_04:902×903, A03_05:1032×903.
Das akzeptierte Stilbild1214×935 ist NUR Materialreferenz, keine Geometrievorlage.

1. Im gewählten Ausschnittordner zuerst01_GEOMETRIE.png und danach
   02_STILMASTER.png im ChatGPT-Fenster anhängen. Dann03_AUFTRAG.txt kopieren.
2. Einen normalen HD-Ausschnitt gestalten lassen. Noch keine16:9-Erweiterung.
   Derselbe freigegebene Stilmaster bleibt bei jedem Durchgang Bild2.
3. Ergebnis herunterladen und auf05_PNG_PRUEFEN.cmd ziehen. Das verändert kein
   Bild; es schreibt Pruefbericht.json mit Maßen, RGBA und Alpha-Vergleich.
4. Stil und Bauform gesondert ansehen: alle begehbaren Steine, Positionen,
   Fugen/Deckenfunktion und Übergänge. Technisches PASS ist KEINE Gesamtfreigabe.
   Eine unveränderte äußere Alphamaske beweist keine korrekte innere Steinanzahl.
5. Bei kleinem Fehler04_KORREKTUR.txt verwenden, nur einen Fehler benennen.
   Bei grundsätzlich falschem Design/Geometrie wieder mit Original+Stilmaster
   beginnen. Fehlversuche werden keine neue Stilreferenz. Bleibt das schwierig,
   kleinere feste Bauteile/Materialien bearbeiten und in Originalgeometrie setzen.
6. Erst freigegebene Teile in PhotoCraft gemeinsam bei100% prüfen. Für einen
   direkten Anschluss zusätzlich den freigegebenen Nachbarrand klar als ANSCHLUSS
   vorgeben. Überlappung ist Arbeitskontext und darf nicht doppelt eingebaut werden.
7.16:9-Rand separat mit extension_de.txt bearbeiten, danach ins Spielpaket importieren.

Feste16:9-Basis:43 zusätzliche Originalpixel je Seite,172 bei4× bzw.174 bei
4,03125×.256 sind optionale Reserve;247×992 war nur der konkrete A02-Streifen.
Für A03 keine pauschale Übernahme dieser Maße. Import berücksichtigt weiterhin
registrierte manuelle Korrekturen; alte Overrides vor einem Austausch zuordnen.

Prompts als versionierte Quellen unter assets/hd/prompts. PNG-Prüfer:
tools/hd/check_redesign.py. Erkennt falsche Maße und Alpha, prüft KEINE Stiltreue,
Steinanzahl/-positionen oder konstruktive Anschlüsse. Bei Fehlern nicht das ganze
KI-Bild blind passend strecken oder eine leere Maske als Reparatur darüberlegen.
Die Stilverbindlichkeit ist trotz Referenzen keine Garantie der Bildgenerierung.
OpenAI-Primärquelle: developers.openai.com/cookbook/examples/multimodal/image-gen-models-prompting-guide.
Vorbereitungs-/Prüfbericht: artwork-local/a03-workflow-check-2026-10-29.
Keine neue Bildgenerierung, PSD-Änderung oder Installation bei der Vorbereitung.

## Gemeint ist eine durchgehende Steindecke

Die großen vorspringenden Steine am linken Originalrand sind als massive
Deckenfläche nach links fortzusetzen, einschließlich sichtbarer Unterseite.
Eine zurückliegende Kleinsteinwand an dieser Stelle erzeugt den falschen harten
Abschluss. Aktueller Vorschlag: Entwuerfe\A02-links-v5-Decke-247x992.png,
Anschlussvorschau daneben. Original rechts und unterer Streifen ab Zeile680
unverändert. Noch nicht in PSD oder Spiel eingebaut. Prompt und Bericht:
artwork-local/a02-left-v5-2026-10-28.

## Oberen Steinanschluss nachgebessert

Neueste Variante im A02-Ordner Entwuerfe:
A02-links-v4-Steine-247x992.png, Anschlussvorschau daneben.
Nur der obere Teil des linken Streifens wurde korrigiert. Ab Bildzeile380
sind die Pixel unverändert gegenüber Variante3, ebenso der ganze rechte
Originalausschnitt. Format bleibt247×992. Prompt und Vergleichsbericht:
artwork-local/a02-left-v4-2026-10-28. Noch nicht in PSD oder Spiel eingebaut.

## Linker A02-Anschluss in Originalgröße

Der große Torbogen aus Variante2 wurde verworfen: Simon kommt horizontal von
links, kein neuer frontaler Torbogen. Neue zurückhaltende Variante:
Stage 01\A02\Entwuerfe\A02-links-v3-passend-247x992.png.
Nur diesen Streifen verwenden,1:1 links an den ursprünglichen456×992-Ausschnitt
setzen und die oberen Kanten bündig ausrichten. Nicht zusätzlich skalieren.
Die zugehörige Anschlussvorschau endet auf -Anschluss-703x992.png.

KI-Ausgaben hatten die Originalszene intern verkleinert/verschoben. Deshalb
an449 Bildmerkmalen registriert und den unteren Abschluss aus dem Original
übernommen. Vorschau rechts pixelgenau identisch mit Original, alle992 Pixel
der direkten Anschlusskante gleich. Prüfbericht/Prompt/Arbeitsdateien unter
artwork-local/a02-left-v3-2026-10-28. Noch nicht in PSD oder Spiel eingebaut.

## Überarbeiteter linker A02-Eingang

Der erste Randentwurf passte nicht und hatte zu viel Efeu. Für neue Motive:
wenig Bewuchs, lesbares Steinmauerwerk und passend zum vorherigen Abschnitt.
Neue Variante: offener Burgtordurchgang nach der Zugbrücke. Datei unter
Stage 01\A02\Entwuerfe: A02-Eingang-links-v2-247x992.png; Anschlussvorschau
daneben. Noch nicht in PSD oder Spiel eingesetzt. Alter Entwurf bleibt erhalten.

## Linker A02-Rand statt Spiegelung

Unter Stage 01\A02\Entwuerfe liegt A02-links-247x992.png: ein KI-erstellter
linker Erweiterungsstreifen zu deinem Ausschnitt. Die Anschlussvorschau liegt
daneben. Noch nicht in die PSD oder das Spiel eingebaut.

Im bisherigen festen 16:9-Modus sind es43 zusätzliche Originalpixel pro Seite.
Bei deiner Arbeitsauflösung129/32 entspricht das aufgerundet174 Bildpixeln.
247 reichen dafür;256 Pixel pro Seite sind ein praktisches Arbeitsraster.
Bei breiteren Bildformaten muss der Rand neu aus der sichtbaren Breite berechnet
werden. Allgemein: Zusatzbreite pro Seite in Originalpixeln mal Arbeitsmaßstab.
Prompt und Erzeugungsdaten: artwork-local/a02-left-extension-2026-10-28.

## A02-PSD ist gruppiert

In A02.psd sind jetzt sieben Gruppen angelegt: SZENE_VORNE, GITTER,
SZENE_HINTEN, HINTERGRUND, TUER, GARGOYLE und REFERENZ.
REFERENZ enthält die Originalvorlagen und die leere Hilfsebene und ist
ausgeblendet. Alle 15 bisherigen Ebenen, ihre Positionen und die beiden
eingebetteten Gargoyle-Smartobjekte sind erhalten. Die HD-Darstellung wurde
programmgesteuert pixelgenau vor und nach dem Gruppieren verglichen.

Wenn A02.psd noch in PhotoCraft geöffnet ist, die Datei neu laden, damit die
gespeicherten Gruppen erscheinen. Der automatische Spielpaket-Export ist
weiterhin ein eigener nächster Schritt. Zusätzliche Sicherung und Prüfbericht:
artwork-local/photocraft-grouping-2026-10-28.

## Dein Bildeditor ist PhotoCraft

Du verwendest PhotoCraft, nicht Adobe Photoshop. PSD ist das Dateiformat.
Die bisherigen Photoshop-Generator-Menüs sind deshalb keine geprüfte Anleitung
für deinen Editor. Die getrennten Gruppen für Spielebenen bleiben sinnvoll.

PhotoCraft 0.16.0 ist mit einer eigenen Kommandozeile installiert unter
C:\Program Files\PhotoCraft. Damit wurde A02 erfolgreich ausgelesen:
15 Ebenen, keine Importwarnungen. Die beiden Gargoyle-Korrekturen liegen
in der PSD als eingebettete Smartobjekte mit Namen region_21.png/region_22.png.
Gruppieren, Umbenennen und PNG-Export sind als Befehle vorhanden.

PhotoCraft bietet außerdem MCP und einen Steuerkanal für die laufende Anwendung.
Die Verbindung PSD zum Spielpaket ist noch einzurichten; bisher wurde nur gelesen.
Die Original-PSD wurde dabei nicht verändert. Technische Primärquellen:
https://github.com/storytold/photocraft und dessen docs/control-protocol.md.
Lokale Metadaten: artwork-local/photocraft-research-2026-10-28.

## Kein falsches A02-Bild beim Sterben in A03

Die kurze Einblendung der A02-Landschaft vor dem Neustart von A03 ist behoben.
Das HD-Paket wird beim Ausblenden jetzt dem tatsächlich gezeigten Abschnitt
zugeordnet. Beide Windows-Versionen sind aktualisiert. Spiel vollständig
schließen und neu starten; dein F4-Spielstand bleibt unverändert.

## Wo manuelle A02-Bildkorrekturen hingehören

Dauerhafter Arbeitsordner:
`D:\Super Castlevania IV Recomp\Assets (ausgeschnitten)\Stage 01\A02\HD`

Deine bearbeiteten fertigen Spiel-PNGs sind jetzt zusätzlich gesichert unter
`HD\Manuelle-Korrekturen\Gargoyle-02.png` (bisher region_21.png) und
`HD\Manuelle-Korrekturen\Gargoyle-03.png` (bisher region_22.png).
Diese beiden künftig dort bearbeiten und unter denselben Namen speichern.
Die Leinwand bleibt 152×92 Pixel mit Transparenz; nicht nochmals vergrößern
oder beschneiden. Der Import übernimmt diese Dateien ohne erneute Skalierung
und gibt ihnen Vorrang vor den ursprünglichen Gargoyle-Exporten.

Neue Photoshop-Exporte anderer Teile kommen weiterhin direkt in den HD-Ordner
unter ihren bekannten Namen (z.B. Gitter.png). Der Korrektur-Unterordner ist
für bereits fertig registrierte Spielgrafiken gedacht. Bei anderen region_XX-
Dateien zuerst die Zuordnung festhalten lassen; deren Nummer kann sich ändern.

Die jetzigen beiden Änderungen sind bereits auch im aktiven v4-Paket enthalten.
Ein Paketneubau berücksichtigt sie nun automatisch. Hinweise auf manuelle
Korrekturen samt Quelle und Prüfsumme stehen im erzeugten import.json.

## Gitterabschluss und Gargoyle in A02

Die Gitter-PNG enthält bereits den Grasabschluss. Der Renderer hat ihn bisher
unten abgeschnitten. Das ist korrigiert; du musst die Stangen nicht verlängern.
Die drei Gesichtsgrafiken des Gargoyles sitzen drei Originalpixel weiter rechts
und einen höher, damit die Augen zwischen den Stangen sichtbar werden.

Beide Windows-Spielordner verwenden das neue Paket
`stage-01-user-a02-v4-placement`, weiterhin mit 4×. Spiel einmal vollständig
schließen und neu starten. Deine ursprünglichen PNGs bleiben erhalten.

## A02 läuft mit der passenden HD-Auflösung

Die Windows-Version verwendet jetzt **4×** für deine 4×-Bilder. Vorher wurde
unnötig mit 10× gerechnet; das HD-Menü hatte diesen alten Wert sogar automatisch
wieder eingestellt. Das ist behoben, auch im A02-Installer.

Unter **Escape → HD graphics → HD render resolution** bleibt deine Auswahl
jetzt gespeichert. Für deine aktuellen Bilder **4×** verwenden, auch auf dem
4K-Bildschirm. Die Größe der Figuren, Ebenen und Landschaft bleibt gleich.

Beide Windows-Spielordner sind aktualisiert. Das Spiel vollständig schließen
und neu starten. Im A02-Test mit Vollbild, Ton, Laufen und Angreifen wurden
60,08 FPS ohne ausgelassene Spiellogik-Updates gemessen. Deine PNGs bleiben
unverändert; die Werkstatt und das pausierte Simon-Projekt sind unverändert.

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

## HD-Vorlagen: Englisch und Hintergrund ohne Serienbloecke

Aktuell: `Assets (ausgeschnitten)\Stage 01\A03\ChatGPT-Vorlagen-v2-Englisch-ohne-Bloecke`.
Die englischen Vorlagen liegen im Projekt unter `assets/hd/prompts/*_en.txt`.
Nur die im Beispiel bezeichneten wiederholten quadratischen Schmuck-/Spielbloecke
entfallen. Dahinter wird passender Hintergrund deckend rekonstruiert. Andere
Mauersteine, Saeulen, Decken und Architektur bleiben erhalten. Diese Ausnahme hat
Vorrang vor der alten Forderung, alle Spielsteine zu erhalten. Der Nutzer baut
die entfernten Bloecke spaeter selbst ein. Die deutsche v1 bleibt nur Archiv.
Der alte pixelgenaue Alpha-Vergleich prueft diese Ausnahme nicht angemessen:
Transparenz innerhalb entfernter Bloecke darf zugunsten deckenden Hintergrunds
entfallen. Fuer eine strenge Pruefung ist eine explizite Entfernungsmaske noetig;
die Qualitaet der Hintergrundrekonstruktion muss separat beurteilt werden.

## A03: alle fuenf Abschnitte ohne HD-Stilvorlage

Aktuell: `Assets (ausgeschnitten)\Stage 01\A03\ChatGPT-Workflow-v3-Alle-5-ohne-HD-Vorlage`.
Vollstaendiger englischer Auftrag im Projekt: `assets/hd/prompts/a03_autonomous_en.txt`.
Alle fuenf Originale sind dabei reine Geometrievorlagen, keine HD-Stilreferenz.
Masse 01/02/03/04/05: 1032/1032/1161/902/1032 mal jeweils 903 Pixel.
Die KI bearbeitet die ganze Serie ohne Zwischenfreigaben. Matte, ruhige Steinflächen
mit wenigen lokalen Schaeden statt koerniger, glaenzender Flaechentextur. Nur die
bezeichneten quadratischen Serienbloecke entfernen, dahinter deckenden lokalen
Hintergrund rekonstruieren. Keine pauschale Entfernung quadratischer Mauersteine.
Exakte Geometrie und passende Rekonstruktion sind durch einen Prompt nicht garantiert.
Quellkopien hashgeprueft; keine PSD, Quelldatei oder Spielinstallation geaendert.

## A03: duestere gotische Materialwirkung statt Spielzeugoptik

Aktuell ist `Assets (ausgeschnitten)\Stage 01\A03\ChatGPT-Workflow-v4-Duester-Gotisch`.
Die helle orangefarbene, glatte und rund abgeschraegte V3-Ausgabe ist abgelehnt.
Vollauftrag: `assets/hd/prompts/a03_autonomous_en.txt`; kurze Korrektur fuer den
bestehenden Bild-Chat: `assets/hd/prompts/a03_gothic_correction_en.txt`.
Ziel sind schwere verwitterte gotische Mauern, entsaettigtes Braun/Grau und kuehle
tiefe Schatten. Natuerliche lokale Rauheit ja, flaechiges Koerner-/Glitzermuster nein.
Keine Spielzeug-Bevels oder Cartoonoptik; nur Abdunkeln ist keine Materialkorrektur.
Alle fuenf Originale bleiben Geometrievorgabe ohne HD-Stilvorlage. Masse,
Blockentfernung und deckende Hintergrundrekonstruktion gelten unveraendert.
Vorlagenpaket kopiert und Quellen hashgeprueft; keine Bilder neu generiert.

## A03: Originalfarben statt graubrauner Entsaettigung

Aktuell: `Assets (ausgeschnitten)\Stage 01\A03\ChatGPT-Workflow-v5-Originalfarben`.
Auch der graubraune V4-Look ist vom Nutzer abgelehnt. Originale bestimmen jetzt
explizit Geometrie UND lokale Materialfarben. A03-Mauerwerk bleibt deutlich
roetlich-braun; grauer Besatz muss unterscheidbar sein. Düsternis durch lokale
Schatten, Tiefe und Verwitterung statt pauschaler Entsaettigung/kaltem Farbfilter.
Die Cartoon-/Spielzeugoptik aus V3 bleibt ebenfalls abgelehnt.
`assets/hd/prompts/source_colour_correction_en.txt` korrigiert den laufenden
Bild-Chat: A03 vor A04/A05 ueberpruefen, abgelehnte Bilder nicht weitertragen;
A04/A05 behalten ihre eigenen Originalfarben. Vollauftrag und gotische Korrektur
im Projekt ebenfalls angepasst. Nur Prompt-/Vorlagenpflege, keine Bildgenerierung.

## A03-Hintergrund: drei getrennte HD-Dateien (02.11.)

Vorlagen und Anleitung: `Assets (ausgeschnitten)\Stage 01\A03\Hintergrund-Vorlagen-2026-11-02`.
Exports spaeter nach `A03\HD\Hintergrund`: Himmel-Berge.png 1081x391, Wald.png
2451x383 und Mond.png 60x61. Bereits Arbeitsaufloesung, nicht erneut vergroessern
oder automatisch zuschneiden. Himmel/Wald geliefert voll deckend; Schwarz nicht
pauschal entfernen. Mond mit echter Alphatransparenz und ohne eingemalten Himmel.
F3/save2 vom 02.11. in privater Laufzeit als A03/Block2 bestaetigt. Zwei BG2-
Scrollbaender: nach 90 Rechts-Frames h10 bis Zeile94 und h20 ab95, BG1 h50.
Mond durch vier farbkanonisierte Quellfarben auf OBJ identifiziert:71 sichtbare
Pixel, Bounds[56,48,71,63], OAMslot11/Tile170/Attr46,16x16. In beiden Stichproben
ortsfest. Audit: `artwork-local/a03-background-audit-2026-11-02/audit.json`.
Nur Vorbereitung, keine HD-Registrierung/Spielinstallation. F3-SHA nach Pruefung
unveraendert. Keine weiteren Bilder im Bildbetrachter geoeffnet.

## A04-Wasser: native Farbanimation, getrennte Wasserzeichnung (02.11.)

F4/save3 vom 02.11. 22:50 in privater Laufzeit bestaetigt: Block3, Kamera375.
Audit `artwork-local/a04-water-audit-2026-11-02/audit.json`: sieben Stichproben
Frame1/2/5/9/17/33/65, Wasser-VRAM unveraendert, CGRAM99/100/101 zyklisch
mit drei Permutationen. Betroffen1476 BG2-Pixel, Bounds[2,136,242,157]. Andere
VRAM-Aenderungen ab33 nur HUD bei0xb000. Keine zeitabhaengige Wellenverschiebung
in den Stichproben; feste Scrollbaender BG2 h75/150/300 ab Zeilen0/127/159.
Artist-Anleitung `Assets (ausgeschnitten)\Stage 01\A04\WASSER_HD_EXPORT.txt`.
Wasser und Ufer/Fernwald getrennte Gruppen/PNGs, identische Leinwand des
bisherigen Wasser-Ufer-Ausschnitts, Motivpositionen erhalten, aussen transparent.
Statische HD-Gestaltung reicht als Grundlage; keine manuelle Animationsserie.
HD-Farb-/Reflexanimation muss erst beim Import implementiert werden, nicht
automatisch durch den PNG-Export vorhanden. Spielersave SHA unveraendert.

## A05 verwendet A03-Hintergrundgrafik (02.11.)

F5/save4 vom02.11.22:54 in privater Laufzeit als A05/Block4 bestaetigt.
Audit `artwork-local/a05-background-audit-2026-11-02/audit.json`: komplette
BG2-Karte4096/4096 Eintraege mit A03 identisch, ebenso dekodierte Pixel und
Paletten; Mond16x16-Kacheln+Palette identisch, OAM auf Tile170/Attr46 bestaetigt.
HD-Himmel/Berge,Wald,Mond gemeinsam aus A03 verwenden, keine neuen A05-Exporte
der Motive noetig. A05-Scrollversatz anders: nach91 Frames Kamera152, oberer
BG2-Bereich h16, unterer h33. Gleiche Bandgrenze95 wie A03. Registrierung beim
Einbau separat; A05-Vordergrund bleibt eigenstaendig. Artist-Notiz in
`Assets (ausgeschnitten)\Stage 01\A05\HINTERGRUND_AUS_A03.txt`. F5 SHA unveraendert.

## Gemeinsamer HD-Hintergrund-Workflow A03/A04 (02.11.)

Paket: `Assets (ausgeschnitten)\Stage 01\Hintergrund-HD-Workflow-2026-11-02`.
Vollstaendiger englischer Prompt: `assets/hd/prompts/backgrounds_stage01_en.txt`.
ZIP mit17 unveraenderten Quell-PNGs in A03/A04-Unterordnern, SHA-geprueft inkl.
ZIP-Readback. Lokale Pfade allein sind fuer den Bild-Chat kein Dateiupload.
Ziel: echte neue Detailzeichnung statt nur Upscaling, Originalfarben und
duestere Nachtstimmung erhalten, Hintergrundkontrast nach Tiefe abgestuft.
Keine generische graue Entsaettigung, Cartoonformen oder Koerner-/Glitzermuster.
A03-Wald612+613+613+613=2451x383 ergibt pixelgleich den bisherigen Gesamtstreifen.
Weitere Gruppenbreiten: A04-Wald1681x254, Wasser/Ufer2048x133, Fernwald2048x65,
Himmel/Berge1315x451. A03-Himmel1081x391. Mond aktuell in BEIDEN Quellordnern
identisch60x60, ersetzt fruehere60x61-Vorlage. Einmal gestalten, gleich wiederverwenden.
RGB-Streifen bleiben deckend; Mond-Alpha erhalten.17 primaere RGBA-Outputs plus
bei verfuegbaren Dateiwerkzeugen zusaetzliche Wasser-/Ufertrennung fuer drei
A04-Wasserstuecke. Diese muessen jeweils dasselbe komplette Bild rekonstruieren.
Keine Laufzeit-Animation oder HD-Installation in diesem Auftrag implementiert.

## A03, A04 und A05 jetzt im Windows-Spiel in HD (03.11.)

Das neue Paket `stage-01-user-a03-a05-v5` ist in beiden Spielordnern installiert
und mit HD an / Aufloesung4 ausgewaehlt. Spiel neu starten, dann F3=A03,
F4=A04 und F5=A05 laden. Himmel, Wald, Mond, Mauern, Steine, Treppen und
die vorhandenen 16:9-Raender sind eingebunden. A05 nutzt die A03-Hintergruende.
A04-Wasser wechselt mit den Originalfarbenphasen; Ufer und Wald bleiben ruhig.
Die neuen Hintergrund-PNGs stammen aus `Stage01_A03_A04_HD.zip`. A03-Handarbeit
aus der PSD und A04-Steine/Treppen wurden beruecksichtigt. Die grosse A04-
PSD-Ebene war noch Originalgrafik; stattdessen sind die fertigen HD-Wandteile
mit den handgesetzten Steinen kombiniert. A05-Steine und Stufen verwenden
dieselben vorhandenen HD-Motive und ihre Positionen aus der Originalkarte.

Geprueft: Gehen/Angriff/Stillstand, Laden sowie Tod/Neustart in allen drei
Abschnitten. Spiellogik, Originalbild und Speicher mit HD an/aus identisch.
Wasser nach Neuladen identisch. Zeichnungsoptimierung pixelgleich geprueft.
Bildrate beim Gehen+Angreifen: A03/A04 etwa60FPS, A05 zuletzt59,5FPS im
privaten Test. Ton konnte mangels Audiogeraet hier nicht mitgemessen werden.
Eine vollstaendige Durchspielpruefung aller Levelwege ist damit nicht gemeint.

Originale, PSDs, Spielersaves, Tasten und sonstige Einstellungen erhalten.
Altes Paket bleibt vorhanden. Zusaetzliche Sicherung mit vorheriger Auswahl,
EXEs, altem und neuem Paket sowie verwendeten Quellen liegt unter:
`D:\Super Castlevania IV Recomp\backup\hd-artwork\2026-11-03-A03-A04-A05-installation`.

## Saubere Spielebenen und automatische Einzelmotive (04.11.)

Aktiv ist jetzt `stage-01-user-clean-planes-v6` in beiden Windows-Spielordnern.
Spiel neu starten; F3=A03, F4=A04, F5=A05. Die fehlerhafte Wandkachel-Ersetzung
aus v5 ist entfernt. A03 kommt als zusammenhaengendes Bild direkt aus deiner
`A03\HD\Spielebene.png`; dort werden keine Bloecke oder Wandstuecke ersetzt.
A04/A05 benutzen ebenfalls ihre vollstaendigen `HD\Spielebene.png`. Nur die
Originalpositionen der Spielbloecke, Einzelstufen und Anschluesse werden mit
deinen Dateien aus `Stage 01\HD\Gemeinsame-Teile` ergaenzt. Stein-01.png ist
der normale Block. Beide Block-Treppe-Dateien waren gleich: beim Import wird
die Gegenrichtung wie besprochen gespiegelt, deine Dateien bleiben unveraendert.
Die 16:9-Erweiterungen sind schon in den Spielebenen und werden nicht angehaengt.
Die aktuellen zugeschnittenen PNG-Leinwaende und Positionen bitte beibehalten.

Geprueft: A03 im Spiel exakt wie der angepasste PNG-Export; A04/A05 ausserhalb
der eingesetzten Motive pixelgleich. Alle drei kompletten Vordergrundbilder
sind im Spiel gegen die vorbereiteten Bilder verglichen. Gehen, Angriff, Tod,
Neuladen und Wasseranimation funktionieren; Logik/Kollision unveraendert.
A05 mit Gehen+Angriff etwa60FPS im Test ohne Ton.
Sicherung: `D:\Super Castlevania IV Recomp\backup\hd-artwork\2026-11-04-saubere-Spielebenen-v6`.

## Stage-01-Arbeitsordner aufgeraeumt (04.11.)

Uebersicht: `Assets (ausgeschnitten)\Stage 01\ORDNUNG.txt`. Die aktuellen
Spielebenen unter A03/A04/A05\HD und HD\Gemeinsame-Teile bleiben an denselben
Pfaden. Die fertigen Hintergrund-PNGs liegen jetzt unter A03 bzw. A04\HD\Hintergrund.
Originalzuschnitte liegen unter Abschnitt\Original\Ausschnitte und
Original\Hintergrund. Einzelne fertige HD-Wandteile unter HD\Bauteile. Separate
Randgrafiken unter HD\16x9. Weitere A03-Motive liegen unter Einzelteile; die
Steine-/Treppen-PSDs unter A03\Projekte. Beide unterschiedlichen Gesamt-PSDs
liegen unter Projekte\Gesamt. Das fertige Hintergrund-ZIP liegt unter Lieferungen.

473 alte Dateien (rund350MiB) liegen in `Aussortiert_2026-11-04`: KI-Zwischenstaende,
verworfene Entwuerfe, alte Anleitungen und Dubletten. Nichts geloescht. Alle622
urspruenglichen Dateien sind mit unveraendertem SHA256 erhalten. Verschiebungen.csv
und Verschiebungen.json zeigen die alten/neuen Positionen samt Grund.
RUECKGAENGIG.cmd dort stellt die frueheren Positionen wieder her; geaenderte
Dateien oder Namenskonflikte werden vor dem Verschieben erkannt.
Spielinstallation, Spielstaende und alle aktuellen Importdateien sind unveraendert.

## Level-Editor: Monsterwerte, Kerzen und Boss-Begegnungen (04.11.2026)

- Editor neu über `Level_Editor_starten.cmd` starten. Im Originalkatalog zuerst „Als eigene Kopie bearbeiten“, dann das eigene Projekt speichern.
- Beschriftungen sind standardmäßig an. „Auswahl“ zum Ziehen; Pfeile verschieben um 1 Pixel, Umschalt + Pfeile um 8. Strg+C/Strg+V kopiert auch Namen und eigene Werte, danach in die Karte klicken.
- „Werte / KI / Boss-Einstellungen“ zeigt Normal und New Game+ separat. Eigene HP, Kontaktschaden und Trefferbereich gelten pro Exemplar im F5-Spieltest. Leeres Feld = Original-Startwert. Noch nicht gemessene NG+-Bosswerte bleiben ausdrücklich unbekannt.
- Kerzen: Objekte / O-000E. Variante ist das native Inhaltsbyte in Dezimal. Originalimporte übernehmen jetzt auch Kerzen und Szenenobjekte. Nicht erfasste Vorschaubilder werden gekennzeichnet.
- Alle 14 Boss-Codes M-0080..M-008D sind platzierbar. `direct` = vorbereiteter Kampf, `sequence` = früher Bossablauf; vollständige originale Kamerasequenzen sind damit nicht automatisch enthalten.
- Ein Boss ist eine einzelne Begegnung mit festem Ausschnitt. Andere Gegner und dynamische Objekte pausieren und kehren danach zurück. `continue` = im Raum bleiben; `exit` = erster Raumausgang. Spielertod/Sturz startet am eigenen Startpunkt.
- Native Bewegungsgrenzen, besondere Bossphasen und Abhängigkeiten mancher Szenenobjekte bleiben bestehen. Das ist noch kein freier Baukasten für sämtliche Original-Levelskripte.
- Keine neuen HD-Bilder nötig; Original-/Künstlerdateien bleiben unverändert. Details: `docs/LEVEL_EDITOR.md`.

## Level-Editor: Hinzufügen und Ziehen / neue Oberfläche (04.11.2026)

- Editor neu starten. Rechts **Gegner** oder **Objekte** öffnen, ein Bild wählen und **＋ Hinzufügen** drücken. Die Figur erscheint in der sichtbaren Kartenmitte und ist direkt ausgewählt. Alternativ das Bild in die Karte ziehen.
- **Mit Maus platzieren** zeigt die Figur als Vorschau am Zeiger. Ein Klick setzt sie; danach ist wieder **Auswählen & ziehen** aktiv. Umschalt = mehrfach setzen, Esc = abbrechen.
- Figuren direkt mit der linken Maustaste greifen und ziehen, auch aus einem Platzierungsmodus. Kleine Fledermäuse werden jetzt ohne vorherige 8px-Rundung getroffen.
- Beim ersten Ziehen oder Hinzufügen in einer Originalvorlage entsteht automatisch eine eigene Kopie. Bereits vorhandene eigene Räume und ungespeicherte Arbeit bleiben dabei erhalten.
- Links stehen nur die passenden Eigenschaften der Auswahl; Werte/KI per Schaltfläche oder Doppelklick. Gelände liegt getrennt unter **Gelände**. Die größere dunkle Oberfläche ist auch für 4K ausgelegt.
- F5 testet den gerade geöffneten eigenen Raum, ohne den gespeicherten Startraum zu ändern.

## 2026-11-04 – Gemeinsames Castlevania Studio
- Level-Editor und vollständige Monster-Werkstatt sind eine Anwendung mit den Bereichen „Level & Räume“ und „Monster & Animationen“. `Gegner_Werkstatt_starten.cmd` startet `level_editor.py --monsters`, der normale Levelstarter öffnet weiterhin den Originalkatalog.
- Map-Figur → Animationen & HD öffnet Code/Variante; „Werte der Level-Figur“ bearbeitet instanzbezogene Levelwerte. Neutraler Testraum zeigt Original-/NG+-Werte. Namen werden sofort in Karte/Bibliothek übernommen. „Im Level hinzufügen“ setzt die gewählte Variante in die sichtbare Karte.
- Bestehende Künstler-Werkstatt/PNG-Dateinamen bleiben erhalten. Karten-/Projektformat unverändert. Levelkarte und F5-Leveltest bleiben Originalgrafik; das HD-Livepreview sitzt in der eingebauten Werkstatt.
- Werkstatt wird erst beim Öffnen geladen, Arena pausiert im Hintergrund; eigener Leveltest wird beim Wechsel beendet. Hauptfenster speichert/schließt seine eigenen Prozesse. Strg+Z/Y im Monsterbereich verändert die verdeckte Karte nicht.
- Nativ geprüft: Knochenangriff, NG+, zusätzliche Bosse 82/8D, echte Hintergrundpause und Prozessende; GUI 1280×900 und 4K ohne Bildbetrachter. Artist-Metadaten werden im Test nur privat kopiert. Vollständige Boss-Phasen bleiben nicht durchgängig geprüft.

## Leveltest – getrennte Gegnerressourcen und stabile Bosskulisse
- Die frühere globale 11-Seiten-OBJ-/Palettenplanung ist im Leveltest ersetzt: Levelgrafik immer als eigener RGB555-Atlas; pro Monster/Variante eigene Original-VRAM-/Farbkontexte und Host-Sprite-Pixel. Keine fremden OBJ-Uploads über Levelkacheln, keine Ablehnung gemischter Familien wegen gemeinsamer Grafikseiten. Native OAM-Emission, Priorität und Blinkregeln bleiben maßgeblich.
- Bis 4096 Platzierungen pro Raum; native KI weiterhin maximal 37 aktive Slots inkl. Geschossen/Hilfsteilen. Nahe Platzierungen zuerst; entfernte lebende Gegner vor dem nativen Offscreen-Destruktor auslagern und mit Zustand/HP fortsetzen. Kerzen benutzen kleine Slot-indizierte Persistenzplätze statt Projektindex*2; sonst würden Einträge ab128 fremden RAM überschreiben.
- Szenen-Familie2 ist kein gewöhnlicher Gegner-ABI: eigene Levelkopien zeigen vorhandene Bilder als Kulisse, führen die ursprünglichen Kameras/Grafikwechsel/Skripte nicht aus. Fehlende Aufnahmen bleiben als solche ausgewiesen. Original-F5 läuft unverändert nativ. Diese Einschränkung offen benennen.
- Boss-Y der Originaleinträge ist oft die Controllerhöhe. Kampfboden auf eigene Kollisionsfläche ausrichten; Vorschau/Rahmen gleich. Mode7-Körper im eigenen Level komponieren; HUD-Schrift/Farben und oberste32Rasterzeilen separat halten. Keine Zusage freier Mehrfachboss-KI: weiterhin eine Begegnung, andere dynamische Figuren pausieren.
- Spieltestpaket bleibt CV4LVL4 mit validiertem CV4VOBJ1-Anhang (Posebank + eigene Kontexte); alte Formate bleiben lesbar. Diagnosekommando level_status zeigt eigene Kamera, Platzierungen, Kontexte und aktive native Slots. Nach Codeänderungen Editor und privaten F5-Test neu starten. Installierte Spiel-EXEs/HD-Packs bleiben unberührt; build-lua ist neu gebaut.

## 2026-11-06 - Leveltest: sichtbarer Start und bewegliche Fremdgegener
- Nutzer-Marker in play-wej1r2ui zeigen zwei verschiedene Phasen: erster Marker vor Ende der nativen Vorbereitung, zweiter nach Projektladung. F5 bleibt jetzt bis zum fertig gezeichneten Projekt verdeckt; erst der Editor zeigt das Fenster. Normales Spiel/Artist-Dateien bleiben unveraendert. Editor einmal vollstaendig neu starten.
- Konkreter weiterer Grafikfehler reproduziert: M-0009 schreibt OAM vor seiner Positionsaktualisierung. Selbst 1px RAM/OAM-Abstand liess die virtuelle Originaltextur ausfallen und native fremde CHR durch. Zuordnung prueft jetzt vollstaendige emittierte Teile, eindeutige nahe Position und vorherigen Zustand; kein Erfinden unsichtbarer Posen.
- Eigenes Spielfeld komponiert nur Projektatlas, echte OBJ und gegebenenfalls Mode7-Bosskoerper. Native BG3/HUD-Reste duerfen unterhalb des HUD nichts verdecken. Eigene Levels nutzen den benoetigten Renderer auch bei NewRenderer=0, ohne die Konfiguration zu aendern. Marker enthalten editor_level und Rendererdiagnose.
- PASS neuer test_level_playtest_render.py: Nutzer-Gegnerkombination, verdeckter Start, beweglicher M-0009 (vorher0/nachher124 Originalpixel), Laufen/Peitsche/Kontaktschaden/fortlaufender Test; ueber590000 Hintergrund-/Luftpixel exakt; absichtlich verunreinigte BG3-Karte und Referenzrenderer-Konfiguration. Auch mit normalem Tempo und Ton bestanden. Isolationstest jetzt14 statt9 gleichzeitige Typen pixelgenau. Boss-/Editorpruefungen bestanden, keine Aussage zu vollstaendig durchgespielten Bosskaempfen.
