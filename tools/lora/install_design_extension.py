"""Install reviewed new-design poses while preserving all Photoshop walking art.

Only character assets change. Native stair cells come from captured game pixels;
manifest publication is last. Each destination is backed up before any writes.
"""
import argparse
import copy
from pathlib import Path
import shutil

from PIL import Image

from repaint_walk_parts import read, write, digest


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", type=Path, required=True, help="Extension working directory")
    p.add_argument("--export", dest="export", type=Path, required=True)
    p.add_argument("--destinations", type=Path, nargs="+", required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    if args.out.exists():
        raise FileExistsError("Use a fresh installation audit directory")
    placement, recipe = read(args.export / "placement.json"), read(args.source / "extension.json")
    rows = {p["name"]: p for p in recipe["poses"]}
    size, offset = placement["frame_size"], placement["offset"]
    if placement["scale"] != 10 or any(n % 10 for n in size):
        raise ValueError("Only native10x images may be installed")
    poses = []
    for row in placement["frames"]:
        name, relative = row["name"], row["image"]
        source = args.export / relative
        image = Image.open(source)
        if digest(source) != row["sha256"] or image.mode != "RGBA" or list(image.size) != size:
            raise ValueError("Export changed after review: " + name)
        folder = args.source / rows[name].get("generation_folder", name)
        if read(folder / "job.json").get("status") != "accepted_for_preview":
            raise ValueError("Pose must be visually reviewed before installation: " + name)
        poses.append((row, source, folder / "native.png"))
    # Validate all targets first; keep individual gameplay/anchors per destination.
    plans = []
    for number, destination in enumerate(args.destinations):
        old = read(destination / "character.json")
        data = copy.deepcopy(old)
        atlas = Image.open(destination / "body.png").convert("RGBA")
        original_atlas = atlas.copy()
        walking = [r for r in old["frames"] if r["label"].startswith("Walking-")]
        walking_hashes = {r["hd"]["image"]: digest(destination / r["hd"]["image"]) for r in walking}
        occupied = {r["cell"] for r in data["frames"]}
        by_id = {r["id"]: r for r in data["frames"]}
        for row, source, native_source in poses:
            native = row["native_frame"]
            if native["id"] in by_id:
                frame = by_id[native["id"]]
                if frame["label"].startswith("Walking-"):
                    raise ValueError("Never replace an existing walking pose")
            else:
                cell = next(n for n in range(256) if n not in occupied)
                occupied.add(cell)
                x, y = cell % 8 * 96, cell // 8 * 96
                if original_atlas.crop((x, y, x + 96, y + 96)).getchannel("A").getbbox():
                    raise ValueError("Unmapped atlas cell contains artwork")
                native_image = Image.open(native_source).convert("RGBA")
                if native_image.size != (96, 96):
                    raise ValueError("Invalid native reference")
                atlas.paste(native_image, (x, y))
                frame = {k: copy.deepcopy(native[k]) for k in ("id", "anchor", "hand")}
                frame.update(cell=cell, label=row["name"])
                data["frames"].append(frame)
                by_id[frame["id"]] = frame
            frame["hd"] = {"image": source.name, "scale": 10,
                           "offset": offset, "display_size": placement["display_size"]}
        data["name"] = f"Simon HD ({len(data['frames'])} poses)"
        assert walking == [r for r in data["frames"] if r["label"].startswith("Walking-")]
        assert data.get("gameplay") == old.get("gameplay")
        for row in old["frames"]:
            cell = row["cell"]
            box = (cell % 8 * 96, cell // 8 * 96, cell % 8 * 96 + 96, cell // 8 * 96 + 96)
            assert atlas.crop(box).tobytes() == original_atlas.crop(box).tobytes()
        plans.append((number, destination, data, atlas, walking_hashes))
    args.out.mkdir(parents=True)
    for number, destination, _, _, _ in plans:
        shutil.copytree(destination, args.out / "before" / str(number))
    report = {"status": "installing", "walking_unchanged": True, "destinations": []}
    write(args.out / "install.json", report)
    for number, destination, data, atlas, walking_hashes in plans:
        for _, source, _ in poses:
            target = destination / source.name
            temp = target.with_suffix(".install-tmp")
            shutil.copy2(source, temp)
            temp.replace(target)
        for alias in recipe["duplicate_outputs"]:
            source = args.export / "frames" / (alias + "_HD_10x.png")
            shutil.copy2(source, destination / source.name)
        temp = destination / "body.install-tmp"
        atlas.save(temp, format="PNG")
        temp.replace(destination / "body.png")
        temp = destination / "character.install-tmp"
        write(temp, data)
        temp.replace(destination / "character.json")
        for filename, value in walking_hashes.items():
            assert digest(destination / filename) == value
        for row, source, _ in poses:
            assert digest(destination / source.name) == row["sha256"]
        assert read(destination / "character.json") == data
        write(destination / "design-import.json", {"source": str(args.export.resolve()),
              "placement": placement, "walking_sha256": walking_hashes})
        report["destinations"].append({"path": str(destination.resolve()),
              "backup": str((args.out / "before" / str(number)).resolve()),
              "poses": len(data["frames"]), "walking_sha256": walking_hashes})
    report["status"] = "installed_verified"
    write(args.out / "install.json", report)
    print(f"Installed{len(poses)} distinct new poses; walking art unchanged")


if __name__ == "__main__":
    main()
