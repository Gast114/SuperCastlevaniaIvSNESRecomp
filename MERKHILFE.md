# Meine Merkhilfe zum Spiel

Hier stehen kurze Anleitungen für dich.
Ich ergänze diese Datei, wenn neue wichtige Hinweise dazukommen.
Stand: 21. Oktober 2026.

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

## Die drei Simon-Bilder austauschen

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

Bisher gibt es drei HD-Posen für Simon.
Beim Laufen und bei anderen fehlenden Posen erscheint noch die Originalfigur.

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

- Gib mir für jede Pose die kleine Originalvorlage und das passende HD-PNG.
- Das HD-Bild hat die zehnfache Breite und Höhe der Vorlage.
  Beispiel: 24 × 46 Pixel werden zu 240 × 460 Pixeln.
- Behalte den durchsichtigen Hintergrund bei.
- Schneide Haare, Hände und Schuhe nicht ab.
- Halte Figur, Kleidung, Farben und Licht zwischen den Bildern gleich.
- Eine Blickrichtung nach rechts reicht. Die andere Seite spiegelt das Spiel.
- Du brauchst keinen großen Bildbogen zu bauen. Einzelne PNGs reichen.

Die DPI-Zahl ist hier egal. Entscheidend sind die Pixelmaße.
Neue Posen müssen zusätzlich zugeordnet werden. Das übernehme ich.

## Unsere Arbeitsweise

- Nur notwendige, gezielte Prüfungen. Keine unnötigen Testreihen.
- Du erstellst die Bilder. Ich baue sie ins Spiel ein.
- Neue Alltagshinweise ergänze ich hier in einfacher Sprache.
- Technische Einzelheiten für die Weiterarbeit stehen in `docs/HANDOFF.md`.
