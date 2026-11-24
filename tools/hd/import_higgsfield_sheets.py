#!/usr/bin/env python3
"""1-Click Automatic Importer for Higgsfield/Claude HD Sprite Sheets.
Drop any generated HD sheet (.png / .jpg / .webp) matching its `output_stem` into:
  D:\Super Castlevania IV Recomp\Assets (ausgeschnitten)\Higgsfield_Vorbereitung\04_Higgsfield_Output\
Then run this script to automatically:
  1. Slice every 4x2 cell with strict 100% opaque border flood-fill (zero interior holes!)
  2. Register every sprite pixel-exact to its 1x reference bounding box at 8x (768x768)
  3. Auto-derive identical-size crimson red-blink for Bone Pillar (0x0b) & companion frames
  4. Merge into hd-stage01/enemies.json and sync to build-play, build, and build-lua!
"""

import json
import shutil
from collections import deque
from pathlib import Path
import numpy as np
from PIL import Image, ImageOps

ROOT = Path(r"D:\Super Castlevania IV Recomp\SuperCastlevaniaIvSNESRecomp")
KIT = Path(r"D:\Super Castlevania IV Recomp\Assets (ausgeschnitten)\Higgsfield_Vorbereitung")
DIR_OUT = KIT / "04_Higgsfield_Output"
EP_WORK = ROOT / "artwork-local" / "enemy-packs-hd" / "hd-stage01"
GEGNER_HD = Path(r"D:\Super Castlevania IV Recomp\Assets (ausgeschnitten)\Gegner\HD_4x_8x")


def matte_black_opaque(im: Image.Image, bg_soft: int = 26, bg_hard: int = 12) -> Image.Image:
    rgba = np.array(im.convert("RGBA"), dtype=np.float32)
    rgb = rgba[:, :, :3]
    lum_max = rgb.max(axis=2)
    lum_min = rgb.min(axis=2)
    h, w = lum_max.shape

    # Auto-detect whether this cell has a white background or black background from its border pixels
    border_min = np.concatenate([lum_min[0, :], lum_min[-1, :], lum_min[:, 0], lum_min[:, -1]])
    is_white_bg = float(np.mean(border_min > 232)) > 0.45

    if is_white_bg:
        bg_cand = (lum_min > 228) & ((lum_max - lum_min) < 22)
    else:
        bg_cand = lum_max < bg_soft

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

    if is_white_bg:
        ext_a = np.clip((248.0 - lum_min) / 20.0, 0.0, 1.0)
        alpha = np.where(ext, ext_a, 1.0)
        inner_bg = (~ext) & (lum_min > 242) & ((lum_max - lum_min) < 12)
    else:
        ext_a = np.clip((lum_max - bg_hard) / max(1.0, float(bg_soft - bg_hard)), 0.0, 1.0)
        alpha = np.where(ext, ext_a, 1.0)
        inner_bg = (~ext) & (lum_max <= 8.0)

    # Clear only large enclosed pure-bg pockets (>= 160 px)
    visited = np.zeros((h, w), dtype=bool)
    ys_b, xs_b = np.where(inner_bg)
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
                if 0 <= ny < h and 0 <= nx < w and not visited[ny, nx] and inner_bg[ny, nx]:
                    visited[ny, nx] = True
                    qq.append((ny, nx))
        if len(comp) >= 160:
            for cy, cx in comp:
                alpha[cy, cx] = 0.0

    edge = ext & (alpha > 0.05) & (alpha < 0.98)
    if not is_white_bg:
        for c in range(3):
            rgba[:, :, c] = np.where(edge, np.clip(rgba[:, :, c] / np.maximum(alpha, 0.35), 0, 255), rgba[:, :, c])
    else:
        # Remove 1px bright white halo touching transparent exterior
        pad = np.pad(ext, 1, mode="constant", constant_values=True)
        touch = pad[:-2, 1:-1] | pad[2:, 1:-1] | pad[1:-1, :-2] | pad[1:-1, 2:]
        alpha = np.where((~ext) & touch & (lum_min > 205) & ((lum_max - lum_min) < 20), 0.0, alpha)
    rgba[:, :, 3] = np.clip(alpha * 255.0, 0, 255)
    u8 = rgba.astype(np.uint8)
    ys, xs = np.where(u8[:, :, 3] > 24)
    if ys.size == 0:
        return Image.fromarray(u8, "RGBA")
    return Image.fromarray(u8[ys.min():ys.max() + 1, xs.min():xs.max() + 1], "RGBA")


def register_to_bbox_8x(crop_im: Image.Image, bbox_1x: list, canvas_1x: int = 96) -> Image.Image:
    nx0, ny0, nx1, ny1 = bbox_1x
    nw, nh = max(1, nx1 - nx0), max(1, ny1 - ny0)
    im8 = Image.new("RGBA", (canvas_1x * 8, canvas_1x * 8), (0, 0, 0, 0))
    im8.paste(crop_im.resize((nw * 8, nh * 8), Image.Resampling.LANCZOS), (nx0 * 8, ny0 * 8))
    return im8


def make_crimson_identical(im: Image.Image) -> Image.Image:
    arr = np.array(im.convert("RGBA"), dtype=np.float32)
    a = arr[:, :, 3]
    lum = 0.299 * arr[:, :, 0] + 0.587 * arr[:, :, 1] + 0.114 * arr[:, :, 2]
    out = np.zeros_like(arr)
    out[:, :, 0] = np.where(a > 0, np.clip(lum * 1.48 + 38.0, 0, 255), 0)
    out[:, :, 1] = np.where(a > 0, np.clip(lum * 0.44 + (lum / 255.0) ** 2 * 55.0, 0, 255), 0)
    out[:, :, 2] = np.where(a > 0, np.clip(lum * 0.18, 0, 255), 0)
    out[:, :, 3] = a
    return Image.fromarray(out.astype(np.uint8), "RGBA")


def find_sheet_file(stem: str) -> Path | None:
    for ext in (".png", ".jpg", ".jpeg", ".webp"):
        p = DIR_OUT / f"{stem}{ext}"
        if p.exists():
            return p
    return None


def main():
    manifest = json.loads((KIT / "sheet_manifest.json").read_text(encoding="utf-8"))
    ep_meta = json.loads((EP_WORK / "enemies.json").read_text(encoding="utf-8"))
    by_id = {f["id"]: f for f in ep_meta["frames"]}

    all_sheets = (
        manifest.get("priority_sheets", [])
        + manifest.get("boss_sheets", [])
        + manifest.get("monster_sheets", [])
    )

    # Also load the 56 1:1 ROM-matched Einzelmonster sheets + 26 complete deduplicated Boss sheets!
    einzel_mp = KIT / "06_Einzelmonster_Aus_Sprites" / "einzelmonster_manifest.json"
    einzel_sheets = json.loads(einzel_mp.read_text(encoding="utf-8")).get("sheets", []) if einzel_mp.exists() else []
    boss_mp = KIT / "02_Alle_Bosse_1x_Sheets" / "boss_complete_manifest.json"
    boss_complete_sheets = json.loads(boss_mp.read_text(encoding="utf-8")).get("sheets", []) if boss_mp.exists() else []
    einzel_sheets = einzel_sheets + boss_complete_sheets

    imported_sheets = 0
    imported_poses = 0
    for sh in all_sheets:
        stem = sh["output_stem"]
        hd_path = find_sheet_file(stem)
        if not hd_path:
            continue
        im = Image.open(hd_path).convert("RGBA")
        W, H = im.size
        cw, ch = W // 4, H // 2
        imported_sheets += 1
        print(f"Importing {hd_path.name} ({W}x{H}) -> {len(sh['cells'])} poses...")

        for cell in sh["cells"]:
            col, row = cell["col"], cell["row"]
            box = (col * cw + 6, row * ch + 6, (col + 1) * cw - 6, (row + 1) * ch - 6)
            crop = matte_black_opaque(im.crop(box))
            ref_im = Image.open(cell["ref_png"]).convert("RGBA")
            canvas_1x = ref_im.width  # 96 or 192 for large bosses!
            im8 = register_to_bbox_8x(crop, cell["bbox_1x"], canvas_1x=canvas_1x)

            fid = cell["id"]
            fname = f"{fid}.png"
            im8.save(EP_WORK / fname)
            by_id[fid] = {
                "id": fid,
                "actor_type": cell["actor_type"],
                "pose": cell["pose"],
                "image": fname,
                "display_size": [canvas_1x, canvas_1x],
                "anchor": [canvas_1x // 2, canvas_1x // 2],
            }
            imported_poses += 1

            # Auto-derive companion poses where applicable!
            if fid == "gegner-000b_pose-8d70_d88a204c80492654":
                red_id = "gegner-000b_pose-8c0f_d88a204c80492654"
                make_crimson_identical(im8).save(EP_WORK / f"{red_id}.png")
                by_id[red_id] = {
                    "id": red_id, "actor_type": 0x0b, "pose": 0x8c0f,
                    "image": f"{red_id}.png", "display_size": [96, 96], "anchor": [48, 48],
                }
            elif fid == "gegner-0001_pose-905c_34c3a09dda5a9115":
                f2_id = "gegner-0001_pose-9061_b1b5a0285c4e9667"
                crop2 = crop.rotate(18.0, Image.Resampling.BICUBIC, expand=True)
                register_to_bbox_8x(crop2, cell["bbox_1x"], 96).save(EP_WORK / f"{f2_id}.png")
                by_id[f2_id] = {
                    "id": f2_id, "actor_type": 0x01, "pose": 0x9061,
                    "image": f"{f2_id}.png", "display_size": [96, 96], "anchor": [48, 48],
                }
            elif fid == "gegner-0003_pose-a4f8_eda52702eaba7e09":
                b2_id = "gegner-0003_pose-a4fd_9a69b42bf3422c28"
                register_to_bbox_8x(ImageOps.mirror(crop), cell["bbox_1x"], 96).save(EP_WORK / f"{b2_id}.png")
                by_id[b2_id] = {
                    "id": b2_id, "actor_type": 0x03, "pose": 0xa4fd,
                    "image": f"{b2_id}.png", "display_size": [96, 96], "anchor": [48, 48],
                }

    # Import any completed Einzelmonster HD sheets (1:1 ROM-matched with automatic H-flip alignment!)
    for sh in einzel_sheets:
        stem = sh["output_stem"]
        hd_path = find_sheet_file(stem)
        if not hd_path:
            continue
        im = Image.open(hd_path).convert("RGBA")
        W, H = im.size
        cw, ch = W // 4, H // 2
        imported_sheets += 1
        print(f"Importing Einzelmonster {hd_path.name} ({W}x{H})...")
        for cell in sh["cells"]:
            if not cell.get("rom_matches"):
                continue
            col, row = cell["col"], cell["row"]
            box = (col * cw + 6, row * ch + 6, (col + 1) * cw - 6, (row + 1) * ch - 6)
            crop = matte_black_opaque(im.crop(box))
            for m in cell["rom_matches"]:
                c_use = ImageOps.mirror(crop) if m.get("hflip") else crop
                canvas_1x = m.get("canvas_1x", 96)
                im8 = register_to_bbox_8x(c_use, m["bbox_1x"], canvas_1x=canvas_1x)
                fid = m["id"]
                fname = f"{fid}.png"
                im8.save(EP_WORK / fname)
                by_id[fid] = {
                    "id": fid,
                    "actor_type": m["actor_type"],
                    "pose": m["pose"],
                    "image": fname,
                    "display_size": [canvas_1x, canvas_1x],
                    "anchor": [canvas_1x // 2, canvas_1x // 2],
                }
                imported_poses += 1

    if imported_sheets == 0:
        print(f"No HD sheets found yet in {DIR_OUT} (ready for Higgsfield outputs!).")
        print(f"Total manifests indexed: {len(all_sheets)} workshop/boss sheets + {len(einzel_sheets)} 1:1 ROM-matched Einzelmonster sheets.")
        return

    ep_meta["frames"] = sorted(by_id.values(), key=lambda f: (f["actor_type"], f["pose"], f["id"]))
    (EP_WORK / "enemies.json").write_text(json.dumps(ep_meta, indent=2) + "\n", encoding="utf-8")

    from sync_hd_pack_to_workshop import sync_runtime_packs, sync_workshop_artwork
    sync_runtime_packs()
    sync_workshop_artwork()
    print(f"DONE! Imported {imported_poses} poses from {imported_sheets} sheets -> synced {len(ep_meta['frames'])} total frames to game + Monster-Werkstatt!")


if __name__ == "__main__":
    main()
