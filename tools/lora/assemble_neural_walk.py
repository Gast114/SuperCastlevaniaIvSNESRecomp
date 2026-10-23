"""Export reviewed neural walk corrections as RGBA, using one shared 20x canvas.

The existing common reference01 face/upper-body corrections are retained. All
rejected lower-body warps and erased hems are discarded: lower pixels start
from the original native-motion draft and receive actual neural edits only.
No per-frame resizing, limb warping, hand-drawn muscle or hem erasure.
"""
import argparse
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from repaint_walk_parts import read, write, digest


EDITS = {
    "Walking-01.png": ["repair-01-master"],
    "Walking-02.png": ["repair-02-hem"],
    "Walking-03.png": ["03-thigh-style-bf16", "repair-03-gap-guided"],
    "Walking-04.png": ["repair-04-hem-guided"],
    "Walking-05.png": ["repair-05-lower", "repair-05-gap-guided"],
    "Walking-06.png": ["repair-06-emblem", "repair-06-lower"],
}
# The neural01 result added the correct medallion but ignored closed abdomen.
# Retain the already closed upper armor and use only its successful back edit.
SELECTION_SUBSETS = {"repair-01-master": [0]}


def matte(image, session):
    pixels = np.asarray(image, dtype=np.float32)
    tensor = pixels / max(float(pixels.max()), 1.)
    tensor -= np.array([.485, .456, .406], np.float32)
    prediction = session.run(None, {session.get_inputs()[0].name: tensor.transpose(2, 0, 1)[None].copy()})[0][0, 0]
    alpha = (prediction - prediction.min()) / max(float(np.ptp(prediction)), 1e-8)
    alpha[alpha < .012] = 0
    alpha[alpha > .985] = 1
    rgb = pixels / 255
    border = np.concatenate([rgb[0], rgb[-1], rgb[:, 0], rgb[:, -1]])
    background = np.median(border, axis=0)
    edge = (alpha > .04) & (alpha < .985)
    recovered = (rgb - (1 - alpha[..., None]) * background) / np.maximum(alpha[..., None], .04)
    rgb[edge] = np.clip(recovered[edge], 0, 1)
    return rgb, alpha


def blend(base, rgb, alpha, selection):
    old = base.astype(np.float32) / 255
    weight = selection.astype(np.float32) / 255
    new_alpha = old[:, :, 3] * (1 - weight) + alpha * weight
    premul = (old[:, :, :3] * old[:, :, 3, None] * (1 - weight[..., None]) +
              rgb * alpha[..., None] * weight[..., None])
    color = premul / np.maximum(new_alpha[..., None], 1e-8)
    color[new_alpha == 0] = 0
    mixed = np.uint8(np.clip(np.rint(np.dstack((color, new_alpha)) * 255), 0, 255))
    result = base.copy()
    result[selection > 0] = mixed[selection > 0]
    if not np.array_equal(base[selection == 0], result[selection == 0]):
        raise ValueError("Unselected RGBA pixels changed")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True, help="Original native-motion packaged directory")
    parser.add_argument("--common-upper", type=Path, required=True, help="Existing edited1024 RGBA with common reference01 face")
    parser.add_argument("--edits", type=Path, required=True)
    parser.add_argument("--matting-model", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise FileExistsError("Choose a fresh assembly directory")
    # Do not allocate matting alongside an active Comfy inference job.
    from repaint_walk_parts import request
    queue = request("/queue")
    if queue.get("queue_running") or queue.get("queue_pending"):
        raise RuntimeError("Wait until shared-RAM inference has finished")
    import onnxruntime as ort
    options = ort.SessionOptions()
    options.intra_op_num_threads = 12
    session = ort.InferenceSession(str(args.matting_model), sess_options=options,
                                   providers=["CPUExecutionProvider"])
    args.out.mkdir(parents=True)
    (args.out / "rgba-full").mkdir()
    (args.out / "selections").mkdir()
    records = []
    for frame, parts in EDITS.items():
        original = args.baseline / "rgba-full" / frame
        upper = args.common_upper / frame
        base = np.array(Image.open(original).convert("RGBA"))
        common = np.array(Image.open(upper).convert("RGBA"))
        if base.shape != (1024, 1024, 4) or common.shape != base.shape:
            raise ValueError("All sources must share the original working canvas")
        # All earlier thigh transforms / hem cuts begin below this boundary.
        # At the actual join these two source files must already be identical.
        join, other = base[395:405], common[395:405]
        visible = (join[:, :, 3] > 0) | (other[:, :, 3] > 0)
        if (not np.array_equal(join[:, :, 3], other[:, :, 3]) or
                not np.array_equal(join[visible], other[visible])):
            raise ValueError("Common upper layer would introduce a visible join: " + frame)
        base[:400] = common[:400]
        inputs = []
        for part in parts:
            folder = args.edits / part
            meta = read(folder / "job.json")
            if meta["status"] not in ("rendered_needs_visual_review", "accepted_for_preview"):
                raise ValueError("Edit is not complete: " + part)
            if not meta.get("unchanged_outside_selection"):
                raise ValueError("Edit lacks source-preservation evidence: " + part)
            if meta["job"]["frame"] != frame:
                raise ValueError("Wrong pose attached to " + part)
            image = Image.open(folder / "edited-full.png").convert("RGB")
            rgb, alpha = matte(image, session)
            selection_image = Image.open(folder / "selection.png").convert("L")
            subset = SELECTION_SUBSETS.get(part)
            if subset is not None:
                selection_image = Image.new("L", (1024, 1024))
                draw = ImageDraw.Draw(selection_image)
                for index in subset:
                    draw.polygon([tuple(p) for p in meta["job"]["selections"][index]], fill=255)
                selection_image = selection_image.filter(ImageFilter.MaxFilter(13)).filter(ImageFilter.GaussianBlur(4))
            used_selection = args.out / "selections" / (part + ".png")
            selection_image.save(used_selection)
            selection = np.array(selection_image)
            base = blend(base, rgb, alpha, selection)
            inputs.append({"part": part, "prompt_id": meta["prompt_id"],
                           "rgb_sha256": digest(folder / "edited-full.png"),
                           "selection_sha256": digest(used_selection), "selection_subset": subset,
                           "source_selection_sha256": digest(folder / "selection.png"),
                           "history_sha256": digest(folder / "history.json")})
        output = args.out / "rgba-full" / frame
        Image.fromarray(base).save(output)
        records.append({"frame": frame, "sha256": digest(output), "neural_edits": inputs,
                        "native_motion_sha256": digest(original), "common_upper_sha256": digest(upper)})
        print("Assembled " + frame, flush=True)
    write(args.out / "series.json", {"status": "preview_needs_visual_review", "game_installed": False,
          "method": "Local reference-guided FLUX.2 Klein neural part edits; CPU BF16; ISNet alpha",
          "working_canvas": [1024, 1024], "working_scale": 20, "final_scale": 10,
          "face": "Existing common reference01 face/upper corrections retained above y400; no new body-part transforms",
          "lower_body": "Original native-motion pixels plus neural edits; rejected lower warps/hem alpha cuts discarded",
          "unselected_rgba_preserved": True, "matting_model_sha256": digest(args.matting_model),
          "frames": records})


if __name__ == "__main__":
    main()
