"""Data-driven localization loader shared by Python studio tools.
Automatically discovers every *.json locale file in assets/locales/
so adding a new language only requires dropping a new JSON file there.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCALES_DIR = ROOT / "assets" / "locales"
SETTINGS_FILE = ROOT / "ui_settings.json"

_LOCALES: dict[str, dict] = {}
_CURRENT: str = "de"
_LOADED: bool = False

_ORDER = {"de": 0, "en": 1, "es": 2, "fr": 3}


def _load() -> None:
    global _LOADED, _CURRENT
    if _LOADED:
        return
    _LOADED = True
    _LOCALES.clear()
    if LOCALES_DIR.is_dir():
        for p in sorted(LOCALES_DIR.glob("*.json")):
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                code = str(data.get("_code") or p.stem)
                _LOCALES[code] = data
            except (OSError, ValueError):
                pass
    if "en" not in _LOCALES:
        _LOCALES["en"] = {"_code": "en", "_name": "English"}
    # Read persisted language from ui_settings.json if present
    if SETTINGS_FILE.is_file():
        try:
            cfg = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
            lang = cfg.get("language")
            if isinstance(lang, str) and lang in _LOCALES:
                _CURRENT = lang
                return
        except (OSError, ValueError):
            pass
    if _CURRENT not in _LOCALES:
        _CURRENT = "en"


def available_languages() -> list[tuple[str, str]]:
    """Return [(code, display_name), ...] sorted with core languages first."""
    _load()
    items = [(code, str(d.get("_name", code))) for code, d in _LOCALES.items()]
    items.sort(key=lambda kv: (_ORDER.get(kv[0], 10), kv[1].lower()))
    return items


def current_language() -> str:
    _load()
    return _CURRENT


def current_language_name() -> str:
    _load()
    return str(_LOCALES.get(_CURRENT, {}).get("_name", _CURRENT))


def set_language(code: str, persist: bool = True) -> None:
    global _CURRENT
    _load()
    if code not in _LOCALES:
        return
    _CURRENT = code
    if persist:
        cfg = {}
        if SETTINGS_FILE.is_file():
            try:
                cfg = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                cfg = {}
        cfg["language"] = code
        try:
            SETTINGS_FILE.write_text(json.dumps(cfg, ensure_ascii=False) + "\n", encoding="utf-8")
        except OSError:
            pass


def tr(key: str, *args) -> str:
    """Translate key in active language, falling back to English, then key."""
    _load()
    val = _LOCALES.get(_CURRENT, {}).get(key)
    if val is None:
        val = _LOCALES.get("en", {}).get(key, key)
    if args:
        try:
            return str(val) % args
        except TypeError:
            return str(val)
    return str(val)
