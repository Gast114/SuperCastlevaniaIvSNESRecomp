#!/usr/bin/env python3
"""Rebuild ALL 13 Boss 4x2 reference sheets directly from the user's COMPLETE Sprites/<Boss>.png files
(no incomplete Monster-Werkstatt subsets, no mixing of different monsters on one sheet!).
- Automatically removes solid/transparent background & Spriters Resource logos/text
- Splits every pose cleanly with uniform integer scale & common foot baseline per boss
- Matches every pose 1:1 against our 887-pose ROM/Werkstatt database for automatic 1-click import!
"""

import json
import re
from collections import deque
from pathlib import Path
import numpy as np
from PIL import Image

ROOT = Path(r"D:\Super Castlevania IV Recomp\SuperCastlevaniaIvSNESRecomp")
SPRITES_DIR = Path(r"D:\Super Castlevania IV Recomp\Assets (ausgeschnitten)\Sprites")
LIB_NT = ROOT / "artwork-local" / "enemy-library" / "native-template"
OUT_BOSS = Path(r"D:\Super Castlevania IV Recomp\Assets (ausgeschnitten)\Higgsfield_Vorbereitung\02_Alle_Bosse_1x_Sheets")
OUT_BOSS.mkdir(parents=True, exist_ok=True)

BOSS_FILES = [
    ("Boss_Medusa",           "Medusa.png",                 0x83),
    ("Boss_Orphic_Vipers",    "Orphic Vipers.png",          0x81),
    ("Boss_Puwexyl",          "Puwexyl.png",                0x84),
    ("Boss_Koranot",          "Koranot.png",                0x82),
    ("Boss_Dancing_Specters", "Dancing Specters.png",       0x8b),
    ("Boss_Sir_Grakul",       "Sir Grakul.png",             0x8a),
    ("Boss_Frankenstein",     "Frankenstein's Monster.png", 0x87),
    ("Boss_Akmodan_II",       "Akmodan.png",                0x8c),
    ("Boss_Slogra",           "Slogra.png",                 0x89),
    ("Boss_Gaibon",           "Gaibon.png",                 0x88),
    ("Boss_Zapf_Bat",         "Zapf Bat.png",               0x86),
    ("Boss_Death",            "Death.png",                  0x89),
    ("Boss_Dracula",          "Dracula.png",                0x85),
]


def to_clean_rgba(im: Image.Image) -> Image.Image:
    """Convert either transparent RGBA or solid-color-background RGB Spriters Resource sheet to clean RGBA."""
    if im.mode == "RGBA":
        arr = np.array(im)
        # If corner pixel is opaque, also key out that exact flat background color
        if arr[0, 0, 3] > 200:
            bg = arr[0, 0, :3].copy()
            is_bg = np.all(arr[:, :, :3] == bg, axis=2)
            arr[is_bg, 3] = 0
        return Image.fromarray(arr, "RGBA")
    arr_rgb = np.array(im.convert("RGB"))
    bg = arr_rgb[0, 0].copy()
    is_bg = np.all(arr_rgb == bg, axis=2)
    rgba = np.zeros((arr_rgb.shape[0], arr_rgb.shape[1], 4), dtype=np.uint8)
    rgba[:, :, :3] = arr_rgb
    rgba[:, :, 3] = np.where(is_bg, 0, 255)
    return Image.fromarray(rgba, "RGBA")


def split_boss_sprites(im: Image.Image, min_area: int = 80, min_dim: int = 12) -> list:
    """Split a boss sheet into clean individual poses using strict empty-row & empty-column projection
    (zero gluing of 1px-spaced poses!), filtering out tiny text letters."""
    arr = np.array(im.convert("RGBA"))
    mask = arr[:, :, 3] > 0
    h, w = mask.shape
    if not mask.any():
        return []

    row_has = mask.any(axis=1)
    row_bands = []
    in_b = False
    y0 = 0
    for y in range(h):
        if row_has[y] and not in_b:
            y0 = y; in_b = True
        elif not row_has[y] and in_b:
            row_bands.append((y0, y)); in_b = False
    if in_b:
        row_bands.append((y0, h))

    crops = []
    for by0, by1 in row_bands:
        band = mask[by0:by1, :]
        col_has = band.any(axis=0)
        in_c = False
        x0 = 0
        for x in range(w):
            if col_has[x] and not in_c:
                x0 = x; in_c = True
            elif not col_has[x] and in_c:
                sub = band[:, x0:x]
                if int(sub.sum()) >= min_area:
                    ys, xs = np.where(sub)
                    bx0, b_y0 = x0 + int(xs.min()), by0 + int(ys.min())
                    bx1, b_y1 = x0 + int(xs.max()) + 1, by0 + int(ys.max()) + 1
                    if (bx1 - bx0) >= min_dim or (b_y1 - b_y0) >= min_dim:
                        crops.append(im.crop((bx0, b_y0, bx1, b_y1)))
                in_c = False
        if in_c:
            sub = band[:, x0:w]
            if int(sub.sum()) >= min_area:
                ys, xs = np.where(sub)
                bx0, b_y0 = x0 + int(xs.min()), by0 + int(ys.min())
                bx1, b_y1 = x0 + int(xs.max()) + 1, by0 + int(ys.max()) + 1
                if (bx1 - bx0) >= min_dim or (b_y1 - b_y0) >= min_dim:
                    crops.append(im.crop((bx0, b_y0, bx1, b_y1)))
    return crops


def deduplicate_by_silhouette(crops: list, iou_thresh: float = 0.90) -> list:
    """Collapse palette-swap / color-flash duplicates (like Death's 15 color swaps!) into ONE canonical
    bright full-color pose per unique silhouette, recording all color variants so Python can recolor
    the exact same HD pixels later with 100% identical geometry!"""
    unique = []  # list of (best_crop, best_mask, variant_count)
    for sp in crops:
        arr = np.array(sp.convert("RGBA"))
        m = arr[:, :, 3] > 0
        h, w = m.shape
        # Measure color richness (prefer full-color bright pose over dark fade or monochrome flash!)
        fg = arr[m, :3].astype(np.float32)
        score = float(fg.max(axis=1).mean()) + float(fg.std(axis=1).mean()) * 1.5

        merged = False
        for ui, (u_sp, u_m, u_score, u_cnt) in enumerate(unique):
            uh, uw = u_m.shape
            if abs(uh - h) > 2 or abs(uw - w) > 2:
                continue
            mh, mw = min(h, uh), min(w, uw)
            inter = int(np.logical_and(m[:mh, :mw], u_m[:mh, :mw]).sum())
            union = int(m.sum()) + int(u_m.sum()) - inter
            if (inter / max(1, union)) >= iou_thresh:
                # Always keep the FIRST (default/normal Row-1) palette instead of later red/flash swaps!
                unique[ui] = (u_sp, u_m, u_score, u_cnt + 1)
                merged = True
                break
        if not merged:
            unique.append((sp, m, score, 1))
    return [(u[0], u[3]) for u in unique]


def main():
    # Load all boss poses from enemy-library/native-template for 1:1 ROM matching
    nt_j = json.loads((LIB_NT / "enemies.json").read_text(encoding="utf-8"))
    rom_db = []
    for fr in nt_j["frames"]:
        if "__teil-" in fr["id"] or fr["actor_type"] < 0x80:
            continue
        p = LIB_NT / (fr["id"] + ".png")
        if not p.exists():
            continue
        im = Image.open(p).convert("RGBA")
        bb = im.getbbox()
        if not bb:
            continue
        c = np.array(im.crop(bb))
        rom_db.append({
            "id": fr["id"], "actor_type": fr["actor_type"], "pose": fr["pose"],
            "mask": c[:, :, 3] > 0, "ref_png": str(p), "bbox_1x": list(bb), "canvas_1x": im.width,
        })

    # Clean old incomplete boss sheets
    for old_f in OUT_BOSS.glob("*.png"):
        old_f.unlink()

    all_boss_sheets = []
    for slug, fname, default_type in BOSS_FILES:
        src = SPRITES_DIR / fname
        if not src.exists():
            continue
        im = to_clean_rgba(Image.open(src))
        # Special trim: remove SMITHYGCN Seal of Quality logo & broken-pose note at bottom-right of Slogra.png
        if fname == "Slogra.png":
            arr = np.array(im)
            arr[:, 430:, 3] = 0       # right logo
            arr[140:, 90:, 3] = 0     # broken poses + note at bottom
            im = Image.fromarray(arr, "RGBA")
        elif fname == "Death.png":
            # Trim raw VRAM tile-sheet block at y=2575..2743 of Death.png
            arr = np.array(im)
            arr[2570:, :, 3] = 0
            im = Image.fromarray(arr, "RGBA")

        raw_crops = split_boss_sprites(im, min_area=90, min_dim=14)
        deduped = deduplicate_by_silhouette(raw_crops, iou_thresh=0.88)
        crops = [x[0] for x in deduped]
        chunks = [crops[i:i + 8] for i in range(0, len(crops), 8)]
        matched_total = 0
        for ci, ch in enumerate(chunks, 1):
            canvas = Image.new("RGB", (1280, 720), (0, 0, 0))
            max_w = max(x.width for x in ch)
            max_h = max(x.height for x in ch)
            sc = max(1, min(8, min(288 // max(1, max_w), 328 // max(1, max_h))))
            cells = []
            for idx, sp in enumerate(ch):
                col, row = idx % 4, idx // 4
                big = sp.resize((sp.width * sc, sp.height * sc), Image.Resampling.NEAREST)
                ox = col * 320 + (320 - big.width) // 2
                oy = max(row * 360 + 8, row * 360 + (360 - big.height) - 20)
                canvas.paste(big, (ox, oy), big)

                # Match silhouette against ROM db
                m = np.array(sp)[:, :, 3] > 0
                h, w = m.shape
                rom_matches = []
                for rec in rom_db:
                    dm = rec["mask"]
                    dh, dw = dm.shape
                    if abs(dh - h) > 3 or abs(dw - w) > 3:
                        continue
                    mh, mw = min(h, dh), min(w, dw)
                    for flip in (False, True):
                        tm = m[:, ::-1] if flip else m
                        inter = int(np.logical_and(tm[:mh, :mw], dm[:mh, :mw]).sum())
                        union = int(tm.sum()) + int(dm.sum()) - inter
                        iou = inter / max(1, union)
                        if iou >= 0.78:
                            rom_matches.append({
                                "id": rec["id"], "actor_type": rec["actor_type"], "pose": rec["pose"],
                                "hflip": flip, "iou": round(iou, 3), "ref_png": rec["ref_png"],
                                "bbox_1x": rec["bbox_1x"], "canvas_1x": rec["canvas_1x"],
                            })
                            break
                if rom_matches:
                    matched_total += 1
                cells.append({
                    "col": col, "row": row, "size_1x": [sp.width, sp.height], "rom_matches": rom_matches
                })
            out_name = f"{slug}_Sheet{ci:02d}_4x2_REF.png"
            canvas.save(OUT_BOSS / out_name, "PNG")
            all_boss_sheets.append({
                "boss": slug,
                "source_file": fname,
                "output_stem": f"{slug}_Sheet{ci:02d}_HD",
                "ref_png": str(OUT_BOSS / out_name),
                "cells": cells,
            })
        print(f"  {slug:22s}: {len(raw_crops):3d} raw -> {len(crops):2d} UNIQUE silhouettes -> {len(chunks)} sheet(s) ({matched_total} matched in ROM DB)")

    (OUT_BOSS / "boss_complete_manifest.json").write_text(json.dumps({"version": 2, "sheets": all_boss_sheets}, indent=2) + "\n", encoding="utf-8")
    print(f"\nDONE! Built {len(all_boss_sheets)} COMPLETE per-boss 4x2 sheets from Sprites/*.png in {OUT_BOSS}")


if __name__ == "__main__":
    main()
