"""eszközszerepek — a Fúzió saját eszközrétege (lézer, 3D nyomtató, és bármely új szerep egy .role fájllal)

    roles()                 a szerepek leírása + állapota (csatlakoztatva-e, melyik eszköz, rögzített azonosító)
    present()               gyors állapot (a Shell 2 mp-enként hívja): [{role, name, present, dev}]
    com_usage(roles=None)   ki melyik COM-porton éri el a szerepet: {szerep: [{id, name, com}]}
    assign(szerep, eszköz) / forget(szerep)   — rootként, a fusion-admin kapun át

Egy hely, egy igazság (M8): a szerepfájl `windows.com` kulcsa csak JAVASLAT (ezt kínálja fel a Programkezelő egy
Windows-program engedélyezésekor); a ténylegesen használt COM-port a program leírójában van (`port.COMn = szerep`) —
a Fúzió Windows Runtime (fwr) is onnan olvassa.
"""
import glob
import os
import subprocess

from . import ADMIN, kv, permissions

ROLES_DIR = os.environ.get("FUSION_DEVICES_ROLES", "/usr/lib/fusion/devices/roles")
DB = os.environ.get("FUSION_DEVICES_DB", "/etc/fusion/devices.conf")
DEV_DIR = os.environ.get("FUSION_DEV", "/dev/fusion")
PROGRAMS_DIR = os.environ.get("FUSION_PROGRAMS_DIR", "/data/programs")

_cache = {"key": None, "defs": []}


def definitions():
    """a .role fájlok (a mappa változásakor újraolvasva)"""
    files = sorted(glob.glob(os.path.join(ROLES_DIR, "*.role")))
    key = tuple((f, os.path.getmtime(f)) for f in files if os.path.exists(f))
    if key != _cache["key"]:
        defs = []
        for f in files:
            r = kv.read(f)
            if r.get("role"):
                defs.append({"role": r["role"], "name": r.get("name", r["role"]), "match": r.get("match.usb", ""),
                             "identify": r.get("identify", ""), "com": r.get("windows.com", "")})
        _cache.update(key=key, defs=defs)
    return [dict(d) for d in _cache["defs"]]


def assignments():
    """a rögzített azonosítók (devices.conf): {szerep: "serial:…" | "path:…"}"""
    out = {}
    try:
        with open(DB, encoding="utf-8") as f:
            for line in f:
                p = line.split()
                if len(p) >= 2 and not line.startswith("#"):
                    out[p[0]] = p[1]
    except OSError:
        pass
    return out


def _state(role):
    link = os.path.join(DEV_DIR, role)
    present = os.path.exists(link)
    return present, (os.path.basename(os.path.realpath(link)) if present else "")


def present():
    out = []
    for d in definitions():
        p, dev = _state(d["role"])
        out.append({"role": d["role"], "name": d["name"], "present": p, "dev": dev})
    return out


def com_usage(defs=None):
    use = {d["role"]: [] for d in (defs or definitions())}
    for f in sorted(glob.glob(os.path.join(PROGRAMS_DIR, "*", "program.fusion"))):
        m = kv.read(f)
        for k, v in m.items():
            if k.startswith("port.") and v in use:
                use[v].append({"id": m.get("id", os.path.basename(os.path.dirname(f))), "name": m.get("name", ""),
                               "com": k[5:]})
    return use


def roles():
    defs = definitions()
    db = assignments()
    use = com_usage(defs)
    out = []
    for d in defs:
        p, dev = _state(d["role"])
        d.update(present=p, dev=dev, key=db.get(d["role"], ""), programs=use.get(d["role"], []))
        out.append(d)
    return out


def _admin(*args):
    try:
        r = subprocess.run(["sudo", "-n", ADMIN] + list(args), capture_output=True, text=True, timeout=30)
        return r.returncode, (r.stdout + r.stderr).strip()
    except (OSError, subprocess.TimeoutExpired) as e:
        return 1, str(e)


def assign(role, dev, program="fusion"):
    if not permissions.check(program, f"device:{role}"):
        return 1, "nincs engedély"
    return _admin("devices-assign", role, dev)


def forget(role, program="fusion"):
    if not permissions.check(program, f"device:{role}"):
        return 1, "nincs engedély"
    return _admin("devices-forget", role)
