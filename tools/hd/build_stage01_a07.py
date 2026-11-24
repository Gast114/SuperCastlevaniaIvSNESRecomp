"""Build Stage 01 HD pack adding Section A07 (block 6) onto a prior verified collection.

Preserves entrance, a02, a03, a04, a05, a06 byte-for-byte from --prior and appends a07
(playfield A07-01..06 with widescreen left gothic lattice pillar margin, BG2 512x512
wrapping map with A07-BG-02-01..03 + A07-BG-01-02/03 ghost horse meadow + fog + stars,
and OBJ atlas preserving shared_objects).
"""
import argparse
import hashlib
import json
import math
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
LEFT_MARGIN_NATIVE = 43
LEFT_MARGIN_HD = LEFT_MARGIN_NATIVE * SCALE  # 172 px

# Exact native 1x coordinates measured from room06 BG2 VRAM map (512x512)
BG2_STARS_1X = [
    (67.0, 74.0),
    (259.0, 74.0),
    (451.0, 74.0),
]

NEBEL_02_POS_1X = [
    (160, 73), (192, 73), (352, 73), (384, 73),
    (64, 81), (256, 81), (448, 81),
]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def draw_star(px, w, h, cx, cy, sf=1):
    radius = 7 * sf
    for dy in range(-radius, radius + 1):
        for dx in range(-radius, radius + 1):
            x = int(round(cx + dx))
            y = int(round(cy + dy))
            if not (0 <= x < w and 0 <= y < h):
                continue
            r_dist = math.hypot(dx, dy) / sf
            core = math.exp(-(r_dist ** 2) / 2.2)
            ax = abs(dx) / sf
            ay = abs(dy) / sf
            spike_h = math.exp(-ax / 2.4) * math.exp(-(ay ** 2) / 0.45)
            spike_v = math.exp(-ay / 2.4) * math.exp(-(ax ** 2) / 0.45)
            inten = min(1.0, core * 0.95 + max(spike_h, spike_v) * 0.55)
            if inten < 0.04:
                continue
            t = min(1.0, core)
            cr = int(min(255, (145 + (235 - 145) * t) * inten))
            cg = int(min(255, (95 + (205 - 95) * t) * inten))
            cb = int(min(255, (175 + (250 - 175) * t) * inten))
            or_, og, ob, oa = px[x, y]
            px[x, y] = (max(or_, cr), max(og, cg), max(ob, cb), 255)


def blend_wrap_seam_x(im: Image.Image, y_top: int, y_bot: int, band_w: int = 24):
    """Smoothly blend the x=W-1 -> x=0 wrap seam in an open sky/meadow band."""
    w, h = im.size
    px = im.load()
    for y in range(y_top, y_bot):
        l_rgb = px[0, y]
        r_rgb = px[w - 1, y]
        mid = tuple(0.5 * (l_rgb[i] + r_rgb[i]) for i in range(3))
        for dx in range(band_w):
            ht = 1.0 - dx / band_w
            xr = w - 1 - dx
            cr = px[xr, y]
            px[xr, y] = (
                max(0, min(255, int(round(cr[0] + (mid[0] - r_rgb[0]) * ht)))),
                max(0, min(255, int(round(cr[1] + (mid[1] - r_rgb[1]) * ht)))),
                max(0, min(255, int(round(cr[2] + (mid[2] - r_rgb[2]) * ht)))),
                255,
            )
            xl = dx
            cl = px[xl, y]
            px[xl, y] = (
                max(0, min(255, int(round(cl[0] + (mid[0] - l_rgb[0]) * ht)))),
                max(0, min(255, int(round(cl[1] + (mid[1] - l_rgb[1]) * ht)))),
                max(0, min(255, int(round(cl[2] + (mid[2] - l_rgb[2]) * ht)))),
                255,
            )


def blend_internal_seam_x(im: Image.Image, seam_x: int, y_top: int, y_bot: int, half_w: int = 16):
    """Smoothly cross-fade a small vertical seam inside a cloud or grass band."""
    w, h = im.size
    px = im.load()
    for y in range(y_top, y_bot):
        l_rgb = px[(seam_x - 1) % w, y]
        r_rgb = px[seam_x % w, y]
        mid = tuple(0.5 * (l_rgb[i] + r_rgb[i]) for i in range(3))
        for dx in range(half_w):
            ht = 1.0 - dx / half_w
            xl = (seam_x - 1 - dx) % w
            cl = px[xl, y]
            px[xl, y] = (
                max(0, min(255, int(round(cl[0] + (mid[0] - l_rgb[0]) * ht)))),
                max(0, min(255, int(round(cl[1] + (mid[1] - l_rgb[1]) * ht)))),
                max(0, min(255, int(round(cl[2] + (mid[2] - l_rgb[2]) * ht)))),
                255,
            )
            xr = (seam_x + dx) % w
            cr = px[xr, y]
            px[xr, y] = (
                max(0, min(255, int(round(cr[0] + (mid[0] - r_rgb[0]) * ht)))),
                max(0, min(255, int(round(cr[1] + (mid[1] - r_rgb[1]) * ht)))),
                max(0, min(255, int(round(cr[2] + (mid[2] - r_rgb[2]) * ht)))),
                255,
            )


def build(a07_hd: Path, a06_hd: Path, prior: Path, output: Path, audit: Path):
    a07_hd, a06_hd, prior, output, audit = [Path(p).resolve() for p in (a07_hd, a06_hd, prior, output, audit)]
    if output.exists() or audit.exists():
        raise FileExistsError("Use new output and audit directories")
    audit.mkdir(parents=True)

    receipts = []

    def track(path: Path, rel_prefix: str = "A07/HD-Gemini") -> Path:
        path = Path(path).resolve()
        receipts.append({
            "source": str(path),
            "sha256": sha(path),
            "backup_relative_path": f"{rel_prefix}/{path.name}",
        })
        return path

    # Verify prior collection and copy intact
    prior_meta = json.loads((prior / "pack.json").read_text(encoding="utf-8"))
    before = {str(p.relative_to(prior)): sha(p) for p in prior.rglob("*") if p.is_file()}
    shutil.copytree(prior, output)

    # 1. Assemble A07 playfield (BG1): 172px left widescreen margin + 6144px (A07-01..06) = 6316 x 896 RGBA
    strips = [Image.open(track(a07_hd / f"A07-0{i}_HD_4x.png")).convert("RGBA") for i in range(1, 7)]
    play_w = sum(s.width for s in strips)
    assert play_w == 6144 and all(s.height == 896 for s in strips), f"Unexpected A07 playfield dimensions: {play_w}"

    full_fg = Image.new("RGBA", (LEFT_MARGIN_HD + play_w, 896), (0, 0, 0, 0))
    # Build seamless 172px left widescreen extension from A07-01's gothic stone-and-iron lattice pillar (x=0..128)!
    s1 = strips[0]
    pillar = s1.crop((0, 0, 128, 896))
    pillar_mir = ImageOps.mirror(pillar)
    # Fill x=0..172 (world x = -43..0) aligned flush with A07-01 at x=172
    full_fg.paste(pillar_mir, (LEFT_MARGIN_HD - 128, 0))
    full_fg.paste(pillar.crop((128 - (LEFT_MARGIN_HD - 128), 0, 128, 896)), (0, 0))
    cx = LEFT_MARGIN_HD
    for s in strips:
        full_fg.paste(s, (cx, 0))
        cx += s.width
    full_fg.save(audit / "A07-foreground-complete.png")

    # 2. Assemble A07 BG2 (512x512 native -> 2048x1024 at 4x, layer=1, coordinates="map", wrap_x=512, wrap_y=512)
    bg02_1 = Image.open(track(a07_hd / "A07-BG-02-01_HD_4x.png")).convert("RGBA")  # 960x204 -> x=0..960
    bg02_2 = Image.open(track(a07_hd / "A07-BG-02-02_HD_4x.png")).convert("RGBA")  # 704x204 -> x=960..1664
    bg02_3 = Image.open(track(a07_hd / "A07-BG-02-03_HD_4x.png")).convert("RGBA")  # 644x204 -> x=1664..2048 (crop 384w)

    bg01_2 = Image.open(track(a07_hd / "A07-BG-01-02_HD_4x.png")).convert("RGBA")  # 1024x128 -> x=1920..2048 + 0..896
    bg01_3 = Image.open(track(a07_hd / "A07-BG-01-03_HD_4x.png")).convert("RGBA")  # 948x128 -> x=896..1844
    nebel2 = Image.open(track(a06_hd / "A06-BG-Nebel-02_HD_4x.png", "A06/HD-Gemini")).convert("RGBA")

    bg_map = Image.new("RGBA", (2048, 1024), (0, 0, 0, 255))

    # Upper clouds + gothic forest + slate watchtowers band at y_native=77 -> y_hd=308 (height 204 -> y=308..512)
    bg_map.paste(bg02_1, (0, 308))
    bg_map.paste(bg02_2, (960, 308))
    bg_map.paste(bg02_3.crop((0, 0, 384, 204)), (1664, 308))
    # Smooth cloud sky seams at x=960, x=1664, and wrap seam x=2048->0 (y=348..384 pure cloud band above HDMA split!)
    blend_internal_seam_x(bg_map, 960, 348, 384, half_w=20)
    blend_internal_seam_x(bg_map, 1664, 348, 384, half_w=20)
    blend_wrap_seam_x(bg_map, 348, 384, band_w=24)

    # Lower ghost-horse nocturnal meadow + ruins band at y_native=128 -> y_hd=512 (height 128 -> y=512..640)
    # A07-BG-01-02 wraps at x=1920..2048 (left 128px of bg01_2) and x=0..896 (right 896px of bg01_2)!
    bg_map.paste(bg01_2.crop((0, 0, 128, 128)), (1920, 512))
    bg_map.paste(bg01_2.crop((128, 0, 1024, 128)), (0, 512))
    # A07-BG-01-03 sits at x=896..1844 (width 948)
    bg_map.paste(bg01_3, (896, 512))
    # Fill remaining 76px meadow gap (x=1844..1920) cleanly using right meadow grass from bg01_2 (x=948..1024)
    bg_map.paste(bg01_2.crop((948, 0, 1024, 128)), (1844, 512))
    # Smooth grass transition at x=1844 (y=548..640 meadow grass)
    blend_internal_seam_x(bg_map, 1844, 548, 640, half_w=16)

    # Stars in upper sky (y_native=74 -> y_hd=296)
    bgpx = bg_map.load()
    for sx, sy in BG2_STARS_1X:
        draw_star(bgpx, 2048, 1024, sx * SCALE, sy * SCALE, sf=1)

    # Drifting gothic fog wisps at exact native BG2 positions
    for fx, fy in NEBEL_02_POS_1X:
        bg_map.alpha_composite(nebel2, (fx * SCALE, fy * SCALE))

    bg_map.save(audit / "A07-bg2-region_01.png")

    # 3. Create a07/ scene directory, OBJ atlas (shared_objects copied from a06), and pack.json
    a07_dir = output / "a07"
    a07_dir.mkdir(parents=True)

    a06_meta = json.loads((prior / "a06" / "pack.json").read_text(encoding="utf-8"))
    _, _, a06_tiles = load_pack(prior / "a06")
    shared_keys = list(a06_meta.get("shared_objects", []))
    tile_dict = {k: a06_tiles[k] for k in shared_keys}

    write_pack(tile_dict, a07_dir, SCALE)
    atlas_meta = json.loads((a07_dir / "pack.json").read_text(encoding="utf-8"))

    # Write playfield chunks (<= 4096 px wide each)
    regions = []
    for x in range(0, full_fg.width, 4096):
        chunk_name = f"foreground_{x // 4096:02d}.png"
        full_fg.crop((x, 0, min(full_fg.width, x + 4096), full_fg.height)).save(a07_dir / chunk_name)
        regions.append({
            "image": chunk_name,
            "layer": 0,
            "x": -LEFT_MARGIN_NATIVE + x // SCALE,
            "y": 0,
            "coordinates": "world",
            "wrap_x": 0,
            "wrap_y": 0,
            "modes": [1],
        })

    # Write BG2 map region
    bg_map.convert("RGB").save(a07_dir / "region_01.png")
    regions.append({
        "image": "region_01.png",
        "layer": 1,
        "x": 0,
        "y": 0,
        "coordinates": "map",
        "wrap_x": 512,
        "wrap_y": 512,
        "modes": [1],
    })

    scene_meta = {
        "version": 1,
        "scale": SCALE,
        "tile_size": SCALE * 8,
        "atlas_size": atlas_meta["atlas_size"],
        "tiles": atlas_meta["tiles"],
        "scene_block": 6,
        "native_maps": [0, 4096],
        "requires": ["scene-regions-v1", "shared-objects-v1"],
        "shared_objects": shared_keys,
        "regions": regions,
    }
    (a07_dir / "pack.json").write_text(json.dumps(scene_meta, indent=2) + "\n", encoding="utf-8")

    # 4. Update collection pack.json and write import.json receipt
    scenes = list(prior_meta["scenes"])
    if "a07" not in scenes:
        scenes.append("a07")
    prior_meta["scenes"] = scenes
    prior_meta["name"] = "Stage 01 HD: exact 4x grid, A01-A07 complete"
    (output / "pack.json").write_text(json.dumps(prior_meta, indent=2) + "\n", encoding="utf-8")

    # Verify prior pack was completely untouched
    assert before == {str(p.relative_to(prior)): sha(p) for p in prior.rglob("*") if p.is_file()}, "Prior pack changed!"
    assert all(sha(r["source"]) == r["sha256"] for r in receipts), "Source changed during import!"

    report = {
        "a07_foreground_size": list(full_fg.size),
        "a07_foreground_chunks": len(regions) - 1,
        "a07_bg2_size": list(bg_map.size),
        "a07_shared_objects": len(shared_keys),
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
    p.add_argument("--a07-hd", type=Path, required=True)
    p.add_argument("--a06-hd", type=Path, required=True)
    p.add_argument("--prior", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--audit", type=Path, required=True)
    args = p.parse_args()
    build(args.a07_hd, args.a06_hd, args.prior, args.out, args.audit)
