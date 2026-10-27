"""Export local reference-edited Simon poses at 10x, with shared native placement.

No diffusion, source edits or game installation. CPU ISNet extracts alpha after
the shared Comfy queue is idle. A20x working render receives one shared20-to10x
reduction; no individual pose normalization or geometric body-part warping.
"""
import argparse
import json
import math
from pathlib import Path
import zipfile

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from repaint_walk_parts import read, write, digest, request


def matte(image, session):
    tensor = np.array(image.resize((1024, 1024), Image.Resampling.BILINEAR), dtype=np.float32)
    tensor /= max(float(tensor.max()), 1.)
    tensor -= np.array([.485, .456, .406], np.float32)
    prediction = session.run(None, {session.get_inputs()[0].name: tensor.transpose(2, 0, 1)[None].copy()})[0][0, 0]
    prediction = (prediction - prediction.min()) / max(float(np.ptp(prediction)), 1e-8)
    mask = Image.fromarray(np.uint8(np.clip(prediction * 255, 0, 255))).resize(image.size, Image.Resampling.LANCZOS)
    alpha = np.array(mask, dtype=np.float32) / 255
    alpha[alpha < .012] = 0
    alpha[alpha > .985] = 1
    solid = Image.fromarray(np.uint8(alpha > .1) * 255)
    ys, xs = np.nonzero(alpha > .1)
    if not len(xs):
        raise ValueError("Empty neural foreground")
    near = np.argmin((xs - image.width * .5) ** 2 + (ys - image.height * 210 / 512) ** 2)
    ImageDraw.floodfill(solid, (int(xs[near]), int(ys[near])), 128)
    connected = Image.fromarray(np.uint8(np.array(solid) == 128) * 255).filter(ImageFilter.MaxFilter(7))
    alpha[np.array(connected) == 0] = 0
    rgb = np.array(image, dtype=np.float32) / 255
    background = np.median(np.concatenate([rgb[0], rgb[-1], rgb[:, 0], rgb[:, -1]]), axis=0)
    edge = (alpha > .04) & (alpha < .985)
    recovered = (rgb - (1 - alpha[..., None]) * background) / np.maximum(alpha[..., None], .04)
    rgb[edge] = np.clip(recovered[edge], 0, 1)
    return Image.fromarray(np.uint8(np.clip(np.rint(np.dstack((rgb, alpha)) * 255), 0, 255)))


def sheet(frames, names, out, columns=3):
    panel = Image.new("RGB", (columns * 360, math.ceil(len(names) / columns) * 550), "#dadada")
    draw = ImageDraw.Draw(panel)
    for i, name in enumerate(names):
        image = frames[name].copy()
        image.thumbnail((340, 500), Image.Resampling.LANCZOS)
        x, y = i % columns * 360, i // columns * 550
        panel.paste(image, (x + (360 - image.width) // 2, y + 20), image)
        draw.text((x + 12, y + 528), name, fill="black")
    panel.save(out)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", type=Path, required=True)
    p.add_argument("--model", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    if args.out.exists():
        raise FileExistsError("Use a fresh export directory")
    q = request("/queue")
    if q["queue_running"] or q["queue_pending"]:
        raise RuntimeError("Wait for the shared inference queue and RAM")
    import onnxruntime as ort
    options = ort.SessionOptions()
    options.intra_op_num_threads = 12
    session = ort.InferenceSession(str(args.model), sess_options=options, providers=["CPUExecutionProvider"])
    recipe = read(args.source / "extension.json")
    images, boxes, metadata = {}, [], {}
    args.out.mkdir(parents=True)
    (args.out / "rgba-work").mkdir()
    (args.out / "frames").mkdir()
    for pose in recipe["poses"]:
        name = pose["name"]
        folder = args.source / pose.get("generation_folder", name)
        meta = read(folder / "job.json")
        if meta["status"] not in ("rendered_needs_visual_review", "accepted_for_preview"):
            raise ValueError("Incomplete pose: " + name)
        image = Image.open(folder / "edited-full.png").convert("RGB")
        if image.size not in ((512, 512), (1024, 1024)):
            raise ValueError("Unexpected working canvas")
        image = matte(image, session)
        if image.size == (1024, 1024):
            image = image.resize((512, 512), Image.Resampling.LANCZOS)
        image.save(args.out / "rgba-work" / (name + ".png"))
        box = image.getchannel("A").point(lambda a: 255 if a > 8 else 0).getbbox()
        if not box or box[0] == 0 or box[1] == 0 or box[2] == 512 or box[3] == 512:
            raise ValueError("Pose touches image edge: " + name)
        boxes.append(box)
        images[name], metadata[name] = image, meta
        print("Transparent " + name, flush=True)
    crop = [math.floor((min(b[0] for b in boxes) - 10) / 10) * 10,
            math.floor((min(b[1] for b in boxes) - 10) / 10) * 10,
            math.ceil((max(b[2] for b in boxes) + 10) / 10) * 10,
            math.ceil((max(b[3] for b in boxes) + 10) / 10) * 10]
    offset = [22 + crop[0] // 10, 27 + crop[1] // 10]
    size = [crop[2] - crop[0] + 10, crop[3] - crop[1]]
    if min(offset) < 0 or offset[0] + size[0] // 10 > 96 or offset[1] + size[1] // 10 > 96:
        raise ValueError("Export exceeds native96 cell")
    def place(image):
        canvas = Image.new("RGBA", size)
        canvas.paste(image.crop(crop), (4, 0))
        return canvas
    frames, records = {}, []
    for name, image in images.items():
        frame = place(image)
        file = args.out / "frames" / (name + "_HD_10x.png")
        frame.save(file)
        frames[name] = frame
        records.append({"name": name, "image": "frames/" + file.name, "sha256": digest(file),
                        "native_frame": metadata[name]["native_frame"],
                        "prompt_id": metadata[name]["prompt_id"],
                        "history_sha256": digest(args.source / next(p.get("generation_folder", name)
                            for p in recipe["poses"] if p["name"] == name) / "history.json")})
    for alias, name in recipe["duplicate_outputs"].items():
        frames[alias] = frames[name]
        frames[alias].save(args.out / "frames" / (alias + "_HD_10x.png"))
    reference = Image.new("RGBA", (512, 512))
    reference.paste(Image.open(args.source / "reference/Walking-01-user.png").convert("RGBA"), (86, 0))
    place(reference).save(args.out / "reference.png")
    static = ["Idle-01", "Ducking-01", "Jumping-01"]
    stairs = [f"going-upstairs-{i:02d}" for i in range(1, 7)]
    sheet(frames, static, args.out / "Drei_Posen.png")
    sheet(frames, stairs, args.out / "Treppe_Alle.png")
    frames[stairs[0]].save(args.out / "Treppe.webp", save_all=True,
                          append_images=[frames[n] for n in stairs[1:]], duration=130, loop=0, lossless=True)
    names = static + stairs
    write(args.out / "placement.json", {"status": "exported_for_visual_review", "scale": 10,
          "working_source_origin": [22.4, 27], "crop": crop, "left_padding": 4,
          "frame_size": size, "offset": offset, "display_size": [v // 10 for v in size],
          "root_in_png": [260 - crop[0], 210 - crop[1]],
          "common_20_to_10_reduction": any(m.get("working_scale") == 20 for m in metadata.values()),
          "per_pose_rescaling": False, "walking_unchanged": True,
          "duplicate_outputs": recipe["duplicate_outputs"], "frames": records})
    page = '''<!doctype html><meta charset="utf-8"><title>Simon: neues Design</title>
<style>body{font:18px system-ui;background:#24262b;color:white;text-align:center}img{max-height:72vh;background:#aaa}button,select{font:inherit;padding:8px;margin:8px}.pair{display:flex;gap:24px;justify-content:center}</style>
<h1>Simon im Lauf-Design</h1><div class="pair"><div>Deine Lauf-Vorlage<br><img src="reference.png"></div><div id="pose"><span id="name"></span><br><img id="image"></div></div>
<p><button id="prev">Zurück</button><button id="next">Nächstes Bild</button><select id="select"></select></p>
<p><a href="Drei_Posen.png">Die drei Posen</a> · <a href="Treppe_Alle.png">Alle Treppenbilder</a> · <a href="Treppe.webp">Treppe in Bewegung</a></p>
<script>const names=NAMES;let i=0;const sel=document.querySelector('#select');names.forEach(n=>sel.add(new Option(n,n)));function show(){sel.selectedIndex=i;document.querySelector('#name').textContent=names[i];document.querySelector('#image').src='frames/'+names[i]+'_HD_10x.png'}document.querySelector('#next').onclick=()=>{i=(i+1)%names.length;show()};document.querySelector('#prev').onclick=()=>{i=(i+names.length-1)%names.length;show()};sel.onchange=()=>{i=sel.selectedIndex;show()};show();</script>'''.replace("NAMES", json.dumps(names))
    (args.out / "Vorschau.html").write_text(page, encoding="utf-8")
    with zipfile.ZipFile(args.out / "Neue_Posen_10x.zip", "w", zipfile.ZIP_DEFLATED) as archive:
        for file in [*sorted((args.out / "frames").glob("*.png")), *[args.out / n for n in
                     ("reference.png", "Drei_Posen.png", "Treppe_Alle.png", "Treppe.webp", "placement.json", "Vorschau.html")]]:
            archive.write(file, file.relative_to(args.out).as_posix())
    print(json.dumps({"frames": len(frames), "size": size, "offset": offset, "output": str(args.out.resolve())}))


if __name__ == "__main__":
    main()
