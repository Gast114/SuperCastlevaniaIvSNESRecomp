"""Build Stage 01 HD pack adding Section A08 (block 7: stairs & Rowdain Boss Chamber)
onto a prior verified collection.

Preserves entrance, a02, a03, a04, a05, a06, a07 byte-for-byte from --prior and appends a08
(playfield A08-07..08 at world x=1504..2048 with widescreen left cobblestone wall extension,
BG2 512x512 map matching A06 byte-for-byte [0/4096 VRAM diff words], and OBJ atlas
preserving shared_objects + HD crescent moon tiles).
"""
import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tools" / "hd"))
from hd_common import load_pack
from hd_tiles import write_pack

SCALE = 4
A08_WORLD_X0 = 1504
LEFT_MARGIN_NATIVE = 76   # covers camera_x=1471 - 43 = 1428 cleanly in 16:9 widescreen
LEFT_MARGIN_HD = LEFT_MARGIN_NATIVE * SCALE  # 304 px


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def build(a08_hd: Path, prior: Path, output: Path, audit: Path):
    a08_hd, prior, output, audit = [Path(p).resolve() for p in (a08_hd, prior, output, audit)]
    if output.exists() or audit.exists():
        raise FileExistsError("Use new output and audit directories")
    audit.mkdir(parents=True)

    receipts = []

    def track(path: Path) -> Path:
        path = Path(path).resolve()
        receipts.append({
            "source": str(path),
            "sha256": sha(path),
            "backup_relative_path": f"A08/HD-Gemini/{path.name}",
        })
        return path

    # Verify prior collection and copy intact
    prior_meta = json.loads((prior / "pack.json").read_text(encoding="utf-8"))
    before = {str(p.relative_to(prior)): sha(p) for p in prior.rglob("*") if p.is_file()}
    shutil.copytree(prior, output)

    # 1. Assemble A08 playfield (BG1): 304px left widescreen cobblestone wall + 1152 (A08-07) + 1024 (A08-08) = 2480 x 896 RGBA
    s07 = Image.open(track(a08_hd / "A08-07_HD_4x.png")).convert("RGBA")
    s08 = Image.open(track(a08_hd / "A08-08_HD_4x.png")).convert("RGBA")
    assert s07.size == (1152, 896) and s08.size == (1024, 896), f"Unexpected A08 sizes: {s07.size}, {s08.size}"

    full_fg = Image.new("RGBA", (LEFT_MARGIN_HD + s07.width + s08.width, 896), (0, 0, 0, 0))
    # Seamless left widescreen extension from A08-07's left cobblestone column (x=0..128)
    stone_col = s07.crop((0, 0, 128, 896))
    stone_mir = ImageOps.mirror(stone_col)
    # Fill x = 0..304 aligned flush with A08-07 at x = 304
    full_fg.paste(stone_mir, (LEFT_MARGIN_HD - 128, 0))
    full_fg.paste(stone_col, (LEFT_MARGIN_HD - 256, 0))
    rem = LEFT_MARGIN_HD - 256  # 48 px
    full_fg.paste(stone_mir.crop((128 - rem, 0, 128, 896)), (0, 0))
    full_fg.paste(s07, (LEFT_MARGIN_HD, 0))
    full_fg.paste(s08, (LEFT_MARGIN_HD + s07.width, 0))
    full_fg.save(audit / "A08-foreground-complete.png")

    # 2. Create a08/ scene directory, copy verified A06 BG2 map (0/4096 diff words in VRAM!) and A06 OBJ atlas
    a08_dir = output / "a08"
    a08_dir.mkdir(parents=True)

    a06_meta = json.loads((prior / "a06" / "pack.json").read_text(encoding="utf-8"))
    _, _, a06_tiles = load_pack(prior / "a06")
    shared_keys = list(a06_meta.get("shared_objects", []))
    # Preserve all shared objects + crescent moon OBJ tiles from a06
    tile_dict = dict(a06_tiles)
    write_pack(tile_dict, a08_dir, SCALE)
    atlas_meta = json.loads((a08_dir / "pack.json").read_text(encoding="utf-8"))

    # Write playfield region (2480 x 896 <= 4096, single crisp PNG!)
    full_fg.save(a08_dir / "foreground_00.png")
    shutil.copy2(prior / "a06" / "region_01.png", a08_dir / "region_01.png")

    regions = [
        {
            "image": "foreground_00.png",
            "layer": 0,
            "x": A08_WORLD_X0 - LEFT_MARGIN_NATIVE,
            "y": 0,
            "coordinates": "world",
            "wrap_x": 0,
            "wrap_y": 0,
            "modes": [1],
        },
        {
            "image": "region_01.png",
            "layer": 1,
            "x": 0,
            "y": 0,
            "coordinates": "map",
            "wrap_x": 512,
            "wrap_y": 512,
            "modes": [1],
        },
    ]

    scene_meta = {
        "version": 1,
        "scale": SCALE,
        "tile_size": SCALE * 8,
        "atlas_size": atlas_meta["atlas_size"],
        "tiles": atlas_meta["tiles"],
        "scene_block": 7,
        "native_maps": [0, 4096],
        "requires": ["scene-regions-v1", "shared-objects-v1"],
        "shared_objects": shared_keys,
        "regions": regions,
    }
    (a08_dir / "pack.json").write_text(json.dumps(scene_meta, indent=2) + "\n", encoding="utf-8")

    # 3. Update collection pack.json and write import.json receipt
    scenes = list(prior_meta["scenes"])
    if "a08" not in scenes:
        scenes.append("a08")
    prior_meta["scenes"] = scenes
    prior_meta["name"] = "Stage 01 HD: exact 4x grid, A01-A08 complete"
    (output / "pack.json").write_text(json.dumps(prior_meta, indent=2) + "\n", encoding="utf-8")

    # Verify prior pack was completely untouched
    assert before == {str(p.relative_to(prior)): sha(p) for p in prior.rglob("*") if p.is_file()}, "Prior pack changed!"
    assert all(sha(r["source"]) == r["sha256"] for r in receipts), "Source changed during import!"

    report = {
        "a08_foreground_size": list(full_fg.size),
        "a08_world_x_range": [A08_WORLD_X0 - LEFT_MARGIN_NATIVE, A08_WORLD_X0 + 544],
        "a08_bg2_source": "a06/region_01.png (0/4096 VRAM diff words)",
        "a08_shared_objects": len(shared_keys),
        "scenes": scenes,
    }
    receipt = {
        "art_scale": SCALE,
        "presentation_scale": SCALE,
        "sources": receipts,
        "builder_sha256": sha(__file__),
        "preserved_existing_collection": str(prior),
        "prior_sha256": before,
        "report": report,
        "source_files_unchanged": True,
    }
    (output / "import.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    (audit / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output), **report}, indent=2))


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--a08-hd", type=Path, required=True)
    p.add_argument("--prior", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--audit", type=Path, required=True)
    args = p.parse_args()
    build(args.a08_hd, args.prior, args.out, args.audit)
