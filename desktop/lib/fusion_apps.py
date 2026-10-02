"""FusionOS — egységes programlista (Start menü, irányítópult, keresés)

Források:
  - /usr/lib/fusion/desktop/apps.json   a Fusion Desktop saját és a rendszer programjai
  - a Fusion Programkezelő leírásai      /data/programs/<id>/program.fusion (Windows és Linux)
  - az ismert Windows-programok receptjei (fwr), amelyek még nincsenek telepítve:
                                         „telepítés” bejegyzés → Programkezelő
Minden bejegyzés: id, name, desc, icon (Fusion-csempe), iconFile (a program saját ikonja, ha van),
exec, type (fusion|linux|web|windows), installed, search_only, pid (Programkezelő-azonosító).
"""
import json
import os
import sys

APPS_FILE = os.environ.get("FUSION_APPS", "")
_PROG_LIB = os.environ.get("FUSION_PROGRAMS_LIB") or next(
    (p for p in ("/usr/lib/fusion/programs",
                 os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))), "programs"))
     if os.path.isfile(os.path.join(p, "fusion_programs.py"))), "/usr/lib/fusion/programs")
if _PROG_LIB not in sys.path:
    sys.path.insert(0, _PROG_LIB)
try:
    import fusion_programs as fp
except ImportError:      # a Programkezelő nélkül is legyen Start menü
    fp = None


# Start menü csoportjai: (azonosító, név, ikon) — a sorrend a menü sorrendje
GROUPS = [
    ("muhely", "Műhely", "laser"),
    ("grafika", "Grafika", "file-image"),
    ("iroda", "Iroda", "file-text"),
    ("internet", "Internet", "web"),
    ("media", "Hang és videó", "volume"),
    ("fejlesztes", "Fejlesztés", "file-code"),
    ("tudomany", "Oktatás és tudomány", "flask"),
    ("jatek", "Játékok", "game"),
    ("seged", "Segédprogramok", "app"),
    ("rendszer", "Rendszer", "settings"),
    ("egyeb", "Egyéb", "menu"),
]
GROUP_IDS = [g[0] for g in GROUPS]
# freedesktop-kategória → csoport (az első találat dönt; a Műhely elöl: a CAD / 3D / lézer ide tartozik)
CATEGORY_GROUP = [
    (("Engineering", "3DGraphics", "Electronics", "Laser", "3DPrinting", "Robotics"), "muhely"),
    (("WebBrowser", "Network", "Email", "Chat", "InstantMessaging", "FileTransfer", "P2P"), "internet"),
    (("Office", "WordProcessor", "Spreadsheet", "Presentation", "Calendar", "ContactManagement", "Finance"), "iroda"),
    (("Graphics", "Photography", "RasterGraphics", "VectorGraphics", "2DGraphics", "Viewer"), "grafika"),
    (("AudioVideo", "Audio", "Video", "Music", "Player", "Recorder"), "media"),
    (("Development", "IDE", "Debugger", "RevisionControl"), "fejlesztes"),
    (("Education", "Science", "Math", "Astronomy", "Chemistry", "Geography"), "tudomany"),
    (("Game",), "jatek"),
    (("System", "Settings", "TerminalEmulator", "PackageManager", "FileManager", "Monitor"), "rendszer"),
    (("Utility", "Accessories", "TextEditor", "Archiving", "Calculator"), "seged"),
]
MENU_FILE = os.path.join(os.path.expanduser("~"), ".config", "fusion", "menu.json")


def group_for_categories(cats):
    have = {c.strip() for c in (cats or "").replace(",", ";").split(";") if c.strip()}
    for keys, gid in CATEGORY_GROUP:
        if have.intersection(keys):
            return gid
    return "egyeb"


def menu_state():
    """a felhasználó Start menü-beállításai: kézi csoportok, indítások száma"""
    try:
        with open(MENU_FILE, encoding="utf-8") as f:
            d = json.load(f)
            if isinstance(d, dict):
                d.setdefault("groups", {})
                d.setdefault("launches", {})
                return d
    except (OSError, ValueError):
        pass
    return {"groups": {}, "launches": {}}


def _save_menu(d):
    os.makedirs(os.path.dirname(MENU_FILE), exist_ok=True)
    tmp = MENU_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)
    os.replace(tmp, MENU_FILE)


def set_group(app_id, group):
    """kézi csoport (üres: vissza az automatikusra)"""
    d = menu_state()
    if group in GROUP_IDS:
        d["groups"][app_id] = group
    else:
        d["groups"].pop(app_id, None)
    _save_menu(d)


def record_launch(app_id):
    d = menu_state()
    d["launches"][app_id] = int(d["launches"].get(app_id, 0)) + 1
    _save_menu(d)


def groups(apps):
    """a nem üres csoportok, a menü sorrendjében: [{id, name, icon, count}]"""
    cnt = {}
    for a in apps:
        if not a.get("search_only"):
            cnt[a["group"]] = cnt.get(a["group"], 0) + 1
    return [{"id": g, "name": n, "icon": i, "count": cnt[g]} for g, n, i in GROUPS if cnt.get(g)]


def program_apps():
    if fp is None:
        return []
    out, have = [], set()
    for m in fp.programs():
        i = fp.info(m)
        have.add(m["id"])
        out.append({"id": "prog-" + m["id"], "pid": m["id"], "fwr": m["id"] if m["type"] == "win64" else "",
                    "name": i["name"], "type": "windows" if m["type"] == "win64" else "linux",
                    "desc": i["comment"] or i["typeName"] + "-program", "icon": i["icon"], "iconFile": i["iconFile"],
                    "exec": "fusion-run " + m["id"], "installed": True, "search_only": False,
                    "keywords": (m.get("categories", "") + " " + m.get("appid", "")).replace(";", " "),
                    "categories": m.get("categories") or _recipe_categories(m)})
    for r in fp.recipes():
        if r["id"] in have:
            continue
        out.append({"id": "prog-" + r["id"], "pid": r["id"], "fwr": r["id"], "name": r.get("name", r["id"]),
                    "type": "windows", "desc": "Nincs telepítve — Programkezelő", "icon": r.get("icon", "app"),
                    "iconFile": "", "exec": "fusion-settings programs", "installed": False, "search_only": False,
                    "keywords": "telepítés", "categories": r.get("categories", "")})
    return out


def _recipe_categories(m):
    """régebbi leírásban nincs kategória: a recept (pl. lightburn.fwr) adja"""
    if fp is None or not m.get("recipe"):
        return ""
    return fp.read_kv(os.path.join(fp.RECIPES, m["recipe"])).get("categories", "")


def load(apps_file=None):
    path = apps_file or APPS_FILE or os.path.join(
        os.environ.get("FUSION_DESKTOP_DIR") or os.path.dirname(os.path.dirname(os.path.realpath(__file__))), "apps.json")
    try:
        with open(path, encoding="utf-8") as f:
            base = json.load(f)
    except (OSError, ValueError):
        base = [{"id": "terminal", "name": "Terminál", "desc": "Parancssor", "icon": "terminal", "exec": "xterm"}]
    for a in base:
        a.setdefault("type", "fusion")
        a.setdefault("installed", True)
        a.setdefault("search_only", False)
        a.setdefault("keywords", "")
        a.setdefault("iconFile", "")
        a.setdefault("pid", "")
        a.setdefault("fwr", "")
    try:
        progs = program_apps()
    except Exception:      # egy hibás leírás ne vigye el a Start menüt
        progs = []
    # a telepített programok a lista elejére (a Prototype 0.1 célprogramja a LightBurn)
    apps = sorted(progs, key=lambda a: (not a["installed"], a["name"].lower())) + base
    st = menu_state()
    for a in apps:
        auto = a.get("group") if a.get("group") in GROUP_IDS else group_for_categories(a.get("categories", ""))
        a["autoGroup"] = auto
        a["group"] = st["groups"].get(a["id"]) if st["groups"].get(a["id"]) in GROUP_IDS else auto
        a["launches"] = int(st["launches"].get(a["id"], 0))
    return apps
