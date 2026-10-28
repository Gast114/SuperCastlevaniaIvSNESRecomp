# Arbeitsstand & Übergabe (2026-10-23, lokale KI-Spritekorrektur)

**Dauerhafte Nutzerpräferenz:** Vergessbare Bedienhinweise immer in MERKHILFE.md
in einfacher Sprache ergänzen. Nur notwendige gezielte Prüfungen, keine
unnötigen KI-Testreihen oder Skalenmatrix. Fertige Änderungen nach dev pushen.

## Dauerhafte manuelle A02-Korrekturen (28.10.)

Nutzer hatte region_21/22 im alten Player-v3-Paket manuell verändert und fragt
nach dauerhaftem Ablageort. Beide Dateien waren bereits hashgleich mit dem
aktiven v4-Player-Paket, aber ungleich dem ursprünglichen Audit-Build. Außerdem
sind aktuelle Originalexporte Gargoyle-02/03 inzwischen149×88. Keine Dateien
zurücksetzen, Originalexporte und Nutzeränderungen erhalten.

Bearbeitete Spiel-PNGs verlustfrei kopiert nach
D:\Super Castlevania IV Recomp\Assets (ausgeschnitten)\Stage 01\A02\HD\Manuelle-Korrekturen
als Gargoyle-02.png und Gargoyle-03.png (je152×92 RGBA). Zusätzliche Sicherung
und preserved.json unter artwork-local/a02-manual-2026-10-28. Keine Bilder
geöffnet. Spielerinstallationen nicht verändert, da beide Änderungen dort sind.

Importrezept registered_overrides nennt Verzeichnis und Dichte4. build_a02_pack
übernimmt optionale gleichnamige RGBA-Korrekturen NACH Registrierung/Einpassung,
VOR Ausgabe. Prüft exakte Leinwandgröße und Dichte; keine zweite Skalierung,
Padding oder Positionskorrektur. Unterstützt Ebenen, Türphasen und Gargoyle-
Phasen unter stabilen Quelldateinamen statt wandelbarer region_XX-Nummern.
Aufgeteilte Ebenenteile nicht ungeprüft als vollständige Ebene ablegen.
Normale neue Photoshop-Exporte weiterhin unter HD direkt. Eine vorhandene
manuelle Korrektur hat Vorrang; für Rückkehr zum Original sie aus diesem
Unterordner nehmen. import.json protokolliert kind=registered-manual-correction,
replaces, Pfad, Maße und SHA. Installer sichert Korrekturen separat unter
source-pngs/Manuelle-Korrekturen, sodass gleichnamige Originale erhalten bleiben.

Gezielter Neubau artwork-local/a02-manual-2026-10-28/rebuild-check bestanden:
beide RGBA-Bilder pixelgenau wie Nutzerdateien, komplette Regionsmetadaten
identisch mit aktivem v4, 13 Quellenhashes einschließlich zwei Korrekturen
geprüft. Bericht check.json daneben. Kein Runtime-/Performance-Eingriff und
kein neues Paket installiert. Fremde offene Änderungen weiter erhalten.

## A02: Grasabschluss und sichtbare Gargoyle-Augen (27.10.)

Nutzer zeigte drei eigene Bilder: schwebende Stangen im Spiel, Gargoyle mit
verdeckten Augen und Photoshop-Grasabschluss. Keine weiteren Bilder geöffnet.
Die Gitter-PNG enthält das Gras bereits: opake Bildpunkte bis etwa Welt-y=202,
Region bis y=213. RegionAt und Overlay-Vorauswahl schnitten vorher fest bei
Welt-y=193 ab. Für a02_kind=1 gilt jetzt die registrierte untere Regionskante
r.y+r.h; die native Türgrenze bleibt 193. Einfahrbewegung weiterhin gemessen
vom nativen Zaun, keine Skalierung/Ankeränderung der Gittergrafik.

Die drei Gargoyle-PNGs sind Gesicht/Leuchtphasen, kein separat beweglicher
vollständiger Körper. Importrezept hat offset_native=[3,-1], nach bestehender
Registrierung angewendet. Alle drei Phasen gemeinsam verschoben. Nativer
phase_probe=[1551,104] unverändert; sonst würde die native Blinkphase am neuen
Grafikort statt an der originalen Statue gelesen. Keine Pixelbearbeitung und
keine Änderung der Original-PNGs. Neues Paket stage-01-user-a02-v4-placement
im Audit neu aus allen elf unveränderten Quellen gebaut.

Gezielter Vorher/Nachher-Test tools/test_a02_footing.py, Bericht
build-lua/a02-footing-3cjq_tam/report.json: F2 0/40/80/120/160, F3 mit Up
0/40/80/120/160, Endkamera1792 (synthetische Relokation), beide Leuchtphasen
gezielt durch echten Renderer erzwungen. Alle nativen Bilder und vollständigen
WRAM-Dumps identisch. Neu gezeichnete Abschluss-Pixel im y193..213-Band:
F2-160:335, F3-0:5497, Ende:3180 bei 4× und Widescreen. Rote/grüne Augen
17/17 geprüfte Punkte sichtbar, vorher4/17 und5/17. Quelle des Vorher-Builds:
artwork-local/a02-visual-fix-2026-10-27/before-lua (archivierte Lua-EXE aus
vorherigem Performance-Test); Test akzeptiert --before-build ausdrücklich.
Kein Bildviewer benutzt. Keine neue breite Performance-Testreihe, HD bleibt4×.

Release und Lua-Release gebaut. Neues Paket und Release in beiden Windows-
Spielordnern installiert, 4× beibehalten. Quellen per SHA geprüft, Saves,
Steuerung/Config/CPU-Timing/Charakterdaten unverändert. Installationsbeleg und
Backups unter artwork-local/a02-visual-fix-2026-10-27/install-backup; EXEs
zusätzlich eine Ebene darüber vor Release-Build gesichert. Kein Spielerprozess
beendet, Neustart nötig. Altes v3-Paket weiterhin vorhanden. Kein Web-Deployment.
Fremde Browser-/Landschaftsänderungen und deren Doku nicht mitcommitten.

## A02-Performance und veraltete 10×-Vorgabe korrigiert (27.10.)

Nutzer meldete etwa 30 FPS bei Bewegung/Kampf in A02 und stellte klar:
aktuelle Bilder sind 4×, nicht mehr 10×. Beide Windows-Spielprofile hatten
trotzdem scale=10. HdPanel erzwang beim Öffnen sogar wieder 10×; der A02-
Installer setzte ebenfalls immer 10×. Nun Standard 4×, explizite gespeicherte
Auswahl 2/4/6/10 im Menü ohne Seiteneffekt beim Öffnen. A02-Installer nimmt
art_scale aus dem Importbeleg (auch bei alten Belegen mit presentation_scale=10),
neue Belege verwenden die tatsächliche art_scale als presentation_scale.
Keine Änderung an PNGs, Registrierung, Ebenengrößen oder Spieltempo.

Renderer: leere Tile-Pakete überspringen unnötige Schlüsselberechnung.
StoreScenePixel vergleicht/kopiert nur geordnete sichtbare Kandidaten; bei
sicher opakem Gewinner nur diesen. Unbenutzte zwölf Sampling-Datensätze
werden nicht mehr bei jeder Bewegung vollständig kopiert. Sortierung,
Alpha, native Priorität, Farbmathematik und Cache-Invalidierung bleiben.

Messungen auf Nutzer-PC, private Lua-Instanzen, keine Bildansicht:
- benchmark_hd_a02.py: alter 10×-Lauf a02-perf-before-beux8xvj (240 Frames
  je Fall) beim Laufen 27,88 ms / 35,86 ungedrosselte FPS, Angriff 18,91 ms.
  Das sind Rechenreserve-Messungen, nicht die normale Spielgeschwindigkeit.
- Vorher 4×: a02-perf-before4-pa0oht75. Nachher 4×:
  a02-perf-compact4-r6c3m5o6; HD-/native RGB-Hashes und vollständiges WRAM
  für Stehen, Laufen, Angriff und F2-Eintritt exakt gleich. Laufzeiten schwanken
  mit Systemlast; keine isolierte Prozentzusage für den kleineren Cache-Fix.
- profile_sciv_fps.py jetzt optional --player-config. fps-profile-l4q6swnr:
  echte Spieler-Graphics-Einstellungen (Fullscreen=1, Widescreen=1, VSync=0),
  Audio an, 4×, Right+Y, F3, CPU-Timing 2, normale Taktung, 360 Frames,
  letzte 300 ausgewertet: 60,0756 FPS, 299/299 Logikupdates, null Wiederholungen.
  Gast 3,22 ms, Raster/HD 8,31 ms, Upload/Present 0,38 ms im Mittel.
  Kein Anspruch auf 60 FPS in allen ungetesteten Räumen/auf anderen Geräten.
- test_hd_reuse.py: hd-reuse-ygrt_iy3, 175 HD-Checksums/native Bilder/
  benannte Zustände identisch mit und ohne Wiederverwendung. Brückenfixture,
  A02 F3 für Angriff und F2 für Einfahranimation (kein echter Todestest),
  Skalen-/Ebenenwechsel, Laden, HD-Toggle und Paket-Reload.
- test_hd_hud_background.py: hud-background-k7xgviip bestanden, auch A02-HUD.
- test_hd_ui.py: Release hd-ui-check-50benvus, echter ImGui-Klick, zwei Starts,
  Auswahl bleibt 4×, Marker 1368×896 bei nativer Breite 342. Kein Bildviewer.

Release und Lua-Release gebaut. Installiert in build und build-play/game,
jeweils hd_settings.json scale=4. EXE SHA256:
94646301e1f186b557378e706eba2de4ab9a64f7300bfdbb005b31601f564972.
Backup und Installationsbeleg unter artwork-local/a02-performance-2026-10-27.
Spielstände, Config/Steuerung/CPU-Timing, Paketauswahl, Original-Simon und alle
Dateien des aktiven HD-Pakets hashgleich. Keine Spielerprozesse beendet.
Neustart erforderlich. Alte Player-EXE zusätzlich als .a02-perf-before-20261027.exe.

Offene Browserarbeit nicht mitcommitten/deployen: In der bereits untracked
web/prepare_sources.py nur die jetzt überflüssige HD-Menü-Textersetzung entfernt;
Vorversion im Audit gesichert. Quelladapter läuft erfolgreich nach
build-audit/a02-browser-source-check. Der Browser benutzt künftig dasselbe
Menü; laufende Website wurde nicht geändert. CMakeLists, übrige Browser-/KI-
Dateien und fremde Abschnitte in MERKHILFE/HANDOFF bleiben uncommitted.

## HD-Landschaft hinter dem HUD korrigiert (27.10.)

Nutzer meldet native Landschaft oben an der HUD-Anzeige, ausdrücklich Windows.
src/hd_render.cpp hatte Szene/Regionen für die kompletten oberen32Zeilen
abgeschaltet und ausschließlich den normalenTilepfad verwendet. Jetzt werden
auch dieseZeilen mit ihren eigenenPPU-Zuständen gesammelt. Nur tatsächlich
sichtbareBG3/HUD-Pixel behalten den bisherigenProvenienzpfad, die Landschaft
dazwischen verwendet die normaleHD-Komposition. NativeBG3-Gewinner separat
übernommen, weilWidescreenHUD-Verschiebung reguläreTileprovenienz ausschließt.
KeinBackground-Overlay überSchrift/Balken; Fenster/Priorität/ColorMath bleiben.

NeuerTest tools/test_hd_hud_background.py reproduzierte denFehler vorKorrektur.
Danach hud-background-gdahjz9z bestanden:3562HUD-Pixel exakt,20100veränderteHD-
Pixel undechteSubpixeldetails imDiagnosehintergrund, Kategorie-/Szenenguards,
installiertesBrückenpaket undA02F3:735200HD-Pixel imoberenBereich, sichtbare
HUD-Zeichen,nativeRaster undvollständigeWRAM-Dumps unverändert. Vergleiche
programmgesteuert,keinBildbetrachter. test_hd_scene.py ebenfalls bestanden
(hd-scene-check-gc5gcnyd):2/4/10xOriginalidentität,Alpha,Szenenguards,Scroll,
Brückenrotation undWasseranimation, nativeBilder/Zustände gleich.

Lua- undregulärerWindowsBuild erfolgreich. NeueEXE inbuild undbuild-play/game
installiert, SHA256626b96629413473c7d6af725e67b0baa985fe797e328e01bbb0b17c3ada3fa93.
VorherigeEXEs undInstallationsnachweis unterartwork-local/hud-background-2026-10-27.
Die alteSpiel-EXE liegt zusätzlich alsSuperCastlevaniaIvSNESRecomp.hud-before-
20261027.exe imSpielordner. Austausch durchUmbenennen+vorbereiteteDatei nach
Prüfung an eigenerlaufenderTestinstanz; keinBenutzerprozess beendet. Aktive
Spielpaketauswahl,Steuerung,ROM-/Performance-Auswahl hashgleich; Original-Simon
weiterausgewählt,keineBild-/Paketänderungen. Neustart fürgeladenenCode nötig.
Browser nichtdeployt (Nutzer meldet Windows);gemeinsamerQuellfix ist beimnächsten
Webbuild enthalten. AndereoffeneBrowser-/Landschaftsänderungen nichtcommitten.

## Level-Editor mit nativem Spieltest (24.10.)

**Neuester Ausbau: freie Grafikquellen (Vorrang vor älteren Formatdetails unten).**
Nutzer will bestehende/neueLevels gleichwertig bearbeiten und innerhalb eines
Raums Grafiken aus allenAbschnitten frei kombinieren. Quellen unabhängig von
Zielraum undZielebene:69Einträge, R00..67 plus spätererMode7-KontextR23.
Alle69Quellen erfolgreich lokal vorbereitet; rooms/sources.json bestätigt dies.
Mode7 auchR21/22/27; seine1024Mapblöcke und256Texturkacheln sind statisch nutzbar.
Vertikaler/Mode7-Kartenimport undSkriptmechaniken bleiben gesondert offen.

tools/level_tiles.py: Projektv2 mit32bitZellen. Low16=nativesKachelwort,
Bits16..22=Quell-ID+1,Bit23=QuelleBG2,EMPTY01000000. Quellen0..68.
Legacy16bitZellen werden weiter relativ zumRaum gelesen; Copy/Pick binden sie
vorTransport explizit. Flip erhält Quelle/Farben undmanuelleKollision.
Project liestv1 undv2, speichertv2;Kollision bleibt16bit. KeinPixelmaterial inGit.

tools/level_graphics.py: Pixelatlas ausbenutztenOriginalkacheln, RGB555+Opacity,
dedupliziert nachPixeldaten; ursprünglicheBG-Priorität proZelle. BG-Grafiken
unterliegen damit nichtmehr demgemeinsamenSNES-Kachel-/8Palettenbudget.
CV4LVL2 ergänztAtlas und32bitKarten;altesCV4LVL1 unverändertlesbar. Vollständige
Validierung inklAtlasindizes vorAktivierung. MaximalesPaket512MB/1048576Tiles.
Cv4LevelTrack/RenderLine komponieren nachnativemPPU-Lauf: BG1/2nativeDummytile0
transparent, eigenePixel unterBeachtung vonLayer-Screens/Windows, Priorität,
OBJ/HUD,ColorMath undHelligkeit. Kollision undnativeMonster laufenwievorher.
Grafikrenderer nurimexplizitenProjektspieltest;keinSubmodulgeändert,keinNormalspielpfad.

Grafikpicker bietetQuellabschnitt/-ebene unabhängig vomZiel. Hintergrundquelle
kann z.B.imVordergrund platziertwerden. Vorbereitung seriell undabbrechbar beim
Schließen; fertigeQuellen werden sofort imUI freigegeben. prepare_level_sources.py
bereitetalleQuellen vor. ensure_source68 verwendetechtenvorbereitetenMode7-Boss81-
Videokontext, daR23 initialnochMode1 zeigt;kein zusätzlicherQuelllevelstart nötig.

Tests:test_level_editor.py weiterhinbestanden(check-dtpo2zjp). NeuerTest
test_level_tiles.py bestanden(mixed-check-14palfwo):69Referenzen/beideEbenen,
JSONv1/v2,TkQuellwahl/69Quellenvorbereitung/Mode7Picker,BG2→BG1,Kopie/Flip/Save,Mode7rawbyte-Abgleich,
3584exakteRasterpixel mit17Quell-/Palettenkombinationen,Transparenz,NativeOBJ
vor/hinterfremderGrafik,RaumwechselundatomareAtlasfehler. KeineBildbetrachter.
Alle69Quellen einschließlichPlausibilitätsprüfung aufFarb-/Grafikdaten bereit;
initialeVorbereitung294s. BeideBuildvarianten erfolgreich. EinschränkungenzuBossadaptern,MonsterOBJ-Budget
undKampagnenexport geltenweiter;freieBG-Grafiken sinddavonunabhängig.

Nutzerwunsch: eigener Level-Editor im Stil von Lunar Magic. Neue separate
Tk-Anwendung tools/level_editor.py, Start Level_Editor_starten.cmd. Zwei
Grafikebenen, 32px/8px-Palette, Kollision, Bereichskopie, Spiegelung, Undo/Redo,
Räume, Startpunkt, Monster-Codes, Ausgangszonen und native Testinstanz.
tools/level_demo.py legt die lokale Erste_Testwelt einmalig an. Projektformat
.sc4level.json in artwork-local/level-editor/projects; keine Originaldaten in Git.
Maße/Kollision/Objekte/Ausgangsziele validiert; atomare JSON-Speicherung.

tools/level_assets.py: echte WRAM-/VRAM-Assets einmalig pro Originalraum,
Cache mit ROM-SHA; horizontaler Mode1-Import. WRAM6000/C000 Blockdefinitionen,
8000/E000 Metatilekarten. Metatileflip8000=horizontal,4000=vertikal,
anders als8pxTilewort. Tileklassifikation ausC8..E4. Originalakteure aus
vollständiger sechsByteListe05:(00:D81B+Raum*2), keine uniqueCatalog-Platzierung.
Nicht unterstützte Spezialobjekte gezählt und angezeigt. Vertikal/Mode7-Import
explizit abgelehnt; eigene hohe Räume funktionieren.

src/level_editor.cpp: opt-in Lua level_project/level_room; inaktiver Standardpfad.
CV4LVL1 enthält Raumheader, D400ByteVRAM-Präfix+CGRAM, beide8pxKarten und
Collisionmaps, Actor/Exitrecords. Atomar vollständig vor Installation validiert.
BeforeFrame füllt originalen512pxKollisionsring4000/A000 und streamt Actorplätze;
BeforeDraw installiert Grafik und mappt64x32PPU-Ringe4000/4800 mit eigener Kamera.
NativeObjektplätze undKI bleiben erhalten; Raum0 ist ruhiger Basiskontext.
Original-Streamer auf tatsächlichenFFFF-Abschluss der Raum0Liste gesetzt,
Phase5/Raum0/B8=0. Vorherige Arena-/Herkunftsraumroutinen werden nicht benutzt.
GameSessionReset deaktiviert den Projektadapter. Keine Normalspiel-Konfigänderung.

Kollisionsroutine00:CF86: AE0/2 nurBG1, AE1 BG1+BG2 nachOriginalregel,
AE3 getrennteSpielebenen, Actor+02=8018 wähltBG1, sonstBG2. Neu erstellteRäume
verwenden3; Import übernimmtAE. AuchAusgänge können Zielebene wählen.
OBJ-Prioritätsflag8018 überschreibt nurPriorität12/13, NICHT Palettenbits9..11.

tools/level_playtest.py: private NativeSession, ROM-direkte Monsterressourcen
inklusive belegter Kinder/Todesobjekte, ursprünglicheParameter undRaumbonus.
AlleProjekträume teilen derzeit11nativeOBJ-Seiten und einen kompatiblen Satz
Originalpaletten; Konflikte vor Start mit Erklärung abweisen. Bossmarker bleiben
planbar/speicherbar, Spieltest lehnt sie bis zum passendenSpezialadapter ab.
EigeneKampagnen-/Modexporte, HD-Kartenansicht, Treppen/Skriptobjekte, vertikaler
Originalimport undMode7 bleiben offen; nicht als vollständigenLunarMagic-Klon ausgeben.

Bedienung/Grenzen in docs/LEVEL_EDITOR.md und einfacher MERKHILFE.md.
tools/test_level_editor.py prüft echteTkCallbacks und Original-Engine einschließlich
1792 Originaltilewörtern,2196Rasterpixeln ohneBildbetrachter, handgezeichnetemBoden,
M-0012 ausfremdemRaum, Touch-/Up-Ausgängen, Kamera492/261 imhohenRaum und
getrenntenBöden192/160 aufbeidenSpielebenen; abgeschnittenesPaket atomar abgewiesen.
Abschließender Testlauf check-9m0e9tsp bestanden, ohneBildbetrachter.
Originalraum1 zusätzlich importiert:2048x256,AE3,16Monster;60nativeFelder stabil.
Regulärer undLuaBuild erfolgreich. RegulärerStartupcheck startup-check-tsqvwr9x
mitRunAhead0/1 jeweils sichtbaremSpiel bestanden. GUI undTestfenster skalieren
mitBildschirmgröße; beideSpielinstanzen beimSchließen sauber beendet.
InteraktiverTest zusätzlich mitScale4/echtemResume; fehlendesAudiogerät wird
gezielt durchNeustart ohneTon behandelt. PrivateTestkonfiguration deaktiviert
RunAhead/Rewind, daAdapterzustandnoch nicht imNativeSnapshot enthalten ist.

## Echter neutraler Spawn und portable Monsterressourcen (24.10.)

**Aktuell, Vorrang vor älteren Kontextbeschreibungen unten:** Nutzer möchte
keine Herkunftslevels pro Monster starten und künftig Monster/Bosse frei in
anderen Levels einsetzen. Standard-Monsterwerkstatt lädt jetzt ausschließlich
eine gemeinsame Basisszene und richtet darin neutralen Boden/Seitenwände ein.
Kein Herkunftsraum, keine Ladephase3 und kein fremder Snapshot beim Live-Spawn.
NativeSession.arena_enabled routet nach spawn_neutral; _spawn_original bleibt
Offline-/altem internem Client vorbehalten, ohne bisherigen Arena-Sonderpfad.

tools/enemy_resources.py entpackt native Grafiken direkt aus ROM. Codec
02:864A..87C5: 1024Byte-Ring, Header ist komprimiertes Ende, LZ-Referenzen,
Literal-/Zero-/Byte-/Zero-Literal-Runs. Originalpointer01:A900+t*3,
Slotreservierung01:AA80+t, Relocation01:A8D4, VRAMziele01:A8EA, Lookup00:D7CC.
AA80 ist Reservierung, nicht exakt entpackte Länge:11/12/56 teilen08:9F60,
verwenden2/3/4KiB. Deklarierten Präfix verwenden, verbleibenden Tail nullen.
Gemeinsame Ressourcen zusammenfassen; Plan mit first_slot unterstützt getrennte
Reservierungen und weist >11native1KiB-Seiten ab. Feste Effekte mit CountFF
bleiben im gemeinsamen Grundbestand. NativeSlots13A0 nur am Gruppenanfang setzen.

src/enemy_resources.cpp: atomarer Grafikimport CV4OBJ1, nur OBJ6A00..7FFF,
8/16px-Layout6000/7000, Palette separat, alleSpannen/Überlappungen vor Änderung
prüfen. NativePalettequelle steht in$48, gewöhnlich2200; OBJ128..255 liegt
darum bei2300..23FF. PPU-CGRAM und WRAM-Shadow gemeinsam aktualisieren.
Keine Actor-/OAM-/CPU-/Leveldaten in diesen Bundles. Kein Gameplayhook im
normalen Spiel; Lua-Befehl enemy_resources wird vom separaten Client verwendet.

Farben einmalig aus vorhandenen belegten Kontexten: prepare_monster_resources.py
mit --ensure im Launcher;95Paletten lokal vorbereitet. Fehlender Boss81-Kontext
einmalig original erfasst, danach Cache mit SHA256/ROM-Bindung; Live-Spawn lädt
nie ersatzweise ein Level. Customlibrary im Worker bis NativeSession durchgereicht.
Bosse nutzen ihren Originalcontroller2A im neutralen Raum0, kein Herkunftsraum.
44=PPU-Layer/ColorMath-Preset;46=HDMA-Preset, KEINE Raumskripte. 1200..127F sind
Palette-Jobs; vor Spawn leeren, danach native Bossjobs erhalten. B8 für
Bossauxdispatch bewahren. Originale Weltkoordinaten/Ursprung wegen fester
Bossgrenzen behalten. Kollision einmal je Reset bauen, nicht pro Feld native
Arbeitsdaten überschreiben. Kamera und geschütztes Spielerziel weiter halten.
Mode7-81 nativ sichtbar; HD-Texturzuordnung bleibt offen.

Live-Stats enthalten runtime_room=0 und neutral=true. Der Normal/NG+-Vergleich
nutzt zur Vergleichbarkeit weiterhin den Originalzuschlag des Herkunftsraums;
UI weist darauf hin. Tatsächlicher Testraum und Wertebezug sind getrennt.
Keine neuen Plätze in tatsächlichen Spiellevels installiert. Nächste Schritte:
Platzierungseditor, gemeinsame Grafik-/Palettenverwaltung bei Familienmix,
Bossgrenzen/Spezialeffekte und globalenB8-/Levelabschluss pro Einsatz entkoppeln.

Ohne Bildansicht geprüft: test_neutral_monsters.py sperrt _spawn_original,
fremdeRaum-/Phase3-Schreibvorgänge sowie fremdeSnapshotloads. Alle47 normalen
Codes je96Felder und12Bosse je360Felder sichtbar, Raum0/Phase5, keineZiel-HP-
Verluste. Evidenz neutral-check-vhjrkhtd/report.json, kompakte Metadaten in
assets/monster_arena_verified.json. Zusätzlich neuere Collision-once-Prüfung:
81/8B/8C je480Felder, neutral-check-eh95eajn;7F360Felder samt exakter Hostimport-
und PaletteShadow-Prüfung, neutral-check-ma03ae0q. Beide ohne Herkunftslevel.
Nativer Tk-Test inklusive Original/HD, Sprung/Wurf/Tod und BossNormal/NG+:
monster-check-pcbi29ys/report.json. Direkter Decoder bytegleich gegen
vorher unabhängig erfasstes Original-VRAM für07/11/12/31/56/69/7F; Ressourcen-
Unitprüfungen inkl. Palette-Warmcache. Release mit/ohneLua kompiliert.
Keine Bilder angesehen, keine bestehenden Artist-PNGs geändert.

## Boss-Werkstatt: Grafikladen und stabile Originalszene (24.10.)

Nutzer meldete fehlerhafte Bosse. Hauptursache: spawn_boss hatte $1A12 als
Musikwarteflag gelöscht und Controllerzustand2 erzwungen. $1A12 ist aber der
Grafikladerstatus im DP-Block1A00 (02810E/0282C7), abgewartet in0293B6.
Originalcontroller2A jetzt Zustand0 starten, nur Countdown+24 verkürzen,
Grafiktransfer und Übergang natürlich fertig laufen lassen. Raum zuerst vollständig
laden, Streamer am echten FFFF-Abschluss anhalten, keine doppelten Controller.
80 benutzt den belegten Raum7 samt Controllervariante80 statt Ersatzraum4.

Private Bosskamera an Raumursprung halten, Spielerziel invulnerabel, Phase5 und
Raum festhalten, keine neutrale Boss-Kollision erfinden. Erstes sichtbares Teil
vor Spawn-Rückgabe abwarten; originale Einleitungen können lange Pose0 haben.
Native Beobachtung jetzt nach NMI/OAM in GameDrawPpuFrame. Nur Werkstatt:
vollständig unsichtbare Teile aus exaktem Deskriptor/VRAM ergänzen; bei um bis16px
versetzten Bossroutinen nur eine eindeutige vollständige OAM-Geometrie akzeptieren.
Normales Spiel behält strikte Matchbedingungen und bisherigen Hookzeitpunkt.

Neue workshop_capture.cpp: native Mode7-BG1-Pixel je Scanline nach IRQ/HDMA,
Index0 transparent; Oberfläche reist als PNG-Bytes im selben Snapshot mit OBJ.
81 jetzt sichtbar in beiden Ansichten, seine HD-BG-Texturzuordnung bleibt offen.
Bossauxfamilie01..0D gehört zusammen ($B8-Dispatch), 0E ist Simons Waffe.
Live-Hauptwerte nach konfiguriertem Slot, insbesondere8B → Typ09 / Slot0D80.
Bossposen/Teile ohne semantischen Beleg unter Noch zuordnen, keine erfundene Aktion.

Library native_setup_revision2 invalidiert nur alte Bossaufnahmen. Alte Metadaten
und Aufzeichnungen unter legacy_captures/history, PNGs unverändert erhalten.
Neue Bossaufnahmen lokal vorbereitet; normale Profile werden wiederverwendet.
Aktuelle Bildzahlen aus library.json lesen, ältere Zahlen unten sind historisch.

Prüfung ohne Bildansicht: alle12 ×480 native Felder, Raum/Phase stabil, Ziel-HP16,
bewegte OBJ-Posen und40 unterschiedliche Mode7-Körperbilder. Messung:
artwork-local/enemy-workshop/boss-check-n91ruq7a/verified-report.json.
Zusätzlicher120-Felder-Starttest86/8A nach Wartefix vollständig sichtbar:
boss-check-lrhdnw4y/report.json. Tk-Prüfung inklusive Mode7, Pause und Boss8B
Normal/NG+: monster-check-xmczxvfu/report.json. Unabhängiger Export vergleicht
IDs und alle RGBA-Pixel für07/12/85: pose-export-21tvb1g0/report.json.
Renderer15Checks inkl. Clipping/eindeutige/mehrdeutige OAM-Zuordnung bestanden.
Library9Tests inklusive Revisionsmigration/PNG-Erhalt: library-check-p00z14ho.
Arbeitsbibliothek aktualisiert; SHA256 aller5592 vorher vorhandenen Artist-/
Referenzdateien unverändert: boss-check-n91ruq7a/artist-preservation.json.
Release mit und ohne Lua kompiliert. Keine Original-ROM/Save-/Artistdaten in Git.

## Monsterwerte: Normal / New Game+ und spätere eigene Modi (24.10.)

Nutzer möchte beide Originaldurchgänge separat sehen und später eigene Modi mit
überschriebenen Werten entwickeln. Rechts jetzt Reiter Werte und KI/Hinweise,
Vergleichstabelle Normal/NG+ sowie Auswahl Vorschau, die die echte private Szene
neu spawnt. NativeSession.quest setzt0088 vor Raumladung;0084/0088/source_room
werden mit den Live-Werten geliefert. Keine Änderungen am normalen Spiel.

ROM00:D3FA..D40E: 0084 = Byte01:A88F+Raum + (0088?16:0).
ROM00:D74E..D75C: HP = min(7FFF, Wort01:AC00+Typ*2 +0084).
Kontakt01:AF00+Typ bleibt hierbei unverändert. Früher Raum M0012:48/64 HP,
Kontakt3/3. Später Kontext M006B:64/80 HP, Schwierigkeit16/32, nativ geprüft.
Boss-HP weiter ungeprüft; kein pauschales+16 auf alle Attribute behaupten.

Modell tools/monster_balance.py: original_stats und pure resolve_mode.
Version1, base_profile normal/new_game_plus, overrides nach M-XXXX; anfangs hp
und contact_damage mit Grenzen/Typprüfung. Original/effective getrennt und tief
kopiert. Kein automatisches Laden/Schreiben von Moduswerten im eigentlichen Spiel;
Editor und Engine-Anwendung sind Zukunftsarbeit, keine aktuelle Änderung.
Prüfung: test_monster_balance.py fünf Tests, erweiterter nativer Tk-Test inklusive
NG+-Umschaltung und Rückkehr zu Normal; keine Bilder angesehen.

## Korrektur: Monster-Prüfstand statt gemischter Sprite-Browser (24.10.)

**Aktueller Nutzerwunsch:** Keine erfundenen Namen. Monster per stabilem Code
wählen, eigene Namen speichern, Körper/Angriffe/Geschosse/Todesbilder zusammen
sehen; echte KI in neutraler Umgebung, Live-Werte und belegte KI-Erklärungen.
Bilder möglichst nicht ansehen, weil das sein Sitzungskontingent belastet.
Diese Umsetzung wurde ohne Bildbetrachter oder Screenshotansicht geprüft.

Launcher startet jetzt `tools/monster_workshop.py`. Der frühere Client bleibt
interne Grundlage; die Standardansicht ist Monster → Variante → Aktionsreiter.
Codes M-XXXX, Namen in `project.json/monster_names`. PNGs bestehender Projekte
werden nicht umbenannt oder überschrieben. Neue Dateien/Monster-ZIPs verwenden
Codes. Angriff von M-0012 enthält Körper und Knochen; geteilte PNGs können
mehreren Aktionen angehören. Optionale Grafikvarianten halten die Standardliste
bei einer PNG pro Pose/Teil. Lebende PNGs und exakte native Import-IDs bleiben.

NativeSession.arena_enabled lädt erst Originalgrafiken und ersetzt dann beide
privaten Kollisionskarten 4000/A000 durch Luft/Boden192/Seitenwände. Raster nach
00:CF86, 4 Seiten mit je 32x32 8px-Zellen. Heroziel96/168, invulnerabel; Raumskript0
und Phase5 werden pro Feld gehalten. 31 lädt die echte Platzierung Raum18,
05:9128 statt Raum17 mit automatischem Übergang. Bossstart deaktiviert die
neutrale Arena für den Controller und bleibt experimenteller Originalkontext.
45/46 gewöhnliche Codes kurz sichtbar geprüft. 007F bleibt instabil; die Szene
hält an und zeigt keine Müllwerte. Unsichtbare Helfer6C/73 und leerer Handler77
(02:A970 = RTL) sind keine eigenen Monster. Kategorien/Namen alter Audits nicht
als verbindliche Monster-Identifikation verwenden.

Werte: HP-Basis01:AC00+t*2, live+06; Kontakt01:AF00+t (BYTE!), Hitbox+28/+2A,
State+12, X/Y+0A/+0E, Geschwindigkeit18/1A/1C/1E. Bosskontakt01:B201; Alias8B→09
noch ohne geprüften Schadenswert. Modell: tools/monster_model.py.
Gehen/Springen/Angriff für12/31/56 durch Originalzustände geprüft;11/69 kein
nativer Sprung/Wurf. Attack56 benutzt 91D8/9201 und ist Nahkontakt, kein Geschoss
(E096 ist Schadenprüfung, kein Spawner). M0012 Wurfkörper8B1B/8B30/8B4D,
Geschoss2 mit900C/9011/9016. Todesübergang nach00:DBF2..DC64, neue Bilder werden
unter monster_actions gespeichert. Andere Aktions-/Geschosszuordnungen noch
ungeprüft: Natürlich und Noch zuordnen ehrlich ausweisen.

Interne vollständiger vorbereitete Bildbibliothek: 106 native Profile plus16
reine Vorlagengruppen,3697 Bild-/Teil-Zuordnungen;631 ganze Vorlagen,3066 Teile.
25.504 native Felder aus kurzen Probeabläufen;425 zusätzliche PNGs aus direkt
belegten ROM-Posen und gemessenen GFX-Kontexten. Kein Vollständigkeitsnachweis aller
Aktionen. Werkzeuge enemy_workshop_library.py, enemy_sprite_inventory.py,
enemy_sprite_export.py, prepare_sprite_library.py. Warm-Cache startet keinen
Emulator. Source-PNGs und Zeichnungen bleiben erhalten; ROM/PNGs nicht in Git.
Extra-Kontext-/Boss82/8D-Probes sind Forschungswerkzeuge, noch nicht im Standard.

Gezielte Prüfungen: test_monster_workshop.py (native Tk-Funktionen, echte Sprung-
und Wurfroutine, Werte, Pause, PNG-Livereload, Export, Tod, Codes/Namen),
test_enemy_library.py (8 Prüfungen), test_enemy_sprite_inventory.py (6 Prüfungen).
Neue Anleitung: docs/ENEMY_WORKSHOP.md; Merkhilfe entsprechend ersetzt.

## Separate Gegner-Werkstatt und volle Skelett-Aktionen (24.10.)

Das bisherige Zwei-Gehbilder-Pilotpaket war unvollständig. Jetzt vorhanden:
eigener Tk-Desktopclient `Gegner_Werkstatt_starten.cmd` mit isolierter Lua-EXE,
Original/HD aus demselben nativen Feld, Pause, Einzelbild, Zeitlupe, Spawn,
Spielerziel Links/Rechts und live austauschbaren ganzen Posen oder Einzelteilen.

Native Skelettvarianten $11/$12, Knochenwerfer $12: Körperposen 8AF4,8B05,
8B1B,8B30,8B4D; Knochen Actor02 mit 900C/9011/9016; Todeseffekte Actor2D
mit zehn Posen 80DC..8145. Sammlung außerhalb Git in Assets (ausgeschnitten)/
Gegner/02_Skelette_Alle_Aktionen und Arbeitskopie Gegner/Werkstatt:
55 verschiedene 387er-PNGs, davon 18 ganze Bilder und 37 optionale Teile;
73 native Zuordnungen. ZIP: Skelette_Alle_Aktionen_2026-10-24.zip.
Keine Nutzerzeichnung installiert. Die alte Sammlung bleibt erhalten.

Katalog: 94 Profile zweimal 24/32 native Felder geprüft, 83 exakt sichtbar.
Davon 39 als Gegner, 17 als Objekte, 8 als Gefahren und 5 als Effekte
beschrieben; 14 unbestimmt. Elf generische Kontexte offen. Metadaten:
assets/enemy_catalog_verified.json. Sichtbarkeit beweist keine vollständigen
Aktionen. Bosscontroller2A intern; Profile80,81,83..8C, davon elf mit echten
C++-Hauptbildern. 81 braucht BG/Mode7; 82/8D offen. 8B erzeugt Haupttyp09
in Slot0D80. 80 nutzt belegten Testkontext Raum4, Originalraum7 noch offen.
Weitere Aktionen und Projektile familienweise ausbauen. Keine vollständige
Sammlung aller Gegneranimationen behaupten. Grenzen: docs/ENEMY_WORKSHOP.md.

Renderer: ganze Posen und __teil-N pro originalem Metaspriteindex, genaue
OAM-Masken, 96/256 native Leinwand, 387/1032 Arbeits-PNGs. Ganze Pose nur bei
einheitlicher Priorität/Farbrechnung; sonst Teile/Original. PNG-Aufnahme async,
flush beim Schließen. Originalvorschau nach globaler OAM-Reihenfolge auch für
Knochen/Körper-Überlappung. Referenzen behalten den ersten Palettenstand;
Palette und Blitze sind in der neutralen Vorschau noch nicht farbgenau.

Gezielt bestanden: 180 native Skelettfelder mit allen 5+3+10 Bildern/Teilen;
neun Live-PNG-/Importfälle; C++-Masken, Spiegelung, große Leinwand und gemischte
Priorität; echter Renderer mit Zaunverdeckung und identischem WRAM/VRAM/CGRAM/
OAM; Tk-Bedienung, Pause/Einzelbild, Spawn bei Pause, Filter/Teile und Cleanup;
Katalogmetadaten. Berichte unter artwork-local/enemy-workshop,
enemy-workshop-review und enemy-catalog-audit. Bossabschluss:
artwork-local/enemy-workshop/boss-profile-evidence-2026-10-24.json.

Release in build und build-play/game aktualisiert. Altes EXE-Backup und
Profilprüfsummen unter D:/Super Castlevania IV Recomp/backup/hd-artwork/
2026-10-24-enemy-workshop-prebuild. Einstellungen und Spielstände unverändert.
Release-SHA256: 26801DE8CA92E063A4371649755C5C53A84FFA7B27B2AE901683DB825B9368FE.
Parallelchat-LoRA-/Landschaftsänderungen nicht mitstagen oder überschreiben.

## Fertige PNG-Sammlung für Gegner-Redesigns (23.10.)

Nutzer wollte PNGs zum eigenen Redesign statt Laufzeit-Screenshots.
Startpaket angelegt neben den bisherigen Assets unter D:/Super Castlevania IV
Recomp/Assets (ausgeschnitten)/Gegner/01_Skelette. Zwei artwork-PNGs bereits
387×387 (4,03125×), native references unverändert96×96, project.json mit vier
belegten Zuständen ($11/$12 × $8AF4/$8B05), Bildergalerie, UEBERSICHT.png,
kurze Anleitung. ZIP daneben:Skelette_Redesign_Startpaket.zip. Keine Art ins
Spiel installiert; die EXEs und Profile bleiben unverändert.

Tools:enemy_hd.prepare optional --work-size387, Galerie wird automatisch
angelegt. work_templates-Pixelprüfsummen verhindern, dass bloß vorab vergrößerte
Originale als neue Designs gepackt werden. Geänderte Exporte bleiben bytegleich.
GUI-Button für vorbereitete Skelette bevorzugt die neue Sammlung, mit altem
internen Arbeitsordner als Rückfall. Zwei fokussierte Importtests und Prüfung
gegen die echten vier Runtime-Referenzen bestanden. Siehe docs/ENEMY_HD.md.

Aktueller Umfang bleibt nur die sicher zugeordneten Skelett-Gehposen.
Optionale Frage zu weiteren Gegnern gestellt; bislang keine Antwort.
Nicht als fertigen Katalog aller Gegner ausgeben. Artwork und ZIP bleiben lokal.

## Menüüberarbeitung für 4K vom 23.10. (Punkt 6)

Escape-Menü: Lato 18px Basis, mehrere direkt gerasterte Größen bis45px,
automatische Windows-/Auflösungsskalierung (4K:200%,36px), gespeicherte
Menu-size-Auswahl 100–250%/Automatic in ui_settings.json. Fensterbegrenzung,
umbruchfähige Navigation und tatsächliche Work-Area für alle Panels.
Shortcuts:42px-Zeilen multipliziert mit UI-Skala, Filter, feste Binding-/Clear-
Spalten, einklappbare Controller-Hilfe. HD-/Figuren-/Notiz-/Einzelbild-UI passt
sich mit an. Shared runtime UI skaliert Desktop-Metriken, größere Panels,
umgebrochene Beschreibungen und +/- auf der ersten Textzeile.

UI-Fork:39adc724dd725cd777480e91d18ee68dc460739f auf
Gast114/recomp-ui codex/sciv-menu-work-area veröffentlicht; Pin und Bare-Backup
aktualisiert. Root-Spielordner build und build-play/game aktualisiert.
Vorherige EXEs + Installationsbeleg unter D:/Super Castlevania IV Recomp/backup/
hd-artwork/2026-10-23-menu-4k-prebuild; Konfiguration, Grafikpaketauswahl und
Spielerdaten per Hash unverändert. Details/Nachweise:docs/GAMEPLAY_TOOLS.md.
Neue gezielte Regression:tools/test_menu_scale.py. Echte 800×600-/4K-Renderings,
Shortcut-Interaktion, Menu-size-Mauswahl/Speichern/Lesen und bestehende
Shortcut-/Performance-/HD-Menütests bestanden. Keine neue Spielgrafik erzeugt.

## Spieltechnik vom 23.10.: Rewind, zweiter Durchgang, Gegner und Import

Nutzerauftrag mit fünf Punkten umgesetzt: neuester Debug-Marker an der
Zugbrücke korrigiert (BG2-Weltkoordinaten statt wiederholtem Kartenanfang),
F8-Rewind verlässt nach Enter/Escape zuverlässig das Menü (Öffnungsflanke vor
modalem Aufruf verbrauchen), NEW GAME+ setzt das echte native Questflag$88
wie der Abspann statt Sandbox. START bleibt normal; Save/Load und zusätzliche
A02-Gegner sind belegt. Kein vollständiger Spiel-/Passwortdurchlauf behauptet.

Gegner-HD funktioniert als geprüfter Skelett-Pilot ($11/$12, zwei Schritte,
beide Spielebenen), mit vollständiger OAM-Zuordnung und PPU-Gewinnerkennung.
Unbekannte Posen bleiben nativ; weitere Gegner/Bosse brauchen eigene Belege.
Keine neuen HD-Designs installiert. Vorlagen: `artwork-local/import-workspaces/
skelette-2026-10-23/VORLAGEN.html` (nur zwei PNGs bearbeiten).

`HD_Import_starten.cmd`: gemeinsames Fenster für Simon und Gegner, Original-
Vorlagen mit Bildergalerie, freie PNG-Auflösung inkl.4,03125×, Paketprüfung und
Einbauen-Knopf für beide Spielordner mit Auswahlbackup/Rollback. Quell-PNGs
bleiben bytegleich. Sechs Import-, fünf Installertests und echte Laufzeittests
bestanden. Details/gezielte Nachweise: `docs/GAMEPLAY_TOOLS.md`, `HD_IMPORT.md`,
`ENEMY_HD.md`. Rewind und HD-Menü auch im Release ohne Lua getestet.

Beide Spieler-EXEs installiert; Kulisse `hd_packs/stage-01-user-a02-v3` gewählt.
Sicherung/Hashes: `D:/Super Castlevania IV Recomp/backup/hd-artwork/
2026-10-23-gameplay-tools-v1`; vor Neubau alte EXEs zusätzlich `...-prebuild`.
Saves, Marker, Charakter-/Gegnerpakete und Steuerung hashgleich erhalten.
Framework `fc9dface236e695931c42f51d68651bb64d8f39b` auf eigenem gast114/sciv
veröffentlicht und Bare-Backup aktualisiert; Root-Pin angepasst. Fremde lokale
LoRA-/Landschaftsänderungen nicht mit diesem Auftrag committen.

## Aktuell: lokaler SDXL-LoRA-Pilot und GPU-Beschleunigung

### Pausiert auf Nutzerwunsch: HD-Simon (27.10.2026)

Der Nutzer hat den bisherigen HD-Simon verworfen und das gesamte Sprite-Projekt
vorerst pausiert. KEINE weitere Erzeugung, Trainingsfortsetzung oder Installation
ohne ausdruecklichen neuen Auftrag. Die zuvor geplanten drei Posen und Treppen-
bilder sind keine offenen automatischen Folgeaufgaben mehr.

In build-play/game und build ist characters/selected.txt leer: Original-Simon.
Die beiden installierten simon-user-hd-three-poses-v1-Verzeichnisse wurden nach
artwork-local/simon-pausiert-2026-10-27/spielpakete/build-play bzw. build verschoben;
Originalpfade, Auswahl und SHA256 aller Dateien stehen in status.json. Keine
Bilder geloescht. Lokales Quellpaket unter artwork-local/characters bleibt.
Sieben Werkzeugkopien im Archiv unter werkzeuge sichern den unfertigen Stand.

Browser ebenfalls auf Originalfigur umgestellt: lokale dist/sciv-web/site-
Auswahl und Manifest aktualisiert, bestehendes sciv-web.tar.gz entsprechend
neu gepackt, vorheriges Paket im Archiv. Live auf CT116 unter
/opt/sciv-web/site/content nur characters/selected.txt und dessen Manifest-
Eintrag geaendert. Remote Sicherung /root/sciv-simon-pausiert-20261027-120152.
443 und8443 mit Zertifikatspruefung verifiziert: Auswahl0Bytes, Manifest korrekt.
Bestehende Browserdaten uebernehmen den neuen Standard beim Neuladen, sofern
die Auswahl nicht individuell geaendert wurde. Keine Saves/TLS/anderen Pakete
geaendert. Kein laufendes Windows-Spiel beim Wechsel.

Gemeinsame Comfy-Queue war leer; Modelle per /free entladen. Keine aktive Sprite-
Berechnung. Server selbst bleibt fuer andere lokale Arbeiten verfuegbar.
extension.json im Arbeitsordner hat paused_by_user und resume_requires_explicit_request.

Bisherige Versuche bleiben unter artwork-local/simon-design-extension-2026-10-23.
Eigenes600erLoRA ist fertig, traf den Stil aber nicht ausreichend. FLUX mit zwei
Ganzkoerperreferenzen uebernahm die Laufpose statt der Treppenhaltung. Die letzte
Pose-Initialisierung mit Sigmas .58,.43,.28,.14,0 bewahrte die Haltung, aenderte
aber den Stil praktisch nicht. Auch sie ist kein fertiges Spielbild.
Eine Detailtafel aus Walking01 liegt unter reference/Design_Details_2026-10-26.png;
sie wurde nur vorbereitet und angesehen, NICHT in einer weiteren Berechnung
verwendet. Keine neuen Posen exportiert/installiert. Keine weitere Probe starten.

Training/Quellen waren bereits extern unter backup/hd-artwork/
2026-10-23-simon-design-extension SHA256-geprueft gesichert. Alte Modelle und
Python-Umgebungen unveraendert. Merkhilfe und PAUSIERT.md nennen den aktuellen
Original-Simon-Stand; aeltere Aktivierungsangaben sind nur Verlauf.

### Vorheriger Stand: Photoshop-Laufbilder des Nutzers installiert

2026-10-23: Nutzer hat sechs PNGs in walking-neural-edit-2026-10-22/review-v1/frames
selbst überarbeitet und den Einbau ausdrücklich beauftragt. Tatsächliche Dateien
waren eng zugeschnitten:201x478,256x480,296x470,237x480,224x488,267x462; niemals
unverändert in den Renderer kopieren (%10-Anforderung und alte display_size!).
Gegen die gesicherten Vor-Photoshop-PNGs registriert, ganzer Körper und Schuhe
geben dieselben Translationen:[64,13],[33,13],[12,23],[50,13],[44,13],[22,28].
Ohne Resampling auf gemeinsame330x510-PNGs gesetzt. Vier transparente Pixel
links plus sechs rechts machen den alten nativen Ursprung31,4 bei int-Offset31
exakt darstellbar. Neuer PNG-root[170,210], hd.offset[31,27], display_size[33,51],
scale10 für alle sechs. Original-RGBA jedes bearbeiteten Bilds unverändert auf
Arbeitsfläche kopiert und exakt geprüft. Keine neuen KI-Berechnungen/EXE-Builds.

Installiert in build-play/game/characters/simon-user-hd-three-poses-v1,
build/characters/simon-user-hd-three-poses-v1 und artwork-local/characters/... .
Pro Ziel nur sechs Lauf-PNGs, ihre hd-Felder im Manifest und Importbelege geändert.
Native IDs, cells, anchor/hand, body.png, übrige3HD-Posen und Gameplay erhalten.
Beide Spielordner haben das Paket schon ausgewählt. Automatisches Reload oder
Esc → Character workshop → Reload. Keine Gameplay-Testmatrix nötig für Bildimport.

Audit/Originalquellen/vorherige Pakete/Prüfsummen:
artwork-local/simon-photoshop-walk-install-2026-10-23/install.json und Unterordner.
Externes SHA256-geprüftes Backup:
D:/Super Castlevania IV Recomp/backup/hd-artwork/2026-10-23-simon-photoshop-walk.
Die Photoshop-Quelldateien nicht ändern. Alte Kontaktbögen/ZIPs in review-v1
wurden nicht neu erzeugt und zeigen noch den ursprünglichen KI-Stand.

Nutzer hat auch going-upstairs-01.png bis06 + going-upstairs.png unter
D:/Super Castlevania IV Recomp/Assets (ausgeschnitten)/Simon Belmont ergänzt.
Das sind native RGBA21x47,32x47,21x47,26x47,26x47,24x47. Noch keine HD-Treppen-
Bilder erzeugt/installiert; Vorlagen erhalten. Einzelne Frames, gemeinsame
transparente HD-Arbeitsfläche und fester Bezugspunkt empfohlen; keine separate
Zentrierung, kein Alpha-Trim pro Phase. Hinweise in MERKHILFE.md ergänzt.

### Vorheriger Stand: lokale neuronale Korrektur als Vorschau


Aktuelle Ausgabe:
`artwork-local/lora-pilot-2026-10-21/walking-neural-edit-2026-10-22/review-v1`.
Sechs transparente PNGs320x510/10x, Animation.webp, synchroner Vorher/Nachher-
Vergleich, HTML-Einzelschritt, ZIP und placement.json. Kontaktbogen wirklich
visuell geprüft; PNG-Modus/Größen/Manifesthashes/ZIP vollständig geprüft.
Gemeinsamer Crop[180,0,820,1020], root[166,210], ground_y500; keine individuelle
Skalierung/Zentrierung. **Nutzerbeurteilung ausstehend, NICHT im Spiel eingebaut.**
Kleine Platten-/Nietendetails variieren weiterhin; keine perfekte Konsistenz
behaupten. Aktive Spielbilder sind unverändert.

Akzeptierte Bewegung aus walking-native-2026-10-22 bleibt Basis. Alte Fassung
walking-identity-2026-10-22 wegen verzogener Oberschenkel, Alpha-Saumschnitten,
fehlenden Emblemen01/06 verworfen. assembled-v1 setzt die UNTERE Körperhälfte
auf die ursprüngliche native-motion-RGBA zurück und nutzt dort ausschließlich
neuronale Korrekturen. Vorhandenes gemeinsames01-Gesicht/obere Korrekturen bis
y400 bleiben erhalten; sichtbare Pixel am Übergang sind identisch. Keine neuen
Donor-Hautverformungen. 01-Bauch bleibt die bereits geschlossene obere Rüstung:
FLUX ignorierte diese Aufforderung, daher vom01-Edit nur Rücken-Auswahl0 verwenden.

Verwendete fertige Edits (alle unter walking-neural-edit-2026-10-22):
- 01 repair-01-master: Rückenemblem, NUR Auswahl0.
- 02 repair-02-hem: neuer kurzer Saum.
- 03 03-thigh-style-bf16 + repair-03-gap-guided: neuer warmer Oberschenkel und
  zusätzliches inneres Beinfragment entfernt.
- 04 repair-04-hem-guided: neuer Saum. Ersten repair-04-hem wegen seitlichem
  spitzen Rest im vollen Komposit verworfen.
- 05 repair-05-lower + repair-05-gap-guided: natürliche offene Oberschenkel,
  schmalerer tragender Oberschenkel, langen inneren Stoffzipfel entfernt.
- 06 repair-06-emblem + repair-06-lower: Rückenemblem, offene Haut, kurzer Saum.

Fertige Prompt-IDs, NICHT erneut einreichen:
03-Stil6f1ff8ed-9011-49da-8c09-c55829afa8b9;
6erBatch e9d1e2ad-50ba-426e-85d7-cdfd55937d68 (repairs-batch.json);
2erSpaltBatch d3c92463-2884-4360-9de2-74b1c07dad6d (gaps-batch.json);
04-Saum de701a3b-c914-40c8-8eb9-149ab2fbc460.
Rohbilder, tatsächliche API-Graphen, History, Quellen, Auswahlen und Hashes in
jeweiligen Editordnern. assembled-v1/selections dokumentiert tatsächlich verwendete
Auswahlen inklusive01-Teilmenge; series.json hält genaue Herkunft fest.

Workflow: direct_edit_walk.py prepare/submit/batch/collect, Rezept
assets/character/simon_walk_direct_edits.json. FLUX.2 Klein4B Distilled,
4Schritte/Euler/CFG1, echte Referenzlatents,512erCrop ohne Skalierung in1024erCanvas.
Bei03/04/05 nur im KI-Eingabebild einen störenden Rest mit Hintergrundfarbe
überblendet. FLUX zeichnet finale Kanten; kein Alpha-Löschpolygon als Endgrafik.
collect erhält RGB außerhalb Auswahl bytegleich. assemble_neural_walk.py
verwendet vorhandenes CPU-ISNet für Alpha; RGBA außerhalb jeweiliger Auswahl
bytegleich zur gemeinsamen Basis. package_walk.py --prematted --method gibt
nur10x aus und dokumentiert die Methode ehrlich.

Neue öffentliche Modelle separat unter externem ComfyUI/models/*/simon-klein:
UNet7,75GB, Qwen8,04GB, VAE336MB. download_edit_model.py + Manifest
assets/character/simon_local_edit_models.json pinnen Revisionen/LFS-SHA256/Größen;
alle drei Downloads wirklich geprüft. Keine Venv-/Treiber-/Serverkonfigurations-
oder vorhandenen Modelländerungen. SDXL-LoRA nicht mit FLUX kompatibel.
Offizielle Anleitung: https://docs.comfy.org/tutorials/flux/flux-2-klein

FLUX-GPU-Versuch scheiterte an HIP launch failure im Final-Layer/Weight-Cast.
Kein Bild; History unter03-anatomy. Danach nur verifizierte Comfy-PIDs bei leerer
Queue beendet und unveränderten Landschafts-Launcher neu gestartet. Keine
identische GPU-Probe wiederholen. CPU-only-Server8189 und langsame FP32-Versuche
vollständig beendet. start_cpu_edit.ps1 nur historischer Fallback, NICHT starten.
Tatsächlich funktioniert --cpu-model auf DERSELBEN Queue8188 mit vorhandenen
Core-Nodes SelectModelDevice(cpu), ModelComputeDtype(bf16), SelectCLIPDevice(cpu).
AVX512_BF16 unterstützt. Ohne ComputeDtype-Node auf CPU still FP32! Kein zweiter
Inferenzprozess, Landschaft/Sprites auch wegen gemeinsamem RAM seriell rechnen.

Alle Aufträge fertig; nach letzter leerer Queue /free mit unload_models und
free_memory gepostet. Queue0/0, zuletzt13,2GiB RAM und16,7GiB VRAM frei. Server
bleibt unverändert für Landschaft verfügbar. Aktuelle PIDs/Logpfade nur aus
externem logs/server-launch.json lesen. /free liefert leeren HTTP-Body; Helfer
akzeptiert das. GPU-frei während laufender CPU-Jobs allein reicht nicht für RAM.

Backup: D:/Super Castlevania IV Recomp/backup/hd-artwork/2026-10-21-local-lora/
2026-10-23-walking-neural-repair. Neue Ausgabe/Quellen/Rezepte/Werkzeuge/Docs mit
SHA256 gesichert; große Grundmodelle und Venvs nicht dupliziert.
Git: Fremde untracked Landschafts-/Krita-Dateien und Landschaftsabschnitt ganz
oben in MERKHILFE.md gehören zur Parallelaufgabe. Nicht stage/commit/entfernen.
Eigene Merkhilfe-Hunks separat binär per git apply --cached stage; keine
Textstdin-CRLF-Umwandlung. Fertige eigene Code/Docs nachdev pushen.

### Historischer Stand der inzwischen abgelehnten manuellen Korrektur

Nutzer bewertet die native-konturgesteuerte Gehbewegung ausdrücklich als
"sehr gut". Diese Bewegung NICHT neu generieren oder durch festen Torso ersetzen.
Neue Kritik betrifft Gesicht/Haarlänge, offene Bauchstelle01, lange hintere
Rockzipfel02/04/05/06, doppelte Bein-/Armfragmente03, geschlossene Oberschenkel
03/05/06 und zu dicken Oberschenkel05. Referenz01, Bauch soll wie übrige
Phasen geschlossen sein. Genau diese Bereiche wurden lokal überarbeitet.

Aktuelle Ausgabe: `artwork-local/lora-pilot-2026-10-21/walking-identity-2026-10-22/review`.
SechsRGBA-PNGs320x510, Animation.webp, Vorher_Nachher.webp/png, synchroner
HTML-Einzelschritt mit Vorher/Nachher, ZIP und placement.json. **Neue Korrektur
vom Nutzer abgelehnt und nicht im Spiel installiert.** Kleine
Nieten-/Plattenformen außerhalb der genannten Bereiche bleiben poseabhängig;
keinen vollständig identischen 3D-Anzug behaupten.

Werkzeug `tools/lora/refine_walk_identity.py`, editierbares Rezept
`assets/character/simon_walk_identity_patches.json`. Ausgangspunkt die sechs
1024erRGBA in walking-native-2026-10-22/packaged/rgba-full. Kopf/Haar aus01,
nur Translation an individuelle Halsposition;06hat+10px zusätzlichen
Halsanschluss gegenüber nativer Kopfoberkante. Schnitt nur am Kopf/Kragen,
KEINE erneute ganze Schulter-/Arm-/Torso-Kopie. Bauch01 erhält geschlossenen
Panzerbereich aus04. Offene Hautpartien/Arm03 lokal aus bestehenden Posen
mit expliziten Drei-/Vierpunkttransformationen und Masken,05lokale
Konturverengung mit unveränderten Hüft-/Knieanschlüssen. Hintere Stoff-/Limb-
Fragmente explizit gelöscht, neue Schnittkanten mit schmaler Kontur versehen.
Keine Diffusionsaufrufe, kein neues Training, kein Bild-Upload, kein Imagegen.
Vorhandene Modelle und Python-Umgebungen in diesem Auftrag unverändert.

`package_walk.py --prematted` übernimmt bearbeiteteAlpha ohne neue Segmentierung;
`--before` erstellt gleichen Koordinatenvergleich und beide Seiten steuernde
HTML-Vorschau. Gemeinsame20x→10x-Reduktion unverändert. Validierter neuer
RGBA-Stand unter `edited`, Arbeitsvarianten edited-v1..v4/packaged-v4 und
der erste packaged-Export sind Zwischenstände; nur `review` an Nutzer verlinken.

Backup dieses Stands unter `D:/Super Castlevania IV Recomp/backup/hd-artwork/2026-10-21-local-lora/2026-10-22-walking-identity`,
mit SHA256-Manifest für bearbeiteteRGBA, Ausgabe, Rezept, Werkzeuge und Hinweise.
Gezielt geprüft: sechsRGBA-PNGs320x510, drei6Frame-WebPs, vollständiges ZIP mit
Vorher/Nachher-Bildern; deckende Gesichts-Innenbereiche aller sechs Posen sind
nach Translation identisch zur Referenz01 (max. Kanalabweichung0 im Prüffeld).

**GPU-Abstimmung:** Parallel wird lokal ComfyUI/Landschaft vorbereitet. Mensch
bittet, keine vorhandenen Python-Umgebungen/Modelle zu verändern und GPU-Jobs
nacheinander auszuführen. In diesem Chat laufen nur CPU-Bildedits/Exporte;
GPU für Landschaft freigemeldet. Keine neuen GPU-Jobs ohne Abstimmung starten.
Die untracked ComfyUI-/Landschaft-Dateien und der entsprechende neue Abschnitt
ganz oben in MERKHILFE.md gehören zur Parallelaufgabe; nicht in diesen Commit
übernehmen oder entfernen.

**Korrektur zum bisherigen Walking-Abschluss:** Nutzer hat die Serie wegen
falscher Schulter-, Arm- und Beinbewegungen abgelehnt. `packaged-final` ist
historischer Dateiname, KEINE akzeptierte Endfassung. `--lock-upper-body`
friert die benötigte Schulter-/Armdrehung ein und darf für die Korrektur nicht
benutzt werden. Vorlagen im alten simon_walk_poses.json nur manuell angenähert;
Phasen 1/4 und 2/5 im Ergebnis viel zu ähnlich. Keine weiteren freien
Posebeschreibungen als Nachweis für exakte native Bewegung behandeln.

Neuer Ansatz unter `walking-native-2026-10-22`: prepare_native_walk.py liest
die sechs Originalzellen aus body.png, mit gemeinsamem 10x-Transform und ohne
Einzelbildzentrierung. Smoothed Canny plus vollständige Alpha-Kontur erhalten
Schulter-, Hand- und Beinpositionen. render_sdxl_trial.py unterstützt jetzt
IP-Adapter nur im Stilblock (`--ip-mode style`), damit Referenzhaltung nicht
erneut alle Phasen überschreibt. Öffentlicher Xinsir-Canny-Controller lokal
geladen, Revision1271357eda52d54b857c650cacb5b51144643ccb. Keine Uploads.
Phase04 zuerst wirklich geprüft, danach übrige fünf berechnet. Neue komplette
Ausgabe jetzt `walking-native-2026-10-22/packaged`: sechsRGBA-PNGs320x510,
Originalvergleich.webp/png, Animation.webp, HTML-Einzelschritt, ZIP und
placement.json. **Bewegung vom Nutzer akzeptiert; damalige Kleidungs-/Gesichts-
abweichungen sind noch offen; der manuelle Identity-Stand wurde abgelehnt.**
Konturen/Schulter-/Arm-/Beinpositionen deutlich näher am Original. Rüstungsdetails
variieren weiterhin zwischen Phasen; nicht als fertige konsistente Spielfigur
verkaufen. Keine erneute Oberkörperkopie als vermeintliche Lösung einführen.

Tatsächliche Einstellungen:1024²Arbeitsfläche20x, Xinsir-Canny1,1bis90%,
LoRA0,65, IP-Adapter nurStilblock0,8,36Schritte, Seed20261021. Ursprünglicher
600er-Adapter unverändert. Restliche fünf mit `--offload none --latents-only`,
je161–168s, Peak11846851584Bytes. Phase04 aus geprüftem ersten Lauf wiederverwendet.
`decode_sdxl_latents.py` hat alle sechs danach gemeinsam mit allein geladenem
FP32-VAE/GPU-Matrix-Attention und512erKacheln ausgegeben. Erste Ausgabe146s
inklusive MIOpen-Vorbereitung, danach5,0–5,2s/Bild, alle vollständig erfolgreich.
MIOpen meldete dabei einmal "Invalid elapsed time"; kein Abbruch, PNGs geprüft.
Keine Warmup-Zahl als allgemeine Benchmark behaupten.

`package_walk.py` hat die Oberkörper-Sperre jetzt vollständig entfernt.
Originalformen/Phasen behalten gemeinsame Koordinaten, gemeinsame20x→10x-
Reduktion, kein individuelles Zentrieren oder Normalisieren der Füße.
`review_native_walk.py` zeigt die native Kontur grün auf dem HD-Bild.
Quellen: guides-hd, rendered(Safetensors + Phase04-Provenienz), decoded.
Die Zwischenordner guides/guides-v2 enthalten unvollständige frühere Konturen,
probe-04 war zu weich/falsch und ist keine Ausgabe. Nur packaged verlinken.
Backup: `D:/Super Castlevania IV Recomp/backup/hd-artwork/2026-10-21-local-lora/2026-10-22-walking-native-shapes`,
80Dateien mit SHA256 geprüft, inkl. gültiger Bilder/Latents/Guides/Werkzeuge/Docs,
ohne erneut kopierte Basismodelle oder Python-Venvs.

**Neuester Auftrag: sechs Gehposen erstellen.** Arbeit unter
`artwork-local/lora-pilot-2026-10-21/walking-2026-10-22/`. Sechs native Phasen
anhand des lokalen Atlas angesehen und manuell angenähert: assets/character/
simon_walk_poses.json. Kein automatischer Pose-Detektor oder exakte neue native
Körperzuordnung. Der Nutzerauftrag umfasst hier Erzeugung, keinen stillen Tausch
des laufenden Figurenpakets.

Die sechs Bilder wurden tatsächlich lokal auf890M erzeugt: SDXL-LoRA0,65 plus
OpenPose1,4 bis Ende,32Schritte, fester Seed20261021, IP-Adapter-Plus0,6 mit der
korrigierten Schulterhaar-/Knieschoner-Vorlage. Original600er-LoRA nicht neu
trainiert. Öffentliche IP-Adapter-Gewichte Revision018e402774aeeddd60609b4ecdb7e298259dc729
lokal heruntergeladen; CLIP-ViT-H-Bildembedding einmal berechnet, Encoder danach
von GPU genommen, dieselbe Referenz für alle sechs. Renderzeiten37–39s/Bild,
Peak11846851584Bytes GPU. Kein Cloud-Aufruf.

Bei Walking02/05 tauchten unerwünschte separate Knieplatten wieder auf. Die endgültige
Korrektur verwendet tools/lora/correct_walk_details.py mit expliziten Polygonen
und ganzzahlig verschobenen glatten Knie-/Schienbeinbereichen aus Walking03.
Pixel außerhalb weicher Masken bleiben erhalten. Diffusions-Inpaint-Versuche
(corrected/corrected-v2) waren unbrauchbar und gehören nicht zur Ausgabe.
Originale unter rendered, gültige Korrekturen unter corrected-final. tools/lora/package_walk.py
stellt mit lokalem ISNet-Anime frei und entfernt abgetrennte Maskenartefakte.
Phase01 liefert zusätzlich Gesicht, Schulterpanzer, Torso und gehaltene Arme
für alle sechs Frames: feste Position mit der kleinen vorgegebenen Vertikalbewegung,
Übergang bei Quell-Y270, vormultiplizierte Alpha-Mischung mit klarer Silhouette.
So wechseln Gesicht und Oberkörperrüstung nicht pro Bild; unterer Rock/Beine
bleiben aus den Gehphasen. Das ist bewusst wiederverwendete 2D-Bildarbeit, kein
Nachweis, dass LoRA allein alle Details gleich hält.
Ein gemeinsamer Ausschnitt, keine Neuskalierung pro Bild. Finale Ausgabe
packaged-final: sechsRGBA-PNGs, Animation.webp, Kontaktbogen, HTML-Einzelschritt,
placement.json. Die erste packaged-Ausgabe vor Detailkorrektur ist nicht final.
Native Fingerprints nur als Referenz notiert, Offset/Handpunkt/Übergänge vor
einem Spieleinbau weiterhin prüfen. Merkhilfe enthält Bedienung und Pfade.

**Neueste Designkorrektur vom 22.10.:** Nutzer möchte schulterlange Haare und den
einzelnen hervorstehenden Knieschoner entfernen. Die sichtbare GPU-Armprobe
wurde gezielt mit dem eingebauten Imagegen bearbeitet, als separate Vorlage
unter `design-corrections-2026-10-22/Simon_Schulterhaare_ohne_einzelnen_Knieschoner_v1.png`
im Pilotordner gespeichert. Kein neues lokales LoRA-Ergebnis und kein Nachtraining
behaupten. Lokaler Render-Prompt nennt nun Schulterhaare und passende glatte
Beinschienen, Negative schließen lange Haare und separate Knieschoner aus.
Die bisherigen Trainingsbilder, Prüfsummen und Gewichte bleiben unverändert.

Nutzer wollte nach dem abgelehnten 3D-Modell LoRA ausprobieren und ausdrücklich
lokal arbeiten: Dauer zunächst egal. Danach Auftrag, die Leistung des BosgameM6
mit Radeon890M und KI-Chip zu verwenden. Keine Cloud-Uploads oder bezahlten Calls;
fal-Tab ohne Upload geschlossen. Kein API-Schlüssel erforderlich.

**Alle Prozesse dieses Piloten sind fertig**, keinen alten Job neu starten:
`artwork-local/lora-pilot-2026-10-21`. CPU600Updates mit acht HD-Nutzerbildern,
Walking06 als Holdout, ca.93min; drei Review-Bilder danach ca.14min. Finale
LoRA-SHA256: `3d014d02897b05bada80f2b72c7f3574bb26faa14b8dbc08f70284f7d1d8b282`.
Originale/Alpha/Captions/Quellhashes im Dataset, Rezepte in assets/character.
Aktuelle Walking-Downloads unterscheiden sich vom installierten Spielpaket;
kein stiller Austausch. Abgelehntes Meshy-Modell/A-Pose nicht mittrainiert.

**Hardware tatsächlich erfasst:** RyzenAI9HX370,12Kerne/24Threads, Radeon890M
(gfx1150),32GiB installiert,8GiB Grafikreservierung. ROCm meldet ca.16,9GiB
nutzbaren GPU-Speicher; GPU-Renderpeak10,53GiB. Dynamische Speichernutzung klappt;
keine BIOS-, Windows-Energieplan- oder Treiberänderung vorgenommen. NPU wird vom
PyTorch-LoRA-Ablauf nicht genutzt, kein bloßes Addieren von CPU/GPU/NPU-TOPS.

**CPU-Umgebung:** artwork-local/lora-runtime, Torch2.14.1+cpu.
**Neue GPU-Umgebung:** artwork-local/lora-rocm-runtime, Torch2.14.0+rocm10.1.0,
AMD-gfx1150/115x-Gerätepakete, Diffusers0.41.0/Transformers5.20.2/PEFT0.21.2.
Offizieller AMD-Paketindex, Python3.13.16. Das frühere Argument fehlender
Windows-Unterstützung galt für den damals geprüften7.2.1-Pfad; aktuelles10.1
führt890M/gfx1150. Native GPU-Ausführung funktioniert mit installiertem Treiber.

**Echte Nachweise:** GPU-Conv/SDPA-BF16-Gradienten gültig, danach zwei volle
SDXL-LoRA-Updates aus CPU-Checkpoint600 in `gpu-training-check-2026-10-22`.
Schritt60170,96s (Aufwärmen),6021,34s, beide endliche Gradienten und Loss,
Checkpoint602 gespeichert. CPU zuvor6–11s/Update. Keine Langzeit- oder
bitgleiche A/B-Benchmarkbehauptung aus nur einem warmen GPU-Schritt ableiten.

Einzelner GPU-Poseversuch mit stärkerem ControlNet1,25 bis zum Schluss.
Erster Versuch scheiterte nach28Denoise-Schritten bei FP32-VAE-SDPA mit
hipErrorProfilerNotInitialized. `render_sdxl_trial.py` verwendet nur im ROCm-VAE
nun gewöhnliche GPU-Matrix-Attention; BF16-UNet/ControlNet bleiben optimiert.
Korrigierter Lauf vollständig fertig: `review-gpu-2026-10-22-fixed/arm-forward.png`,
109,32s inklusive erster VAE-Vorbereitung, derselbe600er-Adapter. Gescheiterter
Ordner ohne fertiges Bild bleibt als Diagnose; nicht als Ergebnis verwenden.

**Bilder wirklich angesehen:** Gemalter Schwarz-Gold-Look erkennbar, klar näher
an Nutzerbildern als abgelehntes Meshy-Modell. Details/Proportionen nicht völlig
stabil. Ursprünglicher waagerechter Arm hing herunter; verstärkte GPU-Probe zeigt
Arm nach vorn, aber Ellenbogen noch gebeugt. Kein perfektes Pose-Following oder
fertige Spielanimation behaupten. Alpha/Ursprung/Handpunkt/native Zuordnung
weiter offen. Aktive9HD-Posen und Spiel-/Save-Dateien unverändert.

**Werkzeuge:** tools/prepare_character_lora.py sowie tools/lora. Trainer heißt
jetzt `train_sdxl.py` (CPU/ROCm), `compute.py` wählt auto/cpu/cuda und standardmäßig
alle24CPU-Threads; cuda bedeutet hier AMD-HIP. RDNA3.5-Attention-Flag
TORCH_ROCM_AOTRITON_ENABLE_EXPERIMENTAL=1 pro Prozess, mit0 übersteuerbar.
Vollständige Installations-Freezes im Pilotordner, direkte CPU-/GPU-Pins unter
requirements.txt/requirements-rocm.txt. Fortsetzen verwendet normale Priorität.
Eigene Adapter/Optimizer/RNG-Checkpoints, keine fremden Pickles laden.

Bedienung/Dateien/Quellen und Beispiele: [LOCAL_LORA.md](LOCAL_LORA.md),
Alltagshinweise MERKHILFE.md. `Status.cmd` zeigt ursprünglichen fertigen Auftrag.
Nicht nochmals600Schritte starten, nur weil eine alte Statusaufnahme training
sagt. Neuere Statusdateien lesen. Kein GPU-Neutraining zur bloßen Wiederholung.

Backup unter `D:/Super Castlevania IV Recomp/backup/hd-artwork/2026-10-21-local-lora`:
Originale/Dataset, Werkzeuge, Modelquellen, fertiger600er-Checkpoint und Review-
Bilder werden gesichert, mit SHA256-Manifest. Basismodelle/Venv nicht duplizieren.
Nur notwendige Syntax-/Abhängigkeits-/Kernel- und echte Integrationsprüfungen;
keine Game-Neubuilds oder breiten Testreihen für diese Werkzeug-Ergänzung.

## Vorherige Rückmeldung zum 3D-Pilot

Nutzer: „das 3d Modell sieht zu schlecht aus, leider“. Der erzeugte Meshy-Körper
ist damit qualitativ als Sprite-Ersatz abgelehnt. Nicht ins Spiel übernehmen
oder weitere Animationen auf diesem Modell ausarbeiten. Dateien und Blender
bleiben erhalten. Diese Rückmeldung widerlegt nicht grundsätzlich jeden
3D-Produktionsweg; unser konkreter KI-Modellversuch hat den gewünschten Look
nicht erreicht. Ein 2D-Rig war danach vorgeschlagen, aber noch nicht erstellt.
Der Nutzer hat stattdessen den oben beschriebenen LoRA-Versuch gewählt.

## Historisch: abgelehnter Simon-Modellversuch mit Skelett und PNG-Export

Nutzer hat den Meshy/Blender-Piloten und gegebenenfalls die Blender-Installation
beauftragt, Meshy selbst angemeldet und den Browser-Dateizugriff aktiviert.
Offizielle Portable-Version **Blender4.5.14LTS** unter
`C:/Users/Gaming/AppData/Local/Programs/Blender-4.5.14/blender.exe`; offizieller
SHA-256-Abgleich und gültige Blender-Foundation-Signatur geprüft. Startmenülink
**Blender4.5LTS**. Keine bestehende Installation gefunden, keine Systemänderung mit Adminrechten.

**Echter Pilot:** `artwork-local/blender-pilot-2026-10-21/` enthält Referenz,
Meshy-GLBs, `.blend`-Projekte und gerenderte Bilder. Eine neutrale A-Pose mit dem
eingebauten Imagegen aus der letzten Idle-Nutzervorlage erzeugt, Prompt in
`reference/prompt.txt`. Keine Einzelbild-KI-Animationsreihe. Meshy6Lite-Modell10Credits,
Bildtextur10Credits; Check-in automatisch+30, Schlussstand110. Erster Rigging-Versuch
gratis; zweiter für Farbversion hinter Abo-Sperre. Keine Zahlung oder Subscription.
Vier reguläre Downloads innerhalb des freien Kontingents; Free-Lizenz im WebCCBY4.0.

`tools/blender/sprite_pilot.py` nutzt deshalb lokal das vorhandene Rig und
überträgt Gewichte auf das heruntergeladene Farbmesh desselben Körpers; UVs/PBR
bleiben erhalten. **66.815Vertices**, nächster maximaler Positionsabstand nach
Ruhehöhen-/Zentrenabgleich **8,68e-7der Körperhöhe**; Geometrieabweichungen>0,005
werden abgelehnt. glTF-generierter Icosphere als Knochen-Widget wird aus der
Körpergeometrie ausgeschlossen. Unpassender erster Versuch in`walk-v1` brach
kontrolliert ab; finale Ausgabe ist`walk-final`, frühere Arbeitsausgaben nicht benutzen.

**Hauptdatei:** `walk-final/Simon_Pilot.blend`, gepackte Bilder, drei Actions
**Walking, Running, Attack**,36Knochen. Shortcut`Simon-Pilot.lnk` im Pilotordner.
Leeres vorbereitbares Studio separat`studio/Simon_Exportstudio.blend` mit eigenem
Shortcut. Feste orthografische Seitenkamera, +Xrechts,960×960RGBA,10×,49native
Körperhöhe, Ursprung48/48, Bodenziel77,35. Normalisierung nur aus Ruhepose, keine
Neuskalierung je Bild. PNG-Sampling kompensiert horizontale Hips-Bewegung;
unbearbeitete Blender-Actions bleiben in ihrer ursprünglichen Bewegung.

**Anschaubares Ergebnis:** sechsWalking-Bilder und dreiAttack-Bilder.
`walk-preview/Vorschau.html`, `attack-preview/Vorschau.html`: Einzelschritt,
Abspielen, Vorschauzeit. Jeweils`Animation.webp` lossless mit gemeinsamem
Ausschnitt (340×520bzw.340×550); echte gekürzte PNGs plus`placement.json`
mit unverändertem Pixelmaß/Offset. `tools/blender/package_preview.py` rundet
nur transparente Ränder nach außen auf10px. Alle Renderings bei10×, typische
reine Renderzeit nach Initialisierung ca.0,5s/Bild lautLogs.

**Grenzen:** echter, konsistenter3D-Look, sichtbar plastischer/glatter als die
gemalten Bilder. Attack ist eine Überkopf-Bibliotheksbewegung, noch kein nativer
Peitschenschlag. Sechs gleichmäßig gesampelteWalking-Bilder sind noch nicht
mit nativen Laufphasen abgeglichen. Nicht ins aktive9-Posen-Paket eingebaut;
Spiel-EXEs, ausgewählte Pakete, Einstellungen, Saves und Marker unverändert.
Keine Gameplay-/Leistungs-Testmatrix. Gezielter tatsächlicher Import/Render,
PNG-/Alpha-/Rand-/Metadatenprüfung und Sichtkontrolle durchgeführt. Die
Browserrichtlinie blockiert`file:`-URLs; deshalb keine automatisierte HTML-UI-Prüfung
oder Umgehung per lokalem Server. Nutzer kann die HTML-Dateien selbst öffnen.
Meshy-Ergebnis im Browser als Nachweis gesichert und gezeigt.

Reproduzierbare Befehle und technische Details:
`docs/SPRITE_PIPELINE_NOTES.md`. Bedienung in leichter Sprache:`MERKHILFE.md`.
Lokale Quellen/Ergebnisse extern unter
`D:/Super Castlevania IV Recomp/backup/hd-artwork/2026-10-21-blender-pilot` sichern;
nur Werkzeuge/Dokumentation auf`dev` veröffentlichen. Nächster sinnvoller Schritt:
Nutzer beurteilt den Look. Bei Zustimmung Laufphasen und native Peitschen-Handpunkte
im Rig anpassen, danach getrenntes spielbares Probepaket erstellen. Kein weiterer
Meshy-Rig oder Abo ohne konkrete Freigabe.

## Aktuell: anderen Produktionsweg für viele animierte HD-Figuren recherchiert

Nutzer möchte keine Einzelbild-Prompts mit Anweisungen für jedes Körperteil mehr. Auftrag war eine eigenständige Software-/KI-Recherche während seiner Abwesenheit, keine neue Bildgenerierung. Hauptempfehlung als noch zu bestätigender Pilot: Meshy → wiederverwendbare 3D-Bewegungen → Blender → transparente2D-PNGs. Für den bisherigen gemalten Look Alternative Spine Professional mit einmalig vorbereiteten Bildteilen. Weitere bewertete Kandidaten: Cartoon Animator5, Wan Animate2 als Bewegungsübertragung aus Video, PixelLab mit256×256-Grenze, Mixamo, Cascadeur und Synfig. Herstellerquellen, Export-/Tarifgrenzen und die Trennung von gesicherten Funktionen und eigener Einschätzung stehen in `SPRITE_ANIMATION.md` in einfacher Sprache. Technischer Anschlussplan in `docs/SPRITE_PIPELINE_NOTES.md`; Merkhilfe verlinkt die Empfehlung.

**Noch kein Qualitätsnachweis an unseren Figuren:** keine Bild-/Video-KI gestartet, keine Modelle oder Programme installiert, keine Käufe/Uploads. Radeon890M/24GB RAM lokal erkannt; keine belastbare Aussage zur lokalen Inferenzgeschwindigkeit. Vorgeschlagener nächster Schritt: kleiner Simon-Pilot mit Laufzyklus und wenigen Peitschenposen, danach Wiederverwendung auf einer zweiten Figur bewerten. Ein fertiger 3D-Clip darf die native Spielbewegung nicht doppeln; Hand-/Peitschenabgleich und Pose-Sampling bleiben nötig. Gegner-Rendering ist durch diese Recherche nicht bereits erweitert.

**Vorbereiteter Bedarf:** `tools/character_pose_inventory.py` liest nur Manifeste und schreibtCSV/JSON in einen neuen Ordner. Auf dem aktuellen nativen Simon-Template83 Einträge →77 volle Körper-Hashes,6 weitere Alias-IDs,9 Gruppen mit HD,68 erfasste Gruppen ohne HD. Kein vollständiger Spielkatalog und keine Animationsreihenfolge. Ausgabe `artwork-local/animation-research-2026-10-21/simon-inventory/`. Keine Gameplay-Tests/Builds für die Recherche. Externe Sicherung unter `D:/Super Castlevania IV Recomp/backup/hd-artwork/2026-10-21-animation-research`; Dokumentation und Werkzeug auf `dev` pushen.

## Aktuell: Lauf-Flackern behoben, Einzelbildmodus

**Ursache nachgewiesen:** Im längeren Laufzyklus erscheinen bei identischen normalisierten Körperpixeln zusätzliche Metasprite-IDs: `9e0c-e4c4686f3649c330` (Walking-05) und `9bb9-1168be4736083938` (Walking-06). Das Neun-Posen-Paket enthielt jeweils nur den anderen Präfix. Bei exakter ID-Suche fielen dadurch einzelne Felder auf Originalgrafik zurück. Aufnahme mit alter EXE: `build-lua/walk-flash-q3zrbvde/frames.json`,23 inaktive Felder einschließlich eines ersten OAM-Felds direkt nach Snapshot-Laden.

**Fix:** `character_pack.cpp::findBodyFrame` bevorzugt die exakte ID; fehlt sie, wird nur ein eindeutiger Treffer des vollständigen normalisierten Körper-Hashes verwendet. Der ursprüngliche strenge Abgleich aller OAM-Bestandteile bleibt Voraussetzung. Kein Festhalten des vorherigen HD-Bildes, keine Ähnlichkeitssuche. Bei mehreren möglichen Hash-Zuordnungen bleibt der native Fallback erhalten. Artwork und die neun Manifest-Einträge bleiben unverändert.

**Einzelbildmodus:** Strg+P pausiert ungedimmt beziehungsweise setzt fort; Strg+N fordert genau ein Videofeld an und bleibt anschließend stehen. Beide Befehle sind unter Shortcuts sichtbar, sofort änderbar und werden in `[KeyMap] FrameInspection`/`FrameAdvance` gespeichert. OS-Tastenwiederholung wird ignoriert. Einstieg auch über Escape → Performance → Inspect frames. Verschiebbares, einklappbares ImGui-Fenster mit Bildnummer, Next frame und Resume; tatsächliche Spieltasten/Pad können beim Schritt gehalten werden. Audio bleibt pausiert, nach jedem Schritt wird seine Warteschlange geleert. Run-ahead, Turbo-Auslassung und Frame-Blending werden während der Inspektion umgangen; Normaltempo bleibt unverändert. Lokaler Modus, im Netplay nicht zugelassen. Lua-Diagnose `game.command("frameinspect", "on|off|step")` beziehungsweise leeres Argument liefert Modus und Host-Bildnummer.

**Gezielt geprüft:** `tools/test_walking_frame_inspection.py` mit Release-Lua → `build-lua/walking-inspection-s7or72yl`:600 Lauf-Felder rechts/links, beide Alias-IDs aktiv in HD; sämtliche benannten Zustände identisch mit der Aufnahme vor dem Fix. Nur das erste OAM-Aufbaufeld direkt nach dem Laden ist aus dem Sichtbarkeitsvergleich ausgenommen. Zwölf Einzelbildschritte jeweils exakt+1, dazwischen eingefroren. Native Konfigurationsprüfung `build-audit/frame-inspection-config-test.exe`: neue Standardtasten, Live-Neubelegung und Persistenz bestanden. Echter SDL-Tastentest `inspection-input-b440176j`: Strg+P, Strg+N und ignorierte OS-Wiederholung bestanden. Tatsächliche ImGui-Klicks → `build-lua/inspection-ui-ib1e8__n`: Next frame exakt ein Feld, Resume beendet Modus. Aktivierung nur durch `SNESRECOMP_FRAME_INSPECTION_UI_SELFTEST=1`. Bedienleiste im Screenshot visuell geprüft. Release mit und ohne Lua gebaut; keine Skalen-/Performance-/Gesamtregressionsmatrix.

**Installation:** aktuelle EXEs in `build/` und `build-play/game/`; Nutzer muss für diese Codeänderung das Spiel neu starten. Pack-Auswahl, PNGs, Einstellungen, Saves und Marker werden durch die Installation nicht verändert. Arbeitsnachweise und vorherige Haupt-EXE unter `artwork-local/walking-flash-2026-10-21/`, externe Sicherung unter `D:/Super Castlevania IV Recomp/backup/hd-artwork/2026-10-21-walking-flash-frame-inspection`. Bedienung in `MERKHILFE.md`. Framework `7d57b7eaf2edb7282530c7d9b7350a9a421175f3` auf eigenem `gast114/sciv` veröffentlicht und Pin aktualisiert; Root-dev zum Abschluss pushen.

## Aktuell: sechs HD-Laufphasen

Die sechs Nutzerbilder `C:/Users/Gaming/Downloads/Walking-01_HD_10x.png` bis `Walking-06_HD_10x.png` sind bytegleich übernommen. Das vorhandene Paket `simon-user-hd-three-poses-v1` heißt im Manifest jetzt **Simon HD (9 poses)**; Ordnername und Auswahl bleiben erhalten. Installiert in `build-play/game/characters/`, `build/characters/` und im lokalen Quellpaket `artwork-local/characters/`. Die bisherigen drei PNGs und ihre Frame-Einträge sind unverändert. Kein EXE-Build nötig; Bilder und Manifest werden live neu geladen. Angriffe und weitere fehlende Posen bleiben nativ.

Zuordnung folgt dem tatsächlich aufgenommenen normalen Laufzyklus, nicht einer bloßen Ähnlichkeit der ausgeschnittenen SD-Referenzen. Die vorhandenen SD-Dateien `Walking-02.png` und `Walking-06.png` sind identisch und die Vorlagen enthalten Treppenposen; sie ergeben allein keine eindeutige Laufzuordnung. Native Aufnahme: `build-lua/walk-import-uu2v_q25/walk.json` und dessen `characters/simon-template/`.

| HD-Bild | Körper-Fingerprint | PNG-Maße | Zelloffset | display_size |
| --- | --- | --- | --- | --- |
| Walking-01 | `9bb9-65478f912fca6458` | 200×460 | [37,28] | [22,50] |
| Walking-02 | `9bb9-c577013b20a5dd10` | 230×450 | [32,24] | [29,56] |
| Walking-03 | `9bb9-d131e28d720d7423` | 200×460 | [36,29] | [22,51] |
| Walking-04 | `9bb9-81bf240d752d172d` | 250×460 | [34,27] | [29,53] |
| Walking-05 | `9bb9-e4c4686f3649c330` | 240×460 | [33,25] | [28,53] |
| Walking-06 | `9e0c-1168be4736083938` | 230×450 | [34,28] | [26,51] |

Native Vorschauzellen3…8 ergänzt; Anker und Handpunkt aus der Aufnahme übernommen. Unterschiedliche transparente Ränder werden über `hd.offset` und `hd.display_size` ausgeglichen, ohne die Nutzer-PNGs zu ändern. Optische Höhe an die vorhandene Standfigur angepasst; opaker Fußpunkt aller sechs Bilder innerhalb0,34 nativer Pixel um deren Fußpunkt. Native Animation, Spiegelung und Physik bleiben erhalten.

**Gezielte Prüfung:** `build-lua/walk-hd-ofjkqusx`,120 Frames (60 rechts,60 links), alle sechs Phasen in beiden Richtungen aktiv; über98% der opaken HD-Pixel stimmen mit der erwarteten Darstellung überein. Sämtliche benannten Gameplay-Zustände identisch mit der nativen Aufnahme. Ein Prüfbild visuell angesehen. Die erste Aufnahme beim Richtungswechsel zeigt nativ noch nach rechts; der Prüfvergleich berücksichtigt diese OAM-Verzögerung. Keine Skalierungs- oder Regressionstestmatrix. `tools/test_character_hd.py` bleibt ein Test für eine Drei-Posen-Probe und erwartet fehlende Laufposen; nicht unverändert gegen dieses erweiterte Paket ausführen.

**Ablage und Sicherung:** `artwork-local/simon-hd-walking-2026-10-21/` enthält Paket, Importplan/Checksummen, gezieltes Prüfskript, Prüfbilder und Installationsbericht. Vorherige Pakete unter `user-before/`. Externe Kopie: `D:/Super Castlevania IV Recomp/backup/hd-artwork/2026-10-21-simon-hd-walking`. Artwork bleibt lokal; Dokumentation auf `dev` committen und pushen. Bedienhinweise und alle neun austauschbaren Dateinamen stehen in `MERKHILFE.md`.

Die folgenden Abschnitte beschreiben frühere Arbeitsstände. Hinweise auf nur drei HD-Posen beziehungsweise native Laufposen gelten dort historisch.

## PNG-Austausch vom21.10.

Die drei vom Nutzer verbesserten `Idle-01_HD_10x_240x460.png`, `Ducking-01_HD_10x_230x350.png`, `Jumping-01_HD_10x_200x450.png` sind bytegleich aus `../Assets (ausgeschnitten)/Simon Belmont/` in beide aktiven `characters/simon-user-hd-three-poses-v1/`-Ordner und das lokale Quellpaket unter `artwork-local/characters/` übernommen. `character.json` bleibt unverändert: letzte Vergrößerung/Fußpunktkorrektur erhalten. Import-Checksummen aktualisiert. Alte Dateien und Manifeste unter `artwork-local/simon-hd-refresh-2026-10-21/`, extern `D:\Super Castlevania IV Recomp\backup\hd-artwork\2026-10-21-simon-hd-refresh`. Nur Maße und Kopierergebnis geprüft; kein Build, kein Gameplay-/Skalierungstest.

**Selbst austauschen:** Nutzer startet normalerweise `build-play/game/SuperCastlevaniaIvSNESRecomp.exe`; seine aktiven PNGs liegen in `build-play/game/characters/simon-user-hd-three-poses-v1/`. Dieselben drei Dateinamen, PNG mit Transparenz und dieselben Pixelmaße verwenden. Laufendes Spiel lädt Änderungen ungefähr alle30 Frames neu; bei Bedarf Escape → Character workshop → Reload. `body.png`/`character.json` für einen reinen Bildaustausch unverändert lassen. `build/characters/simon-user-hd-three-poses-v1/` gehört zur alternativen EXE unter `build/`; die Ordner synchronisieren sich nicht automatisch. Neue Posen brauchen zusätzlich eine Zuordnung im Manifest.

## Aktuell: Idle / Ducking / Jumping in echtem10×

**Letzte Nutzerkorrektur, vor Session-Ende:** Probe wirkte zu klein/schwebend. Nur die Darstellung angepasst: Idle26×50 bei Zelloffset[35,28], Ducking25×38 bei[36,28], Jumping22×49 bei[39,26]. `hd.display_size` skaliert im Loader aus unveränderten PNGs; Stand-/Duck-Fußpunkt2 native Pixel tiefer. Keine Physikänderung. Nach dieser kleinen Korrektur auf ausdrücklichen Wunsch nur gebaut, keine weitere Testmatrix; visuelle Freigabe durch Nutzer noch offen. Laufende alte EXE wurde zum Austausch umbenannt; neue Darstellung und10×-Menü nach Spielneustart.

Nutzer möchte seine sechs gelieferten PNGs probeweise integrieren und das Format weiterer Figurenbilder wissen. Keine Bildgenerierung oder Bearbeitung seiner Originaldateien. Paket **`characters/simon-user-hd-three-poses-v1`** in `build/` und `build-play/game/` installiert und ausgewählt. Vorherige Auswahl (`custom-1` in `build/`) sowie sämtliche Figuren, Saves, Marker, Tastenkürzel, HD- und CPU-Einstellungen gesichert unter `artwork-local/simon-hd-three-poses-v1/user-before/`; bestehende Dateien bis auf die ausdrücklich gewählte neue Figur hashgleich erhalten. Gameplay-Werte der vorherigen Figur und der Probe identisch. Landschaft bleibt `stage-01-user-v4-final`,10×; Performance-Standard weiterhin Boost.

**Neue Nutzerpräferenz:**2×/4×/6× sind uninteressant und aus dem HD-Menü entfernt. Nutzeroberfläche bietet Original oder10×-HD; beim Öffnen des HD-Panels wird eine ältere niedrigere Auswahl auf10× gesetzt. Interne Diagnoseparameter bleiben für Entwickler verfügbar. Keine unnötigen tokenintensiven Tests/erneuten Matrizen: nur gezielte notwendige Prüfungen. Nach dieser späten kleinen Menüänderung ausschließlich gebaut, keine weiteren Testläufe. Bisherige unten aufgeführte Skalierungsprüfungen fanden vor dieser Anweisung statt.

- **Steuerung:** Strg+H schaltet diese HD-Posen mit der Landschaft zurück auf Original. Escape → Character workshop → Use character pack deaktiviert nur die Figurenprobe. Der Character-Chooser bietet die Probe und vorherige eigene Figuren. HD-Sprites-Kategorie muss eingeschaltet sein. Laufen, Angriffe und sämtliche nicht gelieferten Posen bleiben nativ; das sichtbare Wechseln zwischen SD und HD ist bei dieser Teilprobe beabsichtigt.
- **Zuordnung:** kompletter normalisierter Körper-Fingerprint des vorhandenen Figurenimports, nicht einzelne wiederverwendete Simon-Tiles. Idle `9bb9-40b103a1bbf51ab0`, Ducking `9c25-f15281d7dda728b7`, Jumping `9c25-7e85729b52a75b82`. Native 96×96-Zelloffsets `[36,30]`, `[37,29]`, `[40,29]`. Originale Bildgrößen240×460,230×350,200×450 bleiben unverändert. Blickrichtung wird automatisch gespiegelt. OAM-Vollabgleich erhält Sichtbarkeit/Blinken und native Animation/Position/Spielmechanik.
- **Importformat:** bestehendes Character-Manifest Version1 bleibt kompatibel; optionales `hd` pro Frame enthält `image`, `scale:10`, `offset:[x,y]` in nativen Zellkoordinaten. Separate PNGs statt eines riesigen 10×-Gesamtbogens. `body.png` bleibt die native Vorschau zur Verankerung; HD-Pixel liegen unverändert in den einzelnen Dateien. Menü-Speichern erhält HD-Metadaten. PNGs werden wie das Manifest live neu geladen; unvollständige Dateien behalten das letzte gültige Paket.
- **Renderer:** native OBJ-Abdeckung dient nur als kleine Prioritäts-/Fenster-Probe. Der HD-Compositor liest anschließend die unveränderten hochauflösenden RGBA-Daten vor Transparenz/Farbmathematik. Keine Verkleinerung des eigentlichen HD-Artworks auf Originalauflösung. Immutable Kopien beider Spiegelachsen und Pack-Revision schützen die Wiederverwendung; keine Frame-für-Frame-Bilddateien. Samplingdichte pro Bild erlaubt unterschiedliche Dichten von Landschaft und Figur. Auch der sichtbare OBJ-Pfad über dem HUD kann HD-Figurdaten lesen.
- **Weitere Bilder:** genau wie geliefert: je Originalpose SD-PNG plus transparentes HD-PNG mit zehnfacher Breite und Höhe; Pixelmaße statt DPI sind entscheidend. Dieselbe Figur, Proportionen, Farben, Beleuchtung und Orientierung über die Animation hinweg. Gliedmaßen/Haare/Schuhe vollständig im Bild; transparente Ränder erhalten. Rechtsansicht genügt. Technische Zuordnung/Verankerung und mehrfach vorkommende Posen übernimmt der Import. Als nächstes einen vollständigen Laufzyklus, danach weitere komplette Bewegungs-/Angriffsgruppen; keine KI-Zwischenbilder automatisch erfinden.

**Werkzeuge und Nachweise:** `tools/import_character_hd.py --template build-play/game/characters/simon-template --source "../Assets (ausgeschnitten)/Simon Belmont" --out artwork-local/characters/simon-user-hd-three-poses-v1`; Ziel muss neu sein. `import.json` hält Fingerprints, Offset, Originalpfad und SHA-256 fest. Native Alphaabweichung zu den heruntergeladenen SD-Referenzen Idle1 / Ducking3 / Jumping0 Pixel; eindeutige Zuordnung zu aufgenommenen Spielposen. `tools/test_character_hd.py` mit tatsächlicher Spieler-EXE → `build-play/game/character-hd-lhvd5dcq`: alle sechs Ansichten, über98% opake Bildpixel exakt,2/4/6/10×, Zustandsidentität, Original-/Sprites-Schalter, fehlende Laufposen, Hot-Reload und Recovery nach unvollständigem PNG bestanden. Erster visueller Lauf `build-lua/character-hd-4wwr28id`, Skalierungslauf `character-hd-jg_r8fto`.

**Regressionen:** bisheriger SD-Figurenimport `build-lua/character-test-of1qd5x9`:20 Posen,401 unveränderte Bilder bitgleich, Live-Reload erfolgreich. Szene/Steine/Wasser/Mode7 `build-lua/hd-scene-check-f8bymhmg`; Legacy-/Kontext-/Alpha-/Reload-Regression `build-lua/hd-live-check-z5xbrnjz`, beide grün. Release ohne Lua und Release mit Lua gebaut. Profiler unterstützt `--character <Paket>` in einer isolierten Sitzung; mit Probe und HD-Landschaft10×:60,08FPS,179/179 Logikupdates, keine Wiederholungen (`build-lua/fps-profile-clywyfm8`,240 Frames,61…240 ausgewertet). Keine Garantie für ungetestete Posen/Orte; keine vollständige Simon-Animation geliefert.

**Ablage:** Quellen, Paket, Installationsnachweis und Prüfbilder unter `artwork-local/simon-hd-three-poses-v1/`; extern SHA-256-geprüft unter `D:\Super Castlevania IV Recomp\backup\hd-artwork\2026-10-20-simon-hd-three-poses-v1`. Quellcode/Tests/Übergabe auf `dev` committen und pushen; Artwork/Saves bleiben lokal. Framework-Pin unverändert `6839cf0`.

## Aktueller Fix: ursprüngliche Slowdowns reduzieren, HD-Arbeit wiederverwenden

Nutzer hat ausdrücklich die Umsetzung beauftragt, einschließlich Installation, Commit auf `dev` und Push. Keine Bildgenerierung; Nutzerbilder und Paket `stage-01-user-v4-final` bleiben unverändert bei 10×. Beide Spielerinstallationen sind `build/` (Release ohne Lua) und `build-play/game/` (Release mit Lua).

- **Escape → Performance → SNES slowdown reduction** bietet **Original SNES**, **FastROM**, **FastROM + CPU boost**. Standard ist der dritte Eintrag. Auswahl wird neben der jeweiligen EXE in `performance_settings.json` als `cpu_timing: 0/1/2` gespeichert, gilt ab dem nächsten Frame und bleibt beim Laden eines Savestates erhalten. Fehlende Datei →2; ungültige Datei →0. Keine ROM-Patches oder Änderungen an Nutzersaves.
- **FastROM und Boost sind getrennt:** Modus1 beschleunigt CPU-ROM-Zugriffe über die vom Spiel verwendeten LoROM-Spiegel auf6 Masterzyklen; WRAM bleibt8. Modus2 setzt diese CPU-ROM- und WRAM-Zugriffe auf4 und Interpreter-internes Rechnen auf3 statt6. MMIO, Joypad, SRAM, DMA und die Videofrequenz bleiben unverändert. Politik gilt ausschließlich im Spielmodus4; andere Framework-Spiele optieren nicht automatisch ein. AOT-Blockkonstanten bleiben konservativ. Das ist ein Host-Gegenstück zum FastROM-Prinzip mit zusätzlicher optionaler CPU-Beschleunigung, kein unverändert übernommener Retail-ROM-Hack.
- **Kein globaler Turbo:**357368 Masterzyklen pro NTSC-Feld und 60,0988Hz bleiben erhalten; `DisableFrameDelay=0` in beiden Spieler-Konfigurationen. In unbelasteten Szenen sind benannte Zustände und native Bilder Original/Boost identisch. Der Boost entfernt die durch CPU-Überlast ausgelassenen Updates, statt grundsätzlich mehr Updates pro Videofeld zu erzeugen.
- **Gegner-/Todestests:**24 künstlich platzierte native Medusaköpfe: Original89/179, FastROM89/179, Boost179/179 Logikupdates. Zwölf Köpfe gleichzeitig in nativen Todeszustand gesetzt: Original172/179, Boost179/179, bis30 native Fragmente. FastROM allein reicht für diese künstliche Extremlast nicht. Originalzustände und Erzeugungsmethode bleiben unter `artwork-local/performance-2026-10-20/` erhalten.
- **HD-Komposition:** unveränderte Zellen werden anhand ihrer vollständigen Sampling-/Farbzustände wiederverwendet; bei einem sicher opaken Gewinner zählt nur dessen sichtbarer Kandidat. Pack-Neuladen, Maß-/Skalenwechsel, HUD-/Fallback-Zeilen und Szenenwechsel invalidieren die betroffenen Einträge. Kleinere Farbdaten statt ungenutzter Samplingdaten pro Zelle; zusammenhängender Bildtransfer. Außerhalb gelieferter Landschaften prüfen reine Shared-OBJ-Szenen zunächst nur Objekt-Provenienz: ohne passenden HD-Schlüssel direkt das native Pixel erhalten, BG-Provenienz erst bei einem Treffer holen. Keine Auflösungs- oder Qualitätsreduktion.
- **HD-Threads:** neuer Standard bis16 Teilnehmer, durch vorhandene CPUs begrenzt; `SNESRECOMP_RENDER_WORKERS` überschreibt dies für Diagnosen. Nach der Wiederverwendung wurde die Matrix erneut gemessen:8→57,59,12→57,53,16→59,89,24→59,90 FPS im normal getakteten Brückentest. Mehr Threads allein waren vor der Optimierung nicht ausreichend.

**Abschließende Leistungsmessung auf dem Nutzer-PC, jeweils300 Frames,61…300 ausgewertet:** Original60,08FPS; HD10× Brücke60,04FPS;24 Gegner Original60,08FPS / HD10×60,09FPS;12 gleichzeitige native Todesanimationen mit bis30 Fragmenten, HD10× und Audioausgabe60,10FPS. Alle stabilen Läufe239/239 Logikupdates, keine Wiederholungen. Ungedrosselte HD-Brücke84,71FPS als Rechenreserve, nicht als Spieltempo; vor dem Fix50,45FPS. Raster/HD-Kosten dort12,88→6,17ms, Bildkopie1,82→1,13ms. Release-Lua,16 Teilnehmer, VSync aus; Audio nur im Todeslauf an (WASAPI-Gerät und Callback im Log bestätigt). Bericht `artwork-local/performance-fix-2026-10-20/summary.json` und vollständige Roh-CSV/Logs je Lauf.

**Bewegung und Grenzen:** Brücke mit gehaltenem Right,180 Frames: stabile Gameplay-Intervalle60,11FPS,94/94 Logikupdates. Gesamtmittel einschließlich Raumladen42,77FPS, zuvor mit Originalgrafik ebenfalls42,79FPS. Ladephasen werden ausdrücklich von stabilen Gameplay-Intervallen unterschieden: der native Decoder darf bei deaktiviertem NMI bis16 Feldbudgets beanspruchen. Das ist weiter bestehende Ladezeit, kein Beleg für60FPS während jedes Übergangs. Keine Zusage für sämtliche ungetesteten Räume oder andere PCs.

**Regressionen bestanden:** Framework-Interpreter186/186; `test_cpu_performance.py` → `build-lua/cpu-performance-oft1sgas` (Buskosten/Gegner/Tod/unbelastete Identität); `test_hd_scene.py` → `build-lua/hd-scene-check-6g51rzor` (2/4/10×, Wasser/Ufer/alle Steinphasen, Shared-OBJ-Fallback außerhalb der Landschaft, Mode7); Effekte → `hd-effects-tbx1nd8d` (genauen Bericht siehe lokale Testlogs); Route elf Prüfpunkte → `build-lua/hd-route-x4nspsid`; Legacy-/Kontext-/Fallback-/Reload-Test → `build-lua/hd-live-check-lwiskxax`.175 vollständige HD-RGB-Prüfsummen, native Bilder und Zustände mit/ohne Wiederverwendung identisch; zuletzt mit der installierten EXE unter `build-play/game/`. Menütests auf Release ohne Lua: `build/performance-ui-nr3f8cr_` (alle drei Modi, Neustart, kleine Fenster) und `build/hd-ui-check-sk2b6aky` (HD-Klick/Persistenz/Marker). Installierter Übergangstest uild-play/game/hd-transitions-ns5j1e4t: Original59,97 / HD60,01FPS, echter Abschnittswechsel und weitere Bewegung. Abschließende Installationslogs unter `build-audit/performance-installed-*.log`; Nachweise dauerhaft im Performance-Fix-Ordner gesichert.

**Werkzeuge:** `test_cpu_performance.py`, `test_hd_reuse.py`, `test_performance_ui.py`; Profiler jetzt mit `--cpu-timing 0/1/2`, `--audio`, `--buttons Right` und standardmäßig16 HD-Threads. Weiterhin isolierte Ordner über `sciv_play.py`/`sciv_test_support.py`, keine Tests im eigentlichen Spielerprofil. `hdhash` liefert einen diagnostischen RGB-Checksum des vollständigen HD-Bildes, ohne PNG-Schreibkosten bei jedem Vergleich.

**Sicherung dieser Arbeit:** `artwork-local/performance-fix-2026-10-20/user-session-at-install/` enthält die vorherigen EXEs, Konfigurationen, Saves und Marker beider Startordner. Installation prüft alle Saves, Marker, Tastenkürzel, `config.ini` und `hd_settings.json` per SHA-256 unverändert; neue bewusste Einstellung ausschließlich `cpu_timing=2`. Installationsbericht `install.json` im selben Arbeitsordner. Artwork/Pakete und F5-Reparatur des vorherigen Auftrags bleiben erhalten.

**Git:** Framework `6839cf07583da84983c5eb4980819235cf43f1cd` auf eigenem `gast114/sciv` veröffentlicht, `framework_pins.txt` aktualisiert, lokales Bare-Backup nachgezogen. Root `dev` enthält Implementierung, Tests und Dokumentation; Push auf `origin/dev` gehört zum Abschluss. Fremde Remotes bleiben gegen Push gesperrt. Keine ROMs, generierten ROM-Dateien, Saves oder HD-Quellen committen.

Die folgenden Abschnitte dokumentieren frühere Diagnose- und Implementierungsstände; offene Performancearbeit dort ist durch den aktuellen Abschnitt teilweise erledigt.

## Vorherige Diagnose: FPS und Gegnerlast (20.10., historisch)

**Zwei getrennte Bremsen nachgewiesen; Spielcode/EXEs/Tempo/HD-Qualität bei dieser Prüfung unverändert.** Aktuell installierter Spielstand bleibt `6a8c318` mit Framework `a6d6920`. Neues Diagnosewerkzeug `tools/profile_sciv_fps.py` vergleicht PC-Zeit mit dem nativen Logikzähler WRAM `$3A`; `$3C` allein ist kein zuverlässiger Lag-Nachweis.

- **HD-Kosten auf dem PC:** Brücke F4, ausschließlich stabile Phase5, Hostframes61…300, ungebremster Diagnoselauf: Original237,56 FPS / HD10×50,45 FPS. Mittlere Zeiten: Spiellogik3,49ms, Raster/HD-Komposition12,88ms, Kopie des HD-Bildes1,82ms, Upload/Present1,48ms. Für60 FPS stehen16,64ms zur Verfügung. Hauptengpass ist der CPU-Compositor (`GatherSceneLine`/`RenderRows`), nicht die Begrenzung der SNES-Simulation. 3420×2240 =7,66 Mio. Pixel pro Bild; Alphakomposition, Mode7, native Sichtbarkeit/Farbmathematik und vollständiger Bildtransfer kosten Zeit. HD6×67,39 FPS als Diagnose; Qualität nicht automatisch reduziert. Zusätzliche Threads reichen nicht: 4→37,90, 8→50,45, 12→49,11, 16→51,55, 24→53,71 FPS (einzelne Läufe, keine garantierten Leistungswerte).
- **SNES-Zeitbudget bei Gegnern:** In isolierter Kopie 0/4/12/24 Medusaköpfe erzeugt. Vorlage wurde durch den echten nativen Auto-Spawner des Raums (Block6) erstellt, dann freie Actorslots kopiert; waagerechte Geschwindigkeit0 hält sie für die Messung im Bild. Health/AI/vertikale Bewegung bleiben nativ. Kein Schreibzugriff auf Nutzersaves oder ROM. Bis12 Gegner keine ausgelassenen Logikupdates. Bei24 Gegnern **~60 ausgegebene Bilder/s, aber nur~30 Logikupdates/s**, auch mit HD aus. Im Messfenster90 Wiederholungen in179 Gameplay-Intervallen. PC hat im ungebremsten Originaltest trotzdem~235 FPS Reserve.
- **Todesanimationen separat provoziert:** Zur Diagnose native Medusa-Todeszustände entsprechend Retailtabellen `$01:AE07/AE87` (ID7/State2, HP/Hitstun/Hitbox auf0) gesetzt. Der Spielcode erzeugt daraus selbst bis30 Fragmente; keine gemalten/gefälschten Effekte. Bei12 Gegnern ohne Tod0, mit diesen Todesanimationen7 ausgelassene Logikupdates. Bei24 Gegnern sind komplette native Bilder und sämtliche aufgezeichneten Logik-/Actor-Daten Original/HD bytegleich; FPS-Kosten und SNES-Slowdown dadurch getrennt. Dies ist ein synthetischer Stresstest, keine exakte Rekonstruktion der ungespeicherten Nutzerstelle und kein Vergleich mit echter SNES-Hardware.
- **Ursache im Code:** `src/game_rtl.c:GameRunOneFrame` behält357368 Masterzyklen pro NTSC-Feld. Der originale NMI `$00:81B8` führt bei gesetztem `$3C` nur seinen Lag-Zweig `$84C8` aus. Der hybride Recomp hebt dieses Zeitbudget nicht automatisch auf. Gleiche Wallclock-FPS bedeuten daher nicht immer gleich viele Spielupdates. Eine globale Turbo-/FPS-Erhöhung wäre keine passende Reparatur der ursprünglichen Slowdowns.

**Nächste technische Arbeit:** Zuerst HD-Kosten in Zeilenabfrage/Komposition und Bildkopie senken, statische Arbeit unter korrekter Invalidation wiederverwenden; bei Bedarf GPU-Komposition. Separat eine optionale CPU-Budget-/Slowdown-Reduktion untersuchen, bei unveränderter60,0988-Hz-Videotaktung und validiertem NMI/IRQ/HDMA/APU-Verhalten. Noch keine solche Overclock-Funktion eingebaut.

**Nachweise:** `artwork-local/performance-2026-10-20/summary.json`, unveränderte Roh-CSV/Logs/Bilder je Lauf unter `runs/`, vier synthetische Fixtures unter `fixtures/`. Aufbau der Stresszustände in `make_stress.py` (benötigt isolierte `sciv_play`-Sitzung), Tod-/Skalierungs-/Worker-Matrix in `stress_probe.py`/`probe.py`. Basismatrix-Brückenwerte in `summary.json` schließt die nach Frame313 beginnende Raumtransition ausdrücklich aus. Rechner: Ryzen AI9 HX370, 12 Kerne/24 Threads, Radeon890M; Release-Lua-Build, VSync/Audio aus. SHA-256-geprüft extern gesichert: `D:\Super Castlevania IV Recomp\backup\hd-artwork\2026-10-20-performance`.

**Werkzeug verifiziert:** ungebremster HD-Todeslauf `build-lua/fps-profile-aahaeykg` (30 Fragmente), normal getakteter Native-Stresslauf `build-lua/fps-profile-06p6cfou` (~60,14 FPS, 89 Logikupdates/179 Intervalle). Keine laufende Testsitzung hinterlassen. Neuer Profiler sammelt Daten im Speicher und schreibt beim normalen Ende; Default ist Originalgeschwindigkeit, `--unthrottled` ausschließlich Messreserve.


Antworten auf Deutsch. Nutzer liefert sämtliche Bilder selbst; keine Bildgenerierung. Aktueller Auftrag umfasst ausdrücklich Commit auf `dev` und Push aller Änderungen.

**Aktuell installiert:** `stage-01-user-v4-final`, 10×, in **beiden** Startordnern `build/hd_packs/` und `build-play/game/hd_packs/`. `build/` ist wieder ausdrücklich Release ohne Lua (sein CMake-Cache stand zwischenzeitlich auf Debug); `build-play/game/` enthält den aktuellen Release mit Lua. F4=`saves/save3.sav`, F5=`saves/save4.sav`. Beide Konfigurationen haben jetzt `DisableFrameDelay = 0` für Originalgeschwindigkeit.

**Behoben und geprüft:**
- **Brückenkette:** 21 statt 11 registrierte Originalschlüssel aus zusätzlicher VRAM/OAM-Aufnahme; neuer Ausschnitt x125…337/y0…161 schließt den Ansatz ein, ohne die separaten zerbrechenden Steine einzufangen. Kein neues Artwork. Kette wird auch über dem HUD per sichtbarem OBJ-Tilepfad ersetzt; native HUD-Schrift/Balken bleiben exakt erhalten. Kettensegmentkanten und native Rasterkonturen bleiben sichtbar.
- **Kurzes Originalbild am Tor:** HD ist für alle Levelphasen in Spielmodus4 freigegeben. Registrierte Szene bleibt durch `native_maps: [16384,18432]` (BG1/BG2) geschützt. In Übergangsphase6 darf das ausgehende Bild trotz bereits erhöhtem Block weiterhin HD erhalten; der neu geladene Raum bekommt dadurch keine falsche Landschaft. PPU-Modi1/7 geprüft, kein pauschaler Ersatz aller SNES-Effekte. Räume ohne gelieferte HD-Grafiken bleiben nativ.
- **Treppe F5:** Tatsächlicher Wechsel **Block5 → Block6**, nächster Raum lädt, Phase5 und weitere Bewegung nachgewiesen. Kein Festhalten Simons am oberen Rand. Ursache war der frühere Widescreen-Objektpatch: links wurde der Lebensbereich versehentlich kleiner. Retail `[-96,+352)` war falsch zu `[-48,+448)` geworden; jetzt korrekt `[-144,+400)`. Guarded Patches bei ROM-Datei `$498B` (`SBC #$0090`) und `$4991` (`ADC #$0220`), Originalbytes weiterhin geprüft. Rückwärts geladener Ausgang darf nicht sofort wieder verschwinden; Laufzeitregression prüft seine Lebensdauer am linken Rand.
- **F5 war bereits beschädigt:** Der native Ausgangsactor Typ `$15` fehlte schon im gespeicherten Zustand. Nur diesen Slot unter `build-play/game/saves/save4.sav` einmalig repariert: Kopie des Originals geladen, Forward-Eventcursor WRAM `$94` von `$8404` auf den fehlenden nativen Datensatz `$05:83E0` gesetzt, einen Frame durch den nativen Parser ausgeführt und vor dem Übergang gespeichert. Genau ein nativer Ausgang entsteht; Originalverhalten übernimmt den Abschnittswechsel. Kein allgemeiner Cursor-Rescan, kein Actor-/Treppen-Hack im Spielcode. Original F5 bleibt in `artwork-local/stage01-user-v4/fixtures/F5.sav` und im Installationsbackup; reparierte Fixture `F5-recovered.sav`.
- **Geschwindigkeit:** Spieler-Konfiguration `build-play/game/config.ini` hatte durch den bisherigen Testordner `DisableFrameDelay=1` (ungebremst). Jetzt 0; neue CLI-Testläufe landen in eindeutigen `build-play/sessions/session-*`, verändern keine Spielersaves/-Konfiguration. Escape → Emulation → **Original game speed (NTSC)** ist sichtbar und persistent. Ziel ist native SNES-NTSC-Taktung 60.098811862 Hz, unabhängig vom HD-Schalter. Nach Render-Überläufen entfällt außerdem die unnötige zusätzliche volle Frame-Wartezeit; alte Zeitrückstände werden nicht nachgeholt. Uhrtests prüfen langsame Frames, lange Pausen, PAL/NTSC und Präsentationsraten.
- **Performance-Grenze offen:** Letzter Test der tatsächlich installierten EXE: Original **59,99 FPS**, HD-Brücke **48,23 FPS** über je180 Frames. Vor der Wartezeitkorrektur lag dieselbe lange HD-Probe bei etwa30 FPS. **Stabile 60 FPS mit HD sind noch nicht erreicht**; bei Überlast läuft die Simulation weiterhin langsamer. Kein schnellerer Spielablauf als Original im normalen Modus. Weitere HD-Performancearbeit bleibt nötig.
- **Debug-Aufnahmen:** Beide Nutzermarker `2026-10-20_12-34-56_level` und `2026-10-20_12-38-16_level` existieren unverändert unter `build-play/game/debug_markers/`. Neue Aufnahmen werden atomar in einen frischen Ordner geschrieben; gleiche Sekunde/Szene erhält `_1`, `_2`, … . Regression belegt, dass vorhandene Notizen nicht überschrieben werden. Strg+D aufnehmen, Strg+Enter speichern; Strg+H HD/Original.

**Installation und Sicherung:** `artwork-local/stage01-user-v4/user-session-at-install/{build,build-play-game}` enthält ursprüngliche Konfigurationen, alle Saves, Marker, Keybindings und HD-Einstellungen unmittelbar vor Installation. Alle Marker, Keybindings und sonstigen Saves hashgleich erhalten. Beabsichtigte Änderungen: EXE/Paketauswahl, Geschwindigkeitsflag 0 sowie ausschließlich F5 im tatsächlichen Spielerordner. Installationsnachweis `review/install.json`. Externe SHA-256-Sicherung unter `D:\Super Castlevania IV Recomp\backup\hd-artwork\2026-10-20-stage01-transitions`.

**Quellen:** weiterhin 29 unveränderte Bilder und Basisschlüssel unter `artwork-local/stage01-user-v3/`; neue Aufnahme/Original-Fixtures/repariertes F5 unter `stage01-user-v4/`. Aktuelles Rezept `assets/hd/stage_01.recipe.json`, 62 Schlüsselbilder (Mond4, Fledermäuse6, Wasser15, Kette21, Steine16), 13 Dateiregionen/11 Laufzeitregionen. Zusätzlicher Neubauparameter `--video artwork-local/stage01-user-v4/chain-video.bin`, siehe `HD_PIPELINE.md`. Quellen/Paket/Prüfberichte bleiben absichtlich lokal und gitignored.

**Regressionen grün:**
- `test_hd_transitions.py`: `build-lua/hd-transitions-tugks5y8`; zusätzlich mit Kopie der tatsächlich installierten Spieler-EXE/Paket/F5: `build-play/game/hd-transitions-7ao4o0qq`. HUD-Identität, obere Kette, ausgehende Brücke/kein Landschaftsleck, Native/HD-Spielzustände und Bilder gleich, Ausgangs-Lebensdauer, echter Abschnittswechsel und weitere Bewegung, normale Taktung.
- PPU-Test; `test_hd_scene.py` → `build-lua/hd-scene-check-n6qs42ej` (alle Steinphasen, Wasser/Transparenz/Ufer/Originalstrich/linke Erweiterung/Brückenrotation); `test_hd_effects.py` → `build-lua/hd-effects-02jlvcxy` (Upgrade/Tod).
- `test_hd_render.py` → `build-lua/hd-live-check-ha_carqg`; Route mit elf Prüfpunkten → `build-lua/hd-route-oohqe6tf`; HD-Menü-Klick/Persistenz/Marker → `build/hd-ui-check-1vaadyje`; Shortcuts → `build/shortcut-ui-x6j0ojqg`; Marker-Kollisionen → `build/marker-check-fkafwb7s`; Startup RunAhead0/1 → `build/startup-check-x7m_8zt5`.
- `test_sciv_play_session.py`: eindeutige Schnell-/Normal-Testordner; Spielerdaten hashgleich. Framework-C-Tests `config_roundtrip_test` einschließlich Geschwindigkeitsflag und `host_clock_test` einschließlich 20ms-Renderbudget bestanden. Vollständiger Spiel-CRC-Lauf nicht durchgeführt.

**Git:** Rootbranch `dev`; Frameworkbranch `sciv`, neuer Commit `a6d6920ffb75de19dd66c45e9b28241f891a2c47`, Pin aktualisiert. UI unverändert `af0f8b9`. Framework-Push ausdrücklich über `gast114/sciv` im eigenen Fork; fremdes Framework-`origin` nun gegen Push gesperrt. Root `origin/dev` im eigenen Konto; kein Force-Push. Lokales Bare-Backup des Frameworks ist aktualisiert. Keine ROMs, generierten ROM-Dateien oder Spielerdaten committen.

## Vorheriger Stand: HD-Politur (20.10.; folgende Angaben sind historisch)

Antworten auf Deutsch. Nutzer erstellt sämtliche Grafiken selbst; keine weitere Bildgenerierung oder Promptpakete. Codex importiert fertige Bilder und prüft die Darstellung.

**Installiert:** `stage-01-user-v3-water-final`, HD an, 10×, sowohl `build/hd_packs/` als auch **`build-play/game/hd_packs/`**. Der Nutzer startete tatsächlich die EXE unter `build-play/game` mit einem alten Prototyp-Paket. Auch diese EXE ist jetzt aktualisiert (Lua-Build); `build/` enthält den Release ohne Lua. Spielersaves, `config.ini` und `keybinds.ini` per Hash unverändert. Nur die Paketauswahl in `hd_settings.json` wurde aktualisiert. Sicherung unmittelbar vor Installation: `artwork-local/stage01-user-v3/user-session-at-install`.

**Umsetzung abgeschlossen; Veröffentlichung auf `origin/dev`:**
- Vier gelieferte `STEIN_STUFE_1..4_HD_200x170.png` ersetzen die früheren Original-Rissmasken. Ein gemeinsamer Satz für alle passenden nativen OBJ-Schlüssel `$A0/A2/A4/A6`, Base `$6000`, Palette240; 16 Atlas-Tiles. Seitenverhältnis erhalten: 200×170 →160×136, oben in einem 160×160-Canvas. Keine hochgerechneten Details, Originaldateien unverändert. Bewegung/Timing/Fallen/Verschwinden weiterhin nativ, keine statischen Doppelbilder. Native OBJ-Rasterkonturen bleiben eine Grenze.
- Peitschen-Upgrade und Tod waren keine fehlenden Bilder: HD war nur in Phase5 erlaubt. Jetzt auch Level-Anzeigephasen 3/4/6/10/12 bei Modus4 und passendem Block. F1-Repro ist **`saves/save0.sav`**, nicht save1! Unveränderte Kopie: `artwork-local/stage01-user-v3/fixtures/whip/state.sav`. Upgrade Phase10 und Tod Phase12 geprüft; native Bilder und benannte Spielzustände Original/HD identisch.
- Gemeinsame Steine nutzen auch außerhalb des Landschaftsblocks die Alpha-Komposition vor der Sichtbarkeit. Zeilenkopie speichert `regionsActive`; Worker lesen keine laufende WRAM. Außerhalb der Szene nur exakte gemeinsame OBJ-Schlüssel, keine Landschaftslecks.
- Wasser nach neuester Nutzerpräzisierung: **Ufer vor Wasser; Felsen im See hinter transparentem Wasser**. Felsregion erhält Priorität `$7000`, Wasser `$7100`; native Main/Subscreen-Farbmathematik liefert die Transparenz. Test färbt Wasser und Felsen unabhängig um: beide tragen unter der Wasserlinie bei, Ufer bleibt durch Wasserfärbung unverändert.
- Nativer Erdstrich auf Bildzeile191: Darstellungskorrektur für Block0/Mode1, Zeile192, BG1-Map`$4000`/BG2-Map`$4800`, VScroll1023 und obige Anzeigephasen. Brüchige Gleichheitsbedingung der HScrolls entfernt. V0 nur während dieser Zeile, anschließend sofort restauriert; keine Simulation-/VRAM-/HDMA-Änderung. Wirkt bei HD aus. Der alte tatsächlich gestartete Build enthielt diese Korrektur noch nicht.
- **Strg+H** schaltet HD/Original. **Escape → Shortcuts** zeigt alle Host-Tastenkürzel, einschließlich aller 20 Lade-/Speicherslots; per Klick erfassen, Konflikte anzeigen, löschen, sofort anwenden und gezielt in `[KeyMap]` speichern. Menübindung lässt sich ändern und über `Default` auf Escape zurücksetzen; sie wird nicht ersatzlos gelöscht. Pad-Gesten für Debug/Rewind separat auswählbar und persistent. Spieletasten weiterhin im Controller-Menü.
- **Debug-Screenshot mit Problembeschreibung: Strg+D / Select+L3**, speichern mit **Strg+Enter / A**, verwerfen mit Esc/B. Ablage neben der gestarteten EXE: beim Nutzer derzeit `build-play/game/debug_markers/`.
- Große Navigationsbuttons (38px), eigener 72px-Arbeitsbereich, Inhalte darunter. Resize-Rand 20→6px; während Modalmenüs HitTest normal statt Resize/Ctrl-Drag. Kleine Fenster öffnen das Menü vorübergehend mindestens 800×600; beim Schließen alte Größe wiederherstellen, sofern Fensterstufe/Vollbild nicht bewusst geändert wurden.

**Quellen/Prüfung:** 29 unveränderte Dateien unter `artwork-local/stage01-user-v3/source`, `source-checksums.json`; Rezept `assets/hd/stage_01.recipe.json`, Paket `artwork-local/packs/stage-01-user-v3-water-final`: 52 Tile-Bilder, 13 Dateiregionen/11 Laufzeitregionen. Aufbau ist selbstständig mit `stage01-user-v3/pilot-keys`, `capture`, `water-video.bin`; Neubau liefert alle Paketdateien bytegleich. Prüfberichte und Screenshots dauerhaft in `artwork-local/stage01-user-v3/review`.

Grün: PPU-Test; `test_hd_scene.py` (`build-lua/hd-scene-check-jud4d1ri`, einschließlich Transparenz/Ufer/alle Steinphasen/Randeintritt/Brückenrotation); `test_hd_effects.py` (`build-lua/hd-effects-6hdop_dk`, F1-Upgrade/Tod); `test_hd_render.py` (`build-lua/hd-live-check-dt2pfclm`); Route mit elf nativen Prüfpunkten (`build-lua/hd-route-n31ss8ni`); Release-HD-Menü-Klick/Persistenz/Marker (`build/hd-ui-check-6_qmvtx8`); Startup RunAhead0/1 (`build/startup-check-grdmmqvr`); Config-C-Roundtrip einschließlich opt-in Defaults/Rebinding/Slot-Erhalt. Shortcuts: echter ImGui-Klick, SDL-Erfassung, Konflikt/Abbruch/Löschen, Neustart und Unterdrückung von Key-Repeat (`build-lua/shortcut-ui-9m8uvqr1`; abschließender Release-Lauf unter `build/shortcut-ui-4x9mqg_3`). Kein vollständiger Spiel-CRC-Test.

**Git:** Root `dev` veröffentlicht auf `origin/dev` im eigenen Repository `https://github.com/Gast114/SuperCastlevaniaIvSNESRecomp`. Implementierung `5a76b92`; nachfolgender Publikationscommit aktualisiert `.gitmodules` und diese Übergabe. HTTPS-Anmeldung für Git als Gast114 eingerichtet, `origin` wieder zum Push freigegeben; fremdes `upstream` bleibt gesperrt. Beide nötigen Forks im Nutzerkonto angelegt und zuerst veröffentlicht: Framework `https://github.com/Gast114/snesrecomp-sciv`, Branch `sciv`, Commit `1b779c7fa0574f7d1172282da508b21beccd53e2`; UI `https://github.com/Gast114/recomp-ui`, Branch `codex/sciv-menu-work-area`, Commit `af0f8b916ff661d9461040adb8233f23c646b995`. `.gitmodules` zeigt auf diese Forks/Branches, Pins unverändert. Bare-Sicherungen beider Submodule unter `D:\Super Castlevania IV Recomp\backup\snesrecomp-sciv.git` und `recomp-ui-sciv.git`. Nutzer hat ausdrücklich den Push aller Änderungen beauftragt; frühere Nur-lokal-Vorgabe aufgehoben. ROM, generierter ROM-Code, Spielersaves und lokale HD-Pakete/Artwork bleiben gemäß `.gitignore` lokal.

**Restpunkte:** Weitere Landschaften und Figuren benötigen Nutzerbilder; Kette/Fledermäuse behalten native Rasterkonturen, Kettensegmentkanten bleiben sichtbar. Kein allgemeiner HD-Ersatz aller SNES-Effekte. Weitere Bilder weiterhin manuell vom Nutzer.

Quellen, Paket, Fixtures, Nutzer-Save-Sicherung und Review per SHA-256 gesichert unter `D:\Super Castlevania IV Recomp\backup\hd-artwork\2026-10-20-stage01-polish`. Alle Paketdateien inklusive Receipt im Neubau bytegleich; Prüfmanifest `review/rebuild.json`.

RAM-Map / Spielmodi: `D:\Reverse Engineering\docs\sc4\analysis.md`.

## Regeln des Nutzers
- Aktuelle Anweisung (20.10.): Änderungen am Ende pushen. Frühere Nur-lokal-Vorgabe aufgehoben; `origin` und eigene Framework-Forks sind eingerichtet. Fremdes `upstream` bleibt gesperrt. ROM und generierter Code nie ins Repo.
- Installieren/Git ohne Nachfrage erlaubt. Laufendes Spiel darf geschlossen werden.
- Ergänzungen im Spiel müssen **nativ** aussehen (Spielschrift, Tilemap, echter Cursor), keine Overlays.
- Fehlt im Widescreen-Rand Bildinhalt, wird er **selbst gestaltet** (aus den Tiles der Szene), nicht abgeschnitten oder mit Fremdinhalt gelassen.
- Kennzeichnen, was verifiziert (gebaut/ausgeführt/gelesen) vs. Vermutung ist. Token sparen, Qualität halten.
- Klarstellung des Nutzers: **NEW GAME+ bedeutet den originalen schwereren zweiten Durchgang nach dem Durchspielen** (wie START 2), nicht den Sandbox-Raum. Umsetzung noch offen, Bedeutung bereits geklärt.
- Wiederkehrende Tiles sollen **einmal** als HD-Quelle entstehen und wiederverwendet werden, auch über Level hinweg. Keine erneute KI-Generierung pro Vorkommen.
- Artwork künftig als zusammenhängende Motive/Ebenen extern vom Nutzer erstellen lassen. Technisches Zerlegen/Wiederverwenden bleibt Codex-Aufgabe; keine handwerkliche Tile-Zuordnung vom Nutzer verlangen. Nutzerbeispiel bestimmt Stil, Originalvorlage Geometrie. Bestehenden Pilot als historischen Versuch behandeln.

## Git
- Arbeitsbranch `dev` (lokal): … 633733b Widescreen-Ränder · aac6d65 natives NEW GAME+ · c81539d Handoff · **57b62dc Savestate-Ausführungszustand** · **6570042 Debug-Marker** · (+ Handoff-Commit).
- Framework `snesrecomp` = lokaler Branch `sciv` (RetroPortingToolKit main a6be975 + 2 Rasmus-Commits + a4e0d83 Lua-Host). **Veröffentlicht im eigenen Fork**, lokal in `.git/modules/snesrecomp`; Spiegel-Backup: `D:\Super Castlevania IV Recomp\backup\snesrecomp-sciv.git` (nach Framework-Commits mit `git -C <backup> fetch` aktualisieren). `recomp-ui` = af0f8b9 (Work-Area). Pins in `framework_pins.txt`. Framework aktuell **1b779c7** (HD-/Menü-Hotkeys, Modal-HitTest, Menü-Mindestgröße), davor **47b75a8** (read-only BG/OBJ-Zeilenkandidaten inkl. transparenter Flächen/Mode 7), davor **1cd41e1** (BG-Nachbarschaftsabfrage für HD-Motive), davor **d837790** (HD-Provenienz + Presenter-Hooks) und **9cd151c** (Debug-Marker). Pin und lokales Spiegel-Backup sind aktualisiert.
- Identität repo-lokal: `Gast114 <Gast114@users.noreply.github.com>`.

## Builds (alle gitignored)
| Ordner | Zweck |
|---|---|
| `build-play/game/` | tatsächlich vom Nutzer gestartete EXE; aktualisiert, F1=`saves/save0.sav` |
| `build/` | Nutzer-Build, **Release** (seine `config.ini`, `characters/`, `saves/`, `debug_markers/`); Release inklusive Szenen-HD vom 20.10. neu gebaut |
| `build-dev/` | Release für Tests |
| `build-lua/` | `-DSNESRECOMP_ENABLE_LUA=ON` für `tools/sciv_play.py` |
| `build-diag/` | `-DSNESRECOMP_ENABLE_PPU_DMA_HISTORY=ON` |
| `build-audit/` | Wegwerf-Ausgaben |

Neu konfigurieren: `cmake -S . -B <dir> -G Ninja -DCMAKE_BUILD_TYPE=Release -DSNESRECOMP_SDL3_SOURCE_DIR="<repo>/build/_deps/sdl3-src"` (kein Download).
Toolchain: retcomm clang 22/CMake/Ninja im PATH; Python 3.15 + Pillow; Rust (`/c/Users/Gaming/.cargo/bin` in Bash-PATH aufnehmen); nativer Analyzer gebaut (`snesrecomp/recompiler-rs/target/release/snesrecomp-analyze.exe`).

## Debug-Marker (vom Nutzer gesetzte Problemstellen – zuerst ansehen!)
- Im Spiel **Strg+D** bzw. Pad **Select+L3** (`config.ini [KeyMap] DebugMarker`, `[Controller] DebugGesture`): Spiel friert ein, Notizfenster; Strg+Enter/A speichert, Esc/B verwirft.
- Ablage: `build/debug_markers/<Datum>_<Uhrzeit>_<Szene>/` mit `note.md` (Beschreibung), `marker.json` (Szene, Frame, Modus/Block/Kamera/Spieler, PPU-Ebenen), `screen.png` (Bild inkl. Ränder), `state.sav`, `video.bin` (VRAM+CGRAM+OAM, für `render_map.py`), `wram.bin`. Neue Marker zusätzlich `lines.bin` (225×32 Byte Zeilenregister für die HD-Vorschau); bei HD auch `hd_screen.png` und Einstellungen unter `marker.json.hd`.
- Auswerten: `python tools/debug_markers.py` (Liste, neueste zuerst), `... show <id-Präfix>`; nachstellen: `sciv_play.py start --build-dir build-lua --widescreen --fast` → `sciv_play.py loadfile build/debug_markers/<id>/state.sav` → `layers`/`shot`/`dump`/`press`.
- Code: `src/debug_marker.cpp` (Aufnahme + ImGui-Panel), `src/debug_capture.c` (gemeinsam mit Lua-Befehlen), Framework-Hooks in `host_main.c` (`RunDebugMarkerLoop`). Selbsttest: `SNESRECOMP_DEBUG_MARKER_AT=<frame>` + `_NOTE=<text>` oder `_TYPE=<text>` (tippt über SDL-Ereignisse).

## Werkzeuge
- **HD:** [HD_PIPELINE.md](HD_PIPELINE.md). Escape → HD graphics → **HD graphics enabled** schaltet live Original/HD um; unabhängige Backgrounds/Text/Sprites-Schalter, Paketauswahl und 2×/4×/6×/10×. Sammlung separat: Collect graphics while playing. Nach regulärem Beenden `python tools/hd/hd_pipeline.py --build build` (Real-ESRGAN) bzw. `--method nearest` (Identitätsprüfung). Ergebnis `build/hd_pack/`, Vorschau im neuesten Marker mit `lines.bin`. **Szenenpaket mit voller Alpha-Komposition; ältere Tile-/Kontextpakete behalten native Silhouetten.**
- **Grafikquellen des Nutzers:** 33 PNG-Bögen in `C:\Users\Gaming\Downloads\assets`; `python tools/hd/hd_sources.py` schreibt den Katalog nach `build/hd_work/source_sheets.json`. Originale unverändert, noch kein automatischer Sheet-Import. Stage-9-Hintergrundbogen fehlt in diesem Ordner.
- Tests: `python tools/test_<name>.py --rom "Super Castlevania IV (USA).sfc" --build-dir build-dev` (startup, campaign2, character_pack, character_stairs, character_tuning, debug_marker, hd_pipeline – alle sieben am 18.10. erneut grün). Neu: `test_hd_ppu.py` ohne ROM, `test_hd_render.py` mit `--build-dir build-lua`, `test_hd_ui.py` mit `--pack build/hd_pack`; ebenfalls grün.
- Spielsteuerung: `tools/sciv_play.py start --build-dir build-lua --widescreen --fast`, dann `press Right 30`, `wait N`, `state`, `ppu` (jetzt mit Tile-Basis `tiles`), `shot x.png`, `save/load N`, `loadfile <state.sav>`, `reset`, `peek/poke` (peek beliebig lang), `eval`, `stop`. Neu: `lines f.bin` (225 Zeilenregister), `dump f.bin` (VRAM+CGRAM+OAM roh), `layers 0x02` (Ebenenfilter für folgende Shots, ohne Argument = alle).
  - Ablauf ohne Savestate: Boot → `wait 300` → `press Start 3` (Titel) → `press Start 3` (Bestätigung) → `wait 200` → `press Start 3` (Name überspringen) → `wait 300` = Tor-Sequenz → `wait 430` = Block 1-1.
- RE: `tools/re/dis65.py <rom> BB:AAAA [n] [m] [x]`; `tools/re/render_map.py dump.bin out.png --map 0x1000 --tiles 0x2000 --wide --tall --grid --scale 2` (ganze BG-Map mit Spaltennummern – zum Gestalten von Rändern); `tools/re/run_mesen.ps1`, `mesen_column_trace.lua`, `contact_sheet.py`.
- 4:3-Bitgleichheit (P16) prüfen: gleiche `.input` headless mit altem und neuem Build, `SNESRECOMP_PRESENT_LOG=<csv>` schreibt CRC32 pro Bild → Frames vergleichen.
- Headless: `SNESRECOMP_RUN_FRAMES`, `SNESRECOMP_SCREENSHOT(_FRAME)`, `SNESRECOMP_SCREENSHOT_DIR/FROM/TO`, `SNESRECOMP_LAYER_MASK`, `--script <file>.input`.

## Historie (18.–19.10.; aktueller Stand und Auftrag stehen oben)
- **Gemeinsame Mauer-/Treppenquellen (19.10., nach e17add4):**
  - Auswählbar: Escape → HD graphics → Graphics pack **`hd_packs/pilot-1-1-shared-v5`**, HD an, 10×. Das frühere `pilot-1-1-painted-v2` bleibt als Vergleich. Zwischenstände aus dem Menü ins lokale Artwork-Archiv verschoben. Keine C++-Änderung, daher kein Neubau erforderlich; Spielersaves/Downloads/Konfiguration unverändert.
  - Fünf mit eingebautem Imagegen erzeugte Bögen ergeben **47 ungespiegelte 80×80-Quellen**. Originalauflösung 256–887 Pixel pro Zelle, heruntergerechnet, nicht hochskaliert. Versioniertes Rezept samt Prompts/Referenzen: `assets/hd/shared_blocks_1_1.recipe.json`; ausgewählte Originalausgaben unter `artwork-local/shared-blocks-v1/generated/`, extrahierte Quellen unter `artwork-local/library/shared/`. Historische Entwürfe bleiben erhalten.
  - `tools/hd/hd_shared.py extract` prüft Raster, echte Mindestauflösung, native Referenzorientierung und optionale vollständige Deckkraft. Native Alpha-Maske wird erst beim Import angewendet. Frühe halbtransparente Materialien mischten im Live-Renderer unerwünscht Originalpixel dazu; finale Quellen sind innerhalb der nativen Silhouette vollständig deckend. Keine neue Konturkomposition.
  - `hd_shared.py pack` registriert gemeinsame Quellen in BG-Aufnahmen ausgewählter Szene/Ebene; andere Motive des Basispakets bleiben erhalten. **2.361 aufgezeichnete Verwendungen, 659 unterschiedliche Nachbarschaften → 375 gleichwertige Regeln**, insgesamt 255 gespeicherte Bilder inklusive alter Felsmotive. Eine neue Quelldatei plus Neubau aktualisiert alle ihre Referenzen. Zählung betrifft Aufnahmen, keine eindeutigen Weltpositionen; unbekannte Nachbarschaften fallen weiter auf Original zurück.
  - Rechte Mauer war durch Aufnahmegrenze unvollständig registriert. Neue Aufnahme `artwork-local/captures/upper-stairs` (Kamera 177) ergänzt `captures/pilot`; alle 1.618 erfassten Tile-Vorkommen pixelgenau gegen ihren Originalschlüssel geprüft. Fixture `fixtures/block-1-1-upper-stairs/state.sav` entsteht nach dem Schritt `upper-stairs` der versionierten Strecke, Aufnahme acht Frames später in frischem Prozess mit `SNESRECOMP_HD_COLLECT=1`. Frischer Prozess nötig, weil der Sammler ausreichend häufig gesehene Schlüssel nicht ständig erneut aufnimmt. Zentraler Katalog jetzt **2.958 Originalschlüssel / 48.354 Vorkommen / 1.985 Palettenfamilien / 47 HD-Quellen**.
  - Tests grün: `test_hd_shared.py` (Referenz, Alpha, Mindestauflösung, Spiegelungen, Mehrfachverwendung, Szenenfilter, Basiserhalt, Änderungen, Regeln-Vereinfachung), `test_hd_motifs.py`, `test_hd_catalog.py`, `test_sciv_state.py`. Live-Renderer-Regression `build-lua/hd-live-check-vy_7avrt`, Log `build-audit/hd-shared-render.log`. Finale Route `build-lua/hd-route-97ggqvpb`: elf native Bild-/Zustandsprüfpunkte Original/HD/Original identisch; alle elf HD-Bilder zusätzlich vor/nach Regelvereinfachung bytegleich. Finaler Nutzer-Build-Klicktest `build/hd-ui-check-j_sgk__c`: an/aus, Neustart-Persistenz, Marker grün.
  - `sciv_play.py`-Messung ohne weitere Spieltests, Kamera146, 240 ungedrosselte Frames, 10×: ca. **58 FPS** nach Vereinfachung, ca.56 davor. Mehr HD-Abdeckung kostet Leistung; stabile 60 FPS noch nicht nachgewiesen. Bericht/Bilder dauerhaft unter `artwork-local/shared-blocks-v1/review/v5/`, insbesondere `performance-isolated.json`, `route-report.json`, `compaction-check.json`.
  - SHA-256-geprüftes Quellen-/Paket-Backup: `D:\Super Castlevania IV Recomp\backup\hd-artwork\2026-10-19-shared-blocks`. Manifest `artwork-local/library-checksums.json`; Bilddateien bleiben gitignored. Reproduzierbare Import-/Paketbefehle in `HD_PIPELINE.md`.
  - **Nächster Schritt:** sichtbare Steinmaßstab-/Nahtwechsel und rote Treppen-/Reliefstruktur gestalterisch überarbeiten (aktuell eher Materialstudie), fehlende Boden-/Randbausteine und BG2 ergänzen. Dabei vorhandene Schlüssel wiederverwenden, neue Nachbarschaften registrieren. Danach glatte Live-Konturen, Simon-Bewegungssatz/Gegner und Performance weiter bearbeiten. Nicht als fertigen 4K-Level verkaufen.
- **HD-Wiederverwendung und reproduzierbare Strecke (19.10., nach 8ad4d15):**
  - `tools/hd/hd_catalog.py` katalogisiert Originalschlüssel über Aufnahmen hinweg, gruppiert Palettenfamilien ohne sie zu verschmelzen und erzeugt `shared_tiles.json`. Lokaler Katalog `artwork-local/library/`: **2.944 Originaltiles, 46.736 aufgezeichnete Vorkommen, 1.971 Palettenfamilien**. Keine Weltpositionszählung; noch keine freigegebenen HD-Quellen unter `shared/`.
  - `hd_motifs.py`: Rezept kann eine gemeinsame `shared_library` oder einzelne `shared_tiles` referenzieren. Eine ungespiegelte 80×80-Quelle versorgt alle registrierten Vorkommen ihres Originalschlüssels; Nachbarschaftsprüfungen bleiben aktiv. Identische RGBA-Bilder belegen nur eine PNG/Atlasposition. Abweichende Motivvarianten bleiben separat; Änderungen der Quelle erfordern Paket-Neubau. Mindestauflösung, Alpha-Grenzen und Schreibschutz unverändert.
  - Bestehenden Materialpilot aus dauerhaften Quellen unter `artwork-local/packs/pilot-reuse-v1` neu gebaut: alle **312 Platzierungen samt Nachbarn und Pixeln identisch** zum installierten v2. Keine künstliche Zusammenlegung der 312 unterschiedlichen Bilder; Nutzerpaket bleibt unverändert.
  - `assets/hd/block_1_1.route.json` + `test_hd_route.py`: elf Prüfpunkte, echter linker Rand, Treppe auf/ab, Sprung/Landung und Peitsche. Treppe explizit nachgewiesen (`player_state=11`, Y=131/83), Abstieg endet geduckt (177), Sprung 126, Landung 165. Original/HD/Original nach gleichem State: native Bilder und benannte Zustände an allen Punkten identisch. Bericht: `build-lua/hd-route-8j7__f7n/report.json`, dauerhafte Kopie `artwork-local/verification/block-1-1.report.json`. Nur Checkpoints, noch kein interaktiver Eingaberecorder/Frame-für-Frame-CRC-Test.
  - `sciv_play.py` korrigiert: Lua-Bridge liefert maximal 16 Werte, bisher fehlte `player_state` hinter Frame + 16 Feldern stillschweigend. Liest jetzt in begrenzten Blöcken und lehnt unvollständige Antworten ab.
  - `test_hd_contours.py`: Offline-Beweis für glattes Alpha vor Sichtbarkeitsentscheidung, Erweiterung/Ausschnitt der nativen Kontur, BG2-Durchsicht, Sprite-Priorität und Flips; echter Marker nativ pixelgleich. Cyan-Diagnose unter `build-audit/hd-contours/`. **Kein neuer Live-Compositor und kein neues fertiges Artwork.** Bild der Route oben auf der Treppe geprüft: Pilot weiterhin sichtbar lückenhaft, grobe native Kanten/Übergänge; kein abgeschlossener Level-Remaster.
  - Tests grün: `test_hd_catalog.py`, `test_hd_motifs.py` (eine Quelle/vier gespiegelte Platzierungen, Quellenänderung, Bibliotheksindex, Export/Rebuild), `test_sciv_state.py`, `test_hd_contours.py`, `test_hd_route.py`, `test_hd_render.py` (`build-lua/hd-live-check-744_3sue`, Log `build-audit/hd-reuse-render.log`). Keine C++-Änderung; bestehende Release-Builds weiterhin passend.
  - Dauerhafte lokale Quellen: `artwork-local/pilot-1-1-v1`, `captures/pilot`, `library`, `fixtures/block-1-1/state.sav`, `fixtures/contour-reference`. SHA-256-geprüftes Backup: `D:\Super Castlevania IV Recomp\backup\hd-artwork\2026-10-19-hd-library`. Alles gitignored; Downloads/Spielersaves unverändert.
  - Nächster konkreter Schritt: wiederverwendbare Mauer-/Treppenbausteine gestalterisch freigeben, restlichen ersten Abschnitt ergänzen; echte HD-Konturen live integrieren, dann kleiner vollständiger Simon-Bewegungssatz + ein Gegner. Anleitung und reproduzierbare Befehle in `HD_PIPELINE.md`.
- **Materialpilot 1-1 (19.10., nach db54dae):** auswählbar unter Escape → HD graphics → Graphics pack **`hd_packs/pilot-1-1-painted-v2`**, HD an, 10×. Drei neue Motive mit eingebautem Imagegen: Mauerwerk, rote Treppe, Fels/Vegetation. Quellbilder unverändert unter `build/hd_work/pilot-1-1-v1/`, generierte Bilder in `generated/`; vollständige Prompts/Schnittkoordinaten versioniert in `assets/hd/pilot_1_1.recipe.json`. Kein API-Fallback und keine Downloads-Dateien geändert.
  - Echte Bildauflösung: 1536×1024 für 96×64 Mauerwerk, 1254×1254 für 96×96 Treppe, 1024×1536 für 96×144 Felsen. Auf 80×80-Tiles **heruntergerechnet**, keine künstliche Hochskalierung zu 10×. Das zuerst erzeugte ganze Ebenenbild hatte zu wenig Auflösung und ist nur ein verworfener Entwurf.
  - **Wichtige Erkenntnis:** globale Original-Tile-Schlüssel reichen für neu gemalte größere Motive nicht. Derselbe Fels-/Mauerbaustein wird anderswo in anderer Nachbarschaft verwendet; das führte sichtbar zu Flickstellen. Deshalb optionales Paketfeld `contexts` mit Originalschlüssel, Bildstück, Spiegelung und Nachbar-Schlüsseln. Nur passende Kontexte greifen, sonst Original. Der verworfene globale Versuch wurde nach `build/hd_work/pilot-1-1-v1/rejected-global-tiles-v1` verschoben und steht nicht im Auswahlmenü.
  - `tools/hd/hd_motifs.py`: geprüfter Import aus Ausschnitten, keine zu kleinen/anders proportionierten Bilder, Schutz belegter Ausgabeordner, SHA-256-Quellenbeleg, unabhängige PNGs in `editable/`, Kontext-/Duplikatbericht `motifs.json`. Ergebnis **312 kontextgebundene 80×80-Bilder für 178 Originalschlüssel**. `hd_tiles.py export/build` erhält `contexts.json`; diese Datei beim Bearbeiten behalten. `hd_preview.py` verweist bei Kontextpaketen auf den Live-Renderer, statt irreführend nur Original zu zeigen.
  - Framework `PpuGetBackgroundTileSource` liefert auch verdeckte/transparente BG-Tileidentität unter den aktuellen Zeilenregistern. Sichtbarkeit entscheidet weiterhin `PpuGetTileSource`/native PPU. Renderer-Kontextcache gilt über Tilezeilen; Invalidation bei Register-/HDMA-, VRAM-/Palettenänderungen und Zeilenbandgrenzen. Unbekannte `requires` und ungültige Kontexte werden ohne Verlust des letzten gültigen Pakets abgelehnt.
  - **Grenzen sichtbar geprüft:** Teilabdeckung, Übergänge zu Originalteilen, originale grobe Außenkonturen und teils abweichende KI-Trittflächen/Steinreihen. Noch kein vollständig schöner erster Abschnitt, kein neuer Simon, kein glatter vollständiger HD-Compositor. Nachbarn verhindern unpassende Wiederverwendung, lösen aber keine malerischen Naht-/Geometriefehler. Nächster Schritt: vollständige zusammenhängende Motive und Kantenkorrektur, dann HD-Transparenz/Simon-Probe; erst nach Stilbeurteilung auf weitere Stages ausweiten.
  - Tests grün: `test_hd_motifs.py` (Flips/Alpha, Kontext-Export/Rebuild, Schreibschutz/Mindestauflösung), `test_hd_ppu.py` (zusätzlich transparente/verdeckte Identität), erweitertes `test_hd_render.py` (Kontext-Nearest beim Scrollen, echte Ersatzfarbe, falsche Nachbarn → 0 Ersetzungen/exaktes Original, unbekannte Features abgelehnt). Finale Laufzeitprüfung: `build-lua/hd-live-check-vky2fuol`, Log `build-audit/pilot-render-final.log`.
  - `test_hd_ui.py` mit echtem Pilotpaket auf Nutzer-Build: Klick an/aus, Persistenz, HD/native Marker grün (`build/hd-ui-check-m5myrba8`). `test_hd_pipeline.py --rom ...`: 31.508 Vorkommen, 1320 unveränderte CRCs, Marker-Roundtrip/Sitzungserhalt (`build-dev/hd-check-idd87crz`). Zusätzlich alle 1320 Original-CRCs mit dem Stand vor diesem Pilot verglichen: identisch.
  - `sciv_play.py`: echtes Paket geladen, 90 Frames rechts/30 links, Bilder geprüft: `build-audit/pilot-1-1-context-live.png`, `pilot-1-1-scroll-right.png`, `pilot-1-1-scroll-left.png`. Optimierter Cache liefert zum vorherigen Cache **pixelidentisches** Standbild und Rechts-/Links-Scrollbilder (`pilot-1-1-cached-live.png`, `pilot-1-1-cached-right.png`, `pilot-1-1-cached-left.png`). Messung 240 ungedrosselte Frames bei Kamera146: **ca. 64 FPS** bei 10× gegenüber ca.53 vorher; `build-audit/pilot-performance-cached.json`. Nur diese Szene/dieser Rechner gemessen.
  - Nutzer-Build `build/`, `build-dev/`, `build-lua/` als Release aktualisiert. Startup mit RunAhead 0/1 grün (`build/startup-check-ahb5eid6`). Nutzer-Konfiguration und Saves unverändert, kein Testspiel bleibt absichtlich offen. Alle Grafikpakete/Quellbilder bleiben lokal gitignored.
- **Live-HD / 4K-Grundlage (18.10., nach 2cf6d09):** `src/hd_render.cpp` lädt austauschbare Tile-Pakete; Schalter in Escape → HD graphics, Kategorien Backgrounds/Text-HUD/Sprites, Paketauswahl (`hd_pack`, `hd_packs/*`), Reload und Faktor 2/4/6/10. Persistenz `hd_settings.json`. Paketfehler erhalten das vorherige gültige Paket. Pakete bleiben gitignored.
  - 10× = 3420×2240 intern mit Widescreen, Presenter korrigiert Seitenverhältnis auf dem Zielmonitor. **80×80 reale Pixel pro Original-8×8-Tile** als 4K-Artworkziel; DPI ist irrelevant. Windows-Auflösung wird nicht verändert.
  - Lokales `build/hd_pack/`: 446 bereits zuvor mit Real-ESRGAN bearbeitete 4×-Probetiles für Mauerwerk/Treppen und Teile des Schlosstors. Noch **kein kompletter 4K-Grafiksatz**, keine neuen vollständigen Figurenanimationen. Original standardmäßig an, HD per Klick aktivieren.
  - Framework: optionale `presentation_scale`/`draw_hd_frame`-Hooks, native Thumbnails, HD unter Pause-Menü; PPU-Tileprovenienz (inkl. echter OAM-Gewinner), Farbfensterflags. Ersatzfarben werden anhand der tatsächlichen Zeilenregister/-palette/-VRAM zugeordnet, dann in unveränderlichen Pixelbeschreibungen auf bis zu 8 Render-Threads komponiert. Worker-Pool aus bestehendem Framework, Override `SNESRECOMP_RENDER_WORKERS=1` für seriell.
  - Grenzen: native Sichtbarkeit/Silhouetten bleiben erhalten; Ersatzalpha wird innerhalb nativer sichtbarer Pixel mit Originalfarbe gemischt. **Echte glatte HD-Konturen erfordern später Komposition vor der Transparenzentscheidung.** Modi 2–7, Mosaic, Interlace/Hires und unsupported Host-Transforms fallen auf Original zurück; Character-Workshop-Körper bleiben nativ. RGB8-Farbmathematik für neue Farben; unveränderte Samples exakt Original.
  - Werkzeuge: `sciv_play.py hd on|off`, `hd scale 10`, `hd layers 0x13`, `hd pack ORDNER`, `hdshot DATEI`. `hd_tiles.py export/build` für einzelne editierbare Schlüssel-PNGs und getrennte Grafikvarianten; Paket-/Custom-Upscale-Skalen bis 10×, bestehendes Real-ESRGAN-x4-Modell weiterhin nur 4×.
  - Verifiziert: `test_hd_ppu.py` (BG/OBJ-Flips, 16×16-BG, Weltspiegelung, Mosaic/Window-Fallback); `test_hd_render.py` gegen Lua-Build (2/4/10× pixelidentisches Nearest, native Simulation unverändert, echte 80×80-Testmuster, alle Kategorien unabhängig, ungültiger Reload, Persistenz); `test_hd_ui.py` (echter Checkbox-Klick an/aus über Neustart, HD-Marker 3420×2240 plus Original 342×224). UI-Screenshot `build-audit/hd-menu-final.png` geprüft.
  - Messung über `sciv_play.py`, 240 ungedrosselte Frames in festem 1-1-Zustand: ca. **88 FPS** mit 446-4×-Probetiles bei 10× Ausgabe; ca. **70 FPS** mit 2944 echten 80×80-Diagnosetiles. `build-audit/hd-performance.json`. Kein Leistungsversprechen für alle Stages/Computer.
  - Originalpfad zusätzlich gegen den Vor-HD-Build geprüft: **alle 1320 Bild-CRCs unverändert**. Finaler Exporttest `build-dev/hd-check-1o_z_3ml`: 31.508 Vorkommen, 1320 Frames, Marker-Roundtrip und Session-Erhalt grün.
  - Hauptartefakte: `build-lua/hd-live-check-zh_k8ytn`, `build/hd-ui-check-w7kr6pgo`, `build-audit/hd-live-final.png`. Nutzer-Build und Lua-Build aktualisiert; finale UI-Klicktests auf dem Nutzer-Build und Startup mit RunAhead 0/1 grün (`build/startup-check-hws4lyp2`). Nutzer-Saves/Charaktere/Downloads unverändert.
- **HD-Vorbereitung (18.10.):** Claudes uncommittierten Stand übernommen und fertiggestellt: `hd_collect.cpp` erfasst BG1–3/Sprites, PNGs und Tile-Zuordnung im Hintergrund; eindeutige Sitzungsnamen erhalten frühere Aufnahmen, Warteschlange begrenzt, Schreibfehler werden gemeldet. Debug-Marker erhalten Zeilenregister; Werkzeuge unter `tools/hd/` skalieren, bauen Atlanten und rekonstruieren Marker. Quellprüfsummen verhindern veraltete Upscale-Caches. Exporte sind gitignored. Grenzen: Dokumentation lesen, insbesondere Modus 7, Effekte und Widescreen fehlen in der Vorschau.
  - Verifiziert mit `test_hd_pipeline.py --rom ...`: **31.508 Tile-Vorkommen korrekt, 1320 Bild-CRCs mit/ohne Sammlung gleich**, 1-1-Marker pixelgenau rekonstruiert; Nearest-Paket identisch, zweiter Spielstart erhält alte Aufnahmen. Tests für Flips, Alpha, Cache und ungültige Maße ebenfalls grün.
  - Real-ESRGAN lokal auf Radeon 890M ausgeführt: zwei Ebenenbilder → 446 HD-Tiles, teilweise HD-Vorschau in `build-audit/hd-realesrgan-review/`. Kein fertiges Vollspiel-Grafikpaket.
  - `build-lua` gebaut, Titel mit `sciv_play.py` angefahren und Screenshot geprüft/gespeichert (`build-audit/hd-current-title.png`).
  - Nutzer-Build `build/` war im Cache auf Debug gestellt; wieder als **Release** konfiguriert und gebaut, wie hier dokumentiert. Nutzerdateien bleiben erhalten.
- **Widescreen-Ränder** (633733b, `src/main.c` `Cv4CurrentScene` + `src/widescreen_fill.c`):
  - Ursache war **nicht** der Ladeabstand: Horizontal-Streamer `$06:A0E6` lädt schon ±48 px (`LDA #$0130` / `#$FFD0` bei `$06:A146/A14D`), Raumaufbau `$06:965F` baut 47 Spalten X−56…X+312. Gemessen: 0 abweichende Pixel in den Rändern beim Laufen durch 1-1 (vor/zurück, BG1). (`$06:A15A/A1F0/A20A` = vertikal, `$06:A22C` = Metatile-Schreiber.)
  - Titel: BG1-Logo-Map 32 Spalten → lief als Kopie in die Ränder; BG1 im Titel (Modus 1, 3, 2/0) auf 256 px geklemmt, BG2-Mauer füllt nahtlos.
  - 1-1 links: links von Welt-X 0 baut das Spiel nie (negativ → Spalte 0); die Parallaxe-BG2 schaute dort hinein. Jetzt BG1+BG2 an Welt-X 0 gespiegelt (`PpuSetWidescreenLayerWorldMirrorBand`, nur Kamera < 512). Der alte „schwarze, wachsende Rand“-Hack ist entfernt.
  - Tor-Sequenz (Modus 4, `$70`=0, `$72`=3, `$02:FEA8`) und Prolog/Grabstein (Modus 2/1): gestaltete Randspalten aus `assets/widescreen_margins.txt` (Tor: gespiegelte Fortsetzung wie das selbst spiegelsymmetrisch gebaute Original; Grabstein: saubere erste Bildkopie statt Fremd-Tiles; Nebel BG1 `follow` = Rand nur in Zeilen, die der Nebel im 4:3-Bild schon erreicht hat). Angewendet auf eine reine Darstellungs-VRAM-Kopie (`ppu->renderVram`), Datei wird im laufenden Spiel bei Änderung neu geladen.
  - P16: 4:3 bitgleich außer Titelmenü (beabsichtigt). Widescreen ändert sich nur in Titel, Tor, Levelanfang.
- **Natives NEW GAME+** (aac6d65, `src/title_menu.c`, 7 Guarded Patches, all-or-nothing): START (Zeile 17), NEW GAME+ (19), CONTINUE (21), OPTION (23); „PLAY SELECT“ auf Wunsch entfernt. Index `$1E02`: 0 START, 1 CONTINUE, 2 OPTION, **3 NEW GAME+**; Navigation per Tabellen in Anzeigereihenfolge. Herz-Cursor (`$27`), Blinken beim Bestätigen nativ. „+“ = neues Tile `$33`, vom Spiel-Loader entpackt. `campaign2.c` macht aus bestätigter 3 → START + Kampagnen-Tag `$11E0=$C402` (Sandbox-Raum wie vorher). Overlay-Menü entfernt. Verifiziert: Navigation, Blinken, Tag/Raum, CONTINUE → Modus 6, OPTION → Modus 5 (Test).

- **Savestates** (57b62dc): Chunk „CV4S“ speichert zusätzlich den Ausführungszustand (`RtlSaveExecutionState`, angewendet in `on_state_loaded`). Verifiziert: Titel-State aus Prozess A läuft in Prozess B weiter; Gameplay-State in neuem Prozess spielt bitgenau gleich weiter. Alte „CV4R“-States laden wie bisher (nur gleicher Prozess zuverlässig). Rollback/Run-Ahead bleibt abgelehnt (`exec_state_bound` = 0).
- **Debug-Marker** (6570042 + Framework 9cd151c), siehe oben. Verifiziert: Test, sichtbarer Lauf mit getipptem Text, Laden des Marker-States in `sciv_play`. 4:3 und Widescreen über 1500 Frames bitgleich zum Stand davor.

## RE-Notizen (neu, gelesen bzw. ausgeführt)
- Modus 4, `$70`=0: `$72` 1 = Namenseingabe (`$03:8000`), 3 = Tor (`$02:FEA8`), 4 = Spielinit (`$00:94C5`; `$1E02`≠0 behält `$86`).
- Asset-Loader `$02:80E8` Typ 0: `00 00` + Einträge `[VRAM-Wort lo,hi][Quelle lo,hi,bank]`, Ende `FF FF`. Titel-Liste `$01:B5A7` (Font `$07:8DC9`→`$5000`, Satzzeichen `$07:8FF4`→`$5180`).
- LZ-Entpacker `$02:863D`: Kopf u16 Gesamtlänge; `<$80` Rückverweis, `$80–9F` Literal (n=c&31), `$A0–BF` 0/Byte-Wechsel, `$C0–DF` RLE Byte (n+2), `$E0–FF` RLE 0 (n+2); 1-KB-Ringpuffer.
- BG3-Font: `$01–$0A` 0–9, `$0B–$24` A–Z, `$25` =, `$26` -, `$27` Herz-Cursor, `$2E` ©, `$30` „,“, `$31` „.“, ab `$33` frei (`$33` jetzt „+“ im Titel).
- Freier ROM-Platz `$01:FF24–FFFF`: belegt bis `$01:FFDE`, **33 Byte frei** (`$01:FFDF–FFFF`).
- Menü-Routinen (`008607–00BB39`) sind `lle_only` → ROM-Patches wirken; AOT nur laut `src/gen/program_manifest.json`.

## Offene Aufgaben (Priorität)
1. **Widescreen weiter** – am besten anhand der Debug-Marker des Nutzers: andere Stages (vertikale Schächte, Levelenden rechts, Bossräume, Modus 7), Namenseingabe/CONTINUE/OPTION, Abspann; andere Sprites/Randsituationen (zweites OAM-Gate jetzt erweitert und an den Steinen geprüft); Prolog-Nebellücke links oben; optional 1-1-Weltkante gestalten statt spiegeln. Ablauf für neue Szenen: `dump` → `render_map.py --grid` → Regeln in `widescreen_margins.txt` → live prüfen.
2. **NEW GAME+ korrekt anschließen:** Nutzer hat Bedeutung geklärt: originaler schwererer zweiter Durchgang. Retail-Abschluss-/Schwierigkeitsflag reverse-engineeren und den Menüeintrag daran anschließen; aktuell startet er weiterhin den Host-Sandbox-Raum aus `campaign2.c`.
3. **Szenen-Regressionstests erweitern:** erste versionierte 1-1-Strecke mit Savestate, elf Bild-/Zustandsprüfpunkten und Original/HD/Original-Vergleich fertig (`test_hd_route.py`, siehe oben). Weitere Szenen, Vergleich jedes Frames (`SNESRECOMP_PRESENT_LOG`) und interaktive Eingabeaufzeichnung fehlen noch (Framework-Hooks `frame_begin/frame_end`, Upstream `--resume-state`).
4. **Code neu generieren** mit nativem Analyzer: `symbols.toml` setzt bei `emit=false` jetzt `force_lle` für Reset/NMI → vorher `emit=true` setzen, um den getesteten AOT-Stand zu halten; Ausgabe mit altem `src/gen` vergleichen, Tests laufen lassen.
5. **HD weiterführen:** Nutzer liefert fertige Motive; Codex importiert. Block 1-1 hat volle BG-/registrierte feste OBJ-Konturen und rotierendes HD-Brückendeck. Linke BG2-Erweiterung, Wasser/Ufer und zerbrechende Steine eingebaut. Offen: glatte bewegte Kette/allgemeine OBJ-Stapel, weitere Szenen und spielweite Prüfung. Details/Workflow: HD_PIPELINE.md.
6. Später: Level-Editor, Gegner-Mods, Zufallsmodus, Android, Mods als Pakete im Launcher.
