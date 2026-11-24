#!/usr/bin/env python3
"""Prepare the complete Full-Game Level & Background HD Kit for Super Castlevania IV (Rooms 08-68, Stages 02-11):
1. Deduplicates all 61 remaining rooms (08-68) into their exact unique BG1/BG2 tileset+palette groups.
2. For each unique Stage/Area group:
   - Renders a 1x Scene Preview (BG2 + BG1 combined around spawn)
   - Extracts the exact BG2 Parallax Background 1x reference canvas (seamless repeating window)
   - Extracts all actively used unique 32x32 BG1 Foreground metatile blocks into clean 8x4 (32-block) 1x reference sheets
   - Records exact 8x8 tile FNV-1a keys (`fnv_key`) for every BG1 block & BG2 tile in `level_manifest.json`
3. Generates a visual overview contact sheet (`Alle_Level_Bereiche_Uebersicht.jpg`) and ready-to-paste
   ChatGPT/Claude + Higgsfield MCP (`nano_banana_pro`, `use_unlim: true`) prompts!
"""

import hashlib
import json
import struct
import sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(r"D:\Super Castlevania IV Recomp\SuperCastlevaniaIvSNESRecomp")
ROOMS = ROOT / "artwork-local" / "level-editor" / "rooms"
KIT = Path(r"D:\Super Castlevania IV Recomp\Assets (ausgeschnitten)\Higgsfield_Vorbereitung")
LVL_ROOT = KIT / "05_Alle_Level_Hintergruende_und_Tilesets"
DIR_BG2 = LVL_ROOT / "01_BG2_Hintergruende_1x"
DIR_BG1 = LVL_ROOT / "02_BG1_Vordergrund_Bloecke_1x"
DIR_PREV = LVL_ROOT / "03_Szenen_Vorschau_1x"
DIR_OUT = LVL_ROOT / "04_Level_Higgsfield_Output"

for d in (DIR_BG2, DIR_BG1, DIR_PREV, DIR_OUT):
    d.mkdir(parents=True, exist_ok=True)

sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tools" / "hd"))
from level_assets import Assets
from hd_preview import fnv_key


def decode_bg_tile_indices(a: Assets, word: int, layer: str) -> tuple:
    """Return (bpp, px_list_64, palette_colors_list, hflip, vflip) for exact fnv_key computation."""
    mode = a.meta["ppu"]["bgmode"] & 7
    index = 0 if layer == "front" else 1
    spec = a.meta["ppu"]["layers"][index]
    bpp = 2 if mode == 0 else 8 if (mode == 3 and index == 0) else 4
    base = (spec["tiles"] + (word & 1023) * (bpp * 4)) & 32767
    pal_off = 0 if (bpp == 8 or mode == 7) else ((word >> 10) & 7) * (1 << bpp) + (32 * index if mode == 0 else 0)
    px = []
    for y in range(8):
        for x in range(8):
            bit = 7 - x
            if mode == 7:
                v = a.vram[((word & 255) * 64 + y * 8 + x) & 32767] >> 8
            else:
                v = 0
                for pair in range(bpp // 2):
                    w0 = a.vram[(base + pair * 8 + y) & 32767]
                    v |= (((w0 >> bit) & 1) | (((w0 >> (bit + 8)) & 1) << 1)) << (pair * 2)
            px.append(v)
    # Note: fnv_key uses unflipped tile indices; engine applies H/V flip at draw time
    cols = [int(a.colors[pal_off + c]) for c in range(1 << bpp)] if mode != 7 else [int(a.colors[c]) for c in range(256)]
    key = fnv_key(bpp, px, cols)
    hf = bool(word & 0x4000)
    vf = bool(word & 0x8000)
    return key, hf, vf, any(v != 0 for v in px)


def render_block_32(a: Assets, block_idx: int, layer: str) -> Image.Image:
    im = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    words = a.block(block_idx, layer)
    for bi, w in enumerate(words):
        t = a.tile(w, layer)
        im.paste(t, ((bi % 4) * 8, (bi // 4) * 8), t)
    return im


def get_used_blocks(a: Assets, layer: str) -> list:
    """Return sorted list of unique 32x32 block indices actually referenced in the room's tilemap."""
    base = 0x8000 if layer == "front" else 0xe000
    w_blocks = min(8192, a.meta["width"]) // 32
    h_blocks = min(2048, a.meta["height"]) // 32
    used = set()
    for by in range(min(h_blocks, 32)):
        for bx in range(min(w_blocks, 128)):
            # Standard SCV4 32px block map addressing
            at = base + (bx // 8) * 128 + by * 16 + (bx % 8) * 2
            if at + 2 <= len(a.ram):
                m = struct.unpack_from("<H", a.ram, at)[0]
                bidx = m & 255
                used.add(bidx)
    # Filter out completely empty blocks
    nonempty = []
    for bidx in sorted(used):
        im = render_block_32(a, bidx, layer)
        if im.getbbox():
            nonempty.append(bidx)
    return nonempty


def render_bg2_canvas(a: Assets) -> tuple:
    """Render a clean 512x256 (16x8 blocks of 32x32) BG2 parallax background canvas + per-tile key map."""
    w_b = min(16, max(8, min(512, a.meta["width"]) // 32))
    h_b = 8  # 256px tall
    canvas = Image.new("RGBA", (w_b * 32, h_b * 32), (0, 0, 0, 255))
    # Fill sky color from CGRAM[0]
    c0 = int(a.colors[0])
    expand = lambda n: (n << 3) | (n >> 2)
    sky_rgb = (expand(c0 & 31), expand((c0 >> 5) & 31), expand((c0 >> 10) & 31))
    canvas = Image.new("RGBA", (w_b * 32, h_b * 32), (*sky_rgb, 255))

    tile_entries = []
    base = 0xe000
    for by in range(h_b):
        for bx in range(w_b):
            at = base + (bx // 8) * 128 + by * 16 + (bx % 8) * 2
            if at + 2 > len(a.ram):
                continue
            m = struct.unpack_from("<H", a.ram, at)[0]
            bidx = m & 255
            flip_b = (0x4000 if (m & 0x8000) else 0) | (0x8000 if (m & 0x4000) else 0)
            words = a.block(bidx, "back")
            for ty in range(4):
                for tx in range(4):
                    xx = 3 - tx if (m & 0x8000) else tx
                    yy = 3 - ty if (m & 0x4000) else ty
                    w = words[yy * 4 + xx] ^ flip_b
                    t_im = a.tile(w, "back")
                    px_x = bx * 32 + tx * 8
                    px_y = by * 32 + ty * 8
                    canvas.alpha_composite(t_im, (px_x, px_y))
                    key, hf, vf, nz = decode_bg_tile_indices(a, w, "back")
                    if nz:
                        tile_entries.append({
                            "x": px_x, "y": px_y, "key": key, "hf": hf, "vf": vf
                        })
    return canvas, tile_entries, sky_rgb


def render_scene_preview(a: Assets) -> Image.Image:
    """Render a 512x256 1x preview combining BG2 + BG1."""
    bg2, _, _ = render_bg2_canvas(a)
    w_b = bg2.width // 32
    h_b = 8
    base = 0x8000
    for by in range(h_b):
        for bx in range(w_b):
            at = base + (bx // 8) * 128 + by * 16 + (bx % 8) * 2
            if at + 2 > len(a.ram):
                continue
            m = struct.unpack_from("<H", a.ram, at)[0]
            bidx = m & 255
            words = a.block(bidx, "front")
            flip_b = (0x4000 if (m & 0x8000) else 0) | (0x8000 if (m & 0x4000) else 0)
            for ty in range(4):
                for tx in range(4):
                    xx = 3 - tx if (m & 0x8000) else tx
                    yy = 3 - ty if (m & 0x4000) else ty
                    w = words[yy * 4 + xx] ^ flip_b
                    t_im = a.tile(w, "front")
                    bg2.alpha_composite(t_im, (bx * 32 + tx * 8, by * 32 + ty * 8))
    return bg2.convert("RGB")


def main():
    # Group rooms 08..67 by unique (BG1+BG2 VRAM + CGRAM) hash
    groups = {}
    group_order = []
    for r_idx in range(8, 68):
        rdir = ROOMS / f"{r_idx:02d}"
        if not (rdir / "room.json").exists():
            continue
        rj = json.loads((rdir / "room.json").read_text(encoding="utf-8"))
        if (rj["ppu"]["bgmode"] & 7) != 1:
            continue
        vid = (rdir / "video.bin").read_bytes()
        l0 = rj["ppu"]["layers"][0]["tiles"] * 2
        h = hashlib.md5(vid[l0:l0 + 0x4000] + vid[0x10000:0x10100]).hexdigest()[:8]
        if h not in groups:
            groups[h] = []
            group_order.append(h)
        groups[h].append(r_idx)

    manifest = {
        "version": 1,
        "output_folder": str(DIR_OUT),
        "areas": [],
    }

    # Build overview contact sheet of all unique Stage/Area groups
    n_areas = len(group_order)
    ov_cols = 4
    ov_rows = (n_areas + ov_cols - 1) // ov_cols
    ov_w, ov_h = 320, 184
    overview = Image.new("RGB", (ov_cols * ov_w, ov_rows * ov_h), (16, 16, 22))
    ov_draw = ImageDraw.Draw(overview)

    total_bg2_sheets = 0
    total_bg1_sheets = 0

    for g_idx, gh in enumerate(group_order, 1):
        r_list = groups[gh]
        rep_r = r_list[0]
        a = Assets(ROOMS / f"{rep_r:02d}")
        r_tag = f"Area_{g_idx:02d}_R{r_list[0]:02d}" + (f"-R{r_list[-1]:02d}" if len(r_list) > 1 else "")

        # 1. Scene preview (512x256)
        prev = render_scene_preview(a)
        prev_p = DIR_PREV / f"{r_tag}_Vorschau_1x.png"
        prev.save(prev_p)

        # Paste onto overview contact sheet
        oc, orow = (g_idx - 1) % ov_cols, (g_idx - 1) // ov_cols
        thumb = prev.resize((304, 152), Image.Resampling.NEAREST)
        overview.paste(thumb, (oc * ov_w + 8, orow * ov_h + 24))
        ov_draw.rectangle([oc * ov_w + 2, orow * ov_h + 2, (oc + 1) * ov_w - 3, (orow + 1) * ov_h - 3], outline=(62, 68, 86))
        ov_draw.text((oc * ov_w + 8, orow * ov_h + 6), f"{r_tag} ({len(r_list)} Raeume)", fill=(255, 232, 160))

        # 2. BG2 Parallax Background 1x canvas (upscaled 2x nearest for crystal-clear AI input!)
        bg2_im, bg2_tiles, sky_rgb = render_bg2_canvas(a)
        bg2_ref_name = f"{r_tag}_BG2_Hintergrund_REF.png"
        bg2_out_stem = f"{r_tag}_BG2_Hintergrund_HD"
        bg2_im.resize((bg2_im.width * 2, bg2_im.height * 2), Image.Resampling.NEAREST).save(DIR_BG2 / bg2_ref_name)
        total_bg2_sheets += 1

        # 3. Collect ALL actively used 32x32 BG1 blocks across ALL rooms in this tileset group!
        used_blocks = set()
        for rx in r_list:
            ax = Assets(ROOMS / f"{rx:02d}")
            used_blocks.update(get_used_blocks(ax, "front"))
        used_blocks = sorted(used_blocks)

        # Pack used 32x32 BG1 blocks into clean 8x4 (32 blocks -> 256x128 native -> 1024x512 4x-nearest ref!) sheets
        bg1_sheets = []
        chunks = [used_blocks[i:i + 32] for i in range(0, len(used_blocks), 32)]
        for ci, chunk in enumerate(chunks, 1):
            sh_1x = Image.new("RGBA", (8 * 32, 4 * 32), (0, 0, 0, 255))
            block_meta = []
            for bi, bidx in enumerate(chunk):
                col, row = bi % 8, bi // 8
                bim = render_block_32(a, bidx, "front")
                sh_1x.alpha_composite(bim, (col * 32, row * 32))
                # Record exact 16 8x8 tile keys inside this 32x32 block
                words = a.block(bidx, "front")
                sub_tiles = []
                for ti, w in enumerate(words):
                    key, hf, vf, nz = decode_bg_tile_indices(a, w, "front")
                    if nz:
                        sub_tiles.append({"tx": ti % 4, "ty": ti // 4, "key": key, "hf": hf, "vf": vf})
                block_meta.append({
                    "col": col, "row": row, "block_idx": bidx, "tiles": sub_tiles
                })
            ref_name = f"{r_tag}_BG1_Bloecke_Part{ci:02d}_REF.png"
            out_stem = f"{r_tag}_BG1_Bloecke_Part{ci:02d}_HD"
            sh_1x.convert("RGB").resize((1024, 512), Image.Resampling.NEAREST).save(DIR_BG1 / ref_name)
            total_bg1_sheets += 1
            bg1_sheets.append({
                "output_stem": out_stem,
                "ref_png": str(DIR_BG1 / ref_name),
                "blocks": block_meta,
            })

        manifest["areas"].append({
            "area_tag": r_tag,
            "rooms": r_list,
            "sky_rgb": list(sky_rgb),
            "preview_png": str(prev_p),
            "bg2": {
                "output_stem": bg2_out_stem,
                "ref_png": str(DIR_BG2 / bg2_ref_name),
                "native_size": [bg2_im.width, bg2_im.height],
                "tiles": bg2_tiles,
            },
            "bg1_sheets": bg1_sheets,
        })

    ov_path = LVL_ROOT / "Alle_Level_Bereiche_Uebersicht.jpg"
    overview.save(ov_path, "JPEG", quality=91, optimize=True)
    (LVL_ROOT / "level_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    # Write dedicated Level Prompts guide for ChatGPT / Claude + Higgsfield MCP
    lvl_prompts = f"""# Super Castlevania IV — Alle Level & Hintergründe (Stages 02–11) HD-Produktions-Kit

> **Für ChatGPT App / Claude + Higgsfield MCP (`use_unlim: true` = 0 Credits!):**
> - Modell: **`nano_banana_pro`** (oder **`gpt_image_2_6`**)
> - Seitenverhältnis: **`2:1` / `16:9`** (`resolution: "2k"`, **`use_unlim: true`**)
> - Fertige HD-Bilder mit dem exakten **`output_stem`.png / `.jpg`** speichern in:
>   `D:\\Super Castlevania IV Recomp\\Assets (ausgeschnitten)\\Higgsfield_Vorbereitung\\05_Alle_Level_Hintergruende_und_Tilesets\\04_Level_Higgsfield_Output\\`
> - Danach **1 Befehl ausführen** zum automatischen Zerschneiden, Hashen & Installieren ins Spiel:
>   ```powershell
>   python "D:\\Super Castlevania IV Recomp\\SuperCastlevaniaIvSNESRecomp\\tools\\hd\\import_higgsfield_levels.py"
>   ```

## Statistik (alle 60 übrigen Mode-1-Räume `R08`–`R67` dedupliziert!)
- **Einzigartige Level-Bereiche (Stages 02–11):** `{n_areas}` (Übersicht: `Alle_Level_Bereiche_Uebersicht.jpg`)
- **BG2 Parallax-Hintergründe (`01_BG2_Hintergruende_1x/`):** `{total_bg2_sheets}` Sheets
- **BG1 Vordergrund-Block-Sheets (`02_BG1_Vordergrund_Bloecke_1x/`):** `{total_bg1_sheets}` Sheets (je bis zu 32 32×32-Blöcke im 8×4-Raster)

---

## Universal-Prompt für BG2 Parallax-Hintergründe (`*_BG2_Hintergrund_REF.png`)
```text
Remaster this Super Castlevania IV 16-bit parallax background painting into a rich, atmospheric dark-gothic oil-painted HD game background (matching classic Castlevania dark baroque architecture, moody moonlight, weathered stone, misty forests, cavernous rock, and dramatic rim lighting). CRITICAL: Keep the EXACT pixel composition, horizon line, pillar/arch/window positions, and left-to-right seamless wrapping 1:1 with the reference image so every tile aligns seamlessly in-game. No text, no borders, no modern objects, full edge-to-edge painting.
```

## Universal-Prompt für BG1 Vordergrund-Blöcke (`*_BG1_Bloecke_PartXX_REF.png`)
```text
Remaster this 8x4 grid of 32x32 Super Castlevania IV foreground level tiles (platforms, stone bricks, wood beams, stairs, pillars, spikes, chains, gothic arches) into ultra-crisp dark-gothic oil-painted HD game tiles on a PURE SOLID BLACK (#000000) background. CRITICAL: Preserve the EXACT 8x4 grid cell boundaries, every single platform top/bottom/left/right edge, stair angle, and silhouette 1:1 with zero shift so adjacent tiles connect seamlessly without seams! Keep solid rock/wood/metal completely opaque, and keep empty background areas pure #000000 black.
```
"""
    (LVL_ROOT / "PROMPTS_LEVELS_CHATGPT_CLAUDE.md").write_text(lvl_prompts, encoding="utf-8")

    print(f"Prepared Full-Game Level Kit in: {LVL_ROOT}")
    print(f"  Unique Stage/Area groups (Rooms 08-67): {n_areas}")
    print(f"  BG2 Background sheets                 : {total_bg2_sheets}")
    print(f"  BG1 Foreground block sheets           : {total_bg1_sheets}")
    print(f"  Overview contact sheet                : {ov_path} ({ov_path.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
