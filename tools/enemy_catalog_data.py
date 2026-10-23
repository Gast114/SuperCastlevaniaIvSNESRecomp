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
    0x04:('object','Zugbrückenkette'),
    0x06:('object','Holzplattform'),
    0x07:('enemy','Spinne'),
    0x08:('object','Peitschenring'),
    0x09:('enemy','Flugkreatur'),
    0x0a:('enemy','Vierbeiniges Ungeheuer'),
    0x0b:('enemy','Knochensäule'),
    0x0c:('enemy','Fledermaus'),
    0x0d:('enemy','Vierbeiniges Ungeheuer – Variante'),
    0x10:('enemy','Vogel'),
    0x11:('enemy','Skelett – Gehen'),
    0x12:('enemy','Skelett – Knochenwerfer'),
    0x14:('object','Turm- und Kulissenteil'),
    0x16:('hazard','Stachelplatte'),
    0x17:('object','Kleine Plattform'),
    0x30:('enemy','Kleiner Frosch'),
    0x31:('enemy','Skelett – andere Bauart'),
    0x32:('enemy','Frosch'),
    0x33:('object','Sarg'),
    0x34:('enemy','Feuergestalt'),
    0x37:('object','Stein- und Brückenteil'),
    0x39:('object','Gitterrahmen'),
    0x3a:('object','Holzpfosten'),
    0x3b:('object','Waagrechter Holzbalken'),
    0x3e:('enemy','Geflügelte Kreatur'),
    0x3f:('object','Brücken- und Plattformteil'),
    0x42:('object','Lange Platte'),
    0x43:('enemy','Spinne – andere Bauart'),
    0x44:('object','Langer Holzpfosten'),
    0x45:('effect','Zerfalls- und Todeseffekt'),
    0x4a:('hazard','Kleine Stachelplatte'),
    0x4c:('enemy','Schwebende Frauengestalt'),
    0x4d:('object','Kronleuchter'),
    0x4e:('enemy','Fledermaus – andere Variante'),
    0x4f:('effect','Kleines fliegendes Geschoss'),
    0x50:('effect','Kleiner Partikeleffekt'),
    0x51:('enemy','Schwebende Frauengestalt – Variante'),
    0x52:('enemy','Gepanzerter Wächter'),
    0x53:('effect','Axtgeschoss'),
    0x56:('enemy','Skelett – gebeugte Bauart'),
    0x58:('enemy','Großer Vogel'),
    0x59:('enemy','Gepanzerter Wächter – Variante'),
    0x5a:('enemy','Schwebende Geistergestalt'),
    0x5b:('enemy','Blasse Geistergestalt'),
    0x5c:('enemy','Skelett – weitere Variante'),
    0x60:('hazard','Langer spitzer Schaft'),
    0x61:('object','Violette Mechanik'),
    0x62:('object','Violette Mechanik – Teil'),
    0x64:('object','Fass und Rolle'),
    0x65:('object','Kleiner Steinblock'),
    0x69:('enemy','Rote untote Gestalt'),
    0x6b:('enemy','Große Flugkreatur'),
    0x6c:('enemy','Skelett mit Bogen'),
    0x6d:('hazard','Stachelige Kugel'),
    0x6e:('enemy','Grüner Wurm'),
    0x6f:('enemy','Fliegender Kopf'),
    0x70:('enemy','Kleine Flugkreatur'),
    0x71:('enemy','Fliegender Kopf – Variante'),
    0x72:('hazard','Goldene Scheibe'),
    0x74:('effect','Feuerkugel'),
    0x75:('enemy','Geflügelte Kreatur mit Schild'),
    0x78:('enemy','Feuergestalt – weitere Bauart'),
    0x79:('effect','Kleine Flammengestalt'),
    0x7b:('object','Sarg – Variante'),
    0x7c:('hazard','Zahnrad und Kreissäge'),
    0x7e:('enemy','Skelett mit Schild'),
    0x7f:('enemy','Steingestalt'),
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
