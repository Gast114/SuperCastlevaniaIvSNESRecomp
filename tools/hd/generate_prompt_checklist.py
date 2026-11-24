#!/usr/bin/env python3
"""Generate the master ALLE_SPRITE_PROMPTS_CHECKLISTE.md (v3 — Official Castlevania IV Bestiary Lore
+ 26 COMPLETE silhouettes-deduplicated Boss sheets + 56 1:1 ROM-matched Enemy sheets + 123 Level sheets)
and export `bestiary_lore.json` for optional Monster-Werkstatt UI integration!"""

import json
from pathlib import Path

KIT = Path(r"D:\Super Castlevania IV Recomp\Assets (ausgeschnitten)\Higgsfield_Vorbereitung")

# Official Castlevania IV Bestiary (Castlevania Wiki) lore + visually verified colors/materials
BOSS_LORE = {
    "Boss_Medusa": {
        "canon_name": "Medusa (Gorgon Queen)", "stage": "Stage 2", "actor_type": "0x83",
        "de": "Gorgonenkönigin mit Schlangenhaar und smaragdgrünem Schlangenschwanz; greift mit Versteinerungsringen an.",
        "prompt_desc": "Medusa, Gorgon Queen boss of Super Castlevania IV Stage 2 (glossy emerald-green scaly serpent tail, warm bronze human torso, writhing snakes, petrifying energy rings)",
    },
    "Boss_Orphic_Vipers": {
        "canon_name": "Orphic Vipers", "stage": "Stage 3", "actor_type": "0x81",
        "de": "Zweiköpfiges Wasser-/Knochendrachen-Paar in der unterirdischen Wasserhöhle; speit Feuer und Wasserkugeln.",
        "prompt_desc": "Orphic Vipers, Stage 3 twin-headed serpentine cave-dragon boss (weathered bony dragon heads, segmented scaly necks, glowing eyes, water/fire projectiles)",
    },
    "Boss_Puwexyl": {
        "canon_name": "Puweyxil (Death Breath Head)", "stage": "Stage 4", "actor_type": "0x84",
        "de": "Riesiger schwebender brennender Schädel in Stage 4; greift mit langer Zunge und Giftatem an.",
        "prompt_desc": "Puweyxil (Death Breath Head), Stage 4 giant floating fiery burnt-orange/ochre weathered bone skull boss with deep dark eye sockets, jagged teeth, and sinuous tongue",
    },
    "Boss_Koranot": {
        "canon_name": "Koranot (Stone Guardian)", "stage": "Stage 4", "actor_type": "0x82",
        "de": "Riesiger belebter Sandstein-Golem aus Mauerblöcken; springt und teilt sich in kleinere Golems.",
        "prompt_desc": "Koranot, Stage 4 massive animated sandstone-and-brick stone guardian golem boss (cracked warm ochre stone blocks, glowing runes, heavy stone fists)",
    },
    "Boss_Dancing_Specters": {
        "canon_name": "Dancing Spectres (Paula Abghoul & Fred Askare)", "stage": "Stage 6", "actor_type": "0x8b",
        "de": "Viktorianisches Ballsaal-Geisterpaar im Walzertanz (grauer Frack & fließendes rotes Ballkleid).",
        "prompt_desc": "The Dancing Spectres (Paula Abghoul & Fred Askare), Stage 6 aristocratic 19th-century Victorian ballroom waltzing ghosts (pale grey-suited gentleman & lady in flowing crimson-orange gown)",
    },
    "Boss_Sir_Grakul": {
        "canon_name": "Sir Grakul", "stage": "Stage 7", "actor_type": "0x8a",
        "de": "Schwer gepanzerter Bronze-/Eisenritter mit rotem Helmbusch, Rundschild und gewaltiger Hellebarde.",
        "prompt_desc": "Sir Grakul, Stage 7 heavily armored ornate antique-bronze and forged-iron gothic knight boss with bright crimson-red helmet plume, round shield, and massive steel halberd axe",
    },
    "Boss_Frankenstein": {
        "canon_name": "Frankenstein's Monster (The Creature)", "stage": "Stage 8", "actor_type": "0x87",
        "de": "Das Monster im zerrissenen olivbraunen Mantel mit blaugrauer vernähter Haut; wirft Alchemie-Flaschen und Blitze.",
        "prompt_desc": "Frankenstein's Monster (The Creature), Stage 8 hulking stitched undead giant in tattered olive-brown coat, pale blue-grey stitched skin, flat-topped dark hair, heavy boots, and glowing alchemical flasks",
    },
    "Boss_Zapf_Bat": {
        "canon_name": "Zapf Bat (Treasure Bat)", "stage": "Stage 9", "actor_type": "0x86",
        "de": "Riesige goldene Schatz-Vampirfledermaus aus funkelnden Gold- und Edelstein-Mosaikplättchen.",
        "prompt_desc": "Zapf Bat (Treasure Bat), Stage 9 giant golden-amber vampire bat composed of glittering faceted gold-and-bronze mosaic tiles studded with sparkling cyan, pink, and gold jewels",
    },
    "Boss_Akmodan_II": {
        "canon_name": "Akmodan II (Mummy Lord)", "stage": "Stage 9", "actor_type": "0x8c",
        "de": "Uralter verfluchter ägyptischer Mumienfürst in verwitterten ockerbraunen Leinenbinden.",
        "prompt_desc": "Akmodan II, Stage 9 ancient cursed Egyptian mummy lord tightly wrapped in weathered ochre-brown tattered linen bandages",
    },
    "Boss_Slogra": {
        "canon_name": "Slogra", "stage": "Stage 11", "actor_type": "0x89",
        "de": "Schnabel-Skelettdämon mit langem Speer (Phase 1) und blanken Klauen (Phase 2) in Draculas Turm.",
        "prompt_desc": "Slogra, Stage 11 beaked ochre-brown skeletal bird-demon warrior with long curved skull beak, glowing blue eye, ribbed torso, tail, weathered dark-iron silver-tipped spear and sharp claws",
    },
    "Boss_Gaibon": {
        "canon_name": "Gaibon", "stage": "Stage 11", "actor_type": "0x88",
        "de": "Muskulöser königsblauer Gargoyle-Dämon mit Fledermausflügeln und leuchtend magentafarbenen Augen.",
        "prompt_desc": "Gaibon, Stage 11 muscular deep royal-blue winged gargoyle demon with glowing magenta-pink eyes, horned head, sharp claws, and dark teal-edged bat wings",
    },
    "Boss_Death": {
        "canon_name": "Death (The Grim Reaper)", "stage": "Stage 11", "actor_type": "0x89",
        "de": "Der Sensenmann in zerrissener mitternachtsblauer Kapuzenrobe mit goldenem Amulett, großer Silbersense und fliegenden Sicheln.",
        "prompt_desc": "Death (The Grim Reaper), Stage 11 hooded midnight-blue tattered cloak, skeletal ivory skull face, golden medallion necklace, huge gleaming silver scythe and swirling silver sickle slashes",
    },
    "Boss_Dracula": {
        "canon_name": "Count Dracula", "stage": "Stage 11 (Final)", "actor_type": "0x85",
        "de": "Graf Dracula im dunklen indigo-schwarzen Umhang mit blutrotem Innenfutter, hohem Kragen und bleichem Adelsgesicht.",
        "prompt_desc": "Count Dracula, Final Boss aristocratic gothic vampire lord in dark indigo-black flowing cloak with crimson-red inner lining, high ornate collar, pale noble face, and dark magic flames",
    },
}

ENEMY_DETAILS = {
    "Armor_Knight": "Axe Armor / Knight (bronze-and-iron medieval knight with horned helmet and pale bronze-ivory tower shield)",
    "Banshee": "Banshee / Wraith (spectral golden-yellow robed female ghost raising glowing emerald-green skeletal hands)",
    "Bat": "Bat / Batton (dark slate-grey gothic vampire bat with crimson-red inner wings)",
    "Black_Panther": "Black Panther / Dead Mate (sleek muscular charcoal-black and dark slate-blue prowling panther)",
    "Blood_Hound": "Hellhound / Zombie Dog (ferocious fiery orange-red demonic hound leaping and running)",
    "Bone_Dragon": "Bone Dragon / White Dragon (segmented pale ivory-bone skeletal dragon neck & horned skull)",
    "Bone_Pillar": "Pillar of Bones (stacked double horse-skull bone pillar in aged ivory bone)",
    "Centipede": "Larva / Fiery Centipede segment (glowing crimson-orange armored multi-legged fiery bug segment)",
    "Crawling_Ghoul": "Ground Zombie / Crawling Ghoul (tattered rotting brown-ochre legless undead ghoul crawling low)",
    "Crawling_Hand": "Crawling Hand (severed pale-greenish rotting undead skeletal hand scuttling on its fingers)",
    "Crow": "Crow / Raven (dark blue-black gothic raven with bright orange beak and talons)",
    "Dullahan": "Headless Hunter / Dullahan (deep royal-purple armored headless knight wielding silver lance/sword)",
    "Ectoplasm": "Poltergeist / Ghost (pale ghostly ivory-white haunted floating skeletal phantom & glowing spectral spawn orbs)",
    "Flying_Book": "Magic Book (burgundy-red leather-bound antique gothic spellbooks flapping open like wings)",
    "Frog": "Frog / Korochen (emerald-green spotted swamp frog crouching and mid-leap)",
    "Ghost_Couple": "Dancing Spectres / Ballroom Ghost Couple (19th-century Victorian gentleman in grey suit & lady in crimson gown)",
    "Ghost_Man": "Ballroom Ghost Man (19th-century Victorian spectral gentleman in pale grey tailcoat)",
    "Ghost_Woman": "Ballroom Ghost Woman (19th-century Victorian spectral noblewoman in flowing crimson-orange gown)",
    "Gold_Skeleton": "Gold Skeleton (gleaming burnished-gold metallic skeletal warrior)",
    "Gold_Whip_Skeleton": "Gold Whip Skeleton (gleaming burnished-gold metallic skeletal warrior cracking a golden whip)",
    "Hands": "Stage 02 Ground Hands (creepy disembodied muddy undead hands rising out of the earth)",
    "Harpy": "Harpy (winged gothic harpy with warm brown feathered eagle wings, pale torso, and clawed talons)",
    "Haunted_Painting": "Haunted Painting Ghost (spectral Victorian noblewoman emerging from a haunted gothic portrait)",
    "Horse_Head": "Mr. Hed / Flying Horse Head (floating ghostly burnt-orange severed horse head with fiery mane)",
    "Lantern_Man": "Lantern Man / Night Watchman (hunched Victorian watchman in tattered pale trenchcoat & bowler hat with glowing yellow lantern)",
    "Man_Bat": "Man-Bat / Ogideran Gargoyle (dark emerald-green muscular winged gargoyle demon)",
    "Medusa_Head": "Medusa Head (floating weathered stone-and-ivory Medusa head with writhing serpents for hair)",
    "Merman": "Merman (orange-copper scaly fish-man with violet-purple webbed fins spitting pale-blue water/ice jets)",
    "Moving_Chair": "Poltergeist Chair (antique dark mahogany-brown carved gothic wooden dining chair)",
    "Moving_Table": "Poltergeist Table (long antique carved mahogany-brown gothic banquet table with white linen cloth)",
    "Mud_Man": "Mud Man / Kiggaa Pillar Ghoul (mossy dark-green armored undead ghoul emerging hand-first with weathered iron-studded club)",
    "Peeping_Eye": "Peeping Eye (floating fiery orange-amber bloodshot demonic eyeball)",
    "Red_Skeleton": "Red Skeleton (blood-crimson undead skeleton walking and collapsing into a flat pile of crimson bones)",
    "Rock_Golem": "Brick Doll / Rock Golem (muscular warm sandstone-ochre carved stone giant golem in large, medium, and small sizes)",
    "Skeleton": "Skeleton / Bone Chukker (classic weathered ivory-white undead skeleton warrior)",
    "Skeleton_Knight": "Skeleton Soldier / Knight (pale-gold and aged-ivory armored skeleton swordsman with steel broadsword)",
    "Spider": "Spider (hairy reddish-brown gothic dungeon spider hanging on a vertical silk thread)",
    "Spike_Lizard": "Needle Lizard (fiery orange-red armored spiky lizard curling into a spiked ball)",
    "Spore": "Fuzz Buster / Keseran Pasaran (glowing pale seafoam-cyan spiky floating fungal spore orb)",
    "Stone_Man": "Animated Statue / Stone Man (weathered grey-brown mossy carved stone statue warrior)",
    "Swamp_Vines": "Une / Swamp Vines (gnarled dark moss-green thorny swamp vines creeping along the ground)",
    "Tentacles": "Ceiling Slime Tentacles (writhing dark sea-green thorny organic gothic slime crawler)",
    "Vampire_Coffin": "Vampire Coffin (ornate dark crimson-mahogany gothic wooden vampire coffin with iron trim opening in stages)",
    "Wall_Skeleton": "Hanging / Wall Skeleton (weathered ivory-white skeleton chained to a dark dungeon wall)",
    "Whip_Skeleton": "Whip Skeleton (weathered ivory-bone skeletal warrior cracking a long leather/chain whip)",
    "Winged_Guard": "Winged Guard / Gargoyle Knight (weathered olive-green stone gargoyle warrior with crimson-red tower shield)",
    "Zombie": "Zombie / Cruela (rotting olive-green undead zombie in tattered muddy coat rising from the ground)",
    "Spear_Knight_Library": "Spear Knight / Guard (pale silver-ivory armored medieval knight from the Library thrusting a long steel-and-bronze spear)",
    "Crimson_Moth": "Crimson Moth (fiery crimson-red and dark-iron winged gothic moth, 3 wing-flap poses)",
    "Winged_Imp_Gremlin": "Gremlin / Imp (fiery burnt-orange and dark-brown winged dungeon gremlin)",
    "Chandelier_Plasma_Orb": "Chandelier Energy Orb (glowing violet-purple electrical energy orbs)",
    "Blood_Plasma_Drop": "Crimson Droplet (glowing dark crimson-red liquid droplet blob)",
    "Enemy_Projectiles_Mix": "Enemy Projectiles (glowing pale-violet ice beam, lavender magic orbs, bronze-ivory shield/arm)",
    "Dungeon_Spike_Traps": "Dungeon Spike Traps (violet-iron ceiling spike crusher plate, mossy ceiling spikes, forged-steel vertical spear shaft)",
}


def main():
    # Export structured Castlevania IV Bestiary Lore JSON for Monster-Werkstatt integration!
    lore_out = {
        "source": "Castlevania Wiki (Super Castlevania IV Bestiary) + visual 1x verification",
        "bosses": BOSS_LORE,
        "enemies": ENEMY_DETAILS,
    }
    (KIT / "bestiary_lore.json").write_text(json.dumps(lore_out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    tracker = json.loads((KIT / "higgsfield_job_tracker.json").read_text(encoding="utf-8"))
    running = {j["target"]: j["job_id"] for j in tracker["jobs"] if j.get("status") == "waiting"}
    out_dir = KIT / "04_Higgsfield_Output"
    done_stems = {p.stem for p in out_dir.glob("*.png")} | {p.stem for p in out_dir.glob("*.jpg")}

    boss_manifest = json.loads((KIT / "02_Alle_Bosse_1x_Sheets" / "boss_complete_manifest.json").read_text(encoding="utf-8"))
    lvl_manifest = json.loads((KIT / "05_Alle_Level_Hintergruende_und_Tilesets" / "level_manifest.json").read_text(encoding="utf-8"))
    einzel_files = sorted((KIT / "06_Einzelmonster_Aus_Sprites").glob("*_4x2_REF.png"))

    lines = [
        "# Super Castlevania IV HD — Master Prompt-Checkliste v3 (Vollständige Sprites + Castlevania-Wiki-Lore)",
        "",
        "> **Anweisung für Prüf-/Verwaltungs-Modell (leichtes Modell genügt!):**",
        '> 1. Rufe `higgsfield.show_generations(only_completed=False, size=24, type="image")` auf (0 Credits, rein lesend).',
        "> 2. Für jeden Job mit `status == completed`: Lade die `url` in den angegebenen `Ziel`-Pfad herunter, setze den Haken hier auf `[x]` und starte `import_higgsfield_sheets.py` (Sprites/Bosse) bzw. `import_higgsfield_levels.py` (Level).",
        "> 3. Zähle aktive Jobs (`waiting` / `in_progress`). Higgsfield erlaubt max. **8 gleichzeitig** (und max. **6 pro `generate_image_batch`-Aufruf**, Rest separat).",
        '> 4. Nimm exakt die nächsten `8 - aktive` Einträge mit `[ ]` aus dieser Liste, kopiere deren **Dateipfade + Prompts 1:1 unverändert** in einen Fire-and-Forget `generate_image_batch`-Befehl (`model: "nano_banana_pro"`, `resolution: "2k"`, `use_unlim: true`, **KEIN `jobs_wait`!**) für ChatGPT und markiere sie nach Rückmeldung der `job_id`s mit `[~]`.',
        "",
        "**Legende:** `[ ]` offen | `[~]` läuft in Higgsfield-Queue (mit `job_id`) | `[x]` fertig heruntergeladen & im Spiel eingebaut",
        "",
    ]

    def status_box(stem: str) -> str:
        if stem in done_stems:
            return "[x]"
        if stem in running:
            return f"[~] (job_id: `{running[stem]}`)"
        return "[ ]"

    # 1. Priorität Simon & Peitsche
    lines += ["---", "## 1. Priorität: Simon Belmont & Peitschen (noch offen: Stahlketten-/Lederpeitsche)", ""]
    prio_items = [
        ("01_Simon_V2_Idle_Walk_Duck_HD", [r"01_Prioritaet_Simon_und_Stage01\01_Simon_V2_Idle_Walk_Duck_4x2_REF.png", r"01_Prioritaet_Simon_und_Stage01\00_Simon_Style_Anchor.jpg"], r"04_Higgsfield_Output\01_Simon_V2_Idle_Walk_Duck_HD.png",
         "Remaster the 4x2 pixel-art sprite sheet from image 1 into high-detail dark-gothic oil-painted HD game sprites on a PURE SOLID BLACK (#000000) background with ZERO grid lines, ZERO text, ZERO floor, ZERO shadows on the background. Match the EXACT face, warm chestnut-brown hair with headband, warm bronze skin tone, dark riveted slate-blue iron cuirass, pauldrons, faulds, greaves, gold-trimmed belt, and brown boots from image 2 across ALL 8 poses with 100% IDENTICAL color tone, lighting, head size, and body height."),
        ("03_Simon_Whip_Components_HD", [], r"04_Higgsfield_Output\03_Simon_Whip_Components_HD.png",
         "Create a 16:9 (4 columns x 2 rows) dark-gothic oil-painted HD game-asset sprite sheet of Simon Belmont's Castlevania IV Whip Weapon Components on a PURE SOLID BLACK (#000000) background with ZERO grid lines, ZERO text, ZERO labels. Dramatic specular forged-steel highlights, weathered iron, braided dark brown leather, antique burnished brass. Row 1 Col 1: Horizontal straight section of heavy FORGED DARK-STEEL INTERLOCKING CHAIN LINKS. Row 1 Col 2: Vertical straight section of the exact same forged dark-steel chain links. Row 1 Col 3: 45-degree diagonal section of the exact same forged dark-steel chain links. Row 1 Col 4: Heavy 3D SPIKED MORNING STAR FLAIL BALL at the end of 1 steel chain link. Row 2 Col 1: Horizontal straight section of thick BRAIDED DARK-BROWN LEATHER WHIP. Row 2 Col 2: 45-degree diagonal braided leather whip. Row 2 Col 3: Tapered braided leather WHIP TIP curving slightly upward. Row 2 Col 4: Ornate Gothic leather-wrapped WHIP HANDLE with antique burnished brass pommel and iron guard collar. Pure solid #000000 black background."),
    ]
    for stem, refs, out_rel, prompt in prio_items:
        ref_str = ", ".join(f"`{r}`" for r in refs) if refs else "*(kein Referenzbild — Text-to-Image)*"
        lines += [
            f"- {status_box(stem)} **{stem}**",
            f"  - **Ref:** {ref_str}",
            f"  - **Ziel:** `{out_rel}` | **Format:** `16:9`, `2k`, `nano_banana_pro`, `use_unlim: true`",
            f"  - **Prompt:** `{prompt}`",
            "",
        ]

    # 2. Alle 26 vollständigen, silhouetten-deduplizierten Boss-Sheets!
    lines += ["---", f"## 2. Alle 13 Bosse — Vollständig & Silhouetten-Dedupliziert ({len(boss_manifest['sheets'])} Sheets)", ""]
    for bs in boss_manifest["sheets"]:
        stem = bs["output_stem"]
        boss_key = bs["boss"]
        lore = BOSS_LORE.get(boss_key, {"canon_name": boss_key, "stage": "", "prompt_desc": boss_key})
        rel_ref = Path(bs["ref_png"]).relative_to(KIT)
        prompt = (
            f"Remaster this 4x2 Super Castlevania IV boss sprite sheet of {lore['prompt_desc']} into high-detail dark-gothic oil-painted HD game sprites "
            f"(classic Castlevania dark baroque oil-painting aesthetic, rich weathered textures, dramatic rim lighting) on a PURE SOLID BLACK (#000000) background with ZERO grid lines, ZERO text, ZERO floor shadows. "
            f"Preserve the EXACT 4x2 grid layout, facing direction, silhouette, limb/weapon positions, and uniform scale of EVERY cell 1:1 with 100% identical color tone and lighting across all frames. "
            f"Keep all character interiors completely solid opaque (no black holes), pure #000000 background only outside the sprites."
        )
        lines += [
            f"- {status_box(stem)} **{stem}** — *{lore['canon_name']} ({lore['stage']}, {len(bs['cells'])} Posen)*",
            f"  - **Ref:** `{rel_ref}`",
            f"  - **Ziel:** `04_Higgsfield_Output\\{stem}.png` | **Format:** `16:9`, `2k`, `nano_banana_pro`, `use_unlim: true`",
            f"  - **Prompt:** `{prompt}`",
            "",
        ]

    # 3. Alle 56 1:1-ROM-verknüpften Einzelmonster-Sheets!
    lines += ["---", f"## 3. Alle Einzelmonster — 100 % 1:1 ROM-Verknüpft ({len(einzel_files)} Sheets)", ""]
    for ef in einzel_files:
        stem = ef.stem.replace("_4x2_REF", "_HD")
        base_key = ef.stem.replace("_4x2_REF", "").split("_Part")[0]
        desc = ENEMY_DETAILS.get(base_key, base_key.replace("_", " "))
        rel_ref = ef.relative_to(KIT)
        prompt = (
            f"Remaster this 4x2 Super Castlevania IV enemy sprite sheet of {desc} into high-detail dark-gothic oil-painted HD game sprites "
            f"(Castlevania dark baroque oil-painting aesthetic, rich weathered textures, crisp rim lighting) on a PURE SOLID BLACK (#000000) background with ZERO grid lines, ZERO text, ZERO floor shadows. "
            f"Preserve the EXACT 4x2 grid layout, facing direction, silhouette, limb positions, uniform scale, and foot baseline of EVERY cell 1:1 "
            f"with 100% identical colors and lighting across all frames. Keep all sprite interiors completely solid opaque (no black holes), pure #000000 background only outside the sprites."
        )
        lines += [
            f"- {status_box(stem)} **{stem}**",
            f"  - **Ref:** `{rel_ref}`",
            f"  - **Ziel:** `04_Higgsfield_Output\\{stem}.png` | **Format:** `16:9`, `2k`, `nano_banana_pro`, `use_unlim: true`",
            f"  - **Prompt:** `{prompt}`",
            "",
        ]

    # 4. Alle Level-Hintergründe BG2 (32) + BG1 (91)
    lines += ["---", f"## 4. Alle Level-Hintergründe BG2 — Stages 02–11 ({len(lvl_manifest['areas'])} Sheets)", ""]
    for area in lvl_manifest["areas"]:
        bg2 = area["bg2"]
        stem = bg2["output_stem"]
        rel_ref = Path(bg2["ref_png"]).relative_to(KIT)
        rooms_str = ", ".join(f"R{r:02d}" for r in area["rooms"])
        prompt = (
            f"Remaster this Super Castlevania IV 16-bit parallax background ({area['area_tag']}) into a rich, atmospheric dark-gothic oil-painted HD game background "
            f"(classic Castlevania dark baroque architecture, moody night lighting, weathered stone, misty atmosphere, dramatic rim lighting). "
            f"CRITICAL: Keep the EXACT pixel composition, horizon line, pillar/arch/tree/window positions, and seamless left-to-right wrapping 1:1 with the reference. No text, no borders, full edge-to-edge painting."
        )
        lines += [
            f"- {status_box(stem)} **{stem}** ({rooms_str})",
            f"  - **Ref:** `{rel_ref}`",
            f"  - **Ziel:** `05_Alle_Level_Hintergruende_und_Tilesets\\04_Level_Higgsfield_Output\\{stem}.png` | **Format:** `16:9`, `2k`, `nano_banana_pro`, `use_unlim: true`",
            f"  - **Prompt:** `{prompt}`",
            "",
        ]

    bg1_count = sum(len(a["bg1_sheets"]) for a in lvl_manifest["areas"])
    lines += ["---", f"## 5. Alle Level-Vordergrund-Blöcke BG1 — Stages 02–11 ({bg1_count} Sheets)", ""]
    for area in lvl_manifest["areas"]:
        for sh in area["bg1_sheets"]:
            stem = sh["output_stem"]
            rel_ref = Path(sh["ref_png"]).relative_to(KIT)
            prompt = (
                f"Remaster this 8x4 grid of 32x32 Super Castlevania IV foreground level tiles ({area['area_tag']}: platforms, stone bricks, wood beams, stairs, pillars, spikes, chains, gothic arches) "
                f"into ultra-crisp dark-gothic oil-painted HD game tiles on a PURE SOLID BLACK (#000000) background. "
                f"CRITICAL: Preserve the EXACT 8x4 grid cell boundaries, every platform top/bottom/left/right edge, stair angle, and silhouette 1:1 with zero shift so adjacent tiles connect seamlessly without seams! "
                f"Keep solid stone/wood/metal completely opaque, and keep empty background areas pure #000000 black."
            )
            lines += [
                f"- {status_box(stem)} **{stem}** ({len(sh['blocks'])} Blöcke)",
                f"  - **Ref:** `{rel_ref}`",
                f"  - **Ziel:** `05_Alle_Level_Hintergruende_und_Tilesets\\04_Level_Higgsfield_Output\\{stem}.png` | **Format:** `16:9`, `2k`, `nano_banana_pro`, `use_unlim: true`",
                f"  - **Prompt:** `{prompt}`",
                "",
            ]

    out_md = KIT / "ALLE_SPRITE_PROMPTS_CHECKLISTE.md"
    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    total = len(prio_items) + len(boss_manifest["sheets"]) + len(einzel_files) + len(lvl_manifest["areas"]) + bg1_count
    print(f"Wrote v3 checklist {out_md} ({total} items) + bestiary_lore.json!")


if __name__ == "__main__":
    main()
