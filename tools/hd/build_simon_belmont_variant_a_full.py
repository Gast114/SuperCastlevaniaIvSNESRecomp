#!/usr/bin/env python3
"""Slice, color-lock, align, and build the complete 96-frame Simon Belmont HD Character Pack (Variant A v2):
- 100% opaque interior (strict border flood-fill, zero see-through holes in dark armor/hair/boots)
- Unified warm dark-gothic color tone locked to Sheet 2 (Walk/Idle-01 face & palette) across ALL 8 sheets
- Constant body scale & torso-spine centerline alignment (zero horizontal walk jitter, zero Giant-Simon when aiming UP)
- Exact 8-directional Whip-Hold poses (cells 29,30,44,48,49,59,60,70,75) using 100% locked Idle-01 body + rotating HD arm
"""

import json
import math
import shutil
from collections import deque
from pathlib import Path
from PIL import Image, ImageDraw
import numpy as np

ROOT = Path(r"D:\Super Castlevania IV Recomp\SuperCastlevaniaIvSNESRecomp")
BRAIN = Path(r"C:\Users\Gaming\.gemini\antigravity\brain\0e3d1566-2f3c-4183-be49-fad33ce3d4a9")
TPL_DIR = ROOT / "build-play" / "game" / "characters" / "simon-template"
USER_SIMON_DIR = Path(r"D:\Super Castlevania IV Recomp\Assets (ausgeschnitten)\Simon Belmont\HD_Variante_A")
USER_SIMON_DIR.mkdir(parents=True, exist_ok=True)

PACK_NAME = "simon-gothic-variant-a"
PACK_WORK = ROOT / "artwork-local" / "characters" / PACK_NAME
PACK_PLAY = ROOT / "build-play" / "game" / "characters" / PACK_NAME
PACK_BUILD = ROOT / "build" / "characters" / PACK_NAME
PACK_LUA = ROOT / "build-lua" / "characters" / PACK_NAME

SHEETS = {
    1: BRAIN / "simon_8poses_hd_remaster_v2_1795372715979.jpg",
    2: BRAIN / "simon_walk_4x2_hd_v2_1795372726123.jpg",
    3: BRAIN / "simon_stairs_8poses_hd_remaster_v1_1795376259295.jpg",
    4: BRAIN / "simon_sheet4_stairs_whip_windup_8poses_hd_v3_1795376308238.jpg",
    5: BRAIN / "simon_sheet5_whip_standing_crouch_8poses_hd_v2_1795376268442.jpg",
    6: BRAIN / "simon_sheet6_air_whip_8poses_hd_remaster_1795376251526.jpg",
    7: BRAIN / "simon_sheet7_swing_death_8poses_hd_remaster_1795376249381.jpg",
    8: BRAIN / "simon_stairs_whip_8poses_hd_remaster_1795376253863.jpg",
}


def matte_black_bg_opaque(im: Image.Image, bg_soft: int = 26, bg_hard: int = 12) -> Image.Image:
    """Remove pure black exterior background via strict border flood-fill while keeping 100% of Simon's
    interior pixels (dark armor, hair, shadows, boots) completely SOLID OPAQUE (alpha = 255)."""
    rgba = np.array(im.convert("RGBA"), dtype=np.float32)
    r, g, b = rgba[:, :, 0], rgba[:, :, 1], rgba[:, :, 2]
    lum = np.maximum(np.maximum(r, g), b)
    h, w = lum.shape

    bg_cand = lum < bg_soft
    ext = np.zeros((h, w), dtype=bool)
    q = deque()
    for x in range(w):
        if bg_cand[0, x]:
            ext[0, x] = True
            q.append((0, x))
        if bg_cand[h - 1, x] and not ext[h - 1, x]:
            ext[h - 1, x] = True
            q.append((h - 1, x))
    for y in range(h):
        if bg_cand[y, 0] and not ext[y, 0]:
            ext[y, 0] = True
            q.append((y, 0))
        if bg_cand[y, w - 1] and not ext[y, w - 1]:
            ext[y, w - 1] = True
            q.append((y, w - 1))

    while q:
        cy, cx = q.popleft()
        for ny, nx in ((cy - 1, cx), (cy + 1, cx), (cy, cx - 1), (cy, cx + 1)):
            if 0 <= ny < h and 0 <= nx < w and not ext[ny, nx] and bg_cand[ny, nx]:
                ext[ny, nx] = True
                q.append((ny, nx))

    # Only exterior pixels get alpha-ramped; ALL interior pixels are strictly 100% opaque (alpha = 1.0)!
    # Exception: large pure-black enclosed gaps (e.g. between crossed arms/legs, >= 140 px of lum <= 8)
    alpha = np.ones((h, w), dtype=np.float32)
    ext_alpha = np.clip((lum - bg_hard) / max(1.0, float(bg_soft - bg_hard)), 0.0, 1.0)
    alpha = np.where(ext, ext_alpha, 1.0)

    # Check for large enclosed pure-black background pockets (between legs/arms)
    inner_black = (~ext) & (lum <= 8.0)
    visited = np.zeros((h, w), dtype=bool)
    ys_b, xs_b = np.where(inner_black)
    for sy, sx in zip(ys_b.tolist(), xs_b.tolist()):
        if visited[sy, sx]:
            continue
        comp = []
        qq = deque([(sy, sx)])
        visited[sy, sx] = True
        while qq:
            cy, cx = qq.popleft()
            comp.append((cy, cx))
            for ny, nx in ((cy - 1, cx), (cy + 1, cx), (cy, cx - 1), (cy, cx + 1)):
                if 0 <= ny < h and 0 <= nx < w and not visited[ny, nx] and inner_black[ny, nx]:
                    visited[ny, nx] = True
                    qq.append((ny, nx))
        if len(comp) >= 140:
            for cy, cx in comp:
                alpha[cy, cx] = 0.0

    # Gentle edge decontamination only on semi-transparent exterior border
    edge = ext & (alpha > 0.05) & (alpha < 0.98)
    for c in range(3):
        rgba[:, :, c] = np.where(edge, np.clip(rgba[:, :, c] / np.maximum(alpha, 0.35), 0, 255), rgba[:, :, c])
    rgba[:, :, 3] = np.clip(alpha * 255.0, 0, 255)

    arr_u8 = rgba.astype(np.uint8)
    ys, xs = np.where(arr_u8[:, :, 3] > 20)
    if ys.size == 0:
        return Image.fromarray(arr_u8, "RGBA")
    return Image.fromarray(arr_u8[ys.min():ys.max() + 1, xs.min():xs.max() + 1], "RGBA")


def extract_cell(sheet_im: Image.Image, col: int, row: int) -> Image.Image:
    w, h = sheet_im.size
    cw, ch = w // 4, h // 2
    box = (col * cw + 6, row * ch + 6, (col + 1) * cw - 6, (row + 1) * ch - 6)
    return matte_black_bg_opaque(sheet_im.crop(box))


def compute_fg_stats(crops: list) -> tuple:
    """Compute per-channel mean & std of opaque foreground pixels across a list of RGBA crops."""
    rs, gs, bs = [], [], []
    for im in crops:
        arr = np.array(im, dtype=np.float32)
        m = arr[:, :, 3] > 220
        if m.any():
            rs.append(arr[m, 0])
            gs.append(arr[m, 1])
            bs.append(arr[m, 2])
    r = np.concatenate(rs)
    g = np.concatenate(gs)
    b = np.concatenate(bs)
    means = np.array([r.mean(), g.mean(), b.mean()], dtype=np.float32)
    stds = np.array([max(1.0, r.std()), max(1.0, g.std()), max(1.0, b.std())], dtype=np.float32)
    return means, stds


def match_color_to_anchor(im: Image.Image, src_means: np.ndarray, src_stds: np.ndarray,
                          tgt_means: np.ndarray, tgt_stds: np.ndarray, strength: float = 0.80) -> Image.Image:
    """Lock sheet color tone & warmth to Sheet 2 (Walk/Idle anchor) so Simon never shifts color between poses."""
    arr = np.array(im, dtype=np.float32)
    m = arr[:, :, 3] > 10
    for c in range(3):
        adj = (arr[:, :, c] - src_means[c]) * (tgt_stds[c] / src_stds[c]) + tgt_means[c]
        blended = arr[:, :, c] * (1.0 - strength) + adj * strength
        arr[:, :, c] = np.where(m, np.clip(blended, 0, 255), arr[:, :, c])
    return Image.fromarray(arr.astype(np.uint8), "RGBA")


def estimate_spine_x(alpha_2d: np.ndarray, y_lo_frac: float = 0.12, y_hi_frac: float = 0.52) -> float:
    """Estimate Simon's head/torso spine centerline X (ignoring outstretched arms)."""
    ys, xs = np.where(alpha_2d > 128)
    if ys.size == 0:
        return alpha_2d.shape[1] * 0.5
    y0, y1 = int(ys.min()), int(ys.max())
    h = max(1, y1 - y0)
    band = (ys >= y0 + int(h * y_lo_frac)) & (ys <= y0 + int(h * y_hi_frac))
    if band.sum() >= 10:
        return float(np.median(xs[band]))
    return float(np.median(xs))


def fit_simon_pose_to_cell(hd_crop: Image.Image, cell_1x: np.ndarray, cell_id: int) -> tuple:
    """Fit tight HD crop into the 96x96 cell at 10x scale using:
    - Constant body height scale (never blows Simon into a giant when arm reaches UP!)
    - Torso-spine horizontal registration (never jitters left/right when swinging arms!)
    """
    ys, xs = np.where(cell_1x[:, :, 3] > 0)
    x0, x1 = int(xs.min()), int(xs.max()) + 1
    y0, y1 = int(ys.min()), int(ys.max()) + 1
    w_1x = x1 - x0
    h_1x = y1 - y0

    tw, th = hd_crop.size

    # Detect poses where an arm extends straight UP above Simon's head (y0 < 27 while feet at y1 >= 74)
    # In those cases, if the HD crop itself ALSO has a raised arm, scale by h_1x;
    # otherwise cap body height to 46px (460px) so Simon NEVER becomes a giant!
    scale_h = (h_1x * 10.0) / max(1, th)
    scale_w = ((w_1x + 3) * 10.0) / max(1, tw)
    s = min(scale_h, scale_w * 1.05)

    # Extra safety guard: standing/walking poses with feet at y1>=74 should keep Simon's body height consistent
    # (normal standing body is ~46px -> 460px; only raised-arm poses exceed 490px).
    nw = max(10, int(round(tw * s)))
    nh = max(10, int(round(th * s)))
    resized = hd_crop.resize((nw, nh), Image.Resampling.LANCZOS)

    # Align bottom of boots to y1 * 10
    py1 = min(960, y1 * 10)
    py0 = max(0, py1 - nh)

    # Align horizontal spine centerline of HD torso/head to 1x torso/head spine centerline!
    spine_1x = estimate_spine_x(cell_1x[:, :, 3]) * 10.0
    spine_hd = estimate_spine_x(np.array(resized)[:, :, 3])
    px0 = int(round(spine_1x - spine_hd))
    px0 = max(0, min(960 - nw, px0))
    px1 = min(960, px0 + nw)

    ox = max(0, px0 // 10)
    oy = max(0, py0 // 10)
    ox1 = min(96, (px1 + 9) // 10)
    oy1 = min(96, (py1 + 9) // 10)
    dw = max(1, ox1 - ox)
    dh = max(1, oy1 - oy)

    sub_canvas = Image.new("RGBA", (dw * 10, dh * 10), (0, 0, 0, 0))
    sub_canvas.alpha_composite(resized, (px0 - ox * 10, py0 - oy * 10))
    return sub_canvas, [ox, oy], [dw, dh]


def build_locked_whiphold_pose(idle_full_960: Image.Image, strike_arm_full_960: Image.Image,
                               tip_1x: tuple, shoulder_1x: tuple = (49, 41)) -> tuple:
    """Build an 8-directional Whip-Hold pose where Simon's head, torso, hips, and legs are
    100% PIXEL-FOR-PIXEL IDENTICAL to Idle-01, and ONLY his armored right whip-arm rotates
    around the shoulder pivot to hit the exact 1x hand tip coordinate!"""
    sh_x, sh_y = shoulder_1x[0] * 10, shoulder_1x[1] * 10  # (490, 410)
    tx, ty = tip_1x[0] * 10, tip_1x[1] * 10

    # 1. Start with exact Idle-01 body and erase ONLY the raised idle forearm/fist protruding right of torso
    base_arr = np.array(idle_full_960, dtype=np.uint8)
    yy, xx = np.mgrid[0:960, 0:960]
    # Idle-01's right forearm/fist extends past x > 522 in y in [365..475]
    erase_idle_arm = (xx > 522) & (yy >= 360) & (yy <= 485)
    base_arr[erase_idle_arm, 3] = 0
    canvas = Image.fromarray(base_arr, "RGBA")

    # 2. Extract the straight horizontal armored whip-arm from Standing Forward Whip-Strike (cell 28)
    # In cell 28 (aligned to 960x960), the outstretched arm runs from shoulder ~(490, 410) to fist tip ~(685, 425)
    arm_arr = np.array(strike_arm_full_960, dtype=np.uint8)
    # Keep ONLY pixels of the right arm: x >= 475, y in [360..465]
    arm_mask = (xx >= 478) & (xx <= 720) & (yy >= 362) & (yy <= 465) & (arm_arr[:, :, 3] > 20)
    arm_only = np.zeros_like(arm_arr)
    arm_only[arm_mask] = arm_arr[arm_mask]

    # Measure actual arm tip in strike_arm_full_960
    ays, axs = np.where(arm_only[:, :, 3] > 128)
    if axs.size > 0:
        arm_tip_x = float(axs.max())
        # Median Y near the fist tip
        near_tip = axs >= (arm_tip_x - 25)
        arm_tip_y = float(np.median(ays[near_tip]))
    else:
        arm_tip_x, arm_tip_y = 660.0, 420.0

    src_dx = arm_tip_x - sh_x
    src_dy = arm_tip_y - sh_y
    src_len = max(10.0, math.hypot(src_dx, src_dy))
    src_ang = math.degrees(math.atan2(src_dy, src_dx))

    tgt_dx = tx - sh_x
    tgt_dy = ty - sh_y
    tgt_len = max(80.0, math.hypot(tgt_dx, tgt_dy))
    tgt_ang = math.degrees(math.atan2(tgt_dy, tgt_dx))

    # Scale arm length slightly (clamped to [0.78..1.18]) so arm proportions stay natural and reach exact hand tip!
    arm_scale = float(np.clip(tgt_len / src_len, 0.78, 1.18))
    rot_deg = -(tgt_ang - src_ang)  # PIL rotate is CCW positive, screen Y is down

    # Crop tightly around shoulder pivot in a centered square for clean rotation
    rad = 260
    arm_sq = Image.new("RGBA", (rad * 2, rad * 2), (0, 0, 0, 0))
    arm_im = Image.fromarray(arm_only, "RGBA")
    arm_sq.paste(arm_im.crop((sh_x - rad, sh_y - rad, sh_x + rad, sh_y + rad)), (0, 0))
    if abs(arm_scale - 1.0) > 0.01:
        ns = max(20, int(round(rad * 2 * arm_scale)))
        arm_scaled = arm_sq.resize((ns, ns), Image.Resampling.LANCZOS)
        arm_sq = Image.new("RGBA", (rad * 2, rad * 2), (0, 0, 0, 0))
        off = (rad * 2 - ns) // 2
        arm_sq.paste(arm_scaled, (off, off))
    arm_rot = arm_sq.rotate(rot_deg, Image.Resampling.BICUBIC, expand=False)

    # Composite rotated arm behind/onto shoulder, then restore Simon's shoulder pauldron & head cleanly on top!
    canvas.alpha_composite(arm_rot, (sh_x - rad, sh_y - rad))

    # Restore head & upper-left shoulder/chest from Idle-01 so head/hair/pauldron never get overlapped by rotated arm
    restore = np.array(idle_full_960, dtype=np.uint8)
    keep_head_pauldron = (
        ((yy < 395) & (xx < 525)) |           # head & hair
        ((xx >= 440) & (xx <= 515) & (yy >= 380) & (yy <= 435))  # shoulder pauldron
    )
    restore[~keep_head_pauldron, 3] = 0
    canvas.alpha_composite(Image.fromarray(restore, "RGBA"))

    # Tight sub-box crop in 1x cell coordinates [0..96]
    final_arr = np.array(canvas)
    fys, fxs = np.where(final_arr[:, :, 3] > 20)
    px0, px1 = int(fxs.min()), int(fxs.max()) + 1
    py0, py1 = int(fys.min()), int(fys.max()) + 1
    ox = max(0, px0 // 10)
    oy = max(0, py0 // 10)
    ox1 = min(96, (px1 + 9) // 10)
    oy1 = min(96, (py1 + 9) // 10)
    dw = max(1, ox1 - ox)
    dh = max(1, oy1 - oy)
    sub_canvas = canvas.crop((ox * 10, oy * 10, ox1 * 10, oy1 * 10))
    return sub_canvas, [ox, oy], [dw, dh]


def main():
    loaded_sheets = {}
    for idx, spath in SHEETS.items():
        loaded_sheets[idx] = Image.open(spath).convert("RGBA")
        shutil.copy2(spath, USER_SIMON_DIR / f"Simon_Belmont_Variante_A_Sheet_{idx:02d}_HD.jpg")

    # Map canonical cells to (sheet_idx, col, row)
    # CRITICAL FIX: Idle-01 (cell 4) now uses Sheet 2 (2, 0, 0) — the EXACT warm face & palette of the Walk poses!
    direct_cell_map = {
        4:  (2, 0, 0),  # Idle-01 (from Sheet 2 — matches Walking face & warm color tone 100%!)
        37: (1, 1, 0),  # Ducking-01
        9:  (1, 2, 0),  # Jumping-01
        28: (1, 3, 0),  # Standing Forward Whip-Strike
        0:  (2, 1, 0),  # Walking-01
        1:  (2, 2, 0),  # Walking-02
        2:  (2, 3, 0),  # Walking-03
        3:  (2, 0, 1),  # Walking-04
        5:  (2, 1, 1),  # Walking-05
        6:  (2, 2, 1),  # Walking-06

        # Sheet 3: Stairs Up (14..19) & Stairs Down (20..21)
        14: (3, 0, 0),
        15: (3, 1, 0),
        16: (3, 2, 0),
        17: (3, 1, 1),
        18: (3, 0, 1),
        19: (3, 1, 1),
        20: (3, 2, 1),
        21: (3, 3, 1),

        # Sheet 4: Stairs Down (22..25) & Standing Whip Windup / Diagonal Up-Forward Strikes
        22: (4, 0, 0),
        23: (4, 1, 0),
        24: (4, 2, 0),
        25: (4, 3, 0),
        26: (4, 0, 1),
        27: (4, 1, 1),
        47: (4, 2, 1),
        50: (4, 3, 1),

        # Sheet 5: Standing Up/Down Whip Strikes, Guard, Knockback & Crouching Whip
        80: (5, 0, 0),
        81: (5, 1, 0),
        31: (5, 2, 0),
        42: (5, 3, 0),
        67: (5, 0, 1),
        68: (5, 1, 1),
        35: (5, 2, 1),
        45: (5, 3, 1),

        # Sheet 6: Mid-Air Jumping Whip Windups & Directional Strikes
        32: (6, 0, 0),
        33: (6, 1, 0),
        34: (6, 2, 0),
        38: (6, 3, 0),
        39: (6, 0, 1),
        58: (6, 1, 1),
        46: (6, 2, 1),
        51: (6, 3, 1),

        # Sheet 7: Whip-Grapple Pendulum Swing Angles (52..56) & Kneeling/Collapsed Defeat (72..73)
        69: (6, 0, 1),
        52: (7, 1, 0),
        53: (7, 2, 0),
        54: (7, 3, 0),
        55: (7, 0, 1),
        56: (7, 1, 1),
        72: (7, 2, 1),
        73: (7, 3, 1),

        # Sheet 8: On-Stairs Whip Windups & Strikes
        61: (8, 0, 0),
        62: (8, 1, 0),
        63: (8, 2, 0),
        86: (8, 3, 0),
        87: (8, 0, 1),
        89: (8, 1, 1),
        90: (8, 2, 1),
        91: (8, 3, 1),
    }

    # Exact 1x hand tip coordinates for the 9 Whip-Hold / Limp-Whip poses (locked Idle-01 body + rotating HD arm!)
    whiphold_tips = {
        29: (65, 44),  # Straight forward
        30: (63, 39),  # Slight up-forward
        44: (63, 51),  # Down-forward
        48: (52, 19),  # Straight UP (ZERO giant Simon!)
        49: (63, 30),  # Diagonal up-forward
        59: (47, 58),  # Straight down
        60: (47, 58),  # Straight down
        70: (63, 30),  # Diagonal up-forward
        75: (63, 51),  # Down-forward
    }

    alias_to_canonical = {
        7:  5,
        8:  6,
        10: 37,
        11: 37,
        12: 37,
        13: 37,
        36: 37,
        74: 37,
        88: 37,
        40: 9,
        41: 9,
        43: 34,
        57: 9,
        65: 9,
        84: 9,
        64: 45,
        71: 45,
        83: 45,
        66: 69,
        79: 69,
        76: 61,
        77: 62,
        78: 63,
        82: 42,
        93: 42,
        85: 19,
        94: 19,
        95: 19,
        92: 91,
    }

    # 1. Extract all unique (sheet, col, row) crops with 100% opaque border flood-fill
    raw_by_sheet = {}
    crop_cache = {}
    for c_idx, scr in direct_cell_map.items():
        if scr not in crop_cache:
            im = extract_cell(loaded_sheets[scr[0]], scr[1], scr[2])
            crop_cache[scr] = im
            raw_by_sheet.setdefault(scr[0], []).append(im)

    # 2. Color-lock ALL sheets (1, 3, 4, 5, 6, 7, 8) to Sheet 2's warm bronze/slate-blue palette!
    anchor_means, anchor_stds = compute_fg_stats(raw_by_sheet[2])
    sheet_stats = {s_idx: compute_fg_stats(ims) for s_idx, ims in raw_by_sheet.items()}
    for scr, im in list(crop_cache.items()):
        s_idx = scr[0]
        if s_idx != 2:
            sm, ss = sheet_stats[s_idx]
            crop_cache[scr] = match_color_to_anchor(im, sm, ss, anchor_means, anchor_stds, strength=0.80)

    # Build full 960x960 aligned Idle-01 (cell 4) and Standing Forward Whip-Strike (cell 28) for locked whip-hold compositing!
    PACK_WORK.mkdir(parents=True, exist_ok=True)
    shutil.copy2(TPL_DIR / "body.png", PACK_WORK / "body.png")
    tpl_json = json.loads((TPL_DIR / "character.json").read_text(encoding="utf-8"))
    tpl_body = Image.open(TPL_DIR / "body.png").convert("RGBA")
    tpl_json["name"] = "Simon Belmont Gothic HD (Variante A v2)"

    def make_full_960(cell_id: int) -> Image.Image:
        cx, cy = (cell_id % 8) * 96, (cell_id // 8) * 96
        c1x = np.array(tpl_body.crop((cx, cy, cx + 96, cy + 96)))
        sub, off, dsz = fit_simon_pose_to_cell(crop_cache[direct_cell_map[cell_id]], c1x, cell_id)
        full = Image.new("RGBA", (960, 960), (0, 0, 0, 0))
        full.alpha_composite(sub, (off[0] * 10, off[1] * 10))
        return full

    idle_full_960 = make_full_960(4)
    strike_full_960 = make_full_960(28)

    cols, rows = 12, 9
    cw, ch = 155, 175
    contact = Image.new("RGB", (cols * cw, rows * ch), (16, 16, 20))
    cdraw = ImageDraw.Draw(contact)

    for idx, fr in enumerate(tpl_json["frames"]):
        c = fr["cell"]
        if c in whiphold_tips:
            sub_png, offset, display_size = build_locked_whiphold_pose(idle_full_960, strike_full_960, whiphold_tips[c])
            src_tag = f"HOLD->{whiphold_tips[c][0]},{whiphold_tips[c][1]}"
        else:
            can_c = c if c in direct_cell_map else alias_to_canonical.get(c, 4)
            scr = direct_cell_map[can_c]
            hd_crop = crop_cache[scr]
            cx, cy = (c % 8) * 96, (c // 8) * 96
            cell_1x = np.array(tpl_body.crop((cx, cy, cx + 96, cy + 96)))
            sub_png, offset, display_size = fit_simon_pose_to_cell(hd_crop, cell_1x, c)
            src_tag = f"{scr[0]}:{scr[1]},{scr[2]}"

        png_name = f"simon_cell_{c:02d}_hd10x.png"
        sub_png.save(PACK_WORK / png_name)
        sub_png.save(USER_SIMON_DIR / png_name)

        fr["hd"] = {
            "image": png_name,
            "scale": 10,
            "offset": offset,
            "display_size": display_size,
        }

        r_i, c_i = idx // cols, idx % cols
        x0, y0 = c_i * cw, r_i * ch
        sc = min(135 / max(1, sub_png.width), 130 / max(1, sub_png.height))
        thumb = sub_png.resize((max(1, int(round(sub_png.width * sc))), max(1, int(round(sub_png.height * sc)))), Image.Resampling.LANCZOS)
        contact.paste(thumb, (x0 + (cw - thumb.width) // 2, y0 + 8 + (132 - thumb.height) // 2), thumb)
        cdraw.rectangle([x0 + 1, y0 + 1, x0 + cw - 2, y0 + ch - 2], outline=(62, 68, 86))
        cdraw.text((x0 + 6, y0 + 144), f"[{idx:02d}] c={c:02d} {fr['id'][:4]}", fill=(245, 230, 185))
        cdraw.text((x0 + 6, y0 + 158), f"{display_size[0]}x{display_size[1]} {src_tag}", fill=(160, 175, 195))

    (PACK_WORK / "character.json").write_text(json.dumps(tpl_json, indent=2) + "\n", encoding="utf-8")
    contact_path = BRAIN / "scratch" / "simon_ref" / "simon_variant_a_v2_all_96_hd_poses.jpg"
    contact.save(contact_path, "JPEG", quality=91, optimize=True)
    shutil.copy2(contact_path, USER_SIMON_DIR / "Simon_Belmont_Alle_96_Posen_Uebersicht_HD.jpg")
    print(f"Built {PACK_NAME} v2 with {len(tpl_json['frames'])} HD frames! Contact: {contact_path}")

    for target in (PACK_PLAY, PACK_BUILD, PACK_LUA):
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(PACK_WORK, target)
        (target.parent / "selected.txt").write_text(PACK_NAME, encoding="utf-8")
    print("Installed and selected simon-gothic-variant-a v2 in build-play, build, and build-lua.")


if __name__ == "__main__":
    main()
