#!/usr/bin/env python3
"""Stage 01 Local Quality & Bugfix Pass v25 (0 Credits, 0 Cloud-AI calls):
1. Enemy Pack (hd-stage01):
   - F6 Bone Pillar (0x0b): Pixel-identical silhouette crimson-ember recolor for red-blink pose 0x8c0f
     so the Bone Pillar NEVER grows/shrinks when blinking red!
   - F6 Bone Pillar Fireballs (0x01): Add missing actor_type=0x01 poses 0x905c & 0x9061 in 8x HD!
   - F5 Ceiling Slime (0x32): Add missing floor/crawl poses 0x8a4a & 0x8a53 in 8x HD!
2. HD Tile Pack (stage-01-user-grid-v21-8x-skeleton):
   - F2 Thrown Holy Water Bottle ([0x2c, 0x2d, 0x3c, 0x3d]): Bind rotated HD Holy Water vial across all 8 palettes!
   - Original-faithful Golden Gothic Castlevania IV Boomerang Cross ([0x44..0x57]): Crisp beveled antique-gold
     & pale-ivory cross with gleaming silver tips and zero 1x staircase artifacts across all 8 palettes!
   - Items & Weapons: Opaque border flood-fill, safe inset padding (zero flat-clipped edges!), and full 8-palette
     bindings (preserving White/Red/Blue Money Bag variants) so NO item ever drops back to 1x pixel art!
"""

import json
import math
import shutil
import sys
from collections import deque
from pathlib import Path
import numpy as np
from PIL import Image, ImageOps

ROOT = Path(r"D:\Super Castlevania IV Recomp\SuperCastlevaniaIvSNESRecomp")
BRAIN = Path(r"C:\Users\Gaming\.gemini\antigravity\brain\0e3d1566-2f3c-4183-be49-fad33ce3d4a9")
ITEMS_DIR = Path(r"D:\Super Castlevania IV Recomp\Assets (ausgeschnitten)\Items")
GEGNER_HD = Path(r"D:\Super Castlevania IV Recomp\Assets (ausgeschnitten)\Gegner\HD_4x_8x")
CAP_NT = BRAIN / "scratch" / "missing_enemies_capture" / "native-template"

sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tools" / "hd"))
from level_assets import Assets
import hd_common as hd
from hd_preview import fnv_key
from hd_tiles import write_pack


def decode_obj_indices(vram, tid: int) -> np.ndarray:
    addr = 0x6000 + tid * 16
    rows = []
    for y in range(8):
        a, b = int(vram[addr + y]), int(vram[addr + y + 8])
        rows.append([
            ((a >> bit) & 1)
            | (((a >> (bit + 8)) & 1) << 1)
            | (((b >> bit) & 1) << 2)
            | (((b >> (bit + 8)) & 1) << 3)
            for bit in range(7, -1, -1)
        ])
    return np.array(rows, np.uint8)


def extract_clean_opaque_item(sheet_1280: Image.Image, col: int, row: int,
                              target_bbox_16: tuple, out_canvas_1x: int = 16,
                              pad_px_4x: int = 1) -> tuple:
    """Extract an HD item from a 4x3 sheet using border-only flood-fill (zero dark interior holes!)
    and safe inset padding inside the 16x16 cell so edges are NEVER clipped flat."""
    x_c0, y_c0 = col * 320 + 24, row * 240 + 12
    x_c1, y_c1 = (col + 1) * 320 - 24, (row + 1) * 240 - 12
    rgba = np.array(sheet_1280.crop((x_c0, y_c0, x_c1, y_c1)).convert("RGBA"), dtype=np.float32)
    lum = rgba[:, :, :3].max(axis=2)
    h, w = lum.shape

    bg_cand = lum < 26.0
    ext = np.zeros((h, w), dtype=bool)
    q = deque()
    for x in range(w):
        if bg_cand[0, x]:
            ext[0, x] = True; q.append((0, x))
        if bg_cand[h - 1, x] and not ext[h - 1, x]:
            ext[h - 1, x] = True; q.append((h - 1, x))
    for y in range(h):
        if bg_cand[y, 0] and not ext[y, 0]:
            ext[y, 0] = True; q.append((y, 0))
        if bg_cand[y, w - 1] and not ext[y, w - 1]:
            ext[y, w - 1] = True; q.append((y, w - 1))
    while q:
        cy, cx = q.popleft()
        for ny, nx in ((cy - 1, cx), (cy + 1, cx), (cy, cx - 1), (cy, cx + 1)):
            if 0 <= ny < h and 0 <= nx < w and not ext[ny, nx] and bg_cand[ny, nx]:
                ext[ny, nx] = True
                q.append((ny, nx))

    ext_a = np.clip((lum - 11.0) / 15.0, 0.0, 1.0)
    alpha = np.where(ext, ext_a, 1.0)
    rgba[:, :, 3] = np.clip(alpha * 255.0, 0, 255)
    u8 = rgba.astype(np.uint8)

    ys, xs = np.where(u8[:, :, 3] > 24)
    crop_im = Image.fromarray(u8[ys.min():ys.max() + 1, xs.min():xs.max() + 1], "RGBA")

    tx0, ty0, tx1, ty1 = target_bbox_16
    c4 = out_canvas_1x * 4
    c8 = out_canvas_1x * 8

    # Safe inset so items touching 0 or 16 never get flat-clipped!
    x0_4 = max(pad_px_4x if tx0 == 0 else 0, tx0 * 4)
    y0_4 = max(pad_px_4x if ty0 == 0 else 0, ty0 * 4)
    x1_4 = min(c4 - (pad_px_4x if tx1 == out_canvas_1x else 0), tx1 * 4)
    y1_4 = min(c4 - (pad_px_4x if ty1 == out_canvas_1x else 0), ty1 * 4)
    w4, h4 = max(4, x1_4 - x0_4), max(4, y1_4 - y0_4)

    # Preserve aspect ratio cleanly inside the target box!
    sc4 = min(w4 / crop_im.width, h4 / crop_im.height)
    rw4, rh4 = max(4, int(round(crop_im.width * sc4))), max(4, int(round(crop_im.height * sc4)))
    ox4 = x0_4 + (w4 - rw4) // 2
    oy4 = y0_4 + (h4 - rh4) // 2
    im_4x = Image.new("RGBA", (c4, c4), (0, 0, 0, 0))
    im_4x.alpha_composite(crop_im.resize((rw4, rh4), Image.Resampling.LANCZOS), (ox4, oy4))

    im_8x = Image.new("RGBA", (c8, c8), (0, 0, 0, 0))
    im_8x.alpha_composite(crop_im.resize((rw4 * 2, rh4 * 2), Image.Resampling.LANCZOS), (ox4 * 2, oy4 * 2))
    return im_4x, im_8x


def render_golden_gothic_boomerang(angle_deg: float, size: int = 128) -> Image.Image:
    """Render an ultra-crisp, original-faithful Castlevania IV Golden Gothic Holy Cross Boomerang
    matching the iconic 1x palette (pale ivory/champagne gold bevels, warm antique bronze shadows,
    gleaming silver-white tips, dark recessed center rivet) with ZERO 1x staircase artifacts."""
    yy, xx = np.mgrid[0:size, 0:size].astype(np.float32)
    cx = (size - 1) * 0.5
    cy = (size - 1) * 0.5
    rad = math.radians(angle_deg)
    ca, sa = math.cos(rad), math.sin(rad)
    dx = xx - cx
    dy = yy - cy
    ux = dx * ca + dy * sa
    uy = -dx * sa + dy * ca

    arm_len = size * 0.435   # safe margin inside 128x128 so tips are NEVER clipped!
    arm_hw = size * 0.088    # crisp proportional blade half-width (matches 1x 3px / 16px ratio!)

    # Horizontal bar & vertical bar signed distances
    dh_x = np.abs(ux) - arm_len
    dh_y = np.abs(uy) - arm_hw
    d_horiz = np.maximum(dh_x, dh_y)

    dv_x = np.abs(ux) - arm_hw
    dv_y = np.abs(uy) - arm_len
    d_vert = np.maximum(dv_x, dv_y)

    d_cross = np.minimum(d_horiz, d_vert)
    alpha = np.clip((1.1 - d_cross) / 1.8, 0.0, 1.0)

    # Compute bevel normal on each blade (bright top/left facet, warm bronze bottom/right facet)
    in_h = d_horiz <= d_vert
    # Local signed position across blade width [-1..1]
    cross_t = np.where(in_h, uy / arm_hw, ux / arm_hw)
    # Distance along arm [0..1]
    along_t = np.where(in_h, np.abs(ux) / arm_len, np.abs(uy) / arm_len)
    # Bevel ridge along center of each arm
    ridge = 1.0 - np.clip(np.abs(cross_t), 0.0, 1.0)
    # Top-left directional metallic lighting
    light = np.clip(0.58 - 0.34 * cross_t + 0.24 * ridge, 0.0, 1.0)

    # Antique gold / champagne-ivory palette matching ref_boomerang_1x_2x1.png!
    stops = np.array([0.0, 0.28, 0.58, 0.84, 1.0], dtype=np.float32)
    r_ramp = np.array([56, 118, 184, 232, 255], dtype=np.float32)
    g_ramp = np.array([34,  78, 138, 198, 242], dtype=np.float32)
    b_ramp = np.array([18,  46,  92, 146, 206], dtype=np.float32)

    r = np.interp(light, stops, r_ramp)
    g = np.interp(light, stops, g_ramp)
    b = np.interp(light, stops, b_ramp)

    # Gleaming silver-white sharpened blade tips (along_t > 0.82)
    tip_glow = np.clip((along_t - 0.80) / 0.18, 0.0, 1.0)
    r = r * (1.0 - tip_glow * 0.65) + 248.0 * (tip_glow * 0.65)
    g = g * (1.0 - tip_glow * 0.65) + 250.0 * (tip_glow * 0.65)
    b = b * (1.0 - tip_glow * 0.72) + 255.0 * (tip_glow * 0.72)

    # Dark recessed gothic center hub + inner gold rim (matching 1x dark square hub!)
    hub_d = np.maximum(np.abs(ux), np.abs(uy))
    hub_mask = np.clip((size * 0.095 - hub_d) / 1.5, 0.0, 1.0)
    rivet_mask = np.clip((size * 0.042 - np.hypot(ux, uy)) / 1.2, 0.0, 1.0)
    r = r * (1.0 - hub_mask * 0.75) + 34.0 * (hub_mask * 0.75)
    g = g * (1.0 - hub_mask * 0.75) + 22.0 * (hub_mask * 0.75)
    b = b * (1.0 - hub_mask * 0.75) + 12.0 * (hub_mask * 0.75)
    # Dark obsidian center jewel/rivet
    r = r * (1.0 - rivet_mask) + 18.0 * rivet_mask
    g = g * (1.0 - rivet_mask) + 26.0 * rivet_mask
    b = b * (1.0 - rivet_mask) + 32.0 * rivet_mask

    # Crisp dark bronze outer outline for readability on dark & bright backgrounds
    rim = np.clip((d_cross + 1.5) / 1.8, 0.0, 1.0)
    r *= (1.0 - rim * 0.45)
    g *= (1.0 - rim * 0.45)
    b *= (1.0 - rim * 0.45)

    out = np.zeros((size, size, 4), dtype=np.uint8)
    out[:, :, 0] = np.clip(r, 0, 255).astype(np.uint8)
    out[:, :, 1] = np.clip(g, 0, 255).astype(np.uint8)
    out[:, :, 2] = np.clip(b, 0, 255).astype(np.uint8)
    out[:, :, 3] = np.clip(alpha * 255.0, 0, 255).astype(np.uint8)
    return Image.fromarray(out, "RGBA")


def make_crimson_blink_identical(im: Image.Image) -> Image.Image:
    """Create a glowing crimson-ember attack-blink version of the Bone Pillar with 100% PIXEL-IDENTICAL
    geometry/alpha so it NEVER changes size or shape when blinking red!"""
    arr = np.array(im.convert("RGBA"), dtype=np.float32)
    a = arr[:, :, 3]
    lum = 0.299 * arr[:, :, 0] + 0.587 * arr[:, :, 1] + 0.114 * arr[:, :, 2]
    # Map bone ivory luminance to glowing hellfire crimson-orange-gold
    nr = np.clip(lum * 1.48 + 38.0, 0, 255)
    ng = np.clip(lum * 0.44 + (lum / 255.0) ** 2 * 55.0, 0, 255)
    nb = np.clip(lum * 0.18, 0, 255)
    out = np.zeros_like(arr)
    out[:, :, 0] = np.where(a > 0, nr, 0)
    out[:, :, 1] = np.where(a > 0, ng, 0)
    out[:, :, 2] = np.where(a > 0, nb, 0)
    out[:, :, 3] = a
    return Image.fromarray(out.astype(np.uint8), "RGBA")


def register_crop_to_ref_96(crop_im: Image.Image, ref_path: Path) -> Image.Image:
    ref_1x = np.array(Image.open(ref_path).convert("RGBA"))
    ry, rx = np.where(ref_1x[:, :, 3] > 0)
    nx0, ny0, nx1, ny1 = int(rx.min()), int(ry.min()), int(rx.max()) + 1, int(ry.max()) + 1
    nw, nh = nx1 - nx0, ny1 - ny0
    im8 = Image.new("RGBA", (96 * 8, 96 * 8), (0, 0, 0, 0))
    im8.paste(crop_im.resize((nw * 8, nh * 8), Image.Resampling.LANCZOS), (nx0 * 8, ny0 * 8))
    return im8


def fix_enemy_pack():
    stage_ep = ROOT / "artwork-local" / "enemy-packs-hd" / "hd-stage01"
    manifest = json.loads((stage_ep / "enemies.json").read_text(encoding="utf-8"))
    by_id = {f["id"]: f for f in manifest["frames"]}

    # 1. F6 Bone Pillar (0x0b): Replace 0x8c0f red-blink with 100% pixel-identical crimson recolor of 0x8d70!
    normal_id = "gegner-000b_pose-8d70_d88a204c80492654"
    red_id = "gegner-000b_pose-8c0f_d88a204c80492654"
    normal_im = Image.open(stage_ep / by_id[normal_id]["image"]).convert("RGBA")
    crimson_im = make_crimson_blink_identical(normal_im)
    crimson_im.save(stage_ep / by_id[red_id]["image"])
    crimson_im.save(GEGNER_HD / "Knochensaeule_Angriff_HD_8x.png")
    print("Fixed F6 Bone Pillar red-blink (0x8c0f) to 100% identical silhouette!")

    # 2. F6 Bone Pillar Fireballs (0x01): Add 0x905c and 0x9061!
    fire_src = Image.open(GEGNER_HD / "Knochensaeule_Feuerball_1_HD_8x.png").convert("RGBA")
    fbbox = fire_src.getbbox()
    fire_crop = fire_src.crop(fbbox)
    fire_crop2 = fire_crop.rotate(18.0, Image.Resampling.BICUBIC, expand=True)

    for fid, pose, fcrop in [
        ("gegner-0001_pose-905c_34c3a09dda5a9115", 0x905c, fire_crop),
        ("gegner-0001_pose-9061_b1b5a0285c4e9667", 0x9061, fire_crop2),
    ]:
        ref_p = CAP_NT / f"{fid}.png"
        im8 = register_crop_to_ref_96(fcrop, ref_p)
        fname = f"{fid}.png"
        im8.save(stage_ep / fname)
        by_id[fid] = {
            "id": fid,
            "actor_type": 0x01,
            "pose": pose,
            "image": fname,
            "display_size": [96, 96],
            "anchor": [48, 48],
        }
    print("Added F6 Bone Pillar Fireballs (actor_type 0x01: 0x905c, 0x9061) in 8x HD!")

    # 3. F5 Ceiling Slime (0x32): Add missing floor/crawl poses 0x8a4a and 0x8a53!
    slime_src = Image.open(GEGNER_HD / "Deckenschleim_A06_01_HD_8x.png").convert("RGBA")
    sbbox = slime_src.getbbox()
    slime_crop = slime_src.crop(sbbox)
    slime_mirror = ImageOps.mirror(slime_crop)

    for fid, pose, scrop in [
        ("gegner-0032_pose-8a4a_d6e953176ab53713", 0x8a4a, slime_mirror),
        ("gegner-0032_pose-8a53_8cf4ec372e28198d", 0x8a53, slime_crop),
    ]:
        ref_p = CAP_NT / f"{fid}.png"
        im8 = register_crop_to_ref_96(scrop, ref_p)
        fname = f"{fid}.png"
        im8.save(stage_ep / fname)
        by_id[fid] = {
            "id": fid,
            "actor_type": 0x32,
            "pose": pose,
            "image": fname,
            "display_size": [96, 96],
            "anchor": [48, 48],
        }
    print("Added F5 Ceiling Slime missing poses (0x8a4a, 0x8a53) in 8x HD!")

    manifest["frames"] = sorted(by_id.values(), key=lambda f: (f["actor_type"], f["pose"], f["id"]))
    (stage_ep / "enemies.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    # Sync hd-stage01 to build-play, build, build-lua
    for dst in (
        ROOT / "build-play" / "game" / "enemy_packs" / "hd-stage01",
        ROOT / "build" / "enemy_packs" / "hd-stage01",
        ROOT / "build-lua" / "enemy_packs" / "hd-stage01",
    ):
        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(stage_ep, dst)
    print(f"Synced hd-stage01 ({len(manifest['frames'])} total frames) to build-play, build, build-lua!")


def fix_items_boomerang_holywater():
    a5 = Assets(ROOT / "artwork-local/level-editor/rooms/05")
    vram = a5.vram
    room_cgrams = [Assets(ROOT / f"artwork-local/level-editor/rooms/{i:02d}").colors for i in range(8)]

    w_sheet = Image.open(BRAIN / "hd_weapons_4x3_sheet_1795305172692.jpg").convert("RGBA").resize((1280, 720), Image.Resampling.LANCZOS)
    ci_sheet = Image.open(BRAIN / "hd_candles_items_4x3_1795305175197.jpg").convert("RGBA").resize((1280, 720), Image.Resampling.LANCZOS)

    ALL_PALS = [0, 1, 2, 3, 4, 5, 6, 7]

    WEAPONS_META = [
        (0, 0, "Waffe_Dolch",                (0, 6, 16, 10), [0x26, 0x27, 0x36, 0x37], ALL_PALS),
        (1, 0, "Waffe_Axt",                  (0, 0, 15, 15), [0x28, 0x29, 0x38, 0x39], ALL_PALS),
        (3, 0, "Waffe_Taschenuhr",           (3, 1, 16, 16), [0x48, 0x49, 0x58, 0x59], ALL_PALS),
        (0, 1, "Waffe_Weihwasser_Flakon",    (3, 1, 14, 16), [0x2a, 0x2b, 0x3a, 0x3b], ALL_PALS),
        (1, 1, "Waffe_Weihwasser_Flamme_1",  (0, 0, 7, 7),   [0x9f],                   ALL_PALS),
        (2, 1, "Waffe_Weihwasser_Flamme_2",  (5, 5, 10, 14), [0x40, 0x41, 0x50, 0x51], ALL_PALS),
        (3, 1, "Waffe_Weihwasser_Flamme_3",  (2, 3, 13, 14), [0x42, 0x43, 0x52, 0x53], ALL_PALS),
        (0, 2, "Waffe_Weihwasser_Flamme_4",  (0, 0, 16, 14), [0x84, 0x85, 0x94, 0x95], ALL_PALS),
        (1, 2, "Waffe_Peitsche_Morgenstern", (0, 0, 16, 16), [0x60, 0x61, 0x70, 0x71], ALL_PALS),
        (2, 2, "Waffe_Multiplikator_2x",     (0, 0, 12, 11), [0x64, 0x65, 0x74, 0x75], ALL_PALS),
        (3, 2, "Waffe_Multiplikator_3x",     (0, 0, 12, 11), [0x66, 0x67, 0x76, 0x77], ALL_PALS),
    ]

    CANDLES_ITEMS_META = [
        (0, 0, "Kerze_Wandleuchter_1",        (4, 0, 13, 15), [0x24, 0x25, 0x34, 0x35], ALL_PALS),
        (1, 0, "Kerze_Wandleuchter_2",        (4, 0, 13, 15), [0x80, 0x81, 0x90, 0x91], ALL_PALS),
        (2, 0, "Item_Herz_Klein",             (1, 1, 8, 7),   [0x9e],                   ALL_PALS),
        (3, 0, "Item_Herz_Gross",             (3, 4, 13, 13), [0x4a, 0x4b, 0x5a, 0x5b], ALL_PALS),
        (0, 1, "Item_Geldbeutel_Weiss",       (1, 1, 15, 14), [0x62, 0x63, 0x72, 0x73], [1]),
        (1, 1, "Item_Fleisch_Keule_Klein",    (3, 4, 14, 12), [0x68, 0x69, 0x78, 0x79], ALL_PALS),
        (2, 1, "Item_Fleisch_Braten_Gross",   (0, 4, 16, 15), [0x6a, 0x6b, 0x7a, 0x7b], ALL_PALS),
        (3, 1, "Item_Rosenkranz_Kreuz",       (0, 2, 15, 16), [0x4c, 0x4d, 0x5c, 0x5d], ALL_PALS),
        (0, 2, "Item_Unverwundbarkeitstrank", (1, 1, 12, 16), [0x4e, 0x4f, 0x5e, 0x5f], ALL_PALS),
        (1, 2, "Item_1UP_Extraleben",         (0, 3, 16, 16), [0x86, 0x87, 0x96, 0x97], ALL_PALS),
        (2, 2, "Item_Boss_Kristallkugel_1",   (1, 1, 16, 16), [0x6c, 0x6d, 0x7c, 0x7d], ALL_PALS),
        (3, 2, "Item_Boss_Kristallkugel_2",   (1, 1, 16, 16), [0x6e, 0x6f, 0x7e, 0x7f], ALL_PALS),
    ]

    dir_weapons = ITEMS_DIR / "02_Waffen"
    dir_items = ITEMS_DIR / "03_Kerzen_und_Items"

    bindings = []
    extracted_w = {}
    for col, row, cname, bbox, tids, pals in WEAPONS_META:
        c_size = 8 if len(tids) == 1 else 16
        im4, im8 = extract_clean_opaque_item(w_sheet, col, row, bbox, c_size, pad_px_4x=2)
        im4.save(dir_weapons / f"{cname}_HD_4x.png")
        im8.save(dir_weapons / f"{cname}_HD_8x.png")
        extracted_w[cname] = (im4, im8)
        bindings.append((im4, tids, pals))

    # Original-faithful Golden Gothic Boomerang Cross (Frame 1 = 22 deg tilted, Frame 2 = 0 deg '+'!)
    bum1_8 = render_golden_gothic_boomerang(22.0, 128)
    bum1_4 = bum1_8.resize((64, 64), Image.Resampling.LANCZOS)
    bum2_8 = render_golden_gothic_boomerang(0.0, 128)
    bum2_4 = bum2_8.resize((64, 64), Image.Resampling.LANCZOS)
    bum1_4.save(dir_weapons / "Waffe_Kreuz_Bumerang_1_HD_4x.png")
    bum1_8.save(dir_weapons / "Waffe_Kreuz_Bumerang_1_HD_8x.png")
    bum2_4.save(dir_weapons / "Waffe_Kreuz_Bumerang_2_HD_4x.png")
    bum2_8.save(dir_weapons / "Waffe_Kreuz_Bumerang_2_HD_8x.png")
    bindings.append((bum1_4, [0x44, 0x45, 0x54, 0x55], ALL_PALS))
    bindings.append((bum2_4, [0x46, 0x47, 0x56, 0x57], ALL_PALS))

    # F2 Thrown Holy Water Bottle ([0x2c, 0x2d, 0x3c, 0x3d]) — rotated -42 deg centered on (5,5)-(12,12)!
    hw_8 = extracted_w["Waffe_Weihwasser_Flakon"][1]
    hw_crop = hw_8.crop(hw_8.getbbox())
    hw_rot = hw_crop.rotate(-42.0, Image.Resampling.BICUBIC, expand=True)
    hw_rot = hw_rot.crop(hw_rot.getbbox())
    # Fit into 9x9 native (72x72 in 8x, 36x36 in 4x) centered at native (8.5, 8.5)
    sc_hw = min(68.0 / hw_rot.width, 68.0 / hw_rot.height)
    hw_r8 = hw_rot.resize((max(8, int(round(hw_rot.width * sc_hw))), max(8, int(round(hw_rot.height * sc_hw)))), Image.Resampling.LANCZOS)
    hw_throw_8 = Image.new("RGBA", (128, 128), (0, 0, 0, 0))
    hw_throw_8.alpha_composite(hw_r8, (68 - hw_r8.width // 2, 68 - hw_r8.height // 2))
    hw_throw_4 = hw_throw_8.resize((64, 64), Image.Resampling.LANCZOS)
    hw_throw_4.save(dir_weapons / "Waffe_Weihwasser_Wurf_HD_4x.png")
    hw_throw_8.save(dir_weapons / "Waffe_Weihwasser_Wurf_HD_8x.png")
    bindings.append((hw_throw_4, [0x2c, 0x2d, 0x3c, 0x3d], ALL_PALS))

    # Alternating Holy Water large flame
    fl4_4 = extracted_w["Waffe_Weihwasser_Flamme_4"][0]
    bindings.append((ImageOps.mirror(fl4_4), [0x82, 0x83, 0x92, 0x93], ALL_PALS))

    # Candles & Items
    extracted_i = {}
    for col, row, cname, bbox, tids, pals in CANDLES_ITEMS_META:
        c_size = 8 if len(tids) == 1 else 16
        im4, im8 = extract_clean_opaque_item(ci_sheet, col, row, bbox, c_size, pad_px_4x=2)
        extracted_i[cname] = (im4, im8)

    # Lock Kerze_Wandleuchter_2 lower holder to Kerze_Wandleuchter_1
    k1_4, k1_8 = extracted_i["Kerze_Wandleuchter_1"]
    k2_4, k2_8 = extracted_i["Kerze_Wandleuchter_2"]
    k1a, k2a = np.array(k1_4, dtype=np.float32), np.array(k2_4, dtype=np.float32)
    for y in range(14, 64):
        w = min(1.0, (y - 14) / 4.0)
        k2a[y] = k1a[y] * w + k2a[y] * (1.0 - w)
    k2_4 = Image.fromarray(k2a.astype(np.uint8), "RGBA")
    extracted_i["Kerze_Wandleuchter_2"] = (k2_4, k2_8)

    for col, row, cname, bbox, tids, pals in CANDLES_ITEMS_META:
        im4, im8 = extracted_i[cname]
        im4.save(dir_items / f"{cname}_HD_4x.png")
        im8.save(dir_items / f"{cname}_HD_8x.png")
        bindings.append((im4, tids, pals))

    # Money bag Red (pal 3) & Blue (pals 0,2,4,5,6,7)
    def tint_bag(im, mode):
        arr = np.array(im, dtype=np.float32)
        r, g, b, a = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2], arr[:, :, 3]
        lum = 0.299 * r + 0.587 * g + 0.114 * b
        is_cord = (r - b) > 35.0
        if mode == "red":
            nr, ng, nb = np.clip(lum * 1.35 + 25.0, 0, 255), np.clip(lum * 0.55, 0, 255), np.clip(lum * 0.42, 0, 255)
        else:
            nr, ng, nb = np.clip(lum * 0.55, 0, 255), np.clip(lum * 0.78 + 10.0, 0, 255), np.clip(lum * 1.40 + 30.0, 0, 255)
        out = arr.copy()
        out[:, :, 0] = np.where(is_cord, r, nr)
        out[:, :, 1] = np.where(is_cord, g, ng)
        out[:, :, 2] = np.where(is_cord, b, nb)
        return Image.fromarray(out.astype(np.uint8), "RGBA")

    bag_w4 = extracted_i["Item_Geldbeutel_Weiss"][0]
    bag_r4 = tint_bag(bag_w4, "red")
    bag_b4 = tint_bag(bag_w4, "blue")
    bag_r4.save(dir_items / "Item_Geldbeutel_Rot_HD_4x.png")
    bag_b4.save(dir_items / "Item_Geldbeutel_Blau_HD_4x.png")
    bindings.append((bag_r4, [0x62, 0x63, 0x72, 0x73], [3]))
    bindings.append((bag_b4, [0x62, 0x63, 0x72, 0x73], [0, 2, 4, 5, 6, 7]))

    obj_tiles_4x = {}
    for im4, tids, pals in bindings:
        arr = np.array(im4, dtype=np.uint8)
        for idx, tid in enumerate(tids):
            px_idx = decode_obj_indices(vram, tid)
            if not px_idx.any():
                continue
            px_list = px_idx.ravel().tolist()
            if len(tids) == 1:
                tile_32 = arr.copy()
            else:
                qx, qy = idx % 2, idx // 2
                tile_32 = arr[qy * 32:(qy + 1) * 32, qx * 32:(qx + 1) * 32].copy()
            for cg in room_cgrams:
                for p_idx in pals:
                    cols = [int(cg[128 + p_idx * 16 + c]) for c in range(16)]
                    key = fnv_key(4, px_list, cols)
                    obj_tiles_4x[key] = tile_32

    print(f"Built {len(obj_tiles_4x)} updated 4bpp OBJ tile keys (Items + Golden Boomerang + Thrown Holy Water)!")

    # Patch directly into stage-01-user-grid-v21-8x-skeleton across all 8 scenes and sync to build-play, build, build-lua!
    pack_name = "stage-01-user-grid-v21-8x-skeleton"
    pack_src = ROOT / "build-play" / "game" / "hd_packs" / pack_name
    tmp_root = BRAIN / "scratch" / "pack_v25_tmp"
    if tmp_root.exists():
        shutil.rmtree(tmp_root)
    tmp_root.mkdir(parents=True, exist_ok=True)

    new_keys = set(obj_tiles_4x.keys())
    for sc in ["entrance", "a02", "a03", "a04", "a05", "a06", "a07", "a08"]:
        sc_dir = pack_src / sc
        meta = json.loads((sc_dir / "pack.json").read_text(encoding="utf-8"))
        _, _, existing_tiles = hd.load_pack(sc_dir)
        for old_at in sc_dir.glob("atlas_*.png"):
            old_at.unlink()
        merged = {**existing_tiles, **obj_tiles_4x}
        tdir = tmp_root / sc
        tdir.mkdir(parents=True, exist_ok=True)
        write_pack(merged, tdir, 4)
        tmeta = json.loads((tdir / "pack.json").read_text(encoding="utf-8"))
        for atf in tdir.glob("atlas_*.png"):
            shutil.copy2(atf, sc_dir / atf.name)
        meta["atlas_size"] = tmeta["atlas_size"]
        meta["tiles"] = tmeta["tiles"]
        meta["shared_objects"] = sorted(set(meta.get("shared_objects", [])) | new_keys)
        (sc_dir / "pack.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
        print(f"  Patched scene {sc:8s}: {len(merged)} tiles")

    shutil.rmtree(tmp_root, ignore_errors=True)

    # Sync to build & build-lua hd_packs
    for dst in (
        ROOT / "build" / "hd_packs" / pack_name,
        ROOT / "build-lua" / "hd_packs" / pack_name,
    ):
        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(pack_src, dst)
    print("Synced updated stage-01-user-grid-v21-8x-skeleton to build-play, build, and build-lua!")


if __name__ == "__main__":
    fix_enemy_pack()
    fix_items_boomerang_holywater()
