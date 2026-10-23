"""Local neural sprite corrections through the existing ComfyUI queue.

prepare is CPU-only. submit never starts a second inference process or unloads
another job. collect records the executed graph and composites only the painted
selection. Source art, Python environments and original model weights stay intact.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import uuid
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import ProxyHandler, Request, build_opener

import numpy as np
from PIL import Image, ImageDraw, ImageFilter


SERVER = "http://127.0.0.1:8188"
OPENER = build_opener(ProxyHandler({}))


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(path)


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def request(route, data=None, content_type=None, raw=False):
    if isinstance(data, dict):
        data, content_type = json.dumps(data).encode(), "application/json"
    req = Request(SERVER + route, data=data,
                  headers={"Content-Type": content_type} if content_type else {})
    try:
        with OPENER.open(req, timeout=30) as response:
            payload = response.read()
    except HTTPError as exc:
        raise RuntimeError(exc.read().decode(errors="replace")[:6000]) from exc
    return payload if raw else (json.loads(payload) if payload else None)


def upload(path, folder):
    boundary = "simon" + uuid.uuid4().hex
    body = bytearray()
    for key, value in (("type", "input"), ("subfolder", folder), ("overwrite", "false")):
        body.extend(f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n'.encode())
    body.extend(f'--{boundary}\r\nContent-Disposition: form-data; name="image"; filename="{path.name}"\r\nContent-Type: image/png\r\n\r\n'.encode())
    body.extend(path.read_bytes())
    body.extend(f"\r\n--{boundary}--\r\n".encode())
    result = request("/upload/image", bytes(body), f"multipart/form-data; boundary={boundary}")
    return (result.get("subfolder", "").strip("/") + "/" + result["name"]).lstrip("/")


def prepare(recipe_path, part, out):
    recipe = read(recipe_path)
    job = recipe["parts"][part]
    if out.exists():
        raise FileExistsError("Choose a new output directory")
    base = Path(recipe["baseline"])
    frame = job["frame"]
    source = base / "decoded" / frame
    alpha_source = base / "packaged/rgba-full" / frame
    control = base / "guides-hd" / frame
    reference = base / "decoded" / job["reference"]
    box = job["crop"]
    if box[2] - box[0] != box[3] - box[1] or (box[2] - box[0]) % 64:
        raise ValueError("Use a square crop in whole 64-pixel blocks, without stretching")
    out.mkdir(parents=True)
    for name, file in (("source-full.png", source), ("source-alpha.png", alpha_source)):
        shutil.copy2(file, out / name)
    initial = Image.open(source).convert("RGB")
    # Flat material hints are only conditioning, never finished sprite pixels.
    # Let diffusion draw anatomy instead of stretching another frame's muscles.
    for hint in job.get("material_hints", []):
        selection = Image.new("L", initial.size)
        ImageDraw.Draw(selection).polygon([tuple(p) for p in hint["polygon"]], fill=255)
        selection = selection.filter(ImageFilter.GaussianBlur(2))
        initial = Image.composite(Image.new("RGB", initial.size, tuple(hint["color"])),
                                  initial, selection)
    initial.crop(box).save(out / "input.png")
    # Original native motion guide; no wrong HD shorts/armor edges are added.
    Image.open(control).convert("RGB").crop(box).save(out / "control.png")
    Image.open(reference).convert("RGB").crop(job["reference_crop"]).save(out / "reference.png")
    mask = Image.new("L", (1024, 1024))
    draw = ImageDraw.Draw(mask)
    for polygon in job["selections"]:
        draw.polygon([tuple(p) for p in polygon], fill=255)
    mask = mask.filter(ImageFilter.MaxFilter(17))
    mask.crop(box).save(out / "mask.png")
    mask.filter(ImageFilter.GaussianBlur(5)).crop(box).save(out / "blend.png")
    preview = Image.open(source).convert("RGB")
    shade = Image.new("RGB", preview.size, (40, 200, 230))
    preview = Image.composite(Image.blend(preview, shade, .4), preview, mask)
    ImageDraw.Draw(preview).rectangle(box, outline=(255, 220, 0), width=3)
    preview.save(out / "selection-review.png")
    write(out / "job.json", {"schema": "simon-neural-part-repaint-v1", "status": "prepared",
          "part": part, "settings": {**recipe["settings"], **job.get("settings", {})}, "job": job,
          "source_sha256": digest(source), "alpha_sha256": digest(alpha_source),
          "reference_sha256": digest(reference), "guide_sha256": digest(control),
          "prepared_sha256": {p.name: digest(p) for p in out.glob("*.png")},
          "local_only": True, "game_installed": False, "artistic_approval": False})


def graph_for(settings, job, images, prefix):
    graph = {}
    def add(key, kind, **inputs):
        graph[str(key)] = {"class_type": kind, "inputs": inputs}
    add(1, "DiffusersLoader", model_path="sdxl")
    add(2, "LoraLoaderModelOnly", model=["1", 0], lora_name=settings["lora_name"],
        strength_model=settings["lora_scale"])
    add(3, "CLIPTextEncode", clip=["1", 1], text=job["positive"])
    add(4, "CLIPTextEncode", clip=["1", 1], text=job["negative"])
    add(5, "LoadImage", image=images["input"])
    add(6, "LoadImageMask", image=images["mask"], channel="red")
    add(7, "LoadImage", image=images["control"])
    add(8, "ControlNetLoader", control_net_name="canny-sdxl/diffusion_pytorch_model.safetensors")
    add(9, "ControlNetApplyAdvanced", positive=["3", 0], negative=["4", 0],
        control_net=["8", 0], image=["7", 0], strength=settings["control_scale"],
        start_percent=0., end_percent=.9, vae=["1", 2])
    add(10, "LoadImage", image=images["reference"])
    add(11, "IPAdapterModelLoader", ipadapter_file="ip-adapter-plus_sdxl_vit-h.safetensors")
    add(12, "CLIPVisionLoader", clip_name="model.safetensors")
    add(13, "IPAdapterAdvanced", model=["2", 0], ipadapter=["11", 0], image=["10", 0],
        clip_vision=["12", 0], weight=settings["reference_scale"], weight_type="style transfer",
        combine_embeds="average", start_at=0., end_at=1., embeds_scaling="V only")
    # Clearing selected RGB avoids treating the wrong metal shorts as anatomy.
    # The mask is a selection for neural drawing, not an alpha-erasure result.
    if job.get("initialization") == "material_hints":
        add(14, "VAEEncode", pixels=["5", 0], vae=["1", 2])
        add(19, "SetLatentNoiseMask", samples=["14", 0], mask=["6", 0])
        latent = ["19", 0]
    else:
        add(14, "VAEEncodeForInpaint", pixels=["5", 0], vae=["1", 2], mask=["6", 0], grow_mask_by=8)
        latent = ["14", 0]
    add(15, "KSampler", model=["13", 0], positive=["9", 0], negative=["9", 1],
        latent_image=latent, seed=settings["seed"], steps=settings["steps"],
        cfg=5., sampler_name="euler", scheduler="normal", denoise=settings.get("denoise", 1.))
    add(16, "VAEDecodeTiled", samples=["15", 0], vae=["1", 2], tile_size=512,
        overlap=64, temporal_size=64, temporal_overlap=8)
    add(17, "SaveImage", images=["16", 0], filename_prefix=prefix)
    return graph


def export_comfy_lora(source, target, expected):
    """Copy tensor values unchanged, using ComfyUI's supported Kohya key names."""
    from safetensors.numpy import load_file, save_file
    provenance = target.with_suffix(".source.json")
    if target.exists():
        if not provenance.exists():
            raise FileExistsError("Do not replace an existing model without its provenance")
        record = read(provenance)
        if record["source_sha256"] != expected or record["export_sha256"] != digest(target):
            raise ValueError("Existing LoRA export does not match its source")
        return record
    weights = load_file(str(source))
    converted = {}
    for key, value in weights.items():
        if not key.startswith("unet."):
            raise ValueError("Only the known UNet-only Simon adapter is supported")
        stem, direction = key.removeprefix("unet.").split(".lora.")
        if direction not in ("down.weight", "up.weight"):
            raise ValueError("Unexpected adapter tensor: " + key)
        name = "lora_unet_" + stem.replace(".", "_") + ".lora_" + direction
        if name in converted:
            raise ValueError("LoRA key conversion collision")
        converted[name] = value
    target.parent.mkdir(parents=True, exist_ok=True)
    save_file(converted, str(target), metadata={"source_sha256": expected,
              "note": "Key names only; original tensor values and rank16 alpha16 unchanged"})
    record = {"source_sha256": expected, "export_sha256": digest(target),
              "tensor_count": len(converted), "values_unchanged": True,
              "format": "ComfyUI Kohya keys; rank16 alpha16"}
    write(provenance, record)
    return record


def submit(out, model_directory):
    meta = read(out / "job.json")
    if meta["status"] != "prepared":
        raise RuntimeError("This job has already been submitted; use status or collect")
    queue = request("/queue")
    if queue.get("queue_running") or queue.get("queue_pending"):
        raise RuntimeError("GPU queue busy: sprite job not submitted. Leave the landscape running.")
    stats = request("/system_stats")
    device = stats.get("devices", [{}])[0]
    if device.get("type") == "cpu" or not any(v in str(device).lower() for v in ("amd", "radeon", "gfx1150")):
        raise RuntimeError("Expected the existing Radeon ComfyUI server")
    settings = meta["settings"]
    source_lora = Path(settings["lora_source"])
    if digest(source_lora) != settings["lora_sha256"]:
        raise ValueError("Original trained LoRA does not match its recorded hash")
    target_lora = model_directory / "loras" / settings["lora_name"]
    lora_export = export_comfy_lora(source_lora, target_lora, settings["lora_sha256"])
    info = request("/object_info")
    for filename, sha in meta["prepared_sha256"].items():
        if digest(out / filename) != sha:
            raise ValueError("Prepared image changed: " + filename)
    folder = "simon_repaint/" + uuid.uuid4().hex
    images = {key: upload(out / (key + ".png"), folder)
              for key in ("input", "mask", "control", "reference")}
    graph = graph_for(settings, meta["job"], images, folder + "/generated")
    for node in graph.values():
        kind = node["class_type"]
        if kind not in info:
            raise RuntimeError("Missing existing ComfyUI node: " + kind)
        for key, spec in info[kind]["input"]["required"].items():
            value = node["inputs"].get(key)
            if isinstance(spec[0], list) and isinstance(value, str) and kind not in ("LoadImage", "LoadImageMask"):
                matches = [v for v in spec[0] if v.replace("\\", "/") == value.replace("\\", "/")]
                if not matches:
                    raise ValueError(f"Unavailable {kind}.{key}: {value}")
                node["inputs"][key] = matches[0]
    write(out / "workflow_api.json", graph)
    # Save submission intent first; an ambiguous HTTP outcome must not be
    # silently retried and produce a second expensive GPU job.
    meta.update(status="submitting", client_id=uuid.uuid4().hex, gpu_before=stats,
                lora_export=lora_export)
    write(out / "job.json", meta)
    response = request("/prompt", {"prompt": graph, "client_id": meta["client_id"]})
    if not response.get("prompt_id") or response.get("node_errors"):
        meta.update(status="rejected", submission=response)
        write(out / "job.json", meta)
        raise RuntimeError(str(response))
    meta.update(status="queued", prompt_id=response["prompt_id"])
    write(out / "job.json", meta)
    print(json.dumps({"status": "queued", "prompt_id": meta["prompt_id"]}))


def collect(out):
    meta = read(out / "job.json")
    ident = meta["prompt_id"]
    history = request("/history/" + ident).get(ident)
    if not history:
        print(json.dumps({"status": "waiting", "prompt_id": ident}))
        return
    write(out / "history.json", history)
    if history["status"].get("status_str") == "error":
        meta.update(status="failed")
        write(out / "job.json", meta)
        raise RuntimeError("Sprite generation failed; see history.json")
    if not history["status"].get("completed"):
        print(json.dumps({"status": "waiting", "prompt_id": ident}))
        return
    if history["prompt"][2] != read(out / "workflow_api.json"):
        raise ValueError("Executed graph differs from the submitted sprite job")
    image = history["outputs"]["17"]["images"][0]
    (out / "generated.png").write_bytes(request("/view?" + urlencode(image), raw=True))
    original = Image.open(out / "source-full.png").convert("RGB")
    patch = Image.open(out / "generated.png").convert("RGB")
    box = meta["job"]["crop"]
    if patch.size != (box[2] - box[0], box[3] - box[1]):
        raise ValueError("Generated crop was stretched or resized unexpectedly")
    blend = Image.open(out / "blend.png").convert("L")
    original.paste(Image.composite(patch, original.crop(box), blend), box)
    original.save(out / "repainted-full.png")
    # Exact preservation outside the feathered selection is a real invariant.
    mask = Image.new("L", original.size)
    mask.paste(blend, box)
    a = np.array(Image.open(out / "source-full.png").convert("RGB"))
    b = np.array(original)
    unchanged = bool(np.array_equal(a[np.array(mask) == 0], b[np.array(mask) == 0]))
    if not unchanged:
        raise ValueError("Pixels outside the edit selection changed")
    original_source = Image.open(out / "source-full.png").convert("RGB")
    compare = Image.new("RGB", (1024, 1024), (216, 216, 216))
    compare.paste(original_source.resize((512, 512)), (0, 0))
    compare.paste(original.resize((512, 512)), (512, 0))
    compare.paste(original_source.crop(box).resize((512, 512)), (0, 512))
    compare.paste(patch.resize((512, 512)), (512, 512))
    compare.save(out / "comparison.png")
    meta.update(status="rendered_needs_visual_review", unchanged_outside_selection=unchanged,
                generated_sha256=digest(out / "generated.png"), history_sha256=digest(out / "history.json"))
    write(out / "job.json", meta)
    print(json.dumps({"status": meta["status"], "unchanged_outside_selection": unchanged}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    prep = sub.add_parser("prepare")
    prep.add_argument("--recipe", type=Path, required=True)
    prep.add_argument("--part", required=True)
    prep.add_argument("--out", type=Path, required=True)
    run = sub.add_parser("submit")
    run.add_argument("--out", type=Path, required=True)
    run.add_argument("--model-directory", type=Path, required=True)
    get = sub.add_parser("collect")
    get.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "prepare":
        prepare(args.recipe, args.part, args.out)
    elif args.command == "submit":
        submit(args.out, args.model_directory)
    else:
        collect(args.out)


if __name__ == "__main__":
    main()
