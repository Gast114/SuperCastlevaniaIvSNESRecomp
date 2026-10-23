# Spieltechnik und Grafikwerkzeuge – 23. Oktober 2026

Die fünf beauftragten Arbeiten sind unabhängig von neuen HD-Designs umgesetzt.
Bedienung steht auch in `MERKHILFE.md`.

## Debug-Marker: wiederholte Kulisse an der Zugbrücke

`build-play/game/debug_markers/2026-10-22_21-47-16_level` zeigt die Wiederholung
des Anfangsfelsens am rechten Bildrand. BG2 läuft dort langsamer als BG1;
seine HD-Region war fälschlich mit 512 Pixeln wiederholbar. Das Rezept verwendet
jetzt Weltkoordinaten ohne Wiederholung. Wasser bleibt separat animiert.

Das neue lokale Paket `stage-01-user-a02-v3` enthält denselben A02-Import wie v2
und diese korrigierte Eingangskulisse. Die elf Quellen wurden nicht verändert.
Die Änderung ist im Importbeleg des Pakets protokolliert.

## Rewind

Beim Verlassen des modalen Rewind-Browsers übersprang `continue` das Löschen
von `g_rewind_hotkey`. Deshalb öffnete derselbe Tastendruck das Menü sofort
erneut. Die Öffnungsflanke wird nun vor dem modalen Aufruf verbraucht.

F8 öffnen, Links/Rechts wählen, Enter/Leertaste übernehmen, Escape/Rücktaste
abbrechen. Native Rewind-Historie und Spielerspeicherdateien bleiben erhalten.
Die gezielte Regression injiziert echte SDL-Tastenereignisse und weist nach,
dass das Spiel nach Übernehmen und Abbrechen weiterläuft.

## NEW GAME+

Der frühere Testraum ist entfernt. Der Original-Abspann setzt bei `$03:FCAE`
das Questflag `$0088=1`. Die native Rauminitialisierung `$00:D3FA` erzeugt daraus
die höhere Schwierigkeit in `$0084`; `$00:D6F0` aktiviert zusätzliche Gegner
mit dem ursprünglichen Spawnbit. Der neue Menüpunkt setzt dasselbe Flag vor
der ersten Rauminitialisierung. START bleibt normal. Der kurze ausstehende
Menüauftrag liegt in WRAM und folgt dadurch Save/Load und Rewind.

Menüauswahl und echte Schlusssequenz ergeben dieselbe native Schwierigkeit.
Save/Load sowie zusätzliche A02-Gegner sind geprüft. Ein kompletter Durchlauf
und interaktive Passwort-Eingabe wurden dafür nicht durchgeführt.

## Gegner und Importe

Der erste Gegner-Pilot umfasst die tatsächlich aufgenommenen A02-Skelette
beider nativer Typen. Referenzen werden automatisch gespeichert, neue Bilder
ersetzen eindeutig erkannte vollständige Posen und behalten native Prioritäten
und OAM-Reihenfolge. Fehlende oder unvollständig erkannte Posen bleiben original.
Es sind noch keine neuen HD-Gegnerdesigns installiert. Weitere Gegner und Bosse
brauchen jeweils eine geprüfte Zuordnung. Details: `ENEMY_HD.md`.

`HD_Import_starten.cmd` öffnet die lokale Importoberfläche mit Vorlagen,
Bilderübersicht, Prüfung und Paketbau. Quell-PNGs bleiben bytegleich; Anzeigegröße
und Verankerung stammen aus der nativen Vorlage. Der Einbauen-Knopf übernimmt
ein geprüftes Paket in beide Spielversionen und sichert die bisherige Auswahl.
Details und Grenzen: `HD_IMPORT.md`.

## Gezielte Nachweise

- Rewind mit Tastatur: `build/rewind-key-check-e6ya8rsb` auf Release ohne Lua,
  beide Fälle bestanden; zuvor `build-lua/rewind-key-check-6wj62cr6`.
- Nativer zweiter Durchgang: `build-lua/second-quest-check-e5uvyqfh/report.json`;
  dauerhaft `artwork-local/newgameplus-2026-10-23`.
- Debug-Marker: `build-lua/bridge-repeat-check-qfir23rr/report.json`.
- Freie PNG-Auflösung: `build-lua/character-hd-gjvy0ggr/report.json`, drei Posen
  in beiden Richtungen, unveränderte Spielzustände, Reload und Dateifehler-Rückfall.
- Gegner: `build-lua/enemy-runtime-p66khw8j/report.json`, echte Skelettaufnahmen,
  387×387-Test-PNGs auf 96×96-Fläche und identische vollständige RAM-/Video-Hashes.
- PPU-Provenienz: `tools/test_hd_ppu.py` bestanden (Spiegelung, große Tiles,
  Weltreflexion, Mosaic und Fenster). Weitere Importtests stehen bei den Werkzeugen.
- HD-Menü auf Release: `build/hd-ui-check-o_mp3g4o`, echter Checkbox-Klick,
  Neustart-Persistenz und Markerbilder bestanden.
- Import: sechs gezielte Importtests, fünf isolierte Installertests und
  verdeckter Tk-Smoke inklusive Gegner-Paketbau und Installation in Testordnern.

Installation und SHA-256-Nachweise liegen unter
`D:/Super Castlevania IV Recomp/backup/hd-artwork/2026-10-23-gameplay-tools-v1`.
Beide Startordner erhalten denselben Release-Build und wählen die v3-Kulisse.
Die vorherigen EXEs vor dem Neubau liegen zusätzlich unter
`2026-10-23-gameplay-tools-prebuild`. Spielstände, Debug-Marker, Charakterbilder
und bestehende Gegnerpakete werden vor/nach Installation per SHA-256 geprüft.
