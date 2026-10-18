"""Fúzió — Fúzió Programkezelő (Fúzió Program Runtime): a háttérrész

Egy program = egy leírás a DATA-n: /data/programs/<id>/program.fusion (kulcs = érték).
A felület (Beállítások → Programkezelő, Start menü, Fájlkezelő) és a parancssor (fusion-programs,
fusion-run) mind ezt a modult használja. A program típusa csak itt és a futtatókban számít:

    win64     Windows x64 program — futtató: fwr (ma Wine-alapú, kísérleti M4-megoldás)
    flatpak   Linux-program a Flathubról (felhasználói telepítés, homokozó) — a fő Linux-formátum
    appimage  Linux AppImage — telepítéskor kibontva (FUSE nem kell)
    native    Linux-program archívumból / önálló binárisként

Közös mezők: id, name, type, version, exec, icon (fájl a program mappájában vagy ikonnév),
categories, comment, open (fájltársítás: kiterjesztések), mime, installed, source.
win64: exe, windows, prefix, port.COMn = szerep, drive.X = mappa (az fwr ugyanezt olvassa).
flatpak: appid.  appimage / native: exec (a program mappájához képest).

Minden művelet a fusion felhasználóként, root nélkül fut (spec 17.).
"""
try:
    from fusion import kv as _fkv, schema as _fschema, permissions as _fperm
except ImportError:      # fejlesztői fa: <repo>/desktop/lib
    import sys as _sys
    import os as _os
    _sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.realpath(__file__))), "desktop", "lib"))
    from fusion import kv as _fkv, schema as _fschema, permissions as _fperm
import configparser
import fnmatch
import glob
import json
import mimetypes
import os
import re
import shutil
import struct
import subprocess
import tarfile
import time
import zipfile

PROGRAMS = os.environ.get("FUSION_PROGRAMS_DIR", "/data/programs")
RECIPES = os.environ.get("FWR_PROFILES", "/usr/lib/fusion/fwr/profiles")
# Linux-programok receptjei (Flatpak-azonosító szerint): ugyanaz a séma; pl. URL-sémák (scheme), indítási kapcsolók
LINUX_RECIPES = os.environ.get("FUSION_PROGRAM_RECIPES", os.path.join(os.path.dirname(os.path.realpath(__file__)), "recipes"))
FWR_DATA = os.environ.get("FWR_DATA", "/data/fwr")
HOME = os.path.expanduser("~")
APPS_DIR = os.path.join(HOME, ".local/share/applications")
FLATPAK_EXPORTS = os.path.join(HOME, ".local/share/flatpak/exports/share")
FLATPAK_SYSTEM_EXPORTS = "/var/lib/flatpak/exports/share"
# ezek változása jelzi, hogy kívülről (parancssorból) települt / tűnt el egy Flatpak
WATCH_DIRS = (os.path.join(FLATPAK_EXPORTS, "applications"), os.path.join(FLATPAK_SYSTEM_EXPORTS, "applications"))
FLATHUB = "https://dl.flathub.org/repo/flathub.flatpakrepo"
ASSOC_FILE = os.path.join(HOME, ".config/fusion/associations.json")
TYPE_NAMES = {"win64": "Windows", "flatpak": "Linux (Flatpak)", "appimage": "Linux (AppImage)", "native": "Linux"}
ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")


class ProgramError(Exception):
    pass


def _rmtree(path):
    """mappa törlése hibatűrően: a csak olvasható almappák (pl. az fwr „Adatok” nézete) is törlődnek; hivatkozást
    nem követ (a Windows-környezet Asztal-hivatkozásai a saját mappára mutatnak — azokat csak eltávolítja)"""
    def onerror(func, p, _exc):
        try:
            parent = os.path.dirname(p)
            os.chmod(parent, os.stat(parent).st_mode | 0o700)
            if func in (os.unlink, os.remove, os.rmdir):
                func(p)
        except OSError:
            pass
    if os.path.islink(path):
        try:
            os.unlink(path)
        except OSError:
            pass
        return
    shutil.rmtree(path, onerror=onerror)


def _log(log, msg):
    if log:
        log(msg)


# ---------------------------------------------------------------------------
# leírás (manifest)
# ---------------------------------------------------------------------------
def read_kv(path):
    """a leírók (program.fusion, *.fwr) olvasása — a Fúzió API egyetlen kulcs=érték olvasójával"""
    return _fkv.read(path)


def write_manifest(m):
    d = os.path.join(PROGRAMS, m["id"])
    os.makedirs(d, exist_ok=True)
    order = ["id", "name", "type", "version", "comment", "exec", "exe", "appid", "icon", "categories",
             "open", "mime", "windows", "prefix", "installed", "source", "recipe"]
    keys = order + sorted(k for k in m if k not in order)
    lines = ["# Fúzió — Fúzió Programkezelő: programleírás (a Programkezelő írja)"]
    for k in keys:
        if k == "dir":
            continue
        v = m.get(k)
        if v not in (None, ""):
            lines.append(f"{k} = {v}")
    tmp = os.path.join(d, "program.fusion.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    os.replace(tmp, os.path.join(d, "program.fusion"))


def manifest(pid):
    m = read_kv(os.path.join(PROGRAMS, pid, "program.fusion"))
    if m:
        m.setdefault("id", pid)
        m["dir"] = os.path.join(PROGRAMS, pid)
    return m


def programs():
    out = []
    for f in sorted(glob.glob(os.path.join(PROGRAMS, "*", "program.fusion"))):
        m = manifest(os.path.basename(os.path.dirname(f)))
        if m and m.get("type") in TYPE_NAMES:
            out.append(m)
    return out


def recipes():
    out = []
    for f in sorted(glob.glob(os.path.join(RECIPES, "*.fwr"))):
        r = read_kv(f)
        if r.get("id") and r.get("id") != "fwr-check":
            r["recipe_file"] = f
            out.append(r)
    return out


def linux_recipe(appid):
    """a Flatpak-program receptje (<appid>.recipe), vagy None"""
    if not appid or not re.match(r"^[A-Za-z0-9_.-]+$", appid):
        return None
    f = os.path.join(LINUX_RECIPES, appid + ".recipe")
    r = read_kv(f) if os.path.isfile(f) else {}
    if not r:
        return None
    r["recipe_file"] = f
    return r


def _apply_linux_recipe(m):
    """a recept kulcsai a leírásba (az azonosság — id, név, típus — a leírásé marad) → True, ha változott"""
    rec = linux_recipe(m.get("appid"))
    if not rec:
        return False
    new = _fschema.apply_recipe({k: v for k, v in rec.items() if k not in ("id", "name", "type", "appid")}, m)
    new["recipe"] = os.path.basename(rec["recipe_file"])
    if new == m:
        return False
    m.clear()
    m.update(new)
    return True


def new_id(name):
    base = _slug(name)
    pid, n = base, 2
    while os.path.exists(os.path.join(PROGRAMS, pid)):
        pid = f"{base}-{n}"
        n += 1
    return pid


def _slug(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower().replace("á", "a").replace("é", "e").replace("í", "i")
                  .replace("ó", "o").replace("ö", "o").replace("ő", "o").replace("ú", "u").replace("ü", "u")
                  .replace("ű", "u")).strip("-")[:40] or "program"


def target_id(name, typ):
    """újratelepítés / frissítés: ha már van ilyen nevű, azonos típusú program, ugyanaz marad az azonosító"""
    base = _slug(name)
    m = manifest(base)
    if m and m.get("type") == typ:
        return base, m
    return new_id(name), None


def icon_path(m):
    """az ikon fájlja (abszolút út) vagy üres — akkor a felület a típus szerinti ikont mutatja"""
    ic = m.get("icon", "")
    if ic and "/" not in ic and m.get("dir"):
        p = os.path.join(m["dir"], ic)
        if os.path.isfile(p):
            return p
    if ic.startswith("/") and os.path.isfile(ic):
        return ic
    return ""


def size_mib(m):
    tot, seen = 0, set()
    paths = [m.get("dir", "")]
    if m.get("type") == "win64" and m.get("prefix") and not m["prefix"].startswith(m.get("dir", "") + "/"):
        paths.append(m["prefix"])
    for p in paths:
        for root, dirs, files in os.walk(p) if p else []:
            for f in files:
                try:
                    st = os.lstat(os.path.join(root, f))
                except OSError:
                    continue
                if (st.st_dev, st.st_ino) not in seen:
                    seen.add((st.st_dev, st.st_ino))
                    tot += st.st_blocks * 512
    return tot / 1048576.0


# ---------------------------------------------------------------------------
# felismerés
# ---------------------------------------------------------------------------
def _pe_header(data):
    if data[:2] != b"MZ" or len(data) < 0x40:
        return None
    off = struct.unpack_from("<I", data, 0x3C)[0]
    if data[off:off + 4] != b"PE\0\0":
        return None
    return off


def pe_info(path):
    """{"arch": "x64"|"x86", "gui": bool} vagy None"""
    try:
        with open(path, "rb") as f:
            data = f.read(4096)
    except OSError:
        return None
    off = _pe_header(data)
    if off is None:
        return None
    machine = struct.unpack_from("<H", data, off + 4)[0]
    magic = struct.unpack_from("<H", data, off + 24)[0]
    sub = struct.unpack_from("<H", data, off + 24 + 68)[0] if off + 24 + 70 <= len(data) else 0
    return {"arch": "x64" if magic == 0x20B or machine == 0x8664 else "x86", "gui": sub == 2}


def detect(path):
    """a fájl típusa telepítéshez: win64 | win32 | msi | appimage | flatpakref | flatpak | archive | elf | ismeretlen"""
    low = path.lower()
    if low.endswith(".flatpakref"):
        return "flatpakref"
    if low.endswith(".flatpak"):
        return "flatpak"
    if low.endswith(".msi"):
        return "msi"
    try:
        with open(path, "rb") as f:
            head = f.read(16)
    except OSError:
        return "ismeretlen"
    if head[:4] == b"\x7fELF":
        return "appimage" if head[8:11] in (b"AI\x01", b"AI\x02") or low.endswith(".appimage") else "elf"
    if head[:2] == b"MZ":
        pi = pe_info(path)
        if pi:
            return "win64" if pi["arch"] == "x64" else "win32"
    if tarfile.is_tarfile(path) or zipfile.is_zipfile(path):
        return "archive"
    return "ismeretlen"


# ---------------------------------------------------------------------------
# Windows: ikon a PE-erőforrásokból, parancsikonok (.lnk)
# ---------------------------------------------------------------------------
def pe_icon(path, out_base):
    """a program első ikoncsoportja → <out_base>.png (ha PNG van benne) vagy .ico; visszaadja a fájlnevet"""
    try:
        with open(path, "rb") as f:
            data = f.read()
    except OSError:
        return ""
    off = _pe_header(data)
    if off is None:
        return ""
    nsec = struct.unpack_from("<H", data, off + 6)[0]
    optsz = struct.unpack_from("<H", data, off + 20)[0]
    opt = off + 24
    magic = struct.unpack_from("<H", data, opt)[0]
    ddir = opt + (112 if magic == 0x20B else 96)
    rsrc_rva, rsrc_size = struct.unpack_from("<II", data, ddir + 2 * 8)
    if not rsrc_rva:
        return ""
    secs = []
    for i in range(nsec):
        s = opt + optsz + i * 40
        vsize, va, rawsz, rawptr = struct.unpack_from("<IIII", data, s + 8)
        secs.append((va, max(vsize, rawsz), rawptr))

    def r2o(rva):
        for va, sz, raw in secs:
            if va <= rva < va + sz:
                return raw + rva - va
        return None
    base = r2o(rsrc_rva)
    if base is None:
        return ""

    def entries(doff):
        n_named, n_id = struct.unpack_from("<HH", data, base + doff + 12)
        out = []
        for i in range(n_named + n_id):
            name, offd = struct.unpack_from("<II", data, base + doff + 16 + i * 8)
            out.append((name, offd))
        return out

    def leaf(offd):
        # a nyelvi szint első eleme → adatbejegyzés
        while offd & 0x80000000:
            ents = entries(offd & 0x7FFFFFFF)
            if not ents:
                return None
            offd = ents[0][1]
        rva, size = struct.unpack_from("<II", data, base + offd)
        o = r2o(rva)
        return data[o:o + size] if o is not None else None

    try:
        types = dict((n, o) for n, o in entries(0) if not n & 0x80000000)
        if 14 not in types or 3 not in types:
            return ""
        icons = {n: o for n, o in entries(types[3] & 0x7FFFFFFF)}
        groups = entries(types[14] & 0x7FFFFFFF)
        grp = leaf(groups[0][1])
        _r, _t, count = struct.unpack_from("<HHH", grp, 0)
        imgs = []
        for i in range(count):
            w, h, colors, _res, planes, bits, size, nid = struct.unpack_from("<BBBBHHIH", grp, 6 + i * 14)
            blob = leaf(icons[nid]) if nid in icons else None
            if blob:
                imgs.append((w or 256, h or 256, colors, planes, bits, blob))
    except (struct.error, KeyError, IndexError, TypeError):
        return ""
    if not imgs:
        return ""
    imgs.sort(key=lambda x: (x[0], x[4]), reverse=True)
    best = imgs[0]
    if best[5][:8] == b"\x89PNG\r\n\x1a\n":
        fn = out_base + ".png"
        with open(fn, "wb") as f:
            f.write(best[5])
        return os.path.basename(fn)
    # klasszikus ICO: az összes méret egy fájlban (a Qt a legjobbat választja)
    hdr = struct.pack("<HHH", 0, 1, len(imgs))
    offset = 6 + 16 * len(imgs)
    dirs, blobs = b"", b""
    for w, h, colors, planes, bits, blob in imgs:
        dirs += struct.pack("<BBBBHHII", w % 256, h % 256, colors, 0, planes, bits, len(blob), offset + len(blobs))
        blobs += blob
    fn = out_base + ".ico"
    with open(fn, "wb") as f:
        f.write(hdr + dirs + blobs)
    return os.path.basename(fn)


def lnk_target(path):
    """egy Windows-parancsikon célja (C:\\…\\x.exe) — a LinkInfo helyi útvonala, különben szövegkeresés"""
    try:
        with open(path, "rb") as f:
            data = f.read(65536)
    except OSError:
        return ""
    try:
        if struct.unpack_from("<I", data, 0)[0] == 0x4C:
            flags = struct.unpack_from("<I", data, 20)[0]
            pos = 76
            if flags & 0x1:
                pos += 2 + struct.unpack_from("<H", data, pos)[0]
            if flags & 0x2:
                li = pos
                lflags = struct.unpack_from("<I", data, li + 8)[0]
                hsize = struct.unpack_from("<I", data, li + 4)[0]
                if lflags & 0x1:
                    if hsize >= 0x24:
                        uoff = struct.unpack_from("<I", data, li + 28)[0]
                        if uoff:
                            s = data[li + uoff:li + uoff + 1040]
                            end = s.find(b"\0\0")
                            while end >= 0 and end % 2:
                                end = s.find(b"\0\0", end + 1)
                            t = s[:end].decode("utf-16-le", "replace")
                            if t:
                                return t
                    boff = struct.unpack_from("<I", data, li + 16)[0]
                    t = data[li + boff:data.index(b"\0", li + boff)].decode("latin-1")
                    if t:
                        return t
    except (struct.error, ValueError):
        pass
    for text in (data.decode("utf-16-le", "ignore"), data.decode("latin-1", "ignore")):
        m = re.search(r"[A-Za-z]:\\[^\x00\"<>|*?\r\n]{1,260}?\.exe", text, re.I)
        if m:
            return m.group(0)
    return ""


def win_to_unix(prefix, winpath):
    p = winpath.replace("\\", "/")
    if len(p) > 2 and p[1] == ":":
        drive = p[0].lower()
        if drive == "c":
            return os.path.join(prefix, "drive_c", p[3:])
        link = os.path.join(prefix, "dosdevices", drive + ":")
        if os.path.islink(link):
            return os.path.join(os.path.realpath(link), p[3:])
    return p


def _visible_roots(m):
    """(Linux-mappa, Windows-út) párok a program látókörében — a környezet tényleges hivatkozásaiból
    (dosdevices meghajtók, a meghajtók gyökerében lévő mappahivatkozások, pl. a D: Adatok nézet, és az
    Asztal hivatkozásai), valamint a leírás drive.X kulcsaiból (még elő nem készített környezethez)"""
    prefix = m.get("prefix") or os.path.join(FWR_DATA, m["id"])
    roots = []

    def add(target, win):
        try:
            if os.path.isdir(target):
                roots.append((os.path.realpath(target), win))
        except OSError:
            pass

    dd = os.path.join(prefix, "dosdevices")
    try:
        letters = sorted(e for e in os.listdir(dd) if re.match(r"^[a-y]:$", e) and os.path.islink(os.path.join(dd, e)))
    except OSError:
        letters = []
    for e in letters:
        win = e[0].upper() + ":\\"
        root = os.path.join(dd, e)
        add(root, win)
        if e == "c:":
            continue
        try:
            for n in os.listdir(root):
                if os.path.islink(os.path.join(root, n)):
                    add(os.path.join(root, n), win + n)
        except OSError:
            pass
    for desk in glob.glob(os.path.join(prefix, "drive_c", "users", "*", "Desktop")):
        user = os.path.basename(os.path.dirname(desk))
        try:
            for n in os.listdir(desk):
                if os.path.islink(os.path.join(desk, n)):
                    add(os.path.join(desk, n), "C:\\users\\" + user + "\\Desktop\\" + n)
        except OSError:
            pass
    for k, v in m.items():
        if k.startswith("drive."):
            add(v if v.startswith("/") else os.path.join(HOME, v), k[6:].upper() + ":\\")
    add(os.path.join(prefix, "drive_c"), "C:\\")
    # a leghosszabb (legpontosabb) Linux-mappa nyer; azonos mappánál a rövidebb Windows-út (meghajtóbetű)
    roots.sort(key=lambda r: (-len(r[0]), len(r[1])))
    return roots


def unix_to_win(m, path):
    """fájl → Windows-út a program látókörében (C: = a környezet, drive.X = megosztott mappák,
    a Fusion helyei: D: Adatok, E: pendrive, az Asztal hivatkozásai — lásd fwr places)"""
    path = os.path.realpath(path)
    for target, win in _visible_roots(m):
        if path == target:
            return win
        if path.startswith(target.rstrip("/") + "/"):
            rel = os.path.relpath(path, target).replace("/", "\\")
            return win + rel if win.endswith("\\") else win + "\\" + rel
    return ""


def _start_menu_lnks(prefix):
    pats = ["drive_c/ProgramData/Microsoft/Windows/Start Menu/Programs/**/*.lnk",
            "drive_c/users/*/AppData/Roaming/Microsoft/Windows/Start Menu/Programs/**/*.lnk",
            "drive_c/users/*/Desktop/*.lnk", "drive_c/users/Public/Desktop/*.lnk"]
    out = set()
    for p in pats:
        out.update(glob.glob(os.path.join(prefix, p), recursive=True))
    return out


def _program_exes(prefix):
    out = set()
    for pf in ("Program Files", "Program Files (x86)"):
        out.update(glob.glob(os.path.join(prefix, "drive_c", pf, "**", "*.exe"), recursive=True))
    return out


SKIP_WORDS = ("uninstall", "unins", "eltávolít", "remove", "readme", "help", "súgó", "update", "updater", "setup")


# ---------------------------------------------------------------------------
# futtatók (adapterek)
# ---------------------------------------------------------------------------
def _run(cmd, log=None, timeout=None, env=None, cwd=None):
    _log(log, "$ " + " ".join(cmd))
    try:
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, errors="replace",
                             env=env, cwd=cwd)
    except OSError as e:
        raise ProgramError(f"{cmd[0]}: {e}")
    out = []
    t0 = time.time()
    for line in p.stdout:
        line = line.rstrip("\n")
        out.append(line)
        _log(log, line)
        if timeout and time.time() - t0 > timeout:
            p.kill()
            break
    rc = p.wait()
    return rc, "\n".join(out)


def _xdg_desktop(path):
    cp = configparser.RawConfigParser(strict=False, interpolation=None)
    cp.optionxform = str
    try:
        cp.read(path, encoding="utf-8")
        return dict(cp.items("Desktop Entry"))
    except (configparser.Error, OSError, UnicodeDecodeError):
        return {}


def _desktop_name(d):
    return d.get("Name[hu]") or d.get("Name") or ""


def _best_icon(paths):
    def score(p):
        m = re.search(r"/(\d+)x\d+/", p)
        return (p.endswith(".svg"), int(m.group(1)) if m else (64 if p.endswith(".png") else 0))
    paths = [p for p in paths if os.path.isfile(p)]
    return max(paths, key=score) if paths else ""


# --- Windows ---
def _match_recipe(installer):
    name = os.path.basename(installer)
    for r in recipes():
        pat = r.get("match")
        if pat and fnmatch.fnmatch(name.lower(), pat.lower()):
            return r
    return None


def install_windows(installer, log=None, name=None, portable=False):
    kind = detect(installer)
    if kind not in ("win64", "msi", "win32"):
        raise ProgramError("nem Windows-program: " + os.path.basename(installer))
    recipe = _match_recipe(installer)
    if recipe:
        pid = recipe["id"]
        m = _fschema.apply_recipe(recipe, manifest(pid) or {})
        m["recipe"] = os.path.basename(recipe["recipe_file"])
        # a már meglévő (régi helyű) környezet marad — a telepített program és beállításai megmaradnak
        if not m.get("prefix"):
            old = os.path.join(FWR_DATA, pid)
            m["prefix"] = old if os.path.isdir(old) else os.path.join(PROGRAMS, pid, "win64")
        _log(log, f"Ismert program: {m.get('name')} (recept: {m['recipe']})")
    else:
        base = name or re.sub(r"(?i)[-_ .]*(setup|install(er)?|x64|win64|v?\d+[\d._-]*)+.*$", "",
                              os.path.splitext(os.path.basename(installer))[0]) or "Windows-program"
        pid, old = target_id(base, "win64")
        if old:      # újabb változat a meglévő környezetbe (a beállítások, adatok maradnak)
            m = old
            _log(log, f"Már telepítve: {m.get('name')} — a telepítő a meglévő környezetbe fut (frissítés)")
        else:
            m = {"id": pid, "name": base, "windows": "win10", "drive.P": "Projektek",
                 "prefix": os.path.join(PROGRAMS, pid, "win64")}
    m["type"] = "win64"
    m["source"] = "file:" + os.path.basename(installer)
    exe_known = m.get("exe", "") if recipe else ""
    old_exe = m.pop("exe", None) if not recipe else None
    existed = os.path.exists(os.path.join(PROGRAMS, pid, "program.fusion"))
    write_manifest(m)
    try:
        return _install_windows_run(installer, m, pid, recipe, name, portable, old_exe, exe_known, log)
    except ProgramError:
        if not existed:      # sikertelen új telepítés: ne maradjon félkész bejegyzés
            _rmtree(os.path.join(PROGRAMS, pid))
        raise


def _install_windows_run(installer, m, pid, recipe, name, portable, old_exe, exe_known, log):
    prefix = m["prefix"]
    if portable:
        rc, out = _run(["fwr", "prepare", pid], log)
        if rc != 0:
            raise ProgramError("a Windows-környezet nem hozható létre")
        dst_dir = os.path.join(prefix, "drive_c", "Program Files", pid)
        os.makedirs(dst_dir, exist_ok=True)
        dst = os.path.join(dst_dir, os.path.basename(installer))
        shutil.copy2(installer, dst)
        m["exe"] = "C:\\Program Files\\" + pid + "\\" + os.path.basename(installer)
    else:
        # előbb a környezet (a Windows saját programjai ne számítsanak újnak), utána a pillanatkép
        rc, out = _run(["fwr", "prepare", pid], log)
        if rc != 0:
            raise ProgramError("a Windows-környezet nem hozható létre (napló: ~/.local/share/fusion/fwr/" + pid + ".log)")
        before_lnk = _start_menu_lnks(prefix)
        before_exe = _program_exes(prefix)
        _log(log, "A telepítő elindul — a telepítő ablakában fejezze be a telepítést.")
        rc, out = _run(["fwr", "install", pid, installer], log)
        if rc != 0:
            raise ProgramError("a telepítő hibával állt le (napló: ~/.local/share/fusion/fwr/" + pid + ".log)")
        if not exe_known:
            exe = ""
            for lnk in sorted(_start_menu_lnks(prefix) - before_lnk):
                t = lnk_target(lnk)
                ln = os.path.basename(lnk).lower()
                if t.lower().endswith(".exe") and not any(w in ln for w in SKIP_WORDS) \
                        and not any(w in os.path.basename(t).lower() for w in ("unins", "uninstall")):
                    exe = t
                    if not name:   # a parancsikon neve a program valódi neve (pl. "FusionTeszt")
                        m["name"] = os.path.splitext(os.path.basename(lnk))[0]
                    break
            if not exe:
                new = [e for e in _program_exes(prefix) - before_exe
                       if not any(w in os.path.basename(e).lower() for w in SKIP_WORDS)]
                new = [e for e in new if (pe_info(e) or {}).get("gui")] or new
                if new:
                    best = max(new, key=os.path.getsize)
                    exe = "C:\\" + os.path.relpath(best, os.path.join(prefix, "drive_c")).replace("/", "\\")
            if not exe and old_exe and os.path.isfile(win_to_unix(prefix, old_exe)):
                exe = old_exe      # frissítés: nincs új parancsikon, a program a régi helyén
            if not exe:
                raise ProgramError("a telepítés után nem található a program (nincs új parancsikon vagy .exe)")
            m["exe"] = exe
    exe_path = win_to_unix(prefix, m["exe"])
    if not os.path.isfile(exe_path):
        raise ProgramError("a program nem található: " + m["exe"])
    if not m.get("icon") or m.get("icon") in ("laser", "app"):
        ic = pe_icon(exe_path, os.path.join(PROGRAMS, pid, "icon"))
        if ic:
            m["icon_tile"] = m.get("icon", "")
            m["icon"] = ic
    m["installed"] = time.strftime("%Y-%m-%d")
    write_manifest(m)
    _log(log, f"Telepítve: {m['name']} ({m['exe']})")
    return manifest(pid)


# --- Flatpak ---
def _flatpak(args, log=None, timeout=None):
    return _run(["flatpak"] + args, log, timeout)


def flatpak_ensure_remote(log=None):
    rc, out = _flatpak(["remote-add", "--user", "--if-not-exists", "flathub", FLATHUB], log, 120)
    if rc != 0:
        raise ProgramError("a Flathub nem érhető el: " + out.strip().splitlines()[-1] if out.strip() else "a Flathub nem érhető el")


def flatpak_apps(detail=False):
    """a telepített Flatpak-alkalmazások: [(azonosító, változat)] — a felhasználói és a rendszerszintű is
    (detail=True: {azonosító: (változat, "user"|"system")})"""
    rc, out = _run(["flatpak", "list", "--app", "--columns=application,version,installation"])
    if rc != 0 and detail:
        raise ProgramError("flatpak list: " + (out.strip().splitlines() or ["?"])[-1])
    res = {}
    for line in out.splitlines():
        parts = line.split("\t") if "\t" in line else line.split()
        if parts and "." in parts[0] and not line.startswith("$"):
            inst = parts[2].strip() if len(parts) > 2 else "user"
            # ha mindkét helyen ott van, a felhasználói az irányadó
            if parts[0] not in res or inst == "user":
                res[parts[0]] = (parts[1].strip() if len(parts) > 1 else "", "system" if inst == "system" else "user")
    if detail:
        return res
    return [(a, v[0]) for a, v in res.items()]


def _flatpak_scope(m):
    return "--system" if m.get("installation") == "system" else "--user"


def _flatpak_manifest(appid, version="", source="flathub", installation="user"):
    exports = FLATPAK_SYSTEM_EXPORTS if installation == "system" else FLATPAK_EXPORTS
    d = _xdg_desktop(os.path.join(exports, "applications", appid + ".desktop"))
    name = _desktop_name(d) or appid.split(".")[-1]
    existing = next((p for p in programs() if p.get("appid") == appid), None)
    pid = existing["id"] if existing else new_id(appid.split(".")[-1])
    icons = glob.glob(os.path.join(exports, "icons/hicolor/*/apps", appid + ".*"))
    m = {"id": pid, "name": name, "type": "flatpak", "appid": appid, "version": version,
         "comment": d.get("Comment[hu]") or d.get("Comment", ""),
         "categories": d.get("Categories", "").strip(";").replace(";", "; "),
         "mime": d.get("MimeType", "").strip(";"), "source": source,
         "installation": "system" if installation == "system" else "",
         "installed": (existing or {}).get("installed") or time.strftime("%Y-%m-%d")}
    os.makedirs(os.path.join(PROGRAMS, pid), exist_ok=True)
    best = _best_icon(icons)
    if best:
        dst = os.path.join(PROGRAMS, pid, "icon" + os.path.splitext(best)[1])
        shutil.copy2(best, dst)
        m["icon"] = os.path.basename(dst)
    old = manifest(pid) if existing else {}
    for k, v in (old or {}).items():          # a korábbi leírás kiegészítései (recept, felhasználói beállítás) maradnak
        if k not in m and k != "dir":
            m[k] = v
    _apply_linux_recipe(m)
    write_manifest(m)
    return manifest(pid)


def install_flatpak(ref, log=None):
    """ref: Flathub-azonosító (org.mozilla.firefox), .flatpakref vagy .flatpak fájl"""
    before = {a for a, _v in flatpak_apps()}
    if os.path.isfile(ref) and ref.endswith(".flatpakref"):
        rc, out = _flatpak(["install", "--user", "-y", "--noninteractive", "--from", ref], log, 3600)
    elif os.path.isfile(ref) and ref.endswith(".flatpak"):
        rc, out = _flatpak(["install", "--user", "-y", "--noninteractive", "--bundle", ref], log, 3600)
    else:
        if not re.match(r"^[A-Za-z0-9_.-]+\.[A-Za-z0-9_.-]+$", ref):
            raise ProgramError("érvénytelen Flathub-azonosító: " + ref)
        flatpak_ensure_remote(log)
        rc, out = _flatpak(["install", "--user", "-y", "--noninteractive", "flathub", ref], log, 3600)
    if rc != 0:
        raise ProgramError("a Flatpak-telepítés nem sikerült: " + (out.strip().splitlines() or ["?"])[-1])
    apps = dict(flatpak_apps())
    new = [a for a in apps if a not in before] or ([ref] if ref in apps else [])
    if not new:
        raise ProgramError("a telepítés után nem található az alkalmazás")
    m = None
    for a in new:
        m = _flatpak_manifest(a, apps.get(a, ""), "flathub" if not os.path.isfile(ref) else "file:" + os.path.basename(ref))
        _log(log, f"Telepítve: {m['name']} ({a})")
    return m


def flatpak_search(term, log=None):
    if not term.strip():
        return []
    flatpak_ensure_remote(log)
    rc, out = _run(["flatpak", "search", "--user", "--columns=name,description,application,version", term], None, 120)
    res = []
    for line in out.splitlines():
        p = line.split("\t")
        if len(p) >= 3 and "." in p[2]:
            res.append({"name": p[0], "desc": p[1], "appid": p[2], "version": p[3] if len(p) > 3 else ""})
    return res[:50]


# --- AppImage / natív ---
def _swap_app(pid):
    """az új változat (app.new) a régi (app) helyére — a felhasználói adatok nem itt vannak"""
    base = os.path.join(PROGRAMS, pid)
    _rmtree(os.path.join(base, "app"))
    os.rename(os.path.join(base, "app.new"), os.path.join(base, "app"))
    return os.path.join(base, "app")


def install_appimage(path, log=None, name=None):
    pid, old = target_id(name or re.sub(r"(?i)[-_.](x86_64|amd64|linux).*$", "", os.path.splitext(os.path.basename(path))[0]), "appimage")
    d = os.path.join(PROGRAMS, pid, "app.new")
    _rmtree(d)
    os.makedirs(d)
    tmp = os.path.join(d, "telepito.AppImage")
    shutil.copy2(path, tmp)
    os.chmod(tmp, 0o755)
    rc, out = _run([tmp, "--appimage-extract"], log, 600, cwd=d)
    os.unlink(tmp)
    if rc != 0 or not os.path.isfile(os.path.join(d, "squashfs-root", "AppRun")):
        _rmtree(d if old else os.path.join(PROGRAMS, pid))
        raise ProgramError("az AppImage nem bontható ki")
    d = _swap_app(pid)
    root = os.path.join(d, "squashfs-root")
    desk = next(iter(glob.glob(os.path.join(root, "*.desktop"))), "")
    dd = _xdg_desktop(desk) if desk else {}
    m = {"id": pid, "name": name or _desktop_name(dd) or pid, "type": "appimage", "exec": "app/squashfs-root/AppRun",
         "comment": dd.get("Comment[hu]") or dd.get("Comment", ""), "mime": dd.get("MimeType", "").strip(";"),
         "categories": dd.get("Categories", "").strip(";").replace(";", "; "),
         "source": "file:" + os.path.basename(path), "installed": time.strftime("%Y-%m-%d")}
    ic = dd.get("Icon", "")
    best = _best_icon(glob.glob(os.path.join(root, ic + ".*")) + glob.glob(os.path.join(root, "usr/share/icons/hicolor/*/apps", ic + ".*"))) if ic else ""
    if not best and os.path.exists(os.path.join(root, ".DirIcon")):
        best = os.path.join(root, ".DirIcon")
    if best:
        ext = os.path.splitext(best)[1] or ".png"
        shutil.copy2(best, os.path.join(PROGRAMS, pid, "icon" + ext))
        m["icon"] = "icon" + ext
    write_manifest(m)
    _log(log, f"Telepítve: {m['name']} (AppImage)")
    return manifest(pid)


def install_native(path, log=None, name=None, exec_rel=None):
    """archívum (tar.*, zip) vagy önálló Linux-bináris a program mappájába"""
    base = re.sub(r"(?i)(\.tar)?\.(gz|xz|bz2|zst|zip|tgz|txz)$", "", os.path.basename(path))
    pid, old = target_id(name or re.sub(r"[-_.]v?\d.*$", "", base) or base, "native")
    d = os.path.join(PROGRAMS, pid, "app.new")
    _rmtree(d)
    os.makedirs(d)
    try:
        if detect(path) == "elf":
            dst = os.path.join(d, os.path.basename(path))
            shutil.copy2(path, dst)
            os.chmod(dst, 0o755)
            exec_rel = exec_rel or os.path.basename(path)
        elif tarfile.is_tarfile(path):
            with tarfile.open(path) as t:
                t.extractall(d, filter="tar")
        elif zipfile.is_zipfile(path):
            with zipfile.ZipFile(path) as z:
                for i in z.infolist():
                    target = os.path.realpath(os.path.join(d, i.filename))
                    if target.startswith(os.path.realpath(d) + "/"):
                        z.extract(i, d)
                        mode = (i.external_attr >> 16) & 0o777
                        if mode:
                            os.chmod(target, mode)
        else:
            raise ProgramError("nem ismert formátum")
    except (tarfile.TarError, OSError, zipfile.BadZipFile, ProgramError) as e:
        _rmtree(d if old else os.path.join(PROGRAMS, pid))
        raise ProgramError(f"a kicsomagolás nem sikerült: {e}")
    d = _swap_app(pid)
    dd, desk = {}, ""
    for f in glob.glob(os.path.join(d, "**", "*.desktop"), recursive=True):
        desk, dd = f, _xdg_desktop(f)
        break
    if not exec_rel and dd.get("Exec"):
        cand = dd["Exec"].split()[0]
        for c in [os.path.join(os.path.dirname(desk), cand)] + glob.glob(os.path.join(d, "**", os.path.basename(cand)), recursive=True):
            if os.path.isfile(c) and os.access(c, os.X_OK):
                exec_rel = os.path.relpath(c, os.path.join(PROGRAMS, pid))
                break
    if not exec_rel:
        tops = [x for x in os.listdir(d) if not x.startswith(".")]
        if len(tops) == 1 and os.path.isdir(os.path.join(d, tops[0])):
            c = os.path.join(d, tops[0], tops[0])
            if os.path.isfile(c) and os.access(c, os.X_OK):
                exec_rel = os.path.relpath(c, os.path.join(PROGRAMS, pid))
    elif not exec_rel.startswith("app/"):
        exec_rel = os.path.join("app", exec_rel) if os.path.exists(os.path.join(d, exec_rel)) else exec_rel
    if not exec_rel:
        if not old:
            _rmtree(os.path.join(PROGRAMS, pid))
        raise ProgramError("nem található a program indítófájlja (adja meg: --exec <út az archívumon belül>)")
    nm = name or _desktop_name(dd) or (os.path.basename(exec_rel).capitalize())
    m = {"id": pid, "name": nm, "type": "native", "exec": exec_rel, "mime": dd.get("MimeType", "").strip(";"),
         "comment": dd.get("Comment[hu]") or dd.get("Comment", ""),
         "categories": dd.get("Categories", "").strip(";").replace(";", "; "),
         "source": "file:" + os.path.basename(path), "installed": time.strftime("%Y-%m-%d")}
    if dd.get("X-Fusion-Open"):
        m["open"] = dd["X-Fusion-Open"]
    pngs = [p for p in glob.glob(os.path.join(d, "**", "*.png"), recursive=True) + glob.glob(os.path.join(d, "**", "*.svg"), recursive=True)]
    ic = dd.get("Icon", "")
    pref = [p for p in pngs if ic and os.path.splitext(os.path.basename(p))[0] == os.path.basename(ic)] or \
           [p for p in pngs if re.search(r"default128\.png$|icon.*\.(png|svg)$|" + re.escape(pid) + r".*\.(png|svg)$", p, re.I)]
    if pref:
        best = max(pref, key=lambda p: (p.endswith(".svg"), os.path.getsize(p)))
        ext = os.path.splitext(best)[1]
        shutil.copy2(best, os.path.join(PROGRAMS, pid, "icon" + ext))
        m["icon"] = "icon" + ext
    write_manifest(m)
    _log(log, f"Telepítve: {m['name']} ({exec_rel})")
    return manifest(pid)


# --- Windows-program archívumban (hordozható: a teljes mappa kell, pl. Vas & Króm Windows-változat) ---
def _archive_names(path):
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as z:
            return [i.filename for i in z.infolist() if not i.is_dir()]
    with tarfile.open(path) as t:
        return [i.name for i in t.getmembers() if i.isfile()]


def archive_windows_exes(path):
    """az archívumban lévő Windows-programok (.exe) — ha Linux-indítófájl (.desktop) is van, natívnak számít"""
    try:
        names = _archive_names(path)
    except (OSError, zipfile.BadZipFile, tarfile.TarError):
        return []
    if any(n.lower().endswith(".desktop") or n.lower().endswith(".appimage") for n in names):
        return []
    return [n for n in names if n.lower().endswith(".exe")]


def install_windows_archive(path, log=None, name=None, exec_rel=None):
    """ZIP / tar egy hordozható Windows-programmal: a teljes tartalom a Windows-környezet Program Files mappájába,
    az indítandó .exe a legfelső szinten lévő grafikus program (nem telepítő, nem eltávolító, nem segédprogram)"""
    base = re.sub(r"(?i)(\.tar)?\.(gz|xz|bz2|zst|zip|tgz|txz)$", "", os.path.basename(path))
    base = re.sub(r"(?i)[-_ .]*(windows|win64|win|x64|portable|v?\d+[\d._-]*)+.*$", "", base) or base
    pid, old = target_id(name or base, "win64")
    m = old or {"id": pid, "name": name or base, "windows": "win10", "drive.P": "Projektek",
                "prefix": os.path.join(PROGRAMS, pid, "win64")}
    m["type"] = "win64"
    m["source"] = "file:" + os.path.basename(path)
    existed = os.path.exists(os.path.join(PROGRAMS, pid, "program.fusion"))
    write_manifest(m)
    try:
        rc, out = _run(["fwr", "prepare", pid], log)
        if rc != 0:
            raise ProgramError("a Windows-környezet nem hozható létre")
        dst = os.path.join(m["prefix"], "drive_c", "Program Files", pid)
        _rmtree(dst)
        os.makedirs(dst)
        root = os.path.realpath(dst) + "/"
        _log(log, f"Kicsomagolás: {os.path.basename(path)} → C:\\Program Files\\{pid}")
        if zipfile.is_zipfile(path):
            with zipfile.ZipFile(path) as z:
                for i in z.infolist():
                    if os.path.realpath(os.path.join(dst, i.filename)).startswith(root):
                        z.extract(i, dst)
        else:
            with tarfile.open(path) as t:
                t.extractall(dst, filter="data")
        # egyetlen legfelső mappa (pl. VasEsKrom/) → a tartalma közvetlenül a program mappájába
        top = os.listdir(dst)
        if len(top) == 1 and os.path.isdir(os.path.join(dst, top[0])):
            inner = os.path.join(dst, top[0])
            for n in os.listdir(inner):
                os.rename(os.path.join(inner, n), os.path.join(dst, n))
            os.rmdir(inner)
        if exec_rel:
            exe = os.path.join(dst, exec_rel)
        else:
            cands = []
            for e in glob.glob(os.path.join(dst, "**", "*.exe"), recursive=True):
                bn = os.path.basename(e).lower()
                if any(w in bn for w in SKIP_WORDS) or any(w in bn for w in ("unins", "setup", "install")) \
                        or re.match(r"^pythonw?(\d|\.exe)", bn) or bn in ("python.exe", "pythonw.exe"):
                    continue
                pi = pe_info(e) or {}
                cands.append((os.path.relpath(e, dst).count("/"), not pi.get("gui"),
                              _slug(os.path.splitext(bn)[0]) != _slug(base), e))
            if not cands:
                raise ProgramError("az archívumban nincs indítható Windows-program (.exe)")
            exe = sorted(cands)[0][3]
        if not os.path.isfile(exe):
            raise ProgramError("a program nem található: " + exe)
        m["exe"] = "C:\\" + os.path.relpath(exe, os.path.join(m["prefix"], "drive_c")).replace("/", "\\")
        ic = pe_icon(exe, os.path.join(PROGRAMS, pid, "icon"))
        if ic:
            m["icon"] = ic
        m["installed"] = time.strftime("%Y-%m-%d")
        write_manifest(m)
        _log(log, f"Telepítve: {m['name']} ({m['exe']})")
        return manifest(pid)
    except (ProgramError, OSError, zipfile.BadZipFile, tarfile.TarError) as e:
        if not existed:
            _rmtree(os.path.join(PROGRAMS, pid))
        raise ProgramError(str(e)) if not isinstance(e, ProgramError) else e


def install(src, log=None, name=None, exec_rel=None, portable=False):
    """telepítés bármiből: fájl (típus felismerve) vagy flathub:<azonosító>"""
    if src.startswith("flathub:"):
        m = install_flatpak(src[8:], log)
    else:
        if not os.path.isfile(src):
            raise ProgramError("nem található: " + src)
        kind = detect(src)
        _log(log, f"Felismerve: {kind} — {os.path.basename(src)}")
        if kind in ("win64", "msi", "win32"):
            m = install_windows(src, log, name, portable)
        elif kind in ("flatpakref", "flatpak"):
            m = install_flatpak(src, log)
        elif kind == "appimage":
            m = install_appimage(src, log, name)
        elif kind == "archive" and archive_windows_exes(src):
            m = install_windows_archive(src, log, name, exec_rel)
        elif kind in ("archive", "elf"):
            m = install_native(src, log, name, exec_rel)
        else:
            raise ProgramError("ismeretlen fájltípus: " + os.path.basename(src))
    sync_desktop()
    return m


# ---------------------------------------------------------------------------
# eltávolítás, frissítés, szinkron
# ---------------------------------------------------------------------------
def remove(pid, data=False, log=None):
    m = manifest(pid)
    if not m:
        raise ProgramError("nincs ilyen program: " + pid)
    t = m.get("type")
    if t == "flatpak":
        args = ["uninstall", _flatpak_scope(m), "-y", "--noninteractive"] + (["--delete-data"] if data else []) + [m["appid"]]
        rc, out = _flatpak(args, log, 600)
        if rc != 0 and "not installed" not in out:
            raise ProgramError("a Flatpak-eltávolítás nem sikerült: " + (out.strip().splitlines() or ["?"])[-1])
        _flatpak(["uninstall", _flatpak_scope(m), "-y", "--noninteractive", "--unused"], log, 600)
    elif t == "win64":
        prefix = m.get("prefix", "")
        shared = [p for p in programs() if p["id"] != pid and p.get("prefix") == prefix]
        if prefix and not shared:
            subprocess.run(["fwr", "stop", pid], capture_output=True, timeout=30)
            _rmtree(prefix)
            _log(log, "a Windows-környezet törölve: " + prefix)
    _rmtree(m["dir"])
    if data and t in ("native", "appimage"):
        for p in glob.glob(os.path.join(HOME, ".config", pid)) + glob.glob(os.path.join(HOME, ".local/share", pid)):
            _rmtree(p)
    sync_desktop()
    _log(log, f"Eltávolítva: {m.get('name', pid)}")


def update(pid, log=None):
    m = manifest(pid)
    if not m:
        raise ProgramError("nincs ilyen program: " + pid)
    if m.get("type") == "flatpak":
        rc, out = _flatpak(["update", _flatpak_scope(m), "-y", "--noninteractive", m["appid"]], log, 3600)
        if rc != 0:
            raise ProgramError("a frissítés nem sikerült: " + (out.strip().splitlines() or ["?"])[-1])
        ver = dict(flatpak_apps()).get(m["appid"], m.get("version", ""))
        _flatpak_manifest(m["appid"], ver, m.get("source", "flathub"), m.get("installation") or "user")
        sync_desktop()
        return "kész" + (f" ({ver})" if ver else "")
    if m.get("type") == "win64":
        return "Windows-program: frissítés az újabb telepítővel (Programkezelő → Telepítés fájlból)"
    return "a program saját frissítőjével, vagy az újabb változat telepítésével"


def sync(log=None):
    """a már telepített Flatpakok (pl. parancssorból) és a régi helyű Windows-programok leírást kapnak"""
    try:
        have = flatpak_apps(detail=True) if shutil.which("flatpak") else None
    except ProgramError as e:      # a Flatpak most nem kérdezhető le: ne vegyünk ki semmit
        _log(log, str(e))
        have = None
    if have is not None:
        known = {}
        for p in programs():
            if p.get("type") == "flatpak":
                known[p.get("appid")] = p
        for appid, p in known.items():         # recept (pl. URL-séma) a már meglévő leírásokra is
            if appid in have and _apply_linux_recipe(p):
                p.pop("dir", None)
                write_manifest(p)
                _log(log, f"Recept alkalmazva: {p.get('name', appid)} ({p['recipe']})")
        for appid, (ver, inst) in sorted(have.items()):
            if appid not in known:
                m = _flatpak_manifest(appid, ver, "flatpak (parancssor)", inst)
                _log(log, f"Felvéve: {m['name']} ({appid})")
        # kívülről eltávolított Flatpak: a leírása is megy (az adatai a Flatpaké, azokhoz nem nyúlunk)
        for appid, p in known.items():
            if appid and appid not in have:
                _rmtree(p["dir"])
                _log(log, f"Kivéve (már nincs telepítve): {p.get('name', appid)}")
    # régi helyű (fwr) Windows-programok: leírás a meglévő környezetre — újratelepítés nélkül
    for r in recipes():
        pid = r["id"]
        if manifest(pid):
            continue
        prefix = os.path.join(FWR_DATA, pid)
        exe = win_to_unix(prefix, r.get("exe", "")) if r.get("exe") else ""
        if exe and os.path.isfile(exe):
            m = _fschema.apply_recipe(r)
            m.update({"type": "win64", "prefix": prefix, "recipe": os.path.basename(r["recipe_file"]),
                      "source": "átköltöztetve (fwr)", "installed": time.strftime("%Y-%m-%d")})
            write_manifest(m)
            ic = pe_icon(exe, os.path.join(PROGRAMS, pid, "icon"))
            if ic:
                m["icon_tile"], m["icon"] = m.get("icon", ""), ic
                write_manifest(m)
            _log(log, f"Átköltöztetve: {m.get('name', pid)} (a meglévő környezet marad: {prefix})")
    sync_desktop()


_watch_state = None


def changed_outside():
    """volt-e kívülről (parancssorból) Flatpak-telepítés / -eltávolítás a legutóbbi hívás óta — olcsó (mtime)"""
    global _watch_state
    st = []
    for d in WATCH_DIRS:
        try:
            st.append(os.stat(d).st_mtime_ns)
        except OSError:
            st.append(0)
    first, changed = _watch_state is None, st != _watch_state
    _watch_state = st
    return changed and not first


def sync_desktop():
    """XDG-bejegyzések (~/.local/share/applications/fusion-<id>.desktop) és alapértelmezett társítások"""
    os.makedirs(APPS_DIR, exist_ok=True)
    keep = set()
    defaults = {}
    schemes = {}
    for m in programs():
        fn = os.path.join(APPS_DIR, f"fusion-{m['id']}.desktop")
        keep.add(fn)
        mimes = [x for x in m.get("mime", "").replace(",", ";").split(";") if x.strip()]
        for ext in m.get("open", "").split():
            mt = mimetypes.guess_type("x" + ext)[0]
            if mt and mt not in mimes:
                mimes.append(mt)
        for sch in m.get("scheme", "").split():       # URL-séma (pl. prusaslicer://) — a böngészőből ide jut
            if re.match(r"^[a-z][a-z0-9+.-]*$", sch) and "x-scheme-handler/" + sch not in mimes:
                mimes.append("x-scheme-handler/" + sch)
        lines = ["[Desktop Entry]", "Type=Application", f"Name={m.get('name', m['id'])}",
                 f"Exec=fusion-run {m['id']} %U", f"Comment={m.get('comment', '')}",
                 f"Icon={icon_path(m) or 'application-x-executable'}", "Terminal=false",
                 f"Categories={m.get('categories', '').replace('; ', ';')};" if m.get("categories") else "Categories=",
                 f"MimeType={';'.join(mimes)};" if mimes else "MimeType=", "X-Fusion-Program=" + m["id"]]
        with open(fn, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        for mt in mimes:
            defaults.setdefault(mt, os.path.basename(fn))
            if mt.startswith("x-scheme-handler/"):
                schemes[mt] = f"fusion-{m['id']}"
    _seed_url_choices(schemes)
    for f in glob.glob(os.path.join(APPS_DIR, "fusion-*.desktop")):
        if f not in keep:
            os.unlink(f)
    # mimeapps.list: csak a Fúzió-bejegyzések alapértelmezései (a felhasználó választása elsőbbséget kap)
    user = _assoc_user()
    # a kiterjesztéssel megadott választás (.svg → program) a MIME-típusára is vonatkozik
    for k, pid in list(user.items()):
        if k.startswith(".") and pid != BUILTIN:
            mt = mimetypes.guess_type("x" + k)[0]
            if mt and mt not in user:
                user[mt] = pid
                defaults.setdefault(mt, f"fusion-{pid}.desktop")
    lines = ["[Default Applications]"]
    for mt, desk in sorted(defaults.items()):
        pid = user.get(mt)
        lines.append(f"{mt}=fusion-{pid}.desktop" if pid and manifest(pid) else f"{mt}={desk}")
    os.makedirs(os.path.join(HOME, ".config"), exist_ok=True)
    with open(os.path.join(HOME, ".config", "mimeapps.list"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def _seed_url_choices(schemes):
    """Flatpak-programok (pl. a Firefox) linkjei az OpenURI-portálon át nyílnak meg, amely az első néhány alkalommal
    „Megnyitás ezzel…” ablakot mutat — az URL-sémás programnál (prusaslicer://) ez fölösleges kérdés. A portál
    „korábbi választás” tárolójába (desktop-used-apps) bejegyezzük a programot minden Flatpak-programnak, amelynek
    még nincs választása; a felhasználó későbbi választását nem írjuk felül."""
    if not schemes or not shutil.which("flatpak"):
        return
    try:
        r = subprocess.run(["flatpak", "list", "--app", "--columns=application"], capture_output=True, text=True, timeout=30)
        # "" = nem homokozós hívó (a portál így azonosítja) — a QEMU-teszt és a gio-alapú programok útja
        apps = [""] + sorted({a.strip() for a in r.stdout.split() if re.match(r"^[A-Za-z0-9_.-]+$", a.strip())})
    except (OSError, subprocess.SubprocessError):
        return
    for ctype, choice in schemes.items():
        try:
            r = subprocess.run(["flatpak", "permissions", "desktop-used-apps", ctype], capture_output=True, text=True, timeout=10)
            have = {l.split("\t")[2] for l in r.stdout.splitlines() if l.count("\t") >= 3 and l.startswith("desktop-used-apps")}
            for app in apps:
                if app not in have:
                    subprocess.run(["flatpak", "permission-set", "desktop-used-apps", ctype, app, choice, "3"],
                                   capture_output=True, timeout=10)
        except (OSError, subprocess.SubprocessError):
            continue


def _assoc_user():
    try:
        with open(ASSOC_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def associate(key, pid):
    """a felhasználó választása: kiterjesztés (.lbrn) vagy MIME-típus → program"""
    a = _assoc_user()
    a[key] = pid
    os.makedirs(os.path.dirname(ASSOC_FILE), exist_ok=True)
    with open(ASSOC_FILE, "w", encoding="utf-8") as f:
        json.dump(a, f, ensure_ascii=False, indent=1)
    sync_desktop()


def dissociate(key):
    """a felhasználó választásának törlése (vissza az alapértelmezésre)"""
    a = _assoc_user()
    if a.pop(key, None) is None:
        return
    os.makedirs(os.path.dirname(ASSOC_FILE), exist_ok=True)
    with open(ASSOC_FILE, "w", encoding="utf-8") as f:
        json.dump(a, f, ensure_ascii=False, indent=1)
    sync_desktop()


BUILTIN = "-"      # a társítás értéke, ha a Fusion saját nézőkéje nyissa meg


def assoc_key(path):
    """a társítás kulcsa: a kiterjesztés (.svg), ennek hiányában a MIME-típus"""
    base = os.path.basename(path.lower())
    if "." in base.strip("."):
        return "." + base.rsplit(".", 1)[1]
    return mimetypes.guess_type(path)[0] or ""


def open_with_choices(path):
    """a „Megnyitás ezzel…” ablakhoz: {key, current, items: [{id, name, icon, iconFile, rec}]}
    rec: a program jelzi, hogy megnyitja ezt a típust (ezek elöl)"""
    key = assoc_key(path)
    cur = _assoc_user().get(key, "")
    low = path.lower()
    ext = "." + low.rsplit(".", 1)[1] if "." in os.path.basename(low) else ""
    mt = mimetypes.guess_type(path)[0] or ""
    rec = {m["id"] for m in programs()
           if (ext and ext in m.get("open", "").lower().split())
           or (mt and mt in [x.strip() for x in m.get("mime", "").replace(",", ";").split(";")])}
    items = []
    for m in programs():
        i = info(m)
        items.append({"id": m["id"], "name": i["name"], "icon": i["icon"], "iconFile": i["iconFile"], "rec": m["id"] in rec})
    items.sort(key=lambda x: (not x["rec"], x["name"].lower()))
    return {"key": key, "current": cur, "items": items}


def assoc(path, explicit_only=False):
    """melyik program nyitja meg a fájlt: [(id, név)], az alapértelmezett elöl
    explicit_only: csak a Fúzió-társítás (open = kiterjesztés) vagy a felhasználó választása számít,
    a programok MIME-típus-igénye nem (pl. ne a Firefox nyisson meg minden képet)"""
    low = path.lower()
    ext = "." + low.rsplit(".", 1)[1] if "." in os.path.basename(low) else ""
    mt = mimetypes.guess_type(path)[0] or ""
    user = _assoc_user()
    if (user.get(ext) or user.get(mt)) == BUILTIN:
        return []
    res = []
    for m in programs():
        exts = m.get("open", "").lower().split()
        mimes = [x.strip() for x in m.get("mime", "").replace(",", ";").split(";") if x.strip()]
        pref_id = user.get(ext) or user.get(mt)
        if (ext and ext in exts) or (mt and mt in mimes and (not explicit_only or pref_id == m["id"])):
            res.append((m["id"], m.get("name", m["id"])))
    pref = user.get(ext) or user.get(mt)
    # a felhasználó választása akkor is számít, ha a program maga nem jelzi ezt a típust
    if pref and pref not in [r[0] for r in res]:
        pm = manifest(pref)
        if pm:
            res.append((pref, pm.get("name", pref)))
    res.sort(key=lambda x: x[0] != pref)
    return res


# ---------------------------------------------------------------------------
# indítás
# ---------------------------------------------------------------------------
def is_url(a):
    return bool(re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", a)) and not a.startswith("file://")


def command(pid, files=()):
    """files: fájlok vagy webcímek (http://…) — a webcím változatlanul megy tovább"""
    m = manifest(pid)
    if not m:
        raise ProgramError("nincs ilyen program: " + pid)
    t = m.get("type")
    if t == "win64":
        args = []
        if any(not is_url(f) for f in files):
            # a Fusion helyei (D: Adatok, E: pendrive) frissek legyenek a fájl Windows-útjához
            try:
                subprocess.run(["fwr", "places", pid], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=20)
            except (OSError, subprocess.SubprocessError):
                pass
        for f in files:
            if is_url(f):
                args.append(f)
                continue
            w = unix_to_win(m, f)
            if not w:
                raise ProgramError(f"a fájl nincs a program látókörében: {f} (megosztott mappák: " +
                                   ", ".join(f"{k[6:].upper()}: {v}" for k, v in m.items() if k.startswith("drive.")) + ")")
            args.append(w)
        return ["fwr", "launch", pid] + args, None
    if t == "flatpak":
        paths = [f for f in files if not is_url(f)]
        urls = [f for f in files if is_url(f)]
        cmd = ["flatpak", "run"]
        if paths:      # a fájlok a dokumentum-portálon át jutnak be a homokozóba
            cmd += ["--file-forwarding", m["appid"], "@@"] + paths + ["@@"]
        else:
            cmd += [m["appid"]]
        return cmd + (_url_args(m) if urls else []) + urls, None
    exe = os.path.join(m["dir"], m.get("exec", ""))
    if not os.path.isfile(exe):
        raise ProgramError("a program indítófájlja hiányzik: " + exe)
    urls = [f for f in files if is_url(f)]
    return [exe] + (_url_args(m) if urls else []) + list(files), os.path.dirname(exe)


def _url_args(m):
    """a program kapcsolói webcímes / URL-sémás indításhoz (url_args), pl. --single-instance-on-url"""
    return [a for a in m.get("url_args", "").split() if re.match(r"^--?[A-Za-z0-9][A-Za-z0-9_=.-]*$", a)]


def launch(pid, files=()):
    cmd, cwd = command(pid, files)
    subprocess.Popen(cmd, cwd=cwd, start_new_session=True, stdin=subprocess.DEVNULL,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return cmd


def info(m):
    """a felületnek: egy program összefoglalása"""
    return {"id": m["id"], "name": m.get("name", m["id"]), "type": m.get("type"), "typeName": TYPE_NAMES.get(m.get("type"), "?"),
            "version": m.get("version", ""), "comment": m.get("comment", ""), "iconFile": icon_path(m),
            "icon": m.get("icon_tile") or {"win64": "app", "flatpak": "app", "appimage": "app", "native": "app"}.get(m.get("type"), "app"),
            "installed": m.get("installed", ""), "source": m.get("source", ""), "appid": m.get("appid", ""), "dir": m.get("dir", ""),
            "exe": m.get("exe", ""), "prefix": m.get("prefix", ""), "open": m.get("open", ""),
            "devices": {k[5:]: v for k, v in m.items() if k.startswith("port.")},
            "folders": {k[6:].upper(): v for k, v in m.items() if k.startswith("drive.")},
            "canUpdate": m.get("type") == "flatpak",
            "protection": _fperm.of(m)["protection"], "sandbox": m.get("sandbox", "no") == "yes",
            "net": m.get("allow.net", "yes") != "no", "allowFiles": m.get("allow.files", "")}


def set_device(pid, com, role):
    """jogosultság: Windows-program soros eszköze (COMn → szerep), üres szerep = törlés"""
    m = manifest(pid)
    if not m or m.get("type") != "win64":
        raise ProgramError("csak Windows-programnál")
    if not re.match(r"^COM[1-9]$", com) or (role and not re.match(r"^[a-z0-9_-]+$", role)):
        raise ProgramError("érvénytelen beállítás")
    key = "port." + com
    if role:
        m[key] = role
    else:
        m.pop(key, None)
    m.pop("dir", None)
    write_manifest(m)
