# Lokaler Charakter-LoRA-Pilot

Stand: 22.10.2026. Lokal ausgeführt, keine Bild-Uploads, bezahlten Aufrufe oder
veröffentlichten Modellgewichte. Spielpakete, EXEs, Konfiguration und Saves
wurden für diesen Pilot nicht geändert. Alltagshinweise stehen in MERKHILFE.md.

## Ergebnis und Grenzen

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

### Sechs Gehposen mit Bildreferenz (22.10.)

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

Finale Vorschau unter `walking-2026-10-22/packaged-final`: transparente PNGs,
WebP-Loop und HTML mit Einzelbild-Schaltung. Vorschautempo ist ausdrücklich
kein neues Spieltiming. Für stabile Identität wird der Oberkörper aus Phase01
übernommen, mit der kleinen vorgegebenen Gehbewegung in Y. Übergang bei Y270,
vormultiplizierte Alphamischung und direkte Auswahl unterschiedlich geformter
Konturen verhindern graue, durchscheinende Ränder. Gesicht und obere Rüstung
werden wiederverwendet; Beine/untere Rockbereiche behalten die Phasen.
Aktive Spielbilder wurden nicht überschrieben.

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
