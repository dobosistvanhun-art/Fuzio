"""FusionOS — Beállítások: háttérrész

Oldalak: Wi-Fi, Kijelző, Eszközök, Nyomtató (Klipper), Programok (Windows), Asztal, Rendszer.
A lassú lekérdezések és műveletek (Wi-Fi-keresés, kapcsolódás, szolgáltatás-újraindítás) külön
szálon futnak; az eredmény a „result” jelzéssel jön vissza (címke + adat), a felület nem akad meg.
Rendszerjogot igénylő művelet csak a szűk jogú fusion-admin segéden át történik.
"""
import glob
import json
import os
import re
import shlex
import threading
import time
import urllib.request

from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot

import fusion_apps
import fusion_net
import fusion_ui as ui

ROLES_DIR = os.environ.get("FUSION_DEVICES_ROLES", "/usr/lib/fusion/devices/roles")
DEVICES_DB = "/etc/fusion/devices.conf"
MOONRAKER = "http://127.0.0.1:7125"
BG_FILE = os.path.join(ui.CONFIG, "background")
DISPLAY_FILE = os.path.join(ui.CONFIG, "display.sh")
BG_DEFAULT = "#16202b"
SAFE = re.compile(r"^[A-Za-z0-9_.:+-]+$")


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


# --- Programok (Windows-programok a Fusion Windows Runtime-ban) ---
def installers():
    """telepítő (.exe/.msi) a szokásos helyeken: saját mappa, Letöltések, /data/import, USB-meghajtók"""
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
                if f.lower().endswith((".exe", ".msi")):
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

    # --- Programok ---
    @pyqtSlot()
    def programsRefresh(self):
        self._async("programs", lambda: {"apps": fusion_apps.windows_apps(), "installers": installers()})

    @pyqtSlot(str, str, result=str)
    def programInstall(self, fwr_id, installer):
        if not SAFE.match(fwr_id):
            return "érvénytelen program"
        if not os.path.isfile(installer):
            return "a telepítő nem található: " + installer
        # a telepítő grafikus felülete megjelenik; a végén értesítés
        script = ('fwr install "$1" "$2" > "$HOME/.local/share/fusion/fwr-install.log" 2>&1 '
                  '&& fusion-notify -i laser "Telepítve: $3" "Indítás: Start menü" '
                  '|| fusion-notify -u critical "Telepítés sikertelen: $3" "Napló: ~/.local/share/fusion/fwr-install.log"')
        name = next((a["name"] for a in fusion_apps.windows_apps() if a["fwr"] == fwr_id), fwr_id)
        os.makedirs(os.path.expanduser("~/.local/share/fusion"), exist_ok=True)
        ui.spawn(["sh", "-c", script, "fwr-install", fwr_id, installer, name])
        return ""

    @pyqtSlot(str)
    def programLaunch(self, fwr_id):
        if SAFE.match(fwr_id):
            ui.spawn(["fwr", "launch", fwr_id])

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
