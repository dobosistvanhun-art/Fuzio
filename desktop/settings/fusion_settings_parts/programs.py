"""Fúzió — Beállítások háttere: Programkezelő, Programbolt, fejlesztői eszközök, Fejlesztődoboz

A Settings osztály (fusion_settings_backend) ezekből a részekből áll össze; a QML ugyanazt a `settings`
objektumot látja, mint a szétszedés előtt."""
import glob
import json
import os
import re
import threading
import time
from PyQt6.QtCore import pyqtSlot
import fusion_apps  # noqa: F401  (a fusion_programs útvonalát is beállítja — előtte kell)
import fusion_programs as fp
import fusion_store as store
import fusion_ui as ui
import fusion
from fusion import devices as fdev
from fusion_settings_parts.base import _timing, SAFE


# --- Programkezelő: telepítők a szokásos helyeken ---
INSTALLER_EXT = (".exe", ".msi", ".appimage", ".flatpakref", ".flatpak")


def installers():
    """telepítő a szokásos helyeken (saját mappa, Letöltések, /data/import, USB-meghajtók):
    Windows (.exe, .msi), AppImage, Flatpak (.flatpakref, .flatpak)"""
    home = os.path.expanduser("~")
    roots = [home, os.path.join(home, "Letöltések"), os.path.join(home, "Downloads"), "/data/import"] + sorted(glob.glob(fusion.MEDIA + "/*"))
    seen, out = set(), []
    t_end = time.monotonic() + 5          # legfeljebb ennyi idő (egy lassú kötet ne tartsa fel a listát)
    for r in roots:
        if not os.path.isdir(r) or time.monotonic() > t_end:
            continue
        base_depth = r.rstrip("/").count("/")
        for dirpath, dirs, files in os.walk(r):
            if dirpath.count("/") - base_depth >= 2 or time.monotonic() > t_end:
                dirs[:] = []
            # más fájlrendszerre (pl. a Google Drive hálózati csatolása, FUSE) nem lépünk át: a bejárása percekig tartana
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("drive_c", "GoogleDrive")
                       and not os.path.ismount(os.path.join(dirpath, d))]
            for f in files:
                if f.lower().endswith(INSTALLER_EXT):
                    p = os.path.join(dirpath, f)
                    rp = os.path.realpath(p)
                    if rp in seen:
                        continue
                    seen.add(rp)
                    try:
                        st = os.stat(p)
                    except OSError:
                        continue
                    out.append({"path": p, "name": f, "size": ui.human_size(st.st_size),
                                "date": time.strftime("%Y.%m.%d", time.localtime(st.st_mtime)), "mtime": st.st_mtime})
    out.sort(key=lambda x: -x["mtime"])
    return out[:50]


class ProgramsMixin:
    """Programkezelő, Programbolt, fejlesztői eszközök, Fejlesztődoboz — a Settings része (a slotok a QML-nek)"""

    # --- Programkezelő ---
    @pyqtSlot()
    def programsRefresh(self):
        """két lépésben: azonnal a leírásokból (gyors), majd a Flatpak-összehangolás és a telepítők keresése után
        újra — a lista így nem vár a lassú részekre (a ZBookon ez korábban 1–2 perc volt)"""
        if "programs" in self._busy:
            return
        self._busy.add("programs")

        def snapshot(with_installers):
            roles = [{"role": r["role"], "name": r["name"], "com": r["com"]} for r in fdev.definitions()]
            have = {p["id"] for p in fp.programs()}
            d = {"programs": [fp.info(m) for m in fp.programs()], "roles": roles,
                 "recipes": [{"id": r["id"], "name": r.get("name", r["id"]), "match": r.get("match", "")}
                             for r in fp.recipes() if r["id"] not in have],
                 "job": self._job_state()}
            if with_installers:
                d["installers"] = installers()
            return d

        def work():
            try:
                t0 = time.monotonic()
                self.result.emit("programs", snapshot(False))
                try:
                    fp.sync()      # a parancssorból telepített / eltávolított Flatpakok is látszódjanak
                except Exception:
                    pass
                self.result.emit("programs", snapshot(True))
                _timing("programs", time.monotonic() - t0)
            except Exception as e:
                self.result.emit("programs", {"error": str(e)})
            finally:
                self._busy.discard("programs")
        threading.Thread(target=work, daemon=True).start()

    @pyqtSlot()
    def programSizes(self):
        self._async("program-sizes", lambda: {m["id"]: ui.human_size(fp.size_mib(m) * 1048576) for m in fp.programs()})

    @pyqtSlot(str, result=str)
    def programDetect(self, path):
        if not os.path.isfile(path):
            return ""
        return {"win64": "Windows-program (x64)", "win32": "Windows-program (32 bites — a Fusion célja az x64)",
                "msi": "Windows-telepítő (MSI)", "appimage": "Linux-program (AppImage)", "flatpakref": "Linux-program (Flatpak-hivatkozás)",
                "flatpak": "Linux-program (Flatpak-csomag)", "archive": "Linux-program archívumban", "elf": "Linux-program (önálló)",
                }.get(fp.detect(path), "ismeretlen fájltípus")

    @pyqtSlot()
    def programJobWatch(self):
        if self._job_state()["running"]:
            self._job_watch()

    @pyqtSlot(str, str, bool, result=str)
    def programInstall(self, src, name, portable):
        if src.startswith("flathub:"):
            if not re.match(r"^flathub:[A-Za-z0-9_.-]+$", src):
                return "érvénytelen Flathub-azonosító"
            title = "Telepítés: " + src[8:]
        else:
            if not os.path.isfile(src):
                return "a fájl nem található: " + src
            title = "Telepítés: " + os.path.basename(src)
        args = ["install", src] + (["--name", name.strip()] if name.strip() else []) + (["--portable"] if portable else [])
        return self._job(title, args)

    @pyqtSlot(str, bool, result=str)
    def programRemove(self, pid, data):
        m = fp.manifest(pid) if SAFE.match(pid) else None
        if not m:
            return "nincs ilyen program"
        return self._job("Eltávolítás: " + m.get("name", pid), ["remove", pid] + (["--data"] if data else []))

    @pyqtSlot(str, result=str)
    def programUpdate(self, pid):
        m = fp.manifest(pid) if SAFE.match(pid) else None
        if not m:
            return "nincs ilyen program"
        return self._job("Frissítés: " + m.get("name", pid), ["update", pid])

    @pyqtSlot(str)
    def programLaunch(self, pid):
        if SAFE.match(pid):
            ui.spawn(["fusion-run", pid])

    @pyqtSlot(str, str, str, result=str)
    def programDevice(self, pid, com, role):
        try:
            fp.set_device(pid, com, role)
            return ""
        except fp.ProgramError as e:
            return str(e)

    @pyqtSlot(str)
    def flathubSearch(self, term):
        self._async("flathub", lambda: {"results": fp.flatpak_search(term), "term": term})

    # --- Fejlesztői eszközök ---
    @pyqtSlot()
    def devRefresh(self):
        def f():
            rc, out = ui.run(["fusion-dev", "--json"], timeout=90)
            try:
                d = json.loads(out.strip().splitlines()[-1])
            except (ValueError, IndexError):
                d = {"node": "", "npm": "", "wrangler": "", "error": out.strip()[-200:]}
            d.setdefault("box", {})
            d["boxJob"] = self._job_state("devbox")
            return d
        self._async("dev", f)

    # --- Fejlesztődoboz (Ubuntu 24.04 a DATA-n, systemd-nspawn; fusion-devbox) ---
    @pyqtSlot(result=str)
    def devboxCreate(self):
        return self._job("Fejlesztődoboz létrehozása", [], kind="devbox", cmd=("sudo", "-n", ui.ADMIN, "devbox", "create"),
                         app="Programkezelő", icon="terminal", okpat="^KÉSZ:")

    @pyqtSlot()
    def devboxJobWatch(self):
        if self._job_state("devbox")["running"]:
            self._job_watch("devbox")

    @pyqtSlot()
    def devboxRemove(self):
        self._async("devbox-action", lambda: dict(zip(("rc", "msg"), ui.admin("devbox", "remove", "doboz", timeout=900))))

    @pyqtSlot()
    def devboxShell(self):
        ui.spawn(["fusion-devterm"])

    # --- Programbolt (Flathub) ---
    def _installed_apps(self):
        return {m.get("appid"): m["id"] for m in fp.programs() if m.get("type") == "flatpak"}

    @pyqtSlot(str, str, int)
    def storeList(self, kind, arg, page):
        """kind: popular | category | search — az eredmény „store-list”, utána az ikonok „store-icons” címkével"""
        def f():
            if kind == "category":
                r = store.category(arg, page)
            elif kind == "search":
                r = store.search(arg, page)
            else:
                r = store.popular(page)
            r.update({"kind": kind, "arg": arg, "installed": self._installed_apps(),
                      "icons": {a["appid"]: p for a in r["apps"] for p in [store.cached_path(a["icon"])] if p}})
            self._store_icons(r["apps"])
            return r

        def g():
            try:
                return f()
            except store.StoreError as e:
                return {"error": str(e), "kind": kind, "arg": arg, "apps": [], "page": page, "pages": 0}
        # nem _async: egy lassú lekérdezés ne tartsa vissza a következő kattintást (a felület a kind/arg szerint szűr)
        threading.Thread(target=lambda: self.result.emit("store-list", g()), daemon=True).start()

    def _store_icons(self, apps):
        """ikonok letöltése párhuzamosan; csomagokban jelez a felületnek"""
        todo = [a for a in apps if a["icon"] and not store.cached_path(a["icon"])]
        if not todo:
            return

        def work(chunk):
            got = {}
            for a in chunk:
                p = store.cached(a["icon"], timeout=15)
                if p:
                    got[a["appid"]] = p
            if got:
                self.result.emit("store-icons", got)
        for i in range(4):
            threading.Thread(target=work, args=(todo[i::4],), daemon=True).start()

    @pyqtSlot(str)
    def storeDetails(self, appid):
        def f():
            try:
                d = store.details(appid)
            except store.StoreError as e:
                return {"error": str(e), "appid": appid}
            d["iconFile"] = store.cached(d["icon"])
            d["downloadText"] = ui.human_size(d["download"]) if d["download"] else ""
            d["installedText"] = ui.human_size(d["installed"]) if d["installed"] else ""
            d["pid"] = self._installed_apps().get(appid, "")
            d["shotFiles"] = []

            def shots():
                files = [p for p in (store.cached(u, timeout=30) for u in d["screenshots"]) if p]
                self.result.emit("store-shots", {"appid": appid, "files": files})
                store.prune_cache()
            threading.Thread(target=shots, daemon=True).start()
            return d
        threading.Thread(target=lambda: self.result.emit("store-details", f()), daemon=True).start()

    @pyqtSlot(result="QVariant")
    def storeCategories(self):
        return [{"id": c, "name": n, "icon": i} for c, n, i in store.CATEGORIES]

    @pyqtSlot(result="QVariant")
    def storeInstalled(self):
        return self._installed_apps()
