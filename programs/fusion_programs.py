"""FusionOS — Fusion Programkezelő (Fusion Program Runtime): a háttérrész

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
FWR_DATA = os.environ.get("FWR_DATA", "/data/fwr")
HOME = os.path.expanduser("~")
APPS_DIR = os.path.join(HOME, ".local/share/applications")
FLATPAK_EXPORTS = os.path.join(HOME, ".local/share/flatpak/exports/share")
FLATHUB = "https://dl.flathub.org/repo/flathub.flatpakrepo"
ASSOC_FILE = os.path.join(HOME, ".config/fusion/associations.json")
TYPE_NAMES = {"win64": "Windows", "flatpak": "Linux (Flatpak)", "appimage": "Linux (AppImage)", "native": "Linux"}
ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")


class ProgramError(Exception):
    pass


def _log(log, msg):
    if log:
        log(msg)


# ---------------------------------------------------------------------------
# leírás (manifest)
# ---------------------------------------------------------------------------
def read_kv(path):
    d = {}
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    d[k.strip()] = v.strip()
    except OSError:
        pass
    return d


def write_manifest(m):
    d = os.path.join(PROGRAMS, m["id"])
    os.makedirs(d, exist_ok=True)
    order = ["id", "name", "type", "version", "comment", "exec", "exe", "appid", "icon", "categories",
             "open", "mime", "windows", "prefix", "installed", "source", "recipe"]
    keys = order + sorted(k for k in m if k not in order)
    lines = ["# FusionOS — Fusion Programkezelő: programleírás (a Programkezelő írja)"]
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


def unix_to_win(m, path):
    """fájl → Windows-út a program látókörében (C: = a környezet, drive.X = megosztott mappák)"""
    path = os.path.realpath(path)
    prefix = m.get("prefix") or os.path.join(FWR_DATA, m["id"])
    for k, v in m.items():
        if k.startswith("drive."):
            target = v if v.startswith("/") else os.path.join(HOME, v)
            target = os.path.realpath(target)
            if path == target:
                return k[6:].upper() + ":\\"
            if path.startswith(target + "/"):
                return k[6:].upper() + ":\\" + os.path.relpath(path, target).replace("/", "\\")
    c = os.path.realpath(os.path.join(prefix, "drive_c"))
    if path.startswith(c + "/"):
        return "C:\\" + os.path.relpath(path, c).replace("/", "\\")
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
        m = manifest(pid) or {}
        m.update({k: v for k, v in recipe.items() if k not in ("recipe_file", "match")})
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
    write_manifest(m)

    prefix = m["prefix"]
    if portable:
        _run(["fwr", "prepare", pid], log)
        dst_dir = os.path.join(prefix, "drive_c", "Program Files", pid)
        os.makedirs(dst_dir, exist_ok=True)
        dst = os.path.join(dst_dir, os.path.basename(installer))
        shutil.copy2(installer, dst)
        m["exe"] = "C:\\Program Files\\" + pid + "\\" + os.path.basename(installer)
    else:
        before_lnk = _start_menu_lnks(prefix) if os.path.isdir(prefix) else set()
        before_exe = _program_exes(prefix) if os.path.isdir(prefix) else set()
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


def flatpak_apps():
    rc, out = _run(["flatpak", "list", "--user", "--app", "--columns=application,version"])
    res = []
    for line in out.splitlines():
        parts = line.split("\t") if "\t" in line else line.split()
        if parts and "." in parts[0] and not line.startswith("$"):
            res.append((parts[0], parts[1] if len(parts) > 1 else ""))
    return res


def _flatpak_manifest(appid, version="", source="flathub"):
    d = _xdg_desktop(os.path.join(FLATPAK_EXPORTS, "applications", appid + ".desktop"))
    name = _desktop_name(d) or appid.split(".")[-1]
    existing = next((p for p in programs() if p.get("appid") == appid), None)
    pid = existing["id"] if existing else new_id(appid.split(".")[-1])
    icons = glob.glob(os.path.join(FLATPAK_EXPORTS, "icons/hicolor/*/apps", appid + ".*"))
    m = {"id": pid, "name": name, "type": "flatpak", "appid": appid, "version": version,
         "comment": d.get("Comment[hu]") or d.get("Comment", ""),
         "categories": d.get("Categories", "").strip(";").replace(";", "; "),
         "mime": d.get("MimeType", "").strip(";"), "source": source,
         "installed": (existing or {}).get("installed") or time.strftime("%Y-%m-%d")}
    os.makedirs(os.path.join(PROGRAMS, pid), exist_ok=True)
    best = _best_icon(icons)
    if best:
        dst = os.path.join(PROGRAMS, pid, "icon" + os.path.splitext(best)[1])
        shutil.copy2(best, dst)
        m["icon"] = os.path.basename(dst)
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
    shutil.rmtree(os.path.join(base, "app"), ignore_errors=True)
    os.rename(os.path.join(base, "app.new"), os.path.join(base, "app"))
    return os.path.join(base, "app")


def install_appimage(path, log=None, name=None):
    pid, old = target_id(name or re.sub(r"(?i)[-_.](x86_64|amd64|linux).*$", "", os.path.splitext(os.path.basename(path))[0]), "appimage")
    d = os.path.join(PROGRAMS, pid, "app.new")
    shutil.rmtree(d, ignore_errors=True)
    os.makedirs(d)
    tmp = os.path.join(d, "telepito.AppImage")
    shutil.copy2(path, tmp)
    os.chmod(tmp, 0o755)
    rc, out = _run([tmp, "--appimage-extract"], log, 600, cwd=d)
    os.unlink(tmp)
    if rc != 0 or not os.path.isfile(os.path.join(d, "squashfs-root", "AppRun")):
        shutil.rmtree(d if old else os.path.join(PROGRAMS, pid), ignore_errors=True)
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
    shutil.rmtree(d, ignore_errors=True)
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
        shutil.rmtree(d if old else os.path.join(PROGRAMS, pid), ignore_errors=True)
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
            shutil.rmtree(os.path.join(PROGRAMS, pid), ignore_errors=True)
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
        args = ["uninstall", "--user", "-y", "--noninteractive"] + (["--delete-data"] if data else []) + [m["appid"]]
        rc, out = _flatpak(args, log, 600)
        if rc != 0 and "not installed" not in out:
            raise ProgramError("a Flatpak-eltávolítás nem sikerült: " + (out.strip().splitlines() or ["?"])[-1])
        _flatpak(["uninstall", "--user", "-y", "--noninteractive", "--unused"], log, 600)
    elif t == "win64":
        prefix = m.get("prefix", "")
        shared = [p for p in programs() if p["id"] != pid and p.get("prefix") == prefix]
        if prefix and not shared:
            subprocess.run(["fwr", "stop", pid], capture_output=True, timeout=30)
            shutil.rmtree(prefix, ignore_errors=True)
            _log(log, "a Windows-környezet törölve: " + prefix)
    shutil.rmtree(m["dir"], ignore_errors=True)
    if data and t in ("native", "appimage"):
        for p in glob.glob(os.path.join(HOME, ".config", pid)) + glob.glob(os.path.join(HOME, ".local/share", pid)):
            shutil.rmtree(p, ignore_errors=True)
    sync_desktop()
    _log(log, f"Eltávolítva: {m.get('name', pid)}")


def update(pid, log=None):
    m = manifest(pid)
    if not m:
        raise ProgramError("nincs ilyen program: " + pid)
    if m.get("type") == "flatpak":
        rc, out = _flatpak(["update", "--user", "-y", "--noninteractive", m["appid"]], log, 3600)
        if rc != 0:
            raise ProgramError("a frissítés nem sikerült: " + (out.strip().splitlines() or ["?"])[-1])
        ver = dict(flatpak_apps()).get(m["appid"], m.get("version", ""))
        _flatpak_manifest(m["appid"], ver, m.get("source", "flathub"))
        sync_desktop()
        return "kész" + (f" ({ver})" if ver else "")
    if m.get("type") == "win64":
        return "Windows-program: frissítés az újabb telepítővel (Programkezelő → Telepítés fájlból)"
    return "a program saját frissítőjével, vagy az újabb változat telepítésével"


def sync(log=None):
    """a már telepített Flatpakok (pl. parancssorból) és a régi helyű Windows-programok leírást kapnak"""
    known = {p.get("appid") for p in programs() if p.get("type") == "flatpak"}
    if shutil.which("flatpak"):
        for appid, ver in flatpak_apps():
            if appid not in known:
                m = _flatpak_manifest(appid, ver)
                _log(log, f"Felvéve: {m['name']} ({appid})")
    # régi helyű (fwr) Windows-programok: leírás a meglévő környezetre — újratelepítés nélkül
    for r in recipes():
        pid = r["id"]
        if manifest(pid):
            continue
        prefix = os.path.join(FWR_DATA, pid)
        exe = win_to_unix(prefix, r.get("exe", "")) if r.get("exe") else ""
        if exe and os.path.isfile(exe):
            m = {k: v for k, v in r.items() if k not in ("recipe_file", "match")}
            m.update({"type": "win64", "prefix": prefix, "recipe": os.path.basename(r["recipe_file"]),
                      "source": "átköltöztetve (fwr)", "installed": time.strftime("%Y-%m-%d")})
            write_manifest(m)
            ic = pe_icon(exe, os.path.join(PROGRAMS, pid, "icon"))
            if ic:
                m["icon_tile"], m["icon"] = m.get("icon", ""), ic
                write_manifest(m)
            _log(log, f"Átköltöztetve: {m.get('name', pid)} (a meglévő környezet marad: {prefix})")
    sync_desktop()


def sync_desktop():
    """XDG-bejegyzések (~/.local/share/applications/fusion-<id>.desktop) és alapértelmezett társítások"""
    os.makedirs(APPS_DIR, exist_ok=True)
    keep = set()
    defaults = {}
    for m in programs():
        fn = os.path.join(APPS_DIR, f"fusion-{m['id']}.desktop")
        keep.add(fn)
        mimes = [x for x in m.get("mime", "").replace(",", ";").split(";") if x.strip()]
        for ext in m.get("open", "").split():
            mt = mimetypes.guess_type("x" + ext)[0]
            if mt and mt not in mimes:
                mimes.append(mt)
        lines = ["[Desktop Entry]", "Type=Application", f"Name={m.get('name', m['id'])}",
                 f"Exec=fusion-run {m['id']} %F", f"Comment={m.get('comment', '')}",
                 f"Icon={icon_path(m) or 'application-x-executable'}", "Terminal=false",
                 f"Categories={m.get('categories', '').replace('; ', ';')};" if m.get("categories") else "Categories=",
                 f"MimeType={';'.join(mimes)};" if mimes else "MimeType=", "X-Fusion-Program=" + m["id"]]
        with open(fn, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        for mt in mimes:
            defaults.setdefault(mt, os.path.basename(fn))
    for f in glob.glob(os.path.join(APPS_DIR, "fusion-*.desktop")):
        if f not in keep:
            os.unlink(f)
    # mimeapps.list: csak a Fusion-bejegyzések alapértelmezései (a felhasználó választása elsőbbséget kap)
    user = _assoc_user()
    lines = ["[Default Applications]"]
    for mt, desk in sorted(defaults.items()):
        pid = user.get(mt)
        lines.append(f"{mt}=fusion-{pid}.desktop" if pid and manifest(pid) else f"{mt}={desk}")
    os.makedirs(os.path.join(HOME, ".config"), exist_ok=True)
    with open(os.path.join(HOME, ".config", "mimeapps.list"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


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


def assoc(path):
    """melyik program nyitja meg a fájlt: [(id, név)], az alapértelmezett elöl"""
    low = path.lower()
    ext = "." + low.rsplit(".", 1)[1] if "." in os.path.basename(low) else ""
    mt = mimetypes.guess_type(path)[0] or ""
    user = _assoc_user()
    res = []
    for m in programs():
        exts = m.get("open", "").lower().split()
        mimes = [x.strip() for x in m.get("mime", "").replace(",", ";").split(";") if x.strip()]
        if (ext and ext in exts) or (mt and mt in mimes):
            res.append((m["id"], m.get("name", m["id"])))
    pref = user.get(ext) or user.get(mt)
    res.sort(key=lambda x: x[0] != pref)
    return res


# ---------------------------------------------------------------------------
# indítás
# ---------------------------------------------------------------------------
def command(pid, files=()):
    m = manifest(pid)
    if not m:
        raise ProgramError("nincs ilyen program: " + pid)
    t = m.get("type")
    if t == "win64":
        args = []
        for f in files:
            w = unix_to_win(m, f)
            if not w:
                raise ProgramError(f"a fájl nincs a program látókörében: {f} (megosztott mappák: " +
                                   ", ".join(f"{k[6:].upper()}: {v}" for k, v in m.items() if k.startswith("drive.")) + ")")
            args.append(w)
        return ["fwr", "launch", pid] + args, None
    if t == "flatpak":
        if files:
            return ["flatpak", "run", "--file-forwarding", m["appid"], "@@"] + list(files) + ["@@"], None
        return ["flatpak", "run", m["appid"]], None
    exe = os.path.join(m["dir"], m.get("exec", ""))
    if not os.path.isfile(exe):
        raise ProgramError("a program indítófájlja hiányzik: " + exe)
    return [exe] + list(files), os.path.dirname(exe)


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
            "canUpdate": m.get("type") == "flatpak"}


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
