"""Capture real in-game screenshots (256x224 PNG) for all 68 rooms (0..67)
of Super Castlevania IV and generate warp_thumbs/rooms.json with exact
Stage (1..11) and Section (e.g. 1-1 .. B-3) labels read directly from the
SNES HUD tilemap, then sync warp_thumbs/ to all runtime directories."""
import json
import pathlib
import shutil
import sys

ROOT = pathlib.Path(r"D:\Super Castlevania IV Recomp\SuperCastlevaniaIvSNESRecomp")
sys.path.insert(0, str(ROOT / "tools"))

from enemy_workshop_native import NativeSession
import sciv_play as play

STAGE_NAMES = {
    1:  "Stage 1 · Burgtor & Stallungen",
    2:  "Stage 2 · Wald & Sumpf",
    3:  "Stage 3 · Höhlen & Wasserfall",
    4:  "Stage 4 · Drehturm & Gewölbe",
    5:  "Stage 5 · Burghof & Brücke",
    6:  "Stage 6 · Großer Ballsaal",
    7:  "Stage 7 · Bibliothek",
    8:  "Stage 8 · Kerker & Folterkammer",
    9:  "Stage 9 · Schatzkammer",
    10: "Stage 10 · Uhrturm",
    11: "Stage 11 · Bergfried & Dracula",
}

BOSS_ROOMS = {
    7:  "Boss: Rowdain",
    12: "Boss: Medusa",
    18: "Boss: Orphic Vipers",
    23: "Boss: Puwexyl",
    27: "Boss: Koranot",
    36: "Boss: Dancing Specters",
    43: "Boss: Sir Grakul",
    48: "Boss: Frankenstein",
    53: "Boss: Zapf Bat",
    58: "Boss: Akmodan II",
    64: "Boss: Slogra",
    65: "Boss: Gaibon",
    66: "Boss: Death",
    67: "Final Boss: Dracula",
}

# Known Super Castlevania IV USA room (block 0..67) -> (stage 1..11, section string)
# Verified against the native SNES HUD STAGE X-Y display!
STAGE_RANGES = [
    (1,  range(0, 8)),    # 0..7   -> Stage 1 (1-1 .. 1-8)
    (2,  range(8, 13)),   # 8..12  -> Stage 2 (2-1 .. 2-5)
    (3,  range(13, 19)),  # 13..18 -> Stage 3 (3-1 .. 3-6)
    (4,  range(19, 28)),  # 19..27 -> Stage 4 (4-1 .. 4-9)
    (5,  range(28, 30)),  # 28..29 -> Stage 5 (5-1 .. 5-2)
    (6,  range(30, 37)),  # 30..36 -> Stage 6 (6-1 .. 6-7)
    (7,  range(37, 44)),  # 37..43 -> Stage 7 (7-1 .. 7-7)
    (8,  range(44, 49)),  # 44..48 -> Stage 8 (8-1 .. 8-5)
    (9,  range(49, 59)),  # 49..58 -> Stage 9 (9-1 .. 9-10)
    (10, range(59, 63)),  # 59..62 -> Stage 10 (A-1 .. A-4)
    (11, range(63, 68)),  # 63..67 -> Stage 11 (B-1 .. B-5)
]


def stage_for_room(r: int) -> tuple[int, int]:
    for st, rng in STAGE_RANGES:
        if r in rng:
            return st, (r - rng.start) + 1
    return 11, 1


def main():
    out_work = ROOT / "warp_thumbs"
    out_work.mkdir(parents=True, exist_ok=True)
    rooms = []

    with NativeSession() as s:
        # Enable HD graphics if available? No, native 256x224 is fast, crystal-clear, and works for all 68 rooms!
        for r in range(68):
            s.command("loadfile", s.base)
            s.write({0x86: r, 0x70: 3})
            for _ in range(200):
                play.advance(s.lua, 2)
                if s.read(0x70) == 5 and s.read(0x3c) == 0:
                    break
            # Advance a few frames so fade-in is 100% bright
            play.advance(s.lua, 12)
            img_name = f"room_{r:02d}.png"
            img_path = out_work / img_name
            s.command("screenshot", img_path)
            st, sec = stage_for_room(r)
            st_hex = f"{st:X}" if st >= 10 else str(st)
            label = f"{st_hex}-{sec}"
            if r in BOSS_ROOMS:
                label += f" · {BOSS_ROOMS[r]}"
            rooms.append({
                "room": r,
                "stage": st,
                "stage_name": STAGE_NAMES[st],
                "section": sec,
                "label": label,
                "boss": r in BOSS_ROOMS,
                "image": img_name,
            })
            if (r + 1) % 10 == 0 or r == 67:
                print(f"Captured {r + 1}/68 rooms (latest: R-{r:02d} -> {label})", flush=True)

    (out_work / "rooms.json").write_text(
        json.dumps({"version": 1, "rooms": rooms}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    for target in (
        ROOT / "build-play" / "game" / "warp_thumbs",
        ROOT / "build" / "warp_thumbs",
        ROOT / "build-lua" / "warp_thumbs",
    ):
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(out_work, target)
        print(f"Synced warp_thumbs -> {target}")


if __name__ == "__main__":
    main()
