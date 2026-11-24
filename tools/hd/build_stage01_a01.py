"""Build standardized 4x & 8x A01 (entrance, Block 1-1) HD assets and update the Stage 01 HD pack (v18):
1. Standardized 4x & 8x exports in 'Stage 01/A01/HD-Gemini' and 'Stage 01/Exporte-4x/A01/HD':
   - A01-Spielebene_HD_4x.png (4440x896, exact 4x grid with 172px 16:9 margins) & _8x.png (8880x1792)
   - A01-01-Spielebene-Links_HD_4x.png (2788x720) & _8x.png (5576x1440)
   - A01-02-Spielebene-Rechts_HD_4x.png (1740x772, static blocks cleanly removed, rounded bushes intact) & _8x.png (3480x1544)
   - A01-03-Hintergrund_HD_4x.png (1356x768, new dark gothic fractured-slate Skull Rock BG2) & _8x.png (2712x1536)
   - A01-Stein-Stufe-1..4_HD_4x.png (64x64 exact 1:1 square crumbling stone stages from Option 1) & _8x.png (128x128)
   - A01-Mond_HD_4x.png (76x76), A01-Fledermaeuse_HD_4x.png (104x24), A01-Wasser_HD_4x.png (560x392) & _8x.png
2. Converts 'entrance' (scene_block=0) in the Stage 01 pack from legacy scale=10 to unified scale=4 (tile_size=32),
   fixing:
   - Crumbling stone OBJ tiles (frames 160, 162, 164, 166) -> Option 1 2D A01 stone block in 4 progressive HD crack stages
   - New dark gothic Skull Rock BG2 (region_05.png) with transparent sky so the HD crescent moon & bats shine behind the crags
   - Uncut rounded green foliage on the 3 mossy rocks in the water pit (region_03.png with overlay=1, priority=28672)
   - Uncut left 16:9 widescreen parapet wall (widescreen_left.png with overlay=1, priority=8192)
"""
import hashlib
import json
import shutil
import sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter

ROOT = Path(r"D:\Super Castlevania IV Recomp\SuperCastlevaniaIvSNESRecomp")
ASSETS_STAGE01 = Path(r"D:\Super Castlevania IV Recomp\Assets (ausgeschnitten)\Stage 01")
BRAIN = Path(r"C:\Users\Gaming\.gemini\antigravity\brain\0e3d1566-2f3c-4183-be49-fad33ce3d4a9")

sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tools" / "hd"))
from hd_common import load_pack
from hd_tiles import write_pack

SCALE = 4


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def build_opt1_crumbling_stones() -> list:
    """Build the 4 progressive HD crumbling stone stages (160x160 master -> 128x128 8x & 64x64 4x)
     matching mockup_ingame_opt1.png (authentic A01 stone block + hand-painted progressive fractures).
    """
    ai_sheet = Image.open(BRAIN / "crumbling_stone_block_sheet_final_1795289408882.jpg").convert("RGBA")
    s_arr = np.array(ai_sheet)
    top_row = s_arr[45:280, :, :3]
    mask = top_row.max(axis=2) > 25
    cols = np.where(mask.sum(axis=0) > 20)[0]
    splits = np.where(np.diff(cols) > 20)[0]
    x_ranges = []
    start = cols[0]
    for sp in splits:
        x_ranges.append((start, cols[sp]))
        start = cols[sp + 1]
    x_ranges.append((start, cols[-1]))

    ref_boxes_160 = []
    crack_masks_160 = []
    for idx, (x0, x1) in enumerate(x_ranges[:4]):
        sub = s_arr[45:280, x0:x1].copy()
        m = sub[:, :, :3].max(axis=2)
        ys = np.where(m.max(axis=1) > 25)[0]
        y0, y1 = ys[0], ys[-1] + 1
        sub = sub[y0:y1, :]
        lum = sub[:, :, :3].max(axis=2).astype(np.float32)
        sub[:, :, 3] = np.clip((lum - 18.0) * (255.0 / 26.0), 0, 255).astype(np.uint8)
        im160 = Image.fromarray(sub, "RGBA").resize((160, 160), Image.Resampling.LANCZOS)
        arr160 = np.array(im160, dtype=np.float32)
        if idx == 0:
            ref_lum = 0.35 * arr160[:, :, 0] + 0.45 * arr160[:, :, 1] + 0.20 * arr160[:, :, 2]
            ref_alpha = arr160[:, :, 3] / 255.0
            crack_masks_160.append((np.zeros((160, 160), np.float32), ref_alpha))
        else:
            cur_lum = 0.35 * arr160[:, :, 0] + 0.45 * arr160[:, :, 1] + 0.20 * arr160[:, :, 2]
            dark_ratio = np.clip((ref_lum - cur_lum) / np.maximum(ref_lum, 20.0), 0.0, 1.0)
            cur_alpha = (arr160[:, :, 3] / 255.0) * ref_alpha
            crack_masks_160.append((dark_ratio, cur_alpha))
        ref_boxes_160.append(im160)

    sp02_r = Image.open(ASSETS_STAGE01 / "HD/02_SPIELEBENE_HD_RECHTS_4350x1930.png").convert("RGBA")
    blk_a01 = sp02_r.crop((436, 1430, 582, 1584)).resize((160, 160), Image.Resampling.LANCZOS)
    blk_a01_rgb = ImageEnhance.Sharpness(blk_a01.convert("RGB")).enhance(1.45)
    b_arr = np.array(blk_a01, dtype=np.float32)
    b_arr[:, :, :3] = np.array(blk_a01_rgb, dtype=np.float32)
    b_arr[:, :, 3] = np.minimum(b_arr[:, :, 3], np.array(ref_boxes_160[0], dtype=np.float32)[:, :, 3])

    crev = np.array([18.0, 4.0, 16.0], dtype=np.float32)
    base_a = b_arr[:, :, 3] / 255.0
    stages_160 = []
    for idx, (dark_r, c_alpha) in enumerate(crack_masks_160):
        arr = b_arr.copy()
        if idx > 0:
            dr = np.zeros_like(dark_r)
            dr[2:, 2:] = np.maximum(0.0, dark_r[2:, 2:] - dark_r[:-2, :-2])
            arr[:, :, :3] = np.clip(arr[:, :, :3] * (1.0 + dr[:, :, None] * 0.75), 0, 255)
            w = np.clip((dark_r ** 0.85) * 1.15, 0.0, 0.98)[:, :, None]
            arr[:, :, :3] = arr[:, :, :3] * (1.0 - w) + crev[None, None, :] * w
        comb_a = np.minimum(base_a, c_alpha) if idx < 2 else (base_a * c_alpha)
        arr[:, :, 3] = np.clip(comb_a * 255.0, 0, 255)
        stages_160.append(Image.fromarray(arr.astype(np.uint8), "RGBA"))
    return stages_160


def build_new_skull_bg(target_w: int, target_h: int) -> Image.Image:
    """Build the new dark gothic fractured-slate Skull Rock background at (target_w, target_h)
    with clean transparent night sky so the HD crescent moon & bats shine behind the crags.
    """
    hd_old_10x = Image.open(ASSETS_STAGE01 / "HD/03_HINTERGRUND_HD_LINKS_3390x1920.png").convert("RGBA")
    hd_new_raw = Image.open(BRAIN / "stage1_1_bg_skull_rock_hd_1795289380236.jpg").convert("RGBA")

    im_new = hd_new_raw.resize((target_w, target_h), Image.Resampling.LANCZOS)
    im_old = hd_old_10x.resize((target_w, target_h), Image.Resampling.LANCZOS)
    arr = np.array(im_new, dtype=np.float32)
    old_a = np.array(im_old, dtype=np.float32)[:, :, 3] / 255.0

    sky_col = np.array([18.0, 10.0, 33.0], dtype=np.float32)
    dist = np.sqrt(((arr[:, :, :3] - sky_col[None, None, :]) ** 2).sum(axis=2))

    rad = max(3, round(target_h * 0.012))
    old_a_im = Image.fromarray((old_a * 255).astype(np.uint8), "L")
    guard_outer = np.array(
        old_a_im.filter(ImageFilter.MaxFilter(rad * 2 + 1)).filter(ImageFilter.GaussianBlur(rad * 0.5)),
        dtype=np.float32,
    ) / 255.0
    yy, xx = np.mgrid[0:target_h, 0:target_w].astype(np.float32)
    moon_zone = (xx >= target_w * 0.27) & (xx <= target_w * 0.37) & (yy >= target_h * 0.18) & (yy <= target_h * 0.37)
    below_sky = (yy >= target_h * 0.19) & (~moon_zone)
    guard_outer = np.where(below_sky, np.maximum(guard_outer, 1.0), guard_outer)
    guard_inner = np.array(old_a_im.filter(ImageFilter.MinFilter(rad * 2 + 1)), dtype=np.float32) / 255.0

    green_boost = np.maximum(0.0, arr[:, :, 1] - arr[:, :, 0]) * 1.6
    col_alpha = np.clip((dist + green_boost - 6.5) / 11.0, 0.0, 1.0)
    y_idx = np.arange(target_h, dtype=np.float32)[:, None]
    floor_mask = (y_idx > target_h * 0.82) & (old_a > 0.5)

    final_a = np.clip(np.maximum(guard_inner, col_alpha * guard_outer), 0.0, 1.0)
    final_a = np.where(floor_mask, old_a, final_a)

    edge = (final_a > 0.01) & (final_a < 0.95)
    for c in range(3):
        channel = arr[:, :, c]
        cleaned = (channel - sky_col[c] * (1.0 - final_a)) / np.maximum(final_a, 0.15)
        arr[:, :, c] = np.where(edge, np.clip(cleaned, 0, 255), channel)

    arr[:, :, 3] = np.clip(final_a * 255.0, 0, 255)
    return Image.fromarray(arr.astype(np.uint8), "RGBA")


def clean_a01_02_static_blocks(sp02_10x: Image.Image) -> Image.Image:
    """Erase ONLY the 4 static orange/red blocks at x=240..970, y=1415..1602 from 02_SPIELEBENE_HD_RECHTS,
    preserving 100% of the rounded green bush leaves underneath them!
    """
    arr = np.array(sp02_10x).copy()
    sub = arr[1415:1602, 240:970].copy()
    r = sub[:, :, 0].astype(np.int32)
    g = sub[:, :, 1].astype(np.int32)
    b = sub[:, :, 2].astype(np.int32)
    yy = np.arange(1415, 1602)[:, None]
    # Above y=1572, everything in x=240..970 is the 4 static blocks;
    # between y=1572..1602, keep green bush tips (g >= r - 6) and erase warm orange/plum block bottom pixels!
    is_block = (yy < 1576) | ((r - g) > 4) | ((b - g) > 10)
    sub[is_block] = (0, 0, 0, 0)
    arr[1415:1602, 240:970] = sub
    return Image.fromarray(arr, "RGBA")


def main():
    a01_gemini = ASSETS_STAGE01 / "A01" / "HD-Gemini"
    a01_exp4x = ASSETS_STAGE01 / "Exporte-4x" / "A01" / "HD"
    a01_gemini.mkdir(parents=True, exist_ok=True)
    a01_exp4x.mkdir(parents=True, exist_ok=True)

    # 1. Load 10x master sources (read-only!)
    sp01_10x = Image.open(ASSETS_STAGE01 / "HD/01_SPIELEBENE_HD_LINKS_6970x1800.png").convert("RGBA")
    sp02_10x_raw = Image.open(ASSETS_STAGE01 / "HD/02_SPIELEBENE_HD_RECHTS_4350x1930.png").convert("RGBA")
    sp02_10x = clean_a01_02_static_blocks(sp02_10x_raw)
    mond_10x = Image.open(ASSETS_STAGE01 / "HD/04_MOND_HD_190x190.png").convert("RGBA")
    bats_10x = Image.open(ASSETS_STAGE01 / "HD/05_FLEDERMAEUSE_HD_260x60.png").convert("RGBA")
    water_10x = Image.open(ASSETS_STAGE01 / "HD/06_WASSER_HD_1400x980.png").convert("RGBA")

    # 2. Build Option 1 Crumbling Stones (160x160 -> 128x128 8x & 64x64 4x)
    stones_160 = build_opt1_crumbling_stones()
    stones_8x = [im.resize((128, 128), Image.Resampling.LANCZOS) for im in stones_160]
    stones_4x = [im.resize((64, 64), Image.Resampling.LANCZOS) for im in stones_160]
    for i in range(4):
        stones_4x[i].save(a01_gemini / f"A01-Stein-Stufe-{i+1}_HD_4x.png")
        stones_8x[i].save(a01_gemini / f"A01-Stein-Stufe-{i+1}_HD_8x.png")
        stones_4x[i].save(a01_exp4x / f"Stein-Stufe-{i+1}.png")

    # 3. Build New Dark Gothic Skull Rock Background (4x: 1356x768, 8x: 2712x1536)
    bg_4x = build_new_skull_bg(1356, 768)
    bg_8x = build_new_skull_bg(2712, 1536)
    bg_4x.save(a01_gemini / "A01-03-Hintergrund_HD_4x.png")
    bg_8x.save(a01_gemini / "A01-03-Hintergrund_HD_8x.png")
    bg_4x.save(a01_exp4x / "Hintergrund.png")

    # 4. Save standardized 4x and 8x foreground & detail assets
    sp01_4x = sp01_10x.resize((2788, 720), Image.Resampling.LANCZOS)
    sp01_8x = sp01_10x.resize((5576, 1440), Image.Resampling.LANCZOS)
    sp01_4x.save(a01_gemini / "A01-01-Spielebene-Links_HD_4x.png")
    sp01_8x.save(a01_gemini / "A01-01-Spielebene-Links_HD_8x.png")

    sp02_4x = sp02_10x.resize((1740, 772), Image.Resampling.LANCZOS)
    sp02_8x = sp02_10x.resize((3480, 1544), Image.Resampling.LANCZOS)
    sp02_4x.save(a01_gemini / "A01-02-Spielebene-Rechts_HD_4x.png")
    sp02_8x.save(a01_gemini / "A01-02-Spielebene-Rechts_HD_8x.png")

    mond_4x = mond_10x.resize((76, 76), Image.Resampling.LANCZOS)
    mond_8x = mond_10x.resize((152, 152), Image.Resampling.LANCZOS)
    mond_4x.save(a01_gemini / "A01-Mond_HD_4x.png")
    mond_8x.save(a01_gemini / "A01-Mond_HD_8x.png")

    bats_4x = bats_10x.resize((104, 24), Image.Resampling.LANCZOS)
    bats_8x = bats_10x.resize((208, 48), Image.Resampling.LANCZOS)
    bats_4x.save(a01_gemini / "A01-Fledermaeuse_HD_4x.png")
    bats_8x.save(a01_gemini / "A01-Fledermaeuse_HD_8x.png")

    water_4x = water_10x.resize((560, 392), Image.Resampling.LANCZOS)
    water_8x = water_10x.resize((1120, 784), Image.Resampling.LANCZOS)
    water_4x.save(a01_gemini / "A01-Wasser_HD_4x.png")
    water_8x.save(a01_gemini / "A01-Wasser_HD_8x.png")

    # Full unified 4x (4440x896) and 8x (8880x1792) Spielebene matching Exporte-4x standard (x=-43..1067, y=0..224)!
    for sc, s1, s2, suf in [(4, sp01_4x, sp02_4x, "4x"), (8, sp01_8x, sp02_8x, "8x")]:
        full = Image.new("RGBA", ((1024 + 86) * sc, 224 * sc), (0, 0, 0, 0))
        # s1 is at x=-54, y=44 -> offset in x=-43 canvas is (-54 + 43)*sc = -11*sc
        full.alpha_composite(s1.crop((11 * sc, 0, s1.width, s1.height)), (0, 44 * sc))
        # s2 is at x=643, y=31 -> offset in x=-43 canvas is (643 + 43)*sc = 686*sc, width up to 1067 is (435-11)*sc = 424*sc
        full.alpha_composite(s2.crop((0, 0, 424 * sc, s2.height)), (686 * sc, 31 * sc))
        full.save(a01_gemini / f"A01-Spielebene_HD_{suf}.png")
        if sc == 4:
            full.save(a01_exp4x / "Spielebene.png")

    # 5. Build complete v18 pack: stage-01-user-grid-v18-a01-a08
    v17_pack = ROOT / "artwork-local/stage01-v17-2026-11-21/stage-01-user-grid-v17-a06-a08"
    v18_root = ROOT / "artwork-local/stage01-v18-2026-11-21"
    v18_pack = v18_root / "stage-01-user-grid-v18-a01-a08"
    v18_audit = v18_root / "audit"
    if v18_root.exists():
        shutil.rmtree(v18_root)
    v18_audit.mkdir(parents=True)
    shutil.copytree(v17_pack, v18_pack)

    # Convert entrance (scene_block=0) from scale=10 to unified scale=4!
    old_ent = v17_pack / "entrance"
    _, _, old_tiles_10x = load_pack(old_ent)
    old_receipt = json.loads((old_ent / "scene-receipt.json").read_text(encoding="utf-8"))
    old_meta = json.loads((old_ent / "pack.json").read_text(encoding="utf-8"))

    # Downsample all 46 decorative/animated tiles from 80x80 (10x) to 32x32 (4x)
    tiles_4x = {}
    for k, arr80 in old_tiles_10x.items():
        im32 = Image.fromarray(arr80, "RGBA").resize((32, 32), Image.Resampling.LANCZOS)
        tiles_4x[k] = np.array(im32, dtype=np.uint8)

    # Replace the 16 crumbling-stone OBJ tiles (4 frames x 4 quadrants) with our new 64x64 Option 1 stone frames!
    crumble_frames = old_receipt["objects"][0]["frames"]
    for st_idx, fr_info in enumerate(crumble_frames):
        keys = fr_info["keys"]  # [top_left, top_right, bot_left, bot_right]
        st_arr = np.array(stones_4x[st_idx], dtype=np.uint8)  # (64, 64, 4)
        coords = [(0, 0), (1, 0), (0, 1), (1, 1)]
        for k, (qx, qy) in zip(keys, coords):
            tiles_4x[k] = st_arr[qy * 32:(qy + 1) * 32, qx * 32:(qx + 1) * 32].copy()

    ent_dir = v18_pack / "entrance"
    shutil.rmtree(ent_dir)
    ent_dir.mkdir(parents=True)
    write_pack(tiles_4x, ent_dir, SCALE)
    ent_atlas = json.loads((ent_dir / "pack.json").read_text(encoding="utf-8"))

    # Build exact 4x regions for entrance:
    # - region_00.png: drawbridge deck (x=768, y=159, 229x32 native -> 916x128 4x, modes=[1,7])
    reg00_4x = sp02_4x.crop((125 * 4, 128 * 4, 354 * 4, 160 * 4))
    reg00_4x.save(ent_dir / "region_00.png")

    # - region_01.png: 01_SPIELEBENE_HD_LINKS (x=-54, y=44, 697x180 native -> 2788x720 4x, fits in 1 texture < 4096px!)
    sp01_4x.save(ent_dir / "region_01.png")

    # - widescreen_left.png: left 16:9 widescreen extension (x=-54..0, y=44..224 -> 216x720 4x)
    #   Rendered with overlay=1, priority=8192 (0x2000 = native BG1 priority 0) so wrapped blank tiles at x=469..511
    #   never punch rectangular holes into the far-left mossy parapet wall!
    ws_left_4x = sp01_4x.crop((0, 0, 54 * 4, 180 * 4))
    ws_left_4x.save(ent_dir / "widescreen_left.png")

    # - region_03.png: 3 lush mossy rocks & bushes in the water pit + chain anchor (x=643, y=31, 435x193 native -> 1740x772 4x)
    #   Clear ONLY the upper sky/chain area ([0,0,125,134] and [125,0,337,145]) and right tower ([337,0,435,193]),
    #   preserving [184,128,224,160] chain anchor AND 100% of the rounded green bush tops!
    reg03_4x = sp02_4x.copy()
    reg03_4x.paste((0, 0, 0, 0), (0, 0, 125 * 4, 134 * 4))
    reg03_4x.paste((0, 0, 0, 0), (125 * 4, 0, 337 * 4, 145 * 4))
    reg03_4x.paste((0, 0, 0, 0), (337 * 4, 0, 435 * 4, 193 * 4))
    anchor_box = (184 * 4, 128 * 4, 224 * 4, 160 * 4)
    reg03_4x.paste(sp02_4x.crop(anchor_box), anchor_box[:2])
    reg03_4x.save(ent_dir / "region_03.png")

    # - region_05.png: NEW Dark Gothic Skull Rock Background (x=-54, y=0, 339x192 native -> 1356x768 4x)
    bg_4x.save(ent_dir / "region_05.png")

    # - region_06.png: Right Castle Gate Tower on layer=4 (x=980, y=31, 98x193 native -> 392x772 4x)
    reg06_4x = Image.open(old_ent / "region_06.png").convert("RGBA").resize((392, 772), Image.Resampling.LANCZOS)
    reg06_4x.save(ent_dir / "region_06.png")

    # - region_07.png: Mode 7 stationary lower mossy rocks (x=643, y=187, 337x37 native -> 1348x148 4x)
    reg07_4x = Image.open(old_ent / "region_07.png").convert("RGBA").resize((1348, 148), Image.Resampling.LANCZOS)
    reg07_4x.save(ent_dir / "region_07.png")

    # - region_08.png: HD Crescent Moon on layer=4 (screen x=54, y=46, 19x19 native -> 76x76 4x)
    mond_4x.save(ent_dir / "region_08.png")

    # - animation_water_0..3.png: 4-frame water loop (128x24 native -> 512x96 4x)
    water_regions = []
    for r in old_meta["regions"]:
        if r["image"].startswith("animation_water_"):
            wim = Image.open(old_ent / r["image"]).convert("RGBA").resize((512, 96), Image.Resampling.LANCZOS)
            wim.save(ent_dir / r["image"])
            water_regions.append(r)

    moon_mask_keys = next(r["mask_keys"] for r in old_meta["regions"] if r["image"] == "region_08.png")

    ent_regions = [
        dict(layer=0, image="region_00.png", coordinates="world", x=768, y=159, wrap_x=0, wrap_y=0, modes=[1, 7]),
        dict(layer=0, image="region_01.png", coordinates="world", x=-54, y=44, wrap_x=0, wrap_y=0, modes=[1]),
        dict(layer=0, image="widescreen_left.png", coordinates="world", x=-54, y=44, wrap_x=0, wrap_y=0, modes=[1], overlay=1, priority=12288),
        dict(layer=0, image="region_03.png", coordinates="world", x=643, y=31, wrap_x=0, wrap_y=0, priority=28672, modes=[1]),
        dict(layer=0, image="region_03.png", coordinates="world", x=643, y=31, wrap_x=0, wrap_y=0, priority=28672, modes=[1], overlay=1),
        dict(layer=1, image="region_05.png", coordinates="world", x=-54, y=0, wrap_x=0, wrap_y=0),
        dict(layer=4, image="region_06.png", coordinates="world", x=980, y=31, wrap_x=0, wrap_y=0),
        dict(layer=0, image="region_07.png", coordinates="world", x=643, y=187, wrap_x=0, wrap_y=0, modes=[7], stationary=1),
        dict(layer=4, image="region_08.png", coordinates="screen", x=54, y=46, wrap_x=0, wrap_y=0, priority=8960, mask_keys=moon_mask_keys),
        *water_regions,
    ]

    new_ent_meta = {
        "version": 1,
        "scale": SCALE,
        "tile_size": SCALE * 8,
        "atlas_size": ent_atlas["atlas_size"],
        "tiles": ent_atlas["tiles"],
        "requires": ["scene-regions-v1", "shared-objects-v1", "scene-overlays-v1"],
        "scene_block": 0,
        "native_maps": old_meta["native_maps"],
        "shared_objects": old_meta["shared_objects"],
        "object_mask_palette": old_meta["object_mask_palette"],
        "regions": ent_regions,
    }
    (ent_dir / "pack.json").write_text(json.dumps(new_ent_meta, indent=2) + "\n", encoding="utf-8")

    top_meta = json.loads((v18_pack / "pack.json").read_text(encoding="utf-8"))
    top_meta["name"] = "Stage 01 HD v18: A01-A08 unified 4x scale, A01 new Skull Rock BG2, Option 1 crumbling stones, uncut bushes"
    (v18_pack / "pack.json").write_text(json.dumps(top_meta, indent=2) + "\n", encoding="utf-8")

    # Save audit previews
    bg_4x.save(v18_audit / "A01-BG2-4x.png")
    reg03_4x.save(v18_audit / "A01-Bushes-Clean-4x.png")
    print(json.dumps({
        "output": str(v18_pack),
        "entrance_scale": SCALE,
        "entrance_tiles": len(tiles_4x),
        "entrance_regions": len(ent_regions),
        "a01_gemini_files": len(list(a01_gemini.glob("*.png"))),
    }, indent=2))


if __name__ == "__main__":
    main()
