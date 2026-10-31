"""Fúzió — Beállítások háttere: Rendszerfrissítés (.fupd), új változat a forrásból, telepítő pendrive

A Settings osztály (fusion_settings_backend) ezekből a részekből áll össze; a QML ugyanazt a `settings`
objektumot látja, mint a szétszedés előtt."""
import glob
import json
import os
import re
import time
from PyQt6.QtCore import pyqtSlot
import fusion_ui as ui
import fusion
from fusion import jobs as fjobs
from fusion_settings_parts.base import _read


# --- Rendszerfrissítés (M7): .fupd fájlok a szokásos helyeken, a futó rendszer állapota ---
_FUPD_CACHE = {}       # (út, méret, módosítás) → manifest-adatok: egy .fupd-t csak egyszer olvasunk


def fupd_info(path):
    """a frissítőfájl manifestje (csak a tar elejét olvassa; az eredmény gyorsítótárban)"""
    import tarfile
    try:
        st = os.stat(path)
    except OSError:
        return None
    key = (path, st.st_size, st.st_mtime)
    if key in _FUPD_CACHE:
        return _FUPD_CACHE[key]
    try:
        with tarfile.open(path, "r:") as t:
            m = t.next()                    # a manifest a csomag első tagja (build.sh: _make_fupd)
            if m is None or os.path.basename(m.name) != "fusion-update.manifest":
                m = None
            txt = t.extractfile(m).read().decode("utf-8", "replace") if m else ""
    except (tarfile.TarError, OSError):
        return None
    kv = dict(ln.split("=", 1) for ln in txt.splitlines() if "=" in ln and " " not in ln.split("=", 1)[0])
    if "FUSION_VERSION" not in kv:
        _FUPD_CACHE[key] = None
        return None
    info = {"version": kv.get("FUSION_VERSION", "?"), "milestone": kv.get("FUSION_MILESTONE", ""),
            "stamp": kv.get("BUILD_STAMP", ""),
            # T3: telepítő pendrive is készíthető belőle (a telepítő UKI-ja és az ESP-fájlok benne vannak)
            "media": bool(re.search(r"(?m)^uki-installer\.efi ", txt)) and bool(re.search(r"(?m)^esp-static\.tar ", txt))}
    _FUPD_CACHE[key] = info
    return info


# a saját mappa alatt ezekbe soha nem nézünk bele: hálózati / külső kötetek (a Google Drive rclone-csatolása hideg
# gyorsítótárral egyetlen mappanévért is percekig várhat — ZBook-mérés, 2026-10-30: `~/*/build` glob 60 mp fölött)
_UPDATE_SKIP = ("GoogleDrive", "Tárhely", "drive_c", "cache")


def _mount_points():
    """a csatolási pontok a /proc/self/mounts-ból — stat nélkül (egy beragadt hálózati kötet stat-ja is várakozhat)"""
    try:
        with open("/proc/self/mounts", encoding="utf-8", errors="replace") as f:
            return {ln.split()[1].replace("\\040", " ") for ln in f if len(ln.split()) > 1}
    except OSError:
        return set()


def _plain_subdirs(path, mounts):
    """a mappa közvetlen almappái, a rejtettek, a kihagyottak és a csatolási pontok nélkül; a d_type-ot használja
    (nincs stat), a symlinkeket nem követi — így egy kötetbe vezető hivatkozás sem lassít"""
    try:
        with os.scandir(path) as it:
            return [e.path for e in it if not e.name.startswith(".") and e.name not in _UPDATE_SKIP
                    and e.path not in mounts and e.is_dir(follow_symlinks=False)]
    except OSError:
        return []


def update_roots():
    """a keresési helyek, a valószínűek elöl: a saját build kimenete, Letöltések, /data/import, a saját mappa, végül
    a csatolt kötetek (pendrive, Tárhely). A saját mappa alatt csatolt kötetbe (Google Drive) nem lép be."""
    home = os.path.expanduser("~")
    mounts = _mount_points()
    # a saját build kimenete (Fejlesztődoboz: ~/Projektek/fusionos/build/out/release) — legfeljebb két szint mélyen
    builds = []
    for d in _plain_subdirs(home, mounts):
        for cand in [d] + _plain_subdirs(d, mounts):
            rel = os.path.join(cand, "build", "out", "release")
            if os.path.isdir(rel):
                builds.append(rel)
    fast = sorted(set(builds)) + [os.path.join(home, "Letöltések"), os.path.join(home, "Downloads"), "/data/import", home]
    return fast, sorted(glob.glob(fusion.MEDIA + "/*"))


def update_files(roots=None, budget=None):
    """.fupd fájlok a megadott helyeken (legfeljebb 2 szint mélyen); budget: másodperc, utána a bejárás abbamarad"""
    home = os.path.expanduser("~")
    if roots is None:
        fast, media = update_roots()
        roots = fast + media
    t0 = time.monotonic()
    mounts = _mount_points()
    seen, out = set(), []
    for r in roots:
        if not os.path.isdir(r):
            continue
        base = r.rstrip("/").count("/")
        for dirpath, dirs, files in os.walk(r):
            if budget is not None and time.monotonic() - t0 > budget:
                dirs[:] = []
                break
            if dirpath.count("/") - base >= 2:
                dirs[:] = []
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in _UPDATE_SKIP
                       and os.path.join(dirpath, d) not in mounts]
            for f in files:
                if not f.lower().endswith(".fupd"):
                    continue
                p = os.path.join(dirpath, f)
                if os.path.realpath(p) in seen:
                    continue
                seen.add(os.path.realpath(p))
                info = fupd_info(p)
                if not info:
                    continue
                st = os.stat(p)
                out.append(dict(info, path=p, name=f, size=ui.human_size(st.st_size), mtime=st.st_mtime,
                                place=os.path.dirname(p).replace(home, "~")))
    out.sort(key=lambda x: x.get("stamp", ""), reverse=True)
    return out[:20]


LOADER_GUID = "4a67b082-0a4c-41cf-b6c7-440b29bb8c4f"


def running_stamp():
    """a futó rendszer build-bélyege a systemd-boot által indított bejegyzés nevéből (pl. fusionos-0.0.53-e1-<bélyeg>-a)
    — root nélkül, az efivarfs-ból; ha nem olvasható: üres"""
    try:
        with open(f"/sys/firmware/efi/efivars/LoaderEntrySelected-{LOADER_GUID}", "rb") as f:
            name = f.read()[4:].decode("utf-16-le").rstrip("\x00")
    except (OSError, UnicodeDecodeError):
        return ""
    parts = name.split("-")
    return parts[-2] if len(parts) >= 5 and parts[-2].isdigit() else ""


def mark_newer(files, stamp):
    for f in files:
        f["newer"] = bool(f.get("stamp")) and (not stamp.isdigit() or f["stamp"] > stamp)
    return files


def update_state():
    rc, out = ui.admin("update-status", "--json", timeout=20)
    try:
        st = json.loads(out) if rc == 0 else {}
    except ValueError:
        st = {}
    rel = ui.fusion_release()
    running = next((e for e in st.get("entries", []) if e.get("running")), None)
    stamp = running["name"].split("-")[-2] if running and running["name"].count("-") >= 4 else running_stamp()
    return {"version": rel.get("FUSION_VERSION", "?"), "milestone": rel.get("FUSION_MILESTONE", ""),
            "slot": st.get("slot", _read("/run/fusion/slot", "?")), "state": st.get("state", ""),
            "entries": st.get("entries", []), "error": "" if rc == 0 else out.strip()[:200], "stamp": stamp,
            "src": fusion_src()}


# --- Új változat a forrásból (0.0.69): fusion-dev rebuild a Fejlesztődobozban, a végén telepítés kérdéssel ---
def fusion_src():
    """a Fúzió forrásfája a saját gépen (ha nincs: üres — tesztelőknél a gomb nem látszik)"""
    home = os.path.expanduser("~")
    for c in [os.environ.get("FUSION_SRC", "")] + [os.path.join(home, "Projektek", n) for n in ("fusionos", "fuzio", "Fuzio")]:
        if c and os.path.isfile(os.path.join(c, "build", "fusion-build")) and os.path.isdir(os.path.join(c, ".git")):
            return os.path.realpath(c)
    return ""


def _from_src(src, rel, fallback):
    """a forrásfa saját példánya (mindig a legújabb), különben a rendszerkép parancsa"""
    p = os.path.join(src, rel) if src else ""
    return ["python3", p] if p and os.path.isfile(p) else [fallback]


def media_disks():
    """a cserélhető lemezek (telepítő pendrive készítéséhez)"""
    rc, out = ui.admin("disk", "list", timeout=60)
    try:
        d = json.loads(out[out.index("{"):])
    except ValueError:
        return []
    return [{"name": x["name"], "model": x["model"], "size": x["size"], "sizeText": ui.human_size(x["size"]),
             "content": ", ".join((p["label"] or p["partlabel"] or p["name"]) for p in x["partitions"][:4]) or "üres"}
            for x in d.get("disks", []) if x["removable"] and not x["system"]]


class UpdateMixin:
    """Rendszerfrissítés (.fupd), új változat a forrásból, telepítő pendrive — a Settings része (a slotok a QML-nek)"""

    # --- Rendszerfrissítés ---
    @pyqtSlot()
    def updateRefresh(self):
        """két külön szálon: a frissítőfájlok (gyors helyek azonnal, a csatolt kötetek utána) és a rendszer-slotok
        állapota (fusion-admin) — az egyik lassúsága nem tartja vissza a másikat"""
        def st():
            d = update_state()
            d["job"] = self._job_state("update")
            return d
        self._async("update", st)

        def files():
            stamp = running_stamp()
            fast, media = update_roots()
            t0 = time.monotonic()
            quick = mark_newer(update_files(fast, budget=5), stamp)
            self.result.emit("update-files", {"files": quick, "partial": bool(media), "stamp": stamp})
            allf = mark_newer(update_files(fast + media, budget=20), stamp) if media else quick
            return {"files": allf, "partial": False, "stamp": stamp, "secs": round(time.monotonic() - t0, 1)}
        self._async("update-files", files)

    @pyqtSlot(str, result=str)
    def updateInstall(self, path):
        if not path.endswith(".fupd") or not os.path.isfile(path):
            return "nem .fupd frissítőfájl: " + path
        info = fupd_info(path) or {}
        return self._job("Rendszerfrissítés: Fúzió " + info.get("version", "?"), [path], kind="update",
                         cmd=("sudo", "-n", ui.ADMIN, "update-apply"), app="Rendszerfrissítés", icon="update",
                         okpat="^KÉSZ:")

    @pyqtSlot()
    def rebuildCheck(self):
        def go():
            src = fusion_src()
            rc, out = ui.run(_from_src(src, "programs/fusion-dev", "fusion-dev") + ["rebuild", "--check", "--json"], timeout=240)
            try:
                return json.loads(out.strip().splitlines()[-1])
            except (ValueError, IndexError):
                return {"ok": False, "problems": [out.strip()[-300:] or "a fusion-dev nem válaszolt"], "warnings": []}
        self._async("rebuild-check", go)

    @pyqtSlot(result=str)
    def rebuildStart(self):
        src = fusion_src()
        if not src:
            return "nem találom a Fúzió forrását (~/Projektek/fusionos)"
        return self._job("Új változat a forrásból", ["rebuild"], kind="rebuild",
                         cmd=tuple(_from_src(src, "programs/fusion-dev", "fusion-dev")), app="Rendszerfrissítés",
                         icon="update", okpat="^KÉSZ:")

    @pyqtSlot()
    def rebuildJobWatch(self):
        st = self._job_state("rebuild")
        self.result.emit("rebuild-job", st)
        if st["running"]:
            self._job_watch("rebuild")

    @pyqtSlot(result=str)
    def rebuildFupd(self):
        """a legutóbbi sikeres build .fupd-je (a feladat naplójából)"""
        try:
            with open(fjobs._paths("rebuild")[1], encoding="utf-8", errors="replace") as f:
                lines = f.read().splitlines()
        except (OSError, ValueError):
            return ""
        p = next((ln[6:].strip() for ln in reversed(lines) if ln.startswith("FUPD: ")), "")
        return p if p.endswith(".fupd") and os.path.isfile(p) else ""

    @pyqtSlot()
    def rebuildToAI(self):
        """a build naplója a FusionAI-ba (Kimenet → Claude), a Fúzió forrásával mint projekttel"""
        src = fusion_src()
        try:
            log = fjobs._paths("rebuild")[1]
        except ValueError:
            return
        ui.spawn(_from_src(src, "desktop/ai/fusion_ai_app.py", "fusion-ai") + ([src] if src else []) + ["--kimenet", log])

    @pyqtSlot()
    def updateJobWatch(self):
        if self._job_state("update")["running"]:
            self._job_watch("update")

    @pyqtSlot()
    def updateReboot(self):
        self._async("power", lambda: dict(zip(("rc", "msg"), ui.admin("update-reboot"))))

    # --- telepítő pendrive a Rendszerfrissítés oldalról (T3) ---
    @pyqtSlot()
    def mediaDisks(self):
        self._async("media-disks", lambda: {"disks": media_disks()})

    @pyqtSlot(str, str, str, result=str)
    def mediaCreate(self, fupd, disk, confirm):
        info = fupd_info(fupd) or {}
        if not info.get("media"):
            return "ebből a .fupd-ből nem készíthető telepítő (0.0.29 előtti csomag)"
        return self._job("Telepítő pendrive: Fúzió " + info.get("version", "?"), [fupd, disk, confirm], kind="media",
                         cmd=("sudo", "-n", ui.ADMIN, "installer-media"), app="Rendszerfrissítés", icon="drive-usb",
                         okpat="^KÉSZ:")

    @pyqtSlot()
    def mediaJobWatch(self):
        if self._job_state("media")["running"]:
            self._job_watch("media")
