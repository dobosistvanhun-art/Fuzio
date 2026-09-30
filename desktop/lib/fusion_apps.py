"""FusionOS — egységes programlista (Start menü, Beállítások → Programok)

Források:
  - /usr/lib/fusion/desktop/apps.json   a Fusion Desktop saját és a rendszer programjai
  - /usr/lib/fusion/fwr/profiles/*.fwr  Windows-programok (Fusion Windows Runtime):
                                         telepítve → indítható, különben „telepítés” bejegyzés
Minden bejegyzés: id, name, desc, icon, exec, type (fusion|linux|web|windows),
installed, search_only (csak keresésre jelenik meg, pl. egy beállítás-oldal).
"""
import json
import os
import shlex

APPS_FILE = os.environ.get("FUSION_APPS", "")
FWR_PROFILES = os.environ.get("FWR_PROFILES", "/usr/lib/fusion/fwr/profiles")
FWR_DATA = os.environ.get("FWR_DATA", "/data/fwr")


def _profile(path):
    p = {}
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                p[k.strip()] = v.strip()
    except OSError:
        pass
    return p


def win_to_unix(prefix, winpath):
    """C:\\Program Files\\X\\x.exe → <prefix>/drive_c/Program Files/X/x.exe"""
    if len(winpath) > 2 and winpath[1] == ":":
        return os.path.join(prefix, "drive_" + winpath[0].lower(), winpath[3:].replace("\\", "/"))
    return winpath


def windows_apps():
    out = []
    try:
        names = sorted(os.listdir(FWR_PROFILES))
    except OSError:
        return out
    for fn in names:
        if not fn.endswith(".fwr"):
            continue
        p = _profile(os.path.join(FWR_PROFILES, fn))
        pid = p.get("id", fn[:-4])
        if pid == "fwr-check" or not p.get("exe"):
            continue
        exe = win_to_unix(os.path.join(FWR_DATA, pid), p["exe"])
        inst = os.path.isfile(exe)
        out.append({"id": "fwr-" + pid, "fwr": pid, "name": p.get("name", pid), "type": "windows",
                    "desc": "Windows-program" if inst else "Nincs telepítve — Beállítások → Programok",
                    "icon": "laser" if pid == "lightburn" else "app",
                    "exec": "fwr launch " + shlex.quote(pid) if inst else "fusion-settings programs",
                    "installed": inst, "search_only": False})
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
    # a Windows-programok a lista elejére (a Prototype 0.1 célprogramja a LightBurn)
    return windows_apps() + base
