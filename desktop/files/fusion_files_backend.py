"""FusionOS — Fájlkezelő: háttérrész (könyvtárlista, fájlműveletek, keresés, archívumok, kötetek)

A felület (QML) csak megjelenít; minden fájlrendszer-művelet itt történik, a hosszúak
(másolás, mozgatás, törlés, tömörítés, kicsomagolás, keresés, mappaméret) külön szálon,
megszakíthatóan, folyamatjelzéssel. Ugyanez a kód fut az önteszten is (--selftest).
"""
import fnmatch
import json
import os
import shutil
import stat
import tarfile
import threading
import time
import zipfile

from PyQt6.QtCore import (QAbstractListModel, QByteArray, QFileSystemWatcher, QMimeData, QModelIndex,
                          QObject, Qt, QTimer, QUrl, pyqtProperty, pyqtSignal, pyqtSlot)
from PyQt6.QtGui import QGuiApplication

import fusion_ui as ui
import fusion_trash as trashlib
import fusion_apps  # noqa: F401  (a Programkezelő moduljának útvonala)
try:
    import fusion_programs as fp
except ImportError:
    fp = None

TEXT_EXT = {"txt", "md", "log", "cfg", "conf", "ini", "json", "xml", "yaml", "yml", "py", "sh", "csv", "toml",
            "service", "rules", "desktop", "html", "htm", "css", "js", "c", "h", "cpp", "hpp", "fwr", "list",
            "gcode", "gc", "g", "nc", "ngc", "svg", "lbrn", "lbrn2", "tsv", "sql", "bat", "cmd", "ps1", "reg"}
CODE_EXT = {"gcode", "gc", "g", "nc", "ngc", "tap"}
IMAGE_EXT = {"png", "jpg", "jpeg", "gif", "bmp", "webp", "svg", "ico"}
ARCHIVE_EXT = ("zip", "tar", "tar.gz", "tgz", "tar.xz", "txz", "tar.bz2", "tbz2")
EXE_EXT = {"exe", "msi", "appimage", "flatpakref", "flatpak"}   # telepítők → Programkezelő
CHUNK = 1024 * 1024


def ext_of(name):
    low = name.lower()
    for a in ("tar.gz", "tar.xz", "tar.bz2"):
        if low.endswith("." + a):
            return a
    i = low.rfind(".")
    return low[i + 1:] if i > 0 else ""


def is_archive(path):
    return ext_of(os.path.basename(path)) in ARCHIVE_EXT


def icon_for(name, is_dir):
    if is_dir:
        return "folder"
    e = ext_of(name)
    if e in CODE_EXT:
        return "file-code"
    if e in IMAGE_EXT:
        return "file-image"
    if e in ARCHIVE_EXT:
        return "file-archive"
    if e in EXE_EXT:
        return "file-exe"
    if e in TEXT_EXT:
        return "file-text"
    return "file"


def kind_of(path):
    """megnyitáskor: dir | image | archive | exe | text | binary"""
    if os.path.isdir(path):
        return "dir"
    e = ext_of(os.path.basename(path))
    if e in IMAGE_EXT and e != "svg":
        return "image"
    if e == "svg":
        return "image"
    if e in ARCHIVE_EXT:
        return "archive"
    if e in EXE_EXT:
        return "exe"
    try:
        with open(path, "rb") as f:
            head = f.read(4096)
    except OSError:
        return "binary"
    if head.startswith(b"\x7fELF"):
        return "elf"
    if b"\x00" in head:
        return "binary"
    return "text"


def fmt_date(ts):
    return time.strftime("%Y.%m.%d %H:%M", time.localtime(ts))


def perm_text(mode):
    return stat.filemode(mode)[1:]


# ---------------------------------------------------------------------------
# könyvtárlista (egy panel)
# ---------------------------------------------------------------------------
LOG = os.path.join(os.path.expanduser("~"), ".local", "share", "fusion", "files.log")


def slow(what, t0, limit=0.5):
    """a felületet megakasztó lassú műveletek naplója (hibakereséshez): ~/.local/share/fusion/files.log"""
    dt = time.monotonic() - t0
    if dt >= limit:
        try:
            os.makedirs(os.path.dirname(LOG), exist_ok=True)
            with open(LOG, "a", encoding="utf-8") as f:
                f.write(f"{time.strftime('%F %T')} lassú ({dt:.1f} mp): {what}\n")
        except OSError:
            pass


_FREE = {}
_FREE_BUSY = set()


def _statvfs_text(path):
    try:
        s = os.statvfs(path)
        return f"{ui.human_size(s.f_bavail * s.f_frsize)} szabad / {ui.human_size(s.f_blocks * s.f_frsize)}"
    except OSError:
        return ""


class DirModel(QAbstractListModel):
    ROLES = ["name", "ext", "isDir", "isLink", "isParent", "sizeText", "dateText", "attr", "marked", "hidden", "icon", "size"]
    pathChanged = pyqtSignal()
    statusChanged = pyqtSignal()
    errorChanged = pyqtSignal()
    sortChanged = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._path = ""
        self._items = []
        self._sort = "name"
        self._desc = False
        self._hidden = False
        self._error = ""
        self._watch = QFileSystemWatcher(self)
        self._watch.directoryChanged.connect(lambda _p: self._debounce.start())
        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(300)
        self._debounce.timeout.connect(lambda: self.reloadKeep())
        self.current = ""        # a felület jelzi, melyik sor az aktuális (frissítéskor megtartjuk)
        self.freeReady.connect(self.statusChanged)
        self._scanned.connect(self._apply_scan)
        self._scanning = False

    # --- Qt-modell ---
    def roleNames(self):
        return {Qt.ItemDataRole.UserRole + i: QByteArray(r.encode()) for i, r in enumerate(self.ROLES)}

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self._items)

    def data(self, index, role):
        if not index.isValid() or index.row() >= len(self._items):
            return None
        r = role - Qt.ItemDataRole.UserRole
        if 0 <= r < len(self.ROLES):
            return self._items[index.row()].get(self.ROLES[r])
        return None

    # --- tulajdonságok ---
    @pyqtProperty(str, notify=pathChanged)
    def path(self):
        return self._path

    @pyqtProperty(str, notify=errorChanged)
    def error(self):
        return self._error

    @pyqtProperty(str, notify=sortChanged)
    def sortKey(self):
        return self._sort

    @pyqtProperty(bool, notify=sortChanged)
    def sortDesc(self):
        return self._desc

    @pyqtProperty(bool, notify=sortChanged)
    def showHidden(self):
        return self._hidden

    @showHidden.setter
    def showHidden(self, v):
        if v != self._hidden:
            self._hidden = v
            self.sortChanged.emit()
            self.reloadKeep()

    @pyqtProperty(str, notify=statusChanged)
    def status(self):
        files = [i for i in self._items if not i["isParent"]]
        marked = [i for i in files if i["marked"]]
        tot = sum(i["size"] for i in files if not i["isDir"])
        msz = sum(i["size"] for i in marked if not i["isDir"] or i["size"] > 0)
        return f"Kijelölve: {len(marked)} / {len(files)}  ·  {ui.human_size(msz)} / {ui.human_size(tot)}"

    @pyqtProperty(str, notify=statusChanged)
    def free(self):
        """szabad hely — hálózati / felhő-köteten (pl. Google Drive) háttérben, gyorsítótárból:
        ott a lekérdezés a szolgáltatóhoz fordul, és nem akaszthatja meg a felületet"""
        path = self._path
        hit = _FREE.get(path)
        net = trashlib.is_network(path) if path else False
        ttl = 60 if net else 3
        if hit and time.monotonic() - hit[0] < ttl:
            return hit[1]
        if not net:
            t0 = time.monotonic()
            text = _statvfs_text(path)
            slow("szabad hely: " + path, t0)
            _FREE[path] = (time.monotonic(), text)
            return text
        if path not in _FREE_BUSY:
            _FREE_BUSY.add(path)

            def work():
                text = _statvfs_text(path)
                _FREE[path] = (time.monotonic(), text)
                _FREE_BUSY.discard(path)
                self.freeReady.emit()
            threading.Thread(target=work, daemon=True).start()
        return hit[1] if hit else "…"

    freeReady = pyqtSignal()

    @pyqtProperty(bool, notify=pathChanged)
    def isTrash(self):
        return trashlib.is_trash_files_dir(self._path) if self._path else False

    @pyqtProperty(int, notify=statusChanged)
    def markedCount(self):
        return sum(1 for i in self._items if i["marked"])

    @pyqtProperty(int, notify=statusChanged)
    def count(self):
        return len(self._items)

    # --- betöltés ---
    def _scan(self, path):
        items = []
        parent = os.path.dirname(path.rstrip("/")) or "/"
        if path != "/":
            items.append({"name": "..", "ext": "", "isDir": True, "isLink": False, "isParent": True, "size": 0,
                          "sizeText": "", "dateText": "", "attr": "", "marked": False, "hidden": False,
                          "icon": "folder-up", "full": parent})
        dirs, files = [], []
        with os.scandir(path) as it:
            for e in it:
                if not self._hidden and e.name.startswith("."):
                    continue
                try:
                    st = e.stat(follow_symlinks=True)
                    isdir = stat.S_ISDIR(st.st_mode)
                except OSError:          # törött hivatkozás
                    st = e.stat(follow_symlinks=False)
                    isdir = False
                size = 0 if isdir else st.st_size
                d = {"name": e.name, "ext": "" if isdir else ext_of(e.name), "isDir": isdir, "isLink": e.is_symlink(),
                     "isParent": False, "size": size, "sizeText": "<MAPPA>" if isdir else ui.human_size(size),
                     "dateText": fmt_date(st.st_mtime), "mtime": st.st_mtime, "attr": perm_text(st.st_mode),
                     "marked": False, "hidden": e.name.startswith("."), "icon": icon_for(e.name, isdir),
                     "full": os.path.join(path, e.name)}
                (dirs if isdir else files).append(d)
        key = {"name": lambda d: d["name"].lower(), "ext": lambda d: (d["ext"], d["name"].lower()),
               "size": lambda d: (d["size"], d["name"].lower()), "date": lambda d: (d["mtime"], d["name"].lower())}[self._sort]
        # a mappák mindig elöl (név szerint, kivéve dátum/méret rendezést)
        dirs.sort(key=key if self._sort in ("date", "size") else (lambda d: d["name"].lower()), reverse=self._desc)
        files.sort(key=key, reverse=self._desc)
        return items + dirs + files

    @pyqtSlot(str, str, result=int)
    def load(self, path, select=""):
        """könyvtár betöltése; visszaadja a kijelölendő sor indexét"""
        path = os.path.abspath(os.path.expanduser(path or "/"))
        prev = self._path
        t0 = time.monotonic()
        try:
            items = self._scan(path)
            slow("megnyitás: " + path, t0)
        except OSError as e:
            self._error = f"{path}: {e.strerror or e}"
            self.errorChanged.emit()
            return -1
        self.beginResetModel()
        self._items = items
        self.endResetModel()
        if self._watch.directories():
            self._watch.removePaths(self._watch.directories())
        self._watch.addPath(path)
        self._error = ""
        self.errorChanged.emit()
        if path != prev:
            self._path = path
            self.pathChanged.emit()
        self.statusChanged.emit()
        if not select and prev and prev != path and (os.path.dirname(prev.rstrip("/")) or "/") == path:
            select = os.path.basename(prev.rstrip("/"))   # visszalépéskor a korábbi mappán áll
        return max(0, self.indexOf(select)) if select else 0

    _scanned = pyqtSignal(str, "QVariant")

    @pyqtSlot(result=int)
    def reloadKeep(self):
        """frissítés: az aktuális sor és a jelölések megmaradnak
        (hálózati / felhő-köteten a listázás háttérben — a felület nem akad meg)"""
        if self._path and trashlib.is_network(self._path):
            if not self._scanning:
                self._scanning = True
                path = self._path

                def work():
                    try:
                        items = self._scan(path)
                    except OSError:
                        items = None
                    self._scanned.emit(path, items)
                threading.Thread(target=work, daemon=True).start()
            return max(0, self.indexOf(self.current))
        return self._reload_sync()

    def _apply_scan(self, path, items):
        self._scanning = False
        if path != self._path:
            return
        if items is None:
            self._reload_sync()
            return
        self._set_items(items)

    def _set_items(self, items):
        marked = {i["name"] for i in self._items if i["marked"]}
        cur = self.current
        for i in items:
            i["marked"] = i["name"] in marked
        self.beginResetModel()
        self._items = items
        self.endResetModel()
        self.statusChanged.emit()
        self.reloaded.emit(max(0, self.indexOf(cur)))
        return max(0, self.indexOf(cur))

    def _reload_sync(self):
        if not self._path:          # még nincs betöltve (pl. az önteszt üres panelje)
            return 0
        marked = {i["name"] for i in self._items if i["marked"]}
        cur = self.current
        t0 = time.monotonic()
        try:
            items = self._scan(self._path)
            slow("frissítés: " + self._path, t0)
        except OSError:
            # a mappa eltűnt (pl. kihúzott USB): a legközelebbi létező szülő
            p = self._path
            while p and p != "/" and not os.path.isdir(p):
                p = os.path.dirname(p)
            return self.load(p or "/")
        for i in items:
            i["marked"] = i["name"] in marked
        self.beginResetModel()
        self._items = items
        self.endResetModel()
        self.statusChanged.emit()
        self.reloaded.emit(max(0, self.indexOf(cur)))
        return max(0, self.indexOf(cur))

    reloaded = pyqtSignal(int)

    @pyqtSlot(str)
    def setSort(self, key):
        if key == self._sort:
            self._desc = not self._desc
        else:
            self._sort, self._desc = key, False
        self.sortChanged.emit()
        self.reloadKeep()

    # --- lekérdezések ---
    @pyqtSlot(str, result=int)
    def indexOf(self, name):
        for n, i in enumerate(self._items):
            if i["name"] == name:
                return n
        return -1

    @pyqtSlot(int, result="QVariant")
    def item(self, row):
        if 0 <= row < len(self._items):
            i = dict(self._items[row])
            i.pop("mtime", None)
            return i
        return {}

    @pyqtSlot(int, result=str)
    def fullPath(self, row):
        return self._items[row]["full"] if 0 <= row < len(self._items) else ""

    @pyqtSlot(int, result="QStringList")
    def selection(self, row):
        """a művelet tárgya: a jelölt elemek, ha vannak; különben az aktuális sor (nem a ..)"""
        m = [i["full"] for i in self._items if i["marked"]]
        if m:
            return m
        if 0 <= row < len(self._items) and not self._items[row]["isParent"]:
            return [self._items[row]["full"]]
        return []

    @pyqtSlot(str, int, result=int)
    def findPrefix(self, prefix, start):
        """gépelésre ugrás: a következő sor, amelynek neve így kezdődik"""
        p = prefix.lower()
        n = len(self._items)
        for k in range(n):
            i = (start + k) % n
            if self._items[i]["name"].lower().startswith(p) and not self._items[i]["isParent"]:
                return i
        return -1

    # --- jelölés ---
    def _changed(self, rows=None):
        if rows is None:
            self.dataChanged.emit(self.index(0), self.index(max(0, len(self._items) - 1)))
        else:
            for r in rows:
                self.dataChanged.emit(self.index(r), self.index(r))
        self.statusChanged.emit()

    @pyqtSlot(int)
    def toggleMark(self, row):
        if 0 <= row < len(self._items) and not self._items[row]["isParent"]:
            self._items[row]["marked"] = not self._items[row]["marked"]
            self._changed([row])

    @pyqtSlot(int, int, bool)
    def markRange(self, a, b, on):
        lo, hi = min(a, b), max(a, b)
        for r in range(max(0, lo), min(len(self._items), hi + 1)):
            if not self._items[r]["isParent"]:
                self._items[r]["marked"] = on
        self._changed()

    @pyqtSlot(bool)
    def markAll(self, on):
        for i in self._items:
            i["marked"] = on and not i["isParent"]
        self._changed()

    @pyqtSlot()
    def invertMarks(self):
        for i in self._items:
            if not i["isParent"]:
                i["marked"] = not i["marked"]
        self._changed()

    @pyqtSlot(str, bool, result=int)
    def markPattern(self, pattern, on):
        pats = [p.strip() for p in pattern.replace(";", " ").split() if p.strip()] or ["*"]
        n = 0
        for i in self._items:
            if not i["isParent"] and any(fnmatch.fnmatch(i["name"].lower(), p.lower()) for p in pats):
                i["marked"] = on
                n += 1
        self._changed()
        return n

    def mark_names(self, names):
        for i in self._items:
            i["marked"] = i["name"] in names
        self._changed()

    def set_dir_size(self, name, size):
        for r, i in enumerate(self._items):
            if i["name"] == name and i["isDir"]:
                i["size"] = size
                i["sizeText"] = ui.human_size(size)
                self._changed([r])
                return

    def entries(self):
        return [i for i in self._items if not i["isParent"]]


# ---------------------------------------------------------------------------
# fájlműveletek (külön szálon)
# ---------------------------------------------------------------------------
class Cancelled(Exception):
    pass


class Job:
    """egy művelet állapota; a szál írja, a felület időzítővel olvassa"""

    def __init__(self, kind, title):
        self.kind, self.title = kind, title
        self.total = 0
        self.done = 0
        self.files_total = 0
        self.files_done = 0
        self.current = ""
        self.cancel = False
        self.errors = []
        self.finished = False
        self.result = ""


def _walk_size(paths, job=None):
    total, count = 0, 0
    for p in paths:
        if job and job.cancel:
            raise Cancelled()
        if os.path.isdir(p) and not os.path.islink(p):
            for root, dirs, files in os.walk(p):
                for f in files:
                    try:
                        total += os.lstat(os.path.join(root, f)).st_size
                    except OSError:
                        pass
                    count += 1
        else:
            try:
                total += os.lstat(p).st_size
            except OSError:
                pass
            count += 1
    return total, count


def conflicts(srcs, dstdir):
    """a célban már létező (felső szintű) nevek"""
    return [os.path.basename(s.rstrip("/")) for s in srcs if os.path.lexists(os.path.join(dstdir, os.path.basename(s.rstrip("/"))))]


def check_target(srcs, dstdir):
    """hibaüzenet, ha a művelet értelmetlen (önmagába / saját mappájába másolás)"""
    real_dst = os.path.realpath(dstdir)
    for s in srcs:
        rs = os.path.realpath(s)
        if os.path.isdir(s) and (real_dst == rs or real_dst.startswith(rs.rstrip("/") + "/")):
            return f"„{os.path.basename(s)}” nem másolható / mozgatható önmagába"
        if os.path.dirname(rs) == real_dst:
            return "a forrás és a cél ugyanaz a mappa"
    return ""


class FileOps:
    """a műveletek törzse — a szál és az önteszt is ezt hívja"""

    def __init__(self, job, overwrite="ask"):
        self.job = job
        self.overwrite = overwrite     # "all" | "skip"

    def _check(self):
        if self.job.cancel:
            raise Cancelled()

    def _copy_file(self, src, dst):
        self.job.current = os.path.basename(src)
        if os.path.lexists(dst):
            if self.overwrite == "skip":
                self.job.done += os.lstat(src).st_size
                self.job.files_done += 1
                return
            if os.path.isdir(dst) and not os.path.islink(dst):
                shutil.rmtree(dst)
            else:
                os.unlink(dst)
        if os.path.islink(src):
            os.symlink(os.readlink(src), dst)
            self.job.files_done += 1
            return
        tmp = dst + ".fusion-part"
        try:
            with open(src, "rb") as fi, open(tmp, "wb") as fo:
                while True:
                    self._check()
                    b = fi.read(CHUNK)
                    if not b:
                        break
                    fo.write(b)
                    self.job.done += len(b)
            try:
                shutil.copystat(src, tmp)
            except OSError:
                pass          # FAT/NTFS: a jogok nem állíthatók — nem hiba
            os.replace(tmp, dst)
        except BaseException:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise
        self.job.files_done += 1

    def _copy_tree(self, src, dst):
        self._check()
        if os.path.isdir(src) and not os.path.islink(src):
            if os.path.lexists(dst) and not os.path.isdir(dst):
                if self.overwrite == "skip":
                    return
                os.unlink(dst)
            os.makedirs(dst, exist_ok=True)
            for name in sorted(os.listdir(src)):
                self._copy_tree(os.path.join(src, name), os.path.join(dst, name))
            try:
                shutil.copystat(src, dst)
            except OSError:
                pass
        else:
            try:
                self._copy_file(src, dst)
            except Cancelled:
                raise
            except OSError as e:
                self.job.errors.append(f"{src}: {e.strerror or e}")

    def copy(self, srcs, dstdir):
        self.job.total, self.job.files_total = _walk_size(srcs, self.job)
        for s in srcs:
            self._copy_tree(s, os.path.join(dstdir, os.path.basename(s.rstrip("/"))))

    def move(self, srcs, dstdir):
        self.job.total, self.job.files_total = _walk_size(srcs, self.job)
        for s in srcs:
            self._check()
            dst = os.path.join(dstdir, os.path.basename(s.rstrip("/")))
            self.job.current = os.path.basename(s)
            if os.path.lexists(dst):
                if self.overwrite == "skip":
                    continue
                if os.path.isdir(dst) and os.path.isdir(s) and not os.path.islink(dst):
                    # mappák összefésülése: másolás, majd a forrás törlése
                    self._copy_tree(s, dst)
                    if not self.job.errors:
                        shutil.rmtree(s)
                    continue
                if os.path.isdir(dst) and not os.path.islink(dst):
                    shutil.rmtree(dst)
                else:
                    os.unlink(dst)
            try:
                os.rename(s, dst)                  # ugyanazon a köteten: azonnal
                sz, n = _walk_size([dst])
                self.job.done += sz
                self.job.files_done += n
            except OSError as e:
                if e.errno != 18:                  # EXDEV: más kötet → másolás + törlés
                    self.job.errors.append(f"{s}: {e.strerror or e}")
                    continue
                before = len(self.job.errors)
                self._copy_tree(s, dst)
                if len(self.job.errors) == before:
                    if os.path.isdir(s) and not os.path.islink(s):
                        shutil.rmtree(s)
                    else:
                        os.unlink(s)

    def delete(self, srcs):
        _t, self.job.files_total = _walk_size(srcs, self.job)
        for s in srcs:
            self._check()
            self.job.current = os.path.basename(s)
            try:
                if os.path.isdir(s) and not os.path.islink(s):
                    for root, dirs, files in os.walk(s, topdown=False):
                        for f in files:
                            self._check()
                            os.unlink(os.path.join(root, f))
                            self.job.files_done += 1
                        for d in dirs:
                            p = os.path.join(root, d)
                            os.unlink(p) if os.path.islink(p) else os.rmdir(p)
                    os.rmdir(s)
                else:
                    os.unlink(s)
                    self.job.files_done += 1
            except OSError as e:
                self.job.errors.append(f"{s}: {e.strerror or e}")

    def trash(self, srcs):
        """lomtárba helyezés (azonos köteten átnevezés: azonnali); visszaadja a visszavonáshoz szükséges listát"""
        self.job.files_total = len(srcs)
        done = []
        for s in srcs:
            self._check()
            self.job.current = os.path.basename(s)
            try:
                td, name = trashlib.trash(s)
                if td:
                    done.append((td, name))
            except (trashlib.TrashError, OSError) as e:
                self.job.errors.append(str(e) if isinstance(e, trashlib.TrashError) else f"{s}: {e.strerror or e}")
            self.job.files_done += 1
        return done

    def pack(self, srcs, zippath):
        """ZIP-archívum a kijelölt elemekből (a relatív utak a forrásmappától)"""
        self.job.total, self.job.files_total = _walk_size(srcs, self.job)
        base = os.path.dirname(srcs[0].rstrip("/"))
        tmp = zippath + ".fusion-part"
        try:
            with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
                for s in srcs:
                    paths = [s]
                    if os.path.isdir(s) and not os.path.islink(s):
                        paths = []
                        for root, dirs, files in os.walk(s):
                            paths.append(root)
                            paths += [os.path.join(root, f) for f in files]
                    for p in paths:
                        self._check()
                        arc = os.path.relpath(p, base)
                        self.job.current = arc
                        if os.path.isdir(p):
                            z.write(p, arc + "/")
                        else:
                            z.write(p, arc)
                            self.job.done += os.lstat(p).st_size
                            self.job.files_done += 1
            os.replace(tmp, zippath)
        except BaseException:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise

    def extract(self, archives, dstdir):
        """ZIP és TAR (gz, xz, bz2) kicsomagolása; a célon kívülre mutató útvonal nem kerülhet ki"""
        real = os.path.realpath(dstdir)
        for a in archives:
            if zipfile.is_zipfile(a):
                with zipfile.ZipFile(a) as z:
                    infos = z.infolist()
                    self.job.total += sum(i.file_size for i in infos)
                    self.job.files_total += len(infos)
                    for i in infos:
                        self._check()
                        target = os.path.realpath(os.path.join(dstdir, i.filename))
                        if not (target == real or target.startswith(real + "/")):
                            self.job.errors.append(f"kihagyva (a célon kívülre mutat): {i.filename}")
                            continue
                        if os.path.exists(target) and not i.is_dir() and self.overwrite == "skip":
                            continue
                        self.job.current = i.filename
                        z.extract(i, dstdir)
                        mode = (i.external_attr >> 16) & 0o777
                        if mode and not i.is_dir():
                            try:
                                os.chmod(target, mode)
                            except OSError:
                                pass
                        self.job.done += i.file_size
                        self.job.files_done += 1
            elif tarfile.is_tarfile(a):
                with tarfile.open(a) as t:
                    members = t.getmembers()
                    self.job.total += sum(m.size for m in members)
                    self.job.files_total += len(members)
                    for m in members:
                        self._check()
                        self.job.current = m.name
                        if os.path.exists(os.path.join(dstdir, m.name)) and m.isfile() and self.overwrite == "skip":
                            continue
                        try:
                            t.extract(m, dstdir, filter="data")
                        except (tarfile.FilterError, OSError) as e:
                            self.job.errors.append(f"{m.name}: {e}")
                        self.job.done += m.size
                        self.job.files_done += 1
            else:
                self.job.errors.append(f"nem ismert archívum: {os.path.basename(a)}")


def archive_list(path, limit=5000):
    """archívum tartalma szövegként (megtekintéshez)"""
    lines = []
    try:
        if zipfile.is_zipfile(path):
            with zipfile.ZipFile(path) as z:
                for i in z.infolist()[:limit]:
                    d = "%04d.%02d.%02d %02d:%02d" % i.date_time[:5]
                    lines.append(f"{ui.human_size(i.file_size):>10}  {d}  {i.filename}")
                n = len(z.infolist())
        elif tarfile.is_tarfile(path):
            with tarfile.open(path) as t:
                ms = t.getmembers()
                for m in ms[:limit]:
                    lines.append(f"{ui.human_size(m.size):>10}  {fmt_date(m.mtime)}  {m.name}{'/' if m.isdir() else ''}")
                n = len(ms)
        else:
            return "nem ismert archívum"
    except (OSError, zipfile.BadZipFile, tarfile.TarError) as e:
        return f"az archívum nem olvasható: {e}"
    head = f"{os.path.basename(path)} — {n} elem\n\n"
    return head + "\n".join(lines) + ("\n…" if n > limit else "")


def pe_info(path):
    """Windows-program: PE32 / PE32+ (64 bites) felismerése"""
    try:
        with open(path, "rb") as f:
            d = f.read(4096)
        if d[:2] != b"MZ":
            return "nem Windows-program"
        off = int.from_bytes(d[0x3C:0x40], "little")
        if d[off:off + 4] != b"PE\0\0":
            return "DOS-program"
        magic = int.from_bytes(d[off + 24:off + 26], "little")
        return {0x10B: "Windows-program (PE32, 32 bites)", 0x20B: "Windows-program (PE32+, 64 bites)"}.get(magic, "Windows-program")
    except OSError as e:
        return str(e)


def search(root, pattern, text, job, results, limit=5000):
    """fájlkeresés: név minta (* ?; minta nélkül részlet), opcionálisan szöveg a tartalomban"""
    pats = [p.strip().lower() for p in pattern.replace(";", " ").split() if p.strip()] or ["*"]
    pats = [p if any(c in p for c in "*?[") else f"*{p}*" for p in pats]
    needle = text.encode("utf-8").lower() if text else b""
    for dirpath, dirs, files in os.walk(root):
        if job.cancel or len(results) >= limit:
            break
        dirs[:] = [d for d in dirs if not os.path.ismount(os.path.join(dirpath, d)) or dirpath == root]
        job.current = dirpath
        for n in dirs + files:
            if not any(fnmatch.fnmatch(n.lower(), p) for p in pats):
                continue
            full = os.path.join(dirpath, n)
            if needle:
                if n in dirs:
                    continue
                try:
                    with open(full, "rb") as f:
                        if needle not in f.read(20 * CHUNK).lower():
                            continue
                except OSError:
                    continue
            results.append(full)
            job.files_done = len(results)


def compare_dirs(left_entries, right_entries):
    """könyvtár-összehasonlítás: melyik fájl hiányzik a másik oldalon, vagy újabb / más méretű"""
    L = {i["name"]: i for i in left_entries if not i["isDir"]}
    R = {i["name"]: i for i in right_entries if not i["isDir"]}
    lm, rm = set(), set()
    for n, i in L.items():
        o = R.get(n)
        if o is None or i["mtime"] > o["mtime"] + 2 or (abs(i["mtime"] - o["mtime"]) <= 2 and i["size"] != o["size"]):
            lm.add(n)
    for n, i in R.items():
        o = L.get(n)
        if o is None or i["mtime"] > o["mtime"] + 2 or (abs(i["mtime"] - o["mtime"]) <= 2 and i["size"] != o["size"]):
            rm.add(n)
    return lm, rm


def download_dir():
    """a Letöltések mappa (XDG_DOWNLOAD_DIR a ~/.config/user-dirs.dirs-ben — a munkamenet indulásakor jön létre)"""
    home = os.path.expanduser("~")
    try:
        with open(os.path.join(os.environ.get("XDG_CONFIG_HOME") or os.path.join(home, ".config"), "user-dirs.dirs"), encoding="utf-8") as f:
            for line in f:
                if line.startswith("XDG_DOWNLOAD_DIR="):
                    v = line.split("=", 1)[1].strip().strip('"')
                    return v.replace("$HOME", home, 1) if v.startswith("$HOME") else v
    except OSError:
        pass
    return ""


def volumes():
    """„Ez a gép”: helyek és kötetek (a csatolatlanok is — kattintásra csatolhatók)"""
    home = os.path.expanduser("~")
    out = [{"name": "Saját mappa", "path": home, "icon": "home", "dev": "", "info": home, "mounted": True, "media": False}]
    dl = download_dir()
    if dl and os.path.isdir(dl) and os.path.realpath(dl) != os.path.realpath(home):
        out.append({"name": os.path.basename(dl.rstrip("/")) or "Letöltések", "path": dl, "icon": "download", "dev": "",
                    "info": dl, "mounted": True, "media": False})
    if os.path.isdir("/data"):
        out.append({"name": "Adatok (FusionOS DATA)", "path": "/data", "icon": "drive", "dev": "", "info": "/data", "mounted": True, "media": False})
    out.append({"name": "Rendszer", "path": "/", "icon": "drive", "dev": "", "info": "/ (csak olvasható alap)", "mounted": True, "media": False})
    rc, js = ui.run(["lsblk", "-J", "-b", "-o", "NAME,PATH,LABEL,FSTYPE,SIZE,MOUNTPOINTS,RM,TRAN,PARTLABEL,TYPE,PKNAME"], timeout=5)
    try:
        devs = json.loads(js).get("blockdevices", []) if rc == 0 else []
    except ValueError:
        devs = []
    boot = ""
    try:
        boot = open("/run/fusion/boot-disk").read().strip()
    except OSError:
        pass

    def walk(nodes, disk_rm=False, disk_tran="", disk=""):
        for n in nodes:
            rm = bool(n.get("rm")) or disk_rm
            tran = n.get("tran") or disk_tran
            dk = disk or n.get("name", "")
            if n.get("children"):
                walk(n["children"], rm, tran, dk)
            if not n.get("fstype") or n.get("fstype") in ("swap", "crypto_LUKS", "LVM2_member", "linux_raid_member", "squashfs", "erofs"):
                continue
            if dk == boot or (n.get("partlabel") or "").startswith("FUSION_") or n.get("type") == "loop":
                continue
            mps = [m for m in (n.get("mountpoints") or []) if m]
            usb = rm or tran == "usb" or dk.startswith("mmcblk")
            label = n.get("label") or n.get("partlabel") or n.get("name")
            out.append({"name": label, "path": mps[0] if mps else "", "icon": "drive-usb" if usb else "drive",
                        "dev": n.get("path", ""), "mounted": bool(mps), "media": usb or bool(mps and mps[0].startswith("/run/media/")),
                        "info": f"{n.get('path', '')} · {n.get('fstype', '')} · {ui.human_size(int(n.get('size') or 0))}"})
    walk(devs)
    # Lomtár
    try:
        os.makedirs(os.path.join(trashlib.HOME_TRASH, "files"), exist_ok=True)
        tot, cnt = trashlib.size()
        out.insert(2, {"name": "Lomtár", "path": os.path.join(trashlib.HOME_TRASH, "files"), "icon": "trash", "dev": "",
                       "mounted": True, "media": False, "info": f"{cnt} elem · {ui.human_size(tot)}" if cnt else "üres"})
    except OSError:
        pass
    # Google Drive (rclone-csatolás) — ha be van jelentkezve
    try:
        import fusion_drive
        if fusion_drive.configured():
            m = fusion_drive.mounted()
            out.insert(2, {"name": "Google Drive", "path": fusion_drive.MOUNT if m else "", "icon": "cloud", "dev": "gdrive:",
                           "mounted": m, "media": False,
                           "info": fusion_drive.MOUNT if m else "nincs csatolva — kattintásra csatolás (internet kell)"})
    except Exception:
        pass
    return out


# ---------------------------------------------------------------------------
# a QML-nek: műveletek, vágólap, megnyitás, kötetek
# ---------------------------------------------------------------------------
class Files(QObject):
    jobChanged = pyqtSignal()
    jobFinished = pyqtSignal(str, str, "QStringList")     # fajta, összegzés, hibák
    searchChanged = pyqtSignal()
    clipChanged = pyqtSignal()
    volumesChanged = pyqtSignal()

    def __init__(self, left, right):
        super().__init__()
        self.left, self.right = left, right
        self.job = None
        self._job_view = {}
        self._search = {"running": False, "results": [], "status": ""}
        self._search_job = None
        self._search_results = []
        self._clip = {"paths": [], "cut": False}
        self._vols = []
        self._timer = QTimer(self)
        self._timer.setInterval(150)
        self._timer.timeout.connect(self._poll)
        self._dirsize.connect(lambda m, name, sz: m.set_dir_size(name, int(sz)))

    # --- műveletek (szál) ---
    @pyqtProperty("QVariant", notify=jobChanged)
    def jobState(self):
        return self._job_view

    def _start(self, kind, title, fn):
        if self.job and not self.job.finished:
            return False
        job = Job(kind, title)
        self.job = job

        def work():
            try:
                fn(job)
                job.result = "ok"
            except Cancelled:
                job.result = "megszakítva"
            except Exception as e:    # a felület mindig visszajelzést kap
                job.errors.append(str(e))
                job.result = "hiba"
            job.finished = True
        threading.Thread(target=work, daemon=True).start()
        self._t0 = time.monotonic()
        self._timer.start()
        self._poll()
        return True

    def _poll(self):
        j = self.job
        if not j:
            return
        el = time.monotonic() - self._t0
        pct = (100.0 * j.done / j.total) if j.total else (100.0 * j.files_done / j.files_total if j.files_total else 0)
        speed = j.done / el if el > 0.5 else 0
        self._job_view = {"active": not j.finished, "kind": j.kind, "title": j.title, "current": j.current,
                          "pct": min(100.0, pct), "files": f"{j.files_done} / {j.files_total}",
                          "bytes": f"{ui.human_size(j.done)} / {ui.human_size(j.total)}" if j.total else "",
                          "speed": f"{ui.human_size(speed)}/s" if speed else "", "show": el > 0.4 or j.finished}
        self.jobChanged.emit()
        if j.finished:
            self._timer.stop()
            slow(f"{j.title} (teljes idő)", self._t0, 2.0)
            t_fin = time.monotonic()
            msg = {"ok": "kész", "megszakítva": "megszakítva", "hiba": "hiba"}.get(j.result, j.result)
            self.jobFinished.emit(j.kind, f"{j.title}: {msg}" + (f" — {len(j.errors)} hiba" if j.errors else ""), j.errors[:50])
            if j.result == "ok" and not j.errors:
                # sikeres művelet után a jelölések törlődnek (mint a klasszikus kétpaneles kezelőkben)
                for m in (self.left, self.right):
                    for i in m._items:
                        i["marked"] = False
            self.left.reloadKeep()
            self.right.reloadKeep()
            slow("a művelet utáni frissítés", t_fin)
            self._job_view = {"active": False, "show": False}
            self.jobChanged.emit()

    @pyqtSlot()
    def cancelJob(self):
        if self.job:
            self.job.cancel = True

    @pyqtSlot("QStringList", str, result=str)
    def checkTarget(self, srcs, dst):
        return check_target(list(srcs), dst)

    @pyqtSlot("QStringList", str, result="QStringList")
    def conflicts(self, srcs, dst):
        return conflicts(list(srcs), dst)

    @pyqtSlot("QStringList", str, str, result=bool)
    def copy(self, srcs, dst, overwrite):
        srcs = list(srcs)
        return self._start("copy", f"Másolás ({len(srcs)} elem)", lambda j: FileOps(j, overwrite).copy(srcs, dst))

    @pyqtSlot("QStringList", str, str, result=bool)
    def move(self, srcs, dst, overwrite):
        srcs = list(srcs)
        return self._start("move", f"Mozgatás ({len(srcs)} elem)", lambda j: FileOps(j, overwrite).move(srcs, dst))

    @pyqtSlot("QStringList", result=bool)
    def trashItems(self, srcs):
        """Del / F8: a lomtárba (Google Drive-on a Drive saját lomtárába)"""
        srcs = list(srcs)

        def run(j):
            self._last_trash = FileOps(j).trash(srcs)
        return self._start("trash", f"Lomtárba ({len(srcs)} elem)", run)

    @pyqtSlot(result=int)
    def undoTrash(self):
        """az utolsó lomtárba helyezés visszavonása (Ctrl+Z)"""
        n = 0
        for td, name in getattr(self, "_last_trash", []) or []:
            try:
                trashlib.restore(td, name)
                n += 1
            except (trashlib.TrashError, OSError):
                pass
        self._last_trash = []
        self.left.reloadKeep()
        self.right.reloadKeep()
        return n

    @pyqtSlot("QStringList", result="QVariant")
    def restoreFromTrash(self, paths):
        """kijelölt elemek (a lomtár files mappájából) vissza az eredeti helyükre"""
        ok, errs = 0, []
        for p in paths:
            try:
                trashlib.restore(os.path.dirname(os.path.dirname(p)), os.path.basename(p))
                ok += 1
            except (trashlib.TrashError, OSError) as e:
                errs.append(str(e))
        self.left.reloadKeep()
        self.right.reloadKeep()
        return {"ok": ok, "errors": errs}

    @pyqtSlot("QStringList", result=bool)
    def purgeFromTrash(self, paths):
        paths = list(paths)

        def run(j):
            j.files_total = len(paths)
            for p in paths:
                j.current = os.path.basename(p)
                trashlib.purge(os.path.dirname(os.path.dirname(p)), os.path.basename(p))
                j.files_done += 1
        return self._start("delete", f"Végleges törlés ({len(paths)} elem)", run)

    @pyqtSlot(result=bool)
    def emptyTrash(self):
        return self._start("delete", "A lomtár ürítése", lambda j: trashlib.empty())

    @pyqtSlot(str, result="QVariant")
    def trashInfo(self, path):
        """a lomtárban lévő elem eredeti helye és a törlés ideje"""
        orig, date = trashlib._read_info(os.path.dirname(os.path.dirname(path)), os.path.basename(path))
        return {"orig": orig, "date": date}

    @pyqtSlot(result="QVariant")
    def trashSummary(self):
        tot, cnt = trashlib.size()
        return {"count": cnt, "size": ui.human_size(tot), "path": os.path.join(trashlib.HOME_TRASH, "files")}

    @pyqtSlot(str, result=bool)
    def onNetwork(self, path):
        return trashlib.is_network(path)

    @pyqtSlot("QStringList", result=bool)
    def remove(self, srcs):
        srcs = list(srcs)
        return self._start("delete", f"Törlés ({len(srcs)} elem)", lambda j: FileOps(j).delete(srcs))

    @pyqtSlot("QStringList", str, result=bool)
    def pack(self, srcs, zippath):
        srcs = list(srcs)
        return self._start("pack", f"Tömörítés: {os.path.basename(zippath)}", lambda j: FileOps(j).pack(srcs, zippath))

    @pyqtSlot("QStringList", str, str, result=bool)
    def extract(self, archives, dst, overwrite):
        archives = list(archives)
        return self._start("extract", f"Kicsomagolás ({len(archives)} archívum)", lambda j: FileOps(j, overwrite).extract(archives, dst))

    @pyqtSlot(str, str, result=str)
    def mkdir(self, base, name):
        name = name.strip()
        if not name or name in (".", "..") or "\0" in name:
            return "érvénytelen név"
        try:
            os.makedirs(os.path.join(base, name))
            return ""
        except OSError as e:
            return e.strerror or str(e)

    @pyqtSlot(str, str, result=str)
    def rename(self, path, newname):
        newname = newname.strip()
        if not newname or "/" in newname or newname in (".", ".."):
            return "érvénytelen név"
        dst = os.path.join(os.path.dirname(path), newname)
        if os.path.lexists(dst) and os.path.realpath(dst) != os.path.realpath(path):
            return "már létezik ilyen nevű elem"
        try:
            os.rename(path, dst)
            return ""
        except OSError as e:
            return e.strerror or str(e)

    @pyqtSlot(str, str, result=str)
    def newFile(self, base, name):
        name = name.strip()
        if not name or "/" in name:
            return "érvénytelen név"
        p = os.path.join(base, name)
        if os.path.lexists(p):
            return "már létezik"
        try:
            open(p, "x").close()
            return ""
        except OSError as e:
            return e.strerror or str(e)

    # --- mappaméret (Szóköz a mappán) ---
    _dirsize = pyqtSignal(object, str, float)

    @pyqtSlot(QObject, str)
    def dirSize(self, model, path):
        # a szál jelzéssel adja vissza az eredményt (a Qt a fő szálon hívja a modellt)
        def work():
            sz, _n = _walk_size([path])
            self._dirsize.emit(model, os.path.basename(path), float(sz))
        threading.Thread(target=work, daemon=True).start()

    # --- vágólap ---
    @pyqtProperty("QVariant", notify=clipChanged)
    def clip(self):
        return self._clip

    @pyqtSlot("QStringList", bool)
    def setClip(self, paths, cut):
        self._clip = {"paths": list(paths), "cut": cut}
        md = QMimeData()
        md.setUrls([QUrl.fromLocalFile(p) for p in paths])
        md.setText("\n".join(paths))
        # a GNOME-/KDE-programok ebből tudják, hogy kivágás volt
        md.setData("x-special/gnome-copied-files", ("cut\n" if cut else "copy\n").encode() + "\n".join(QUrl.fromLocalFile(p).toString() for p in paths).encode())
        QGuiApplication.clipboard().setMimeData(md)
        self.clipChanged.emit()

    @pyqtSlot(result="QVariant")
    def takeClip(self):
        """beillesztéskor: a saját vágólap, különben más programból érkezett fájl-URL-ek"""
        md = QGuiApplication.clipboard().mimeData()
        paths = [u.toLocalFile() for u in md.urls() if u.isLocalFile()] if md is not None and md.hasUrls() else []
        if paths and set(paths) == set(self._clip["paths"]):
            return dict(self._clip)
        if paths:
            return {"paths": paths, "cut": False}
        return dict(self._clip)

    @pyqtSlot()
    def clipDone(self):
        if self._clip["cut"]:
            self._clip = {"paths": [], "cut": False}
            self.clipChanged.emit()

    # --- megnyitás ---
    @pyqtSlot(str, result=str)
    def kind(self, path):
        return kind_of(path)

    @pyqtSlot(str, result="QVariant")
    def readFile(self, path):
        """megtekintéshez / szerkesztéshez: szöveg (UTF-8, különben latin-1) vagy hexa nézet"""
        info = {"path": path, "name": os.path.basename(path), "text": "", "binary": False, "truncated": False,
                "size": 0, "error": "", "kind": kind_of(path), "info": ""}
        try:
            st = os.stat(path)
            info["size"] = st.st_size
            info["info"] = f"{ui.human_size(st.st_size)} · {fmt_date(st.st_mtime)} · {perm_text(st.st_mode)}"
            if info["kind"] == "archive":
                info["text"] = archive_list(path)
                return info
            if info["kind"] == "image":
                return info
            if info["kind"] == "exe":
                info["info"] += " · " + pe_info(path)
            limit = 4 * CHUNK
            with open(path, "rb") as f:
                data = f.read(limit + 1)
            info["truncated"] = len(data) > limit
            data = data[:limit]
            if b"\0" in data[:65536] or info["kind"] in ("exe", "elf", "binary"):
                info["binary"] = True
                rows = []
                for off in range(0, min(len(data), 65536), 16):
                    chunk = data[off:off + 16]
                    hx = " ".join(f"{b:02x}" for b in chunk)
                    tx = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
                    rows.append(f"{off:08x}  {hx:<47}  {tx}")
                info["text"] = "\n".join(rows)
                info["truncated"] = len(data) > 65536
            else:
                try:
                    info["text"] = data.decode("utf-8")
                except UnicodeDecodeError:
                    info["text"] = data.decode("latin-1")
                    info["info"] += " · latin-1"
        except OSError as e:
            info["error"] = e.strerror or str(e)
        return info

    @pyqtSlot(str, str, result=str)
    def writeFile(self, path, text):
        try:
            tmp = path + ".fusion-save"
            mode = os.stat(path).st_mode & 0o7777 if os.path.exists(path) else 0o644
            with open(tmp, "w", encoding="utf-8", newline="") as f:
                f.write(text)
            os.chmod(tmp, mode)
            os.replace(tmp, path)
            return ""
        except OSError as e:
            return e.strerror or str(e)

    @pyqtSlot(str, result=str)
    def imageUrl(self, path):
        return QUrl.fromLocalFile(path).toString()

    @pyqtSlot(str)
    def runFile(self, path):
        ui.spawn([path], cwd=os.path.dirname(path))

    @pyqtSlot(str)
    def terminalHere(self, path):
        ui.spawn(["xterm"], cwd=path)

    @pyqtSlot(str)
    def installProgram(self, path):
        """telepítés: a Programkezelő nyílik ezzel a fájllal"""
        ui.spawn(["fusion-settings", "programs", path])

    @pyqtSlot(str, bool, result=str)
    def openWithProgram(self, path, explicit_only):
        """ha egy telepített program megnyitja ezt a fájltípust (Programkezelő → társítás): indítás, a program neve"""
        if fp is None:
            return ""
        try:
            progs = fp.assoc(path, explicit_only)
        except Exception:
            return ""
        if not progs:
            return ""
        ui.spawn(["fusion-run", progs[0][0], path])
        return progs[0][1]

    @pyqtSlot(str, result="QVariant")
    def openWithChoices(self, path):
        """„Megnyitás ezzel…”: a programok (a típust ismerők elöl), a kulcs (.svg) és a mostani választás"""
        if fp is None:
            return {"key": "", "keyLabel": "", "current": "", "items": []}
        try:
            d = fp.open_with_choices(path)
        except Exception:
            d = {"key": "", "current": "", "items": []}
        k = d["key"]
        d["keyLabel"] = (k + " fájlokat") if k.startswith(".") else (k + " típusú fájlokat") if k else ""
        cur = d["current"]
        d["currentName"] = "Fusion nézőke" if cur == fp.BUILTIN else next((i["name"] for i in d["items"] if i["id"] == cur), "")
        return d

    @pyqtSlot(str, str, bool, result=str)
    def openWith(self, path, pid, always):
        """megnyitás a választott programmal (pid üres: a Fusion nézőke — azt a felület nyitja);
        always: ezentúl ez a típus mindig ezzel nyíljon (Enter, dupla kattintás)"""
        if fp is None:
            return "a Programkezelő nem érhető el"
        try:
            k = fp.assoc_key(path)
            if always and k:
                fp.associate(k, pid or fp.BUILTIN)
            if pid:
                ui.spawn(["fusion-run", pid, path])
        except Exception as e:
            return str(e)
        return ""

    @pyqtSlot(str)
    def resetAssociation(self, path):
        """a választás törlése: a típus újra az alapértelmezés szerint nyílik"""
        if fp is not None:
            fp.dissociate(fp.assoc_key(path))

    # --- keresés ---
    @pyqtProperty("QVariant", notify=searchChanged)
    def searchState(self):
        return self._search

    @pyqtSlot(str, str, str)
    def startSearch(self, root, pattern, text):
        self.stopSearch()
        job = Job("search", "Keresés")
        results = []
        self._search_job, self._search_results = job, results
        self._search = {"running": True, "results": [], "status": "keresés…"}
        self.searchChanged.emit()

        def work():
            try:
                search(root, pattern, text, job, results)
            except Exception as e:
                job.errors.append(str(e))
            job.finished = True
        threading.Thread(target=work, daemon=True).start()
        self._stimer = QTimer(self)
        self._stimer.setInterval(200)
        self._stimer.timeout.connect(self._poll_search)
        self._stimer.start()

    def _poll_search(self):
        j = self._search_job
        if not j:
            return
        res = list(self._search_results)
        self._search = {"running": not j.finished, "results": res,
                        "status": (f"{len(res)} találat" + ("" if j.finished else f" — {j.current}"))}
        self.searchChanged.emit()
        if j.finished:
            self._stimer.stop()

    @pyqtSlot()
    def stopSearch(self):
        if self._search_job:
            self._search_job.cancel = True

    # --- összehasonlítás ---
    @pyqtSlot(result=str)
    def compare(self):
        lm, rm = compare_dirs(self.left.entries(), self.right.entries())
        self.left.mark_names(lm)
        self.right.mark_names(rm)
        if not lm and not rm:
            return "a két mappa fájljai egyeznek"
        return f"eltérő / hiányzó fájlok: bal {len(lm)}, jobb {len(rm)} (megjelölve)"

    # --- kötetek ---
    @pyqtProperty("QVariant", notify=volumesChanged)
    def volumes(self):
        return self._vols

    @pyqtSlot()
    def refreshVolumes(self):
        t0 = time.monotonic()
        self._vols = volumes()
        slow("kötetek listája", t0)
        self.volumesChanged.emit()

    @pyqtSlot(str, result="QVariant")
    def mountVolume(self, dev):
        if dev == "gdrive:":
            import fusion_drive
            ok, msg = fusion_drive.start()
            self.refreshVolumes()
            return {"ok": ok, "path": msg if ok else "", "msg": "" if ok else "Google Drive: " + msg}
        rc, out = ui.admin("mount", dev)
        self.refreshVolumes()
        path = ""
        for line in out.splitlines():
            if "-> " in line:
                path = line.split("-> ", 1)[1].split(" (")[0].strip()
            elif line.startswith("már csatolva: "):
                path = line.split(": ", 1)[1].strip()
        return {"ok": rc == 0, "path": path, "msg": out.strip()}

    @pyqtSlot(str, result="QVariant")
    def ejectVolume(self, dev_or_path):
        rc, out = ui.admin("eject" if dev_or_path.startswith("/dev/") else "unmount", dev_or_path)
        self.refreshVolumes()
        return {"ok": rc == 0, "msg": out.strip()}

    @pyqtSlot(str, result="QVariant")
    def volumeOf(self, path):
        """a panel „meghajtó” gombjához: melyik kötet / hely tartalmazza az utat"""
        best = None
        for v in self._vols or volumes():
            p = v.get("path")
            if p and (path == p or path.startswith(p.rstrip("/") + "/")):
                if best is None or len(p) > len(best["path"]):
                    best = v
        return best or {"name": path, "icon": "drive", "path": "/"}
