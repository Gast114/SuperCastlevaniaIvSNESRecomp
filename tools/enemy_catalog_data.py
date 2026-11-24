"""Conservative workshop labels backed by the 2026-10-24 native catalog audit.

Verification means an exact native actor/OAM image was observed in a bounded
24/32-field probe. It does not establish all actions or a complete playthrough.
Enemy/object labels are visual descriptions, not claimed official enemy names.
Unknown entries stay unknown; a failed generic initialization is not absence.
Boss/controller profiles are supplied separately by the native workshop.
"""
from pathlib import Path
import json

ROOT=Path(__file__).resolve().parents[1]
AUDIT_SOURCE=ROOT/'assets/enemy_catalog_verified.json'

# category, plain visual description. Unclear small shapes are deliberately not
# promoted into the enemy list merely because the generic actor can draw them.
LABELS={
    0x02:('effect','Knochen und Bruchstücke'),
    0x03:('object','Schwung-Fledermaus (Peitschenring)'),
    0x04:('object','Zugbrückenkette'),
    0x06:('object','Holzplattform'),
    0x07:('enemy','Medusa-Kopf (Medusa Head)'),
    0x08:('enemy','Geist / Poltergeist (Ectoplasm)'),
    0x09:('enemy','Stachelechse (Needle Lizard)'),
    0x0a:('enemy','Schwarzer Panther (Black Panther)'),
    0x0b:('enemy','Knochensäule (Pillar of Bones)'),
    0x0c:('enemy','Fledermaus (Batton)'),
    0x0d:('enemy','Schwarzer Panther – Variante (Black Panther)'),
    0x0f:('enemy','Fliegendes Zauberbuch (Magic Book)'),
    0x10:('enemy','Krähe / Rabe (Crow)'),
    0x11:('enemy','Skelett (Skeleton / Red / Gold)'),
    0x12:('enemy','Knochenwerfer-Skelett (Bone Chukker)'),
    0x14:('object','Turm- und Kulissenteil'),
    0x16:('hazard','Stachelplatte (Spike Crusher)'),
    0x17:('object','Kleine Plattform'),
    0x2c:('enemy','Kriechender Ghul (Crawling Ghoul)'),
    0x30:('enemy','Sumpf-Frosch (Korochen)'),
    0x31:('enemy','Skelett-Ritter (Skeleton Soldier)'),
    0x32:('enemy','Deckenschleim (Ceiling Slime)'),
    0x33:('object','Vampir-Sarg (Vampire Coffin)'),
    0x34:('enemy','Feuergestalt'),
    0x37:('object','Stein- und Brückenteil'),
    0x39:('object','Gitterrahmen'),
    0x3a:('object','Holzpfosten'),
    0x3b:('object','Waagrechter Holzbalken'),
    0x3c:('enemy','Sumpfranken / Laubmonster (Swamp Vines)'),
    0x3e:('enemy','Fledermaus-Dämon (Man-Bat / Ogideran)'),
    0x3f:('object','Brücken- und Plattformteil'),
    0x42:('object','Lange Platte'),
    0x43:('enemy','Spinne (Spider)'),
    0x44:('object','Langer Holzpfosten'),
    0x45:('effect','Zerfalls- und Todeseffekt'),
    0x4a:('hazard','Kleine Stachelplatte'),
    0x4b:('enemy','Blutmotte (Crimson Moth)'),
    0x4c:('enemy','Fischmensch (Merman)'),
    0x4d:('object','Kronleuchter'),
    0x4e:('enemy','Fledermaus – Hängend (Batton 2)'),
    0x4f:('effect','Eis-/Wassergeschoss (Merman)'),
    0x50:('effect','Kleiner Partikeleffekt'),
    0x51:('enemy','Fischmensch – Sprung (Merman)'),
    0x52:('enemy','Axt-Ritter (Axe Armor)'),
    0x53:('effect','Axtgeschoss (Axe Armor)'),
    0x54:('enemy','Banshee / Todesfee'),
    0x56:('enemy','Peitschen-Skelett (Whip Skeleton)'),
    0x57:('enemy','Gremlin / Imp'),
    0x58:('enemy','Harpyie (Harpy)'),
    0x59:('enemy','Speer-Ritter (Spear Knight)'),
    0x5a:('enemy','Ballsaal-Geisterdame (Ghost Woman)'),
    0x5b:('enemy','Ballsaal-Geisterherr (Ghost Man)'),
    0x5c:('enemy','Wand-Skelett (Wall Skeleton)'),
    0x5d:('enemy','Knochendrache – Kopf (Bone Dragon)'),
    0x5e:('enemy','Knochendrache – Hals (Bone Dragon)'),
    0x60:('hazard','Langer spitzer Speerschaft'),
    0x61:('object','Violette Mechanik'),
    0x62:('object','Violette Mechanik – Teil'),
    0x64:('object','Fass und Rolle'),
    0x65:('object','Kleiner Steinblock'),
    0x66:('enemy','Boden-Hände Stage 02 (Hands)'),
    0x69:('enemy','Rotes Skelett (Blood Skeleton)'),
    0x6a:('effect','Kronleuchter-Energieorb'),
    0x6b:('enemy','Bluthund (Hellhound)'),
    0x6c:('enemy','Blut-Plasma-Tropfen'),
    0x6d:('hazard','Spore / Fuzz Buster (Keseran Pasaran)'),
    0x6e:('enemy','Kriechende Hand (Crawling Hand)'),
    0x6f:('enemy','Fliegender Pferdekopf (Mr. Hed)'),
    0x70:('enemy','Schlamm-Effekt / Boden-Tropfen'),
    0x71:('enemy','Fliegender Pferdekopf – Variante (Mr. Hed)'),
    0x72:('hazard','Fliegendes Auge (Peeping Eye)'),
    0x73:('enemy','Säulen-Ghul / Mud Man (Kiggaa)'),
    0x74:('enemy','Feuer-Tausendfüßer (Centipede / Larva)'),
    0x75:('enemy','Geflügelter Wächter (Winged Guard)'),
    0x76:('enemy','Tanzendes Geisterpaar (Ghost Couple)'),
    0x78:('enemy','Feuergestalt – weitere Bauart'),
    0x79:('effect','Kleine Flammengestalt'),
    0x7b:('object','Vampir-Sarg – Variante (Vampire Coffin)'),
    0x7c:('hazard','Zahnrad und Kreissäge'),
    0x7e:('enemy','Kopfloser Ritter (Dullahan)'),
    0x7f:('enemy','Steingolem / Statue (Stone Man / Brick Doll)'),
}

_audit=None
def native_profiles():
    global _audit
    if _audit is None:
        try:
            data=json.loads(AUDIT_SOURCE.read_text(encoding='utf-8'))
            _audit={(r['type'],r['variant']):r for r in data['profiles']}
        except (OSError,ValueError,KeyError,TypeError):
            _audit={}
    return _audit

def catalog_metadata(entry):
    """Return UI metadata without changing native type, variant or spawn fields.

    An enemy label alone never makes an unobserved candidate verified. A visible
    unclassified actor is different from an unobserved initialization candidate.
    """
    actor=int(entry['type']);variant=int(entry.get('variant',0))
    observed=native_profiles().get((actor,variant),{})
    category,name=LABELS.get(actor,('unclassified',f'Figur {actor:02X}'))
    if variant:name+=f' · Variante {variant}'
    verified=bool(observed.get('visible_native_actor'))
    return {'name':name,'category':category,'classification':category,
            'native_verified':verified,'verified':verified,
            'verification':'sichtbar geprüft' if verified else 'Initialisierung noch ungeprüft',
            'identity_basis':'visuelle Beschreibung' if actor in LABELS else 'nicht zugeordnet',
            'observed_poses':observed.get('poses',[]),
            'audit_report':observed.get('source_report'),
            'action_coverage':'kurzer nativer Ablauf; keine Vollständigkeitszusage'}

def describe(entry):
    """Convenience copy for the workshop picker; the supplied entry is unchanged."""
    return dict(entry,**catalog_metadata(entry))
