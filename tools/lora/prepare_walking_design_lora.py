"""Snapshot the six installed Photoshop walking frames for a separate LoRA.

CPU-only512 canvas preparation; no resize, training, environment or game writes.
"""
import argparse
from pathlib import Path
import shutil
import zipfile

from PIL import Image

from repaint_walk_parts import write, digest


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--pack", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    for folder in ("train", "holdout", "originals", "alpha"):
        (args.out / folder).mkdir()
    actions = ["walking right with the rear knee bent and rear heel raised",
               "walking right with both knees bent and feet apart",
               "walking right in a wide stride with the forward foot reaching out",
               "walking right with the opposite rear heel raised",
               "walking right with the forward knee raised",
               "walking right in a broad stride"]
    records = []
    with zipfile.ZipFile(args.out / "Walking-Design-Training.zip", "w", zipfile.ZIP_DEFLATED) as archive:
        for i, action in enumerate(actions, 1):
            original = args.pack / f"Walking-{i:02d}_HD_10x.png"
            image = Image.open(original).convert("RGBA")
            if image.size != (330, 510):
                raise ValueError("Expected the installed Photoshop walking canvas")
            stem = f"walking-design-{i:02d}"
            rgba = Image.new("RGBA", (512, 512))
            rgba.paste(image, (86, 0))
            background = Image.new("RGBA", rgba.size, (128, 128, 128, 255))
            background.alpha_composite(rgba)
            prepared = args.out / "train" / (stem + ".png")
            background.convert("RGB").save(prepared)
            rgba.getchannel("A").save(args.out / "alpha" / (stem + ".png"))
            shutil.copy2(original, args.out / "originals" / original.name)
            caption = ("scivwalkv2, full body outlined painted game character, athletic man, "
                       "shoulder-length brown hair, black gold armor, short skirt, bare thighs, "
                       + action + ", plain gray background")
            txt = prepared.with_suffix(".txt")
            txt.write_text(caption + "\n", encoding="utf-8")
            archive.write(prepared, prepared.name)
            archive.write(txt, txt.name)
            records.append({"name": stem, "split": "train", "source": str(original.resolve()),
                            "source_sha256": digest(original), "source_size": list(image.size),
                            "padding_offset": [86, 0], "caption": caption,
                            "prepared_sha256": digest(prepared)})
    write(args.out / "dataset.json", {"status": "prepared_not_trained", "uploaded": False,
          "canvas": [512, 512], "background": [128, 128, 128], "trigger_word": "scivwalkv2",
          "preparation_rescaled_images": False, "native_root": [256, 210],
          "train_count": 6, "holdout_count": 0, "images": records,
          "archive_sha256": digest(args.out / "Walking-Design-Training.zip")})
    print("Prepared6 Photoshop walking images, no scaling or old-design images")


if __name__ == "__main__":
    main()
