"""Fúzió — Beállítások háttere: Rendszer, Indítás (UEFI), Felhasználók, Hibajelentés

A Settings osztály (fusion_settings_backend) ezekből a részekből áll össze; a QML ugyanazt a `settings`
objektumot látja, mint a szétszedés előtt."""
import glob
import json
import os
import re
import time
from PyQt6.QtCore import pyqtSlot
import fusion_ui as ui
from fusion import trash as ftrash
from fusion import users as fusers
from fusion_settings_parts.base import _read


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
            "gpu": gpu, "trash": trash_state(), "lid": lid_mode()}


LID_MODES = ("suspend", "screen-off-ac", "screen-off")


def lid_mode():
    """fedél lecsukásakor (fusion-power; a beállítás a DATA-n, mindenki olvashatja)"""
    for line in _read("/data/system/power.conf").splitlines():
        if line.startswith("lid=") and line[4:].strip() in LID_MODES:
            return line[4:].strip()
    return "suspend"


def trash_state():
    try:
        t = ftrash.state()
    except Exception:
        return {"count": 0, "sizeText": "?", "autoDays": 0, "autoChoices": [0, 7, 30, 90]}
    return dict(t, sizeText=ui.human_size(t["size"]))


class SystemMixin:
    """Rendszer, Indítás (UEFI), Felhasználók, Hibajelentés — a Settings része (a slotok a QML-nek)"""

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

    @pyqtSlot(str)
    def lidSet(self, mode):
        if mode not in LID_MODES:
            return

        def f():
            rc, out = ui.admin("lid", "set", mode, timeout=30)
            r = system()
            if rc != 0:
                r["lidError"] = (out.strip().splitlines() or ["ismeretlen hiba"])[-1].replace("fusion-admin: ", "")
            return r
        self._async("system", f)

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
            ui.spawn(["fusion-terminal", "-t", "Fúzió — " + cmd, "-e", "sh", "-c", c + "; echo; echo '(Enter: bezárás)'; read x"])

    @pyqtSlot(str)
    def spawn(self, cmd):
        ui.spawn(cmd)
