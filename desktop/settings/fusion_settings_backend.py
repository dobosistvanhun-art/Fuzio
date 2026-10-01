"""FusionOS — Beállítások: háttérrész

Oldalak: Wi-Fi, Kijelző, Eszközök, Nyomtató (Klipper), Programkezelő, Asztal, Rendszer.
A lassú lekérdezések és műveletek (Wi-Fi-keresés, kapcsolódás, szolgáltatás-újraindítás) külön
szálon futnak; az eredmény a „result” jelzéssel jön vissza (címke + adat), a felület nem akad meg.
Rendszerjogot igénylő művelet csak a szűk jogú fusion-admin segéden át történik.
"""
import glob
import json
import os
import re
import shlex
import subprocess
import threading
import time
import urllib.request

from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot

import fusion_apps  # noqa: F401  (a programlista — a fusion_programs útvonalát is beállítja)
import fusion_net
import fusion_sound
import fusion_programs as fp
import fusion_store as store
import fusion_ui as ui

ROLES_DIR = os.environ.get("FUSION_DEVICES_ROLES", "/usr/lib/fusion/devices/roles")
DEVICES_DB = "/etc/fusion/devices.conf"
MOONRAKER = "http://127.0.0.1:7125"
BG_FILE = os.path.join(ui.CONFIG, "background")
DISPLAY_FILE = os.path.join(ui.CONFIG, "display.sh")
BG_DEFAULT = "#16202b"
SAFE = re.compile(r"^[A-Za-z0-9_.:+-]+$")
JOB_DIR = os.path.expanduser("~/.local/share/fusion")
JOB_LOG = os.path.join(JOB_DIR, "programs-job.log")
JOB_PID = os.path.join(JOB_DIR, "programs-job.pid")
JOB_TITLE = os.path.join(JOB_DIR, "programs-job.title")


def _kv(path):
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


def _read(path, default=""):
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return f.read().strip()
    except OSError:
        return default


# --- Kijelző (xrandr) ---
def displays():
    rc, out = ui.run(["xrandr", "--query"], timeout=5)
    outs = []
    cur = None
    for line in out.splitlines():
        m = re.match(r"^(\S+) (connected|disconnected)( primary)?\s*(\d+x\d+\+\d+\+\d+)?", line)
        if m:
            cur = {"name": m.group(1), "connected": m.group(2) == "connected", "primary": bool(m.group(3)),
                   "geometry": m.group(4) or "", "modes": [], "current": "", "preferred": ""}
            outs.append(cur)
            continue
        m = re.match(r"^\s+(\d+x\d+i?)\s+(.*)$", line)
        if m and cur is not None:
            mode, rates = m.group(1), m.group(2)
            if mode not in [x["mode"] for x in cur["modes"]]:
                r = re.findall(r"([\d.]+)([ *+]*)", rates)
                hz = r[0][0] if r else ""
                cur["modes"].append({"mode": mode, "hz": hz})
            if "*" in rates:
                cur["current"] = mode
            if "+" in rates and not cur["preferred"]:
                cur["preferred"] = mode
    return [o for o in outs if o["connected"]], rc == 0


# --- Eszközök ---
def serial_props(dev):
    rc, out = ui.run(["udevadm", "info", "--query=property", "--name", dev], timeout=3)
    p = {}
    for line in out.splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            p[k] = v
    return p


def devices():
    db = {}
    for line in _read(DEVICES_DB).splitlines():
        parts = line.split()
        if len(parts) >= 2 and not line.startswith("#"):
            db[parts[0]] = parts[1]
    roles = []
    bound = set()
    for rf in sorted(glob.glob(os.path.join(ROLES_DIR, "*.role"))):
        r = _kv(rf)
        role = r.get("role", "")
        link = f"/dev/fusion/{role}"
        present = os.path.exists(link)
        tgt = os.path.basename(os.path.realpath(link)) if present else ""
        if present:
            bound.add(os.path.realpath(link))
        roles.append({"role": role, "name": r.get("name", role), "present": present, "dev": tgt,
                      "key": db.get(role, ""), "com": r.get("windows.com", ""), "match": r.get("match.usb", "")})
    serial = []
    for d in sorted(glob.glob("/dev/ttyUSB*") + glob.glob("/dev/ttyACM*")):
        p = serial_props(d)
        serial.append({"dev": os.path.basename(d), "id": f"{p.get('ID_VENDOR_ID', '?')}:{p.get('ID_MODEL_ID', '?')}",
                       "model": (p.get("ID_MODEL_FROM_DATABASE") or p.get("ID_MODEL") or "").replace("_", " "),
                       "vendor": (p.get("ID_VENDOR_FROM_DATABASE") or p.get("ID_VENDOR") or "").replace("_", " "),
                       "port": p.get("ID_PATH", ""), "serial": p.get("ID_SERIAL_SHORT", ""),
                       "role": next((r["role"] for r in roles if r["present"] and os.path.realpath(f"/dev/fusion/{r['role']}") == os.path.realpath(d)), "")})
    usb = []
    rc, out = ui.run(["lsusb"], timeout=3)
    for line in out.splitlines():
        m = re.match(r"Bus (\d+) Device (\d+): ID (\S+)\s*(.*)", line)
        if m and not m.group(4).lower().startswith("linux foundation"):
            usb.append({"id": m.group(3), "name": m.group(4) or "(ismeretlen)", "bus": f"{m.group(1)}/{m.group(2)}"})
    return {"roles": roles, "serial": serial, "usb": usb}


# --- Nyomtató (Klipper) ---
def printer():
    svc = {}
    for s, unit in (("klipper", "fusion-klipper"), ("moonraker", "fusion-moonraker"), ("nginx", "nginx")):
        rc, out = ui.run(["systemctl", "is-active", unit], timeout=3)
        svc[s] = out.strip() or "?"
    info = {"state": "", "message": "", "version": ""}
    try:
        with urllib.request.urlopen(MOONRAKER + "/printer/info", timeout=2) as r:
            res = json.load(r).get("result", {})
            info = {"state": res.get("state", ""), "message": (res.get("state_message") or "").strip(),
                    "version": res.get("software_version", "")}
    except Exception as e:
        info["message"] = f"a Moonraker nem válaszol ({e.__class__.__name__})"
    cfg = "/data/printer/config/printer.cfg"
    serial = ""
    for line in _read(cfg).splitlines():
        if line.strip().startswith("serial"):
            serial = line.split(":", 1)[-1].strip()
            break
    return {"services": svc, "klipper": info, "config": cfg if os.path.exists(cfg) else "", "serial": serial,
            "printerPresent": os.path.exists("/dev/fusion/printer")}


# --- Programkezelő: telepítők a szokásos helyeken ---
INSTALLER_EXT = (".exe", ".msi", ".appimage", ".flatpakref", ".flatpak")


def installers():
    """telepítő a szokásos helyeken (saját mappa, Letöltések, /data/import, USB-meghajtók):
    Windows (.exe, .msi), AppImage, Flatpak (.flatpakref, .flatpak)"""
    home = os.path.expanduser("~")
    roots = [home, os.path.join(home, "Letöltések"), os.path.join(home, "Downloads"), "/data/import"] + sorted(glob.glob("/run/media/*"))
    seen, out = set(), []
    for r in roots:
        if not os.path.isdir(r):
            continue
        base_depth = r.rstrip("/").count("/")
        for dirpath, dirs, files in os.walk(r):
            if dirpath.count("/") - base_depth >= 2:
                dirs[:] = []
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("drive_c",)]
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


# --- Rendszer ---
def system():
    rel = ui.fusion_release()
    cmd = _read("/proc/cmdline")
    slot = next((a.split("=", 1)[1] for a in cmd.split() if a.startswith("fusion.slot=")), "?")
    mem = {}
    for line in _read("/proc/meminfo").splitlines():
        k, v = line.split(":", 1)
        mem[k] = int(v.split()[0]) * 1024
    cpu = next((l.split(":", 1)[1].strip() for l in _read("/proc/cpuinfo").splitlines() if l.startswith("model name")), "?")
    ncpu = os.cpu_count() or 0
    up = float(_read("/proc/uptime", "0").split()[0] or 0)
    disks = []
    for mp, name in (("/data", "Adatok (DATA)"),):
        try:
            s = os.statvfs(mp)
            tot, free = s.f_blocks * s.f_frsize, s.f_bavail * s.f_frsize
            disks.append({"name": name, "path": mp, "used": ui.human_size(tot - free), "total": ui.human_size(tot),
                          "pct": round(100.0 * (tot - free) / tot, 1) if tot else 0, "pctText": f"{100.0 * (tot - free) / tot:.1f}".replace(".", ",") if tot else "0"})
        except OSError:
            pass
    rc, lsb = ui.run(["lsblk", "-dno", "NAME,SIZE,MODEL,TRAN"], timeout=3)
    gpu = _read("/run/fusion/hardware/display.summary")
    return {"version": rel.get("FUSION_VERSION", "?"), "milestone": rel.get("FUSION_MILESTONE", ""),
            "image": rel.get("FUSION_IMAGE_ID", ""), "slot": slot, "bootdisk": _read("/run/fusion/boot-disk", "?"),
            "kernel": os.uname().release, "host": os.uname().nodename, "cpu": f"{cpu} ({ncpu} szál)",
            "memTotal": ui.human_size(mem.get("MemTotal", 0)),
            "memUsed": ui.human_size(mem.get("MemTotal", 0) - mem.get("MemAvailable", 0)),
            "memPctText": f"{100.0 * (mem.get('MemTotal', 1) - mem.get('MemAvailable', 0)) / max(1, mem.get('MemTotal', 1)):.1f}".replace(".", ","),
            "memPct": round(100.0 * (mem.get("MemTotal", 1) - mem.get("MemAvailable", 0)) / max(1, mem.get("MemTotal", 1)), 1),
            "uptime": f"{int(up // 86400)} nap {int(up % 86400 // 3600)} óra {int(up % 3600 // 60)} perc" if up >= 86400 else f"{int(up // 3600)} óra {int(up % 3600 // 60)} perc",
            "disks": disks, "blk": [l for l in lsb.splitlines() if l.strip() and not l.startswith(("loop", "zram"))],
            "gpu": gpu}


class Settings(QObject):
    result = pyqtSignal(str, "QVariant")      # címke, adat (a szálból a fő szálra)
    pageRequested = pyqtSignal(str, str)      # másik indítás kérte: oldal, paraméter

    def __init__(self):
        super().__init__()
        self._busy = set()
        self._jobproc = None

    def _async(self, tag, fn, *args):
        if tag in self._busy:
            return
        self._busy.add(tag)

        def work():
            try:
                res = fn(*args)
            except Exception as e:
                res = {"error": str(e)}
            self._busy.discard(tag)
            self.result.emit(tag, res)
        threading.Thread(target=work, daemon=True).start()

    # --- Wi-Fi ---
    @pyqtSlot()
    def wifiRefresh(self):
        def f():
            st = fusion_net.state()
            return {"state": st, "networks": fusion_net.networks(st), "wired": fusion_net.wired()}
        self._async("wifi", f)

    @pyqtSlot()
    def wifiScan(self):
        def f():
            ok, err = fusion_net.scan()
            time.sleep(4)
            st = fusion_net.state()
            return {"state": st, "networks": fusion_net.networks(st), "wired": fusion_net.wired(), "scanned": ok, "error": "" if ok else err}
        self._async("wifi-scan", f)

    @pyqtSlot(str, str)
    def wifiConnect(self, name, passphrase):
        def f():
            ok, out = fusion_net.connect(name, passphrase)
            for _ in range(20):
                st = fusion_net.state()
                if st.get("state") == "connected" and st.get("ssid") == name:
                    break
                time.sleep(1)
            for _ in range(10):               # a DHCP-cím
                if st.get("ip"):
                    break
                time.sleep(1)
                st = fusion_net.state()
            good = st.get("state") == "connected" and st.get("ssid") == name
            return {"ok": good, "name": name, "msg": "" if good else (out or "nem sikerült (rossz jelszó vagy gyenge jel?)")}
        self._async("wifi-connect", f)

    @pyqtSlot()
    def wifiDisconnect(self):
        self._async("wifi-action", lambda: dict(zip(("ok", "msg"), fusion_net.disconnect())))

    @pyqtSlot(str)
    def wifiForget(self, name):
        self._async("wifi-action", lambda: dict(zip(("ok", "msg"), fusion_net.forget(name))))

    # --- Kijelző ---
    @pyqtSlot()
    def displayRefresh(self):
        def f():
            outs, ok = displays()
            return {"outputs": outs, "ok": ok, "summary": _read("/run/fusion/hardware/display.summary")}
        self._async("display", f)

    @pyqtSlot(str, str, result=str)
    def displayApply(self, output, mode):
        if not (SAFE.match(output) and SAFE.match(mode)):
            return "érvénytelen kijelző / mód"
        rc, out = ui.run(["xrandr", "--output", output, "--mode", mode], timeout=15)
        return "" if rc == 0 else out.strip()

    @pyqtSlot(str, str)
    def displaySave(self, output, mode):
        """a munkamenet indításakor ezt futtatja az xinitrc"""
        if SAFE.match(output) and SAFE.match(mode):
            os.makedirs(ui.CONFIG, exist_ok=True)
            with open(DISPLAY_FILE, "w") as f:
                f.write(f"# FusionOS — Beállítások → Kijelző\nxrandr --output {shlex.quote(output)} --mode {shlex.quote(mode)}\n")

    # --- Eszközök ---
    @pyqtSlot()
    def devicesRefresh(self):
        self._async("devices", devices)

    @pyqtSlot(str, str)
    def deviceAssign(self, role, dev):
        self._async("devices-action", lambda: dict(zip(("rc", "msg"), ui.admin("devices-assign", role, dev))))

    @pyqtSlot(str)
    def deviceForget(self, role):
        self._async("devices-action", lambda: dict(zip(("rc", "msg"), ui.admin("devices-forget", role))))

    # --- Nyomtató ---
    @pyqtSlot()
    def printerRefresh(self):
        self._async("printer", printer)

    @pyqtSlot(str)
    def printerService(self, name):
        self._async("printer-action", lambda: dict(zip(("rc", "msg"), ui.admin("service-restart", name, timeout=90))))

    @pyqtSlot()
    def printerFirmwareRestart(self):
        self._async("printer-action", lambda: dict(zip(("rc", "msg"), ui.run(["fusion-printer", "restart"], timeout=20))))

    # --- Programkezelő ---
    @pyqtSlot()
    def programsRefresh(self):
        def f():
            try:
                fp.sync()      # a parancssorból telepített / eltávolított Flatpakok is látszódjanak
            except Exception:
                pass
            roles = []
            for rf in sorted(glob.glob(os.path.join(ROLES_DIR, "*.role"))):
                r = _kv(rf)
                if r.get("role"):
                    roles.append({"role": r["role"], "name": r.get("name", r["role"]), "com": r.get("windows.com", "")})
            have = {p["id"] for p in fp.programs()}
            return {"programs": [fp.info(m) for m in fp.programs()], "roles": roles,
                    "recipes": [{"id": r["id"], "name": r.get("name", r["id"]), "match": r.get("match", "")}
                                for r in fp.recipes() if r["id"] not in have],
                    "installers": installers(), "job": self._job_state()}
        self._async("programs", f)

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

    # a hosszú műveletek (telepítés, eltávolítás, frissítés) külön folyamatban futnak: a Beállítások
    # bezárása nem szakítja meg őket; a végén értesítés jön, a felület a naplót mutatja
    def _job_state(self):
        try:
            pid = int(_read(JOB_PID, "0") or 0)
        except ValueError:
            pid = 0
        if self._jobproc is not None:
            self._jobproc.poll()          # a saját indítású folyamat begyűjtése (ne maradjon zombi)
        stat = _read(f"/proc/{pid}/stat") if pid > 0 else ""
        running = bool(stat) and stat.split(")")[-1].split()[:1] != ["Z"]
        lines = _read(JOB_LOG).splitlines()
        rc = next((int(x[3:]) for x in reversed(lines) if re.match(r"^RC=\d+$", x)), None)
        try:
            age = time.time() - os.path.getmtime(JOB_LOG)
        except OSError:
            age = 1e9
        return {"running": running, "rc": rc, "title": _read(JOB_TITLE), "recent": running or age < 600,
                "lines": [x for x in lines if not x.startswith("RC=")][-14:]}

    def _job(self, title, args):
        if self._job_state()["running"]:
            return "már fut egy művelet — várja meg a végét"
        os.makedirs(os.path.dirname(JOB_LOG), exist_ok=True)
        with open(JOB_TITLE, "w") as f:
            f.write(title)
        script = ('echo $$ > "$1"; shift; log=$1; shift; title=$1; shift; : > "$log"; '
                  'fusion-programs "$@" >> "$log" 2>&1; rc=$?; echo "RC=$rc" >> "$log"; '
                  'last=$(grep -E "^(Telepítve|Eltávolítva|kész|fusion-programs:)" "$log" | tail -n 1); '
                  'if [ $rc -eq 0 ]; then fusion-notify -i package -a Programkezelő "$title: kész" "$last"; '
                  'else fusion-notify -u critical -i package -a Programkezelő "$title: sikertelen" "${last#fusion-programs: }"; fi')
        self._jobproc = subprocess.Popen(["sh", "-c", script, "fusion-programs-job", JOB_PID, JOB_LOG, title] + args,
                                         start_new_session=True, stdin=subprocess.DEVNULL,
                                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(0.2)
        self._job_watch()
        return ""

    def _job_watch(self):
        def work():
            for _ in range(36000):
                st = self._job_state()
                self.result.emit("program-job", st)
                if not st["running"]:
                    break
                time.sleep(0.5)
        threading.Thread(target=work, daemon=True).start()

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

    # --- Hang ---
    @pyqtSlot()
    def soundRefresh(self):
        self._async("sound", fusion_sound.state)

    def _snd(self, fn, *a):
        def work():
            fn(*a)
            return fusion_sound.state()
        threading.Thread(target=lambda: self.result.emit("sound", work()), daemon=True).start()

    @pyqtSlot(int, bool)
    def soundSetVolume(self, v, source):
        self._snd(fusion_sound.set_volume, v, source)

    @pyqtSlot(bool)
    def soundToggleMute(self, source):
        self._snd(fusion_sound.toggle_mute, source)

    @pyqtSlot(str, bool)
    def soundSetDefault(self, name, source):
        self._snd(fusion_sound.set_default, name, source)

    @pyqtSlot(str, str)
    def soundSetPort(self, sink, port):
        self._snd(fusion_sound.set_port, sink, port)

    @pyqtSlot(str)
    def soundTest(self, sink):
        self._async("sound-test", lambda: {"rc": fusion_sound.test_sound(sink), "sink": sink})

    @pyqtSlot()
    def soundRestart(self):
        """a hangkiszolgáló újraindítása (felhasználói szolgáltatások — root nem kell)"""
        self._async("sound-restart", lambda: dict(zip(("rc", "msg"), ui.run(
            ["systemctl", "--user", "restart", "wireplumber", "pipewire", "pipewire-pulse"], timeout=20))))

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

    # --- Asztal ---
    @pyqtSlot(result=str)
    def background(self):
        c = _read(BG_FILE, BG_DEFAULT)
        return c if re.match(r"^#[0-9a-fA-F]{6}$", c) else BG_DEFAULT

    @pyqtSlot(str)
    def setBackground(self, color):
        if re.match(r"^#[0-9a-fA-F]{6}$", color):
            os.makedirs(ui.CONFIG, exist_ok=True)
            with open(BG_FILE, "w") as f:
                f.write(color + "\n")
            ui.run(["xsetroot", "-solid", color], timeout=3)

    @pyqtSlot(result=bool)
    def dashboard(self):
        return _read(os.path.join(ui.CONFIG, "dashboard"), "on") != "off"

    @pyqtSlot(bool)
    def setDashboard(self, on):
        os.makedirs(ui.CONFIG, exist_ok=True)
        with open(os.path.join(ui.CONFIG, "dashboard"), "w") as f:
            f.write("on\n" if on else "off\n")

    # --- Rendszer ---
    @pyqtSlot()
    def systemRefresh(self):
        self._async("system", system)

    @pyqtSlot(str)
    def power(self, action):
        if action in ("reboot", "poweroff"):
            self._async("power", lambda: dict(zip(("rc", "msg"), ui.admin("power", action))))

    @pyqtSlot(str)
    def openTerminal(self, cmd):
        """egy rendszerparancs kimenete terminálablakban (pl. hardverjelentés, napló)"""
        allowed = {"hwinfo": "fusion-hwinfo; echo; glxinfo -B 2>/dev/null",
                   "journal": "journalctl -b -p warning --no-pager | tail -n 200",
                   "printerlog": "fusion-printer log",
                   "fwrcheck": "fwr check",
                   "devices": "fusion-devices"}
        c = allowed.get(cmd)
        if c:
            ui.spawn(["xterm", "-title", "FusionOS — " + cmd, "-e", "sh", "-c", c + "; echo; echo '(Enter: bezárás)'; read x"])

    @pyqtSlot(str)
    def spawn(self, cmd):
        ui.spawn(cmd)
