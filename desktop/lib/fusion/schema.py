"""leíró-sémák, 1-es változat (M8b) — a Fusion-leírók formális leírása és ellenőrzése

    program.fusion   egy telepített program leírása (/data/programs/<id>/program.fusion) — a Programkezelő írja
    *.fwr            recept: egy ismert Windows-program „gyári” leírása (/usr/lib/fusion/fwr/profiles/<id>.fwr)
    *.role           eszközszerep (/usr/lib/fusion/devices/roles/NN-<szerep>.role)

A recept UGYANAZ a séma, mint a program.fusion (type = win64 alapértelmezéssel, plusz a `match` kulcs).
Elsőbbségi szabály (egy helyen, itt): `apply_recipe(recept, leírás)` — telepítéskor a Programkezelő a recept
kulcsait a leírásba írja (recipe = <fájlnév>), de a felhasználó beállításai (port.*, drive.*, places) a leírásból
maradnak. Futáskor a leírás önmagában teljes: az fwr és a Programkezelő csak a leírást olvassa.

Formátum (mindhárom fájlnál, fusion.kv): `kulcs = érték` sorok, `#` megjegyzés, UTF-8. Ismeretlen kulcs: figyelmeztetés
(egy újabb változat kulcsa lehet), nem hiba.

    from fusion import schema
    schema.validate_program(adatok)        → [(szint, kulcs, üzenet)]   szint: "hiba" | "figyelmeztetés"
    schema.validate_file("…/program.fusion")
    schema.describe()                      → a sémák géppel olvasható leírása (fusion schema --json)
"""
import os
import re

from . import kv

VERSION = 1

ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")
ROLE_RE = re.compile(r"^[a-z0-9_-]{1,32}$")
COM_RE = re.compile(r"^COM[1-9]$")
USB_RE = re.compile(r"^[0-9a-f]{4}:[0-9a-f]{4}$")
WINPATH_RE = re.compile(r"^[A-Za-z]:\\")
EXT_RE = re.compile(r"^\.[A-Za-z0-9_+-]{1,16}$")
APPID_RE = re.compile(r"^[A-Za-z0-9_-]+(\.[A-Za-z0-9_-]+){2,}$")

TYPES = ("win64", "flatpak", "appimage", "native")
WINDOWS_VERSIONS = ("win7", "win8", "win81", "win10", "win11")


def _f(kind, desc, required=False, values=None, types=None, recipe_only=False):
    return {"kind": kind, "desc": desc, "required": required, "values": list(values or []), "types": list(types or []),
            "recipeOnly": recipe_only}


# a program.fusion (és a recept) mezői — kind: a szöveges érték alakja
PROGRAM_FIELDS = {
    "id":          _f("id", "azonosító: kisbetű, szám, . _ - (max. 64); egyezik a mappa nevével", required=True),
    "name":        _f("text", "a program neve a felületen", required=True),
    "type":        _f("enum", "a program típusa (recept: alapértelmezés win64)", required=True, values=TYPES),
    "version":     _f("text", "verzió (tájékoztató)"),
    "comment":     _f("text", "rövid leírás"),
    "icon":        _f("text", "ikon: fájl a program mappájában vagy a Fusion ikonkészlet neve"),
    "icon_tile":   _f("text", "a csempe ikonneve, ha az icon fájl"),
    "categories":  _f("list;", "freedesktop-kategóriák pontosvesszővel (a Start menü csoportja)"),
    "open":        _f("exts", "fájltársítás: kiterjesztések szóközzel (.lbrn .svg)"),
    "mime":        _f("list;", "fájltársítás: MIME-típusok pontosvesszővel"),
    "installed":   _f("text", "a telepítés ideje (a Programkezelő írja)"),
    "source":      _f("text", "honnan települt (fájlnév, flathub …)"),
    "recipe":      _f("text", "a recept fájlneve, amelyből a leírás készült"),
    # win64
    "exe":         _f("winpath", "a program Windows-útja (C:\\…\\x.exe)", types=["win64"]),
    "windows":     _f("enum", "a jelentett Windows-verzió", values=WINDOWS_VERSIONS, types=["win64"]),
    "prefix":      _f("abspath", "a Windows-környezet mappája (alapértelmezés: /data/fwr/<id>)", types=["win64"]),
    "dlloverrides": _f("text", "Wine DLL-felülírások (kísérleti futtató)", types=["win64"]),
    "places":      _f("enum", "a Fusion helyei a fájlválasztóban (D: Adatok, E: pendrive, Asztal)",
                      values=("standard", "none"), types=["win64"]),
    "port.COMn":   _f("role", "soros port → eszközszerep (port.COM3 = laser)", types=["win64"]),
    "drive.X":     _f("dir", "meghajtóbetű → mappa (abszolút, vagy a saját mappához képest)", types=["win64"]),
    "match":       _f("text", "recept: a telepítőfájl nevének mintája (LightBurn*.exe)", types=["win64"], recipe_only=True),
    # flatpak
    "appid":       _f("appid", "Flatpak-azonosító (com.prusa3d.PrusaSlicer)", types=["flatpak"]),
    "installation": _f("enum", "Flatpak-telepítés helye", values=("user", "system"), types=["flatpak"]),
    # appimage / native
    "exec":        _f("relpath", "az indítófájl a program mappájához képest", types=["appimage", "native"]),
}
# típusonként kötelező
PROGRAM_REQUIRED = {"win64": ["exe"], "flatpak": ["appid"], "appimage": ["exec"], "native": ["exec"]}

ROLE_FIELDS = {
    "role":        _f("role", "a szerep neve: kisbetű, szám, _ - (max. 32); /dev/fusion/<szerep>", required=True),
    "name":        _f("text", "a szerep neve a felületen", required=True),
    "match.usb":   _f("usbids", "illeszkedő USB-eszközök: vid:pid szóközzel", required=True),
    "identify":    _f("enum", "azonosítás: serial (sorozatszám) vagy path (fizikai USB-port)", values=("serial", "path")),
    "windows.com": _f("com", "javasolt COM-port a Windows-programoknak (a program leírója dönt)"),
}


def _field(fields, key):
    if key in fields:
        return fields[key]
    m = re.match(r"^(port)\.(.+)$|^(drive)\.(.+)$", key)
    if m and m.group(1):
        return dict(fields["port.COMn"], _sub=m.group(2), _subkind="com")
    if m and m.group(3):
        return dict(fields["drive.X"], _sub=m.group(4), _subkind="letter")
    return None


def _check_value(kind, v, values=()):
    """None, ha rendben; különben a hiba szövege"""
    if kind == "id":
        return None if ID_RE.match(v) else "érvénytelen azonosító (kisbetű, szám, . _ -)"
    if kind == "role":
        return None if ROLE_RE.match(v) else "érvénytelen szerepnév"
    if kind == "enum":
        return None if v in values else "lehetséges értékek: " + ", ".join(values)
    if kind == "winpath":
        return None if WINPATH_RE.match(v) else "Windows-út kell (C:\\…)"
    if kind == "abspath":
        return None if v.startswith("/") else "abszolút út kell (/…)"
    if kind == "relpath":
        return None if v and not v.startswith("/") and ".." not in v.split("/") else "a program mappáján belüli út kell"
    if kind == "dir":
        return None if v and ".." not in v.split("/") else "érvénytelen mappa"
    if kind == "exts":
        bad = [e for e in v.split() if not EXT_RE.match(e)]
        return None if not bad else "érvénytelen kiterjesztés: " + " ".join(bad)
    if kind == "usbids":
        bad = [e for e in v.split() if not USB_RE.match(e.lower())]
        return None if v.split() and not bad else "vid:pid alak kell (1a86:7523)"
    if kind == "com":
        return None if COM_RE.match(v) else "COM1 … COM9"
    if kind == "appid":
        return None if APPID_RE.match(v) else "Flatpak-azonosító kell (org.pelda.Program)"
    return None


def _validate(data, fields, required_extra=(), type_of=None, recipe=False):
    out = []
    t = type_of
    for k, v in data.items():
        if k.startswith("_") or k in ("dir", "recipe_file"):
            continue
        f = _field(fields, k)
        if f is None:
            out.append(("figyelmeztetés", k, "ismeretlen kulcs (újabb változat?)"))
            continue
        if f.get("recipeOnly") and not recipe:
            out.append(("figyelmeztetés", k, "csak receptben használt kulcs"))
        if f["types"] and t and t not in f["types"]:
            out.append(("figyelmeztetés", k, f"a(z) {t} típusnál nincs jelentése"))
        if f.get("_subkind") == "com" and not COM_RE.match(f["_sub"]):
            out.append(("hiba", k, "a port neve COM1 … COM9"))
        if f.get("_subkind") == "letter" and not re.match(r"^[D-Yd-y]$", f["_sub"]):
            out.append(("hiba", k, "a meghajtóbetű D … Y"))
        err = _check_value(f["kind"], str(v).strip(), f["values"])
        if err:
            out.append(("hiba", k, err))
    for k, f in fields.items():
        if f["required"] and not str(data.get(k, "")).strip() and not (recipe and k == "type"):
            out.append(("hiba", k, "kötelező kulcs hiányzik"))
    for k in required_extra:
        if not str(data.get(k, "")).strip():
            out.append(("hiba", k, f"a(z) {t} típusnál kötelező"))
    return out


def validate_program(data, recipe=False):
    """program.fusion (recipe=True: *.fwr recept) ellenőrzése → [(szint, kulcs, üzenet)]"""
    t = data.get("type") or ("win64" if recipe else "")
    req = [] if recipe else PROGRAM_REQUIRED.get(t, [])
    return _validate(data, PROGRAM_FIELDS, req, t, recipe)


def validate_role(data):
    return _validate(data, ROLE_FIELDS)


def kind_of(path):
    b = os.path.basename(path)
    if b.endswith(".fwr"):
        return "recipe"
    if b.endswith(".role"):
        return "role"
    return "program"


def validate_file(path):
    """a fájl típusát a neve dönti el (.fwr, .role, különben program.fusion)"""
    try:
        with open(path, encoding="utf-8") as f:
            data = kv.parse(f.read())
    except (OSError, UnicodeDecodeError) as e:
        return [("hiba", "", f"nem olvasható: {e}")]
    k = kind_of(path)
    if k == "role":
        return validate_role(data)
    res = validate_program(data, recipe=(k == "recipe"))
    d = os.path.basename(os.path.dirname(os.path.abspath(path)))
    if k == "program" and os.path.basename(path) == "program.fusion" and data.get("id") and d != data["id"]:
        res.append(("figyelmeztetés", "id", f"nem egyezik a mappa nevével ({d})"))
    return res


# a felhasználó beállításai (Beállítások → Programkezelő: eszközök, mappák) — ezekben a program leírója dönt
USER_KEY_FAMILIES = ("port.", "drive.", "places")


def _family(k):
    return next((f for f in USER_KEY_FAMILIES if k == f or (f.endswith(".") and k.startswith(f))), None)


def apply_recipe(recipe, program=None):
    """az elsőbbségi szabály (egy helyen): a recept a leírás alapja, a program leírója felülírja.
    Telepítéskor / újratelepítéskor a recept technikai kulcsai (exe, windows, dlloverrides …) frissülnek, a felhasználó
    beállításai (port.*, drive.*, places) viszont megmaradnak, ha a leírásban már van ilyen családú kulcs.
    A recept `match` kulcsa nem kerül a leírásba."""
    program = dict(program or {})
    out = dict(program)
    for k, v in (recipe or {}).items():
        if k in ("match", "recipe_file"):
            continue
        fam = _family(k)
        if fam and any(_family(x) == fam for x in program):
            continue
        out[k] = v
    out.setdefault("type", "win64")
    return out


def describe():
    """a sémák géppel olvasható leírása"""
    return {"version": VERSION,
            "program": {"fields": PROGRAM_FIELDS, "requiredByType": PROGRAM_REQUIRED,
                        "recipe": "ugyanez a séma; type = win64 alapértelmezéssel; match csak itt; "
                                  "elsőbbség: apply_recipe — a felhasználó beállításai (port.*, drive.*, places) a leírásból"},
            "role": {"fields": ROLE_FIELDS}}
