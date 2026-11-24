"""Build Stage 01 HD pack adding Section A06 (block 5) onto a prior verified collection.

Preserves entrance, a02, a03, a04, a05 byte-for-byte from --prior and appends a06
(playfield A06-01..06 with widescreen left tower margin, BG2 512x512 map with upgraded
A06-BG-01-01..03 + fog + stars, and OBJ atlas with shared objects + HD crescent moon).
"""
import argparse
import hashlib
import json
import math
import shutil
import sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tools" / "hd"))
from level_assets import Assets
from hd_common import load_pack
from hd_preview import fnv_key
from hd_tiles import write_pack

SCALE = 4
LEFT_MARGIN_NATIVE = 43
LEFT_MARGIN_HD = LEFT_MARGIN_NATIVE * SCALE  # 172 px

BG2_STARS_1X = [
    (11.0, 50.0), (43.0, 18.0), (107.0, 58.0), (123.0, 50.0),
    (139.0, 50.0), (203.0, 18.0), (235.0, 50.0), (331.0, 26.0),
    (347.0, 18.0), (363.0, 50.0), (427.0, 18.0), (459.0, 50.0),
    (475.0, 26.0), (491.0, 18.0),
]

NEBEL_01_POS_1X = [(301, 0), (77, 32)]
NEBEL_02_POS_1X = [(40, 65), (456, 65), (152, 73), (280, 73)]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def tile_indices(assets, word, base=0x6000):
    at = base + (word & 1023) * 16
    rows = []
    for y in range(8):
        a, b = assets.vram[at + y], assets.vram[at + y + 8]
        rows.append([
            (a >> bit & 1)
            | ((a >> (bit + 8) & 1) << 1)
            | ((b >> bit & 1) << 2)
            | ((b >> (bit + 8) & 1) << 3)
            for bit in range(7, -1, -1)
        ])
    return np.array(rows, np.uint8)


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


def make_moon_sprite_64(bg02_hd_4x: Image.Image) -> Image.Image:
    """Extract the 60x60 HD crescent moon from A06-BG-02-01_HD_4x with clean alpha on 64x64."""
    moon_rgb = bg02_hd_4x.crop((224, 180, 284, 240)).convert("RGB")
    rgba = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    mpx = moon_rgb.load()
    opx = rgba.load()
    for y in range(60):
        for x in range(60):
            r, g, b = mpx[x, y]
            lum = max(r, g, b)
            if lum <= 8:
                continue
            if lum < 28:
                a = int(round((lum - 8) * 255.0 / 20.0))
                opx[x, y] = (r, g, b, a)
            else:
                opx[x, y] = (r, g, b, 255)
    return rgba


def blend_wrap_seam_x(im: Image.Image, y_top: int, y_bot: int, band_w: int = 24):
    """Smoothly blend the x=W-1 -> x=0 wrap seam in the open sky cloud band."""
    w, h = im.size
    px = im.load()
    for y in range(y_top, y_bot):
        vt = 1.0 if y < y_bot - 16 else (y_bot - y) / 16.0
        l_rgb = px[0, y]
        r_rgb = px[w - 1, y]
        mid = tuple(0.5 * (l_rgb[i] + r_rgb[i]) for i in range(3))
        for dx in range(band_w):
            ht = (1.0 - dx / band_w) * vt
            # Right edge approaching wrap
            xr = w - 1 - dx
            cr = px[xr, y]
            px[xr, y] = (
                max(0, min(255, int(round(cr[0] + (mid[0] - r_rgb[0]) * ht)))),
                max(0, min(255, int(round(cr[1] + (mid[1] - r_rgb[1]) * ht)))),
                max(0, min(255, int(round(cr[2] + (mid[2] - r_rgb[2]) * ht)))),
                255,
            )
            # Left edge leaving wrap
            xl = dx
            cl = px[xl, y]
            px[xl, y] = (
                max(0, min(255, int(round(cl[0] + (mid[0] - l_rgb[0]) * ht)))),
                max(0, min(255, int(round(cl[1] + (mid[1] - l_rgb[1]) * ht)))),
                max(0, min(255, int(round(cl[2] + (mid[2] - l_rgb[2]) * ht)))),
                255,
            )


def build(a06_hd: Path, prior: Path, output: Path, audit: Path):
    a06_hd, prior, output, audit = [Path(p).resolve() for p in (a06_hd, prior, output, audit)]
    if output.exists() or audit.exists():
        raise FileExistsError("Use new output and audit directories")
    audit.mkdir(parents=True)

    receipts = []

    def track(path: Path) -> Path:
        path = Path(path).resolve()
        receipts.append({
            "source": str(path),
            "sha256": sha(path),
            "backup_relative_path": f"A06/HD-Gemini/{path.name}",
        })
        return path

    # Verify prior collection and copy intact
    prior_meta = json.loads((prior / "pack.json").read_text(encoding="utf-8"))
    before = {str(p.relative_to(prior)): sha(p) for p in prior.rglob("*") if p.is_file()}
    shutil.copytree(prior, output)

    # 1. Assemble A06 playfield (BG1): 172px left widescreen margin + 6016px (A06-01..06) = 6188 x 896 RGBA
    strips = [Image.open(track(a06_hd / f"A06-0{i}_HD_4x.png")).convert("RGBA") for i in range(1, 7)]
    play_w = sum(s.width for s in strips)
    assert play_w == 6016 and all(s.height == 896 for s in strips), "Unexpected A06 playfield strip dimensions"

    full_fg = Image.new("RGBA", (LEFT_MARGIN_HD + play_w, 896), (0, 0, 0, 0))
    # Build seamless 172px left widescreen extension from A06-01's brick tower (x=0..128) + bottom ground strip!
    s1 = strips[0]
    brick_col = s1.crop((0, 0, 128, 896))
    brick_mir = ImageOps.mirror(brick_col)
    # Fill x = 0..172 (maps to world x = -43..0) using mirrored brick column aligned to x=172
    full_fg.paste(brick_mir, (LEFT_MARGIN_HD - 128, 0))
    full_fg.paste(brick_col.crop((128 - (LEFT_MARGIN_HD - 128), 0, 128, 896)), (0, 0))
    cx = LEFT_MARGIN_HD
    for s in strips:
        full_fg.paste(s, (cx, 0))
        cx += s.width
    full_fg.save(audit / "A06-foreground-complete.png")

    # 2. Assemble A06 BG2 (512x512 native -> 2048x1024 at 4x, layer=1, coordinates="map", wrap_x=512, wrap_y=512)
    bg1 = Image.open(track(a06_hd / "A06-BG-01-01_HD_4x.png")).convert("RGBA")
    bg2 = Image.open(track(a06_hd / "A06-BG-01-02_HD_4x.png")).convert("RGBA")
    bg3 = Image.open(track(a06_hd / "A06-BG-01-03_HD_4x.png")).convert("RGBA")
    bg_sky = Image.open(track(a06_hd / "A06-BG-02-01_HD_4x.png")).convert("RGB")
    nebel1 = Image.open(track(a06_hd / "A06-BG-Nebel-01_HD_4x.png")).convert("RGBA")
    nebel2 = Image.open(track(a06_hd / "A06-BG-Nebel-02_HD_4x.png")).convert("RGBA")

    bg_map = Image.new("RGBA", (2048, 1024), (0, 0, 0, 255))
    # Ruined gatehouse/hedges/clouds band at y_native=80 -> y_hd=320 (height 448 -> y=320..768)
    bg_map.paste(bg1, (0, 320))
    bg_map.paste(bg2, (896, 320))
    bg_map.paste(bg3.crop((0, 0, 384, 448)), (1664, 320))
    # Smoothly blend wrap seam at x=2048->0 in sky cloud band (y=350..490)
    blend_wrap_seam_x(bg_map, y_top=350, y_bot=490, band_w=24)

    # Stars in upper sky (y_native=0..79 -> y_hd=0..316)
    bgpx = bg_map.load()
    for sx, sy in BG2_STARS_1X:
        draw_star(bgpx, 2048, 1024, sx * SCALE, sy * SCALE, sf=1)

    # Drifting gothic fog wisps at exact native BG2 tile positions
    for fx, fy in NEBEL_01_POS_1X:
        bg_map.alpha_composite(nebel1, (fx * SCALE, fy * SCALE))
    for fx, fy in NEBEL_02_POS_1X:
        bg_map.alpha_composite(nebel2, (fx * SCALE, fy * SCALE))
    bg_map.save(audit / "A06-bg2-region_01.png")

    # 3. Create a06/ scene directory, OBJ atlas (shared_objects from a05 + A06 HD crescent moon), and pack.json
    a06_dir = output / "a06"
    a06_dir.mkdir(parents=True)

    # Copy shared_objects tiles from a05 and add A06's 4 crescent moon OBJ tiles (palette 6 = base 224)
    a05_meta = json.loads((prior / "a05" / "pack.json").read_text(encoding="utf-8"))
    _, _, a05_tiles = load_pack(prior / "a05")
    shared_keys = list(a05_meta.get("shared_objects", []))
    tile_dict = {k: a05_tiles[k] for k in shared_keys}

    a5_assets = Assets(ROOT / "artwork-local" / "level-editor" / "rooms" / "05")
    moon_im = make_moon_sprite_64(bg_sky)
    moon_im.save(audit / "A06-moon-64x64.png")
    moon_keys = []
    for cy in range(2):
        for cx_t in range(2):
            px_idx = tile_indices(a5_assets, 170 + cx_t + cy * 16, 0x6000).ravel().tolist()
            key = fnv_key(4, px_idx, list(a5_assets.colors[224:240]))
            tile_dict[key] = np.array(moon_im.crop((cx_t * 32, cy * 32, cx_t * 32 + 32, cy * 32 + 32)))
            moon_keys.append(key)

    write_pack(tile_dict, a06_dir, SCALE)
    atlas_meta = json.loads((a06_dir / "pack.json").read_text(encoding="utf-8"))

    # Write playfield chunks (<= 4096 px wide each)
    regions = []
    for x in range(0, full_fg.width, 4096):
        chunk_name = f"foreground_{x // 4096:02d}.png"
        full_fg.crop((x, 0, min(full_fg.width, x + 4096), full_fg.height)).save(a06_dir / chunk_name)
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
    bg_map.convert("RGB").save(a06_dir / "region_01.png")
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
        "scene_block": 5,
        "native_maps": [0, 4096],
        "requires": ["scene-regions-v1", "shared-objects-v1"],
        "shared_objects": shared_keys,
        "regions": regions,
    }
    (a06_dir / "pack.json").write_text(json.dumps(scene_meta, indent=2) + "\n", encoding="utf-8")

    # 4. Update collection pack.json and write import.json receipt
    scenes = list(prior_meta["scenes"])
    if "a06" not in scenes:
        scenes.append("a06")
    prior_meta["scenes"] = scenes
    prior_meta["name"] = "Stage 01 HD: exact 4x grid, A01-A06 complete"
    (output / "pack.json").write_text(json.dumps(prior_meta, indent=2) + "\n", encoding="utf-8")

    # Verify prior pack was completely untouched
    assert before == {str(p.relative_to(prior)): sha(p) for p in prior.rglob("*") if p.is_file()}, "Prior pack changed!"
    assert all(sha(r["source"]) == r["sha256"] for r in receipts), "Source changed during import!"

    report = {
        "a06_foreground_size": list(full_fg.size),
        "a06_foreground_chunks": len(regions) - 1,
        "a06_bg2_size": list(bg_map.size),
        "a06_moon_keys": moon_keys,
        "a06_shared_objects": len(shared_keys),
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
    p.add_argument("--a06-hd", type=Path, required=True)
    p.add_argument("--prior", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--audit", type=Path, required=True)
    args = p.parse_args()
    build(args.a06_hd, args.prior, args.out, args.audit)
