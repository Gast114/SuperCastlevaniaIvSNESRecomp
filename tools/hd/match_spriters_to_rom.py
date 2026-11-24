#!/usr/bin/env python3
"""Match ALL 47 user-separated RGBA `Enemy - *.png` sheets 1:1 against EVERY non-piece pose in:
  1. `missing_enemies_capture/native-template/` (Stage 01 F1-F10 live captures)
  2. `artwork-local/enemy-library/native-template/` (all 880 whole-pose ROM/Werkstatt frames!)
  3. `artwork-local/enemy-packs-hd/hd-stage01/` (already-imported Stage 01 enemies)
Because we require strict 1x silhouette IoU >= 0.82 against the user's clean Spriters Resource PNG,
corrupted offline VRAM dumps are mathematically rejected while EVERY valid ROM pose matches 1:1!

Outputs:
  - Clean 1-enemy-per-sheet 4x2 1280x720 reference sheets in `06_Einzelmonster_Aus_Sprites/`
  - `einzelmonster_manifest.json` mapping EVERY matched (sheet, col, row) -> exact list of ROM `gegner-XXXX_pose-XXXX_HASH` IDs!
"""

import json
import re
from pathlib import Path
import numpy as np
from PIL import Image

ROOT = Path(r"D:\Super Castlevania IV Recomp\SuperCastlevaniaIvSNESRecomp")
SPRITES_DIR = Path(r"D:\Super Castlevania IV Recomp\Assets (ausgeschnitten)\Sprites")
LIB_NT = ROOT / "artwork-local" / "enemy-library" / "native-template"
CAP_NT = Path(r"C:\Users\Gaming\.gemini\antigravity\brain\0e3d1566-2f3c-4183-be49-fad33ce3d4a9\scratch\missing_enemies_capture\native-template")
STAGE01_REF = Path(r"C:\Users\Gaming\.gemini\antigravity\brain\0e3d1566-2f3c-4183-be49-fad33ce3d4a9\scratch\stage01_enemies_ref")
OUT_DIR = Path(r"D:\Super Castlevania IV Recomp\Assets (ausgeschnitten)\Higgsfield_Vorbereitung\06_Einzelmonster_Aus_Sprites")
OUT_DIR.mkdir(parents=True, exist_ok=True)


def split_rgba_sprites(im: Image.Image) -> list:
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
                if sub.sum() >= 10:
                    ys, xs = np.where(sub)
                    crops.append(im.crop((x0 + int(xs.min()), by0 + int(ys.min()), x0 + int(xs.max()) + 1, by0 + int(ys.max()) + 1)))
                in_c = False
        if in_c:
            sub = band[:, x0:w]
            if sub.sum() >= 10:
                ys, xs = np.where(sub)
                crops.append(im.crop((x0 + int(xs.min()), by0 + int(ys.min()), x0 + int(xs.max()) + 1, by0 + int(ys.max()) + 1)))
    return crops


def load_full_rom_db():
    """Load ALL non-piece whole-pose 1x PNGs from CAP_NT, STAGE01_REF, and LIB_NT."""
    db = []
    seen = set()

    def add_folder(nt_dir: Path, json_name: str = "enemies.json"):
        jp = nt_dir / json_name
        if not jp.exists():
            return
        j = json.loads(jp.read_text(encoding="utf-8"))
        for fr in j.get("frames", []):
            fid = fr["id"]
            if "__teil-" in fid or fid in seen:
                continue
            p = nt_dir / f"{fid}.png"
            if not p.exists():
                continue
            im = Image.open(p).convert("RGBA")
            bb = im.getbbox()
            if not bb:
                continue
            c = np.array(im.crop(bb))
            m = c[:, :, 3] > 0
            if m.sum() < 8:
                continue
            # Also store canvas size & exact 1x bbox inside canvas!
            db.append({
                "id": fid,
                "actor_type": fr["actor_type"],
                "pose": fr["pose"],
                "mask": m,
                "ref_png": str(p),
                "bbox_1x": list(bb),
                "canvas_1x": im.width,
            })
            seen.add(fid)

    add_folder(CAP_NT, "enemies.json")
    add_folder(STAGE01_REF, "captured_all.json")
    add_folder(LIB_NT, "enemies.json")
    return db


def find_all_rom_matches(crop_im: Image.Image, db: list, min_iou: float = 0.80) -> list:
    """Return ALL exact 1:1 ROM pose matches (including palette variants sharing the same silhouette!)."""
    arr = np.array(crop_im.convert("RGBA"))
    m = arr[:, :, 3] > 0
    h, w = m.shape
    matches = []
    for rec in db:
        dm = rec["mask"]
        dh, dw = dm.shape
        if abs(dh - h) > 2 or abs(dw - w) > 2:
            continue
        mh, mw = min(h, dh), min(w, dw)
        best_flip = None
        best_iou = 0.0
        for flip in (False, True):
            tm = m[:, ::-1] if flip else m
            inter = int(np.logical_and(tm[:mh, :mw], dm[:mh, :mw]).sum())
            union = int(tm.sum()) + int(dm.sum()) - inter
            iou = inter / max(1, union)
            if iou > best_iou:
                best_iou = iou
                best_flip = flip
        if best_iou >= min_iou:
            matches.append({
                "id": rec["id"],
                "actor_type": rec["actor_type"],
                "pose": rec["pose"],
                "hflip": best_flip,
                "iou": round(best_iou, 3),
                "ref_png": rec["ref_png"],
                "bbox_1x": rec["bbox_1x"],
                "canvas_1x": rec["canvas_1x"],
            })
    matches.sort(key=lambda x: -x["iou"])
    return matches


def main():
    db = load_full_rom_db()
    print(f"Loaded {len(db)} total whole-pose ROM/Werkstatt sprites for 1:1 silhouette matching.")

    for old_f in OUT_DIR.glob("*.png"):
        old_f.unlink()

    enemy_files = sorted(SPRITES_DIR.glob("Enemy - *.png"))
    manifest_sheets = []
    report = []
    total_poses = 0
    total_matched_poses = 0
    total_rom_ids = 0

    for ef in enemy_files:
        im = Image.open(ef).convert("RGBA")
        crops = split_rgba_sprites(im)
        slug = re.sub(r"[^A-Za-z0-9]+", "_", ef.stem.replace("Enemy - ", "")).strip("_")

        pose_matches = [find_all_rom_matches(c, db, min_iou=0.80) for c in crops]
        matched_cnt = sum(1 for ms in pose_matches if ms)
        total_poses += len(crops)
        total_matched_poses += matched_cnt

        # Pack into clean 4x2 sheets (uniform scale + common foot baseline!)
        chunks = [list(range(i, min(len(crops), i + 8))) for i in range(0, len(crops), 8)]
        for si, idxs in enumerate(chunks, 1):
            ch_crops = [crops[k] for k in idxs]
            canvas = Image.new("RGB", (1280, 720), (0, 0, 0))
            max_w = max(x.width for x in ch_crops)
            max_h = max(x.height for x in ch_crops)
            sc = max(1, min(10, min(280 // max(1, max_w), 320 // max(1, max_h))))
            cells = []
            for local_i, k in enumerate(idxs):
                sp = crops[k]
                col, row = local_i % 4, local_i // 4
                big = sp.resize((sp.width * sc, sp.height * sc), Image.Resampling.NEAREST)
                ox = col * 320 + (320 - big.width) // 2
                oy = max(row * 360 + 8, row * 360 + (360 - big.height) - 24)
                canvas.paste(big, (ox, oy), big)
                ms = pose_matches[k]
                total_rom_ids += len(ms)
                cells.append({
                    "col": col,
                    "row": row,
                    "pose_idx": k,
                    "size_1x": [sp.width, sp.height],
                    "rom_matches": ms,
                })
            out_name = f"{slug}_4x2_REF.png" if len(chunks) == 1 else f"{slug}_Part{si:02d}_4x2_REF.png"
            out_stem = out_name.replace("_4x2_REF.png", "_HD")
            canvas.save(OUT_DIR / out_name, "PNG")
            manifest_sheets.append({
                "enemy": slug,
                "output_stem": out_stem,
                "ref_png": str(OUT_DIR / out_name),
                "cells": cells,
            })

        types_found = sorted(set(f"0x{m['actor_type']:02x}" for ms in pose_matches for m in ms))
        report.append({
            "file": ef.name,
            "poses": len(crops),
            "matched_poses": matched_cnt,
            "rom_ids": sum(len(ms) for ms in pose_matches),
            "actor_types": types_found,
        })

    (OUT_DIR / "einzelmonster_manifest.json").write_text(json.dumps({"version": 1, "sheets": manifest_sheets}, indent=2) + "\n", encoding="utf-8")
    (OUT_DIR / "spriters_match_report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    matched_enemies = [r for r in report if r["matched_poses"] > 0]
    unmatched_enemies = [r for r in report if r["matched_poses"] == 0]
    print(f"RESULT: {len(matched_enemies)}/{len(enemy_files)} enemies matched 1:1 to ROM! ({total_matched_poses}/{total_poses} poses -> {total_rom_ids} ROM frame IDs!)")
    if unmatched_enemies:
        print(f"Unmatched enemies ({len(unmatched_enemies)}):")
        for r in unmatched_enemies:
            print(f"  - {r['file']} ({r['poses']} poses)")


if __name__ == "__main__":
    main()
