# Lokaler Charakter-LoRA-Pilot

**27.10.2026: Auf ausdrücklichen Nutzerwunsch pausiert.** Der HD-Simon ist in
beiden Windows-Spielordnern und im Browserpaket deaktiviert. Die entfernten
Windows-Pakete und Werkzeugkopien liegen unter
`artwork-local/simon-pausiert-2026-10-27`; Bilder, Modelle und Arbeitsordner
bleiben erhalten. Keine weitere Erzeugung, Fortsetzung oder Installation ohne
erneuten Nutzerauftrag. Die folgenden Ergebnisse und Aktivierungsangaben sind
historische Zwischenstände, keine laufenden Aufgaben.

Stand: 23.10.2026. Lokal ausgeführt, keine Bild-Uploads, bezahlten Aufrufe oder
veröffentlichten Modellgewichte. Spielpakete, EXEs, Konfiguration und Saves
wurden für diesen Pilot nicht geändert. Alltagshinweise stehen in MERKHILFE.md.

## Ergebnis und Grenzen

**Update23.10.:** Der Nutzer hat die sechs Einzel-PNGs in Photoshop überarbeitet
und den Einbau beauftragt. Diese Nutzerfassung ist jetzt in beiden Spielordnern
aktiv. Aus zugeschnittenen Quellen ohne Resampling auf330x510-Arbeitsfläche
gebracht; alle Details im neuesten HANDOFF-Abschnitt und im lokalen
simon-photoshop-walk-install-2026-10-23/install.json. Alte Kontaktbögen und ZIPs
zeigen weiter den KI-Zwischenstand. Die folgenden Absätze sind dessen Verlauf.


**Neue lokale Vorschau fertig:** `walking-neural-edit-2026-10-22/review-v1`.
Sechs transparente320x510-PNGs in10x mit gemeinsamen Koordinaten, Kontaktbogen,
Animation, synchronem Vergleich, HTML und ZIP. Wirklich visuell geprüft;
PNG-/Hash-/ZIP-Prüfung erfolgreich. Bewegung aus native-motion erhalten.
Oberschenkel03/05/06 und Säume neu neuronell gezeichnet, Embleme01/06 ergänzt.
Vorhandenes gemeinsames01-Gesicht und bereits geschlossene obere01-Rüstung
bleiben erhalten. Finale Montage/Alpha unter assembled-v1, genaue Quellen und
benutzte Auswahl-Teilmenge01 im dortigen series.json.
Kleine Rüstungsdetails variieren weiterhin. Nutzerfreigabe steht aus, nicht im
Spiel installiert. Alle Inferenzaufträge beendet, eigene Modelle freigegeben;
Queue war0/0,13,2GiB RAM frei. Landschaft kann wieder rechnen.

Die folgenden Abschnitte dokumentieren auch verworfene Zwischenstände.


**Verworfener Zwischenstand: manuelle Korrektur der Gehserie.**
`walking-identity-2026-10-22/review` zeigt unnatürlich verzogene Hautmuskeln und
ausgeschnitten wirkende Rocksäume. Außerdem fehlen01/06 die Rückenembleme.
Die akzeptierte Bewegung stammt weiterhin aus `walking-native-2026-10-22`.
Keine dieser korrigierten Fassungen im aktiven Spielpaket installieren.

Die folgenden zwei SDXL-Inpaint-Proben wurden ebenfalls visuell verworfen:
`walking-repaint-2026-10-22/03-thighs-skirt` (längerer Rock, erneut Beinschutz),
`03-thigh-material` (Haut, aber schlechte Muskel- und Rüstungsanschlüsse).
Nicht weitere gleichartige Posen blind generieren.

Für echte Referenz-Bildbearbeitung ist inzwischen ein separates lokales Modell
vorhanden: FLUX.2 Klein4B Distilled. `download_edit_model.py` lädt nur die drei
in `assets/character/simon_local_edit_models.json` festgeschriebenen öffentlichen
Gewichte, prüft Größe und HF-LFS-SHA256, ersetzt keine vorhandenen Modelldateien
und installiert keine Python-Pakete. Neue Unterordner heißen `simon-klein`.
SDXL-LoRA bleibt erhalten, ist aber nicht auf diesen anderen Modelltyp anwendbar.

`direct_edit_walk.py` bereitet Originalbild/Referenzen/Auswahl auf CPU vor und
verwendet ausschließlich die bereits vorhandenen Core-Nodes des lokalen ComfyUI.
Distilled4Schritte/Euler/CFG1 nach der
[offiziellen ComfyUI-Anleitung](https://docs.comfy.org/tutorials/flux/flux-2-klein).
Edits unter `walking-neural-edit-2026-10-22`.
Comfy-History und Rohbild bleiben erhalten; maskiertes Ergebnis erhält außerhalb
der Auswahl das originale RGB. Noch keine künstlerische Freigabe oder Spielfigur.

Der erste GPU-Versuch mit FLUX ist tatsächlich gescheitert (HIP launch failure,
kein Bild). Der dabei angehaltene Comfy-Arbeiter wurde bei leerer Queue mit
dem bisherigen Launcher/Einstellungen wiederhergestellt. Ein vorübergehender
CPU-only-Server8189 und zwei zu langsame FP32-Versuche wurden beendet. Keine
fertigen Bilder daraus, diese Versuche nicht erneut starten.

Der tatsächlich funktionierende Weg verwendet **denselben Server8188** und
vorhandene Core-Nodes: SelectModelDevice(cpu), ModelComputeDtype(bf16),
SelectCLIPDevice(cpu), VAE weiterhin CPU. --cpu-model wählt diesen Weg.
Die CPU unterstützt AVX512_BF16. Ohne expliziten ComputeDtype-Node wählt Comfy
auf CPU still FP32; die bloße Loader-Meldung beweist den Rechenmodus nicht.
Keine neue Umgebung und keine Änderung an Serverflags nötig.
03-thigh-crop-bf16 war ein echter Formversuch, Haut aber blass. Der fertige
03-thigh-style-bf16 nutzt einen zusätzlichen echten Hautausschnitt aus01 und
hat nach Sichtprüfung wärmere, passendere Haut. Vier Schritte je ca.64s dort,
ohne Text-/VAE-Zeit; keine allgemeine Bildrate behaupten.

Die sechs Stellen wurden als EIN serieller Batch gerechnet mit einmal
geladenen Modellen: 01 Bauch/Emblem,06 Emblem,02/04 Säume,05/06 Oberschenkel/Saum.
repairs-batch.json hält Prompt-ID und pro Teil Ausgabe-Node/-Präfix fest.
direct_edit_walk.py batch speichert auch vor der Übermittlung den Auftrag,
damit ein unbekannter HTTP-Ausgang nicht unbemerkt doppelt gerechnet wird.
collect überprüft den ausgeführten Graphen und erhält außerhalb der Auswahl
das Quell-RGB bytegleich. Keine neue Serie von Zufallsvarianten.

Hoher RAM-Bedarf: auch diese CPU-Jobs und die Landschaftsgenerierung laufen
nacheinander in derselben Queue. Eine freie GPU bedeutet währenddessen nicht
genügend freien RAM. Nach leerer Queue eigene Modelle per /free freigeben,
keinen inzwischen laufenden Fremdauftrag unterbrechen.

assemble_neural_walk.py verwirft alle alten unteren Hautverformungen und
Alpha-Saumschnitte. Grundlage unten ist wieder die native-motion-RGBA, darauf
kommen echte neuronale Auswahlen mit lokalem ISNet-Alpha. Oberhalb y400 bleibt
die vorhandene gemeinsame01-Gesichtskorrektur. Kein neues Verziehen von
Körperteilen. package_walk.py --prematted --method exportiert nur10x mit einem
gemeinsamen Koordinatensystem und ehrlicher Methodenangabe im Manifest.

Bei verbliebenen Fragmenten03 bzw. dem langen Zipfel05 kann das Direct-Edit-
Rezept eine `guide_erase`-Auswahl enthalten. Sie blendet das unerwünschte Teil
nur im RGB-Konditionierungsbild aus, mit Hintergrundfarbe aus einem angegebenen
Bildbereich. source.png bleibt unverändert. FLUX zeichnet danach die Kanten
und den Saum neu; weder die Guide-Auswahl noch ein ausgeschnittener Alpha-Saum
werden als fertige Grafik verwendet. Guide, Eingabehash und Prompt bleiben
zur Nachprüfung im jeweiligen Edit-Ordner erhalten.

Neuer gezielter Ansatz: `repaint_walk_parts.py prepare/submit/collect`, Rezept
`assets/character/simon_walk_repaint.json`. Originalbilder als Ausgangspunkt,
neuraler Inpaint einer zusammenhängenden Kleidungs-/Anatomieauswahl, native
Kontur und gemeinsame Stilreferenz. Kein Verziehen von Hautteilen, kein Löschen
von Rockpixeln als fertige Korrektur. Zuerst03, nicht sofort alle sechs.
Ausführung ausschließlich im vorhandenen lokalen ComfyUI-Server nach dem
Landschaftsjob. Busy-Queue wird abgewiesen; keine zweite Inferenzinstanz,
keine Änderungen an Umgebungen oder ursprünglichen Modellen. Zusätzlicher
Simon-LoRA-Export benennt nur Tensor-Schlüssel ins unterstützte ComfyUI-Format
um; Werte, Rank und Alpha bleiben gleich. Quelle und Export haben eigene Hashes.
Ein echter erfolgreicher Render ist noch keine künstlerische Freigabe.

Der erste CPU-Lauf ist fertig: 600 Updates in ca.93 Minuten, anschließend drei
512×512-Proben in zusammen ca.14 Minuten. Dateien unter
`artwork-local/lora-pilot-2026-10-21/review-local` wirklich angesehen: gemalter
Schwarz-Gold-Look erkennbar, aber Rüstungsdetails wechseln und die Pose mit
waagerechtem Arm wurde nicht eingehalten. Noch keine fertige Animationsreihe.
LoRA allein garantiert keine identischen Körper-/Kleidungsdetails.

Eine einzelne GPU-Armprobe verstärkt deshalb ControlNet auf1,25 bis zum Ende.
Die GPU-Probe ist fertig:109,32s inklusive erster VAE-Vorbereitung,
10,53GiB GPU-Spitze. Der Arm zeigt nun nach vorn, bleibt aber gebeugt.
Eigener Ausgabeordner; die ursprünglichen drei Bilder bleiben erhalten. Keine
neue Modell-/Auflösungsmatrix und kein erneutes komplettes Training erforderlich.
Alle Ausgaben sind RGB-Beurteilungsbilder. Alpha, feste Körpergröße, Ursprung,
Handpunkt und native Pose-Zuordnung fehlen vor einer möglichen Installation.

## Bosgame: tatsächliche Hardware und Beschleunigung

Ryzen AI9HX370, zwölf Kerne/24Threads, Radeon890M/gfx1150,32GiB installierter RAM,
DDR5-5600. Windows11Pro25H2, Build26200. Bereits8GiB Grafikreservierung laut
`HardwareInformation.qwMemorySize`; Windows sieht ca.23,6GiB System-RAM.
ROCm meldet ca.16,9GiB nutzbaren GPU-Speicher einschließlich dynamischer Nutzung.
Keine BIOS-/Treiber-/Energieplanänderung nötig oder vorgenommen.

Die frühere CPU-Wahl beruhte auf dem alten ROCm7.2.1-Windows-Pfad. Die aktuelle
[ROCm10.1-Kompatibilität](https://rocm.docs.amd.com/en/latest/compatibility/compatibility-matrix.html)
und [PyTorch-Installation](https://rocm.docs.amd.com/projects/ai-ecosystem/en/latest/frameworks/pytorch/install.html)
enthalten inzwischen gfx1150 unter Windows. Der native GPU-Pfad wurde jetzt
hier eingerichtet und wirklich ausgeführt; kein WSL oder DirectML-Umweg.

- CPU-Umgebung: Python3.13.16 unter `artwork-local/lora-runtime`, Torch2.14.1+cpu.
- GPU-Umgebung: eigenes `artwork-local/lora-rocm-runtime`, Torch2.14.0+rocm10.1.0,
  gerätespezifische gfx1150/115x-Pakete aus AMDs offiziellem Paketindex.
- Gemeinsame Pins: Diffusers0.41.0, Transformers5.20.2, PEFT0.21.2,
  Accelerate1.15.0; vollständige Freezes im Pilotordner.
- `requirements.txt` ist der CPU-Pfad; `requirements-rocm.txt` der GPU-Pfad.
  Bei ROCm heißt das PyTorch-Gerät weiterhin `cuda`; das ist hier AMD-HIP.
- `compute.py`: `--device auto|cpu|cuda`, standardmäßig alle logischen
  CPU-Prozessoren für CPU-Arbeit (`--threads 0`, hier24). GPU übernimmt UNet und
  Renderberechnung; keine künstliche gleichzeitige Vollauslastung aller Einheiten.
- Optimierte RDNA3.5-Attention: pro Prozess
  `TORCH_ROCM_AOTRITON_ENABLE_EXPERIMENTAL=1`, sofern nicht explizit mit0 überschrieben.
  Auf dieser Installation durch echte Vorwärts-/Rückwärtsrechnung geprüft.
- Das GPU-VAE traf bei FP32-SDPA auf `hipErrorProfilerNotInitialized`. Nur dort
  wird deshalb normale GPU-Matrix-Attention verwendet; BF16-UNet/ControlNet
  behalten optimierte Attention. Finale Latents werden vor Decodierung gesichert.

Notwendige Prüfung: GPU erkannt UND endliche, nichtleere Conv-/SDPA-Gradienten.
Danach zwei echte SDXL-LoRA-Updates vom CPU-Checkpoint600 in einen eigenen Ordner
`gpu-training-check-2026-10-22`: erster Schritt70,96s inklusive Aufwärmen,
zweiter1,34s; beide endliche Loss/Gradientnorm, Checkpoint602 erfolgreich.
CPU-Updates zuvor meist6–11s. Ein warmer GPU-Schritt ist noch kein belastbarer
Langzeitbenchmark; nicht die Aufwärmzeit aus einer Gesamtdauer herausrechnen.

Die NPU wird in diesem PyTorch-Autograd-Ablauf nicht verwendet. AMDs
[NPU-Diffusionsweg](https://ryzenai.docs.amd.com/en/latest/sd_demo.html) verwendet
separat vorbereitete/kompilierte Modelle; er ist kein zuschaltbarer zusätzlicher
LoRA-Trainingsprozessor. Kein unpassendes NPU-Demo installiert.

## Daten und Modellstände

Acht gemalte HD-Nutzerbilder, Walking06 als Holdout. Rezept:
`assets/character/simon_lora_pilot.recipe.json`. Aktuelle Walking-Downloads
unterscheiden sich vom installierten Spielpaket; Quell-Prüfsummen im Datensatz.
Abgelehntes Meshy-Modell und generierte A-Pose sind nicht im Trainingssatz.

`prepare_character_lora.py` polstert vorhandene PNGs ohne Skalierung auf512×512
Grau auf. Alpha und Originale bleiben separat erhalten. Ausrichtung am opaken
Unterrand betrifft nur den Trainingssatz, keine Sprung-/Fußposition im Spiel.
Captions sind selbst geschrieben, Trigger `scivsimonv1`. ZIP nur8PNG+8TXT;
Duplikate/Holdout-Leck abgelehnt. Alte Cloud-JSON-Vorlage unbenutzt, bei neuer
Vorbereitung wird sie nicht mehr erstellt. Diese LoRA gehört zu SDXL, nicht FLUX.

Pinned öffentliche Modellgewichte, kein persönlicher Token beim Download:

- `stabilityai/stable-diffusion-xl-base-1.0`, Revision
  `462165984030d82259a11f4367a4eed129e94a7b`.
- `xinsir/controlnet-openpose-sdxl-1.0`, Revision
  `23f966cd5cfdd3f7729c903e243d87152162d2b7`.
- Quellen je `models/*/download-source.json`; nur notwendige Safetensors/Configs,
  keine doppelten ONNX-/Refiner-Kopien. Training/Inferenz offline, ohne Tracker.

## Training und Pose-Steuerung

`train_sdxl.py`: eingefrorenes SDXL-UNet plus FP32-PEFT-Adapter, BF16-Basis,
600Updates, Batch1, Rank/Alpha16, Q/K/V/Attention-Output, LR8e-5,30Warmup,
Kosinusabfall auf15%, AdamW, Gradient-Checkpointing, Min-SNR5, Clip1, Seed20261021.
Textencoder werden nicht trainiert. Text/VAE werden vorbereitet und vor dem
UNet-Lernen freigegeben. VAE-Mittelwert/Standardabweichung im Cache, frische
Posterior-Abtastung je Update. Basis:
[Diffusers-LoRA](https://huggingface.co/docs/diffusers/training/lora).

Checkpoints alle100 Updates oder nach STOP: Adapter, Diffusers-Safetensors,
eigener Optimizer, CPU-/GPU-RNG und Metadaten. Resume prüft Dataset, Rank, Dtype,
Seed; nur eigene Optimizer mit `weights_only=True` laden. Ein Gerätewechsel
ist numerisch kein bitgleicher Lauf. Fortschritt atomar, Loss/Gradientnorm geloggt.

Drei manuelle ungefähre COCO18-Posen unter `assets/character/simon_lora_poses.json`,
mit `render_pose_guides.py` gezeichnet. Keine automatische Pose-Erkennung aus
winzigen SNES-Sprites, keine finale native Peitschenzuordnung.
`render_sdxl_trial.py`:28Schritte, Seed20261021, LoRA0,85; ursprüngliche
ControlNet-Stärke0,8bis85% des Verlaufs. CLI kann eine einzelne Pose auswählen,
Kontrollstärke verändern und bei wenig GPU-Speicher Offloading verwenden.

## Bedienung und Dateien

### Identität und Kleidungsdetails nach der akzeptierten Bewegung

Die native Gehbewegung ist vom Nutzer positiv bewertet. Aktuelle Korrektur
unter `walking-identity-2026-10-22/review`: Keine neue Generierung, sondern
deterministische lokale Bildarbeit mit `refine_walk_identity.py`. Das JSON-
Rezept `assets/character/simon_walk_identity_patches.json` führt alle Änderungen
je Phase auf und enthält die tatsächlich verwendeten Bildkoordinaten.

Kopf/Haar aus01 werden als eigenes Teil wiederverwendet. Der Schnitt endet am
Kragen, nicht am Bauch wie beim verworfenen ganzen Oberkörper. Bewegliche
Arme/Schultern bleiben erhalten. Körperteile und Materialien werden nur in
expliziten Masken bearbeitet; Premultiplied-Alpha-Transformationen verhindern
schwarze Farbsäume. Eine lokale Konturverengung korrigiert die Oberschenkelbreite05.
Haut statt Hosenpanzer03/05/06 kommt aus vorhandenen plausiblen Hautpartien;
keine neuen nackten Körper-/Gesichtsdetails pro Prompt erzeugt. Kopf-Hals-
Anschluss06 separat gesetzt, alte Kinn-/Haarreste gelöscht.

Ausgangsdateien bleiben unter walking-native-2026-10-22 erhalten. Freigestellte
Bearbeitung unter walking-identity-2026-10-22/edited, Änderungsmasken und
refinement.json daneben. `package_walk.py --prematted --before <altes Paket>`
exportiert PNG/ZIP und synchronen Vergleich ohne erneute Matting-KI.
Altes und neues Paket werden am gemeinsamen Root ausgerichtet, nicht anhand
einzelner Körperbegrenzungen. Damit bleiben tatsächliche Formänderungen sichtbar.

Dieser Durchlauf nutzt nur CPU/Pillow/OpenCV. Kein LoRA-Training, keine
Diffusion, kein Cloud-Upload, keine Änderung der Python-Umgebungen oder Modelle.
Die890M ist für den parallel vorbereiteten ComfyUI-Landschaftstest freigegeben;
beide Arten von GPU-Aufträgen sollen nacheinander laufen.

### Sechs Gehposen mit Bildreferenz (22.10.)

**Diese erste Serie wurde vom Nutzer abgelehnt.** Schulter-, Arm- und
Beinbewegungen passen nicht. Die folgenden Angaben beschreiben den Versuch,
keine akzeptierte Animation. Vor allem `--lock-upper-body` nicht für neue
Gehposen benutzen: Es unterdrückt benötigte Schulter- und Armbewegungen.

`walking-2026-10-22` ergänzt den Pilot um sechs manuell gesetzte Gehphasen in
`assets/character/simon_walk_poses.json`. Sie orientieren sich an der beobachteten
nativen Reihenfolge. Ihre Knochenpunkte sind Annäherungen, keine automatisch
erkannte oder bereits installierte native Zuordnung.

Zur LoRA kommt eine echte lokale Bildreferenz mit
[IP-Adapter Plus](https://huggingface.co/h94/IP-Adapter), Revision
`018e402774aeeddd60609b4ecdb7e298259dc729`. Nur ViT-H-Encoder und notwendige
SDXL-Adapter-Safetensors, ohne Auth-Token heruntergeladen. Embedding einmal aus
der korrigierten Bildvorlage, wiederverwendet für alle sechs. Encoder anschließend
auf CPU, GPU für Diffusion freigegeben. Umsetzung nach
[Diffusers-IP-Adapter](https://huggingface.co/docs/diffusers/using-diffusers/ip_adapter).

Parameter:32Schritte, LoRA0,65, IP0,6, ControlNet1,4 bis Ende, gleicher Seed.
Echte GPU-Zeiten37–39s je Bild, alle sechs vollständig ausgeführt. Kein erneutes
LoRA-Training oder Cloud-Imagegen für diese Gehserie. Knie-Detailkorrektur
bei02/05 am Ende deterministisch: glatte Knie-/Schienbeinbereiche aus Walking03
mit expliziten Polygonmasken und ganzzahliger Translation übernommen. Lokale
Diffusions-Inpaint-Versuche erzeugten erneut unpassende Platten und sind nicht final.
Das endgültige Werkzeug benötigt dafür weder Modell noch neue Generierung.

`download_reference_tools.py` lädt zusätzlich den öffentlichen ISNet-Anime-
ONNX-Stand aus dem rembg-Release, prüft dessen upstream-MD5 und protokolliert
SHA256. `package_walk.py` nutzt ONNXRuntime1.31.0 auf CPU zum Freistellen,
behält weiche Alphakanten und entfernt abgetrennte Maskenreste. Fester
gemeinsamer Ausschnitt für alle sechs Bilder, weder individuelle Skalierung
noch Fußpunkt-Normalisierung. Quelle der Segmentierung:
[rembg](https://github.com/danielgatis/rembg).

Historische Vorschau unter `walking-2026-10-22/packaged-final`: transparente PNGs,
WebP-Loop und HTML mit Einzelbild-Schaltung. Vorschautempo ist ausdrücklich
kein neues Spieltiming. Für stabile Identität wird der Oberkörper aus Phase01
übernommen, mit der kleinen vorgegebenen Gehbewegung in Y. Übergang bei Y270,
vormultiplizierte Alphamischung und direkte Auswahl unterschiedlich geformter
Konturen verhindern graue, durchscheinende Ränder. Gesicht und obere Rüstung
werden wiederverwendet; Beine/untere Rockbereiche behalten die Phasen.
Aktive Spielbilder wurden nicht überschrieben.

### Gehbewegung direkt aus den Original-Sprites

`prepare_native_walk.py` liest sechs native Atlaszellen aus dem aktiven Paket.
Ein gemeinsamer Koordinatenwechsel ersetzt die früheren geschätzten COCO-Punkte.
Vollständige Alpha-Kontur plus geglättete interne Kanten steuern den lokalen
[Xinsir-Canny-Controller](https://huggingface.co/xinsir/controlnet-canny-sdxl-1.0),
Revision `1271357eda52d54b857c650cacb5b51144643ccb`. Öffentliches Modell, kein
Upload. `download_shape_control.py` lädt ausschließlich Config, Safetensors
und Quellenbeschreibung. CPU-Helfer benötigt OpenCV aus requirements-matting.

Die Arbeitsfläche1024 verwendet20Bildpixel je Originalpixel. Eine spätere
Ausgabe für das Spiel wird gemeinsam auf10x reduziert; keine zusätzlichen
Spielauflösungen oder Skalen-Testmatrix. Koordinaten:
`x'=(x-22.4)*20`, `y'=(y-27)*20`. Das lässt Kopf und Füße aller Phasen frei.
Keine Zentrierung einzelner Posen und kein Kopieren des ganzen Oberkörpers.

`render_sdxl_trial.py --ip-mode style` nutzt IP-Adapter nur in
`up.block_0=[0,scale,0]`, nach
[Diffusers-Stilsteuerung](https://huggingface.co/docs/diffusers/using-diffusers/ip_adapter#style-and-layout-control).
Die Haltung der einzelnen Referenz soll die native Bewegung nicht ersetzen.
Render-Prompt gekürzt: Die frühere lange Beschreibung überschritt77CLIP-Tokens
und schnitt die eigentliche Pose ab. Die Kontur kommt dennoch aus dem Bild.

Vor einer neuen Serie einzelne Phase04 gegen das Original vergleichen. Die
512er Formprobe trifft die Haltung besser, war jedoch deutlich zu weich.
Arbeitsordner `walking-native-2026-10-22`, Originale im Spiel bleiben aktiv.

Die1024er Phase04 ist tatsächlich erzeugt und unter `probe-hd-04` mit dem
Original verglichen. Sie folgt Schulterdrehung, zurückgeführter Hand und
angehobenem Bein sichtbar besser. Das gibt noch keine automatische Freigabe
aller anatomischen/Rüstungsdetails. `review_native_walk.py` zeigt RGB-Original,
HD und Originalkontur über HD, ohne beide Bilder neu auszurichten.

Für den restlichen Lauf werden Latents separat gespeichert (`--latents-only`).
Danach gibt `decode_sdxl_latents.py` die Bilder mit allein geladenem FP32-VAE
und512er Kacheln aus. So müssen UNet, ControlNet und CPU-Offload-Kopien nicht
neben dem Decoder im gemeinsamen RAM bleiben. Der erste kombinierte Lauf mit
Group-Offload brauchte für Phase04 insgesamt590s. Keine einmalige Warmup-Zeit
als allgemeine Bildrate ausgeben. In künftigen Läufen synchronisiert der
Schritt-Callback die GPU, damit "35/36" nicht nur noch wartende GPU-Aufträge
beschreibt. Notwendiger ROCm-FP32-VAE-Matrix-Attention-Workaround bleibt erhalten.

`package_walk.py` hat keine Oberkörper-Sperre mehr. Ein gemeinsamer Ausschnitt
und eine gemeinsame Reduktion von20Arbeits- auf10Ausgabepixel je Originalpixel
erhalten die Bewegung. `placement.json` speichert beide Koordinatensysteme.
Wenn native Farbvorlagen neben poses.json liegen, entsteht auch ein synchroner
Originalvergleich alsWebP und Kontaktbogen. Vorschautempo ersetzt keine native
Spiel-Animation. Das Spielpaket wird von keinem dieser Werkzeuge installiert.

Ergebnis dieses Durchlaufs: `walking-native-2026-10-22/packaged`, sechsRGBA-PNGs
320×510,10x, synchroner Originalvergleich, HTML-Einzelbildvorschau und ZIP.
Alle sechs mit vollständiger nativer Außenkontur und eigenem Oberkörper,
kein erneuter Maskentausch an Knien. Die Haltungen sind deutlich näher am
Original; Rüstungsdetails variieren weiterhin. Entwurf für Nutzerbeurteilung,
keine als konsistent freigegebene/installierte Spielfigur. Merkhilfe verlinkt
ausdrücklich den neuen Ordner und kennzeichnet die alte Serie als verworfen.

Pilot: `artwork-local/lora-pilot-2026-10-21`.
`Status.cmd` zeigt den ursprünglichen Auftrag; `Anhalten.cmd`/`Fortsetzen.cmd`
sind für unterbrochenes Training. Der erste Lauf ist bereits fertig, nicht
nochmals in denselben Ausgabeordner starten. `.running.lock` verhindert Doppelstarts.

Wichtige Dateien:

- `job.json`, `training-local/progress.json`, `run.json`, `loss.jsonl`: CPU-Verlauf.
- `training-local/final/pytorch_lora_weights.safetensors`: fertige600er-LoRA.
- `training-local/checkpoint-*`: fortsetzbare Zwischenstände.
- `review-local`: erste drei Bilder und Parameter/LoRA-Prüfsumme.
- `gpu-training-check-2026-10-22`: zwei echte GPU-Updates und eigener Checkpoint.
- `review-gpu-2026-10-22`: gescheiterter erster GPU-Decode, kein fertiges Bild.
- `review-gpu-2026-10-22-fixed`: GPU-Pose nach VAE-Korrektur.
- `build-audit/rocm-*.log/json`: tatsächliche Installation/Kernelnachweise.

Neue Datensatz-/Pose-Ordner lokal vorbereiten:

```powershell
& 'artwork-local/lora-runtime/Scripts/python.exe' tools/prepare_character_lora.py --recipe assets/character/simon_lora_pilot.recipe.json --out artwork-local/NEUER-PILOT/dataset-v1
& 'artwork-local/lora-runtime/Scripts/python.exe' tools/lora/render_pose_guides.py assets/character/simon_lora_poses.json --out artwork-local/NEUER-PILOT/pose-guides
```

Für GPU-Berechnung ausdrücklich den GPU-Interpreter benutzen. Beispiel für eine
einzelne Pose in einem NEUEN Ausgabeordner; Modelle/LoRA werden wiederverwendet:

```powershell
& 'artwork-local/lora-rocm-runtime/Scripts/python.exe' tools/lora/render_sdxl_trial.py --device cuda --model artwork-local/lora-pilot-2026-10-21/models/sdxl --controlnet artwork-local/lora-pilot-2026-10-21/models/openpose-sdxl --lora artwork-local/lora-pilot-2026-10-21/training-local/final --guides artwork-local/lora-pilot-2026-10-21/pose-guides --pose arm-forward --control-scale 1.25 --control-end 1 --out artwork-local/NEUE-POSE
```

Neue komplette lokale Jobs können über `run_local_pilot.py` laufen (Download →
Training → drei Bilder). Keine bestehenden Ausgabeordner überschreiben. Aktive
Jobs verhindern nur automatischen Ruhezustand, ändern keinen Windows-Energieplan.

Backup: `D:/Super Castlevania IV Recomp/backup/hd-artwork/2026-10-21-local-lora`.
Originale/Dataset, Rezepte, Werkzeuge, Quellenbelege und fertige Adapter/Bilder
sichern. Basismodelle und Venv nicht zusätzlich verdoppeln; sie sind erneut
installierbar. SHA256-Manifest im Backup benennt den tatsächlich gesicherten Stand.

### Eigener Adapter aus den Photoshop-Laufbildern (23. Oktober)

Das neue Design kommt ausschließlich aus den sechs aktuell installierten,
vom Nutzer überarbeiteten Laufbildern. `prepare_walking_design_lora.py` kopiert
deren 330×510-Pixel-Arbeitsfläche ohne Resampling bei `[86,0]` auf eine graue
512×512-Fläche. Alle sechs Bilder werden trainiert. Alte Idle-/Duck-/Sprungbilder
sind keine Designreferenz dieses Datensatzes.

Arbeitsordner: `artwork-local/simon-design-extension-2026-10-23`.
Datensatz: `walking-design-dataset`, Trigger `scivwalkv2`.
Das neue Training in `training-walk-design` hat 600 Schritte mit Rang16 und
Start-Lernrate0,00008 auf der Radeon890M abgeschlossen. Es benutzt die bestehende
`lora-rocm-runtime`; Grundmodell, alte Adapter und Python-Umgebungen bleiben
erhalten. Training und Comfy-Inferenz laufen nacheinander.

Der fertige Diffusers-Adapter hat SHA256
`c3f88384659069cc62a901a623bd9ce87024dabc7e6f11135f0a169102e73b4a`.
`export_comfy_lora` benennt seine 1120 Tensoren für ComfyUI um und kopiert deren
Werte unverändert. Der separate Export heißt
`Simon_walk_design_rank16_20261023.safetensors`, SHA256
`28f400ba43765b83f9368e1484171f327cd407dedea17e6a083348baf513e205`.
`training-export.json` und die `.source.json` beim Export belegen die Herkunft.

`native_design_pose.py` steuert neue Haltungen durch die aufgenommenen nativen
96×96-Atlaszellen. Canny und IP-Adapter verwenden die vorhandene gemeinsame
Comfy-Queue8188. Ein Batch teilt Grundmodell, LoRA und Stilreferenz und rechnet
die Posen nacheinander. Er verweigert eine belegte Queue. Keine zweite GPU-
Instanz neben einer Landschaftsberechnung starten.

Der Adapter allein traf den gewünschten Stil noch nicht ausreichend: Hautfarbe,
Muskelgröße und Beinschienen wichen sichtbar ab. Die SDXL-Bilder dienen deshalb
als Haltungsvorlagen. Die finalen Bilder entstehen durch eine direkte lokale
Designübertragung mit dem bereits vorhandenen FLUX.2-Klein-Modell:
`prepare_design_transfer.py` setzt die unveränderte Photoshop-Laufzeichnung an
erste Stelle und eine klare HD-Haltung an zweite Stelle. Der Text benennt die
zweite Zeichnung ausdrücklich als reine Pose und fordert keine Treppenkulisse.
`direct_edit_walk.py batch` teilt Modelle und bei identischem Text auch die
Qwen-Textberechnung. Es benutzt die gemeinsame Queue mit vorhandenen CPU/BF16-
Knoten; der zuvor fehlerhafte Radeon-FLUX-Pfad wird nicht erneut ausprobiert.

Die fertigen Arbeitsbilder haben 512×512Pixel, direkt10x. Eine gegebenenfalls
1024er Haltungsvorlage wird vorher gemeinsam auf512 reduziert. Das sind keine
zusätzlichen Spielauflösungen. `export_design_extension.py` erstellt transparente PNGs,
Kontaktbögen, Treppenanimation, HTML und ZIP. `install_design_extension.py`
übernimmt erst visuell geprüfte Bilder, sichert die alten Pakete und erhält
die Lauf-PNGs, deren Zuordnungen und Gameplay-Daten unverändert.

Die fünf unterschiedlichen nativen Treppen-IDs sind aus den gelieferten
Originalen zugeordnet. Bild06 ist zugeschnitten identisch zu02 und erhält
deshalb eine exakte Kopie. Es gibt acht unterschiedliche neue Posen und neun
PNG-Dateien. Ein fertiges Training allein bestätigt noch keine gelungene
Anatomie oder einheitliche Rüstungsdetails; die wirklichen Bilder werden geprüft.

Quellen und fertiger Adapter sind separat SHA256-geprüft gesichert unter
`D:/Super Castlevania IV Recomp/backup/hd-artwork/2026-10-23-simon-design-extension`.
