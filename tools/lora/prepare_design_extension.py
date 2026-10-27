"""Prepare native-aligned poses with the user's Photoshop walking design.

CPU preparation only. Existing direct_edit_walk batch/collect performs local
reference editing. No game writes, image generation, source changes or training.
"""
import argparse
from pathlib import Path
import shutil

import numpy as np
from PIL import Image

from repaint_walk_parts import read, write, digest


PROMPT = (
    "Redraw the man in image 1 as exactly the same painted character as image 2. "
    "Image 1 specifies ONLY the pose: preserve its head position, arm bends, hands, "
    "knees and both feet in their exact positions. Image 2 specifies his face, "
    "shoulder-length brown hair, athletic build and entire costume. Use the same "
    "outlined painted style, warm tan skin, black and gold shoulder and torso armor, "
    "closed abdomen, brown gold belt, short black skirt with vertical gold borders, "
    "bare upper thighs and fitted black gold shin armor and boots as image 2. "
    "Keep the round gold back medallion and its narrow vertical gold strap where "
    "the back is visible. Exactly two arms and two legs, five fingers per hand. "
    "Same body size and position as image 1, complete head and feet, gray background. "
    "No pixelation, headband, long skirt tail, extra limbs or separate knee pads. "
)


def composite(rgba):
    background = Image.new("RGBA", rgba.size, (64, 64, 64, 255))
    background.alpha_composite(rgba)
    return background.convert("RGB")


def tile(atlas, row):
    cell = row["cell"]
    return atlas.crop((cell % 8 * 96, cell // 8 * 96,
                       cell % 8 * 96 + 96, cell // 8 * 96 + 96))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--pack", type=Path, required=True)
    p.add_argument("--template", type=Path, required=True)
    p.add_argument("--sources", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    inputs = args.out / "reference"
    inputs.mkdir(parents=True, exist_ok=False)
    pack, template = read(args.pack / "character.json"), read(args.template / "character.json")
    atlas = Image.open(args.template / "body.png").convert("RGBA")
    pack_atlas = Image.open(args.pack / "body.png").convert("RGBA")
    rows = {f["label"]: f for f in pack["frames"]}
    walking = Image.open(args.pack / "Walking-01_HD_10x.png").convert("RGBA")
    if walking.size != (330, 510):
        raise ValueError("Expected the installed Photoshop walking canvas")
    shutil.copy2(args.pack / "Walking-01_HD_10x.png", inputs / "Walking-01-user.png")
    reference = Image.new("RGBA", (512, 512))
    reference.paste(walking, (86, 0))  # Installed root170 +86 = working root256.
    composite(reference).save(inputs / "design.png")
    targets = []
    for name in ("Idle-01", "Ducking-01", "Jumping-01"):
        frame = rows[name]
        native = tile(pack_atlas, frame)
        original = args.pack / frame["hd"]["image"]
        rgba = Image.open(original).convert("RGBA")
        box = native.getchannel("A").getbbox()
        if rgba.size != ((box[2] - box[0]) * 10, (box[3] - box[1]) * 10):
            raise ValueError("Original HD pose no longer matches native cropped size: " + name)
        pose = Image.new("RGBA", (512, 512))
        pose.paste(rgba, (round((box[0] - 22.4) * 10), (box[1] - 27) * 10))
        action = {"Idle-01": "standing still with both feet planted",
                  "Ducking-01": "crouching on one knee",
                  "Jumping-01": "jumping with one knee raised"}[name]
        targets.append((name, frame, native, pose, original, action))
    duplicates, seen = {}, {}
    for source in sorted(args.sources.glob("going-upstairs-0*.png")):
        im = Image.open(source).convert("RGBA")
        im = im.crop(im.getchannel("A").getbbox())
        mask = np.array(im)[:, :, 3] > 0
        candidates = []
        for frame in template["frames"]:
            native = tile(atlas, frame)
            box = native.getchannel("A").getbbox()
            if box and (box[2] - box[0], box[3] - box[1]) == im.size:
                difference = int(np.sum(mask != (np.array(native.crop(box))[:, :, 3] > 0)))
                candidates.append((difference, frame["id"], frame))
        candidates.sort(key=lambda x: (x[0], x[1]))
        if not candidates or candidates[0][0] > 1:
            raise ValueError("No exact native stair mapping: " + source.name)
        frame = candidates[0][2]
        if frame["id"] in seen:
            previous = seen[frame["id"]]
            if im.tobytes() != previous[1].tobytes():
                raise ValueError("Same native shape but different supplied stair pixels")
            duplicates[source.stem] = previous[0]
            continue
        seen[frame["id"]] = (source.stem, im)
        native = tile(atlas, frame)
        pose = native.transform((512, 512), Image.Transform.AFFINE,
                                (.1, 0, 22.4, 0, .1, 27), Image.Resampling.NEAREST)
        targets.append((source.stem, frame, native, pose, source,
                        "stepping up an invisible staircase, in precisely the shown climbing pose"))
    records = []
    for name, frame, native, pose, original, action in targets:
        folder = args.out / name
        folder.mkdir(exist_ok=False)
        shutil.copy2(original, folder / ("original-" + original.name))
        native.save(folder / "native.png")
        pose.save(folder / "source-rgba.png")
        composite(pose).save(folder / "source.png")
        composite(pose).save(folder / "input.png")
        Image.new("L", (512, 512), 255).save(folder / "selection.png")
        shutil.copy2(inputs / "design.png", folder / "reference-2.png")
        prompt = PROMPT + "The action is " + action + "."
        write(folder / "job.json", {
            "schema": "simon-new-design-pose-v1", "status": "prepared",
            "job": {"frame": name + ".png", "crop": [0, 0, 512, 512], "prompt": prompt},
            "references": [{"prepared": "reference-2.png", "path": str(inputs / "Walking-01-user.png"),
                            "sha256": digest(inputs / "Walking-01-user.png")}],
            "native_frame": frame, "source_sha256": digest(original), "local_only": True,
            "game_installed": False, "artistic_approval": False,
            "selection_sha256": digest(folder / "selection.png"),
            "conditioning_sha256": digest(folder / "input.png"),
            "working_scale": 10, "working_source_origin": [22.4, 27], "root": [256, 210]})
        records.append({"name": name, "id": frame["id"], "source": str(original),
                        "source_sha256": digest(original), "prompt": prompt})
    write(args.out / "extension.json", {"status": "prepared", "local_only": True,
          "walking_reference_sha256": digest(inputs / "Walking-01-user.png"),
          "walking_game_files_unchanged": True, "working_scale": 10,
          "working_canvas": [512, 512], "root": [256, 210],
          "duplicate_outputs": duplicates, "poses": records})
    print(f"Prepared {len(records)} distinct poses; aliases: {duplicates}")


if __name__ == "__main__":
    main()
