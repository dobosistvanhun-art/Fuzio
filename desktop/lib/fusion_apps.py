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
                    "keywords": (m.get("categories", "") + " " + m.get("appid", "")).replace(";", " ")})
    for r in fp.recipes():
        if r["id"] in have:
            continue
        out.append({"id": "prog-" + r["id"], "pid": r["id"], "fwr": r["id"], "name": r.get("name", r["id"]),
                    "type": "windows", "desc": "Nincs telepítve — Programkezelő", "icon": r.get("icon", "app"),
                    "iconFile": "", "exec": "fusion-settings programs", "installed": False, "search_only": False,
                    "keywords": "telepítés"})
    return out


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
    return sorted(progs, key=lambda a: (not a["installed"], a["name"].lower())) + base
