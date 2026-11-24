"""Build full 8x HD remasters for the remaining Stage 01 enemies:
- Fledermaus (0x0c & 0x4e): 3 flying poses + 1 hanging sleeping pose
- Knochensaeule / Double Horse-Skull Pillar (0x0b): ivory normal + crimson charge + 3 fireball frames (0x48)
- Decken-Schleimmonster A06 (0x32): thorny pale-green tentacle crawler
- Fliegender Pferdekopf (0x6f & 0x71): 3 haunted fiery-mane animation frames

Outputs:
1. Named 4x (384x384) & 8x (768x768) PNGs in 'Assets (ausgeschnitten)/Gegner/HD_4x_8x/'
2. Unified runtime 8x enemy pack 'artwork-local/enemy-packs-hd/hd-stage01' merging
   the 8x Skeleton + Bone poses with all 4 new Stage 01 enemies!
"""
import json
import shutil
import sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageEnhance

ROOT = Path(r"D:\Super Castlevania IV Recomp\SuperCastlevaniaIvSNESRecomp")
ASSETS_ROOT = Path(r"D:\Super Castlevania IV Recomp\Assets (ausgeschnitten)")
GEGNER_HD = ASSETS_ROOT / "Gegner" / "HD_4x_8x"
REF_DIR = Path(r"C:\Users\Gaming\.gemini\antigravity\brain\0e3d1566-2f3c-4183-be49-fad33ce3d4a9\scratch\stage01_enemies_ref")
BRAIN = Path(r"C:\Users\Gaming\.gemini\antigravity\brain\0e3d1566-2f3c-4183-be49-fad33ce3d4a9")


def extract_clean_rgba(cell_rgb: np.ndarray, lum_thresh: float = 14.0, soft_lo: float = 7.0, soft_span: float = 22.0) -> Image.Image:
    """Cut a dark-gothic sprite off pure #000000 black with anti-aliased de-haloed alpha."""
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


def trim_hanging_bat_branch(cell_rgb: np.ndarray) -> Image.Image:
    """Extract the hanging bat cleanly while removing the wide horizontal wooden perch bar at the very top."""
    im = extract_clean_rgba(cell_rgb)
    arr = np.array(im)
    h, w, _ = arr.shape
    # The perch bar sits across the top ~10% of the crop extending left/right past the claws
    top_band = max(1, int(h * 0.11))
    # Inside the top band, keep only the central claws (columns near the two vertical wing edges, x in [w*0.26..w*0.74])
    arr[:top_band, :int(w * 0.25), 3] = 0
    arr[:top_band, int(w * 0.75):, 3] = 0
    # Fade the thin gap right between the two feet at the top edge
    arr[:max(1, int(h * 0.06)), int(w * 0.38):int(w * 0.62), 3] = 0
    ys, xs = np.where(arr[:, :, 3] > 20)
    return Image.fromarray(arr[ys.min():ys.max() + 1, xs.min():xs.max() + 1], "RGBA")


def register_to_reference(crop_im: Image.Image, ref_path: Path) -> tuple:
    """Register crop_im pixel-exact onto the 96x96 native reference bbox at 4x (384x384) and 8x (768x768)."""
    ref_1x = np.array(Image.open(ref_path).convert("RGBA"))
    ry, rx = np.where(ref_1x[:, :, 3] > 0)
    nx0, ny0, nx1, ny1 = int(rx.min()), int(ry.min()), int(rx.max()) + 1, int(ry.max()) + 1
    nw, nh = nx1 - nx0, ny1 - ny0

    im8 = Image.new("RGBA", (96 * 8, 96 * 8), (0, 0, 0, 0))
    im8.paste(crop_im.resize((nw * 8, nh * 8), Image.Resampling.LANCZOS), (nx0 * 8, ny0 * 8))

    im4 = Image.new("RGBA", (96 * 4, 96 * 4), (0, 0, 0, 0))
    im4.paste(crop_im.resize((nw * 4, nh * 4), Image.Resampling.LANCZOS), (nx0 * 4, ny0 * 4))
    return im4, im8


def match_horsehead_brightness(im_f3: Image.Image, im_f2: Image.Image) -> Image.Image:
    """Warm up Frame 3 of the Flying Horse Head so its face matches Frame 2 smoothly with zero dark flicker."""
    arr3 = np.array(im_f3, dtype=np.float32)
    arr2 = np.array(im_f2, dtype=np.float32)
    m3 = arr3[:, :, 3] > 128
    m2 = arr2[:, :, 3] > 128
    # Scale RGB channels proportionally so median luminance and warm amber-crimson tint match Frame 2
    for ch in range(3):
        med3 = float(np.median(arr3[m3, ch]))
        med2 = float(np.median(arr2[m2, ch]))
        if med3 > 1.0:
            gain = np.clip(med2 / med3, 1.0, 1.55)
            arr3[:, :, ch] = np.clip(arr3[:, :, ch] * gain, 0, 255)
    return Image.fromarray(arr3.astype(np.uint8), "RGBA")


def main():
    GEGNER_HD.mkdir(parents=True, exist_ok=True)
    sheet_bats = np.array(Image.open(BRAIN / "stage01_bats_slime_fire_hd_1795334393009.jpg").convert("RGB"))
    sheet_bats_final = np.array(Image.open(BRAIN / "stage01_bats_slime_fire_hd_final_1795334412165.jpg").convert("RGB"))
    sheet_pill = np.array(Image.open(BRAIN / "stage01_pillar_horsehead_hd_1795334371001.jpg").convert("RGB"))

    shutil.copy2(BRAIN / "stage01_bats_slime_fire_hd_final_1795334412165.jpg", GEGNER_HD / "Stage01_Fledermaus_Schleim_Feuer_Sheet_HD.jpg")
    shutil.copy2(BRAIN / "stage01_pillar_horsehead_hd_1795334371001.jpg", GEGNER_HD / "Stage01_Knochensaeule_Pferdekopf_Sheet_HD.jpg")

    hb, wb, _ = sheet_bats.shape   # 1376x768 (3x2 grid)
    hp, wp, _ = sheet_pill.shape   # 1376x768

    # Extract individual crisp RGBA cutouts
    bat_fly1 = extract_clean_rgba(sheet_bats[4:hb // 2 - 4, 4:wb // 3 - 4])
    bat_fly2 = extract_clean_rgba(sheet_bats[4:hb // 2 - 4, wb // 3 + 4:(2 * wb) // 3 - 4])
    bat_fly3 = extract_clean_rgba(sheet_bats[4:hb // 2 - 4, (2 * wb) // 3 + 4:wb - 4])
    bat_hang = extract_clean_rgba(sheet_bats_final[hb // 2 + 4:hb - 4, 4:wb // 3 - 4])
    slime_a06 = extract_clean_rgba(sheet_bats[hb // 2 + 4:hb - 4, wb // 3 + 4:(2 * wb) // 3 - 4])
    fire_base = extract_clean_rgba(sheet_bats[hb // 2 + 4:hb - 4, (2 * wb) // 3 + 4:wb - 4], lum_thresh=18.0, soft_lo=10.0, soft_span=28.0)

    pillar_ivory = extract_clean_rgba(sheet_pill[4:hp - 4, 4:395])
    pillar_red   = extract_clean_rgba(sheet_pill[4:hp - 4, 395:675])
    horse_1      = extract_clean_rgba(sheet_pill[4:375, 675:1025])
    horse_2      = extract_clean_rgba(sheet_pill[375:hp - 4, 675:1025])
    horse_3_raw  = extract_clean_rgba(sheet_pill[375:hp - 4, 1025:wp - 4])
    horse_3      = match_horsehead_brightness(horse_3_raw, horse_2)

    # Fireball animation shimmer: rotate slight angles for the 3 0x48 frames
    fire_1 = fire_base
    fire_2 = fire_base.rotate(14.0, Image.Resampling.BICUBIC, expand=True)
    fire_3 = fire_base.rotate(-16.0, Image.Resampling.BICUBIC, expand=True)

    ASSETS_SPEC = [
        ("Fledermaus_Flug_01",        bat_fly1,     "gegner-000c_pose-8d61_d04c58d6b21c5cbd.png"),
        ("Fledermaus_Flug_02",        bat_fly2,     "gegner-000c_pose-8d66_a02fddd1382dc221.png"),
        ("Fledermaus_Flug_03",        bat_fly3,     "gegner-004e_pose-8d6b_1bffba103a35af2e.png"),
        ("Fledermaus_Haengend_01",    bat_hang,     "gegner-004e_pose-918e_216a9cadeffabdf1.png"),
        ("Deckenschleim_A06_01",      slime_a06,    "gegner-0032_pose-8a41_81640d72194adb2b.png"),
        ("Knochensaeule_Normal",      pillar_ivory, "gegner-000b_pose-8d70_d88a204c80492654.png"),
        ("Knochensaeule_Angriff",     pillar_red,   "gegner-000b_pose-8c0f_d88a204c80492654.png"),
        ("Knochensaeule_Feuerball_1", fire_1,       "gegner-0048_pose-a4e9_279ff7177b3f5904.png"),
        ("Knochensaeule_Feuerball_2", fire_2,       "gegner-0048_pose-a4ee_d64266e09db60c07.png"),
        ("Knochensaeule_Feuerball_3", fire_3,       "gegner-0048_pose-a4f3_c8af3213896900ce.png"),
        ("Fliegender_Pferdekopf_01",  horse_1,      "gegner-006f_pose-962e_d499ba98f11a629f.png"),
        ("Fliegender_Pferdekopf_02",  horse_2,      "gegner-006f_pose-963b_33ce4b69e172be81.png"),
        ("Fliegender_Pferdekopf_03",  horse_3,      "gegner-006f_pose-9648_12c6d708c8402fae.png"),
    ]

    imgs_8x = {}
    for out_stem, crop_im, ref_fname in ASSETS_SPEC:
        im4, im8 = register_to_reference(crop_im, REF_DIR / ref_fname)
        im4.save(GEGNER_HD / f"{out_stem}_HD_4x.png")
        im8.save(GEGNER_HD / f"{out_stem}_HD_8x.png")
        imgs_8x[out_stem] = im8
        print(f"Exported {out_stem}_HD_4x/8x.png cleanly aligned to {ref_fname}")

    # Build unified Stage 01 8x enemy pack 'hd-stage01' merging hd-skeleton + all 4 new Stage 01 enemies!
    skel_ep = ROOT / "artwork-local/enemy-packs-hd/hd-skeleton"
    stage_ep = ROOT / "artwork-local/enemy-packs-hd/hd-stage01"
    if stage_ep.exists():
        shutil.rmtree(stage_ep)
    shutil.copytree(skel_ep, stage_ep)

    skel_manifest = json.loads((stage_ep / "enemies.json").read_text(encoding="utf-8"))
    frames_by_id = {f["id"]: f for f in skel_manifest["frames"]}

    # Load full captured_all.json to pull exact actor_type / pose / id metadata
    cap_manifest = json.loads((REF_DIR / "captured_all.json").read_text(encoding="utf-8"))
    cap_lookup = {f["id"]: f for f in cap_manifest["frames"]}

    ID_TO_STEM = {
        # Vampire Bat (both 0x0c and 0x4e variants)
        "gegner-000c_pose-8d61_d04c58d6b21c5cbd": "Fledermaus_Flug_01",
        "gegner-004e_pose-8d61_d04c58d6b21c5cbd": "Fledermaus_Flug_01",
        "gegner-000c_pose-8d66_a02fddd1382dc221": "Fledermaus_Flug_02",
        "gegner-004e_pose-8d66_a02fddd1382dc221": "Fledermaus_Flug_02",
        "gegner-000c_pose-8d6b_1bffba103a35af2e": "Fledermaus_Flug_03",
        "gegner-004e_pose-8d6b_1bffba103a35af2e": "Fledermaus_Flug_03",
        "gegner-004e_pose-918e_216a9cadeffabdf1": "Fledermaus_Haengend_01",
        # A06 Ceiling Slime (0x32)
        "gegner-0032_pose-8a41_81640d72194adb2b": "Deckenschleim_A06_01",
        # Two-Skull Bone Pillar (0x0b) + Fireballs (0x48)
        "gegner-000b_pose-8d70_d88a204c80492654": "Knochensaeule_Normal",
        "gegner-000b_pose-8c0f_d88a204c80492654": "Knochensaeule_Angriff",
        "gegner-0048_pose-a4e9_279ff7177b3f5904": "Knochensaeule_Feuerball_1",
        "gegner-0048_pose-a4ee_d64266e09db60c07": "Knochensaeule_Feuerball_2",
        "gegner-0048_pose-a4f3_c8af3213896900ce": "Knochensaeule_Feuerball_3",
        # Flying Horse Head (both 0x6f and 0x71 variants)
        "gegner-006f_pose-962e_d499ba98f11a629f": "Fliegender_Pferdekopf_01",
        "gegner-0071_pose-962e_d499ba98f11a629f": "Fliegender_Pferdekopf_01",
        "gegner-006f_pose-963b_33ce4b69e172be81": "Fliegender_Pferdekopf_02",
        "gegner-0071_pose-963b_33ce4b69e172be81": "Fliegender_Pferdekopf_02",
        "gegner-006f_pose-9648_12c6d708c8402fae": "Fliegender_Pferdekopf_03",
        "gegner-0071_pose-9648_12c6d708c8402fae": "Fliegender_Pferdekopf_03",
    }

    for stem, im8 in imgs_8x.items():
        im8.save(stage_ep / f"{stem}_HD_8x.png")

    for gid, stem in ID_TO_STEM.items():
        c = cap_lookup[gid]
        frames_by_id[gid] = {
            "id": gid,
            "actor_type": c["actor_type"],
            "pose": c["pose"],
            "display_size": c["display_size"],
            "anchor": c["anchor"],
            "image": f"{stem}_HD_8x.png",
        }

    # Also register 0x0c hanging bat just in case room variant uses 0x0c instead of 0x4e
    c_hang = cap_lookup["gegner-004e_pose-918e_216a9cadeffabdf1"]
    frames_by_id["gegner-000c_pose-918e_216a9cadeffabdf1"] = {
        "id": "gegner-000c_pose-918e_216a9cadeffabdf1",
        "actor_type": 0x0C,
        "pose": c_hang["pose"],
        "display_size": c_hang["display_size"],
        "anchor": c_hang["anchor"],
        "image": "Fledermaus_Haengend_01_HD_8x.png",
    }

    final_frames = sorted(frames_by_id.values(), key=lambda x: (x["actor_type"], x["pose"], x["id"]))
    (stage_ep / "enemies.json").write_text(
        json.dumps({"version": 1, "name": "Stage 01 HD Enemies (8x Whole-Pose)", "frames": final_frames}, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Built unified Stage 01 8x enemy pack 'hd-stage01' with {len(final_frames)} entries at {stage_ep}")


if __name__ == "__main__":
    main()
