"""jogosultságok (M9) — a program leírójában rögzített jogok, és a Fúzió API kapuja

Minden API-hívás, amely eszközt, rendszerműveletet vagy más program adatát érinti, a `check`-en megy át.
Képességek: "device:<szerep>", "files:<mappa>", "net", "system:<művelet>" (pl. system:bluetooth, system:printers),
"programs:manage".

    caller()          a hívó program azonosítója: FUSION_PROGRAM_ID, vagy "fusion" (a Fúzió saját programjai, a
                      felhasználó szkriptjei és a terminál)
    of(leírás)        egy program jogai: {devices, folders, net, sandbox, enforcement, protection}
    summary(id)       ugyanez azonosító alapján (None, ha nincs ilyen program)
    check(program, képesség)   True / False

A kényszerítés a futtatóé (terv: claude/M9-Jogosultsagi-modell-terv.md, 3.4): Flatpak — a Flatpak homokozója;
win64 / appimage / native — `sandbox = yes` esetén homokozó, különben a felhasználó jogaival fut (a felület ezt
jelzi). A `check` önmagában nem védelem (azonos felhasználói jog mellett megkerülhető) — a homokozóval együtt az.
"""
import os
import re
import subprocess

TRUSTED = ("fusion", "")
SYSTEM_CAPS = ("system:", "programs:")

PROTECTION = {
    "sandbox": "homokozóban: csak a megadott mappákat és eszközöket látja",
    "flatpak": "Flatpak-homokozó: a csomag által kért jogokkal",
    "win64": "nincs homokozó: a Windows-nézetben csak a megadott meghajtók látszanak, de a program a felhasználó "
             "jogaival fut",
    "full": "teljes hozzáférés: a felhasználó jogaival fut",
}


def caller():
    return os.environ.get("FUSION_PROGRAM_ID", "fusion")


def _folders(m):
    out = []
    for k, v in sorted(m.items()):
        if k.startswith("drive."):
            out.append({"path": v, "letter": k[6:].upper(), "readonly": False})
    for e in str(m.get("allow.files", "")).split():
        name, _, ro = e.partition(":")
        out.append({"path": name, "letter": "", "readonly": ro == "ro"})
    return out


def of(m):
    t = m.get("type", "")
    sandbox = m.get("sandbox", "no") == "yes"
    if t == "flatpak":
        enf = "flatpak"
    elif sandbox:
        enf = "sandbox"
    else:
        enf = "win64" if t == "win64" else "full"
    return {"id": m.get("id", ""), "name": m.get("name", m.get("id", "")), "type": t,
            "devices": sorted({v for k, v in m.items() if k.startswith("port.")}),
            "ports": {k[5:]: v for k, v in m.items() if k.startswith("port.")},
            "folders": _folders(m), "net": m.get("allow.net", "yes") != "no", "sandbox": sandbox,
            "enforcement": enf, "protection": PROTECTION[enf]}


def flatpak_permissions(appid):
    """a Flatpak-csomag által kért jogok (flatpak info --show-permissions) — {szakasz: {kulcs: érték}}"""
    try:
        r = subprocess.run(["flatpak", "info", "--show-permissions", appid], capture_output=True, text=True, timeout=15)
    except (OSError, subprocess.TimeoutExpired):
        return {}
    res, sec = {}, ""
    for line in r.stdout.splitlines():
        m = re.match(r"^\[(.+)\]$", line.strip())
        if m:
            sec = m.group(1)
            res.setdefault(sec, {})
        elif "=" in line and sec:
            k, _, v = line.partition("=")
            res[sec][k.strip()] = v.strip()
    return res


def _manifest(pid):
    from . import programs
    fp = programs._fp()
    return fp.manifest(pid) if fp.ID_RE.match(pid or "") else None


def summary(pid, with_flatpak=False):
    m = _manifest(pid)
    if not m:
        return None
    s = of(m)
    if with_flatpak and m.get("type") == "flatpak" and m.get("appid"):
        ctx = flatpak_permissions(m["appid"]).get("Context", {})
        s["flatpak"] = {k: [x for x in v.split(";") if x] for k, v in ctx.items()}
    return s


def check(program, capability):
    """a Fúzió saját programjai (és a felhasználó szkriptjei) mindent elérnek; egy telepített program a leírása
    szerint; ismeretlen program semmit"""
    if program in TRUSTED:
        return True
    m = _manifest(program)
    if not m:
        return False
    if capability.startswith(SYSTEM_CAPS):
        return False
    p = of(m)
    if capability.startswith("device:"):
        return capability[7:] in p["devices"]
    if capability.startswith("files:"):
        want = capability[6:].rstrip("/")
        return any(want == f["path"].rstrip("/") or want.startswith(f["path"].rstrip("/") + "/") for f in p["folders"])
    if capability == "net":
        return p["net"]
    return False
