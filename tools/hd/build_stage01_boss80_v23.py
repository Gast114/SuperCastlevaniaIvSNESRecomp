"""Build 8x HD remasters for Stage 01 A08 Boss Rowdain (0x80/0x04/0x03) from the local FLUX.2 Klein renders:
- 4 Gallop Stride Poses (0x04: a8a3, a8fc, a955, a9ae)
- 2 Articulated Horse Skulls (0x80: ad7d closed, ad82 roaring)
- 2 Fireball Projectiles (0x03: b02e, b033) + glowing lance ember spark (0x04: b029)

Outputs:
1. Named 4x (384x384) & 8x (768x768) PNGs in 'Assets (ausgeschnitten)/Gegner/HD_4x_8x/'
2. Merges all 9 Rowdain entries into unified Stage 01 8x enemy pack 'artwork-local/enemy-packs-hd/hd-stage01'
"""
import json
import shutil
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(r"D:\Super Castlevania IV Recomp\SuperCastlevaniaIvSNESRecomp")
ASSETS_ROOT = Path(r"D:\Super Castlevania IV Recomp\Assets (ausgeschnitten)")
GEGNER_HD = ASSETS_ROOT / "Gegner" / "HD_4x_8x"
REF_DIR = Path(r"C:\Users\Gaming\.gemini\antigravity\brain\0e3d1566-2f3c-4183-be49-fad33ce3d4a9\scratch\boss80_ref")


def extract_clean_rgba(cell_rgb: np.ndarray, lum_thresh: float = 14.0, soft_lo: float = 7.0, soft_span: float = 22.0) -> Image.Image:
    c = cell_rgb.astype(np.float32)
    lum = c[:, :, :3].max(axis=2)
    m = lum > lum_thresh
    ys, xs = np.where(m)
    if ys.size == 0:
        raise ValueError("Empty sprite crop!")
    sub = c[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    s_lum = sub[:, :, :3].max(axis=2)
    alpha = np.clip((s_lum - soft_lo) / soft_span, 0.0, 1.0)
    de_div = np.where(alpha > 0.08, np.maximum(alpha, 0.38), 1.0)
    rgb = np.where(alpha[:, :, None] < 0.99, np.clip(sub[:, :, :3] / de_div[:, :, None], 0, 255), sub[:, :, :3])
    rgba = np.zeros((sub.shape[0], sub.shape[1], 4), dtype=np.uint8)
    rgba[:, :, :3] = np.clip(rgb, 0, 255).astype(np.uint8)
    rgba[:, :, 3] = np.clip(alpha * 255.0, 0, 255).astype(np.uint8)
    return Image.fromarray(rgba, "RGBA")


def fill_skull_eye_sockets(skull_im: Image.Image) -> Image.Image:
    """Make enclosed dark regions (eye sockets, nostril, deep jaw cavity) opaque #080707 instead of transparent,
    so background walls or neck vertebrae never peek through the skull's dark eye socket.
    """
    from collections import deque
    arr = np.array(skull_im)
    h, w, _ = arr.shape
    trans = arr[:, :, 3] < 40
    # Flood fill transparent pixels reachable from image border (exterior background)
    ext = np.zeros((h, w), dtype=bool)
    q = deque()
    for x in range(w):
        for y in (0, h - 1):
            if trans[y, x] and not ext[y, x]:
                ext[y, x] = True
                q.append((y, x))
    for y in range(h):
        for x in (0, w - 1):
            if trans[y, x] and not ext[y, x]:
                ext[y, x] = True
                q.append((y, x))
    while q:
        cy, cx = q.popleft()
        for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            ny, nx = cy + dy, cx + dx
            if 0 <= ny < h and 0 <= nx < w and trans[ny, nx] and not ext[ny, nx]:
                ext[ny, nx] = True
                q.append((ny, nx))
    # Any transparent pixel NOT connected to exterior is an enclosed eye socket / nostril / mouth hole!
    holes = trans & (~ext)
    arr[holes] = [8, 7, 7, 255]
    # Also ensure low-alpha dark pixels already inside skull bounds (>=5px away from exterior) stay solid
    return Image.fromarray(arr, "RGBA")


def make_bone_vertebra_crop(skull_img: Image.Image) -> Image.Image:
    """Create a tight gothic carved bone vertebra joint fitting cleanly inside 5x5 native bounds
    with notched bone ridges and marrow shadow (no smooth bead look).
    """
    sz = 96
    yy, xx = np.mgrid[0:sz, 0:sz].astype(np.float32)
    dx = (xx - 47.5) / 42.0
    dy = (yy - 47.5) / 42.0
    # Slight vertebra hourglass waist horizontally & bumpy condyle ridges at top/bottom
    pinch = 1.0 - 0.16 * np.exp(-((dx * 2.2) ** 2)) + 0.12 * np.exp(-(((dx + 0.45) * 3.0) ** 2))
    dist = np.sqrt((dx / 0.96) ** 2 + (dy / (0.86 * pinch)) ** 2)
    h_field = np.clip(1.0 - dist * dist, 0.0, 1.0)
    nz = np.sqrt(h_field)
    light = np.clip(-0.42 * dx - 0.52 * dy + 0.72 * nz, 0.12, 1.0)
    # Carve sharp anatomical vertebral fissures and bone grain
    crevice = 1.0 - 0.42 * np.exp(-((dy + 0.18) * 5.2) ** 2) - 0.25 * np.exp(-((dx - 0.22) * 5.0) ** 2)
    grain = 1.0 - 0.10 * np.sin(xx * 0.48 - yy * 0.35)
    shade = np.clip(light * crevice * grain, 0.0, 1.0)
    r_ch = 38.0 + 198.0 * shade
    g_ch = 35.0 + 193.0 * shade
    b_ch = 32.0 + 184.0 * shade
    rim = np.clip((0.98 - dist) * 5.5, 0.0, 1.0)
    dark_edge = np.where(rim < 0.55, 0.25 + 1.35 * rim, 1.0)
    alpha = np.where(dist <= 0.97, np.clip((0.97 - dist) * 20.0, 0.0, 1.0) * 255.0, 0.0)
    out = np.zeros((sz, sz, 4), dtype=np.uint8)
    out[:, :, 0] = np.clip(r_ch * dark_edge, 0, 255).astype(np.uint8)
    out[:, :, 1] = np.clip(g_ch * dark_edge, 0, 255).astype(np.uint8)
    out[:, :, 2] = np.clip(b_ch * dark_edge, 0, 255).astype(np.uint8)
    out[:, :, 3] = np.clip(alpha, 0, 255).astype(np.uint8)
    ys, xs = np.where(out[:, :, 3] > 24)
    return Image.fromarray(out[ys.min():ys.max() + 1, xs.min():xs.max() + 1], "RGBA")


def register_to_reference(crop_im: Image.Image, ref_path: Path, pad_scale: float = 1.0) -> tuple:
    """Register crop_im pixel-exact onto the native reference canvas (96x96 or 256x256!) at 4x and 8x."""
    ref_1x = np.array(Image.open(ref_path).convert("RGBA"))
    ref_h, ref_w = ref_1x.shape[:2]
    ry, rx = np.where(ref_1x[:, :, 3] > 0)
    nx0, ny0, nx1, ny1 = int(rx.min()), int(ry.min()), int(rx.max()) + 1, int(ry.max()) + 1
    nw, nh = nx1 - nx0, ny1 - ny0

    im8 = Image.new("RGBA", (ref_w * 8, ref_h * 8), (0, 0, 0, 0))
    tw8, th8 = int(round(nw * 8 * pad_scale)), int(round(nh * 8 * pad_scale))
    ox8 = nx0 * 8 - (tw8 - nw * 8) // 2
    oy8 = ny0 * 8 - (th8 - nh * 8) // 2
    im8.paste(crop_im.resize((tw8, th8), Image.Resampling.LANCZOS), (ox8, oy8))

    im4 = Image.new("RGBA", (ref_w * 4, ref_h * 4), (0, 0, 0, 0))
    tw4, th4 = int(round(nw * 4 * pad_scale)), int(round(nh * 4 * pad_scale))
    ox4 = nx0 * 4 - (tw4 - nw * 4) // 2
    oy4 = ny0 * 4 - (th4 - nh * 4) // 2
    im4.paste(crop_im.resize((tw4, th4), Image.Resampling.LANCZOS), (ox4, oy4))
    return im4, im8


def main():
    GEGNER_HD.mkdir(parents=True, exist_ok=True)
    g2x2_im = Image.open(REF_DIR / "rowdain_2x2_gallop_hd_v2.png").convert("RGB")
    sk_im = Image.open(REF_DIR / "rowdain_skulls_fire_hd_v2.png").convert("RGB")

    shutil.copy2(REF_DIR / "rowdain_2x2_gallop_hd_v2.png", GEGNER_HD / "Boss_Rowdain_Galopp_Sheet_HD.png")
    shutil.copy2(REF_DIR / "rowdain_skulls_fire_hd_v2.png", GEGNER_HD / "Boss_Rowdain_Schaedel_Feuer_Sheet_HD.png")

    g_arr = np.array(g2x2_im)
    s_arr = np.array(sk_im)

    # Extract 4 gallop body quadrants (each 384x384 inside 768x768)
    quads = [
        g_arr[4:380, 4:380].copy(),     # Pose 1: a8a3
        g_arr[4:380, 388:764].copy(),   # Pose 2: a8fc
        g_arr[388:764, 4:380].copy(),   # Pose 3: a955
        g_arr[388:764, 388:764].copy(), # Pose 4: a9ae
    ]
    # Remove tiny residual wooden stub in Pose 1 right above the wrist (x~130..160, y~175..205 relative to quad 0)
    # Clean ONLY the unwanted diagonal cross-stick on Pose 1 (y~165..248) using exact-aligned (dx=9, dy=-2) Pose 4 graft!
    from PIL import ImageFilter
    q0_f = quads[0].astype(np.float32)
    q3_f = np.roll(np.roll(quads[3].astype(np.float32), -2, axis=0), 9, axis=1)
    h_q, w_q, _ = q0_f.shape
    yy_q, xx_q = np.mgrid[0:h_q, 0:w_q]
    # Narrow capsule mask along ONLY the cross-stick from (142, 170) to (234, 245) in quad-0 coords (minus 4px margin = [4:380])
    # In quads[0] coords (offset -4 from full 384 quad): stick runs ~(138, 166) -> (230, 241)
    vx, vy = 230.0 - 138.0, 241.0 - 166.0
    t_proj = np.clip(((xx_q - 138.0) * vx + (yy_q - 166.0) * vy) / (vx * vx + vy * vy), 0.0, 1.0)
    px_c = 138.0 + t_proj * vx
    py_c = 166.0 + t_proj * vy
    dist_c = np.hypot(xx_q - px_c, yy_q - py_c)
    hard_m = (dist_c < 9.5).astype(np.uint8) * 255
    soft_m = np.array(Image.fromarray(hard_m, "L").filter(ImageFilter.GaussianBlur(2.5)), dtype=np.float32) / 255.0
    q0_blend = np.clip(q0_f * (1.0 - soft_m[:, :, None]) + q3_f * soft_m[:, :, None], 0, 255).astype(np.uint8)
    quads[0] = q0_blend

    body_crops = [extract_clean_rgba(q) for q in quads]
    skull_closed = fill_skull_eye_sockets(extract_clean_rgba(s_arr[8:504, 8:250]))
    skull_roar = fill_skull_eye_sockets(extract_clean_rgba(s_arr[8:504, 250:516]))
    fire_1 = extract_clean_rgba(s_arr[8:504, 516:760], lum_thresh=18.0, soft_lo=10.0, soft_span=28.0)
    fire_2 = fire_1.resize((int(fire_1.width * 0.92), int(fire_1.height * 0.92)), Image.Resampling.LANCZOS)
    vertebra_crop = make_bone_vertebra_crop(skull_closed)

    SPEC = [
        ("Boss_Rowdain_Galopp_01",     body_crops[0], "gegner-0004_pose-a8a3_90ede8810e6541a9.png", 1.0),
        ("Boss_Rowdain_Galopp_02",     body_crops[1], "gegner-0004_pose-a8fc_66f8509b5e4bcc12.png", 1.0),
        ("Boss_Rowdain_Galopp_03",     body_crops[2], "gegner-0004_pose-a955_ca89b15d5a35feee.png", 1.0),
        ("Boss_Rowdain_Galopp_04",     body_crops[3], "gegner-0004_pose-a9ae_2a05d7cc7bbcb21b.png", 1.0),
        ("Boss_Rowdain_Schaedel_Zu",   skull_closed,  "gegner-0080_pose-ad7d_dae7a8cf5949cf61.png", 1.0),
        ("Boss_Rowdain_Schaedel_Auf",  skull_roar,    "gegner-0080_pose-ad82_913d5810c123ce3b.png", 1.0),
        ("Boss_Rowdain_Feuerball_01",  fire_1,        "gegner-0003_pose-b02e_aa24d019648fe6c9.png", 1.0),
        ("Boss_Rowdain_Feuerball_02",  fire_2,        "gegner-0003_pose-b033_86ddc6ec6a99bf98.png", 1.0),
        ("Boss_Rowdain_Halswirbel_01", vertebra_crop, "gegner-0004_pose-b029_87a5cd9fc1279166.png", 1.0),
    ]

    imgs_8x = {}
    for stem, crop_im, ref_fname, ps in SPEC:
        im4, im8 = register_to_reference(crop_im, REF_DIR / ref_fname, pad_scale=ps)
        im4.save(GEGNER_HD / f"{stem}_HD_4x.png")
        im8.save(GEGNER_HD / f"{stem}_HD_8x.png")
        imgs_8x[ref_fname[:-4]] = (stem, im8)
        print(f"Exported {stem}_HD_4x/8x.png cleanly aligned to {ref_fname}")

    # Merge into unified Stage 01 8x enemy pack 'hd-stage01'
    stage_ep = ROOT / "artwork-local/enemy-packs-hd/hd-stage01"
    ep_manifest = json.loads((stage_ep / "enemies.json").read_text(encoding="utf-8"))
    frames_by_id = {f["id"]: f for f in ep_manifest["frames"]}

    cap_manifest = json.loads((REF_DIR / "captured_boss80.json").read_text(encoding="utf-8"))
    cap_lookup = {f["id"]: f for f in cap_manifest["frames"]}

    for gid, (stem, im8) in imgs_8x.items():
        c = cap_lookup[gid]
        out_name = f"{stem}_HD_8x.png"
        im8.save(stage_ep / out_name)
        frames_by_id[gid] = {
            "id": gid,
            "actor_type": c["actor_type"],
            "pose": c["pose"],
            "display_size": c["display_size"],
            "anchor": c["anchor"],
            "image": out_name,
        }

    final_frames = sorted(frames_by_id.values(), key=lambda x: (x["actor_type"], x["pose"], x["id"]))
    (stage_ep / "enemies.json").write_text(
        json.dumps({"version": 1, "name": "Stage 01 HD Enemies & Boss Rowdain (8x Whole-Pose)", "frames": final_frames}, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Updated 'hd-stage01' with {len(final_frames)} total entries (including Boss Rowdain)!")


if __name__ == "__main__":
    main()
