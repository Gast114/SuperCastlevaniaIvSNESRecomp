#!/usr/bin/env python3
"""Build true 8x smooth anti-aliased dark-gothic oil-painted HD Whip artwork (Braided Leather Whip,
Interlocking Forged-Steel Chain Links, 3D Spiked Morning Star Flail Ball, and Seamless Antique-Brass Whip Handles)
for all 34 Bank 4 whip metasprite poses (0x8019..0x80be) with ZERO 1x pixel staircase clipping."""

import json
import math
import shutil
from pathlib import Path
from PIL import Image, ImageOps
import numpy as np

ROOT = Path(r"D:\Super Castlevania IV Recomp\SuperCastlevaniaIvSNESRecomp")
BRAIN = Path(r"C:\Users\Gaming\.gemini\antigravity\brain\0e3d1566-2f3c-4183-be49-fad33ce3d4a9")
WHIP_REF = BRAIN / "scratch" / "whip_ref"
USER_SIMON_DIR = Path(r"D:\Super Castlevania IV Recomp\Assets (ausgeschnitten)\Simon Belmont\HD_Variante_A")
USER_WEAPONS_DIR = Path(r"D:\Super Castlevania IV Recomp\Assets (ausgeschnitten)\Items\02_Waffen")

PACK_NAME = "hd-stage01"
PACK_WORK = ROOT / "artwork-local" / "enemy-packs-hd" / PACK_NAME
PACK_PLAY = ROOT / "build-play" / "game" / "enemy_packs" / PACK_NAME
PACK_BUILD = ROOT / "build" / "enemy_packs" / PACK_NAME
PACK_LUA = ROOT / "build-lua" / "enemy_packs" / PACK_NAME

rom = (ROOT / "Super Castlevania IV (USA).sfc").read_bytes()
vram_leather = np.load(WHIP_REF / "vram_leather.npy")
vram_chain = np.load(WHIP_REF / "vram_chain.npy")


def decode_tile_indices(vram_u16: np.ndarray, tid: int) -> np.ndarray:
    addr = (0x6000 + tid * 16) & 0x7fff
    idx = np.zeros((8, 8), dtype=np.uint8)
    for y in range(8):
        w0 = int(vram_u16[addr + y])
        w1 = int(vram_u16[(addr + y + 8) & 0x7fff])
        for x in range(8):
            b = 7 - x
            v = ((w0 >> b) & 1) | (((w0 >> (b + 8)) & 1) << 1) | (((w1 >> b) & 1) << 2) | (((w1 >> (b + 8)) & 1) << 3)
            idx[y, x] = v
    return idx


def compute_whip_pose_hash(vram_u16: np.ndarray, pose_addr: int) -> tuple:
    off = 4 * 0x8000 + (pose_addr & 0x7fff)
    cnt = rom[off]
    assert cnt == 1
    dx = int.from_bytes(rom[off + 1:off + 2], "little", signed=True)
    dy = int.from_bytes(rom[off + 2:off + 3], "little", signed=True)
    tile = int.from_bytes(rom[off + 3:off + 5], "little") | 0x2000
    tid = tile & 0xff
    hf = (tile & 0x4000) != 0
    vf = (tile & 0x8000) != 0

    t_idx = decode_tile_indices(vram_u16, tid)
    indices = np.zeros((96, 96), dtype=np.uint8)
    for py in range(8):
        for px in range(8):
            tx = (7 - px) if hf else px
            ty = (7 - py) if vf else py
            v = int(t_idx[ty, tx])
            if v:
                indices[dy + py + 48, dx + px + 48] = v

    h = 14695981039346656037
    prime = 1099511628211
    mask64 = (1 << 64) - 1
    for v in indices.ravel().tolist():
        h = ((h ^ int(v)) * prime) & mask64
    return f"{h:016x}", dx, dy, tid, hf, vf


def dist_to_polyline(xx: np.ndarray, yy: np.ndarray, pts: list) -> tuple:
    """Compute minimum distance, signed normal offset, and arc length along a polyline of (x, y) points in 0..64 coords."""
    min_d = np.full_like(xx, 1e6)
    best_n = np.zeros_like(xx)
    best_s = np.zeros_like(xx)
    accum_s = 0.0
    for i in range(len(pts) - 1):
        x0, y0 = pts[i]
        x1, y1 = pts[i + 1]
        vx, vy = x1 - x0, y1 - y0
        seg_len = max(1e-5, math.hypot(vx, vy))
        ux, uy = vx / seg_len, vy / seg_len
        nx, ny = -uy, ux  # normal pointing 'up/left' for top-lit shading
        if ny > 0:
            nx, ny = -nx, -ny
        px, py = xx - x0, yy - y0
        t = np.clip((px * ux + py * uy) / seg_len, 0.0, 1.0)
        cx, cy = x0 + t * vx, y0 + t * vy
        d = np.hypot(xx - cx, yy - cy)
        n_off = (xx - cx) * nx + (yy - cy) * ny
        s_val = accum_s + t * seg_len
        better = d < min_d
        min_d = np.where(better, d, min_d)
        best_n = np.where(better, n_off, best_n)
        best_s = np.where(better, s_val, best_s)
        accum_s += seg_len
    return min_d, best_n, best_s, accum_s


def render_smooth_leather_tile(tid: int) -> Image.Image:
    """Render a smooth 64x64 (8x) braided dark-gothic leather whip segment with zero 1x staircase blocks."""
    # Curves in 64x64 space matching the exact 1x entry/exit coordinates
    curves = {
        0x21: ([(0.0, 32.0), (64.0, 32.0)], 8.2, False),
        0x22: ([(32.0, 0.0), (32.0, 64.0)], 8.2, False),
        0x23: ([(-2.0, 56.0), (32.0, 46.0), (66.0, 36.0)], 8.2, False),
        0x30: ([(2.0, 62.0), (46.0, 18.0)], 8.2, False),
        0x31: ([(6.0, 62.0), (16.0, 32.0), (26.0, 0.0)], 8.2, False),
        0x20: ([(0.0, 32.0), (36.0, 30.0), (58.0, 14.0)], 8.2, True),
        0x32: ([(6.0, 62.0), (28.0, 34.0), (34.0, 6.0)], 8.2, True),
        0x33: ([(32.0, 62.0), (30.0, 28.0), (14.0, 6.0)], 8.2, True),
        0x9c: ([(4.0, 4.0), (26.0, 30.0), (54.0, 36.0)], 8.2, True),
    }
    pts, radius, taper_end = curves[tid]
    yy, xx = np.mgrid[0:64, 0:64].astype(np.float32)
    d, n_off, s_val, total_s = dist_to_polyline(xx, yy, pts)

    if taper_end:
        rad = radius * np.clip(1.05 - 0.45 * (s_val / max(1.0, total_s)), 0.45, 1.0)
    else:
        rad = np.full_like(d, radius)

    # Smooth anti-aliased alpha along the curved leather cylinder
    alpha = np.clip((rad - d) / 1.6, 0.0, 1.0)

    # 3D cylindrical normal + braided diagonal plaiting relief
    rel_n = np.clip(n_off / np.maximum(1.0, rad), -1.0, 1.0)
    cyl = np.sqrt(np.clip(1.0 - (d / np.maximum(1.0, rad)) ** 2, 0.0, 1.0))
    top_light = np.clip(0.55 - 0.45 * rel_n, 0.0, 1.0)

    # Diagonal braided leather plaiting along arc length s_val and cross-axis n_off
    b1 = 0.5 + 0.5 * np.sin((s_val * 0.72 + n_off * 0.85))
    b2 = 0.5 + 0.5 * np.sin((s_val * 0.72 - n_off * 0.85))
    braid = 0.65 * b1 + 0.35 * b2

    shade = np.clip(cyl * (0.62 * top_light + 0.28 * braid + 0.12), 0.0, 1.0)

    stops = np.array([0.0, 0.30, 0.60, 0.85, 1.0], dtype=np.float32)
    r_ramp = np.array([26,  74, 138, 196, 236], dtype=np.float32)
    g_ramp = np.array([10,  29,  64, 108, 162], dtype=np.float32)
    b_ramp = np.array([ 7,  16,  28,  44,  86], dtype=np.float32)

    rgba = np.zeros((64, 64, 4), dtype=np.uint8)
    rgba[:, :, 0] = np.clip(np.interp(shade, stops, r_ramp), 0, 255).astype(np.uint8)
    rgba[:, :, 1] = np.clip(np.interp(shade, stops, g_ramp), 0, 255).astype(np.uint8)
    rgba[:, :, 2] = np.clip(np.interp(shade, stops, b_ramp), 0, 255).astype(np.uint8)
    rgba[:, :, 3] = np.clip(alpha * 255.0, 0, 255).astype(np.uint8)
    return Image.fromarray(rgba, "RGBA")


def draw_oval_chain_link(rgba: np.ndarray, cx: float, cy: float, angle_deg: float, rx: float = 14.5, ry: float = 8.2, wire_r: float = 3.6):
    """Composite a 3D forged-steel oval chain link at (cx, cy) rotated by angle_deg onto a 64x64 float buffer."""
    yy, xx = np.mgrid[0:64, 0:64].astype(np.float32)
    th = math.radians(angle_deg)
    c, s = math.cos(th), math.sin(th)
    dx, dy = xx - cx, yy - cy
    lx = dx * c + dy * s
    ly = -dx * s + dy * c

    # Distance to oval stadium ring centerline (major half-segment a = rx - ry, radius r = ry)
    a = max(0.0, rx - ry)
    qx = np.clip(lx, -a, a)
    ring_d = np.hypot(lx - qx, ly) - (ry - wire_r)
    wire_dist = np.abs(ring_d)

    alpha = np.clip((wire_r - wire_dist) / 1.3, 0.0, 1.0)
    if not (alpha > 0).any():
        return

    # 3D torus surface normal for top-left lighting
    nx = (lx - qx) / np.maximum(1e-4, np.hypot(lx - qx, ly))
    ny = ly / np.maximum(1e-4, np.hypot(lx - qx, ly))
    # Rotate normal back to screen space
    snx = nx * c - ny * s
    sny = nx * s + ny * c
    radial_sign = np.sign(ring_d)
    torus_z = np.sqrt(np.clip(1.0 - (wire_dist / wire_r) ** 2, 0.0, 1.0))
    light = np.clip(0.52 * torus_z - 0.35 * radial_sign * (0.6 * snx + 0.8 * sny) + 0.32, 0.0, 1.0)
    spec = np.power(np.clip(light, 0.0, 1.0), 4.0) * 0.35
    shade = np.clip(light + spec, 0.0, 1.0)

    stops = np.array([0.0, 0.32, 0.64, 0.88, 1.0], dtype=np.float32)
    r_ramp = np.array([14,  42,  88, 156, 232], dtype=np.float32)
    g_ramp = np.array([19,  56, 114, 182, 244], dtype=np.float32)
    b_ramp = np.array([25,  68, 132, 198, 252], dtype=np.float32)

    lr = np.interp(shade, stops, r_ramp)
    lg = np.interp(shade, stops, g_ramp)
    lb = np.interp(shade, stops, b_ramp)

    # Alpha composite over existing buffer
    src_a = alpha
    dst_a = rgba[:, :, 3]
    out_a = src_a + dst_a * (1.0 - src_a)
    safe_a = np.maximum(1e-5, out_a)
    rgba[:, :, 0] = (lr * src_a + rgba[:, :, 0] * dst_a * (1.0 - src_a)) / safe_a
    rgba[:, :, 1] = (lg * src_a + rgba[:, :, 1] * dst_a * (1.0 - src_a)) / safe_a
    rgba[:, :, 2] = (lb * src_a + rgba[:, :, 2] * dst_a * (1.0 - src_a)) / safe_a
    rgba[:, :, 3] = out_a


def render_smooth_chain_tile(tid: int) -> Image.Image:
    """Render smooth 64x64 (8x) interlocking forged-steel chain links or 3D spiked Morning Star ball."""
    rgba = np.zeros((64, 64, 4), dtype=np.float32)

    if tid in (0x20, 0x32, 0x33, 0x9c):
        # 3D Spiked Morning Star Flail Ball centered at (32, 32)
        yy, xx = np.mgrid[0:64, 0:64].astype(np.float32)
        cx, cy = 32.0, 32.0
        dx, dy = xx - cx, yy - cy
        r = np.hypot(dx, dy)

        # 8 sharp conical steel spikes at 0, 45, 90, 135, 180, 225, 270, 315 degrees
        for deg in (45, 135, 225, 315, 0, 90, 180, 270):
            th = math.radians(deg)
            ux, uy = math.cos(th), math.sin(th)
            nx, ny = -uy, ux
            proj = dx * ux + dy * uy
            perp = dx * nx + dy * ny
            spike_len = 25.5 if (deg % 90 == 0) else 22.0
            base_w = 5.4 if (deg % 90 == 0) else 4.4
            t = np.clip((proj - 7.0) / (spike_len - 7.0), 0.0, 1.0)
            cone_r = base_w * (1.0 - t)
            in_cone = (proj >= 7.0) & (proj <= spike_len)
            sp_alpha = np.where(in_cone, np.clip((cone_r - np.abs(perp)) / 1.1, 0.0, 1.0), 0.0)
            sp_shade = np.clip(0.58 - 0.38 * (perp / np.maximum(0.8, cone_r)) + 0.25 * t, 0.0, 1.0)

            stops = np.array([0.0, 0.35, 0.68, 0.90, 1.0], dtype=np.float32)
            sr = np.interp(sp_shade, stops, [18, 52, 108, 176, 245])
            sg = np.interp(sp_shade, stops, [24, 68, 132, 198, 250])
            sb = np.interp(sp_shade, stops, [30, 82, 150, 214, 255])

            da = rgba[:, :, 3]
            oa = sp_alpha + da * (1.0 - sp_alpha)
            sa = np.maximum(1e-5, oa)
            rgba[:, :, 0] = (sr * sp_alpha + rgba[:, :, 0] * da * (1.0 - sp_alpha)) / sa
            rgba[:, :, 1] = (sg * sp_alpha + rgba[:, :, 1] * da * (1.0 - sp_alpha)) / sa
            rgba[:, :, 2] = (sb * sp_alpha + rgba[:, :, 2] * da * (1.0 - sp_alpha)) / sa
            rgba[:, :, 3] = oa

        # Central forged-iron flail sphere (radius 12.5 px)
        ball_r = 12.5
        b_alpha = np.clip((ball_r - r) / 1.2, 0.0, 1.0)
        bx = (dx + 4.0) / ball_r
        by = (dy + 4.0) / ball_r
        b_light = np.clip(1.0 - 0.45 * (bx * bx + by * by), 0.08, 1.0)
        b_spec = np.power(b_light, 5.0) * 0.40
        b_shade = np.clip(b_light * 0.78 + b_spec, 0.0, 1.0)

        stops = np.array([0.0, 0.35, 0.65, 0.88, 1.0], dtype=np.float32)
        br = np.interp(b_shade, stops, [14, 40,  86, 152, 235])
        bg = np.interp(b_shade, stops, [18, 54, 110, 178, 245])
        bb = np.interp(b_shade, stops, [24, 66, 128, 196, 255])

        da = rgba[:, :, 3]
        oa = b_alpha + da * (1.0 - b_alpha)
        sa = np.maximum(1e-5, oa)
        rgba[:, :, 0] = (br * b_alpha + rgba[:, :, 0] * da * (1.0 - b_alpha)) / sa
        rgba[:, :, 1] = (bg * b_alpha + rgba[:, :, 1] * da * (1.0 - b_alpha)) / sa
        rgba[:, :, 2] = (bb * b_alpha + rgba[:, :, 2] * da * (1.0 - b_alpha)) / sa
        rgba[:, :, 3] = oa

    elif tid == 0x21:
        # Horizontal chain segment: 2 full oval links + half connector links at edges
        draw_oval_chain_link(rgba, 16.0, 33.0, 0.0, rx=15.0, ry=8.4, wire_r=3.6)
        draw_oval_chain_link(rgba, 48.0, 33.0, 0.0, rx=15.0, ry=8.4, wire_r=3.6)
        draw_oval_chain_link(rgba, 32.0, 33.0, 0.0, rx=11.0, ry=5.2, wire_r=3.2)
    elif tid == 0x22:
        # Vertical chain segment
        draw_oval_chain_link(rgba, 33.0, 16.0, 90.0, rx=15.0, ry=8.4, wire_r=3.6)
        draw_oval_chain_link(rgba, 33.0, 48.0, 90.0, rx=15.0, ry=8.4, wire_r=3.6)
        draw_oval_chain_link(rgba, 33.0, 32.0, 90.0, rx=11.0, ry=5.2, wire_r=3.2)
    elif tid == 0x23:
        # Shallow diagonal (~ -18 deg from bottom-left to mid-right)
        draw_oval_chain_link(rgba, 16.0, 51.0, -18.0, rx=15.0, ry=8.4, wire_r=3.6)
        draw_oval_chain_link(rgba, 48.0, 41.0, -18.0, rx=15.0, ry=8.4, wire_r=3.6)
        draw_oval_chain_link(rgba, 32.0, 46.0, -18.0, rx=11.0, ry=5.2, wire_r=3.2)
    elif tid == 0x30:
        # 45-degree diagonal segment
        draw_oval_chain_link(rgba, 12.0, 52.0, -45.0, rx=14.5, ry=8.2, wire_r=3.5)
        draw_oval_chain_link(rgba, 36.0, 28.0, -45.0, rx=14.5, ry=8.2, wire_r=3.5)
        draw_oval_chain_link(rgba, 24.0, 40.0, -45.0, rx=10.5, ry=5.0, wire_r=3.1)
    elif tid == 0x31:
        # Steep diagonal (~ -72 deg)
        draw_oval_chain_link(rgba, 12.0, 48.0, -72.0, rx=15.0, ry=8.4, wire_r=3.6)
        draw_oval_chain_link(rgba, 22.0, 16.0, -72.0, rx=15.0, ry=8.4, wire_r=3.6)
        draw_oval_chain_link(rgba, 17.0, 32.0, -72.0, rx=11.0, ry=5.2, wire_r=3.2)

    out = np.zeros((64, 64, 4), dtype=np.uint8)
    out[:, :, :3] = np.clip(rgba[:, :, :3], 0, 255).astype(np.uint8)
    out[:, :, 3] = np.clip(rgba[:, :, 3] * 255.0, 0, 255).astype(np.uint8)
    return Image.fromarray(out, "RGBA")


def render_smooth_handle_tile(tid: int) -> Image.Image:
    """Render a smooth 64x64 (8x) leather-wrapped antique-brass whip handle that bridges seamlessly into the first whip link."""
    specs = {
        0x9a: [(0.0, 32.0), (50.0, 32.0)],   # Horizontal handle extending to x=50 so zero gap at x+48!
        0x8c: [(32.0, 20.0), (32.0, 64.0)],  # Vertical handle
        0x8e: [(2.0, 60.0), (34.0, 28.0)],   # 45-degree diagonal handle
    }
    pts = specs[tid]
    yy, xx = np.mgrid[0:64, 0:64].astype(np.float32)
    d, n_off, s_val, total_s = dist_to_polyline(xx, yy, pts)

    # Flared antique-brass pommel & ferrule collar at ends of handle
    t = s_val / max(1.0, total_s)
    is_collar = (t < 0.18) | (t > 0.80)
    rad = np.where(is_collar, 9.6, 8.4)
    alpha = np.clip((rad - d) / 1.4, 0.0, 1.0)

    rel_n = np.clip(n_off / np.maximum(1.0, rad), -1.0, 1.0)
    cyl = np.sqrt(np.clip(1.0 - (d / np.maximum(1.0, rad)) ** 2, 0.0, 1.0))
    top_light = np.clip(0.56 - 0.44 * rel_n, 0.0, 1.0)
    wrap = 0.5 + 0.5 * np.sin(s_val * 0.65 + n_off * 0.55)
    shade = np.clip(cyl * (0.68 * top_light + 0.22 * np.where(is_collar, 0.85, wrap) + 0.10), 0.0, 1.0)

    stops = np.array([0.0, 0.32, 0.64, 0.88, 1.0], dtype=np.float32)
    r_ramp = np.array([26,  72, 134, 188, 232], dtype=np.float32)
    g_ramp = np.array([16,  46,  92, 142, 188], dtype=np.float32)
    b_ramp = np.array([ 9,  22,  42,  68, 110], dtype=np.float32)

    rgba = np.zeros((64, 64, 4), dtype=np.uint8)
    rgba[:, :, 0] = np.clip(np.interp(shade, stops, r_ramp), 0, 255).astype(np.uint8)
    rgba[:, :, 1] = np.clip(np.interp(shade, stops, g_ramp), 0, 255).astype(np.uint8)
    rgba[:, :, 2] = np.clip(np.interp(shade, stops, b_ramp), 0, 255).astype(np.uint8)
    rgba[:, :, 3] = np.clip(alpha * 255.0, 0, 255).astype(np.uint8)
    return Image.fromarray(rgba, "RGBA")


def _extract_white_bg_cell(im: Image.Image, col: int, row: int) -> Image.Image:
    """Extract a cell from the 4x2 white-background Higgsfield Whip sheet with clean border flood-fill."""
    W, H = im.size
    cw, ch = W // 4, H // 2
    crop = im.crop((col * cw + 4, row * ch + 4, (col + 1) * cw - 4, (row + 1) * ch - 4)).convert("RGBA")
    arr = np.array(crop, dtype=np.uint8)
    h, w = arr.shape[:2]
    r, g, b = arr[:, :, 0].astype(np.int16), arr[:, :, 1].astype(np.int16), arr[:, :, 2].astype(np.int16)
    is_bg = (r > 238) & (g > 238) & (b > 238) & (np.abs(r - g) < 12) & (np.abs(g - b) < 12)
    visited = np.zeros((h, w), dtype=bool)
    from collections import deque
    q = deque()
    for x in range(w):
        if is_bg[0, x]:
            visited[0, x] = True; q.append((0, x))
        if is_bg[h - 1, x]:
            visited[h - 1, x] = True; q.append((h - 1, x))
    for y in range(h):
        if is_bg[y, 0] and not visited[y, 0]:
            visited[y, 0] = True; q.append((y, 0))
        if is_bg[y, w - 1] and not visited[y, w - 1]:
            visited[y, w - 1] = True; q.append((y, w - 1))
    while q:
        cy, cx = q.popleft()
        for ny, nx in ((cy - 1, cx), (cy + 1, cx), (cy, cx - 1), (cy, cx + 1)):
            if 0 <= ny < h and 0 <= nx < w and not visited[ny, nx] and is_bg[ny, nx]:
                visited[ny, nx] = True
                q.append((ny, nx))
    # Soft feather 1px around background border to remove white halo
    alpha = np.where(visited, 0, 255).astype(np.uint8)
    arr[:, :, 3] = alpha
    # Clean near-white fringe pixels directly touching transparent pixels
    pad = np.pad(visited, 1, mode="constant", constant_values=True)
    touch = pad[:-2, 1:-1] | pad[2:, 1:-1] | pad[1:-1, :-2] | pad[1:-1, 2:]
    fringe = (~visited) & touch & (r > 200) & (g > 200) & (b > 200)
    arr[fringe, 3] = 0
    return Image.fromarray(arr, "RGBA")


def _crop_to_alpha(im: Image.Image) -> Image.Image:
    bbox = im.getbbox()
    return im.crop(bbox) if bbox else im


def _fit_tile_64(im: Image.Image, target_w: int, target_h: int, cx: int = 32, cy: int = 32) -> Image.Image:
    res = im.resize((max(1, target_w), max(1, target_h)), Image.Resampling.LANCZOS)
    out = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    out.alpha_composite(res, (cx - res.width // 2, cy - res.height // 2))
    return out


def load_higgsfield_whip_tiles():
    """Slice real 2K Higgsfield forged-steel chain, spiked Morning Star, braided leather,
    and Gothic handle artwork from 03_Simon_Whip_Components_HD.png."""
    sheet_path = Path(r"D:\Super Castlevania IV Recomp\Assets (ausgeschnitten)\Higgsfield_Vorbereitung\04_Higgsfield_Output\03_Simon_Whip_Components_HD.png")
    if not sheet_path.is_file():
        return None
    im = Image.open(sheet_path).convert("RGBA")

    # 1) Forged dark-steel chain (horizontal cell 0,0 -> 64x22 strip)
    c_h_raw = _crop_to_alpha(_extract_white_bg_cell(im, 0, 0))
    # Crop middle repeating section so left/right edges tile seamlessly
    cw = c_h_raw.width
    c_h_mid = c_h_raw.crop((int(cw * 0.08), 0, int(cw * 0.92), c_h_raw.height))
    chain_h = _fit_tile_64(c_h_mid, 64, 22, 32, 32)
    chain_v = chain_h.rotate(90, resample=Image.Resampling.BICUBIC)
    chain_18 = _fit_tile_64(c_h_mid, 68, 22, 32, 32).rotate(18, resample=Image.Resampling.BICUBIC)
    chain_45 = _fit_tile_64(c_h_mid, 76, 22, 32, 32).rotate(45, resample=Image.Resampling.BICUBIC)
    chain_72 = _fit_tile_64(c_h_mid, 68, 22, 32, 32).rotate(72, resample=Image.Resampling.BICUBIC)

    # 2) Spiked Morning Star flail ball (cell 3,0 -> trim top-right stray chain)
    ms_cell = _extract_white_bg_cell(im, 3, 0)
    mw, mh = ms_cell.size
    ms_ball = _crop_to_alpha(ms_cell.crop((0, int(mh * 0.14), mw, mh)))
    s_ms = min(56.0 / ms_ball.width, 56.0 / ms_ball.height)
    chain_tip = _fit_tile_64(ms_ball, int(round(ms_ball.width * s_ms)), int(round(ms_ball.height * s_ms)), 32, 32)

    chain_tiles = {
        0x21: chain_h, 0x22: chain_v, 0x23: chain_18, 0x30: chain_45, 0x31: chain_72,
        0x20: chain_tip, 0x32: chain_tip, 0x33: chain_tip, 0x9c: chain_tip,
    }

    # 3) Braided dark-brown leather whip (cell 0,1 -> skip left brass collar so segment tiles seamlessly)
    l_h_raw = _crop_to_alpha(_extract_white_bg_cell(im, 0, 1))
    lw = l_h_raw.width
    l_h_mid = l_h_raw.crop((int(lw * 0.16), 0, lw, l_h_raw.height))
    leather_h = _fit_tile_64(l_h_mid, 64, 18, 32, 32)
    leather_v = leather_h.rotate(90, resample=Image.Resampling.BICUBIC)
    leather_18 = _fit_tile_64(l_h_mid, 68, 18, 32, 32).rotate(18, resample=Image.Resampling.BICUBIC)
    leather_45 = _fit_tile_64(l_h_mid, 76, 18, 32, 32).rotate(45, resample=Image.Resampling.BICUBIC)
    leather_72 = _fit_tile_64(l_h_mid, 68, 18, 32, 32).rotate(72, resample=Image.Resampling.BICUBIC)

    # Tapered leather tip (cell 2,1 -> rotate gently horizontal for 0x20)
    l_tip_raw = _crop_to_alpha(_extract_white_bg_cell(im, 2, 1))
    l_tip_h = _crop_to_alpha(l_tip_raw.rotate(-42, expand=True, resample=Image.Resampling.BICUBIC))
    s_lt = min(58.0 / l_tip_h.width, 32.0 / l_tip_h.height)
    leather_tip_h = _fit_tile_64(l_tip_h, int(round(l_tip_h.width * s_lt)), int(round(l_tip_h.height * s_lt)), 30, 30)
    leather_tip_d = leather_tip_h.rotate(45, resample=Image.Resampling.BICUBIC)
    leather_tip_v = leather_tip_h.rotate(90, resample=Image.Resampling.BICUBIC)

    leather_tiles = {
        0x21: leather_h, 0x22: leather_v, 0x23: leather_18, 0x30: leather_45, 0x31: leather_72,
        0x20: leather_tip_h, 0x32: leather_tip_d, 0x33: leather_tip_v, 0x9c: leather_tip_h.rotate(-35, resample=Image.Resampling.BICUBIC),
    }

    # 4) Ornate Gothic leather-wrapped handle (cell 3,1 -> diagonal ~45 deg; rotate to 0, 90, 45)
    h_raw = _crop_to_alpha(_extract_white_bg_cell(im, 3, 1))
    h_horiz = _crop_to_alpha(h_raw.rotate(-45, expand=True, resample=Image.Resampling.BICUBIC))
    # Flip horizontally so pommel is on left (Simon's hand) and guard collar connects right into whip
    h_horiz = ImageOps.mirror(h_horiz)
    sh = min(56.0 / h_horiz.width, 28.0 / h_horiz.height)
    handle_h = _fit_tile_64(h_horiz, int(round(h_horiz.width * sh)), int(round(h_horiz.height * sh)), 28, 32)
    handle_v = handle_h.rotate(90, resample=Image.Resampling.BICUBIC)
    handle_d = handle_h.rotate(45, resample=Image.Resampling.BICUBIC)
    handle_tiles = {0x9a: handle_h, 0x8c: handle_v, 0x8e: handle_d}

    print(f"[WHIP] Loaded real 2K Higgsfield whip components from {sheet_path.name}!")
    return leather_tiles, chain_tiles, handle_tiles


def main():
    whip_tids = [0x20, 0x21, 0x22, 0x23, 0x30, 0x31, 0x32, 0x33, 0x9c]
    handle_tids = [0x8c, 0x8e, 0x9a]

    hf_tiles = load_higgsfield_whip_tiles()
    if hf_tiles is not None:
        leather_tiles_64, chain_tiles_64, handle_tiles_64 = hf_tiles
    else:
        leather_tiles_64 = {tid: render_smooth_leather_tile(tid) for tid in whip_tids}
        chain_tiles_64   = {tid: render_smooth_chain_tile(tid)   for tid in whip_tids}
        handle_tiles_64  = {tid: render_smooth_handle_tile(tid)  for tid in handle_tids}

    # Save full assembled horizontal Leather Whip and Chain Morning Star Whip
    full_leather_8x = Image.new("RGBA", (6 * 64, 64), (0, 0, 0, 0))
    full_leather_8x.alpha_composite(handle_tiles_64[0x9a], (0, 0))
    for k in range(4):
        full_leather_8x.alpha_composite(leather_tiles_64[0x21], (48 + k * 64, 0))
    full_leather_8x.alpha_composite(leather_tiles_64[0x20], (48 + 4 * 64, 0))
    full_leather_8x.save(USER_SIMON_DIR / "Peitsche_Leder_Komplett_HD_8x.png")
    full_leather_8x.save(USER_WEAPONS_DIR / "Waffe_Lederpeitsche_Angriff_HD_8x.png")

    full_chain_8x = Image.new("RGBA", (8 * 64, 64), (0, 0, 0, 0))
    full_chain_8x.alpha_composite(handle_tiles_64[0x9a], (0, 0))
    for k in range(6):
        full_chain_8x.alpha_composite(chain_tiles_64[0x21], (48 + k * 64, 0))
    full_chain_8x.alpha_composite(chain_tiles_64[0x20], (48 + 6 * 64, 0))
    full_chain_8x.save(USER_SIMON_DIR / "Peitsche_Kette_Morgenstern_Komplett_HD_8x.png")
    full_chain_8x.save(USER_WEAPONS_DIR / "Waffe_Kettenpeitsche_Morgenstern_Angriff_HD_8x.png")

    whip_poses = list(range(0x8019, 0x80c3, 5))
    manifest_path = PACK_WORK / "enemies.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    base_frames = [f for f in manifest["frames"] if f["actor_type"] != 0x0e]
    seen_ids = {f["id"] for f in base_frames}
    new_frames = []

    for pa in whip_poses:
        if pa >= 0x809b:
            h_str, dx, dy, tid, hf, vf = compute_whip_pose_hash(vram_leather, pa)
            tile_im = handle_tiles_64[tid]
            if hf:
                tile_im = ImageOps.mirror(tile_im)
            if vf:
                tile_im = ImageOps.flip(tile_im)
            canvas_8x = Image.new("RGBA", (768, 768), (0, 0, 0, 0))
            canvas_8x.alpha_composite(tile_im, ((dx + 48) * 8, (dy + 48) * 8))
            fname = f"Peitsche_Griff_{pa:04x}_HD_8x.png"
            canvas_8x.save(PACK_WORK / fname)
            canvas_8x.save(USER_SIMON_DIR / fname)
            fid = f"gegner-000e_pose-{pa:04x}_{h_str}"
            if fid not in seen_ids:
                seen_ids.add(fid)
                new_frames.append({
                    "id": fid,
                    "actor_type": 0x0e,
                    "pose": pa,
                    "image": fname,
                    "display_size": [96, 96],
                    "anchor": [48, 48],
                })
        else:
            # 1) Leather Whip
            h_l, dx, dy, tid, hf, vf = compute_whip_pose_hash(vram_leather, pa)
            t_l = leather_tiles_64[tid]
            if hf:
                t_l = ImageOps.mirror(t_l)
            if vf:
                t_l = ImageOps.flip(t_l)
            c_l = Image.new("RGBA", (768, 768), (0, 0, 0, 0))
            c_l.alpha_composite(t_l, ((dx + 48) * 8, (dy + 48) * 8))
            fname_l = f"Peitsche_Leder_{pa:04x}_HD_8x.png"
            c_l.save(PACK_WORK / fname_l)
            c_l.save(USER_SIMON_DIR / fname_l)
            fid_l = f"gegner-000e_pose-{pa:04x}_{h_l}"
            if fid_l not in seen_ids:
                seen_ids.add(fid_l)
                new_frames.append({
                    "id": fid_l,
                    "actor_type": 0x0e,
                    "pose": pa,
                    "image": fname_l,
                    "display_size": [96, 96],
                    "anchor": [48, 48],
                })

            # 2) Chain / Morning Star Whip
            h_c, dx, dy, tid, hf, vf = compute_whip_pose_hash(vram_chain, pa)
            t_c = chain_tiles_64[tid]
            if hf:
                t_c = ImageOps.mirror(t_c)
            if vf:
                t_c = ImageOps.flip(t_c)
            c_c = Image.new("RGBA", (768, 768), (0, 0, 0, 0))
            c_c.alpha_composite(t_c, ((dx + 48) * 8, (dy + 48) * 8))
            fname_c = f"Peitsche_Kette_{pa:04x}_HD_8x.png"
            c_c.save(PACK_WORK / fname_c)
            c_c.save(USER_SIMON_DIR / fname_c)
            fid_c = f"gegner-000e_pose-{pa:04x}_{h_c}"
            if fid_c not in seen_ids:
                seen_ids.add(fid_c)
                new_frames.append({
                    "id": fid_c,
                    "actor_type": 0x0e,
                    "pose": pa,
                    "image": fname_c,
                    "display_size": [96, 96],
                    "anchor": [48, 48],
                })

    manifest["frames"] = base_frames + new_frames
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Updated {manifest_path}: {len(base_frames)} base frames + {len(new_frames)} smooth 8x Whip frames = {len(manifest['frames'])} total frames.")

    for target in (PACK_PLAY, PACK_BUILD, PACK_LUA):
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(PACK_WORK, target)
        (target.parent / "selected.txt").write_text(PACK_NAME, encoding="utf-8")
    print("Synced smooth 8x hd-stage01 to build-play, build, and build-lua.")


if __name__ == "__main__":
    main()
