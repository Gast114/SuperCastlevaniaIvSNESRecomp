"""Extract, properly name, and integrate the HD HUD, Weapons, Candles, and Item Drops:
1. Standardized 1x, 4x, and 8x exports with clean German names in:
   D:\Super Castlevania IV Recomp\Assets (ausgeschnitten)\Items\
     - Original_1x\ (preserved 1x originals)
     - 01_HUD\ (HUD_Komplett, HUD_Rahmen_Subwaffe, HUD_Zeichensatz_Sheet in 4x & 8x)
     - 02_Waffen\ (all 13 weapons, subweapons, holy water flames, whip upgrade, 2x/3x multipliers in 4x & 8x)
     - 03_Kerzen_und_Items\ (candles 1 & 2, small/large hearts, 3 money bags, small/large meat, rosary cross,
                            invincibility potion, 1UP, boss crystal orb 1 & 2 in 4x & 8x)
2. Builds all 2bpp BG3 HUD tile replacements (0x01..0x2d at VRAM 0x5000) and all 4bpp OBJ tile replacements
   (0x24..0x9f at VRAM 0x6000 across all active palettes) into ALL 8 Stage 01 scenes (entrance, a02..a08)
   as 'stage-01-user-grid-v19-hud-items'.
"""
import hashlib
import json
import shutil
import sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter, ImageOps

ROOT = Path(r"D:\Super Castlevania IV Recomp\SuperCastlevaniaIvSNESRecomp")
ITEMS_DIR = Path(r"D:\Super Castlevania IV Recomp\Assets (ausgeschnitten)\Items")
BRAIN = Path(r"C:\Users\Gaming\.gemini\antigravity\brain\0e3d1566-2f3c-4183-be49-fad33ce3d4a9")
WORK = BRAIN / "scratch" / "items_work"
WORK.mkdir(parents=True, exist_ok=True)

sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tools" / "hd"))
from level_assets import Assets
import hd_common as hd
from hd_preview import fnv_key
from hd_tiles import write_pack

SCALE = 4


def decode_bg3_indices(vram, tid: int, hflip=False, vflip=False) -> np.ndarray:
    addr = 0x5000 + tid * 8
    rows = []
    for y in range(8):
        a = int(vram[addr + y])
        rows.append([((a >> bit) & 1) | (((a >> (bit + 8)) & 1) << 1) for bit in range(7, -1, -1)])
    arr = np.array(rows, np.uint8)
    if hflip:
        arr = arr[:, ::-1]
    if vflip:
        arr = arr[::-1]
    return arr


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


def extract_sprite_from_cell(sheet_1280: Image.Image, col: int, row: int, target_bbox_16: tuple, out_canvas_1x: int = 16) -> tuple:
    """Extract a single HD sprite from a 320x240 cell of a 1280x720 4x3 sheet,
    remove the pure black background cleanly, and register its bounding box
    to target_bbox_16 = (x0, y0, x1, y1) inside an (out_canvas_1x * 8) 8x and (out_canvas_1x * 4) 4x cell.
    Returns (im_4x, im_8x).
    """
    x_c0, y_c0 = col * 320 + 24, row * 240 + 12
    x_c1, y_c1 = (col + 1) * 320 - 24, (row + 1) * 240 - 12
    cell = np.array(sheet_1280.crop((x_c0, y_c0, x_c1, y_c1)).convert("RGBA"), dtype=np.float32)

    lum = cell[:, :, :3].max(axis=2)
    mask = lum > 22.0
    if not mask.any():
        raise ValueError(f"Empty cell at col={col}, row={row}")
    ys, xs = np.where(mask)
    by0, by1 = max(0, int(ys.min()) - 1), min(cell.shape[0], int(ys.max()) + 2)
    bx0, bx1 = max(0, int(xs.min()) - 1), min(cell.shape[1], int(xs.max()) + 2)
    sub = cell[by0:by1, bx0:bx1].copy()

    # Smooth alpha extraction from black background + halo decontamination
    s_lum = sub[:, :, :3].max(axis=2)
    alpha = np.clip((s_lum - 14.0) / 24.0, 0.0, 1.0)
    # Interior fill: erode slightly or keep strong interior solid
    sub[:, :, 3] = np.clip(alpha * 255.0, 0, 255)
    crop_im = Image.fromarray(sub.astype(np.uint8), "RGBA")

    # Map to exact 8x (128x128 or 64x64) and 4x (64x64 or 32x32) target bbox!
    tx0, ty0, tx1, ty1 = target_bbox_16
    tw_1x, th_1x = tx1 - tx0, ty1 - ty0

    im_8x = Image.new("RGBA", (out_canvas_1x * 8, out_canvas_1x * 8), (0, 0, 0, 0))
    fitted_8x = crop_im.resize((tw_1x * 8, th_1x * 8), Image.Resampling.LANCZOS)
    im_8x.paste(fitted_8x, (tx0 * 8, ty0 * 8))

    im_4x = Image.new("RGBA", (out_canvas_1x * 4, out_canvas_1x * 4), (0, 0, 0, 0))
    fitted_4x = crop_im.resize((tw_1x * 4, th_1x * 4), Image.Resampling.LANCZOS)
    im_4x.paste(fitted_4x, (tx0 * 4, ty0 * 4))
    return im_4x, im_8x


def tint_bag(im: Image.Image, mode: str) -> Image.Image:
    """Create the Red/Gold ($400) and Blue/Violet ($700) money bag variants from the White/Grey ($100) bag."""
    arr = np.array(im, dtype=np.float32)
    r, g, b, a = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2], arr[:, :, 3]
    lum = 0.299 * r + 0.587 * g + 0.114 * b
    # Keep the golden tie cord (where r > b + 35) warm gold!
    is_cord = (r - b) > 35.0
    if mode == "red":
        nr = np.clip(lum * 1.35 + 25.0, 0, 255)
        ng = np.clip(lum * 0.55, 0, 255)
        nb = np.clip(lum * 0.42, 0, 255)
    elif mode == "blue":
        nr = np.clip(lum * 0.55, 0, 255)
        ng = np.clip(lum * 0.78 + 10.0, 0, 255)
        nb = np.clip(lum * 1.40 + 30.0, 0, 255)
    else:
        return im.copy()
    arr[:, :, 0] = np.where(is_cord, r, nr)
    arr[:, :, 1] = np.where(is_cord, g, ng)
    arr[:, :, 2] = np.where(is_cord, b, nb)
    return Image.fromarray(arr.astype(np.uint8), "RGBA")


def build_hud_tiles_and_exports(vram, cgram, dir_hud: Path) -> dict:
    """Extract all 45 BG3 2bpp HUD tiles (0x01..0x2d) in 4x (32x32) and 8x (64x64) from hd_hud_sheet,
    lock their alpha to the exact 1x BG3 non-zero pixel mask so SampleRgb outputs 100% HD pixels
    with zero 1x bleed, and assemble HUD_Komplett_HD_4x.png (980x216) & _8x.png (1960x432).
    """
    raw_hud = Image.open(BRAIN / "hd_hud_sheet_1795305178106.jpg").convert("RGBA")
    raw_hud.save(dir_hud / "HUD_Zeichensatz_Sheet_HD.png")
    sheet = raw_hud.resize((1280, 720), Image.Resampling.LANCZOS)
    s_arr = np.array(sheet, dtype=np.float32)

    # Dark outline fill colors for each of the 4 BG3 HUD palettes (pal 0..3):
    # Ensures that inside any non-zero 1x pixel where the HD curve rounds slightly inward,
    # SampleRgb sees alpha=255 with the authentic deep dark drop-shadow color instead of falling back to 1x!
    dark_fill = {
        0: np.array([10.0, 32.0, 12.0], dtype=np.float32),   # deep forest shadow for green text
        1: np.array([10.0, 14.0, 24.0], dtype=np.float32),   # deep slate-iron shadow for frame box
        2: np.array([14.0, 8.0, 20.0], dtype=np.float32),    # deep dark bezel for health bars
        3: np.array([28.0, 10.0, 14.0], dtype=np.float32),   # deep crimson-brown shadow for gold digits
    }

    def extract_bg3_tile_64(tid: int, pal: int, box_x: int, box_y: int) -> tuple:
        """Extract 64x64 (8x) and 32x32 (4x) HD tile for (tid, pal) from sheet at (box_x, box_y)."""
        nat_idx = decode_bg3_indices(vram, tid)  # (8, 8) values 0..3
        nat_mask_64 = (nat_idx > 0).repeat(8, axis=0).repeat(8, axis=1)  # (64, 64)
        nat_mask_32 = (nat_idx > 0).repeat(4, axis=0).repeat(4, axis=1)  # (32, 32)

        # Search within a 4px margin around (box_x, box_y, box_x+64, box_y+64) and register bbox to nat_mask_64
        pad = 6
        x0, y0 = max(0, box_x - pad), max(0, box_y - pad)
        x1, y1 = min(1280, box_x + 64 + pad), min(720, box_y + 64 + pad)
        crop = s_arr[y0:y1, x0:x1, :3].copy()
        lum = crop.max(axis=2)
        hd_m = lum > 22.0

        ys_n, xs_n = np.where(nat_mask_64)
        nx0, ny0, nx1, ny1 = int(xs_n.min()), int(ys_n.min()), int(xs_n.max()) + 1, int(ys_n.max()) + 1

        if hd_m.any():
            ys_h, xs_h = np.where(hd_m)
            hx0, hy0, hx1, hy1 = int(xs_h.min()), int(ys_h.min()), int(xs_h.max()) + 1, int(ys_h.max()) + 1
            glyph = Image.fromarray(crop[hy0:hy1, hx0:hx1].astype(np.uint8), "RGB").resize(
                (nx1 - nx0, ny1 - ny0), Image.Resampling.LANCZOS
            )
            aligned_64 = np.zeros((64, 64, 3), dtype=np.float32)
            aligned_64[:, :] = dark_fill[pal][None, None, :]
            g_arr = np.array(glyph, dtype=np.float32)
            g_lum = g_arr.max(axis=2)
            # Blend near-black background pixels smoothly into dark_fill[pal]
            w = np.clip((g_lum - 12.0) / 18.0, 0.0, 1.0)[:, :, None]
            aligned_64[ny0:ny1, nx0:nx1] = g_arr * w + dark_fill[pal][None, None, :] * (1.0 - w)
        else:
            aligned_64 = np.zeros((64, 64, 3), dtype=np.float32)

        rgba_64 = np.zeros((64, 64, 4), dtype=np.uint8)
        rgba_64[:, :, :3] = np.clip(aligned_64, 0, 255).astype(np.uint8)
        rgba_64[:, :, 3] = np.where(nat_mask_64, 255, 0).astype(np.uint8)

        # Downsample RGB to 32x32 and lock alpha to exact nat_mask_32!
        rgb_32 = np.array(
            Image.fromarray(rgba_64[:, :, :3], "RGB").resize((32, 32), Image.Resampling.LANCZOS),
            dtype=np.uint8,
        )
        rgba_32 = np.zeros((32, 32, 4), dtype=np.uint8)
        rgba_32[:, :, :3] = rgb_32
        rgba_32[:, :, 3] = np.where(nat_mask_32, 255, 0).astype(np.uint8)
        return rgba_32, rgba_64

    hud_tiles_4x = {}
    hud_tiles_8x_by_id = {}

    # 1) Row A (y=280): Digits 0..9 (0x01..0x0a, pal 3) + '=', '-', heart (0x25..0x27, pal 0) + health ticks (0x28..0x2a, pal 2)
    row_a_specs = [(t, 3) for t in range(0x01, 0x0b)] + [(0x25, 0), (0x26, 0), (0x27, 0)] + [(0x28, 2), (0x29, 2), (0x2a, 2)]
    for i, (tid, pal) in enumerate(row_a_specs):
        t32, t64 = extract_bg3_tile_64(tid, pal, 16 + i * 78, 280)
        px_idx = decode_bg3_indices(vram, tid).ravel().tolist()
        cols = [int(cgram[pal * 4 + c]) for c in range(4)]
        key = fnv_key(2, px_idx, cols)
        hud_tiles_4x[key] = t32
        hud_tiles_8x_by_id[(tid, pal)] = t64

    # 2) Row B (y=380): Letters A..M (0x0b..0x17, pal 0)
    for i, tid in enumerate(range(0x0b, 0x18)):
        t32, t64 = extract_bg3_tile_64(tid, 0, 16 + i * 78, 380)
        px_idx = decode_bg3_indices(vram, tid).ravel().tolist()
        cols = [int(cgram[c]) for c in range(4)]
        key = fnv_key(2, px_idx, cols)
        hud_tiles_4x[key] = t32
        hud_tiles_8x_by_id[(tid, 0)] = t64

    # 3) Row C (y=480): Letters N..Z (0x18..0x24, pal 0)
    for i, tid in enumerate(range(0x18, 0x25)):
        t32, t64 = extract_bg3_tile_64(tid, 0, 16 + i * 78, 480)
        px_idx = decode_bg3_indices(vram, tid).ravel().tolist()
        cols = [int(cgram[c]) for c in range(4)]
        key = fnv_key(2, px_idx, cols)
        hud_tiles_4x[key] = t32
        hud_tiles_8x_by_id[(tid, 0)] = t64

    # 4) Subweapon Frame Box tiles (0x2b corner, 0x2c horizontal, 0x2d vertical, pal 1)
    #    Sample directly from the bottom-right standalone Frame Box at (1048, 390, 1248, 550) (200x160 -> 320x256 in 8x!)
    box_crop = s_arr[386:554, 1044:1252, :3]
    lum_b = box_crop.max(axis=2) > 22.0
    ys_b, xs_b = np.where(lum_b)
    box_tight = Image.fromarray(
        box_crop[ys_b.min():ys_b.max() + 1, xs_b.min():xs_b.max() + 1].astype(np.uint8), "RGB"
    )
    box_8x_rgb = np.array(box_tight.resize((40 * 8, 32 * 8), Image.Resampling.LANCZOS), dtype=np.float32)

    # Extract 0x2b (top-left corner rx=0, ry=0), 0x2c (top-mid horizontal rx=2, ry=0), 0x2d (left-mid vertical rx=0, ry=1)
    for tid, (rx, ry) in [(0x2b, (0, 0)), (0x2c, (2, 0)), (0x2d, (0, 1))]:
        nat_idx = decode_bg3_indices(vram, tid)
        m64 = (nat_idx > 0).repeat(8, axis=0).repeat(8, axis=1)
        m32 = (nat_idx > 0).repeat(4, axis=0).repeat(4, axis=1)
        cell64 = box_8x_rgb[ry * 64:(ry + 1) * 64, rx * 64:(rx + 1) * 64].copy()
        # Symmetrize 0x2c horizontally and 0x2d vertically so hflip/vflip joints meet seamlessly!
        if tid == 0x2c:
            cell64 = 0.5 * (cell64 + cell64[:, ::-1])
        elif tid == 0x2d:
            cell64 = 0.5 * (cell64 + cell64[::-1, :])
        rgba_64 = np.zeros((64, 64, 4), dtype=np.uint8)
        rgba_64[:, :, :3] = np.clip(cell64, 0, 255).astype(np.uint8)
        rgba_64[:, :, 3] = np.where(m64, 255, 0).astype(np.uint8)

        rgb_32 = np.array(
            Image.fromarray(rgba_64[:, :, :3], "RGB").resize((32, 32), Image.Resampling.LANCZOS),
            dtype=np.uint8,
        )
        rgba_32 = np.zeros((32, 32, 4), dtype=np.uint8)
        rgba_32[:, :, :3] = rgb_32
        rgba_32[:, :, 3] = np.where(m32, 255, 0).astype(np.uint8)

        px_idx = nat_idx.ravel().tolist()
        cols = [int(cgram[4 + c]) for c in range(4)]
        key = fnv_key(2, px_idx, cols)
        hud_tiles_4x[key] = rgba_32
        hud_tiles_8x_by_id[(tid, 1)] = rgba_64

    # Save standalone Subweapon Frame Box in 4x (160x128) and 8x (320x256)
    frame_8x = Image.new("RGBA", (320, 256), (0, 0, 0, 0))
    box_layout = [
        [(0x2b, 0, 0), (0x2c, 0, 0), (0x2c, 0, 0), (0x2c, 0, 0), (0x2b, 1, 0)],
        [(0x2d, 0, 0), None,         None,         None,         (0x2d, 1, 0)],
        [(0x2d, 0, 0), None,         None,         None,         (0x2d, 1, 0)],
        [(0x2b, 0, 1), (0x2c, 0, 1), (0x2c, 0, 1), (0x2c, 0, 1), (0x2b, 1, 1)],
    ]
    for ry, row in enumerate(box_layout):
        for rx, cell in enumerate(row):
            if cell is None:
                continue
            tid, hf, vf = cell
            im_t = Image.fromarray(hud_tiles_8x_by_id[(tid, 1)], "RGBA")
            if hf:
                im_t = ImageOps.mirror(im_t)
            if vf:
                im_t = ImageOps.flip(im_t)
            frame_8x.alpha_composite(im_t, (rx * 64, ry * 64))
    frame_4x = frame_8x.resize((160, 128), Image.Resampling.LANCZOS)
    frame_4x.save(dir_hud / "HUD_Rahmen_Subwaffe_HD_4x.png")
    frame_8x.save(dir_hud / "HUD_Rahmen_Subwaffe_HD_8x.png")

    # Save complete HUD_Komplett_HD_4x.png (980x216) and _8x.png (1960x432) matching Items/HUD.png (245x54)!
    top_hud = s_arr[20:244, 146:1134, :3].copy()
    th_lum = top_hud.max(axis=2)
    th_a = np.clip((th_lum - 14.0) / 22.0, 0.0, 1.0)
    th_rgba = np.zeros((top_hud.shape[0], top_hud.shape[1], 4), dtype=np.uint8)
    th_rgba[:, :, :3] = np.clip(top_hud, 0, 255).astype(np.uint8)
    th_rgba[:, :, 3] = np.clip(th_a * 255.0, 0, 255).astype(np.uint8)
    hud_full_im = Image.fromarray(th_rgba, "RGBA")
    hud_4x = hud_full_im.resize((245 * 4, 54 * 4), Image.Resampling.LANCZOS)
    hud_8x = hud_full_im.resize((245 * 8, 54 * 8), Image.Resampling.LANCZOS)
    hud_4x.save(dir_hud / "HUD_Komplett_HD_4x.png")
    hud_8x.save(dir_hud / "HUD_Komplett_HD_8x.png")

    return hud_tiles_4x


def main():
    # 1. Archive original 1x cutouts into Items/Original_1x (keeping root files intact too!)
    orig_dir = ITEMS_DIR / "Original_1x"
    dir_hud = ITEMS_DIR / "01_HUD"
    dir_weapons = ITEMS_DIR / "02_Waffen"
    dir_items = ITEMS_DIR / "03_Kerzen_und_Items"
    for d in (orig_dir, dir_hud, dir_weapons, dir_items):
        d.mkdir(parents=True, exist_ok=True)
    for p in ITEMS_DIR.glob("*.png"):
        dst = orig_dir / p.name
        if not dst.exists():
            shutil.copy2(p, dst)

    a5 = Assets(ROOT / "artwork-local/level-editor/rooms/05")
    vram = a5.vram
    cgram = a5.colors

    # Collect all CGRAM palettes across rooms 00..07 so OBJ tiles match in EVERY room!
    room_cgrams = [Assets(ROOT / f"artwork-local/level-editor/rooms/{i:02d}").colors for i in range(8)]

    # 2. Build HUD tiles & exports
    hud_tiles_4x = build_hud_tiles_and_exports(vram, cgram, dir_hud)
    print(f"Built {len(hud_tiles_4x)} HD 2bpp BG3 HUD tiles!")

    # 3. Extract Weapons & Subweapons (from hd_weapons_4x3_sheet_1795305172692.jpg)
    w_raw = Image.open(BRAIN / "hd_weapons_4x3_sheet_1795305172692.jpg").convert("RGBA")
    w_raw.save(dir_weapons / "Waffen_Sheet_Komplett_HD.png")
    w_sheet = w_raw.resize((1280, 720), Image.Resampling.LANCZOS)

    WEAPONS_META = [
        # (col, row, clean_name, bbox_16, tids, pals)
        (0, 0, "Waffe_Dolch",                (0, 6, 16, 10), [0x26, 0x27, 0x36, 0x37], [1, 3]),
        (1, 0, "Waffe_Axt",                  (0, 0, 15, 15), [0x28, 0x29, 0x38, 0x39], [1, 3]),
        (2, 0, "Waffe_Kreuz_Bumerang_1",     (1, 0, 16, 16), [0x44, 0x45, 0x54, 0x55], [1, 3]),
        (3, 0, "Waffe_Taschenuhr",           (3, 1, 16, 16), [0x48, 0x49, 0x58, 0x59], [1, 3]),
        (0, 1, "Waffe_Weihwasser_Flakon",    (3, 1, 14, 16), [0x2a, 0x2b, 0x3a, 0x3b], [1, 3]),
        (1, 1, "Waffe_Weihwasser_Flamme_1",  (0, 0, 7, 7),   [0x9f],                   [3, 1]),
        (2, 1, "Waffe_Weihwasser_Flamme_2",  (5, 5, 10, 14), [0x40, 0x41, 0x50, 0x51], [3, 1]),
        (3, 1, "Waffe_Weihwasser_Flamme_3",  (2, 3, 13, 14), [0x42, 0x43, 0x52, 0x53], [3, 1]),
        (0, 2, "Waffe_Weihwasser_Flamme_4",  (0, 0, 16, 14), [0x84, 0x85, 0x94, 0x95], [3, 1]),
        (1, 2, "Waffe_Peitsche_Morgenstern", (0, 0, 16, 16), [0x60, 0x61, 0x70, 0x71], [0, 1, 2, 3, 4, 5, 6, 7]),
        (2, 2, "Waffe_Multiplikator_2x",     (0, 0, 12, 11), [0x64, 0x65, 0x74, 0x75], [0, 1, 2, 3, 4, 5, 6, 7]),
        (3, 2, "Waffe_Multiplikator_3x",     (0, 0, 12, 11), [0x66, 0x67, 0x76, 0x77], [0, 1, 2, 3, 4, 5, 6, 7]),
    ]

    obj_tiles_4x = {}
    extracted_weapons = {}
    for col, row, cname, bbox, tids, pals in WEAPONS_META:
        c_size = 8 if len(tids) == 1 else 16
        im4, im8 = extract_sprite_from_cell(w_sheet, col, row, bbox, c_size)
        im4.save(dir_weapons / f"{cname}_HD_4x.png")
        im8.save(dir_weapons / f"{cname}_HD_8x.png")
        extracted_weapons[cname] = (im4, im8)

    # Also build Waffe_Kreuz_Bumerang_2 (orthogonal '+' 45-degree rotated frame at tids [0x46, 0x47, 0x56, 0x57])!
    bum1_4x, bum1_8x = extracted_weapons["Waffe_Kreuz_Bumerang_1"]
    bum2_8x = bum1_8x.rotate(45, Image.Resampling.BICUBIC)
    bum2_4x = bum2_8x.resize((64, 64), Image.Resampling.LANCZOS)
    bum2_4x.save(dir_weapons / "Waffe_Kreuz_Bumerang_2_HD_4x.png")
    bum2_8x.save(dir_weapons / "Waffe_Kreuz_Bumerang_2_HD_8x.png")
    extracted_weapons["Waffe_Kreuz_Bumerang_2"] = (bum2_4x, bum2_8x)

    # And build alternating large Holy Water flame frame [0x82, 0x83, 0x92, 0x93] by mirroring Flamme_4!
    fl4_4x, fl4_8x = extracted_weapons["Waffe_Weihwasser_Flamme_4"]
    extracted_weapons["Waffe_Weihwasser_Flamme_4a"] = (ImageOps.mirror(fl4_4x), ImageOps.mirror(fl4_8x))

    # 4. Extract Candles & Item Drops (from hd_candles_items_4x3_1795305175197.jpg)
    ci_raw = Image.open(BRAIN / "hd_candles_items_4x3_1795305175197.jpg").convert("RGBA")
    ci_raw.save(dir_items / "Kerzen_und_Items_Sheet_Komplett_HD.png")
    ci_sheet = ci_raw.resize((1280, 720), Image.Resampling.LANCZOS)

    CANDLES_ITEMS_META = [
        (0, 0, "Kerze_Wandleuchter_1",        (4, 0, 13, 15), [0x24, 0x25, 0x34, 0x35], [3, 1]),
        (1, 0, "Kerze_Wandleuchter_2",        (4, 0, 13, 15), [0x80, 0x81, 0x90, 0x91], [3, 1]),
        (2, 0, "Item_Herz_Klein",             (1, 1, 8, 7),   [0x9e],                   [3, 1]),
        (3, 0, "Item_Herz_Gross",             (3, 4, 13, 13), [0x4a, 0x4b, 0x5a, 0x5b], [3, 1]),
        (0, 1, "Item_Geldbeutel_Weiss",       (1, 1, 15, 14), [0x62, 0x63, 0x72, 0x73], [1]),
        (1, 1, "Item_Fleisch_Keule_Klein",    (3, 4, 14, 12), [0x68, 0x69, 0x78, 0x79], [3, 1]),
        (2, 1, "Item_Fleisch_Braten_Gross",   (0, 4, 16, 15), [0x6a, 0x6b, 0x7a, 0x7b], [3, 1]),
        (3, 1, "Item_Rosenkranz_Kreuz",       (0, 2, 15, 16), [0x4c, 0x4d, 0x5c, 0x5d], [0, 1, 2, 3, 4, 5, 6, 7]),
        (0, 2, "Item_Unverwundbarkeitstrank", (1, 1, 12, 16), [0x4e, 0x4f, 0x5e, 0x5f], [3, 1]),
        (1, 2, "Item_1UP_Extraleben",         (0, 3, 16, 16), [0x86, 0x87, 0x96, 0x97], [0, 1, 2, 3, 4, 5, 6, 7]),
        (2, 2, "Item_Boss_Kristallkugel_1",   (1, 1, 16, 16), [0x6c, 0x6d, 0x7c, 0x7d], [0, 1, 2, 3, 4, 5, 6, 7]),
        (3, 2, "Item_Boss_Kristallkugel_2",   (1, 1, 16, 16), [0x6e, 0x6f, 0x7e, 0x7f], [0, 1, 2, 3, 4, 5, 6, 7]),
    ]

    extracted_items = {}
    for col, row, cname, bbox, tids, pals in CANDLES_ITEMS_META:
        c_size = 8 if len(tids) == 1 else 16
        im4, im8 = extract_sprite_from_cell(ci_sheet, col, row, bbox, c_size)
        extracted_items[cname] = (im4, im8)

    # Lock Kerze_Wandleuchter_2's lower candlestick body (y >= 4 native = y >= 16 in 4x / y >= 32 in 8x)
    # 100% to Kerze_Wandleuchter_1 so the iron holder & wax candles stay rock-solid stationary while ONLY the flames flicker!
    k1_4, k1_8 = extracted_items["Kerze_Wandleuchter_1"]
    k2_4, k2_8 = extracted_items["Kerze_Wandleuchter_2"]
    k2_4_arr, k1_4_arr = np.array(k2_4, dtype=np.float32), np.array(k1_4, dtype=np.float32)
    for y in range(14, 64):
        w = min(1.0, (y - 14) / 4.0)
        k2_4_arr[y] = k1_4_arr[y] * w + k2_4_arr[y] * (1.0 - w)
    k2_8_arr, k1_8_arr = np.array(k2_8, dtype=np.float32), np.array(k1_8, dtype=np.float32)
    for y in range(28, 128):
        w = min(1.0, (y - 28) / 8.0)
        k2_8_arr[y] = k1_8_arr[y] * w + k2_8_arr[y] * (1.0 - w)
    k2_4 = Image.fromarray(k2_4_arr.astype(np.uint8), "RGBA")
    k2_8 = Image.fromarray(k2_8_arr.astype(np.uint8), "RGBA")
    extracted_items["Kerze_Wandleuchter_2"] = (k2_4, k2_8)

    for cname, (im4, im8) in extracted_items.items():
        im4.save(dir_items / f"{cname}_HD_4x.png")
        im8.save(dir_items / f"{cname}_HD_8x.png")

    # Build Red/Gold ($400, pal 3) and Blue/Violet ($700, pals 0,2,4,5) Money Bag variants!
    bag_w4, bag_w8 = extracted_items["Item_Geldbeutel_Weiss"]
    bag_r4, bag_r8 = tint_bag(bag_w4, "red"), tint_bag(bag_w8, "red")
    bag_b4, bag_b8 = tint_bag(bag_w4, "blue"), tint_bag(bag_w8, "blue")
    bag_r4.save(dir_items / "Item_Geldbeutel_Rot_HD_4x.png")
    bag_r8.save(dir_items / "Item_Geldbeutel_Rot_HD_8x.png")
    bag_b4.save(dir_items / "Item_Geldbeutel_Blau_HD_4x.png")
    bag_b8.save(dir_items / "Item_Geldbeutel_Blau_HD_8x.png")

    # 5. Bind all extracted 4x OBJ sprites to their exact FNV-1a tile keys across all active palettes!
    ALL_BINDINGS = [
        *[
            (extracted_weapons[cname][0], tids, pals)
            for _, _, cname, _, tids, pals in WEAPONS_META
        ],
        (extracted_weapons["Waffe_Kreuz_Bumerang_2"][0],   [0x46, 0x47, 0x56, 0x57], [1, 3]),
        (extracted_weapons["Waffe_Weihwasser_Flamme_4a"][0], [0x82, 0x83, 0x92, 0x93], [3, 1]),
        *[
            (extracted_items[cname][0], tids, pals)
            for _, _, cname, _, tids, pals in CANDLES_ITEMS_META
        ],
        (bag_r4, [0x62, 0x63, 0x72, 0x73], [3]),
        (bag_b4, [0x62, 0x63, 0x72, 0x73], [0, 2, 4, 5]),
    ]

    for im4, tids, pals in ALL_BINDINGS:
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

    print(f"Built {len(obj_tiles_4x)} HD 4bpp OBJ tile keys for Weapons, Candles, and Items!")

    # Write documentation file NAMEN_UND_ORDNUNG.txt in Items/
    doc_lines = [
        "SUPER CASTLEVANIA IV — ITEMS, WAFFEN, KERZEN & HUD (4x & 8x HD)",
        "================================================================",
        "",
        "Ordnerstruktur in 'Assets (ausgeschnitten)/Items':",
        "  - Original_1x/          : Unveraenderte 1x-Originalzuschnitte (Sicherung)",
        "  - 01_HUD/               : Komplettes HUD (980x216 4x / 1960x432 8x), Subwaffen-Rahmen (160x128 4x / 320x256 8x) & Zeichensatz-Sheet",
        "  - 02_Waffen/            : Alle Subwaffen, Weihwasser-Flammenstufen 1-4, Morgenstern-Upgrade & 2x/3x-Multiplikatoren in 4x (64x64 / 32x32) & 8x (128x128 / 64x64)",
        "  - 03_Kerzen_und_Items/  : Wandleuchter-Kerzen (Frame 1 & 2), Herz Klein/Gross, Geldbeutel (Weiss/Rot/Blau), Fleisch Klein/Gross, Rosenkranz-Kreuz, Unverwundbarkeitstrank, 1UP & Boss-Kristallkugel (Frame 1 & 2) in 4x & 8x",
        "",
    ]
    (ITEMS_DIR / "NAMEN_UND_ORDNUNG.txt").write_text("\n".join(doc_lines), encoding="utf-8")

    # 6. Inject HUD + Weapons + Candles + Items into ALL 8 scenes of Stage 01 -> stage-01-user-grid-v19-hud-items
    v18_pack = ROOT / "artwork-local/stage01-v18-2026-11-21/stage-01-user-grid-v18-a01-a08"
    v19_root = ROOT / "artwork-local/stage01-v19-2026-11-22"
    v19_pack = v19_root / "stage-01-user-grid-v19-hud-items"
    if v19_root.exists():
        shutil.rmtree(v19_root)
    shutil.copytree(v18_pack, v19_pack)

    new_shared_obj_keys = sorted(obj_tiles_4x.keys())

    for sc in ["entrance", "a02", "a03", "a04", "a05", "a06", "a07", "a08"]:
        sc_dir = v19_pack / sc
        meta = json.loads((sc_dir / "pack.json").read_text(encoding="utf-8"))
        if meta.get("tiles"):
            _, _, existing_tiles = hd.load_pack(sc_dir)
        else:
            existing_tiles = {}
        # Remove old atlas_*.png files before writing updated atlas
        for old_at in sc_dir.glob("atlas_*.png"):
            old_at.unlink()

        merged_tiles = {**existing_tiles, **hud_tiles_4x, **obj_tiles_4x}
        # Write temporary pack to generate atlas_*.png and tiles mapping
        tmp_dir = v19_root / f"_tmp_{sc}"
        tmp_dir.mkdir(parents=True, exist_ok=True)
        write_pack(merged_tiles, tmp_dir, SCALE)
        tmp_meta = json.loads((tmp_dir / "pack.json").read_text(encoding="utf-8"))
        for at_file in tmp_dir.glob("atlas_*.png"):
            shutil.copy2(at_file, sc_dir / at_file.name)
        shutil.rmtree(tmp_dir)

        meta["atlas_size"] = tmp_meta["atlas_size"]
        meta["tiles"] = tmp_meta["tiles"]
        reqs = list(meta.get("requires", []))
        if "shared-objects-v1" not in reqs:
            reqs.append("shared-objects-v1")
        meta["requires"] = reqs
        old_shared = set(meta.get("shared_objects", []))
        meta["shared_objects"] = sorted(old_shared | set(new_shared_obj_keys))
        (sc_dir / "pack.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
        print(f"Updated scene {sc:8s}: total_tiles={len(merged_tiles)}, shared_objects={len(meta['shared_objects'])}")

    top_meta = json.loads((v19_pack / "pack.json").read_text(encoding="utf-8"))
    top_meta["name"] = "Stage 01 HD v19: Complete A01-A08 + HD HUD, Weapons, Subweapons, Candles & Item Drops"
    (v19_pack / "pack.json").write_text(json.dumps(top_meta, indent=2) + "\n", encoding="utf-8")
    print("Successfully built:", v19_pack)


if __name__ == "__main__":
    main()
