#!/usr/bin/env python3
"""Slice & build the complete Cloud-AI HD Rowdain Boss (Phase 1 + Transition + Phase 2 + Death Fragments)
and merge with the Stage 01 Enemy Pack (`hd-stage01`)."""

import json
import shutil
from collections import deque
from pathlib import Path
from PIL import Image, ImageDraw
import numpy as np

ROOT = Path(r"D:\Super Castlevania IV Recomp\SuperCastlevaniaIvSNESRecomp")
BRAIN = Path(r"C:\Users\Gaming\.gemini\antigravity\brain\0e3d1566-2f3c-4183-be49-fad33ce3d4a9")
SCAN_DIR = BRAIN / "scratch" / "boss80_rom_scan"

SHEET_1A = BRAIN / "rowdain_phase1_mounted_hd_2x2_final_1795354543590.jpg"
SHEET_1B = BRAIN / "rowdain_mounted_a955_a9ae_hd_1795354639947.jpg"
SHEET_2  = BRAIN / "rowdain_phase2_knight_part1_hd_blackbg_1795354504011.jpg"
SHEET_3  = BRAIN / "boss80_rowdain_phase2_part2_hd_1795354492311.jpg"
SHEET_4  = BRAIN / "boss_rowdain_sheet4_hd_v2_1795354517659.jpg"

USER_GEGNER = Path(r"D:\Super Castlevania IV Recomp\Assets (ausgeschnitten)\Gegner")
USER_OUT = USER_GEGNER / "HD_4x_8x"
USER_OUT.mkdir(parents=True, exist_ok=True)

PACK_NAME = "hd-stage01"
PACK_WORK = ROOT / "artwork-local" / "enemy-packs-hd" / PACK_NAME
PACK_PLAY = ROOT / "build-play" / "game" / "enemy_packs" / PACK_NAME
PACK_BUILD = ROOT / "build" / "enemy_packs" / PACK_NAME
PACK_LUA = ROOT / "build-lua" / "enemy_packs" / PACK_NAME


def remove_black_bg(im: Image.Image, thresh: int = 15, soft: int = 34, keep_interior_holes: bool = False) -> Image.Image:
    """Border flood-fill matting so interior dark bone shadows / eye sockets stay intact."""
    rgba = np.array(im.convert("RGBA"), dtype=np.float32)
    r, g, b = rgba[:, :, 0], rgba[:, :, 1], rgba[:, :, 2]
    lum = np.maximum(np.maximum(r, g), b)
    h, w = lum.shape

    bg_cand = lum < soft
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

    if keep_interior_holes:
        ext_ramp = np.clip((lum - thresh) / max(1.0, float(soft - thresh)), 0.0, 1.0)
        alpha = np.where(ext, ext_ramp, 1.0)
    else:
        alpha = np.clip((lum - thresh) / max(1.0, float(soft - thresh)), 0.0, 1.0)
        alpha = np.where(ext, alpha, np.maximum(alpha, np.where(lum >= thresh - 3, 1.0, 0.0)))

    alpha_2 = alpha ** 0.85
    for c in range(3):
        rgba[:, :, c] = np.clip(rgba[:, :, c] * alpha_2, 0, 255)
    rgba[:, :, 3] = np.clip(alpha * 255.0, 0, 255)

    if keep_interior_holes:
        # Ensure enclosed interior pixels (like the dark eye socket of the horse skull) have opaque dark RGB so vertebrae behind don't show through!
        interior_dark = (~ext) & (lum < thresh)
        rgba[:, :, 0] = np.where(interior_dark, np.maximum(rgba[:, :, 0], 10.0), rgba[:, :, 0])
        rgba[:, :, 1] = np.where(interior_dark, np.maximum(rgba[:, :, 1], 8.0), rgba[:, :, 1])
        rgba[:, :, 2] = np.where(interior_dark, np.maximum(rgba[:, :, 2], 8.0), rgba[:, :, 2])
        rgba[:, :, 3] = np.where(interior_dark, 255.0, rgba[:, :, 3])

    arr_u8 = rgba.astype(np.uint8)
    mask = arr_u8[:, :, 3] > 20
    if mask.any():
        visited = np.zeros((h, w), dtype=bool)
        comps = []
        ys, xs = np.where(mask)
        for y0, x0 in zip(ys, xs):
            if visited[y0, x0]:
                continue
            comp = []
            cq = deque([(y0, x0)])
            visited[y0, x0] = True
            while cq:
                cy, cx = cq.popleft()
                comp.append((cy, cx))
                for ny in range(max(0, cy - 2), min(h, cy + 3)):
                    for nx in range(max(0, cx - 2), min(w, cx + 3)):
                        if not visited[ny, nx] and mask[ny, nx]:
                            visited[ny, nx] = True
                            cq.append((ny, nx))
            comps.append(comp)
        max_len = max(len(c) for c in comps)
        keep = np.zeros((h, w), dtype=bool)
        for c in comps:
            if len(c) >= max(16, int(max_len * 0.004)):
                for cy, cx in c:
                    keep[cy, cx] = True
        dil = keep.copy()
        for dy in range(-2, 3):
            for dx in range(-2, 3):
                if dy == 0 and dx == 0:
                    continue
                sy0, sy1 = max(0, dy), min(h, h + dy)
                sx0, sx1 = max(0, dx), min(w, w + dx)
                dil[sy0:sy1, sx0:sx1] |= keep[sy0 - dy:sy1 - dy, sx0 - dx:sx1 - dx]
        arr_u8[:, :, 3] = np.where(dil, arr_u8[:, :, 3], 0)
        for c in range(3):
            arr_u8[:, :, c] = np.where(dil, arr_u8[:, :, c], 0)

    return Image.fromarray(arr_u8, "RGBA")


def crop_tight(im: Image.Image) -> Image.Image:
    arr = np.array(im)
    ys, xs = np.where(arr[:, :, 3] > 18)
    if ys.size == 0:
        return im
    return im.crop((int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1))


def fit_to_pose(hd_crop: Image.Image, ref_1x: np.ndarray, scale: int = 8, pad_scale: float = 1.03) -> Image.Image:
    """Align HD crop to the exact center and footprint of a 1x reference canvas (96x96 or 256x256)."""
    ref_h, ref_w = ref_1x.shape[:2]
    canvas = Image.new("RGBA", (ref_w * scale, ref_h * scale), (0, 0, 0, 0))
    ys, xs = np.where(ref_1x[:, :, 3] > 0)
    if ys.size == 0:
        return canvas

    rx0, rx1 = int(xs.min()), int(xs.max()) + 1
    ry0, ry1 = int(ys.min()), int(ys.max()) + 1
    rw = (rx1 - rx0) * scale
    rh = (ry1 - ry0) * scale
    rcx = (rx0 + rx1) * 0.5 * scale
    rcy = (ry0 + ry1) * 0.5 * scale

    tight = crop_tight(hd_crop)
    tw, th = tight.size
    if tw == 0 or th == 0:
        return canvas

    s = min((rw * pad_scale) / tw, (rh * pad_scale) / th)
    nw = max(1, int(round(tw * s)))
    nh = max(1, int(round(th * s)))
    resized = tight.resize((nw, nh), Image.Resampling.LANCZOS)

    px = int(round(rcx - nw * 0.5))
    py = int(round(rcy - nh * 0.5))
    canvas.alpha_composite(resized, (px, py))
    return canvas


def extract_box(sheet: Image.Image, fx0: float, fy0: float, fx1: float, fy1: float, keep_holes: bool = False) -> Image.Image:
    w, h = sheet.size
    box = (int(round(fx0 * w)), int(round(fy0 * h)), int(round(fx1 * w)), int(round(fy1 * h)))
    cell = sheet.crop(box)
    return crop_tight(remove_black_bg(cell, keep_interior_holes=keep_holes))


def main():
    # Copy updated EXE to build-play/game so interactive testing also has the 512M pixel budget
    exe_src = ROOT / "build" / "SuperCastlevaniaIvSNESRecomp.exe"
    exe_dst = ROOT / "build-play" / "game" / "SuperCastlevaniaIvSNESRecomp.exe"
    if exe_src.exists() and exe_dst.parent.exists():
        shutil.copy2(exe_src, exe_dst)

    s1a = Image.open(SHEET_1A).convert("RGBA")
    s1b = Image.open(SHEET_1B).convert("RGBA")
    s2  = Image.open(SHEET_2).convert("RGBA")
    s3  = Image.open(SHEET_3).convert("RGBA")
    s4  = Image.open(SHEET_4).convert("RGBA")

    # Also load the cloud-AI fireball from our existing Stage 01 enemy assets
    fb1_hd = crop_tight(Image.open(USER_OUT / "Knochensaeule_Feuerball_2_HD_8x.png").convert("RGBA"))
    fb2_hd = crop_tight(Image.open(USER_OUT / "Knochensaeule_Feuerball_3_HD_8x.png").convert("RGBA"))

    # Extract all unique cloud-AI crops
    crops = {
        # Phase 1 Mounted Gallop (4 poses)
        "Galopp_01": extract_box(s1a, 0.00, 0.00, 0.50, 0.50),
        "Galopp_02": extract_box(s1a, 0.50, 0.00, 1.00, 0.50),
        "Galopp_03": extract_box(s1b, 0.00, 0.00, 0.50, 1.00),
        "Galopp_04": extract_box(s1b, 0.50, 0.00, 1.00, 1.00),

        # Phase 1 Horse Skulls & Neck Vertebra
        "Pferdeschaedel_01": extract_box(s3, 2/3, 0.50, 0.833, 0.796, keep_holes=True),
        "Pferdeschaedel_02": extract_box(s3, 0.833, 0.50, 1.00, 0.796, keep_holes=True),
        "Halswirbel_01":     extract_box(s3, 0.750, 0.796, 0.917, 1.00, keep_holes=True),

        # Phase 1 -> 2 Horse Collapse & Burning Horse Keyframes
        "Kollaps_Key1": extract_box(s4, 0.00, 0.00, 1/3, 0.50),
        "Kollaps_Key2": extract_box(s4, 1/3,  0.00, 2/3, 0.50),
        "Kollaps_Key3": extract_box(s4, 2/3,  0.00, 1.00, 0.50),
        # Note: trim bottom 11.5% of cell (0, 1) on Sheet 4 to cut off the 2 extra lower flame tips
        "Brennen_Key1": extract_box(s4, 0.00, 0.50, 1/3, 0.885),
        "Brennen_Key2": extract_box(s4, 1/3,  0.50, 2/3, 0.985),

        # Phase 2 Dismounted Green Skeleton Knight Fighting Alone on Foot (9 poses)
        "Ritter_Lauf_01":     extract_box(s2, 0.00, 0.00, 0.50, 0.50),
        "Ritter_Lauf_02":     extract_box(s2, 0.50, 0.00, 1.00, 0.50),
        "Ritter_Lauf_03":     extract_box(s2, 0.00, 0.50, 0.50, 1.00),
        "Ritter_Lanze_Hoch":  extract_box(s2, 0.50, 0.50, 1.00, 1.00),
        "Ritter_Lanzenstoss": extract_box(s3, 0.00, 0.00, 1/3,  0.50),
        "Ritter_Sprung":      extract_box(s3, 1/3,  0.00, 2/3,  0.50),
        "Ritter_Hocke":       extract_box(s3, 2/3,  0.00, 1.00, 0.50),
        "Ritter_Zerfall_01":  extract_box(s3, 0.00, 0.50, 1/3,  1.00),
        "Ritter_Zerfall_02":  extract_box(s3, 1/3,  0.50, 2/3,  1.00),

        # Phase 2 Death — 10 Shattered Green Skeleton & Broken Bronze Lance Fragments
        "Splitter_Schaedel":      extract_box(s4, 1290/1920, 550/1080, 1490/1920, 720/1080, keep_holes=True),
        "Splitter_Brustkorb":     extract_box(s4, 1490/1920, 550/1080, 1710/1920, 720/1080),
        "Splitter_Becken":        extract_box(s4, 1710/1920, 550/1080, 1910/1920, 720/1080),
        "Splitter_Knochen_Diag":  extract_box(s4, 1290/1920, 720/1080, 1445/1920, 890/1080),
        "Splitter_Knochen_Horiz": extract_box(s4, 1445/1920, 720/1080, 1600/1920, 890/1080),
        "Splitter_Knochen_Vert":  extract_box(s4, 1600/1920, 720/1080, 1755/1920, 890/1080),
        "Splitter_Knochen_Bein":  extract_box(s4, 1755/1920, 720/1080, 1910/1920, 890/1080),
        "Splitter_Lanze_Schaft":  extract_box(s4, 1290/1920, 890/1080, 1495/1920, 1070/1080),
        "Splitter_Lanze_Griff":   extract_box(s4, 1495/1920, 890/1080, 1705/1920, 1070/1080),
        "Splitter_Lanze_Spitze":  extract_box(s4, 1705/1920, 890/1080, 1910/1920, 1070/1080),

        # Fireballs
        "Feuerball_01": fb1_hd,
        "Feuerball_02": fb2_hd,
    }

    # Map all 49 ROM Bank 4 poses (0xA8A3..0xB033) to their crop key, German asset name, pad_scale, and actor types
    pose_map = {
        # Phase 1 Mounted Gallop (4 poses)
        0xa8a3: ("Galopp_01", "Boss_Rowdain_Galopp_01", 1.03, [0x04, 0x80]),
        0xa8fc: ("Galopp_02", "Boss_Rowdain_Galopp_02", 1.03, [0x04, 0x80]),
        0xa955: ("Galopp_03", "Boss_Rowdain_Galopp_03", 1.03, [0x04, 0x80]),
        0xa9ae: ("Galopp_04", "Boss_Rowdain_Galopp_04", 1.03, [0x04, 0x80]),

        # Phase 1 -> 2 Horse Buckling & Collapsing (10 poses)
        0xaa07: ("Kollaps_Key1", "Boss_Rowdain_Kollaps_01", 1.02, [0x04, 0x80]),
        0xaa60: ("Kollaps_Key1", "Boss_Rowdain_Kollaps_02", 1.02, [0x04, 0x80]),
        0xaab9: ("Kollaps_Key1", "Boss_Rowdain_Kollaps_03", 1.02, [0x04, 0x80]),
        0xab12: ("Kollaps_Key2", "Boss_Rowdain_Kollaps_04", 1.02, [0x04, 0x80]),
        0xab6b: ("Kollaps_Key2", "Boss_Rowdain_Kollaps_05", 1.02, [0x04, 0x80]),
        0xabc4: ("Kollaps_Key2", "Boss_Rowdain_Kollaps_06", 1.02, [0x04, 0x80]),
        0xac1d: ("Kollaps_Key2", "Boss_Rowdain_Kollaps_07", 1.02, [0x04, 0x80]),
        0xac76: ("Kollaps_Key3", "Boss_Rowdain_Kollaps_08", 1.02, [0x04, 0x80]),
        0xacd3: ("Kollaps_Key3", "Boss_Rowdain_Kollaps_09", 1.02, [0x04, 0x80]),
        0xad30: ("Kollaps_Key3", "Boss_Rowdain_Kollaps_10", 1.02, [0x04, 0x80]),

        # Horse Skulls, Neck Vertebrae & Fireballs
        0xad7d: ("Pferdeschaedel_01", "Boss_Rowdain_Pferdeschaedel_01", 1.04, [0x80, 0x04]),
        0xad82: ("Pferdeschaedel_02", "Boss_Rowdain_Pferdeschaedel_02", 1.04, [0x80, 0x04]),
        0xad8b: ("Halswirbel_01",     "Boss_Rowdain_Halswirbel_01",     1.00, [0x04, 0x80]),
        0xb029: ("Halswirbel_01",     "Boss_Rowdain_Halswirbel_01",     1.00, [0x04, 0x80]),
        0xad90: ("Feuerball_01",      "Boss_Rowdain_Feuerball_01",      1.04, [0x03, 0x80]),
        0xb02e: ("Feuerball_01",      "Boss_Rowdain_Feuerball_01",      1.04, [0x03, 0x80]),
        0xad95: ("Feuerball_02",      "Boss_Rowdain_Feuerball_02",      1.04, [0x03, 0x80]),
        0xb033: ("Feuerball_02",      "Boss_Rowdain_Feuerball_02",      1.04, [0x03, 0x80]),

        # Phase 2 Dismounted Green Skeleton Knight Fighting Alone on Foot (9 poses)
        0xad9a: ("Ritter_Lauf_01",     "Boss_Rowdain_Ritter_Lauf_01",     1.03, [0x80, 0x04]),
        0xadc3: ("Ritter_Lauf_02",     "Boss_Rowdain_Ritter_Lauf_02",     1.03, [0x80, 0x04]),
        0xadec: ("Ritter_Lauf_03",     "Boss_Rowdain_Ritter_Lauf_03",     1.03, [0x80, 0x04]),
        0xae15: ("Ritter_Lanze_Hoch",  "Boss_Rowdain_Ritter_Lanze_Hoch",  1.03, [0x80, 0x04]),
        0xae42: ("Ritter_Lanzenstoss", "Boss_Rowdain_Ritter_Lanzenstoss", 1.03, [0x80, 0x04]),
        0xae6b: ("Ritter_Sprung",      "Boss_Rowdain_Ritter_Sprung",      1.03, [0x80, 0x04]),
        0xae80: ("Ritter_Hocke",       "Boss_Rowdain_Ritter_Hocke",       1.03, [0x80, 0x04]),
        0xaea1: ("Ritter_Zerfall_01",  "Boss_Rowdain_Ritter_Zerfall_01",  1.03, [0x80, 0x04]),
        0xaeca: ("Ritter_Zerfall_02",  "Boss_Rowdain_Ritter_Zerfall_02",  1.03, [0x80, 0x04]),

        # Flying Bone Shards (3 poses)
        0xaef3: ("Splitter_Knochen_Diag",  "Boss_Rowdain_Splitter_Knochen_01", 1.04, [0x02, 0x01, 0x80]),
        0xaef8: ("Splitter_Knochen_Horiz", "Boss_Rowdain_Splitter_Knochen_02", 1.04, [0x02, 0x01, 0x80]),
        0xaefd: ("Splitter_Knochen_Vert",  "Boss_Rowdain_Splitter_Knochen_03", 1.04, [0x02, 0x01, 0x80]),

        # Burning Horse on Ground (5 poses)
        0xaf02: ("Brennen_Key1", "Boss_Rowdain_Brennen_01", 1.02, [0x04, 0x80]),
        0xaf33: ("Brennen_Key1", "Boss_Rowdain_Brennen_02", 1.02, [0x04, 0x80]),
        0xaf64: ("Brennen_Key2", "Boss_Rowdain_Brennen_03", 1.02, [0x04, 0x80]),
        0xaf95: ("Brennen_Key2", "Boss_Rowdain_Brennen_04", 1.02, [0x04, 0x80]),
        0xafc6: ("Brennen_Key2", "Boss_Rowdain_Brennen_05", 1.02, [0x04, 0x80]),

        # Shattered Green Skeleton Knight Body Parts & Broken Lance Pieces (10 poses)
        0xaff7: ("Splitter_Schaedel",     "Boss_Rowdain_Splitter_Schaedel",     1.05, [0x01, 0x02, 0x80]),
        0xaffc: ("Splitter_Brustkorb",    "Boss_Rowdain_Splitter_Brustkorb",    1.04, [0x01, 0x02, 0x80]),
        0xb001: ("Splitter_Becken",       "Boss_Rowdain_Splitter_Becken",       1.04, [0x01, 0x02, 0x80]),
        0xb006: ("Splitter_Knochen_Diag", "Boss_Rowdain_Splitter_Knochen_04",   1.04, [0x01, 0x02, 0x80]),
        0xb00b: ("Splitter_Knochen_Bein", "Boss_Rowdain_Splitter_Knochen_Bein", 1.04, [0x01, 0x02, 0x80]),
        0xb010: ("Splitter_Knochen_Diag", "Boss_Rowdain_Splitter_Knochen_05",   1.04, [0x01, 0x02, 0x80]),
        0xb015: ("Splitter_Knochen_Vert", "Boss_Rowdain_Splitter_Knochen_06",   1.04, [0x01, 0x02, 0x80]),
        0xb01a: ("Splitter_Lanze_Schaft", "Boss_Rowdain_Splitter_Lanze_Schaft", 1.04, [0x01, 0x02, 0x80]),
        0xb01f: ("Splitter_Lanze_Griff",  "Boss_Rowdain_Splitter_Lanze_Griff",  1.04, [0x01, 0x02, 0x80]),
        0xb024: ("Splitter_Lanze_Spitze", "Boss_Rowdain_Splitter_Lanze_Spitze", 1.04, [0x01, 0x02, 0x80]),
    }

    decoded_list = json.loads((SCAN_DIR / "rowdain_all_49_decoded.json").read_text(encoding="utf-8"))

    # Load existing Stage 01 enemies.json (keeping only the 30 non-boss entries)
    manifest_path = PACK_WORK / "enemies.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    base_frames = [
        f for f in manifest["frames"]
        if not f["image"].startswith("Boss_Rowdain_")
    ]

    new_frames = []
    seen_ids = {f["id"] for f in base_frames}

    for item in decoded_list:
        pa = item["pose"]
        h_str = item["hash"]
        ds = item["display_size"]
        an = item["anchor"]
        ref_png = SCAN_DIR / item["file"]
        ref_arr = np.array(Image.open(ref_png).convert("RGBA"))

        crop_key, asset_name, pad_sc, actor_types = pose_map[pa]
        hd_crop = crops[crop_key]

        # Build 8x and 4x canvases
        im_8x = fit_to_pose(hd_crop, ref_arr, scale=8, pad_scale=pad_sc)
        im_4x = fit_to_pose(hd_crop, ref_arr, scale=4, pad_scale=pad_sc)

        out_8x_name = f"{asset_name}_HD_8x.png"
        out_4x_name = f"{asset_name}_HD_4x.png"
        im_8x.save(USER_OUT / out_8x_name)
        im_4x.save(USER_OUT / out_4x_name)
        im_8x.save(PACK_WORK / out_8x_name)

        for atype in actor_types:
            fid = f"gegner-{atype:04x}_pose-{pa:04x}_{h_str}"
            if fid in seen_ids:
                continue
            seen_ids.add(fid)
            new_frames.append({
                "id": fid,
                "actor_type": atype,
                "pose": pa,
                "image": out_8x_name,
                "display_size": ds,
                "anchor": an,
            })

    manifest["frames"] = base_frames + new_frames
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Updated {manifest_path}: {len(base_frames)} base frames + {len(new_frames)} Rowdain frames = {len(manifest['frames'])} total frames.")

    # Sync pack to build-play/game, build, and build-lua
    for target in (PACK_PLAY, PACK_BUILD, PACK_LUA):
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(PACK_WORK, target)
        (target.parent / "selected.txt").write_text(PACK_NAME, encoding="utf-8")
    print("Synced hd-stage01 to build-play, build, and build-lua.")


if __name__ == "__main__":
    main()
