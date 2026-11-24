"""Update the Holy Cross Boomerang (Waffe_Kreuz_Bumerang_1 & 2) and build the complete HD Skeleton enemy + Thrown Bone:
1. Updates 'Assets (ausgeschnitten)/Items/02_Waffen/Waffe_Kreuz_Bumerang_1..2_HD_4x/8x.png'
   from holy_cross_boomerang_2f_hd_1795330017245.jpg.
2. Registers all 5 Skeleton body poses + 3 Thrown Bone poses from skeleton_4x2_hd_remaster_1795330022721.jpg:
   - Saves 4x (384x384) & 8x (768x768) PNGs in 'Assets (ausgeschnitten)/Gegner/HD_4x_8x/'
   - Updates 'Assets (ausgeschnitten)/Gegner/02_Skelette_Alle_Aktionen/artwork/' (387x387 whole poses & components)
   - Updates 'Assets (ausgeschnitten)/Gegner/01_Skelette/artwork/' (Skelett_Schritt_01 & 02)
3. Slices all 58 8x8 (32x32 at 4x) VRAM OBJ tiles of the Skeleton & Thrown Bone + the 8 8x8 tiles of the
   2-frame Holy Cross Boomerang and injects them into ALL 8 Stage 01 scenes (entrance, a02..a08)
   as 'stage-01-user-grid-v20-boomerang-skeleton'.
"""
import hashlib
import json
import shutil
import sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageFilter, ImageOps

ROOT = Path(r"D:\Super Castlevania IV Recomp\SuperCastlevaniaIvSNESRecomp")
ASSETS_ROOT = Path(r"D:\Super Castlevania IV Recomp\Assets (ausgeschnitten)")
ITEMS_DIR = ASSETS_ROOT / "Items"
GEGNER_DIR = ASSETS_ROOT / "Gegner"
SKEL_ALL_DIR = GEGNER_DIR / "02_Skelette_Alle_Aktionen"
SKEL_01_DIR = GEGNER_DIR / "01_Skelette"
BRAIN = Path(r"C:\Users\Gaming\.gemini\antigravity\brain\0e3d1566-2f3c-4183-be49-fad33ce3d4a9")

sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tools" / "hd"))
from level_assets import Assets
import hd_common as hd
from hd_preview import fnv_key
from hd_tiles import write_pack

SCALE = 4


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


def fill_1x_mask_gaps(hd_arr: np.ndarray, mask_1x: np.ndarray, scale: int, radius: int = 8) -> np.ndarray:
    """Ensure every subpixel inside a non-zero 1x pixel (expanded by scale) has opaque HD RGB+A coverage.
    Also gently pulls nearby HD details into the 1x silhouette so SNES OAM 1x pixel masking never clips hollow gaps.
    """
    out = hd_arr.copy()
    h, w, _ = out.shape
    m_hd = np.repeat(np.repeat(mask_1x.astype(bool), scale, axis=0), scale, axis=1)
    have = out[:, :, 3] > 96
    need = m_hd & (~have)
    if not need.any():
        # Force full opacity inside the 1x mask
        out[m_hd, 3] = np.maximum(out[m_hd, 3], 245)
        return out

    # Iterative nearest-neighbor propagation from opaque HD pixels into needed 1x-mask subpixels
    cur = out.copy()
    cur_have = have.copy()
    for _ in range(radius):
        still_need = m_hd & (~cur_have)
        if not still_need.any():
            break
        acc_rgb = np.zeros((h, w, 3), dtype=np.float32)
        acc_w = np.zeros((h, w), dtype=np.float32)
        for dy, dx in [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)]:
            sy0, sy1 = max(0, -dy), min(h, h - dy)
            dy0, dy1 = max(0, dy), min(h, h + dy)
            sx0, sx1 = max(0, -dx), min(w, w - dx)
            dx0, dx1 = max(0, dx), min(w, w + dx)
            src_ok = cur_have[sy0:sy1, sx0:sx1]
            w_step = 1.0 if (dy == 0 or dx == 0) else 0.7
            acc_rgb[dy0:dy1, dx0:dx1] += cur[sy0:sy1, sx0:sx1, :3].astype(np.float32) * (src_ok[:, :, None] * w_step)
            acc_w[dy0:dy1, dx0:dx1] += src_ok.astype(np.float32) * w_step
        fill_now = still_need & (acc_w > 0)
        if not fill_now.any():
            break
        cur[fill_now, :3] = np.clip(acc_rgb[fill_now] / acc_w[fill_now, None], 0, 255).astype(np.uint8)
        cur[fill_now, 3] = 255
        cur_have[fill_now] = True

    cur[m_hd, 3] = np.maximum(cur[m_hd, 3], 245)
    return cur


def extract_boomerang_frames(vram) -> tuple:
    """Extract Frame 1 (~21° tilted cross, tids=[0x44,0x45,0x54,0x55]) and Frame 2 (0° upright '+' cross,
    tids=[0x46,0x47,0x56,0x57]) from holy_cross_boomerang_2f_hd_1795330017245.jpg into exact 64x64 (4x)
    and 128x128 (8x) cells aligned 100% to the native 1x OAM pixel masks.
    """
    raw = Image.open(BRAIN / "holy_cross_boomerang_2f_hd_1795330017245.jpg").convert("RGBA")
    sheet = raw.resize((1280, 720), Image.Resampling.LANCZOS)
    arr = np.array(sheet, dtype=np.float32)

    # Extract the upright '+' Holy Cross from the right half (x=660..1240)
    half = arr[40:680, 660:1240].copy()
    lum = half[:, :, :3].max(axis=2)
    m = lum > 22.0
    ys, xs = np.where(m)
    sub = half[ys.min():ys.max() + 1, xs.min():xs.max() + 1].copy()
    s_lum = sub[:, :, :3].max(axis=2)
    alpha = np.clip((s_lum - 16.0) / 24.0, 0.0, 1.0)
    sub[:, :, 3] = np.clip(alpha * 255.0, 0, 255)
    upright_im = Image.fromarray(sub.astype(np.uint8), "RGBA")

    # Build native 16x16 1x masks for Frame 1 ([0x44,0x45,0x54,0x55]) and Frame 2 ([0x46,0x47,0x56,0x57])
    masks_1x = []
    for tids in [[0x44, 0x45, 0x54, 0x55], [0x46, 0x47, 0x56, 0x57]]:
        m16 = np.zeros((16, 16), dtype=bool)
        for idx, tid in enumerate(tids):
            qx, qy = idx % 2, idx // 2
            m16[qy * 8:(qy + 1) * 8, qx * 8:(qx + 1) * 8] = decode_obj_indices(vram, tid) > 0
        masks_1x.append(m16)

    # Frame 1 in SNES is tilted +21° counter-clockwise relative to upright Frame 2
    tilted_raw = upright_im.rotate(21.0, Image.Resampling.BICUBIC, expand=False)
    t_arr = np.array(tilted_raw)
    ty, tx = np.where(t_arr[:, :, 3] > 24)
    tilted_im = Image.fromarray(t_arr[ty.min():ty.max() + 1, tx.min():tx.max() + 1], "RGBA")

    frames_4x, frames_8x = [], []
    for src_im, m16 in [(tilted_im, masks_1x[0]), (upright_im, masks_1x[1])]:
        # Native bbox is (1, 0, 16, 16) -> 15x16 in a 16x16 cell
        im8 = Image.new("RGBA", (128, 128), (0, 0, 0, 0))
        im8.paste(src_im.resize((15 * 8, 16 * 8), Image.Resampling.LANCZOS), (1 * 8, 0))
        arr8 = fill_1x_mask_gaps(np.array(im8), m16, scale=8, radius=16)
        im8 = Image.fromarray(arr8, "RGBA")

        im4 = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        im4.paste(src_im.resize((15 * 4, 16 * 4), Image.Resampling.LANCZOS), (1 * 4, 0))
        arr4 = fill_1x_mask_gaps(np.array(im4), m16, scale=4, radius=8)
        im4 = Image.fromarray(arr4, "RGBA")

        frames_4x.append(im4)
        frames_8x.append(im8)

    return (frames_4x[0], frames_8x[0]), (frames_4x[1], frames_8x[1])


def _extract_cell_rgba(cell_rgb: np.ndarray) -> Image.Image:
    """Cut a gothic bone figure cleanly off pure #000000 black with anti-aliased de-haloed edges."""
    c = cell_rgb.astype(np.float32)
    lum = c[:, :, :3].max(axis=2)
    m = lum > 14.0
    ys, xs = np.where(m)
    sub = c[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    s_lum = sub[:, :, :3].max(axis=2)
    alpha = np.clip((s_lum - 8.0) / 22.0, 0.0, 1.0)
    # Gentle de-premultiply on soft perimeter pixels so dark-black fringes don't appear over light backgrounds
    de_div = np.where(alpha > 0.08, np.maximum(alpha, 0.38), 1.0)
    rgb = np.where(alpha[:, :, None] < 0.99, np.clip(sub[:, :, :3] / de_div[:, :, None], 0, 255), sub[:, :, :3])
    rgba = np.zeros((sub.shape[0], sub.shape[1], 4), dtype=np.uint8)
    rgba[:, :, :3] = np.clip(rgb, 0, 255).astype(np.uint8)
    rgba[:, :, 3] = np.clip(alpha * 255.0, 0, 255).astype(np.uint8)
    return Image.fromarray(rgba, "RGBA")


def extract_skeleton_poses() -> tuple:
    """Extract all 8 poses at full ~620px height from skeleton_8x_part1_hd_1795331543840.jpg and
    skeleton_8x_part2_hd_1795331546225.jpg, registered pixel-exact to each 96x96 native reference bbox.
    Returns (pure_poses_4x, pure_poses_8x, tiled_poses_4x).
    """
    p1 = np.array(Image.open(BRAIN / "skeleton_8x_part1_hd_1795331543840.jpg").convert("RGB"))
    p2 = np.array(Image.open(BRAIN / "skeleton_8x_part2_hd_1795331546225.jpg").convert("RGB"))
    # p1: 1376x768 split into 3 vertical columns (Gehen_01, Gehen_02, Wurf_01_Ausholen)
    # p2: 1376x768 split into 3 columns: Wurf_02_Werfen, Wurf_03_Ausklang, and 3 stacked bones on right
    w1, h1 = p1.shape[1], p1.shape[0]
    w2, h2 = p2.shape[1], p2.shape[0]
    crops = {
        "Skelett_Gehen_01.png":          p1[8:h1 - 8, 8:w1 // 3 - 4],
        "Skelett_Gehen_02.png":          p1[8:h1 - 8, w1 // 3 + 4:(2 * w1) // 3 - 4],
        "Skelett_Wurf_01_Ausholen.png":  p1[8:h1 - 8, (2 * w1) // 3 + 4:w1 - 8],
        "Skelett_Wurf_02_Werfen.png":    p2[8:h2 - 8, 8:w2 // 3 - 4],
        "Skelett_Wurf_03_Ausklang.png":  p2[8:h2 - 8, w2 // 3 + 4:(2 * w2) // 3 - 4],
        "Knochen_Drehung_01.png":        p2[8:int(h2 * 0.37), (2 * w2) // 3 + 8:w2 - 8],
        "Knochen_Drehung_02.png":        p2[int(h2 * 0.37):int(h2 * 0.69), (2 * w2) // 3 + 8:w2 - 8],
        "Knochen_Drehung_03.png":        p2[int(h2 * 0.69):h2 - 8, (2 * w2) // 3 + 8:w2 - 8],
    }

    pure_4x, pure_8x = {}, {}
    for fname, cell_rgb in crops.items():
        crop_im = _extract_cell_rgba(cell_rgb)
        ref_1x = np.array(Image.open(SKEL_ALL_DIR / "references" / fname).convert("RGBA"))
        ry, rx = np.where(ref_1x[:, :, 3] > 0)
        nx0, ny0, nx1, ny1 = int(rx.min()), int(ry.min()), int(rx.max()) + 1, int(ry.max()) + 1
        nw, nh = nx1 - nx0, ny1 - ny0

        im8 = Image.new("RGBA", (96 * 8, 96 * 8), (0, 0, 0, 0))
        im8.paste(crop_im.resize((nw * 8, nh * 8), Image.Resampling.LANCZOS), (nx0 * 8, ny0 * 8))

        im4 = Image.new("RGBA", (96 * 4, 96 * 4), (0, 0, 0, 0))
        im4.paste(crop_im.resize((nw * 4, nh * 4), Image.Resampling.LANCZOS), (nx0 * 4, ny0 * 4))

        pure_4x[fname] = im4
        pure_8x[fname] = im8

    # For tile-mode (pack.tiles) ONLY, harmonize shared 8x8 tiles so bones match seamlessly across poses
    tiled_4x = {k: v.copy() for k, v in pure_4x.items()}
    sc = 4
    g1 = np.array(tiled_4x["Skelett_Gehen_01.png"])
    g2 = np.array(tiled_4x["Skelett_Gehen_02.png"])
    g2[25 * sc:33 * sc, 37 * sc:53 * sc] = g1[25 * sc:33 * sc, 37 * sc:53 * sc]
    g2[33 * sc:41 * sc, 37 * sc:45 * sc] = g1[33 * sc:41 * sc, 37 * sc:45 * sc]
    tiled_4x["Skelett_Gehen_02.png"] = Image.fromarray(g2, "RGBA")

    for w_name in ["Skelett_Wurf_01_Ausholen.png", "Skelett_Wurf_02_Werfen.png", "Skelett_Wurf_03_Ausklang.png"]:
        wa = np.array(tiled_4x[w_name])
        wa[57 * sc:73 * sc, 29 * sc:61 * sc] = g1[57 * sc:73 * sc, 29 * sc:61 * sc]
        tiled_4x[w_name] = Image.fromarray(wa, "RGBA")

    w1 = np.array(tiled_4x["Skelett_Wurf_01_Ausholen.png"])
    w2 = np.array(tiled_4x["Skelett_Wurf_02_Werfen.png"])
    w2[49 * sc:57 * sc, 45 * sc:61 * sc] = w1[49 * sc:57 * sc, 45 * sc:61 * sc]
    tiled_4x["Skelett_Wurf_02_Werfen.png"] = Image.fromarray(w2, "RGBA")

    return pure_4x, pure_8x, tiled_4x


def main():
    room_assets = [(i, Assets(ROOT / f"artwork-local/level-editor/rooms/{i:02d}")) for i in range(8)]
    room_cgrams = [a.colors for _, a in room_assets]
    a5 = room_assets[5][1]

    # 1. Update Cross Boomerang 1 & 2 in Items/02_Waffen
    dir_weapons = ITEMS_DIR / "02_Waffen"
    (bum1_4x, bum1_8x), (bum2_4x, bum2_8x) = extract_boomerang_frames(a5.vram)
    bum1_4x.save(dir_weapons / "Waffe_Kreuz_Bumerang_1_HD_4x.png")
    bum1_8x.save(dir_weapons / "Waffe_Kreuz_Bumerang_1_HD_8x.png")
    bum2_4x.save(dir_weapons / "Waffe_Kreuz_Bumerang_2_HD_4x.png")
    bum2_8x.save(dir_weapons / "Waffe_Kreuz_Bumerang_2_HD_8x.png")

    # 2. Extract & save true-8x HD Skeleton + Thrown Bone poses
    poses_4x, poses_8x, tiled_4x = extract_skeleton_poses()
    skel_hd_dir = GEGNER_DIR / "HD_4x_8x"
    skel_hd_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(BRAIN / "skeleton_8x_part1_hd_1795331543840.jpg", skel_hd_dir / "Skelett_8x_Teil1_Sheet_HD.jpg")
    shutil.copy2(BRAIN / "skeleton_8x_part2_hd_1795331546225.jpg", skel_hd_dir / "Skelett_8x_Teil2_Sheet_HD.jpg")

    # Backup original 387x387 nearest-neighbor artwork folders before updating
    for w_dir in [SKEL_ALL_DIR / "artwork", SKEL_01_DIR / "artwork"]:
        bak = w_dir.parent / "artwork_backup_1x"
        if not bak.exists() and w_dir.exists():
            shutil.copytree(w_dir, bak)

    for fname, im4 in poses_4x.items():
        im8 = poses_8x[fname]
        stem = Path(fname).stem
        im4.save(skel_hd_dir / f"{stem}_HD_4x.png")
        im8.save(skel_hd_dir / f"{stem}_HD_8x.png")
        # Save true 8x (768x768) whole-pose PNG into 02_Skelette_Alle_Aktionen/artwork/!
        # Wait: keep 02_Skelette_Alle_Aktionen/artwork/ at 387x387 for Workshop compatibility,
        # AND write a dedicated runtime enemy_pack 'hd-skeleton' at FULL 768x768 (8x)!
        im387 = im8.resize((387, 387), Image.Resampling.LANCZOS)
        im387.save(SKEL_ALL_DIR / "artwork" / fname)

    # Also update 01_Skelette/artwork/Skelett_Schritt_01.png & 02.png
    if (SKEL_01_DIR / "artwork").exists():
        poses_8x["Skelett_Gehen_01.png"].resize((387, 387), Image.Resampling.LANCZOS).save(
            SKEL_01_DIR / "artwork" / "Skelett_Schritt_01.png"
        )
        poses_8x["Skelett_Gehen_02.png"].resize((387, 387), Image.Resampling.LANCZOS).save(
            SKEL_01_DIR / "artwork" / "Skelett_Schritt_02.png"
        )

    # Build clean standalone 8x runtime enemy_pack ('hd-skeleton') under artwork-local/enemy-packs-hd/hd-skeleton
    ep_out = ROOT / "artwork-local/enemy-packs-hd/hd-skeleton"
    if ep_out.exists():
        shutil.rmtree(ep_out)
    ep_out.mkdir(parents=True, exist_ok=True)
    proj_meta = json.loads((SKEL_ALL_DIR / "project.json").read_text(encoding="utf-8"))
    # Keep only whole-pose Skeleton & Thrown Bone frames (zero tile-component overlaps, pure 768x768 8x smooth silhouettes!)
    clean_frames = []
    for f in proj_meta["frames"]:
        img = f.get("image", "")
        if not f.get("component") and img in poses_8x:
            clean_frames.append({
                "id": f["id"],
                "actor_type": f["actor_type"],
                "pose": f["pose"],
                "display_size": f["display_size"],
                "anchor": f["anchor"],
                "image": img,
            })
    (ep_out / "enemies.json").write_text(
        json.dumps({"version": 1, "name": "HD Skeleton 8x (Smooth Whole-Pose)", "frames": clean_frames}, indent=2) + "\n",
        encoding="utf-8",
    )
    for fname, im8 in poses_8x.items():
        im8.save(ep_out / fname)
    print(f"Built true-8x enemy pack 'hd-skeleton' ({len(clean_frames)} whole-pose entries, 768x768) at {ep_out}")

    # 3. Slice all 58 8x8 (32x32 at 4x) VRAM OBJ tiles for the Skeleton & Thrown Bone
    #    plus the 8 8x8 tiles of the new 2-frame Holy Cross Boomerang!
    # Build RGB -> (tid, pal_idx, hf, vf, px_indices) DB from rooms 00..07 VRAM
    tile_rgb_db = {}
    for r_idx, a in room_assets:
        for tid in range(512):
            addr = 0x6000 + tid * 16
            px = []
            for y in range(8):
                w0, w1 = int(a.vram[addr + y]), int(a.vram[addr + y + 8])
                for b in range(7, -1, -1):
                    px.append(((w0 >> b) & 1) | (((w0 >> (b + 8)) & 1) << 1) | (((w1 >> b) & 1) << 2) | (((w1 >> (b + 8)) & 1) << 3))
            if not any(px):
                continue
            for pal_idx in range(8):
                cols = [int(a.colors[128 + pal_idx * 16 + c]) for c in range(16)]
                rgba = hd.TileInfo(4, cols, px).rgba()
                for hf in (0, 1):
                    for vf in (0, 1):
                        t = rgba[:, ::-1] if hf else rgba
                        if vf:
                            t = t[::-1, :]
                        tile_rgb_db.setdefault(t.tobytes(), []).append((tid, pal_idx, hf, vf, px))

    BODY_BONE_REFS = [
        ("Knochen_Drehung_01.png", ["Knochen_Drehung_01.png"]),
        ("Knochen_Drehung_02.png", ["Knochen_Drehung_02.png"]),
        ("Knochen_Drehung_03.png", ["Knochen_Drehung_03.png"]),
        ("Skelett_Gehen_01.png", [f"Skelett_Gehen_01_Teil_0{i}.png" for i in range(4)]),
        ("Skelett_Gehen_02.png", [f"Skelett_Gehen_02_Teil_0{i}.png" for i in range(3)]),
        ("Skelett_Wurf_01_Ausholen.png", [f"Skelett_Wurf_01_Ausholen_Teil_0{i}.png" for i in range(3)]),
        ("Skelett_Wurf_02_Werfen.png", [f"Skelett_Wurf_02_Werfen_Teil_0{i}.png" for i in range(5)]),
        ("Skelett_Wurf_03_Ausklang.png", ["Skelett_Wurf_03_Ausklang_Teil_00.png", "Skelett_Wurf_03_Ausklang_Teil_03.png"]),
    ]

    skel_tiles_4x = {}
    for whole_name, part_names in BODY_BONE_REFS:
        whole_4x_arr = np.array(tiled_4x[whole_name], dtype=np.uint8)  # (384, 384, 4)
        whole_8x_arr = np.array(poses_8x[whole_name], dtype=np.uint8)  # (768, 768, 4)
        for pn in part_names:
            ref_im = Image.open(SKEL_ALL_DIR / "references" / pn).convert("RGBA")
            arr = np.array(ref_im)
            m = arr[:, :, 3] > 0
            ys, xs = np.where(m)
            for y0 in range(max(0, int(ys.min()) - 8), int(ys.min()) + 1):
                for x0 in range(max(0, int(xs.min()) - 8), int(xs.min()) + 1):
                    hits = []
                    for qy in range(2):
                        for qx in range(2):
                            sub = arr[y0 + qy * 8:y0 + (qy + 1) * 8, x0 + qx * 8:x0 + (qx + 1) * 8]
                            if sub.shape != (8, 8, 4) or not (sub[:, :, 3] > 0).any():
                                continue
                            if sub.tobytes() in tile_rgb_db:
                                hits.append((x0 + qx * 8, y0 + qy * 8, tile_rgb_db[sub.tobytes()][0]))
                    cov = sum((arr[hy:hy + 8, hx:hx + 8, 3] > 0).sum() for hx, hy, _ in hits)
                    if cov == m.sum() and len(hits) > 0:
                        # Also save updated _Teil_XX.png (387x387) into 02_Skelette_Alle_Aktionen/artwork/!
                        if "_Teil_" in pn:
                            part_8x = np.zeros_like(whole_8x_arr)
                            for hx, hy, _ in hits:
                                part_8x[hy * 8:(hy + 8) * 8, hx * 8:(hx + 8) * 8] = whole_8x_arr[
                                    hy * 8:(hy + 8) * 8, hx * 8:(hx + 8) * 8
                                ]
                            Image.fromarray(part_8x, "RGBA").resize((387, 387), Image.Resampling.LANCZOS).save(
                                SKEL_ALL_DIR / "artwork" / pn
                            )
                        for hx, hy, (tid, pal_idx, hf, vf, px_list) in hits:
                            m1x_cell = arr[hy:hy + 8, hx:hx + 8, 3] > 0
                            tile_32 = whole_4x_arr[hy * 4:(hy + 8) * 4, hx * 4:(hx + 8) * 4].copy()
                            # Ensure 100% of the 1x bone silhouette inside this 8x8 cell has opaque HD bone pixels
                            tile_32 = fill_1x_mask_gaps(tile_32, m1x_cell, scale=4, radius=10)
                            # Un-flip if the reference cell was drawn with hflip or vflip!
                            if vf:
                                tile_32 = tile_32[::-1, :].copy()
                            if hf:
                                tile_32 = tile_32[:, ::-1].copy()
                            # For Wurf_03_Ausklang_Teil_03 (outstretched arm overlapping skull at x=37..46),
                            # mask tile_32 by a softly dilated 1x part mask so skull pixels don't duplicate on the arm tile!
                            if pn == "Skelett_Wurf_03_Ausklang_Teil_03.png":
                                m1x = m1x_cell.astype(np.uint8) * 255
                                m32 = Image.fromarray(m1x, "L").resize((32, 32), Image.Resampling.NEAREST)
                                m32 = np.array(m32.filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.GaussianBlur(1.0)), dtype=np.float32) / 255.0
                                if vf:
                                    m32 = m32[::-1, :]
                                if hf:
                                    m32 = m32[:, ::-1]
                                tile_32[:, :, 3] = np.clip(tile_32[:, :, 3].astype(np.float32) * m32, 0, 255).astype(np.uint8)
                            for cg in room_cgrams:
                                for p_i in [pal_idx, 1, 3, 4]:
                                    cols = [int(cg[128 + p_i * 16 + c]) for c in range(16)]
                                    key = fnv_key(4, px_list, cols)
                                    if key not in skel_tiles_4x:
                                        skel_tiles_4x[key] = tile_32
                        break
                else:
                    continue
                break

    # Build updated Cross Boomerang tile keys (Frame 1: [0x44,0x45,0x54,0x55], Frame 2: [0x46,0x47,0x56,0x57])
    bum_tiles_4x = {}
    for im4, tids in [(bum1_4x, [0x44, 0x45, 0x54, 0x55]), (bum2_4x, [0x46, 0x47, 0x56, 0x57])]:
        b_arr = np.array(im4, dtype=np.uint8)
        for idx, tid in enumerate(tids):
            px_idx = decode_obj_indices(a5.vram, tid)
            if not px_idx.any():
                continue
            px_list = px_idx.ravel().tolist()
            qx, qy = idx % 2, idx // 2
            tile_32 = b_arr[qy * 32:(qy + 1) * 32, qx * 32:(qx + 1) * 32].copy()
            for cg in room_cgrams:
                for p_i in [1, 3]:
                    cols = [int(cg[128 + p_i * 16 + c]) for c in range(16)]
                    key = fnv_key(4, px_list, cols)
                    bum_tiles_4x[key] = tile_32

    print(f"Built {len(bum_tiles_4x)} updated Boomerang tile keys and {len(skel_tiles_4x)} Skeleton + Bone tile keys!")

    # 4. Build v21 pack: stage-01-user-grid-v21-8x-skeleton
    v19_pack = ROOT / "artwork-local/stage01-v19-2026-11-22/stage-01-user-grid-v19-hud-items"
    v21_root = ROOT / "artwork-local/stage01-v21-2026-11-22"
    v21_pack = v21_root / "stage-01-user-grid-v21-8x-skeleton"
    if v21_root.exists():
        shutil.rmtree(v21_root)
    shutil.copytree(v19_pack, v21_pack)

    add_shared_keys = set(bum_tiles_4x.keys()) | set(skel_tiles_4x.keys())

    for sc in ["entrance", "a02", "a03", "a04", "a05", "a06", "a07", "a08"]:
        sc_dir = v21_pack / sc
        meta = json.loads((sc_dir / "pack.json").read_text(encoding="utf-8"))
        _, _, existing_tiles = hd.load_pack(sc_dir)
        for old_at in sc_dir.glob("atlas_*.png"):
            old_at.unlink()

        merged_tiles = {**existing_tiles, **skel_tiles_4x, **bum_tiles_4x}
        tmp_dir = v21_root / f"_tmp_{sc}"
        tmp_dir.mkdir(parents=True, exist_ok=True)
        write_pack(merged_tiles, tmp_dir, SCALE)
        tmp_meta = json.loads((tmp_dir / "pack.json").read_text(encoding="utf-8"))
        for at_file in tmp_dir.glob("atlas_*.png"):
            shutil.copy2(at_file, sc_dir / at_file.name)
        shutil.rmtree(tmp_dir)

        meta["atlas_size"] = tmp_meta["atlas_size"]
        meta["tiles"] = tmp_meta["tiles"]
        old_shared = set(meta.get("shared_objects", []))
        meta["shared_objects"] = sorted(old_shared | add_shared_keys)
        (sc_dir / "pack.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
        print(f"Updated scene {sc:8s}: total_tiles={len(merged_tiles)}, shared_objects={len(meta['shared_objects'])}")

    top_meta = json.loads((v21_pack / "pack.json").read_text(encoding="utf-8"))
    top_meta["name"] = "Stage 01 HD v21: Complete A01-A08 + HD HUD, Holy Cross Boomerang, Weapons, Candles, Items & 8x Skeleton"
    (v21_pack / "pack.json").write_text(json.dumps(top_meta, indent=2) + "\n", encoding="utf-8")
    print("Successfully built:", v21_pack)


if __name__ == "__main__":
    main()
