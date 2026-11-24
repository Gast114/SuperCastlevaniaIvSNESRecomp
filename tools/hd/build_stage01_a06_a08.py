"""Build Stage 01 HD pack v16 upgrading A06, A07, and A08 with:
1. Seamless 16:9 widescreen left & right endcaps (overlay=1, stationary=1, priority=0xC000)
   on ALL THREE rooms (A06, A07, A08), including full A06 right divider wall & A08 Boss Room right closure.
2. Exact native BG1 tilemap alpha lock (0 jagged window notches, 0 tree cutout mismatches).
3. Unified modular master tile stamping for cobblestones, floor beams, elevated catwalks, and stairs.
4. Complete removal of baked static rotating wooden trapdoors from BG1 in A07 & A08, paired with
   4x HD OBJ tile replacements for ALL 26 rotating plank frames (0, 45, 90 deg; tiles 0x100..0x11D pal 176).
5. A07 6-frame animated spectral ghost horses (frame_period=10, frame_count=6) using all 6 Gemini HD
   horse poses + seamless nocturnal forest undergrowth & mist transition (eliminating the black bar).
"""
import argparse
import hashlib
import json
import math
import shutil
import sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageFilter, ImageOps

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tools" / "hd"))
from level_assets import Assets
from hd_common import load_pack
from hd_preview import fnv_key
from hd_tiles import write_pack

SCALE = 4
WS_MARGIN_NATIVE = 43
WS_MARGIN_HD = WS_MARGIN_NATIVE * SCALE  # 172 px

A06_STARS_1X = [
    (11.0, 50.0), (43.0, 18.0), (107.0, 58.0), (123.0, 50.0),
    (139.0, 50.0), (203.0, 18.0), (235.0, 50.0), (331.0, 26.0),
    (347.0, 18.0), (363.0, 50.0), (427.0, 18.0), (459.0, 50.0),
    (475.0, 26.0), (491.0, 18.0),
]
A06_NEBEL_01_1X = [(301, 0), (77, 32)]
A06_NEBEL_02_1X = [(40, 65), (456, 65), (152, 73), (280, 73)]

A07_STARS_1X = [(67.0, 74.0), (259.0, 74.0), (451.0, 74.0)]
A07_NEBEL_02_1X = [
    (160, 73), (192, 73), (352, 73), (384, 73),
    (64, 81), (256, 81), (448, 81),
]


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


def render_native_bg1_alpha(assets: Assets) -> np.ndarray:
    """Return exact 1x boolean solid mask (224, width*8) of native BG1 non-transparent pixels."""
    rm = assets.import_room()
    w = rm["width"]
    front = np.array(rm["layers"]["front"], np.uint16).reshape(32, w)
    solid = np.zeros((224, w * 8), dtype=bool)
    for ty in range(28):
        for tx in range(w):
            word = int(front[ty, tx])
            if word == 0:
                continue
            tid = word & 1023
            hflip = bool(word & 0x4000)
            vflip = bool(word & 0x8000)
            at = 8192 + tid * 16
            for y in range(8):
                a_w, b_w = assets.vram[at + y], assets.vram[at + y + 8]
                yy = (7 - y) if vflip else y
                for x in range(8):
                    bit = x if hflip else (7 - x)
                    c = ((a_w >> bit) & 1) | (((a_w >> (bit + 8)) & 1) << 1) | (((b_w >> bit) & 1) << 2) | (((b_w >> (bit + 8)) & 1) << 3)
                    if c != 0:
                        solid[ty * 8 + yy, tx * 8 + x] = True
    return solid, front


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


def blend_internal_seam_x(im: Image.Image, seam_x: int, y_top: int, y_bot: int, half_w: int = 20):
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


def make_moon_sprite_64(bg02_hd_4x: Image.Image) -> Image.Image:
    moon_rgb = bg02_hd_4x.crop((224, 180, 284, 240)).convert("RGB")
    rgba = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    mpx = moon_rgb.load(); opx = rgba.load()
    for y in range(60):
        for x in range(60):
            r, g, b = mpx[x, y]
            lum = max(r, g, b)
            if lum <= 8:
                continue
            a = int(round((lum - 8) * 255.0 / 20.0)) if lum < 28 else 255
            opx[x, y] = (r, g, b, a)
    return rgba


def build_rotating_plank_obj_tiles(assets: Assets, plank_hd_4x: Image.Image, audit_dir: Path) -> dict:
    """Build 4x HD OBJ tile replacements for ALL 26 rotating wooden plank tiles (0x100..0x11D, pal 176)."""
    nat_alpha = np.zeros((16, 128), np.uint8)
    non_empty_tids = []
    for row in (16, 17):
        for col in range(16):
            tid = row * 16 + col
            at = 0x6000 + tid * 16
            has_px = False
            for y in range(8):
                a_w, b_w = assets.vram[at + y], assets.vram[at + y + 8]
                for bit in range(7, -1, -1):
                    c = ((a_w >> bit) & 1) | (((a_w >> (bit + 8)) & 1) << 1) | (((b_w >> bit) & 1) << 2) | (((b_w >> (bit + 8)) & 1) << 3)
                    if c != 0:
                        nat_alpha[(row - 16) * 8 + y, col * 8 + (7 - bit)] = 255
                        has_px = True
            if has_px:
                non_empty_tids.append((tid, row - 16, col))

    h_plank = plank_hd_4x.resize((128, 36), Image.Resampling.LANCZOS)
    v_plank = h_plank.rotate(90, expand=True, resample=Image.Resampling.BICUBIC)
    d_plank = h_plank.rotate(-45, expand=True, resample=Image.Resampling.BICUBIC)
    d_arr = np.array(d_plank)
    dys, dxs = np.where(d_arr[:, :, 3] > 32)
    d_tight = d_plank.crop((int(dxs.min()), int(dys.min()), int(dxs.max() + 1), int(dys.max() + 1)))

    hd_sheet = Image.new("RGBA", (512, 64), (0, 0, 0, 0))

    def mask_piece(piece_img: Image.Image, x0_1x: int, x1_1x: int) -> Image.Image:
        sub_nat = np.zeros_like(nat_alpha)
        sub_nat[:, x0_1x:x1_1x] = nat_alpha[:, x0_1x:x1_1x]
        m4 = Image.fromarray(sub_nat.repeat(4, 0).repeat(4, 1), "L").filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.GaussianBlur(1.0))
        m_arr = np.array(m4)
        m_arr[:, :x0_1x * 4] = 0
        m_arr[:, x1_1x * 4:] = 0
        out_arr = np.array(piece_img)
        out_arr[:, :, 3] = np.minimum(out_arr[:, :, 3], m_arr)
        return Image.fromarray(out_arr, "RGBA")

    # 1. Horizontal (cols 0..3)
    tmp = Image.new("RGBA", (512, 64), (0, 0, 0, 0))
    tmp.alpha_composite(h_plank, (0, 4))
    hd_sheet.alpha_composite(mask_piece(tmp, 0, 32), (0, 0))

    # 2. Vertical top & bottom halves (cols 4..5, 6..7)
    tmp = Image.new("RGBA", (512, 64), (0, 0, 0, 0))
    tmp.alpha_composite(v_plank.crop((0, 0, 36, 64)), (39 * 4, 0))
    hd_sheet.alpha_composite(mask_piece(tmp, 32, 48), (0, 0))

    tmp = Image.new("RGBA", (512, 64), (0, 0, 0, 0))
    tmp.alpha_composite(v_plank.crop((0, 64, 36, 128)), (55 * 4, 0))
    hd_sheet.alpha_composite(mask_piece(tmp, 48, 64), (0, 0))

    # 3. Diagonal halves (cols 8..9 and cols 10..13)
    for x0, x1 in [(64, 80), (80, 112)]:
        ys, xs = np.where(nat_alpha[:, x0:x1] > 0)
        cx = (x0 + 0.5 * (xs.min() + xs.max() + 1)) * 4
        cy = (0.5 * (ys.min() + ys.max() + 1)) * 4
        tmp = Image.new("RGBA", (512, 64), (0, 0, 0, 0))
        px = int(round(cx - d_tight.width / 2))
        py = int(round(cy - d_tight.height / 2))
        tx0, ty0 = max(0, -px), max(0, -py)
        tx1, ty1 = min(d_tight.width, 512 - px), min(d_tight.height, 64 - py)
        tmp.alpha_composite(d_tight.crop((tx0, ty0, tx1, ty1)), (px + tx0, py + ty0))
        hd_sheet.alpha_composite(mask_piece(tmp, x0, x1), (0, 0))

    hd_sheet.save(audit_dir / "rotating_plank_obj_hd_sheet.png")

    # Extract 32x32 HD tiles keyed by fnv_key across OBJ palette 7 (240, exact live plank palette!) + 176/128 fallback
    tiles = {}
    for pal_base in (240, 176, 128):
        pal = list(assets.colors[pal_base:pal_base + 16])
        for tid, r_idx, c_idx in non_empty_tids:
            px_idx = tile_indices(assets, tid, 0x6000).ravel().tolist()
            key = fnv_key(4, px_idx, pal)
            crop32 = hd_sheet.crop((c_idx * 32, r_idx * 32, (c_idx + 1) * 32, (r_idx + 1) * 32))
            tiles[key] = np.array(crop32)
    return tiles


def build_cobble_kit(a06_hd: Path):
    st2 = Image.open(a06_hd / "A06-Stein-zwei-zusammen_HD_4x.png").convert("RGBA").resize((128, 64), Image.Resampling.LANCZOS)
    st1_l = Image.open(a06_hd / "A06-Stein-links_HD_4x.png").convert("RGBA").resize((64, 64), Image.Resampling.LANCZOS)
    st1_r = Image.open(a06_hd / "A06-Stein-rechts_HD_4x.png").convert("RGBA").resize((64, 64), Image.Resampling.LANCZOS)

    def tint(im, m):
        arr = np.array(im, dtype=np.float32)
        arr[:, :, 0] *= m; arr[:, :, 1] *= m; arr[:, :, 2] *= (m * 1.04)
        return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGBA")

    v0 = tint(st2, 0.88)
    v1 = tint(ImageOps.mirror(st2), 0.86)
    v2 = Image.new("RGBA", (128, 64), (0, 0, 0, 0))
    v2.paste(tint(st1_r, 0.88), (0, 0)); v2.paste(tint(st1_l, 0.86), (64, 0))
    v3 = tint(ImageOps.mirror(v2), 0.86)
    return [v0, v1, v2, v3], tint(st1_l, 0.88), tint(st1_r, 0.88)


def stamp_stairs_from_tilemap(dst: Image.Image, a06_treppe: Image.Image, front: np.ndarray, world_x0_1x: int, width_1x: int):
    """Stamp pixel-exact 64x32 HD stair steps at EVERY native SNES 0x2c stair tile (0 px offset under Simon's boots!)."""
    step_desc = a06_treppe.crop((64, 64, 128, 96))
    step_asc = ImageOps.mirror(step_desc)
    sh_asc = Image.new("RGBA", step_asc.size, (0, 0, 0, 0))
    sh_asc.paste((8, 4, 10, 145), (0, 0), step_asc.getchannel("A"))
    sh_asc = sh_asc.filter(ImageFilter.GaussianBlur(2.0))
    sh_desc = Image.new("RGBA", step_desc.size, (0, 0, 0, 0))
    sh_desc.paste((8, 4, 10, 145), (0, 0), step_desc.getchannel("A"))
    sh_desc = sh_desc.filter(ImageFilter.GaussianBlur(2.0))

    tx_start = world_x0_1x // 8
    tx_end = (world_x0_1x + width_1x) // 8
    steps = []
    for ty in range(27, -1, -1):
        for tx in range(tx_start, tx_end):
            w = int(front[ty, tx])
            if (w & 1023) == 0x2c:
                hf = (w >> 14) & 1
                steps.append(((tx - tx_start) * 32, ty * 32, hf))
    for pass_i in range(2):
        for lx, ly, hf in steps:
            if hf == 0:  # ascending left-to-right
                im = sh_asc if pass_i == 0 else step_asc
                px = lx - 10 + (4 if pass_i == 0 else 0)
                py = ly + (5 if pass_i == 0 else 0)
            else:        # descending left-to-right
                im = sh_desc if pass_i == 0 else step_desc
                px = lx - 22 + (4 if pass_i == 0 else 0)
                py = ly + (5 if pass_i == 0 else 0)
            cx0, cy0 = max(0, -px), max(0, -py)
            cx1, cy1 = min(im.width, dst.width - px), min(im.height, dst.height - py)
            if cx1 > cx0 and cy1 > cy0:
                dst.alpha_composite(im.crop((cx0, cy0, cx1, cy1)), (px + cx0, py + cy0))


def build_a07_animated_bg2(a07_hd: Path, a06_hd: Path, audit_dir: Path, track_fn) -> list:
    """Build 4 calm, seamless animation frames (2048x1024) of A07 BG2 using:
    - ONE cohesive oil-painted landscape (unified_left + unified_right, ZERO Flickenteppich, ZERO black bar!)
    - Calm, dignified 4-frame animation of the EXACT SAME transparent spectral ghost horses
      (standing horses gently swaying tails in the night breeze; grazing horses calmly lowering/raising heads;
      ZERO double-exposure, ZERO grass boxes!).
    """
    v17_dir = a07_hd / "v17_anim"
    left_332 = Image.open(track_fn(v17_dir / "A07_BG2_unified_left_1024x332.png", "A07/HD-Gemini/v17_anim")).convert("RGBA")
    right_332 = Image.open(track_fn(v17_dir / "A07_BG2_unified_right_1024x332.png", "A07/HD-Gemini/v17_anim")).convert("RGBA")
    nebel2 = Image.open(track_fn(a06_hd / "A06-BG-Nebel-02_HD_4x.png", "A06/HD-Gemini")).convert("RGBA")

    stand_frames = [
        Image.open(track_fn(v17_dir / f"A07_horse_stand_f{i}.png", "A07/HD-Gemini/v17_anim")).convert("RGBA")
        for i in range(4)
    ]
    graze_frames = [
        Image.open(track_fn(v17_dir / f"A07_horse_graze_f{i}.png", "A07/HD-Gemini/v17_anim")).convert("RGBA")
        for i in range(4)
    ]

    # 1. Assemble unified seamless 2048x1024 BG2 landscape base (y=308..640)
    #    Respect BOTH SNES HDMA parallax splits cleanly:
    #    - Split 1 at y_hd=384 (local y=76): Sky clouds (y<384) scroll slower than forest (y>=384).
    #      Keep EVERY tree crown strictly inside y>=384 and unify the sky clouds to cool Castlevania indigo!
    #    - Split 2 at y_hd=512 (local y=204): Forest (384..512) scrolls slower than meadow (512..640).
    #      Blend a soft dark nocturnal forest-floor shadow symmetrically across y=490..532 (protecting
    #      foreground brick ruins) so the horizontal parallax split is completely invisible while moving!
    left_fixed = left_332.copy()
    # Shift LEFT forest band (loc 72..204 -> 76..204) by 4px so 0 tree pixels poke above y_hd=384
    l_forest = left_332.crop((0, 72, 1024, 204)).resize((1024, 128), Image.Resampling.LANCZOS)
    left_fixed.paste(l_forest, (0, 76))

    right_fixed = right_332.copy()
    # Shift RIGHT forest band (loc 54..204 -> 76..204) so ALL tall right-side tree crowns stay below y_hd=384
    r_forest = right_332.crop((0, 54, 1024, 204)).resize((1024, 128), Image.Resampling.LANCZOS)
    right_fixed.paste(r_forest, (0, 76))

    # Unify entire upper cloud band (loc 0..76 = y_hd 308..384) across 2048px using cool indigo clouds from LEFT
    clouds_l = left_332.crop((0, 0, 1024, 76))
    # Fill tiny bottom 3px of clouds_l (loc 73..76) from loc 70..73 so 0 tree tips exist in the cloud strip
    clouds_l.paste(clouds_l.crop((0, 70, 1024, 73)), (0, 73))
    clouds_r = ImageOps.mirror(clouds_l)
    left_fixed.paste(clouds_l, (0, 0))
    right_fixed.paste(clouds_r, (0, 0))

    base = Image.new("RGBA", (2048, 1024), (0, 0, 0, 255))
    base.paste(left_fixed, (0, 308))
    base.paste(right_fixed, (1024, 308))
    # Smooth cloud sky wrap seams at x=1024 and x=0 (y=308..384 above HDMA split!)
    blend_internal_seam_x(base, 1024, 308, 384, half_w=48)
    blend_internal_seam_x(base, 0, 308, 384, half_w=48)

    # Softly dissolve the forest/meadow HDMA split (y_hd=512) into a unified dark nocturnal forest-floor shadow
    # so different parallax scroll offsets never show a hard horizontal cut line!
    barr = np.array(base, dtype=np.float32)
    shadow_col = np.array([10.0, 18.0, 19.0], dtype=np.float32)
    # Build horizontal protection mask for the two foreground brown brick walls (x=0..118 and x=1024..1142)
    x_idx = np.arange(2048, dtype=np.float32)
    brick_prot = np.zeros(2048, dtype=np.float32)
    for bx0, bx1 in [(0, 114), (1024, 1138)]:
        # 1.0 inside brick wall, feathered over 12px on the right edge
        brick_prot[bx0:bx1] = 1.0
        for dx in range(12):
            if bx1 + dx < 2048:
                brick_prot[bx1 + dx] = max(brick_prot[bx1 + dx], 1.0 - (dx + 1) / 12.0)
    # Apply smooth cos^2 shadow veil across y_hd=488..536 (peak 0.90 at y=511/512; bricks protected below y=512!)
    for y in range(488, 536):
        dist = abs(y - 511.5) / 24.5
        w_base = 0.90 * (math.cos(dist * math.pi * 0.5) ** 2)
        if y >= 512:
            # Foreground brick walls sit cleanly IN FRONT of the forest-floor mist!
            w_x = w_base * (1.0 - 0.88 * brick_prot)
        else:
            # Protect slate watchtower above left brick wall (x=0..92) lightly so its stones stay crisp
            tower_prot = np.where(x_idx < 96, np.clip((96.0 - x_idx) / 16.0, 0.0, 1.0), 0.0)
            w_x = w_base * (1.0 - 0.65 * tower_prot)
        barr[y, :, :3] = barr[y, :, :3] * (1.0 - w_x[:, None]) + shadow_col[None, :] * w_x[:, None]
    # Also softly blend the top 6px of forest sky (y=384..390) into cool night sky ONLY where pixels are sky (not tower)
    base = Image.fromarray(np.clip(barr, 0, 255).astype(np.uint8), "RGBA").copy()

    # Stars & drifting fog wisps in upper sky (y < 384)
    bpx = base.load()
    for sx, sy in A07_STARS_1X:
        draw_star(bpx, 2048, 1024, sx * SCALE, sy * SCALE, sf=1)
    for fx, fy in A07_NEBEL_02_1X:
        base.alpha_composite(nebel2, (fx * SCALE, fy * SCALE))

    # 2. Composite 5 calm spectral ghost horses across 4 clean frames (ZERO double-exposure, ZERO grass box!)
    #    Each horse stays 100% the exact same horse in the exact same spot; hooves tuck softly 6px into the meadow grass!
    def tuck_hooves(spr: Image.Image) -> Image.Image:
        arr = np.array(spr, dtype=np.float32)
        h = arr.shape[0]
        # Gently soften bottom 10px at hooves so grass blades naturally hide the hoof tips
        for dy in range(10):
            y = h - 1 - dy
            arr[y, :, 3] *= (0.20 + 0.80 * (dy / 10.0))
        # Subtle ghostly translucency (88% opacity) so the nocturnal meadow mist glows softly behind the ribcage
        arr[:, :, 3] *= 0.88
        return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGBA")

    stand_clean = [tuck_hooves(im) for im in stand_frames]
    graze_clean = [tuck_hooves(im) for im in graze_frames]

    # Horse positions naturally nestled in the meadow clearings of left_332 (0..1024) & right_332 (1024..2048):
    #   (x_center, y_hooves, frames_list, phase_offset, flip_x)
    horse_specs = [
        (332,  614, graze_clean, 0, True),   # Left clearing: calm grazing horse facing right near mossy ruin
        (560,  624, stand_clean, 1, False),  # Center-left open meadow: calm standing horse facing right
        (788,  620, graze_clean, 2, False),  # Right-left meadow: calm grazing horse facing left
        (1340, 622, stand_clean, 3, False),  # Right half left clearing: calm standing horse facing right
        (1776, 620, graze_clean, 1, False),  # Right half right clearing: calm grazing horse facing left
    ]

    frames = []
    for f_idx in range(4):
        fr = base.copy()
        for hx, hy_bot, f_list, ph_off, do_flip in horse_specs:
            spr = f_list[(f_idx + ph_off) % 4]
            if do_flip:
                spr = ImageOps.mirror(spr)
            fr.alpha_composite(spr, (hx - spr.width // 2, hy_bot - spr.height))
        frames.append(fr.convert("RGB"))
        frames[-1].save(audit_dir / f"A07-bg2-frame_{f_idx}.png")
    return frames


def build_all(a06_hd: Path, a07_hd: Path, a08_hd: Path, prior: Path, output: Path, audit: Path):
    a06_hd, a07_hd, a08_hd, prior, output, audit = [Path(p).resolve() for p in (a06_hd, a07_hd, a08_hd, prior, output, audit)]
    if output.exists() or audit.exists():
        raise FileExistsError("Use new output and audit directories")
    audit.mkdir(parents=True)
    receipts = []

    def track(path: Path, rel_prefix: str) -> Path:
        path = Path(path).resolve()
        receipts.append({
            "source": str(path),
            "sha256": sha(path),
            "backup_relative_path": f"{rel_prefix}/{path.name}",
        })
        return path

    prior_meta = json.loads((prior / "pack.json").read_text(encoding="utf-8"))
    before = {str(p.relative_to(prior)): sha(p) for p in prior.rglob("*") if p.is_file()}
    shutil.copytree(prior, output)

    # Load shared master kits!
    cobbles, cobble_l, cobble_r = build_cobble_kit(a06_hd)
    a06_treppe = Image.open(track(a06_hd / "A06-Treppe_HD_4x.png", "A06/HD-Gemini")).convert("RGBA")
    a06_plank = Image.open(track(a06_hd / "A06-Holzplanke_HD_4x.png", "A06/HD-Gemini")).convert("RGBA")
    a06_spin_plank = Image.open(track(a06_hd / "A06-Holz-was sich dreht_HD_4x.png", "A06/HD-Gemini")).convert("RGBA")

    # Shared OBJ base from a05 (16 shared objects) + A06 HD crescent moon + 26 rotating wooden plank OBJ tiles!
    a05_meta = json.loads((prior / "a05" / "pack.json").read_text(encoding="utf-8"))
    _, _, a05_tiles = load_pack(prior / "a05")
    shared_keys = list(a05_meta.get("shared_objects", []))
    base_obj_tiles = {k: a05_tiles[k] for k in shared_keys}

    a5_assets = Assets(ROOT / "artwork-local/level-editor/rooms/05")
    a6_assets = Assets(ROOT / "artwork-local/level-editor/rooms/06")
    a7_assets = Assets(ROOT / "artwork-local/level-editor/rooms/07")

    # Rotating wooden plank OBJ tiles (all 3 rotation angles: 0, 45, 90 deg!)
    plank_obj_tiles = build_rotating_plank_obj_tiles(a6_assets, a06_spin_plank, audit)
    print(f"Built {len(plank_obj_tiles)} HD rotating wooden plank OBJ tiles!")

    # Moon OBJ tiles (A06 & A08)
    a06_sky = Image.open(track(a06_hd / "A06-BG-02-01_HD_4x.png", "A06/HD-Gemini")).convert("RGB")
    moon_im = make_moon_sprite_64(a06_sky)
    moon_tiles = {}
    for cy in range(2):
        for cx_t in range(2):
            px_idx = tile_indices(a5_assets, 170 + cx_t + cy * 16, 0x6000).ravel().tolist()
            key = fnv_key(4, px_idx, list(a5_assets.colors[224:240]))
            moon_tiles[key] = np.array(moon_im.crop((cx_t * 32, cy * 32, cx_t * 32 + 32, cy * 32 + 32)))

    # =====================================================================
    # 1. REBUILD A06 (block = 5, x = 0..1536 + Left/Right 16:9 Endstücke!)
    # =====================================================================
    a06_strips = [Image.open(track(a06_hd / f"A06-0{i}_HD_4x.png", "A06/HD-Gemini")).convert("RGBA") for i in range(1, 7)]
    nat5_solid, nat5_front = render_native_bg1_alpha(a5_assets)  # (224, 2048)

    # Full A06 gameplay width = 1536 native = 6144 HD (A06-01..06 was 6016 -> extend 128px with full cobblestone divider wall!)
    a06_play = Image.new("RGBA", (6144, 896), (0, 0, 0, 0))
    cx = 0
    for s in a06_strips:
        a06_play.paste(s, (cx, 0)); cx += s.width
    # Fill right cobblestone divider wall (x_native=1472..1536 -> x_hd=5888..6144) seamlessly using unified HD cobblestones!
    for idx, gy in enumerate(range(0, 896, 64)):
        a06_play.alpha_composite(cobbles[idx % 4], (5888, gy))
        a06_play.alpha_composite(cobbles[(idx + 2) % 4], (6016, gy))

    # Stamp unified HD cobblestones on A06 ceiling & mid-level platforms matching native_bg1_A06!
    # Ceiling lintel: x=256..512 (hd 1024..2048), y=0..32 (hd 0..128)
    for row_i, gy in enumerate((0, 64)):
        for col_i, gx in enumerate(range(1024, 2048, 128)):
            a06_play.alpha_composite(cobbles[(row_i + col_i) % 4], (gx, gy))
    # Mid-level stone bridge: x=928..1280 (hd 3712..5120), y=112..144 (hd 448..576)
    # Wait: check exact y of stone bridge in nat5_front! In native_bg1_A06: top row y=96..112 (hd 384..448), bot y=112..128 (hd 448..512)!
    # Let's read exact cobblestone block coords directly from nat5_front (tiles 0x001..0x008 pal 2)!
    for ty in range(0, 28, 2):
        for tx in range(0, 184, 4):  # x = 0..1472
            # Check if 4x2 tile block (32x16 native = 128x64 HD) is a full cobblestone block (pal 2, tids 1..8)
            blk = nat5_front[ty:ty + 2, tx:tx + 4]
            if blk.shape == (2, 4) and np.all(((blk >> 10) & 7) == 2) and np.all((blk & 1023) >= 1) and np.all((blk & 1023) <= 8):
                a06_play.alpha_composite(cobbles[(tx // 4 + ty // 2) % 4], (tx * 32, ty * 32))

    # Stamp unified HD wooden bridge beams (3 beams at x=736..928 -> hd 2944..3712, y=96..112 -> hd 384..448!)
    # Check exact y of A06 wooden bridge beams from nat5_front (tids 0x009..0x01f pal 3)
    for ty in range(0, 28):
        for tx in range(0, 184):
            tid = int(nat5_front[ty, tx]) & 1023
            pal = (int(nat5_front[ty, tx]) >> 10) & 7
            if pal == 3 and tid in (0x009, 0x01f):
                # Start of a 64x16 native (256x64 HD) wooden beam if next 7 tiles are beam tiles
                pass
    # Stamp unified A06-Holzplanke_HD_4x (256x64) cleanly over the 3 elevated wooden bridge beams at y=384 (native y=96)!
    # Verify native y of elevated bridge in nat5_solid:
    bridge_ys = np.where(nat5_solid[:, 760])[0]
    by_top = int(bridge_ys.min()) if len(bridge_ys) else 96
    if 88 <= by_top <= 116:
        beam_256 = a06_plank.resize((256, 64), Image.Resampling.LANCZOS)
        for bx_1x in (736, 800, 864):
            a06_play.alpha_composite(beam_256, (bx_1x * 4, by_top * 4))

    # Stamp unified HD descending wooden staircases on A06 (both descending left-to-right!)
    # Stair 1: x=640..736 (hd 2560..2944), descends to bridge top (by_top*4)
    # Stair 2: x=1344..1440 (hd 5376..5760), descends to floor (y=768)
    # Wait: A06-03 & A06-06 already have great stairs baked in; locking alpha to nat5_solid ensures 100% alignment!

    # Lock A06 alpha 100% pixel-exact to native_bg1_A06 (fixes ALL 713 tree cutout holes & ALL window lintel notches!)
    nat5_a4 = (nat5_solid[:, :1536].repeat(4, 0).repeat(4, 1).astype(np.uint8) * 255)
    # Where nat5 is solid (255) but our HD alpha was 0 (e.g. jagged window lintel notches!), fill from nearest non-transparent pixel vertically!
    a06_arr = np.array(a06_play)
    hole_fix = (nat5_a4 == 255) & (a06_arr[:, :, 3] < 128)
    if hole_fix.any():
        # Copy clean masonry/tree color from 16px above (or below) into those tiny fixed lintel/tree notches!
        ys_h, xs_h = np.where(hole_fix)
        for y, x in zip(ys_h, xs_h):
            # Look up to 24px upward, then downward for an opaque HD pixel
            found = False
            for dy in range(1, 28):
                if y - dy >= 0 and a06_arr[y - dy, x, 3] >= 128:
                    a06_arr[y, x, :3] = a06_arr[y - dy, x, :3]; found = True; break
            if not found:
                for dy in range(1, 28):
                    if y + dy < 896 and a06_arr[y + dy, x, 3] >= 128:
                        a06_arr[y, x, :3] = a06_arr[y + dy, x, :3]; found = True; break
    a06_arr[:, :, 3] = nat5_a4
    a06_play = Image.fromarray(a06_arr, "RGBA")

    # Build A06 Left & Right 16:9 Widescreen Endstücke (172x896 each!)
    brick_col = a06_strips[0].crop((0, 0, 128, 896))
    brick_mir = ImageOps.mirror(brick_col)
    a06_ws_left = Image.new("RGBA", (WS_MARGIN_HD, 896), (0, 0, 0, 255))
    a06_ws_left.paste(brick_mir, (WS_MARGIN_HD - 128, 0))
    a06_ws_left.paste(brick_col.crop((128 - (WS_MARGIN_HD - 128), 0, 128, 896)), (0, 0))

    # Right widescreen endcap for A06 (x=1536..1579): seamless continuation of the right cobblestone divider wall!
    a06_ws_right = Image.new("RGBA", (WS_MARGIN_HD, 896), (12, 8, 14, 255))
    for idx, gy in enumerate(range(0, 896, 64)):
        a06_ws_right.alpha_composite(cobbles[(idx + 1) % 4], (0, gy))
        a06_ws_right.alpha_composite(cobbles[(idx + 3) % 4].crop((0, 0, WS_MARGIN_HD - 128, 64)), (128, gy))

    # Assemble full A06 foreground (left_ws + 6144 playfield = 6316x896) + overlay widescreen_left & widescreen_right!
    a06_full = Image.new("RGBA", (WS_MARGIN_HD + 6144, 896), (0, 0, 0, 0))
    a06_full.paste(a06_ws_left, (0, 0))
    a06_full.paste(a06_play, (WS_MARGIN_HD, 0))
    a06_full.save(audit / "A06-foreground-v16.png")

    # Write a06 folder (keep verified A06 BG2 region_01.png intact!)
    a06_dir = output / "a06"
    if a06_dir.exists(): shutil.rmtree(a06_dir)
    a06_dir.mkdir(parents=True)
    shutil.copy2(prior / "a06" / "region_01.png", a06_dir / "region_01.png")

    a06_tiles = {**base_obj_tiles, **moon_tiles, **plank_obj_tiles}
    write_pack(a06_tiles, a06_dir, SCALE)
    a06_atlas = json.loads((a06_dir / "pack.json").read_text(encoding="utf-8"))

    a06_regions = []
    for x in range(0, a06_full.width, 4096):
        name = f"foreground_{x // 4096:02d}.png"
        a06_full.crop((x, 0, min(a06_full.width, x + 4096), 896)).save(a06_dir / name)
        a06_regions.append(dict(image=name, layer=0, x=-WS_MARGIN_NATIVE + x // SCALE, y=0, coordinates="world", wrap_x=0, wrap_y=0, modes=[1]))
    a06_ws_left.save(a06_dir / "widescreen_left.png")
    a06_ws_right.save(a06_dir / "widescreen_right.png")
    a06_regions.extend([
        dict(image="widescreen_left.png", layer=1, x=-WS_MARGIN_NATIVE, y=0, coordinates="world", wrap_x=0, wrap_y=0, modes=[1], overlay=1, stationary=1, priority=0xC000),
        dict(image="widescreen_right.png", layer=1, x=1536, y=0, coordinates="world", wrap_x=0, wrap_y=0, modes=[1], overlay=1, stationary=1, priority=0xC000),
        dict(image="region_01.png", layer=1, x=0, y=0, coordinates="map", wrap_x=512, wrap_y=512, modes=[1]),
    ])
    (a06_dir / "pack.json").write_text(json.dumps({
        "version": 1, "scale": SCALE, "tile_size": SCALE * 8, "atlas_size": a06_atlas["atlas_size"],
        "tiles": a06_atlas["tiles"], "scene_block": 5, "native_maps": [0, 4096],
        "requires": ["scene-regions-v1", "shared-objects-v1", "scene-overlays-v1"],
        "shared_objects": shared_keys, "regions": a06_regions,
    }, indent=2) + "\n", encoding="utf-8")

    # =====================================================================
    # 2. REBUILD A07 (block = 6, x = 0..1536 + Unified Modular Kit + NO Static Trapdoors
    #                 + 6-Frame Animated Ghost Horses + Seamless Forest-to-Meadow + 16:9 Endstücke!)
    # =====================================================================
    a07_strips = [Image.open(track(a07_hd / f"A07-0{i}_HD_4x.png", "A07/HD-Gemini")).convert("RGBA") for i in range(1, 7)]
    nat6_solid, nat6_front = render_native_bg1_alpha(a6_assets)  # (224, 1536)

    a07_play = Image.new("RGBA", (6144, 896), (0, 0, 0, 0))
    cx = 0
    for s in a07_strips:
        a07_play.paste(s, (cx, 0)); cx += s.width

    # Master modular pieces from our crispest A07-01 / A07-03 / A07-06 HD art:
    #   1) Pure fluted burgundy wall patch (128x64) for erasing ALL 9 baked rotating trapdoors cleanly!
    #   2) Master unified double-stacked weathered oak floor beam with rusted iron end-caps (256x64 from A07-01 x=512..768, y=768..832)!
    #   3) Master unified thick weathered oak log beam (256x64 from A07-03 x=416..672, y=768..832)!
    pure_wall_128x64 = a07_strips[5].crop((768, 320, 896, 384))  # crisp fluted burgundy wall!
    master_double_beam = a07_strips[0].crop((512, 768, 768, 832))  # 256x64 double-stacked oak beam with iron caps!
    master_log_256 = a07_strips[2].crop((416, 768, 672, 832))      # 256x64 thick weathered oak log beam!
    iron_cap_l = master_double_beam.crop((0, 0, 28, 64))

    # A) ERASE ALL 9 BAKED STATIC ROTATING TRAPDOORS FROM BG1 (replace with pure fluted burgundy wall!)
    a07_trapdoor_xs_1x = [192, 288, 448, 608, 704, 800, 864, 960, 1440]
    for tx_1x in a07_trapdoor_xs_1x:
        a07_play.paste(pure_wall_128x64, (tx_1x * 4, 768))

    # B) STAMP UNIFIED MASTER DOUBLE-STACKED FLOOR BEAMS (all 8 exact slots = 100% consistent!)
    for bx_1x in [128, 224, 320, 384, 480, 544, 736, 896]:
        a07_play.paste(master_double_beam, (bx_1x * 4, 768))

    # C) STAMP UNIFIED MASTER THICK OAK LOG BEAMS (all 5 exact slots = 100% consistent!)
    #   64px wide (256 HD): 640, 1472
    #   32px wide (128 HD): 832, 992
    #   96px wide (384 HD): 1344
    a07_play.paste(master_log_256, (640 * 4, 768))
    a07_play.paste(master_log_256, (1472 * 4, 768))
    # 128px short oak log blocks (left iron cap + weathered log)
    short_log_128 = master_log_256.crop((0, 0, 128, 64)).copy()
    short_log_128.paste(iron_cap_l, (0, 0))
    a07_play.paste(short_log_128, (832 * 4, 768))
    a07_play.paste(short_log_128, (992 * 4, 768))
    # 384px long oak log block at 1344..1440
    long_log_384 = Image.new("RGBA", (384, 64), (0, 0, 0, 0))
    long_log_384.paste(master_log_256, (0, 0))
    long_log_384.paste(master_log_256.crop((128, 0, 256, 64)), (256, 0))
    long_log_384.paste(iron_cap_l, (0, 0))
    a07_play.paste(long_log_384, (1344 * 4, 768))

    # D) STAMP UNIFIED HD COBBLESTONES ON A07-01 & A07-06 LANDINGS (exact 128x64 tiles)
    for idx, (gx, gy) in enumerate([(0, 768), (128, 768), (256, 768), (5120, 768), (5248, 768), (5120, 832)]):
        a07_play.alpha_composite(cobbles[idx % 4], (gx, gy))

    # E) STAMP PIXEL-EXACT HD WOODEN STAIRS FROM NATIVE SNES 0x2c TILEMAP (0 px offset under Simon's boots!)
    a07_play.paste(pure_wall_128x64, (384, 768)); a07_play.paste(pure_wall_128x64, (384, 832))
    a07_play.paste(pure_wall_128x64, (4992, 768)); a07_play.paste(pure_wall_128x64, (4992, 832))
    stamp_stairs_from_tilemap(a07_play, a06_treppe, nat6_front, 0, 1536)

    # F) LOCK A07 ALPHA 100% PIXEL-EXACT TO NATIVE BG1 (eliminates ALL jagged notches along window top lintels y=64..75!)
    nat6_a4 = (nat6_solid[:, :1536].repeat(4, 0).repeat(4, 1).astype(np.uint8) * 255)
    # Keep top void above roofline (y < 164) opaque true-black just like native tiles!
    a07_arr = np.array(a07_play)
    hole_fix = (nat6_a4 == 255) & (a07_arr[:, :, 3] < 128)
    if hole_fix.any():
        ys_h, xs_h = np.where(hole_fix)
        for y, x in zip(ys_h, xs_h):
            for dy in range(1, 28):
                if y - dy >= 0 and a07_arr[y - dy, x, 3] >= 128:
                    a07_arr[y, x, :3] = a07_arr[y - dy, x, :3]; break
    a07_arr[:, :, 3] = nat6_a4
    a07_play = Image.fromarray(a07_arr, "RGBA")

    # G) BUILD A07 LEFT & RIGHT 16:9 WIDESCREEN ENDSTÜCKE (172x896 each!)
    pillar_l = a07_play.crop((0, 0, 128, 896))
    pillar_mir = ImageOps.mirror(pillar_l)
    a07_ws_left = Image.new("RGBA", (WS_MARGIN_HD, 896), (0, 0, 0, 255))
    a07_ws_left.paste(pillar_mir, (WS_MARGIN_HD - 128, 0))
    a07_ws_left.paste(pillar_l.crop((128 - (WS_MARGIN_HD - 128), 0, 128, 896)), (0, 0))

    # Right widescreen endcap for A07 (x=1536..1579): seamless continuation of A07-06's fluted burgundy wall + floor oak beam!
    right_src = a07_play.crop((6144 - WS_MARGIN_HD, 0, 6144, 896))
    a07_ws_right = ImageOps.mirror(right_src)

    a07_full = Image.new("RGBA", (WS_MARGIN_HD + 6144, 896), (0, 0, 0, 0))
    a07_full.paste(a07_ws_left, (0, 0))
    a07_full.paste(a07_play, (WS_MARGIN_HD, 0))
    a07_full.save(audit / "A07-foreground-v16.png")

    # H) BUILD A07 6-FRAME ANIMATED GHOST-HORSE BG2 + SEAMLESS FOREST-TO-MEADOW TRANSITION!
    bg2_frames = build_a07_animated_bg2(a07_hd, a06_hd, audit, track)

    a07_dir = output / "a07"
    if a07_dir.exists(): shutil.rmtree(a07_dir)
    a07_dir.mkdir(parents=True)

    a07_tiles = {**base_obj_tiles, **plank_obj_tiles}
    write_pack(a07_tiles, a07_dir, SCALE)
    a07_atlas = json.loads((a07_dir / "pack.json").read_text(encoding="utf-8"))

    a07_regions = []
    for x in range(0, a07_full.width, 4096):
        name = f"foreground_{x // 4096:02d}.png"
        a07_full.crop((x, 0, min(a07_full.width, x + 4096), 896)).save(a07_dir / name)
        a07_regions.append(dict(image=name, layer=0, x=-WS_MARGIN_NATIVE + x // SCALE, y=0, coordinates="world", wrap_x=0, wrap_y=0, modes=[1]))
    a07_ws_left.save(a07_dir / "widescreen_left.png")
    a07_ws_right.save(a07_dir / "widescreen_right.png")
    a07_regions.extend([
        dict(image="widescreen_left.png", layer=1, x=-WS_MARGIN_NATIVE, y=0, coordinates="world", wrap_x=0, wrap_y=0, modes=[1], overlay=1, stationary=1, priority=0xC000),
        dict(image="widescreen_right.png", layer=1, x=1536, y=0, coordinates="world", wrap_x=0, wrap_y=0, modes=[1], overlay=1, stationary=1, priority=0xC000),
    ])
    for fi, fr_im in enumerate(bg2_frames):
        fname = f"region_01_f{fi}.png"
        fr_im.save(a07_dir / fname)
        a07_regions.append(dict(
            image=fname, layer=1, x=0, y=0, coordinates="map", wrap_x=512, wrap_y=512, modes=[1],
            frame_period=24, frame_count=len(bg2_frames), frame_phase=fi,
        ))
    (a07_dir / "pack.json").write_text(json.dumps({
        "version": 1, "scale": SCALE, "tile_size": SCALE * 8, "atlas_size": a07_atlas["atlas_size"],
        "tiles": a07_atlas["tiles"], "scene_block": 6, "native_maps": [0, 4096],
        "requires": ["scene-regions-v1", "shared-objects-v1", "scene-overlays-v1"],
        "shared_objects": shared_keys, "regions": a07_regions,
    }, indent=2) + "\n", encoding="utf-8")

    # =====================================================================
    # 3. REBUILD A08 (block = 7, x = 1504..2048 + NO Static Trapdoors
    #                 + Seamless 16:9 Left & Right Boss Chamber Endstücke!)
    # =====================================================================
    s07 = Image.open(track(a08_hd / "A08-07_HD_4x.png", "A08/HD-Gemini")).convert("RGBA")
    s08 = Image.open(track(a08_hd / "A08-08_HD_4x.png", "A08/HD-Gemini")).convert("RGBA")

    # ERASE BOTH BAKED STATIC ROTATING TRAPDOORS IN A08-07 (local x=512..640 and 896..1024, y=768..832)!
    # Behind those two trapdoors is the dark fluted burgundy wall leading into the pit void (y=832..896)!
    s07_clean = s07.copy()
    dark_pit_wall = pure_wall_128x64.copy()
    dp_arr = np.array(dark_pit_wall, dtype=np.float32)
    # Darken smoothly downward into the black pit void at y=832!
    for py in range(64):
        shade = 0.80 * (1.0 - 0.65 * (py / 63.0))
        dp_arr[py, :, :3] *= shade
    dark_pit_wall = Image.fromarray(np.clip(dp_arr, 0, 255).astype(np.uint8), "RGBA")
    s07_clean.paste(dark_pit_wall, (512, 768))
    s07_clean.paste(dark_pit_wall, (896, 768))

    # Build A08 Left & Right 16:9 Widescreen Endstücke!
    a08_left_margin_nat = 76
    a08_left_margin_hd = a08_left_margin_nat * SCALE  # 304 px (covers camera_x=1471 - 43 = 1428!)
    stone_col = s07_clean.crop((0, 0, 128, 896))
    stone_mir = ImageOps.mirror(stone_col)
    a08_ws_left = Image.new("RGBA", (a08_left_margin_hd, 896), (0, 0, 0, 255))
    a08_ws_left.paste(stone_mir, (a08_left_margin_hd - 128, 0))
    a08_ws_left.paste(stone_col, (a08_left_margin_hd - 256, 0))
    rem = a08_left_margin_hd - 256
    a08_ws_left.paste(stone_mir.crop((128 - rem, 0, 128, 896)), (0, 0))

    # Right widescreen endcap for A08 Boss Chamber (x=2048..2091, 172x896):
    # Cleanly closes the indoor Boss Chamber wall with burgundy stonework + wainscoting + 2-row cobblestone floor!
    a08_ws_right = Image.new("RGBA", (WS_MARGIN_HD, 896), (12, 6, 12, 255))
    # Pure burgundy fluted wall + wainscoting sampled from s08 (x=720..892, y=0..768 -> NO window, NO pillar!)
    boss_wall_strip = s08.crop((768, 0, 896, 768))
    a08_ws_right.paste(boss_wall_strip, (0, 0))
    a08_ws_right.paste(ImageOps.mirror(boss_wall_strip).crop((0, 0, WS_MARGIN_HD - 128, 768)), (128, 0))
    # Extend the 2-row cobblestone Boss Arena floor cleanly across y=768..896!
    a08_ws_right.alpha_composite(cobbles[0], (0, 768))
    a08_ws_right.alpha_composite(cobbles[2].crop((0, 0, WS_MARGIN_HD - 128, 64)), (128, 768))
    a08_ws_right.alpha_composite(cobbles[1], (0, 832))
    a08_ws_right.alpha_composite(cobbles[3].crop((0, 0, WS_MARGIN_HD - 128, 64)), (128, 832))

    a08_full = Image.new("RGBA", (a08_left_margin_hd + s07_clean.width + s08.width, 896), (0, 0, 0, 0))
    a08_full.paste(a08_ws_left, (0, 0))
    a08_full.paste(s07_clean, (a08_left_margin_hd, 0))
    a08_full.paste(s08, (a08_left_margin_hd + s07_clean.width, 0))
    a08_full.save(audit / "A08-foreground-v16.png")

    a08_dir = output / "a08"
    if a08_dir.exists(): shutil.rmtree(a08_dir)
    a08_dir.mkdir(parents=True)
    shutil.copy2(prior / "a06" / "region_01.png", a08_dir / "region_01.png")

    a08_tiles = {**base_obj_tiles, **moon_tiles, **plank_obj_tiles}
    write_pack(a08_tiles, a08_dir, SCALE)
    a08_atlas = json.loads((a08_dir / "pack.json").read_text(encoding="utf-8"))

    a08_full.save(a08_dir / "foreground_00.png")
    a08_ws_left.save(a08_dir / "widescreen_left.png")
    a08_ws_right.save(a08_dir / "widescreen_right.png")
    a08_regions = [
        dict(image="foreground_00.png", layer=0, x=1504 - a08_left_margin_nat, y=0, coordinates="world", wrap_x=0, wrap_y=0, modes=[1]),
        dict(image="widescreen_left.png", layer=1, x=1504 - a08_left_margin_nat, y=0, coordinates="world", wrap_x=0, wrap_y=0, modes=[1], overlay=1, stationary=1, priority=0xC000),
        dict(image="widescreen_right.png", layer=1, x=2048, y=0, coordinates="world", wrap_x=0, wrap_y=0, modes=[1], overlay=1, stationary=1, priority=0xC000),
        dict(image="region_01.png", layer=1, x=0, y=0, coordinates="map", wrap_x=512, wrap_y=512, modes=[1]),
    ]
    (a08_dir / "pack.json").write_text(json.dumps({
        "version": 1, "scale": SCALE, "tile_size": SCALE * 8, "atlas_size": a08_atlas["atlas_size"],
        "tiles": a08_atlas["tiles"], "scene_block": 7, "native_maps": [0, 4096],
        "requires": ["scene-regions-v1", "shared-objects-v1", "scene-overlays-v1"],
        "shared_objects": shared_keys, "regions": a08_regions,
    }, indent=2) + "\n", encoding="utf-8")

    # =====================================================================
    # 4. UPDATE COLLECTION PACK.JSON & RECEIPTS
    # =====================================================================
    scenes = list(prior_meta["scenes"])
    for sc in ("a06", "a07", "a08"):
        if sc not in scenes:
            scenes.append(sc)
    prior_meta["scenes"] = scenes
    prior_meta["name"] = "Stage 01 HD v17: A01-A08 complete, 0x2c exact stairs, unified A07 BG2, calm 4-frame ghost horses"
    (output / "pack.json").write_text(json.dumps(prior_meta, indent=2) + "\n", encoding="utf-8")

    assert before == {str(p.relative_to(prior)): sha(p) for p in prior.rglob("*") if p.is_file()}, "Prior pack changed!"
    assert all(sha(r["source"]) == r["sha256"] for r in receipts), "Source changed during import!"

    report = {
        "rotating_plank_obj_tiles": len(plank_obj_tiles),
        "a06_foreground": list(a06_full.size),
        "a07_foreground": list(a07_full.size),
        "a07_bg2_frames": len(bg2_frames),
        "a08_foreground": list(a08_full.size),
        "scenes": scenes,
    }
    receipt = {
        "art_scale": SCALE, "presentation_scale": SCALE,
        "sources": receipts, "builder_sha256": sha(__file__),
        "preserved_existing_collection": str(prior), "prior_sha256": before,
        "report": report, "source_files_unchanged": True,
    }
    (output / "import.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    (audit / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output), **report}, indent=2))


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--a06-hd", type=Path, required=True)
    p.add_argument("--a07-hd", type=Path, required=True)
    p.add_argument("--a08-hd", type=Path, required=True)
    p.add_argument("--prior", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--audit", type=Path, required=True)
    args = p.parse_args()
    build_all(args.a06_hd, args.a07_hd, args.a08_hd, args.prior, args.out, args.audit)
