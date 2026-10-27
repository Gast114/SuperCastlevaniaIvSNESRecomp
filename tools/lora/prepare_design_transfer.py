"""Prepare a canonical-first local reference edit, using a separate pose guide.

CPU-only preparation. The existing direct_edit_walk submit/batch queues inference.
The walking artwork is copied as conditioning, never edited or installed here.
"""
import argparse
from pathlib import Path
import shutil

from PIL import Image

from repaint_walk_parts import read, write, digest


PROMPT = (
    "Use the EXACT same man and painted style from image 1, with the same face, "
    "shoulder-length brown haircut, lean athletic build, natural tan skin, black "
    "metal armor with gold borders, brown gold belt, short segmented black skirt "
    "with gold strips, completely bare upper thighs and fitted black gold shin "
    "armor and boots. Image 2 specifies ONLY his body pose and position. Transfer "
    "the man from image 1 into exactly that pose: preserve all head, shoulder, "
    "elbow, hand, knee and foot locations of image 2. Do not copy the orange skin "
    "or exaggerated muscles of image 2. Keep the round back medallion and gold "
    "strap from image 1 if visible. Exactly two arms, two hands and two legs. "
    "Leave knees and upper thighs bare. Complete body, head and feet, same scale "
    "as image 2, plain flat gray background. No objects or scenery, no ground, "
    "no extra limbs, no extra knee armor, no long skirt tail."
)

POSE_FIRST_PROMPT = (
    "Edit image 1. Keep its EXACT body pose, silhouette, body angle, joint locations and placement. "
    "Change only the character appearance to match the SAME man from image 2: same face and "
    "shoulder-length brown hairstyle, natural tan skin, lean athletic muscles, black armor with "
    "gold trim, brown gold belt, short black segmented skirt with straight gold strips, bare "
    "upper thighs, fitted black shin armor with diagonal gold straps and matching boots. "
    "Image 2 is ONLY an appearance reference. Do NOT copy its walking pose. Keep both knees, "
    "both feet, shoulders, elbows and both hands exactly where they are in image 1. Keep the "
    "pose and anatomical scale of image 1. Exactly two arms, two hands, two legs. No extra knee "
    "pads, no long skirt tail, no orange skin, no scenery or props. Plain flat gray background, "
    "complete full body."
)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--pose-job", type=Path, required=True)
    p.add_argument("--pose-image", type=Path, help="Default: collected edited-full.png")
    p.add_argument("--canonical", type=Path, required=True, help="Installed330x510 Photoshop walking PNG")
    p.add_argument("--pose-first", action="store_true", help="Use the clear HD pose as primary edit image")
    p.add_argument("--pose-init", action="store_true", help="Initialize from the pose instead of empty noise")
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    if args.pose_init and not args.pose_first:
        raise ValueError("Pose initialization requires --pose-first")
    if args.out.exists():
        raise FileExistsError("Use a fresh design-transfer folder")
    previous = read(args.pose_job / "job.json")
    pose_source = args.pose_image or args.pose_job / "edited-full.png"
    pose = Image.open(pose_source).convert("RGB")
    if pose.size not in ((512, 512), (1024, 1024)):
        raise ValueError("Use a pose on the shared native-coordinate canvas")
    reduced = pose.size == (1024, 1024)
    if reduced:
        pose = pose.resize((512, 512), Image.Resampling.LANCZOS)
    canonical = Image.open(args.canonical).convert("RGBA")
    if canonical.size != (330, 510):
        raise ValueError("Expected the installed Photoshop walking canvas")
    args.out.mkdir(parents=True)
    source = Image.new("RGBA", (512, 512), (128, 128, 128, 255))
    source.alpha_composite(canonical, (86, 0))
    source = source.convert("RGB")
    pose.save(args.out / "source.png")
    pose.save(args.out / "pose.png")
    if args.pose_first:
        pose.save(args.out / "input.png")
        source.save(args.out / "reference-2.png")
        reference = {"path": str(args.canonical.resolve()), "sha256": digest(args.canonical),
                     "prepared": "reference-2.png"}
    else:
        source.save(args.out / "input.png")
        reference = {"path": str((args.out / "pose.png").resolve()),
                     "sha256": digest(args.out / "pose.png"),
                     "prepared": "pose.png"}
    shutil.copy2(args.pose_job / "native.png", args.out / "native.png")
    Image.new("L", pose.size, 255).save(args.out / "selection.png")
    write(args.out / "job.json", {
        "schema": "simon-canonical-design-transfer-v1", "status": "prepared",
        "local_only": True, "game_installed": False, "artistic_approval": False,
        "native_frame": previous["native_frame"], "working_scale": 10,
        "working_source_origin": [22.4, 27], "root": [256, 210],
        "job": {"frame": previous["job"]["frame"], "crop": [0, 0, 512, 512],
                "prompt": POSE_FIRST_PROMPT if args.pose_first else PROMPT,
                "init_pose": args.pose_init,
                "sampler_sigmas": "0.58, 0.43, 0.28, 0.14, 0"},
        "references": [reference], "pose_first": args.pose_first,
        "input_role": "HD anatomy/pose" if args.pose_first else "canonical Photoshop walking character",
        "reference_role": "Photoshop design only" if args.pose_first else "HD anatomy/pose only",
        "pose_reduced_20_to_10": reduced,
        "canonical_source": str(args.canonical.resolve()), "canonical_sha256": digest(args.canonical),
        "pose_source": str(pose_source.resolve()), "pose_source_sha256": digest(pose_source),
        "source_sha256": digest(args.out / "source.png"),
        "selection_sha256": digest(args.out / "selection.png"),
        "conditioning_sha256": digest(args.out / "input.png")})
    print("Prepared reference edit; no inference submitted")


if __name__ == "__main__":
    main()
