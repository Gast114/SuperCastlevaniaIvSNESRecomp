"""Rebuild warp_thumbs/rooms.json (+ the C++ fallback table) from the HUD-decoded
BLOCK X-Y numbers and the ROM-verified boss rooms.

Boss rooms come from the original boss table (tools/enemy_catalog_profiles.py
_BOSSES: Rowdain 7, Medusa 9, Puwexyl 20, Koranot 23, 0x85 Dancing Specters 34,
Sir Grakul 41, Frankenstein 45, Zapf Bat 53, Akmodan II 59, Slogra 63,
Gaibon 64, Death 65). Orphic Vipers (17) and Dracula (67) are the last room of
their block and are not in that table."""
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
THUMBS = ROOT / "warp_thumbs"

BOSS = {7: "Rowdain", 9: "Medusa", 17: "Orphic Vipers", 20: "Puwexyl", 23: "Koranot",
        34: "Dancing Specters", 41: "Sir Grakul", 45: "Frankenstein", 53: "Zapf Bat",
        59: "Akmodan II", 63: "Slogra", 64: "Gaibon", 65: "Death", 66: "Dracula"}

src = json.loads((THUMBS / "rooms.json").read_text(encoding="utf-8"))["rooms"]
blk = {r["room"]: (r["stage"], r["section"]) for r in src}

rooms = []
for r in range(67):  # R-67 is an unused/corrupt room (garbled graphics) and is not offered
    st, sec = blk[r]
    label = f"{st:X}-{sec}"
    if r == 66:
        label += " · Final Boss: Dracula"
    elif r in BOSS:
        label += f" · Boss: {BOSS[r]}"
    rooms.append(dict(room=r, stage=st, stage_name=f"Block {st:X}", section=sec,
                      label=label, boss=r in BOSS, image=f"room_{r:02d}.png"))

payload = json.dumps({"version": 1, "rooms": rooms}, ensure_ascii=False, indent=2) + "\n"
for d in ("warp_thumbs", "build-play/game/warp_thumbs", "build/warp_thumbs", "build-lua/warp_thumbs"):
    p = ROOT / d / "rooms.json"
    if p.parent.is_dir():
        p.write_text(payload, encoding="utf-8")

# C++ fallback (used only when rooms.json is missing)
table = ",".join(f"{{{blk[r][0]},{blk[r][1]}}}" for r in range(67))
bosses = ",".join(f'{{{r},"{n}"}}' for r, n in sorted(BOSS.items()))
cpp = ROOT / "src" / "stage_warp.cpp"
text = cpp.read_text(encoding="utf-8")
start = text.index("static void PopulateFallbackRooms() {")
end = text.index("static void EnsureLoaded() {")
fallback = f'''static void PopulateFallbackRooms() {{
  // HUD-decoded BLOCK X-Y per room and ROM-verified boss rooms.
  static const int kBlock[68][2] = {{{table}}};
  static const std::map<int, const char *> kBosses = {{{bosses}}};
  g_rooms.clear();
  for (int r = 0; r < 67; ++r) {{
    WarpRoom wr;
    wr.room = r;
    wr.stage = kBlock[r][0];
    wr.section = kBlock[r][1];
    char buf[96];
    std::snprintf(buf, sizeof(buf), "Block %X", wr.stage);
    wr.stage_name = buf;
    auto it = kBosses.find(r);
    wr.boss = (it != kBosses.end());
    std::snprintf(buf, sizeof(buf), "%X-%d", wr.stage, wr.section);
    wr.label = buf;
    if (wr.boss) {{ wr.label += r == 66 ? " · Final Boss: " : " · Boss: "; wr.label += it->second; }}
    char img[32];
    std::snprintf(img, sizeof(img), "room_%02d.png", r);
    wr.image = img;
    g_rooms.push_back(std::move(wr));
  }}
}}

'''
cpp.write_text(text[:start] + fallback + text[end:], encoding="utf-8")

# keep the screenshot script consistent
sh = ROOT / "tools" / "build_stage_warp_thumbs.py"
s = sh.read_text(encoding="utf-8")
s = re.sub(r"BOSS_ROOMS = \{.*?\n\}\n", "BOSS_ROOMS = {" + ", ".join(f'{r}: "Boss: {n}"' for r, n in sorted(BOSS.items())) + "}\n", s, flags=re.S)
s += "\n# NOTE: labels/boss rooms are finalised by tools/fix_warp_labels.py (HUD-decoded BLOCK X-Y + ROM boss table).\n"
sh.write_text(s, encoding="utf-8")

for r in (7, 9, 17, 20, 23, 34, 41, 45, 53, 59, 63, 64, 65, 66):
    print(r, rooms[r]["label"])

