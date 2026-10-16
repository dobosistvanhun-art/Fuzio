"""FusionOS — Beállítások: háttérrész

Oldalak: Wi-Fi, Bluetooth, Kijelző, Eszközök (kamera is), Nyomtatók (CUPS), 3D nyomtató (Klipper), Programkezelő,
Asztal, Rendszer.
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

import fusion_apps  # noqa: F401  (a programlista — a fusion_programs útvonalát is beállítja)
import fusion_net
import fusion_sound
import fusion_drive
import fusion_programs as fp
import fusion_store as store
import fusion_ui as ui
import fusion
from fusion import devices as fdev
from fusion import jobs as fjobs
from fusion import trash as ftrash
from fusion import bluetooth as fbt
from fusion import printers as fprn
from fusion import camera as fcam
from fusion import users as fusers

MOONRAKER = "http://127.0.0.1:7125"
BG_FILE = os.path.join(ui.CONFIG, "background")
DISPLAY_FILE = os.path.join(ui.CONFIG, "display.sh")
BG_DEFAULT = "#16202b"
SAFE = re.compile(r"^[A-Za-z0-9_.:+-]+$")


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
    roles = fdev.roles()        # Fusion API: szerepek, állapot, rögzített azonosító, mely programok érik el (COM)
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
    return {"roles": roles, "serial": serial, "usb": usb, "cameras": fcam.cameras()}


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


def _timing(what, secs):
    """mérés: mennyi ideig tartott egy lista (a hibajelentés és a selftest is látja)"""
    try:
        with open(os.path.join(ui.RUNTIME, "fusion-timing.log"), "a") as f:
            f.write(f"{time.strftime('%H:%M:%S')} {what} {secs:.1f}s\n")
    except OSError:
        pass


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


# --- Rendszerfrissítés (M7): .fupd fájlok a szokásos helyeken, a futó rendszer állapota ---
def fupd_info(path):
    """a frissítőfájl manifestje (csak a tar elejét olvassa)"""
    import tarfile
    try:
        with tarfile.open(path, "r:") as t:
            m = next((x for x in t if os.path.basename(x.name) == "fusion-update.manifest"), None)
            txt = t.extractfile(m).read().decode("utf-8", "replace") if m else ""
    except (tarfile.TarError, OSError):
        return None
    kv = dict(ln.split("=", 1) for ln in txt.splitlines() if "=" in ln and " " not in ln.split("=", 1)[0])
    if "FUSION_VERSION" not in kv:
        return None
    return {"version": kv.get("FUSION_VERSION", "?"), "milestone": kv.get("FUSION_MILESTONE", ""),
            "stamp": kv.get("BUILD_STAMP", ""),
            # T3: telepítő pendrive is készíthető belőle (a telepítő UKI-ja és az ESP-fájlok benne vannak)
            "media": bool(re.search(r"(?m)^uki-installer\.efi ", txt)) and bool(re.search(r"(?m)^esp-static\.tar ", txt))}


def update_files():
    home = os.path.expanduser("~")
    # a saját build kimenete is (Fejlesztődoboz: …/fusionos/build/out/release — a mappa mélyebben van, mint
    # amit a saját mappa bejárása elér; 0.0.48: ~/Projektek/fusionos, ~/Fusion/fusionos stb.)
    builds = sorted(set(glob.glob(os.path.join(home, "*", "build", "out", "release"))
                        + glob.glob(os.path.join(home, "*", "*", "build", "out", "release"))))
    roots = ([os.path.join(home, "Letöltések"), os.path.join(home, "Downloads"), home, "/data/import"] + builds
             + sorted(glob.glob(fusion.MEDIA + "/*")))
    seen, out = set(), []
    for r in roots:
        if not os.path.isdir(r):
            continue
        base = r.rstrip("/").count("/")
        for dirpath, dirs, files in os.walk(r):
            if dirpath.count("/") - base >= 2:
                dirs[:] = []
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("drive_c", "GoogleDrive")
                       and not os.path.ismount(os.path.join(dirpath, d))]
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


def update_state():
    rc, out = ui.admin("update-status", "--json", timeout=20)
    try:
        st = json.loads(out) if rc == 0 else {}
    except ValueError:
        st = {}
    rel = ui.fusion_release()
    running = next((e for e in st.get("entries", []) if e.get("running")), None)
    stamp = running["name"].split("-")[-2] if running and running["name"].count("-") >= 4 else ""
    files = update_files()
    for f in files:
        f["newer"] = bool(f.get("stamp")) and (not stamp.isdigit() or f["stamp"] > stamp)
    return {"version": rel.get("FUSION_VERSION", "?"), "milestone": rel.get("FUSION_MILESTONE", ""),
            "slot": st.get("slot", _read("/run/fusion/slot", "?")), "state": st.get("state", ""),
            "entries": st.get("entries", []), "error": "" if rc == 0 else out.strip()[:200], "files": files,
            "stamp": stamp}


# --- Indítás (UEFI-bejegyzések) ---
def boot_state():
    rc, out = ui.admin("boot", "list", "--json", timeout=60)
    try:
        d = json.loads(out[out.index("{"):])
    except ValueError:
        return {"error": (out.strip().splitlines() or ["ismeretlen hiba"])[-1].replace("fusion-admin: ", "")
                .replace("fusion-bootentries: ", ""), "entries": []}
    d["error"] = ""
    return d


# --- Mentés (T3) és telepítő pendrive ---
def backup_state():
    rc, out = ui.admin("backup", "list", timeout=60)
    try:
        d = json.loads(out[out.index("{"):])
    except ValueError:
        return {"error": (out.strip().splitlines() or ["ismeretlen hiba"])[-1].replace("fusion-admin: ", ""),
                "targets": [], "backups": [], "dataUsed": 0}
    d["error"] = ""
    d["dataUsedText"] = ui.human_size(d.get("dataUsed", 0))
    for t in d["targets"]:
        t["freeText"] = ui.human_size(t["free"])
    for b in d["backups"]:
        b["sizeText"] = ui.human_size(b.get("bytes", 0))
        b["when"] = b.get("date", "")[:16].replace("T", " ")
    return d


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


# --- Hibajelentés ---
def report_dir():
    m = re.search(r'^XDG_DOWNLOAD_DIR="([^"]+)"', _read(os.path.expanduser("~/.config/user-dirs.dirs")), re.M)
    return m.group(1).replace("$HOME", os.path.expanduser("~")) if m else os.path.expanduser("~/Letöltések")


def report_files():
    out = []
    for p in sorted(glob.glob(os.path.join(report_dir(), "fusion-hibajelentes-*.txt")), reverse=True)[:10]:
        try:
            st = os.stat(p)
        except OSError:
            continue
        out.append({"path": p, "name": os.path.basename(p), "size": ui.human_size(st.st_size),
                    "time": time.strftime("%Y-%m-%d %H:%M", time.localtime(st.st_mtime))})
    return out


def report_preview(path, n=400):
    if not path.startswith(report_dir() + "/") or not os.path.basename(path).startswith("fusion-hibajelentes-"):
        return ""
    return "\n".join(_read(path).splitlines()[:n])


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
            "gpu": gpu, "trash": trash_state()}


def trash_state():
    try:
        t = ftrash.state()
    except Exception:
        return {"count": 0, "sizeText": "?", "autoDays": 0, "autoChoices": [0, 7, 30, 90]}
    return dict(t, sizeText=ui.human_size(t["size"]))


class Settings(QObject):
    result = pyqtSignal(str, "QVariant")      # címke, adat (a szálból a fő szálra)
    pageRequested = pyqtSignal(str, str)      # másik indítás kérte: oldal, paraméter

    def __init__(self):
        super().__init__()
        self._busy = set()
        self._jobprocs = {}

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

    # --- Felület rajzolása (0.0.32): grafikus kártya (OpenGL) vagy szoftveres ---
    @pyqtSlot(result="QVariant")
    def renderState(self):
        return {"mode": ui.render_mode(), "forced": ui.render_forced()}

    @pyqtSlot(str, result=str)
    def renderSet(self, mode):
        if mode not in ("gpu", "software"):
            return "érvénytelen mód"
        try:
            os.makedirs(ui.CONFIG, exist_ok=True)
            with open(ui.RENDER_FILE + ".tmp", "w") as f:
                f.write(mode + "\n")
            os.replace(ui.RENDER_FILE + ".tmp", ui.RENDER_FILE)
        except OSError as e:
            return f"nem menthető: {e}"
        # a Fusion Shell (panel, Start menü, asztal) azonnal az új móddal indul újra; a többi Fusion-program a
        # következő megnyitáskor
        ui.spawn(["fusion-shell", "restart"])
        return ""

    # --- Eszközök ---
    @pyqtSlot()
    def devicesRefresh(self):
        self._async("devices", devices)

    @pyqtSlot(str, str)
    def deviceAssign(self, role, dev):
        self._async("devices-action", lambda: dict(zip(("rc", "msg"), fdev.assign(role, dev))))

    @pyqtSlot(str)
    def deviceForget(self, role):
        self._async("devices-action", lambda: dict(zip(("rc", "msg"), fdev.forget(role))))

    @pyqtSlot()
    def cameraOpen(self):
        ui.spawn(["fusion-camera"])

    # --- Bluetooth ---
    @pyqtSlot()
    def btRefresh(self):
        def f():
            a = fbt.adapter()
            return {"adapter": a, "devices": fbt.devices() if a["present"] else []}
        self._async("bt", f)

    def _bt(self, tag, fn, *a):
        def f():
            ok, msg = fn(*a)
            return {"ok": ok, "msg": msg}
        self._async(tag, f)

    @pyqtSlot(bool)
    def btPower(self, on):
        self._bt("bt-action", fbt.power, on)

    @pyqtSlot()
    def btScan(self):
        self._bt("bt-scan", fbt.scan, 12)

    @pyqtSlot(str)
    def btPair(self, addr):
        def ev(kind, code):
            self.result.emit("bt-code", {"kind": kind, "code": code, "address": addr})
        self._bt("bt-pair", fbt.pair, addr, ev)

    @pyqtSlot(str)
    def btConnect(self, addr):
        self._bt("bt-action", fbt.connect, addr)

    @pyqtSlot(str)
    def btDisconnect(self, addr):
        self._bt("bt-action", fbt.disconnect, addr)

    @pyqtSlot(str)
    def btRemove(self, addr):
        self._bt("bt-action", fbt.remove, addr)

    # --- Felhasználók ---
    @pyqtSlot()
    def usersRefresh(self):
        self._async("users", fusers.state)

    def _usr(self, fn, *a):
        def f():
            ok, msg = fn(*a)
            return {"ok": ok, "msg": msg}
        self._async("users-action", f)

    @pyqtSlot(str, str, str, bool)
    def userAdd(self, name, fullname, password, admin):
        self._usr(fusers.add, name, fullname, password, admin)

    @pyqtSlot(str, str, str)
    def userPasswd(self, name, old, new):
        self._usr(fusers.passwd, name, old, new)

    @pyqtSlot(str, bool)
    def userDelete(self, name, remove_home):
        self._usr(fusers.delete, name, remove_home)

    @pyqtSlot(str, bool)
    def userAdmin(self, name, on):
        self._usr(fusers.set_admin, name, on)

    @pyqtSlot(str)
    def userAutologin(self, name):
        self._usr(fusers.autologin, name)

    # --- Nyomtatók (CUPS) ---
    @pyqtSlot()
    def prnRefresh(self):
        self._async("prn", lambda: {"service": fprn.service(), "printers": fprn.printers(), "jobs": fprn.jobs()})

    @pyqtSlot()
    def prnDiscover(self):
        self._async("prn-discover", lambda: {"devices": fprn.discover()})

    @pyqtSlot(str)
    def prnDrivers(self, model):
        self._async("prn-drivers", lambda: {"model": model, "drivers": fprn.drivers(model)})

    @pyqtSlot(str, str, str, str)
    def prnAdd(self, uri, model, info, ppd):
        def f():
            ok, msg, name = fprn.add(uri, model, ppd=ppd, info=info)
            return {"ok": ok, "msg": msg, "name": name, "uri": uri, "model": model}
        self._async("prn-add", f)

    @pyqtSlot()
    def prnAddPdf(self):
        def f():
            ok, msg, name = fprn.add_pdf()
            return {"ok": ok, "msg": msg, "name": name}
        self._async("prn-add", f)

    def _prn(self, fn, *a):
        def f():
            r = fn(*a)
            return {"ok": r[0], "msg": r[1]}
        self._async("prn-action", f)

    @pyqtSlot(str)
    def prnRemove(self, name):
        self._prn(fprn.remove, name)

    @pyqtSlot(str)
    def prnDefault(self, name):
        self._prn(fprn.set_default, name)

    @pyqtSlot(str)
    def prnEnable(self, name):
        self._prn(fprn.enable, name)

    @pyqtSlot(str)
    def prnTest(self, name):
        def f():
            ok, msg, job = fprn.test_page(name)
            return {"ok": ok, "msg": msg if not ok else f"Próbaoldal elküldve ({job}).", "test": True}
        self._async("prn-action", f)

    @pyqtSlot(str)
    def prnCancel(self, job):
        self._prn(fprn.cancel, job)

    @pyqtSlot(str)
    def prnCancelAll(self, name):
        self._prn(fprn.cancel_all, name)

    @pyqtSlot()
    def prnWeb(self):
        ui.spawn(["xdg-open", "http://localhost:631/"])

    @pyqtSlot(str)
    def serviceRestart(self, name):
        if name in ("bluetooth", "cups"):
            self._async("service-restart", lambda: dict(zip(("rc", "msg"), ui.admin("service-restart", name))))

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

    # a hosszú műveletek (telepítés, eltávolítás, frissítés) külön folyamatban futnak: a Beállítások
    # bezárása nem szakítja meg őket; a végén értesítés jön, a felület a naplót mutatja
    # (a Fusion API feladat-protokollja: fusion.jobs — az állapot a $XDG_RUNTIME_DIR/fusion/jobs alatt)
    def _job_state(self, kind="programs"):
        for pr in list(self._jobprocs.values()):
            pr.poll()                     # a saját indítású futtató begyűjtése (ne maradjon zombi)
        return fjobs.state(kind)

    def _job(self, title, args, kind="programs", cmd=("fusion-programs",), app="Programkezelő", icon="package",
             okpat="^(Telepítve|Eltávolítva|kész|fusion-programs:)"):
        err, pr = fjobs.start(kind, title, list(cmd) + list(args), app=app, icon=icon, okpat=okpat)
        if err:
            return err
        self._jobprocs[kind] = pr
        time.sleep(0.2)
        self._job_watch(kind)
        return ""

    def _job_watch(self, kind="programs"):
        tag = "program-job" if kind == "programs" else f"{kind}-job"

        def work():
            for _ in range(36000):
                st = self._job_state(kind)
                self.result.emit(tag, st)
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

    # --- Google Drive ---
    @pyqtSlot()
    def driveRefresh(self):
        def f():
            st = fusion_drive.status(with_account=True)
            st["cacheText"] = ui.human_size(fusion_drive.cache_size())
            acc = st.get("account") or {}
            st["quotaText"] = (ui.human_size(acc["used"]) + " / " + ui.human_size(acc["total"])) if acc.get("total") else \
                (ui.human_size(acc["used"]) + " használatban" if acc.get("used") else "")
            return st
        self._async("drive", f)

    @pyqtSlot()
    def driveConnect(self):
        if getattr(self, "_login", None) and self._login.proc and self._login.proc.poll() is None:
            return
        self._login = fusion_drive.Login(lambda kind, text: self.result.emit("drive-login", {"kind": kind, "text": text}))
        self._login.start()

    @pyqtSlot()
    def driveCancel(self):
        if getattr(self, "_login", None):
            self._login.cancel()

    @pyqtSlot(str)
    def driveOpenUrl(self, url):
        if url.startswith("http://127.0.0.1:"):
            fusion_drive.open_browser(url)

    @pyqtSlot()
    def driveDisconnect(self):
        self._async("drive-action", lambda: {"ok": fusion_drive.disconnect(), "msg": "A Google Drive leválasztva (a felhőben lévő fájlok érintetlenek)."})

    @pyqtSlot(bool)
    def driveMount(self, on):
        def f():
            if on:
                ok, msg = fusion_drive.start()
                return {"ok": ok, "msg": "Csatolva: " + msg if ok else "Hiba: " + msg}
            return {"ok": fusion_drive.stop(), "msg": "A csatolás megszüntetve."}
        self._async("drive-action", f)

    @pyqtSlot(bool)
    def driveAutostart(self, on):
        self._async("drive-action", lambda: {"ok": fusion_drive.set_autostart(on),
                                              "msg": "Bejelentkezéskor " + ("csatolódik." if on else "nem csatolódik.")})

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

    # --- Indítás: UEFI-bejegyzések (fusion-bootentries) ---
    @pyqtSlot()
    def bootRefresh(self):
        self._async("boot", boot_state)

    @pyqtSlot(str, str, str)
    def bootAction(self, action, num, confirm):
        if action not in ("first", "next", "delete") or not re.match(r"^[0-9A-Fa-f]{4}$", num):
            return
        args = ["boot", action, num] + ([confirm] if action == "delete" else [])

        def f():
            rc, out = ui.admin(*args, timeout=60)
            return {"ok": rc == 0, "msg": (out.strip().splitlines() or [""])[-1].replace("fusion-bootentries: ", "").replace("KÉSZ: ", "")}
        self._async("boot-action", f)

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

    # --- Rendszerfrissítés ---
    @pyqtSlot()
    def updateRefresh(self):
        def f():
            d = update_state()
            d["job"] = self._job_state("update")
            return d
        self._async("update", f)

    @pyqtSlot(str, result=str)
    def updateInstall(self, path):
        if not path.endswith(".fupd") or not os.path.isfile(path):
            return "nem .fupd frissítőfájl: " + path
        info = fupd_info(path) or {}
        return self._job("Rendszerfrissítés: FusionOS " + info.get("version", "?"), [path], kind="update",
                         cmd=("sudo", "-n", ui.ADMIN, "update-apply"), app="Rendszerfrissítés", icon="update",
                         okpat="^KÉSZ:")

    @pyqtSlot()
    def updateJobWatch(self):
        if self._job_state("update")["running"]:
            self._job_watch("update")

    @pyqtSlot()
    def updateReboot(self):
        self._async("power", lambda: dict(zip(("rc", "msg"), ui.admin("update-reboot"))))

    # --- Mentés (T3) ---
    @pyqtSlot()
    def backupRefresh(self):
        self._async("backup", lambda: dict(backup_state(), job=self._job_state("backup")))

    @pyqtSlot(str, result=str)
    def backupCreate(self, mountpoint):
        return self._job("DATA mentése", [mountpoint], kind="backup", cmd=("sudo", "-n", ui.ADMIN, "backup", "create"),
                         app="Mentés", icon="archive-in", okpat="^kész")

    @pyqtSlot()
    def backupJobWatch(self):
        if self._job_state("backup")["running"]:
            self._job_watch("backup")

    # --- telepítő pendrive a Rendszerfrissítés oldalról (T3) ---
    @pyqtSlot()
    def mediaDisks(self):
        self._async("media-disks", lambda: {"disks": media_disks()})

    @pyqtSlot(str, str, str, result=str)
    def mediaCreate(self, fupd, disk, confirm):
        info = fupd_info(fupd) or {}
        if not info.get("media"):
            return "ebből a .fupd-ből nem készíthető telepítő (0.0.29 előtti csomag)"
        return self._job("Telepítő pendrive: FusionOS " + info.get("version", "?"), [fupd, disk, confirm], kind="media",
                         cmd=("sudo", "-n", ui.ADMIN, "installer-media"), app="Rendszerfrissítés", icon="drive-usb",
                         okpat="^KÉSZ:")

    @pyqtSlot()
    def mediaJobWatch(self):
        if self._job_state("media")["running"]:
            self._job_watch("media")

    # --- Hibajelentés ---
    @pyqtSlot()
    def reportRefresh(self):
        self._async("report", lambda: {"files": report_files(), "dir": report_dir(), "job": self._job_state("report")})

    @pyqtSlot(str, result=str)
    def reportCreate(self, desc):
        return self._job("Hibajelentés", ["-d", desc.strip()[:4000]] if desc.strip() else [], kind="report",
                         cmd=("fusion-report",), app="Hibajelentés", icon="report", okpat="^kész")

    @pyqtSlot()
    def reportJobWatch(self):
        if self._job_state("report")["running"]:
            self._job_watch("report")

    @pyqtSlot(str, result=str)
    def reportPreview(self, path):
        return report_preview(path)

    @pyqtSlot(str)
    def reportShow(self, path):
        """a jelentés mappája a Fájlkezelőben"""
        ui.spawn(["fusion-files", os.path.dirname(path)])

    # --- Rendszer ---
    @pyqtSlot()
    def systemRefresh(self):
        self._async("system", system)

    @pyqtSlot(int, result=str)
    def trashSetAuto(self, days):
        try:
            ftrash.set_auto_days(days)
        except (ValueError, OSError) as e:
            return str(e)
        self._async("system", system)
        return ""

    @pyqtSlot()
    def trashEmpty(self):
        self._async("trash-empty", lambda: {"removed": ftrash.empty(), **system()})

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
                   "devices": "fusion-devices",
                   "dev-install-node": "fusion-dev install node", "dev-update-node": "fusion-dev update node",
                   "dev-remove-node": "fusion-dev remove node", "dev-install-wrangler": "fusion-dev install wrangler",
                   "dev-update-wrangler": "fusion-dev update wrangler", "dev-remove-wrangler": "fusion-dev remove wrangler",
                   "wrangler-login": "wrangler login && wrangler whoami"}
        c = allowed.get(cmd)
        if c:
            ui.spawn(["fusion-terminal", "-t", "FusionOS — " + cmd, "-e", "sh", "-c", c + "; echo; echo '(Enter: bezárás)'; read x"])

    @pyqtSlot(str)
    def spawn(self, cmd):
        ui.spawn(cmd)
