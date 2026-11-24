"""Syncs hd-stage01 enemy pack into all game runtime directories AND into
the Monster-Werkstatt live workspace (Assets (ausgeschnitten)/Gegner/Werkstatt/artwork)
so every imported HD monster/boss is immediately testable in HD in both the game
and the Monster-Werkstatt's Redesign preview pane.
"""
import json
import pathlib
import shutil
from PIL import Image

ROOT = pathlib.Path(r"D:\Super Castlevania IV Recomp\SuperCastlevaniaIvSNESRecomp")
PACK_SRC = ROOT / "artwork-local" / "enemy-packs-hd" / "hd-stage01"
WS_DIR = pathlib.Path(r"D:\Super Castlevania IV Recomp\Assets (ausgeschnitten)\Gegner\Werkstatt")
RUNTIME_TARGETS = [
    ROOT / "build-play" / "game" / "enemy_packs",
    ROOT / "build" / "enemy_packs",
    ROOT / "build-lua" / "enemy_packs",
    ROOT / "enemy_packs",
]


def sync_runtime_packs() -> None:
    for target_root in RUNTIME_TARGETS:
        target_root.mkdir(parents=True, exist_ok=True)
        dest = target_root / "hd-stage01"
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(PACK_SRC, dest)
        (target_root / "selected.txt").write_text("hd-stage01\n", encoding="utf-8")
        print(f"[SYNC] Runtime pack updated: {dest}")


def composite_onto_ws_canvas(hd_img: Image.Image, pf: dict, wf: dict) -> Image.Image:
    """Places hd_img (described by pf['display_size'] and pf['anchor']) onto a
    proportional HD canvas matching wf['display_size'] and wf['anchor'] so
    enemy_workshop_assets.Workspace.image() accepts it without aspect-ratio error
    and aligns it identically to the native SNES anchor."""
    p_dw, p_dh = pf["display_size"]
    p_ax, p_ay = pf["anchor"]
    w_dw, w_dh = wf["display_size"]
    w_ax, w_ay = wf["anchor"]

    # Determine scale factor of hd_img relative to p_dw/p_dh (typically 8.0)
    sx = hd_img.width / float(p_dw)
    sy = hd_img.height / float(p_dh)
    scale = (sx + sy) / 2.0

    # Clamp scale so output never exceeds 4096px (Workspace limit)
    max_dim = max(w_dw, w_dh)
    if max_dim * scale > 4096:
        scale = 4096.0 / max_dim
    # Use integer scale if very close, otherwise rounded canvas
    if abs(scale - round(scale)) < 0.05 and round(scale) >= 1:
        scale = float(round(scale))

    out_w = max(1, int(round(w_dw * scale)))
    out_h = max(1, int(round(w_dh * scale)))

    # If hd_img already matches exact dimensions and anchor, return directly
    if (
        hd_img.width == out_w
        and hd_img.height == out_h
        and p_dw == w_dw
        and p_dh == w_dh
        and p_ax == w_ax
        and p_ay == w_ay
    ):
        return hd_img

    # Resize hd_img to match target scale if scale changed
    src_w = max(1, int(round(p_dw * scale)))
    src_h = max(1, int(round(p_dh * scale)))
    if hd_img.width != src_w or hd_img.height != src_h:
        src = hd_img.resize((src_w, src_h), Image.Resampling.LANCZOS)
    else:
        src = hd_img

    canvas = Image.new("RGBA", (out_w, out_h), (0, 0, 0, 0))
    paste_x = int(round((w_ax - p_ax) * scale))
    paste_y = int(round((w_ay - p_ay) * scale))
    canvas.paste(src, (paste_x, paste_y), src)
    return canvas


def sync_workshop_artwork() -> tuple[int, int, list[int]]:
    pack_json = PACK_SRC / "enemies.json"
    ws_json = WS_DIR / "project.json"
    if not pack_json.is_file() or not ws_json.is_file():
        print("[WARN] Missing enemies.json or Werkstatt project.json")
        return 0, 0, []

    pack = json.loads(pack_json.read_text(encoding="utf-8"))
    ws = json.loads(ws_json.read_text(encoding="utf-8"))

    ws_by_id = {f["id"]: f for f in ws.get("frames", [])}
    ws_by_ap: dict[tuple[int, int], list[dict]] = {}
    for f in ws.get("frames", []):
        if not f.get("component", False):
            ws_by_ap.setdefault((f["actor_type"], f["pose"]), []).append(f)

    artwork_dir = WS_DIR / "artwork"
    artwork_dir.mkdir(parents=True, exist_ok=True)

    written_files = set()
    matched_frames = 0
    matched_actors = set()

    for pf in pack.get("frames", []):
        img_path = PACK_SRC / pf["image"]
        if not img_path.is_file():
            continue

        targets: list[dict] = []
        pid = pf.get("id")
        if pid and pid in ws_by_id:
            targets = [ws_by_id[pid]]
        else:
            key = (pf["actor_type"], pf["pose"])
            if key in ws_by_ap:
                targets = ws_by_ap[key]

        if not targets:
            continue

        with Image.open(img_path) as im:
            hd_img = im.convert("RGBA")
            hd_img.load()

        for wf in targets:
            out_path = artwork_dir / wf["image"]
            comp = composite_onto_ws_canvas(hd_img, pf, wf)
            comp.save(out_path, "PNG")
            written_files.add(wf["image"])
            matched_frames += 1
            matched_actors.add(wf["actor_type"])

    print(
        f"[SYNC] Monster-Werkstatt updated: {len(written_files)} unique HD PNGs "
        f"({matched_frames} frame bindings across {len(matched_actors)} actor types: {sorted(matched_actors)})"
    )
    return len(written_files), matched_frames, sorted(matched_actors)


if __name__ == "__main__":
    sync_runtime_packs()
    sync_workshop_artwork()
