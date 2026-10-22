# Viele HD-Figuren erstellen, ohne jedes Bild neu zu beschreiben

Recherche vom 21. Oktober 2026.

**Aktuelle Entscheidung: Die Qualität des ersten 3D-Modells wurde vom Nutzer abgelehnt.**
Mit diesem Modell arbeiten wir nicht als Ersatz für die gemalten Sprites weiter.
**Neuer Auftrag:** Der Nutzer möchte LoRA mit seinen guten HD-Bildern ausprobieren.
Das Training soll lokal laufen; längere Rechenzeit ist für ihn in Ordnung.
Der lokale SDXL-LoRA-Pilot mit acht Trainingsbildern, einem zurückgehaltenen
Vergleichsbild und drei Pose-Proben ist fertig. GPU-Training und Bilderzeugung
funktionieren inzwischen auf der Radeon 890M. Der gemalte Look ist erkennbar,
aber Rüstungsdetails und exakte Körperhaltung sind noch nicht stabil genug für
eine fertige Animationsreihe. Eine zusätzliche GPU-Probe verstärkt die Pose-Steuerung.
Status und Bedienung stehen in [MERKHILFE.md](MERKHILFE.md#simon-mit-lora-gleich-aussehen-lassen).
Technische Details stehen in [LOCAL_LORA.md](docs/LOCAL_LORA.md).

**Vorhandener 3D-Pilot:** Blender ist eingerichtet.
Es gibt eine bewegliche Simon-Farbfigur, sechs Laufbilder und drei Angriffsbilder
als Vorschau. Öffnen und Bedienung stehen in [MERKHILFE.md](MERKHILFE.md#blender-für-neue-bewegungen).
Der Look ist plastischer als bei den bisherigen gemalten Bildern.
Die Probe ist noch nicht als Figurenpaket im Spiel eingebaut.
Die folgenden Einschätzungen beschreiben die vorausgehende Recherche.

## Empfehlung vor dem Pilot

Für den Umfang dieses Spiels würde ich zuerst **ein 3D-Modell mit wiederverwendbaren Bewegungen und einem Export nach 2D** ausprobieren. Der Hauptkandidat ist **Meshy für das Modell und die ersten Bewegungen, Blender für die fertigen Sprite-Bilder**. Mixamo kann zusätzliche Bewegungen für menschlich gebaute Figuren liefern.

Das Spiel bleibt dabei ein 2D-Spiel. Wir verwenden am Ende weiterhin durchsichtige PNG-Bilder. Das 3D-Modell ist nur das Werkzeug, aus dem diese Bilder entstehen.

**Wenn der bisherige gemalte Look möglichst genau erhalten bleiben soll, ist ein 2D-Skelett in Spine Professional die bessere Alternative.** Dafür muss die Figur einmal in bewegliche Bildteile zerlegt und vervollständigt werden.

Beides ist meine Einschätzung für unser Projekt. Ich habe die Hersteller-Unterlagen geprüft, aber noch keinen unserer Charaktere mit diesen Programmen animiert. Die endgültige Wahl sollte an einem kleinen Beispiel fallen.

Unser künftiger Ablauf wäre:

**Ein Entwurf → eine bewegliche Figur → mehrere Bewegungen → automatisch viele PNGs → Zuordnung im Spiel.**

## Was sich dadurch ändert

Du bestimmst einmal das Aussehen. Kleidung, Körper, Gesicht und Farben stehen dann fest.
Für eine neue Bewegung wird diese Figur bewegt. Sie wird nicht bei jedem Bild neu gezeichnet.
Eine Laufbewegung lässt sich anschließend auf weitere ähnlich gebaute Figuren übertragen.

Ein bisschen Korrektur bleibt: Füße dürfen nicht rutschen, Kleidung darf nicht durch den Körper gehen und die Hand muss zur Peitsche passen. Diese Stellen korrigiert man im Bewegungsprogramm. Man muss nicht immer wieder der Bild-KI einen Arm erklären.

## Die brauchbaren Wege

| Weg | Wofür ich ihn einsetzen würde | Größte verbleibende Arbeit |
| --- | --- | --- |
| **Meshy + Blender** | Hauptkandidat für viele Figuren und wiederverwendbare Bewegungen | Ein gutes Modell bekommen und den Bildstil abstimmen |
| **Spine Professional** | Gemalte HD-Figuren, Flügel, Schlangen und einzelne Körperteile | Bildteile und Gelenke einmal sauber vorbereiten |
| **Cartoon Animator 5** | Einfacherer Einstieg mit fertigen 2D-Bewegungen | Figur an eine Vorlage anpassen; Spielposen korrigieren |
| **Wan Animate 2** | KI-Versuch: Bewegung aus einem Video übernehmen | Ergebnis auf Bildfehler, Freistellung und passende Posen prüfen |
| **PixelLab** | Kleine Pixel-Figuren und Entwürfe für Bewegungen | Für unsere großen, gemalten HD-Bilder zu stark begrenzt |
| **Synfig** | Kostenloser Einstieg in bewegliche 2D-Figuren | Mehr Einrichtung und eigene Bewegungsarbeit |

### 1. Meshy + Blender: mein Hauptkandidat für viele Figuren

Meshy bietet Bild-zu-3D, automatische Skelette und eine Bibliothek fertiger Bewegungen. Modelle mit Bewegungen lassen sich als FBX oder GLB exportieren. Der Anbieter nennt Unterstützung für menschliche und vierbeinige Figuren. Das sind Herstellerangaben; wie gut unser Simon damit aussieht, ist noch offen. [Meshy: Modell und Bewegung](https://www.meshy.ai/use-cases/3d-animation)

In Blender legen wir dann eine feste Kamera und festes Licht an. Die Kamera schaut seitlich auf die Figur. Blender kann Animationen als einzelne Bilder ausgeben; PNG unterstützt Transparenz. Blender selbst ist kostenlos. [Blender](https://www.blender.org/about/), [Bildfolgen](https://docs.blender.org/manual/en/4.4/render/output/introduction.html), [PNG und Alpha](https://docs.blender.org/manual/id/4.4/files/media/image_formats.html), [Kameraarten](https://docs.blender.org/manual/en/4.4/render/cameras.html)

Der große Vorteil für uns: Dasselbe Modell kann stehen, laufen, springen und angreifen. Die Bilder behalten dieselbe Rüstung und dieselben Proportionen. Bei einer neuen Figur können passende Bewegungen wiederverwendet werden.

Der Haken: Ein aus einem Bild erzeugtes 3D-Modell sieht nicht automatisch genau wie die gemalte Vorlage aus. Haare, Hände, Rüstung und verdeckte Körperseiten können Nacharbeit brauchen. Diesen Weg würde ich deshalb zuerst an wenigen Bildern entscheiden, bevor wir den ganzen Figurensatz umstellen.

**Wichtig beim kostenlosen Meshy-Einstieg:** Die Hilfe nennt derzeit zehn Downloads pro Monat für Meshy 6 Lite. Modelle neuerer dort genannter Versionen können beim Download ein Abo verlangen. Die kostenlose Stufe ist also kein Beleg, dass jedes erzeugte Modell kostenlos exportiert werden kann. Die API ist kostenpflichtigen Stufen vorbehalten. [Aktuelle Free-Grenzen](https://help.meshy.ai/en/articles/15696428-what-is-included-on-the-free-plan)

### 2. Spine Professional: näher an deinen bisherigen Bildern

Spine bewegt gezeichnete Bildteile über ein Skelett. Netze können Bilder verformen, statt sie nur wie starre Pappteile zu drehen. Bewegungen und Figurenvarianten lassen sich in einem solchen Aufbau wiederverwenden. [Spine-Funktionen](https://us.esotericsoftware.com/)

Für uns würden daraus PNG-Bildfolgen exportiert. Eine Spine-Laufzeit im Spiel ist dafür nicht nötig. [Spine-Export](https://us.esotericsoftware.com/spine-export/)

Die notwendige Vorarbeit: Kopf, Oberkörper, Oberarme, Unterarme, Hände, Oberschenkel, Unterschenkel, Schuhe und größere Kleidungsteile werden einmal vorbereitet. Verdeckte Stellen müssen ergänzt werden. Ein einzelnes flaches PNG enthält zum Beispiel nicht den Arm, den der Oberkörper verdeckt.

Der Hersteller zeigt derzeit **69 US-Dollar für Essential und 379 US-Dollar für Professional**. Für Netze und IK, also bequemes Bewegen verbundener Gelenke, wäre Professional relevant. Die Testversion kann keine Projekte speichern oder Bilder exportieren. Daher darin kein großes Produktionsprojekt anfangen. Preise können sich ändern. [Editionen](https://us.esotericsoftware.com/spine-purchase), [Testversion](https://en.esotericsoftware.com/spine-download)

### 3. Cartoon Animator 5: interessant für einen leichteren Einstieg

Cartoon Animator kann Figuren aus Bildern und PSD-Ebenen aufbauen. Es gibt gemeinsame Skelettvorlagen und Bewegungsbibliotheken, unter anderem für Menschen, Vierbeiner und Flügel. PNG-Bildfolgen mit durchsichtigem Hintergrund sind als Ausgabe vorgesehen. Das macht es zu einem brauchbaren Kandidaten, wenn fertige Bewegungen wichtiger sind als ein auf Spiele zugeschnittener Editor. [Figurenaufbau und Bewegungen](https://www.reallusion.com/cartoon-animator/2d-character-design.html), [Transparente Bildfolge](https://kb.reallusion.com/ExportPDF50335.aspx)

Es ist Kaufsoftware. Bewegungs- und Zusatzpakete müssen bei einem Preisvergleich mitgerechnet werden. Den im Browser auslesbaren Shoppreis konnte ich nicht verlässlich feststellen. [Offizieller Shop](https://www.reallusion.com/plan-and-pricing/individual/perpetual/cartoon-animator-5-3024)

Meine Einschätzung: leichter mit fertigen Bewegungen anzufangen; für die genaue Handposition bei Simons Peitsche bleibt Anpassung nötig.

## Welche andere KI wirklich interessant ist

### Wan Animate 2: ein Bild und ein Bewegungsvideo

Die aktuelle ComfyUI-Anleitung beschreibt **Wan Animate 2**. Es bekommt ein Figurenbild und ein Video mit der gewünschten Bewegung. Laut Dokumentation ist dafür keine gesonderte Skelett- oder Posenerkennung als Vorstufe nötig. Es gibt einen offiziellen Ablauf für ComfyUI. Das ist für deinen Wunsch viel passender als viele einzelne Bild-Prompts. [Offizieller Ablauf](https://docs.comfy.org/tutorials/video/wan/wan-animate-2)

Ein sinnvoller Versuch wäre: dein Simon-Bild plus ein kurzes, seitlich aufgenommenes Laufvideo. Anschließend prüfen wir Kleidung, Hände, Standhöhe und den Übergang vom letzten zum ersten Bild.

Meine Einschränkung für unser Spiel: Ein schönes Video ist noch kein passender Sprite-Satz. Wir benötigen klare Außenkanten, durchsichtiges Umfeld und genau die Posen, die das Spiel verwendet. Wenn danach wieder jedes Bild einzeln repariert werden muss, verwerfen wir diesen Weg.

Auf diesem Rechner wurde eine Radeon 890M und etwa 24 GB Arbeitsspeicher erkannt. Einen lokalen Durchlauf dieses Modells habe ich nicht geprüft. Eine Empfehlung, dafür sofort große Modelle herunterzuladen oder neue Hardware zu kaufen, lässt sich daraus nicht ableiten.

### PixelLab: richtige Idee, für unseren HD-Stil derzeit zu klein

PixelLab hat eine Skelett-Animation: mehrere Bilder werden aus einer Vorlage und vorgegebenen Skelettposen erzeugt. Die dokumentierte v3 ist Beta, unterstützt drei bis fünfzehn Bilder und höchstens 256 × 256 Pixel. Es gibt außerdem die Übernahme bestehender Bewegungen. [API-Grenzen](https://www.pixellab.ai/pixellab-api), [Skelett-Werkzeug](https://www.pixellab.ai/docs/tools/animate-with-skeleton), [Bewegung übernehmen](https://www.pixellab.ai/docs/tools/animation-to-animation)

Deine Standfigur ist bereits 460 Pixel hoch und soll ihren gemalten Detailgrad behalten. Eine Verkleinerung auf kleine Pixelgrafik mit anschließendem Hochskalieren wäre dafür kein guter Hauptweg. Als Bewegungsentwurf kann das Werkzeug trotzdem nützlich sein.

### Runway Act-Two: für diesen Zweck kein Favorit

Runway empfiehlt bei Act-Two ein sichtbares Gesicht und Aufnahmen höchstens bis zur Taille. Außerdem kann es selbst Kamera- und Umgebungsbewegung hinzufügen. Das passt schlecht zu seitlichen Ganzkörper-Sprites mit fester Kamera. Ich würde dafür bei unserem Projekt zuerst keine Credits ausgeben. [Hersteller-Anleitung](https://help.runwayml.com/hc/en-us/articles/42311337895827-Performance-Capture-with-Act-Two)

## Zwei weitere Werkzeuge

**Mixamo** liefert kostenlose Bewegungen mit Adobe-Konto, allerdings nur für zweibeinige, menschlich gebaute Figuren. Fledermäuse und Schlangen sind davon nicht abgedeckt. Es ist eine Ergänzung zum 3D-Weg. [Adobe-FAQ](https://helpx.adobe.com/creative-cloud/faq/mixamo-faq.html)

**Cascadeur** hilft beim Stellen von 3D-Posen und bei Bewegungen zwischen wichtigen Posen. Die kostenlose Fassung exportiert nur das eigene Projektformat. Für die Weitergabe an Blender ist eine passende Bezahlstufe erforderlich. Deshalb würde ich es erst ergänzen, wenn fertige Bewegungen nicht ausreichen. [Arbeitsweise](https://cascadeur.com/help/faq), [Aktuelle Tarife](https://cascadeur.com/plans)

**Synfig** ist kostenlos und kann auch Bitmap-Bilder mit Skeletten verformen. PNG-Ausgabe ist dokumentiert. Es ist die kostenlose 2D-Alternative, aber keine KI, die automatisch alle fehlenden Spielbewegungen erzeugt. [Synfig](https://www.synfig.org/), [Ausgabeformate](https://wiki.synfig.org/Render_options)

## Die vielen Gegner müssen nicht alle denselben Aufbau bekommen

Das ist ein Vorschlag für unsere Produktion:

| Figurengruppe | Wiederverwendbarer Aufbau |
| --- | --- |
| Simon, Zombies, Ritter, Mumien | Grundaufbau mit zwei Armen und zwei Beinen; passende Bewegungen übertragen |
| Hunde und ähnliche Tiere | Eigenes Vierbeiner-Skelett |
| Fledermäuse und geflügelte Gegner | Flügelschlag einmal aufbauen; verschiedene Körper und Flügel einsetzen |
| Schlangen, lange Hälse, Tentakel | Kette aus verbundenen Teilen |
| Köpfe, schwebende Teile, Geschosse | Wenige Einzelbilder oder eine kurze wiederholbare Bewegung |
| Feuer, Rauch und Zerfall | Eigene Effekt-Bildfolgen |

So entsteht eine kleine Sammlung von Bewegungsarten. Neue Figuren verwenden davon, was zu ihrem Körper passt. Das spart Arbeit, ersetzt aber keine eigene Bewegung für einen ungewöhnlichen Boss.

## Der erste sinnvolle Versuch

Ich würde **Simon als kleinen 3D-Pilot** nehmen, weil seine HD-Vorlage und die Originalposen schon vorliegen.

1. Ein sauberes Modell aus dem Entwurf erstellen. Arme und Beine sollen in der Ausgangspose getrennt sichtbar sein. Die bisherigen verschränkten Arme sind als einzige Modellvorlage ungünstig.
2. Ein Skelett einsetzen und eine fertige Laufbewegung anwenden.
3. In Blender Kamera, Licht und Größe festlegen.
4. Sechs passende Laufbilder und wenige Angriffsposen als durchsichtige PNGs ausgeben.
5. Mit unseren Originalposen vergleichen. Besonders auf Hände, Füße und gleichbleibende Rüstung achten.
6. Erst bei einem überzeugenden Ergebnis weitere Figuren damit aufbauen.

Falls der 3D-Look nicht zu den Hintergründen passt, würde ich als Nächstes dieselbe kleine Aufgabe mit einer 2D-Figur in Spine oder Cartoon Animator machen. Ich würde nicht gleichzeitig Abos für viele Programme abschließen.

## Was ich schon vorbereitet habe

Die vorhandene Simon-Sammlung wurde nur aus ihren Metadaten ausgewertet:

- 83 bereits erfasste Pose-Einträge.
- 77 verschiedene Körperdarstellungen nach der Erkennung des Spiels; sechs Einträge sind weitere IDs derselben Darstellung.
- Neun Gruppen sind bereits durch HD-Bilder abgedeckt.
- 68 erfasste Gruppen haben noch kein HD-Bild.

Das ist **keine vollständige Liste aller Simon-Posen im Spiel**. Es ist der bisher aufgenommene Bestand. Die Liste ist auch keine Animationsreihenfolge.

Die Arbeitsliste liegt lokal unter:

```text
artwork-local/animation-research-2026-10-21/simon-inventory/poses.csv
```

Damit müssen doppelte interne IDs künftig nicht als neue Bilder bestellt werden. Das Werkzeug dazu ist `tools/character_pose_inventory.py`.

Für fertige Bilder übernimmt weiter das Spiel die Bewegung und das Tempo. Technische Vorgaben für einen späteren Export stehen in [docs/SPRITE_PIPELINE_NOTES.md](docs/SPRITE_PIPELINE_NOTES.md).

Bei dieser Recherche wurden keine Bild- oder Video-Generierungen gestartet und keine Programme gekauft. Die Einschätzungen zu Aussehen und Zeitersparnis müssen noch mit unserem kleinen Pilot bestätigt werden.
