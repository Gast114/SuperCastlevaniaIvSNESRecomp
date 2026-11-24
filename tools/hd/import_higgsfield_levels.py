#!/usr/bin/env python3
"""1-Click Automatic Importer for Full-Game Level Backgrounds (BG2) & Foreground Block Sheets (BG1).
Drop any generated HD BG2 or BG1 sheet (.png / .jpg / .webp) matching its `output_stem` into:
  D:\\Super Castlevania IV Recomp\\Assets (ausgeschnitten)\\Higgsfield_Vorbereitung\\05_Alle_Level_Hintergruende_und_Tilesets\\04_Level_Higgsfield_Output\\
Then run this script to automatically:
  1. Slice every HD BG2 background into exact 4x (32x32) 8x8-tile replacements keyed by `fnv_key`
  2. Slice every HD BG1 foreground 8x4 block sheet (with clean opaque black-keying where 1x is transparent)
     into exact 4x (32x32) 8x8-tile replacements keyed by `fnv_key`
  3. Inject all imported areas into a unified HD pack (preserving all Stage 01 A01-A08 + HUD + Items!)
     and sync into build-play, build, and build-lua!
"""

import json
import shutil
import sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageOps

ROOT = Path(r"D:\Super Castlevania IV Recomp\SuperCastlevaniaIvSNESRecomp")
LVL_ROOT = Path(r"D:\Super Castlevania IV Recomp\Assets (ausgeschnitten)\Higgsfield_Vorbereitung\05_Alle_Level_Hintergruende_und_Tilesets")
DIR_OUT = LVL_ROOT / "04_Level_Higgsfield_Output"

sys.path.insert(0, str(ROOT / "tools" / "hd"))
import hd_common as hd
from hd_tiles import write_pack


def find_sheet(stem: str):
    for ext in (".png", ".jpg", ".jpeg", ".webp"):
        p = DIR_OUT / f"{stem}{ext}"
        if p.exists():
            return p
    return None


def unflip_tile(tile_arr: np.ndarray, hf: bool, vf: bool) -> np.ndarray:
    im = Image.fromarray(tile_arr, "RGBA")
    if hf:
        im = ImageOps.mirror(im)
    if vf:
        im = ImageOps.flip(im)
    return np.array(im, dtype=np.uint8)


def main():
    manifest = json.loads((LVL_ROOT / "level_manifest.json").read_text(encoding="utf-8"))
    new_tiles_4x = {}
    imported_bg2 = 0
    imported_bg1 = 0

    for area in manifest["areas"]:
        # 1. BG2 Parallax Background
        bg2 = area["bg2"]
        bg2_p = find_sheet(bg2["output_stem"])
        if bg2_p:
            nw, nh = bg2["native_size"]
            im = Image.open(bg2_p).convert("RGBA").resize((nw * 4, nh * 4), Image.Resampling.LANCZOS)
            arr = np.array(im, dtype=np.uint8)
            for t in bg2["tiles"]:
                x4, y4 = t["x"] * 4, t["y"] * 4
                patch = arr[y4:y4 + 32, x4:x4 + 32].copy()
                if patch.shape[:2] == (32, 32):
                    new_tiles_4x[t["key"]] = unflip_tile(patch, t["hf"], t["vf"])
            imported_bg2 += 1
            print(f"Imported BG2 {bg2_p.name} ({len(bg2['tiles'])} tiles)")

        # 2. BG1 Foreground 8x4 Block Sheets
        for sh in area["bg1_sheets"]:
            sh_p = find_sheet(sh["output_stem"])
            if not sh_p:
                continue
            im = Image.open(sh_p).convert("RGBA").resize((8 * 128, 4 * 128), Image.Resampling.LANCZOS)
            ref_im = Image.open(sh["ref_png"]).convert("RGB").resize((8 * 128, 4 * 128), Image.Resampling.NEAREST)
            arr = np.array(im, dtype=np.uint8)
            ref_arr = np.array(ref_im, dtype=np.uint8)
            # Clear pure-black transparent areas where BOTH ref and HD are pure black
            hd_lum = arr[:, :, :3].max(axis=2)
            ref_lum = ref_arr.max(axis=2)
            is_bg = (ref_lum == 0) & (hd_lum < 18)
            arr[is_bg, 3] = 0

            for blk in sh["blocks"]:
                bx4, by4 = blk["col"] * 128, blk["row"] * 128
                for t in blk["tiles"]:
                    tx4, ty4 = bx4 + t["tx"] * 32, by4 + t["ty"] * 32
                    patch = arr[ty4:ty4 + 32, tx4:tx4 + 32].copy()
                    if patch.shape[:2] == (32, 32):
                        new_tiles_4x[t["key"]] = unflip_tile(patch, t["hf"], t["vf"])
            imported_bg1 += 1
            print(f"Imported BG1 {sh_p.name} ({len(sh['blocks'])} blocks)")

    if not new_tiles_4x:
        print(f"No Level HD sheets found yet in {DIR_OUT} (ready for tomorrow's Higgsfield outputs!).")
        print(f"Indexed: {len(manifest['areas'])} unique Stage/Area groups (32 BG2 + 91 BG1 sheets).")
        return

    # Inject newly imported tiles into stage-01-user-grid-v21-8x-skeleton as shared global tiles!
    pack_name = "stage-01-user-grid-v21-8x-skeleton"
    pack_src = ROOT / "build-play" / "game" / "hd_packs" / pack_name
    tmp_dir = LVL_ROOT / "_tmp_import"
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)
    tmp_dir.mkdir(parents=True, exist_ok=True)

    # Create or update a dedicated global 'stages-02-11' scene in the pack!
    sc_dir = pack_src / "stages-02-11"
    if sc_dir.exists():
        _, _, old_tiles = hd.load_pack(sc_dir)
    else:
        sc_dir.mkdir(parents=True, exist_ok=True)
        old_tiles = {}
    merged = {**old_tiles, **new_tiles_4x}
    for old_at in sc_dir.glob("atlas_*.png"):
        old_at.unlink()
    write_pack(merged, tmp_dir, 4)
    for atf in tmp_dir.glob("atlas_*.png"):
        shutil.copy2(atf, sc_dir / atf.name)
    tmeta = json.loads((tmp_dir / "pack.json").read_text(encoding="utf-8"))
    tmeta["name"] = "Stages 02-11 HD (Higgsfield Auto-Import)"
    (sc_dir / "pack.json").write_text(json.dumps(tmeta, indent=2) + "\n", encoding="utf-8")
    shutil.rmtree(tmp_dir, ignore_errors=True)

    top_meta = json.loads((pack_src / "pack.json").read_text(encoding="utf-8"))
    if not any(s.get("path") == "stages-02-11" for s in top_meta.get("scenes", [])):
        top_meta["scenes"].append({"name": "Stages 02-11 HD", "path": "stages-02-11"})
        (pack_src / "pack.json").write_text(json.dumps(top_meta, indent=2) + "\n", encoding="utf-8")

    for dst in (ROOT / "build" / "hd_packs" / pack_name, ROOT / "build-lua" / "hd_packs" / pack_name):
        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(pack_src, dst)
    print(f"DONE! Imported {imported_bg2} BG2 + {imported_bg1} BG1 sheets ({len(new_tiles_4x)} unique 4x tiles) -> synced to build-play, build, build-lua!")


if __name__ == "__main__":
    main()
