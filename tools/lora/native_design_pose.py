"""Prepare/submit one native-contour SDXL pose using the Photoshop design.

Uses only installed local ComfyUI models, the shared serial queue and known
native atlas cells. No environment/model changes or new training.
"""
import argparse
from pathlib import Path
import shutil
import uuid

import cv2
import numpy as np
from PIL import Image, ImageFilter

from direct_edit_walk import normalize_graph
from repaint_walk_parts import read, write, digest, request, upload


def prepare(source, out, lora_name, trigger, lora_scale, working_size=1024):
    if out.exists():
        raise FileExistsError("Use a fresh pose folder")
    previous = read(source / "job.json")
    name = previous["job"]["frame"].removesuffix(".png")
    out.mkdir(parents=True)
    shutil.copy2(source / "native.png", out / "native.png")
    native = Image.open(out / "native.png").convert("RGBA")
    factor = working_size / 1024
    rgba = native.transform((working_size, working_size), Image.Transform.AFFINE,
                            (.05 / factor, 0, 22.4, 0, .05 / factor, 27), Image.Resampling.BICUBIC)
    rgba.save(out / "source-rgba.png")
    background = Image.new("RGBA", rgba.size, (128, 128, 128, 255))
    background.alpha_composite(rgba)
    color = background.convert("RGB")
    color.save(out / "source.png")
    Image.new("L", rgba.size, 255).save(out / "selection.png")
    softened = color.filter(ImageFilter.GaussianBlur(8 * factor))
    silhouette = rgba.getchannel("A").filter(ImageFilter.GaussianBlur(3 * factor))
    edges = np.maximum(cv2.Canny(np.array(softened), 65, 140),
                       cv2.Canny(np.array(silhouette), 65, 140))
    Image.fromarray(edges).convert("RGB").save(out / "control.png")
    canonical = Image.open(previous["references"][0]["path"]).convert("RGBA")
    reference = Image.new("RGBA", (512, 512), (128, 128, 128, 255))
    reference.alpha_composite(canonical, (86, 0))
    reference.convert("RGB").save(out / "reference.png")
    action = {"Idle-01": "standing with both feet planted, elbows bent",
              "Ducking-01": "crouching on one knee, elbows bent",
              "Jumping-01": "jumping with one knee lifted, elbows bent"}.get(
                  name, "one knee lifted for a step up, elbows bent, precise pose from the outline")
    positive = (trigger + ", full body painted game character, athletic man, shoulder-length brown hair, "
                "black gold armor, closed abdomen, brown gold belt, short black gold skirt, bare thighs, "
                "black gold greaves and boots, sharp illustrated outlines, plain gray background. " + action)
    negative = ("extra hands, extra arms, extra legs, duplicate limbs, deformed anatomy, staircase, stairs, "
                "scenery, ground, photograph, plastic, 3d render, pixel art, text, long hair, headband, "
                "knee pads, protruding knee guards, long skirt tail, shorts, thigh armor")
    write(out / "job.json", {"schema": "simon-native-design-sdxl-v1", "status": "prepared",
          "local_only": True, "game_installed": False, "artistic_approval": False,
          "pose_source_job": str(source.resolve()), "native_frame": previous["native_frame"],
          "references": previous["references"], "working_source_origin": [22.4, 27],
          "root": [512 * factor, 420 * factor],
          "job": {"frame": name + ".png", "crop": [0, 0, working_size, working_size],
                  "positive": positive, "negative": negative},
          "working_scale": 20 * factor, "working_size": working_size, "output_scale": 10,
          "source_sha256": digest(out / "native.png"),
          "control_sha256": digest(out / "control.png"),
          "reference_sha256": digest(out / "reference.png"),
          "settings": {"steps": 36, "control_scale": 1.1, "control_end": .95,
                       "lora_scale": lora_scale, "lora_name": lora_name,
                       "trigger": trigger, "ip_scale": .9, "seed": 20261021}})


def graph(meta, control, reference, prefix):
    g, settings = {}, meta["settings"]
    def add(key, kind, **inputs):
        g[str(key)] = {"class_type": kind, "inputs": inputs}
    add(1, "DiffusersLoader", model_path="sdxl")
    add(2, "LoraLoaderModelOnly", model=["1", 0], lora_name=settings["lora_name"],
        strength_model=settings["lora_scale"])
    add(3, "CLIPTextEncode", clip=["1", 1], text=meta["job"]["positive"])
    add(4, "CLIPTextEncode", clip=["1", 1], text=meta["job"]["negative"])
    add(7, "LoadImage", image=control)
    add(8, "ControlNetLoader", control_net_name="canny-sdxl/diffusion_pytorch_model.safetensors")
    add(9, "ControlNetApplyAdvanced", positive=["3", 0], negative=["4", 0],
        control_net=["8", 0], image=["7", 0], strength=settings["control_scale"],
        start_percent=0., end_percent=settings["control_end"], vae=["1", 2])
    add(10, "LoadImage", image=reference)
    add(11, "IPAdapterModelLoader", ipadapter_file="ip-adapter-plus_sdxl_vit-h.safetensors")
    add(12, "CLIPVisionLoader", clip_name="model.safetensors")
    add(13, "IPAdapterAdvanced", model=["2", 0], ipadapter=["11", 0], image=["10", 0],
        clip_vision=["12", 0], weight=settings["ip_scale"], weight_type="style transfer",
        combine_embeds="average", start_at=0., end_at=1., embeds_scaling="V only")
    size = meta.get("working_size", 1024)
    add(14, "EmptyLatentImage", width=size, height=size, batch_size=1)
    add(15, "KSampler", model=["13", 0], positive=["9", 0], negative=["9", 1],
        latent_image=["14", 0], seed=settings["seed"], steps=settings["steps"],
        cfg=settings.get("cfg", 6.), sampler_name="dpmpp_2m", scheduler="normal", denoise=1.)
    add(16, "VAEDecodeTiled", samples=["15", 0], vae=["1", 2], tile_size=512,
        overlap=64, temporal_size=64, temporal_overlap=8)
    add(20, "SaveImage", images=["16", 0], filename_prefix=prefix)
    return normalize_graph(g)


def submit(out):
    meta = read(out / "job.json")
    if meta["status"] != "prepared":
        raise RuntimeError("Already submitted; collect instead")
    q = request("/queue")
    if q["queue_running"] or q["queue_pending"]:
        raise RuntimeError("Shared queue busy")
    folder = "simon_native_design/" + uuid.uuid4().hex
    control = upload(out / "control.png", folder)
    reference = upload(out / "reference.png", folder)
    workflow = graph(meta, control, reference, folder + "/edited")
    write(out / "workflow_api.json", workflow)
    meta.update(status="submitting", client_id=uuid.uuid4().hex, server_port=8188,
                backend="radeon_sdxl_native_canny_ipadapter", output_node="20",
                output_prefix=folder + "/edited")
    write(out / "job.json", meta)
    result = request("/prompt", {"prompt": workflow, "client_id": meta["client_id"]})
    if not result.get("prompt_id") or result.get("node_errors"):
        meta.update(status="rejected", response=result)
        write(out / "job.json", meta)
        raise RuntimeError(str(result))
    meta.update(status="queued", prompt_id=result["prompt_id"])
    write(out / "job.json", meta)
    print(meta["prompt_id"])


def batch_submit(parts, report):
    if report.exists() or not 1 <= len(parts) <= 8:
        raise ValueError("Use1-8 prepared poses and a fresh batch report")
    q = request("/queue")
    if q["queue_running"] or q["queue_pending"]:
        raise RuntimeError("Shared queue busy")
    metadata = [read(folder / "job.json") for folder in parts]
    if any(m["status"] != "prepared" for m in metadata):
        raise RuntimeError("Only new prepared poses can be submitted")
    if any(m["settings"] != metadata[0]["settings"] or
           m["reference_sha256"] != metadata[0]["reference_sha256"] for m in metadata):
        raise ValueError("Batch must share the same trained design and settings")
    prefix = "simon_native_batch/" + uuid.uuid4().hex
    reference = upload(parts[0] / "reference.png", prefix)
    shared = {"1", "2", "8", "10", "11", "12", "13"}
    merged, outputs = {}, []
    for i, (folder, meta) in enumerate(zip(parts, metadata)):
        subfolder = prefix + "/" + folder.name
        control = upload(folder / "control.png", subfolder)
        g = graph(meta, control, reference, subfolder + "/edited")
        def key(old):
            return old if old in shared else str(int(old) + 100 * i)
        for old, node in g.items():
            if i and old in shared:
                continue
            inputs = {k: [key(v[0]), v[1]] if isinstance(v, list) else v for k, v in node["inputs"].items()}
            merged[key(old)] = {"class_type": node["class_type"], "inputs": inputs}
        outputs.append({"folder": str(folder.resolve()), "output_node": key("20"),
                        "output_prefix": subfolder + "/edited"})
    client = uuid.uuid4().hex
    write(report, {"status": "submitting", "client_id": client, "outputs": outputs})
    for folder, meta, output in zip(parts, metadata, outputs):
        write(folder / "workflow_api.json", merged)
        meta.update(status="submitting", client_id=client, server_port=8188,
                    backend="radeon_sdxl_native_canny_ipadapter", **output)
        write(folder / "job.json", meta)
    response = request("/prompt", {"prompt": merged, "client_id": client})
    if not response.get("prompt_id") or response.get("node_errors"):
        write(report, {"status": "rejected", "response": response})
        raise RuntimeError(str(response))
    for folder, meta in zip(parts, metadata):
        meta.update(status="queued", prompt_id=response["prompt_id"])
        write(folder / "job.json", meta)
    write(report, {"status": "queued", "prompt_id": response["prompt_id"], "outputs": outputs})
    print(response["prompt_id"])


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("command", choices=("prepare", "submit", "batch"))
    p.add_argument("--source", type=Path)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--lora-name", default="Simon_local_600_rank16.safetensors")
    p.add_argument("--trigger", default="scivsimonv1")
    p.add_argument("--lora-scale", type=float, default=.65)
    p.add_argument("--working-size", type=int, choices=(512, 1024), default=1024,
                   help="Internal render canvas; game export remains10x")
    p.add_argument("--parts", type=Path, nargs="+")
    args = p.parse_args()
    if args.command == "prepare":
        prepare(args.source, args.out, args.lora_name, args.trigger, args.lora_scale, args.working_size)
    elif args.command == "submit":
        submit(args.out)
    else:
        batch_submit(args.parts, args.out)


if __name__ == "__main__":
    main()
