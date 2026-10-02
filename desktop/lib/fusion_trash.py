"""FusionOS — Lomtár (a freedesktop.org Trash-szabvány szerint, így más programokkal is közös)

    saját mappa és a DATA:      ~/.local/share/Trash/{files,info}
    cserélhető meghajtó (USB):  <a meghajtó gyökere>/.Trash-<uid>/{files,info}
    Google Drive (rclone):      nem ide kerül — a Drive a törölt fájlt a saját lomtárába teszi (drive.google.com)

A lomtárba helyezés átnevezés ugyanazon a köteten belül: azonnali, akármekkora a fájl.
"""
import os
import shutil
import time
import urllib.parse

HOME = os.path.expanduser("~")
HOME_TRASH = os.environ.get("FUSION_TRASH_DIR") or os.path.join(
    os.environ.get("XDG_DATA_HOME") or os.path.join(HOME, ".local", "share"), "Trash")
UID = os.getuid()
NETWORK_FS = ("fuse", "fuse.rclone", "nfs", "nfs4", "cifs", "smb3", "fuse.sshfs")


class TrashError(Exception):
    pass


def mounts():
    out = []
    try:
        with open("/proc/self/mounts", encoding="utf-8") as f:
            for line in f:
                p = line.split()
                if len(p) > 2:
                    out.append((p[1].replace("\\040", " "), p[2], p[0]))
    except OSError:
        pass
    return out


def mount_of(path):
    """(csatolási pont, fájlrendszer-típus) a legközelebbi csatolás szerint"""
    path = os.path.realpath(path)
    best = ("/", "")
    for mp, fs, _dev in mounts():
        if (path == mp or path.startswith(mp.rstrip("/") + "/")) and len(mp) >= len(best[0]):
            best = (mp, fs)
    return best


def is_network(path):
    fs = mount_of(path)[1]
    return fs.startswith("fuse.") and fs != "fuse.portal" or fs in NETWORK_FS


def trash_dir_for(path):
    """melyik lomtárba kerül (None: nincs lomtár — pl. Google Drive)"""
    path = os.path.realpath(path)
    try:
        dev = os.lstat(path).st_dev
    except OSError as e:
        raise TrashError(f"{path}: {e.strerror}")
    os.makedirs(HOME_TRASH, exist_ok=True)
    if os.stat(HOME_TRASH).st_dev == dev:
        return HOME_TRASH
    mp, fs = mount_of(path)
    if fs == "fuse.rclone":
        return None
    top = os.path.join(mp, f".Trash-{UID}")
    return top


def _ensure(td):
    for sub in ("files", "info"):
        os.makedirs(os.path.join(td, sub), mode=0o700, exist_ok=True)


def _unique(td, name):
    base, ext = os.path.splitext(name)
    cand, n = name, 1
    while os.path.lexists(os.path.join(td, "files", cand)) or os.path.lexists(os.path.join(td, "info", cand + ".trashinfo")):
        n += 1
        cand = f"{base}.{n}{ext}"
    return cand


def trash(path):
    """egy fájl / mappa a lomtárba; visszaadja (lomtár, név) — Google Drive-on (None, '')"""
    path = os.path.abspath(path)
    td = trash_dir_for(path)
    if td is None:
        # Google Drive: a törlés a Drive saját lomtárába visz (az rclone alapbeállítása)
        if os.path.isdir(path) and not os.path.islink(path):
            shutil.rmtree(path)
        else:
            os.unlink(path)
        return None, ""
    if os.path.realpath(path).startswith(os.path.realpath(td) + "/") or os.path.realpath(path) == os.path.realpath(td):
        raise TrashError("a lomtárban lévő elem csak véglegesen törölhető")
    try:
        _ensure(td)
    except OSError as e:
        raise TrashError(f"a meghajtón nem hozható létre lomtár ({e.strerror}) — véglegesen törölhető")
    name = _unique(td, os.path.basename(path.rstrip("/")))
    # a Path a lomtár gyökeréhez képest relatív a cserélhető meghajtón, abszolút a saját lomtárban
    rel = path if td == HOME_TRASH else os.path.relpath(path, os.path.dirname(td))
    info = os.path.join(td, "info", name + ".trashinfo")
    fd = os.open(info, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write("[Trash Info]\nPath=%s\nDeletionDate=%s\n" % (urllib.parse.quote(rel), time.strftime("%Y-%m-%dT%H:%M:%S")))
    try:
        os.rename(path, os.path.join(td, "files", name))
    except OSError as e:
        os.unlink(info)
        raise TrashError(f"{os.path.basename(path)}: {e.strerror}")
    return td, name


def trash_dirs():
    """minden elérhető lomtár: a saját, és a csatolt cserélhető meghajtóké"""
    out = [HOME_TRASH]
    for mp, fs, _dev in mounts():
        t = os.path.join(mp, f".Trash-{UID}")
        if mp.startswith("/run/media/") and os.path.isdir(os.path.join(t, "files")):
            out.append(t)
    return out


def is_trash_files_dir(path):
    path = os.path.realpath(path)
    return any(path == os.path.realpath(os.path.join(t, "files")) for t in trash_dirs())


def _read_info(td, name):
    d = {}
    try:
        with open(os.path.join(td, "info", name + ".trashinfo"), encoding="utf-8") as f:
            for line in f:
                if "=" in line:
                    k, v = line.split("=", 1)
                    d[k.strip()] = v.strip()
    except OSError:
        pass
    p = urllib.parse.unquote(d.get("Path", ""))
    if p and not p.startswith("/"):
        p = os.path.join(os.path.dirname(td), p)
    return p, d.get("DeletionDate", "").replace("T", " ")


def entries(td=None):
    """[{name, trash, orig, date, isDir}] — a legutóbb törölt elöl"""
    out = []
    for t in ([td] if td else trash_dirs()):
        fdir = os.path.join(t, "files")
        try:
            names = os.listdir(fdir)
        except OSError:
            continue
        for n in names:
            orig, date = _read_info(t, n)
            out.append({"name": n, "trash": t, "orig": orig, "date": date,
                        "isDir": os.path.isdir(os.path.join(fdir, n)) and not os.path.islink(os.path.join(fdir, n))})
    out.sort(key=lambda e: e["date"], reverse=True)
    return out


def restore(td, name):
    """vissza az eredeti helyére (ha ott már van ilyen nevű: „(visszaállítva)” utótaggal); visszaadja az utat"""
    orig, _date = _read_info(td, name)
    if not orig:
        raise TrashError(f"{name}: nincs meg az eredeti hely")
    os.makedirs(os.path.dirname(orig), exist_ok=True)
    dst = orig
    if os.path.lexists(dst):
        base, ext = os.path.splitext(orig)
        dst, n = f"{base} (visszaállítva){ext}", 2
        while os.path.lexists(dst):
            dst = f"{base} (visszaállítva {n}){ext}"
            n += 1
    src = os.path.join(td, "files", name)
    try:
        os.rename(src, dst)
    except OSError as e:
        if e.errno != 18:      # EXDEV: más kötet — másolás
            raise TrashError(f"{name}: {e.strerror}")
        shutil.move(src, dst)
    try:
        os.unlink(os.path.join(td, "info", name + ".trashinfo"))
    except OSError:
        pass
    return dst


def purge(td, name):
    """végleges törlés a lomtárból"""
    p = os.path.join(td, "files", name)
    if os.path.isdir(p) and not os.path.islink(p):
        shutil.rmtree(p, ignore_errors=True)
    elif os.path.lexists(p):
        os.unlink(p)
    try:
        os.unlink(os.path.join(td, "info", name + ".trashinfo"))
    except OSError:
        pass


def empty():
    n = 0
    for e in entries():
        purge(e["trash"], e["name"])
        n += 1
    return n


def purge_older(days=30):
    """a régi elemek automatikus ürítése (bejelentkezéskor)"""
    limit = time.time() - days * 86400
    n = 0
    for e in entries():
        try:
            t = time.mktime(time.strptime(e["date"], "%Y-%m-%d %H:%M:%S"))
        except ValueError:
            continue
        if t < limit:
            purge(e["trash"], e["name"])
            n += 1
    return n


def size():
    tot, cnt = 0, 0
    for t in trash_dirs():
        for root, _d, files in os.walk(os.path.join(t, "files")):
            for f in files:
                try:
                    tot += os.lstat(os.path.join(root, f)).st_blocks * 512
                except OSError:
                    pass
        try:
            cnt += len(os.listdir(os.path.join(t, "files")))
        except OSError:
            pass
    return tot, cnt
