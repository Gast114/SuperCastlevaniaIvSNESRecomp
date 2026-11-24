#!/usr/bin/env python3
"""Prepare the complete turnkey Higgsfield/Claude HD Production Kit from the Monster-Werkstatt:
- 01_Prioritaet_Simon_und_Stage01/ : Simon V2 Walk/Idle, 8-Dir Whip-Hold, Whip Parts, Stage 01 Missing Enemies (F1/F2/F5/F6/F10), Boomerang
- 02_Alle_Bosse_1x_Sheets/         : All remaining Bosses (0x81, 0x83..0x8C) grouped into 4x2 1280x720 1x-reference sheets
- 03_Alle_Monster_1x_Sheets/       : All remaining Game Enemies (Stages 01-11) grouped into 4x2 1280x720 1x-reference sheets
- 04_Higgsfield_Output/            : Drop-in folder for generated HD sheets
- sheet_manifest.json              : Exact (sheet -> cell col,row -> enemy frame_id, actor_type, pose, 1x ref path) mapping
- PROMPTS_CLAUDE_HIGGSFIELD.md     : Ready-to-use prompts for Claude + Higgsfield MCP (nano_banana_pro, use_unlim=True)
"""

import json
import re
import shutil
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(r"D:\Super Castlevania IV Recomp\SuperCastlevaniaIvSNESRecomp")
BRAIN = Path(r"C:\Users\Gaming\.gemini\antigravity\brain\0e3d1566-2f3c-4183-be49-fad33ce3d4a9")
LIB = ROOT / "artwork-local" / "enemy-library"
LIB_NT = LIB / "native-template"
CAP_NT = BRAIN / "scratch" / "missing_enemies_capture" / "native-template"
EP_CUR = ROOT / "artwork-local" / "enemy-packs-hd" / "hd-stage01"

KIT = Path(r"D:\Super Castlevania IV Recomp\Assets (ausgeschnitten)\Higgsfield_Vorbereitung")
DIR_PRIO = KIT / "01_Prioritaet_Simon_und_Stage01"
DIR_BOSS = KIT / "02_Alle_Bosse_1x_Sheets"
DIR_MON  = KIT / "03_Alle_Monster_1x_Sheets"
DIR_OUT  = KIT / "04_Higgsfield_Output"
DIR_PREV = KIT / "00_Uebersichten"

for d in (DIR_PRIO, DIR_BOSS, DIR_MON, DIR_OUT, DIR_PREV):
    d.mkdir(parents=True, exist_ok=True)


def safe_slug(name: str) -> str:
    s = name.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")
    s = s.replace("Ä", "Ae").replace("Ö", "Oe").replace("Ü", "Ue")
    s = re.sub(r"[^A-Za-z0-9]+", "_", s).strip("_")
    return s[:40] or "Enemy"


def make_4x2_sheet(entries: list, out_png: Path) -> list:
    """Pack up to 8 (fid, actor_type, pose, ref_path, label) entries into a clean 1280x720 4x2 pure-black PNG.
    Returns list of cell metadata dicts."""
    canvas = Image.new("RGB", (1280, 720), (0, 0, 0))
    cells = []
    cw, ch = 320, 360
    for idx, (fid, atype, pose, ref_p, label) in enumerate(entries[:8]):
        col, row = idx % 4, idx // 4
        im = Image.open(ref_p).convert("RGBA")
        bbox = im.getbbox()
        if not bbox:
            continue
        crop = im.crop(bbox)
        sc = min(10, int(min((cw - 40) // max(1, crop.width), (ch - 40) // max(1, crop.height))))
        sc = max(1, sc)
        big = crop.resize((crop.width * sc, crop.height * sc), Image.Resampling.NEAREST)
        ox = col * cw + (cw - big.width) // 2
        oy = row * ch + (ch - big.height) // 2
        canvas.paste(big, (ox, oy), big)
        cells.append({
            "col": col,
            "row": row,
            "id": fid,
            "actor_type": atype,
            "pose": pose,
            "label": label,
            "ref_png": str(ref_p),
            "bbox_1x": list(bbox),
        })
    canvas.save(out_png, "PNG")
    return cells


def main():
    # Load currently completed HD enemy IDs so we skip already-done poses (e.g. Rowdain 0x80, Skeleton, Bats, Horsehead)
    cur_ep = json.loads((EP_CUR / "enemies.json").read_text(encoding="utf-8"))
    done_ids = {f["id"] for f in cur_ep["frames"]}

    # Load Monster-Werkstatt library & native-template
    lj = json.loads((LIB / "library.json").read_text(encoding="utf-8"))
    nt_j = json.loads((LIB_NT / "enemies.json").read_text(encoding="utf-8"))
    nt_by_id = {f["id"]: f for f in nt_j["frames"] if "__teil-" not in f["id"]}

    # Also load our Stage 01 F1-F10 freshly captured poses
    cap_j = json.loads((CAP_NT / "enemies.json").read_text(encoding="utf-8"))
    cap_by_id = {f["id"]: f for f in cap_j["frames"] if "__teil-" not in f["id"]}

    manifest = {
        "version": 1,
        "output_folder": str(DIR_OUT),
        "priority_sheets": [],
        "boss_sheets": [],
        "monster_sheets": [],
    }

    # 1. Copy Priority Sheets (Simon + Stage 01 Missing + Boomerang) into 01_Prioritaet_Simon_und_Stage01/
    shutil.copy2(BRAIN / "simon_walk_4x2_hd_v2_1795372726123.jpg", DIR_PRIO / "00_Simon_Style_Anchor.jpg")
    shutil.copy2(BRAIN / "scratch" / "simon_v2_refs" / "ref_simon_idle_walk_4x2.png", DIR_PRIO / "01_Simon_V2_Idle_Walk_Duck_4x2_REF.png")
    shutil.copy2(BRAIN / "scratch" / "simon_v2_refs" / "ref_simon_whiphold_4x2.png", DIR_PRIO / "02_Simon_V2_WhipHold_8Dir_4x2_REF.png")
    shutil.copy2(BRAIN / "scratch" / "missing_enemies_refs" / "ref_missing_enemies_part1_4x2.png", DIR_PRIO / "04_Stage01_Missing_Part1_4x2_REF.png")
    shutil.copy2(BRAIN / "scratch" / "missing_enemies_refs" / "ref_missing_enemies_part2_4x2.png", DIR_PRIO / "05_Stage01_Missing_Part2_4x2_REF.png")
    shutil.copy2(BRAIN / "scratch" / "missing_enemies_refs" / "ref_boomerang_1x_2x1.png", DIR_PRIO / "06_Boomerang_GoldenCross_2x1_REF.png")

    # Record exact cell mappings for Priority Stage 01 Missing Part 1 & Part 2 so auto-importer imports them!
    def cap_entry(atype, pose, label):
        for fid, fr in cap_by_id.items():
            if fr["actor_type"] == atype and fr["pose"] == pose:
                return (fid, atype, pose, CAP_NT / f"{fid}.png", label)
        raise KeyError(f"Missing {hex(atype)} {hex(pose)}")

    p1_entries = [
        cap_entry(0x0b, 0x8d70, "Knochensaeule_V2"),
        cap_entry(0x01, 0x905c, "Feuerball_0x01"),
        cap_entry(0x07, 0x916b, "Medusa_Kopf_1"),
        cap_entry(0x07, 0x917c, "Medusa_Kopf_2"),
        cap_entry(0x08, 0x9198, "Geist_Orb"),
        cap_entry(0x08, 0x89d1, "Geist_1"),
        cap_entry(0x08, 0x89de, "Geist_2"),
        cap_entry(0x03, 0xa4f8, "Schwung_Fledermaus_1"),
    ]
    p2_entries = [
        cap_entry(0x73, 0x96d5, "F10_SaeulenMonster_Hand"),
        cap_entry(0x73, 0x96df, "F10_SaeulenMonster_Kopf"),
        cap_entry(0x73, 0x96f5, "F10_SaeulenMonster_Aufstehen"),
        cap_entry(0x73, 0x96e4, "F10_SaeulenMonster_KeuleOben"),
        cap_entry(0x73, 0x9706, "F10_SaeulenMonster_Schlag"),
        cap_entry(0x32, 0x8a41, "Deckenschleim_1"),
        cap_entry(0x32, 0x8a4a, "Deckenschleim_2"),
        cap_entry(0x32, 0x8a53, "Deckenschleim_3"),
    ]

    for sname, ref_name, entries in [
        ("04_Stage01_Missing_Part1_HD", "04_Stage01_Missing_Part1_4x2_REF.png", p1_entries),
        ("05_Stage01_Missing_Part2_HD", "05_Stage01_Missing_Part2_4x2_REF.png", p2_entries),
    ]:
        cells = []
        for idx, (fid, atype, pose, ref_p, label) in enumerate(entries):
            im = Image.open(ref_p).convert("RGBA")
            cells.append({
                "col": idx % 4, "row": idx // 4,
                "id": fid, "actor_type": atype, "pose": pose,
                "label": label, "ref_png": str(ref_p), "bbox_1x": list(im.getbbox()),
            })
        manifest["priority_sheets"].append({
            "output_stem": sname,
            "ref_png": str(DIR_PRIO / ref_name),
            "cells": cells,
        })

    # 2. Extract ALL remaining Bosses (0x83..0x8C) using STRICTLY live-verified observed_main_frame_ids!
    # (Skip corrupted offline 'Weitere Sprites' ROM dumps AND black fade-in silhouette frames!)
    for old_f in DIR_BOSS.glob("*.png"):
        old_f.unlink()
    for old_f in DIR_MON.glob("*.png"):
        old_f.unlink()

    boss_names = {
        0x83: "Boss_83_Medusa",
        0x84: "Boss_84_Puweex_Riesenschaedel",
        0x85: "Boss_85_Dracula",
        0x86: "Boss_86_Zapf_Bat",
        0x87: "Boss_87_Frankenstein",
        0x88: "Boss_88_Gaibon",
        0x89: "Boss_89_Slogra",
        0x8a: "Boss_8A_Sir_Grakul_Ritter",
        0x8c: "Boss_8C_Akmodan_II_Mumie",
    }

    def is_clean_visible_sprite(ref_p: Path) -> bool:
        if not ref_p.exists():
            return False
        im = Image.open(ref_p).convert("RGBA")
        bbox = im.getbbox()
        if not bbox:
            return False
        if (bbox[2] - bbox[0]) < 6 and (bbox[3] - bbox[1]) < 6:
            return False
        import numpy as _np
        arr = _np.array(im)
        m = arr[:, :, 3] > 128
        if m.sum() < 12:
            return False
        # Reject pure-black fade-in/fade-out silhouette frames!
        lum = arr[m, :3].max(axis=1)
        if float(_np.percentile(lum, 92)) < 36.0:
            return False
        return True

    boss_frames_by_type = {}
    for prof in lj["profiles"]:
        mt = prof.get("main_type") or prof.get("type") or 0
        if mt < 0x83 or "Weitere Sprites" in str(prof.get("name", "")):
            continue
        for fid in prof.get("observed_main_frame_ids", []):
            if "__teil-" in fid:
                continue
            fr = nt_by_id.get(fid)
            if not fr:
                continue
            ref_p = LIB_NT / f"{fid}.png"
            if not is_clean_visible_sprite(ref_p):
                continue
            boss_frames_by_type.setdefault(mt, {})[fid] = fr

    total_boss_poses = 0
    for at in sorted(boss_frames_by_type):
        frs = sorted(boss_frames_by_type[at].values(), key=lambda x: (x["pose"], x["id"]))
        bname = boss_names.get(at, f"Boss_{at:02X}")
        chunks = [frs[i:i + 8] for i in range(0, len(frs), 8)]
        for ci, chunk in enumerate(chunks, 1):
            entries = [(f["id"], f["actor_type"], f["pose"], LIB_NT / f"{f['id']}.png", f"{bname}_p{f['pose']:04x}") for f in chunk]
            ref_file = DIR_BOSS / f"{bname}_Sheet{ci:02d}_4x2_REF.png"
            cells = make_4x2_sheet(entries, ref_file)
            total_boss_poses += len(cells)
            manifest["boss_sheets"].append({
                "boss_type": f"0x{at:02x}",
                "boss_name": bname,
                "output_stem": f"{bname}_Sheet{ci:02d}_HD",
                "ref_png": str(ref_file),
                "cells": cells,
            })

    # 3. Extract ALL remaining Game Monsters using STRICTLY live-verified observed_main_frame_ids!
    seen_mon_ids = set(done_ids) | {e[0] for e in p1_entries + p2_entries}
    mon_groups = {}

    for prof in lj["profiles"]:
        cat = str(prof.get("category") or "").lower()
        mtype = prof.get("main_type") or prof.get("type") or 0
        pname = str(prof.get("name") or f"Monster_{mtype:02X}")
        if mtype >= 0x80 or cat == "object" or "Weitere Sprites" in pname:
            continue
        slug = f"M_{mtype:02X}_{safe_slug(pname)}"
        for fid in prof.get("observed_main_frame_ids", []):
            if "__teil-" in fid or fid in seen_mon_ids:
                continue
            fr = nt_by_id.get(fid)
            if not fr or fr["actor_type"] >= 0x80:
                continue
            ref_p = LIB_NT / f"{fid}.png"
            if not is_clean_visible_sprite(ref_p):
                continue
            seen_mon_ids.add(fid)
            mon_groups.setdefault(slug, []).append((fid, fr["actor_type"], fr["pose"], ref_p, f"{slug}_p{fr['pose']:04x}"))

    # Pack all monster poses into clean 4x2 sheets (grouping small monsters together or per-monster when >= 4 poses)
    total_mon_poses = 0
    sheet_idx = 1
    small_bucket = []
    for slug in sorted(mon_groups):
        entries = sorted(mon_groups[slug], key=lambda e: (e[1], e[2], e[0]))
        if len(entries) >= 4:
            chunks = [entries[i:i + 8] for i in range(0, len(entries), 8)]
            for ci, chunk in enumerate(chunks, 1):
                sname = f"{sheet_idx:02d}_{slug}_Part{ci:02d}"
                ref_file = DIR_MON / f"{sname}_4x2_REF.png"
                cells = make_4x2_sheet(chunk, ref_file)
                total_mon_poses += len(cells)
                manifest["monster_sheets"].append({
                    "group": slug,
                    "output_stem": f"{sname}_HD",
                    "ref_png": str(ref_file),
                    "cells": cells,
                })
                sheet_idx += 1
        else:
            small_bucket.extend(entries)

    # Flush small monsters in batches of 8
    for bi in range(0, len(small_bucket), 8):
        chunk = small_bucket[bi:bi + 8]
        sname = f"{sheet_idx:02d}_Kleinmonster_Mix_{bi // 8 + 1:02d}"
        ref_file = DIR_MON / f"{sname}_4x2_REF.png"
        cells = make_4x2_sheet(chunk, ref_file)
        total_mon_poses += len(cells)
        manifest["monster_sheets"].append({
            "group": "Kleinmonster_Mix",
            "output_stem": f"{sname}_HD",
            "ref_png": str(ref_file),
            "cells": cells,
        })
        sheet_idx += 1

    (KIT / "sheet_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    # 4. Write PROMPTS_CLAUDE_HIGGSFIELD.md
    prompts_md = f"""# Super Castlevania IV HD — Claude + Higgsfield MCP Produktions-Kit

> **Wichtig für Claude + Higgsfield MCP:**
> Nutze immer **`model: "nano_banana_pro"`**, **`aspect_ratio: "16:9"`**, **`resolution: "2k"`** und **`use_unlim: true`** (0 Credits im Ultra-Abo über Claude Chat / Claude Cowork!).
> Speichere jedes fertige HD-Sheet unter dem exakten **`output_stem`.png / `.jpg`** in:
> `D:\\Super Castlevania IV Recomp\\Assets (ausgeschnitten)\\Higgsfield_Vorbereitung\\04_Higgsfield_Output\\`
>
> Danach reicht **ein einziger Befehl**, um alle fertigen Sheets automatisch auszuschneiden, pixelgenau auszurichten und ins Spiel zu installieren:
> ```powershell
> python "D:\\Super Castlevania IV Recomp\\SuperCastlevaniaIvSNESRecomp\\tools\\hd\\import_higgsfield_sheets.py"
> ```

---

## Statistik des vorbereiteten Komplett-Kits (aus der Monster-Werkstatt)
- **Priorität 1 (Simon + Peitsche + Stage 01 Rest):** `6` Sheets in `01_Prioritaet_Simon_und_Stage01/`
- **Alle übrigen Bosse (`0x81`, `0x83`–`0x8C`):** `{len(manifest['boss_sheets'])}` Sheets (`{total_boss_poses}` Posen) in `02_Alle_Bosse_1x_Sheets/`
- **Alle übrigen Monster (Stages 01–11):** `{len(manifest['monster_sheets'])}` Sheets (`{total_mon_poses}` Posen) in `03_Alle_Monster_1x_Sheets/`

---

## Priorität 1 — Sofort-Prompts für Claude + Higgsfield (`nano_banana_pro`, `use_unlim: true`)

### 1. Simon Belmont V2 — Standpose + natürlicher 6-Frame-Laufzyklus + Ducken
- **Referenzen:** `01_Simon_V2_Idle_Walk_Duck_4x2_REF.png` (Bild 1) + `00_Simon_Style_Anchor.jpg` (Bild 2)
- **Zieldatei:** `04_Higgsfield_Output/01_Simon_V2_Idle_Walk_Duck_HD.png`
- **Prompt:**
```text
Remaster the 4x2 pixel-art sprite sheet from image 1 into high-detail dark-gothic oil-painted HD game sprites on a PURE SOLID BLACK (#000000) background with ZERO grid lines, ZERO text, ZERO floor, ZERO shadows on the background. Match the EXACT face, warm chestnut-brown hair with headband, warm bronze skin tone, dark riveted slate-blue iron cuirass, pauldrons, faulds, greaves, gold-trimmed belt, and brown boots from image 2 across ALL 8 poses with 100% IDENTICAL color tone, lighting, head size, and body height. CRITICAL POSE FIDELITY: Every pose faces RIGHT and MUST match the EXACT leg placement (which leg is in front vs behind!), knee height, foot placement, and arm position of image 1: Row 1 Col 1 = Standing Idle-01 (left/rear leg stepped cleanly back, right/front leg forward, SAME warm face & colors as walk poses); Row 1 Cols 2-4 & Row 2 Cols 1-3 = smooth, natural 6-frame human walking cycle (DO NOT lift knees high like stairs!); Row 2 Col 4 = Ducking-01. Completely solid opaque character, pure #000000 background only outside the sprites.
```

### 2. Geschmiedete Stahlkettenpeitsche + Morgenstern + Lederpeitsche
- **Referenzen:** Keine nötig (Text-to-Image, `16:9`, `2K`)
- **Zieldatei:** `04_Higgsfield_Output/03_Simon_Whip_Components_HD.png`
- **Prompt:**
```text
Create a 16:9 (4 columns x 2 rows) dark-gothic oil-painted HD game-asset sprite sheet of Simon Belmont's Castlevania IV Whip Weapon Components on a PURE SOLID BLACK (#000000) background with ZERO grid lines, ZERO text, ZERO labels. Dramatic specular forged-steel highlights, weathered iron, braided dark brown leather, antique burnished brass. Row 1 Col 1: Horizontal straight section of heavy FORGED DARK-STEEL INTERLOCKING CHAIN LINKS. Row 1 Col 2: Vertical straight section of the exact same forged dark-steel chain links. Row 1 Col 3: 45-degree diagonal section of the exact same forged dark-steel chain links. Row 1 Col 4: Heavy 3D SPIKED MORNING STAR FLAIL BALL at the end of 1 steel chain link. Row 2 Col 1: Horizontal straight section of thick BRAIDED DARK-BROWN LEATHER WHIP. Row 2 Col 2: 45-degree diagonal braided leather whip. Row 2 Col 3: Tapered braided leather WHIP TIP curving slightly upward. Row 2 Col 4: Ornate Gothic leather-wrapped WHIP HANDLE with antique burnished brass pommel and iron guard collar. Pure solid #000000 black background.
```

### 3. Stage 01 Fehlende Gegner Teil 1 (F6 Knochensäule V2, F6 Feuerball, F1 Medusa-Köpfe, F2 Geist, F10 Schwung-Fledermaus)
- **Referenzen:** `04_Stage01_Missing_Part1_4x2_REF.png`
- **Zieldatei:** `04_Higgsfield_Output/04_Stage01_Missing_Part1_HD.png`
- **Prompt:**
```text
Remaster this 4x2 Super Castlevania IV pixel-art enemy sprite sheet into high-detail dark-gothic oil-painted HD game sprites on a PURE SOLID BLACK (#000000) background with ZERO grid lines, ZERO text, ZERO floor shadows. Keep the EXACT silhouette, orientation, proportions, and mouth/head heights of EVERY cell 1:1: Row 1 Col 1 = Two-Headed Horse-Skull Bone Pillar (both skulls facing RIGHT at the EXACT vertical heights of the reference so fireballs align with their mouths, ivory aged bone with dark sockets); Row 1 Col 2 = Glowing gothic orange-red Fireball; Row 1 Cols 3-4 = Floating stone-and-flesh Medusa Head with writhing snakes (2 animation frames); Row 2 Col 1 = Glowing spectral Ghost Spawn Orb; Row 2 Cols 2-3 = Haunted pale skeletal Phantom Ghost (2 frames); Row 2 Col 4 = Hanging purple gothic Gargoyle-Bat clutching a forged iron whip-swing ring. Completely solid opaque sprites on pure #000000 black.
```

### 4. Stage 01 Fehlende Gegner Teil 2 (F10 Säulen-Monster 0x73 & F5 Deckenschleim 0x32)
- **Referenzen:** `05_Stage01_Missing_Part2_4x2_REF.png`
- **Zieldatei:** `04_Higgsfield_Output/05_Stage01_Missing_Part2_HD.png`
- **Prompt:**
```text
Remaster this 4x2 Super Castlevania IV pixel-art enemy sprite sheet into high-detail dark-gothic oil-painted HD game sprites on a PURE SOLID BLACK (#000000) background with ZERO grid lines, ZERO text, ZERO floor shadows. Match EVERY cell's exact silhouette, pose, and orientation 1:1: Row 1 Col 1 = Mossy armored undead ghoul hand emerging upward; Row 1 Col 2 = Undead ghoul head/shoulders peeking out; Row 1 Col 3 = Armored green-mossy Stone Pillar Ghoul rising up; Row 1 Col 4 = Pillar Ghoul raising a heavy blood-stained wooden club; Row 2 Col 1 = Pillar Ghoul smashing the wooden club downward; Row 2 Cols 2-4 = Three animation frames of the thorny dark-green gothic Ceiling Slime tentacle crawler on the floor. Completely solid opaque sprites on pure #000000 black.
```

---

## Universal-Prompt für ALLE Bosse (`02_Alle_Bosse_1x_Sheets/`) & ALLE Monster (`03_Alle_Monster_1x_Sheets/`)
Für jedes `*_4x2_REF.png` einfach das Referenzbild anhängen und diesen Prompt senden (Zieldatei = entsprechender `output_stem` aus `sheet_manifest.json` in `04_Higgsfield_Output/`):
```text
Remaster this 4x2 Super Castlevania IV pixel-art monster/boss sprite sheet into high-detail dark-gothic oil-painted HD game sprites (consistent with Castlevania dark baroque oil-painting aesthetic: weathered bone, forged dark iron, tattered cloth, moody rim lighting) on a PURE SOLID BLACK (#000000) background with ZERO grid lines, ZERO text, ZERO labels, ZERO floor shadows. CRITICAL: Preserve the EXACT 4x2 grid layout, facing direction, silhouette, limb positions, and relative proportions of EVERY single cell 1:1 so animations stay rock-solid without jitter. Keep all character interiors 100% solid opaque (no black holes inside sprites), pure #000000 background only outside the sprites.
```
"""
    (KIT / "PROMPTS_CLAUDE_HIGGSFIELD.md").write_text(prompts_md, encoding="utf-8")
    print(f"Prepared complete Higgsfield/Claude Kit in: {KIT}")
    print(f"  Priority sheets : 6")
    print(f"  Boss sheets     : {len(manifest['boss_sheets'])} ({total_boss_poses} poses across {len(boss_frames_by_type)} bosses)")
    print(f"  Monster sheets  : {len(manifest['monster_sheets'])} ({total_mon_poses} poses)")


if __name__ == "__main__":
    main()
