# Meine Merkhilfe zum Spiel

Hier stehen kurze Anleitungen für dich.
Ich ergänze diese Datei, wenn neue wichtige Hinweise dazukommen.
Stand: 22. Oktober 2026.

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
| Laufen 1 | `Walking-01_HD_10x.png` | 200 × 460 |
| Laufen 2 | `Walking-02_HD_10x.png` | 230 × 450 |
| Laufen 3 | `Walking-03_HD_10x.png` | 200 × 460 |
| Laufen 4 | `Walking-04_HD_10x.png` | 250 × 460 |
| Laufen 5 | `Walking-05_HD_10x.png` | 240 × 460 |
| Laufen 6 | `Walking-06_HD_10x.png` | 230 × 450 |

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

## Unsere Arbeitsweise

- Nur notwendige, gezielte Prüfungen. Keine unnötigen Testreihen.
- Du erstellst die Bilder. Ich baue sie ins Spiel ein.
- Neue Alltagshinweise ergänze ich hier in einfacher Sprache.
- Technische Einzelheiten für die Weiterarbeit stehen in `docs/HANDOFF.md`.
