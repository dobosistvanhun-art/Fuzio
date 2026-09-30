"""FusionOS — Fusion Shell: irányítópult (az asztalon, minden ablak alatt)

Egy pillantásra: lézer, 3D nyomtató (Klipper: állapot, nyomtatás, hőmérsékletek), hálózat,
rendszer (CPU, hőmérséklet, memória, DATA), meghajtók, gyorsindítás.
A lekérdezések külön szálon futnak (a Moonraker nem válaszolhat időben — a felület ne akadjon meg).
A nyomtatás végéről / hibájáról értesítés jön.
Ki-/bekapcsolás: Beállítások → Asztal (~/.config/fusion/dashboard: on | off).
"""
import json
import os
import threading
import time
import urllib.request

from PyQt6.QtCore import QObject, pyqtProperty, pyqtSignal, pyqtSlot

import fusion_net
import fusion_ui as ui

MOONRAKER = os.environ.get("FUSION_MOONRAKER", "http://127.0.0.1:7125")
QUERY = "/printer/objects/query?webhooks&print_stats&display_status&virtual_sdcard&extruder&heater_bed"
DASH_FILE = os.path.join(ui.CONFIG, "dashboard")
BG_FILE = os.path.join(ui.CONFIG, "background")


def _read(path, default=""):
    try:
        with open(path) as f:
            return f.read().strip()
    except OSError:
        return default


def printer_status():
    try:
        with urllib.request.urlopen(MOONRAKER + QUERY, timeout=1.5) as r:
            st = json.load(r)["result"]["status"]
    except Exception:
        return {"online": False, "state": "nem elérhető", "message": "", "printing": False}
    ps = st.get("print_stats", {})
    wh = st.get("webhooks", {})
    prog = st.get("display_status", {}).get("progress") or st.get("virtual_sdcard", {}).get("progress") or 0
    ex, bed = st.get("extruder", {}), st.get("heater_bed", {})
    dur = ps.get("print_duration") or 0
    left = (dur / prog - dur) if prog > 0.01 else 0
    return {"online": True, "klippy": wh.get("state", "?"), "message": (wh.get("state_message") or "").strip().split("\n")[0],
            "state": ps.get("state", "standby"), "file": ps.get("filename", ""), "progress": round(prog * 100, 1),
            "printing": ps.get("state") in ("printing", "paused"),
            "elapsed": time.strftime("%H:%M", time.gmtime(dur)), "left": time.strftime("%H:%M", time.gmtime(left)) if left else "",
            "ext": round(ex.get("temperature", 0)), "extT": round(ex.get("target", 0)),
            "bed": round(bed.get("temperature", 0)), "bedT": round(bed.get("target", 0))}


def system_status():
    mem = {}
    for line in _read("/proc/meminfo").splitlines():
        k, v = line.split(":", 1)
        mem[k] = int(v.split()[0]) * 1024
    tot = mem.get("MemTotal", 1)
    used = tot - mem.get("MemAvailable", 0)
    load = _read("/proc/loadavg", "0 0 0").split()[0]
    ncpu = os.cpu_count() or 1
    temp = ""
    for z in sorted(os.listdir("/sys/class/thermal")) if os.path.isdir("/sys/class/thermal") else []:
        t = _read(f"/sys/class/thermal/{z}/type")
        if t in ("x86_pkg_temp", "coretemp", "acpitz") or not temp:
            v = _read(f"/sys/class/thermal/{z}/temp")
            if v.isdigit() and int(v) > 0:
                temp = f"{int(v) // 1000} °C"
                if t == "x86_pkg_temp":
                    break
    data = {}
    try:
        s = os.statvfs("/data")
        t, f = s.f_blocks * s.f_frsize, s.f_bavail * s.f_frsize
        data = {"free": ui.human_size(f), "total": ui.human_size(t), "pct": round(100.0 * (t - f) / t) if t else 0}
    except OSError:
        pass
    up = float(_read("/proc/uptime", "0").split()[0] or 0)
    return {"version": ui.fusion_version(), "memPct": round(100.0 * used / tot), "mem": f"{ui.human_size(used)} / {ui.human_size(tot)}",
            "cpuPct": min(100, round(100.0 * float(load) / ncpu)), "load": load, "temp": temp, "data": data,
            "uptime": f"{int(up // 3600)} óra {int(up % 3600 // 60)} perc", "wired": fusion_net.wired()}


class Dashboard(QObject):
    changed = pyqtSignal()
    _got = pyqtSignal(str, "QVariant")

    def __init__(self, notify):
        super().__init__()
        self._notify = notify
        self._printer = {"online": False, "state": "…", "printing": False}
        self._system = {}
        self._wired = []
        self._bg = "#16202b"
        self._enabled = True
        self._busy = set()
        self._last_state = None
        self._got.connect(self._on_result)

    @pyqtProperty("QVariant", notify=changed)
    def printer(self):
        return self._printer

    @pyqtProperty("QVariant", notify=changed)
    def system(self):
        return self._system

    @pyqtProperty("QVariant", notify=changed)
    def wired(self):
        return self._wired

    @pyqtProperty(str, notify=changed)
    def bg(self):
        return self._bg

    @property
    def enabled(self):
        return self._enabled

    def _async(self, tag, fn):
        if tag in self._busy:
            return
        self._busy.add(tag)

        def work():
            try:
                r = fn()
            except Exception as e:
                r = {"error": str(e)}
            self._busy.discard(tag)
            self._got.emit(tag, r)
        threading.Thread(target=work, daemon=True).start()

    def _on_result(self, tag, r):
        if tag == "printer":
            old = self._last_state
            new = r.get("state")
            if old in ("printing", "paused") and new == "complete":
                self._notify("printer", "Nyomtatás kész", self._printer.get("file", ""))
            elif old in ("printing", "paused") and new in ("error", "cancelled"):
                self._notify("printer", "Nyomtatás: " + ("hiba" if new == "error" else "megszakítva"), r.get("message", ""), 2)
            self._last_state = new
            self._printer = r
        elif tag == "system":
            self._system = r
            self._wired = r.get("wired", [])
        self.changed.emit()

    def tick_fast(self):
        if self._enabled:
            self._async("printer", printer_status)

    def tick_slow(self):
        bg = _read(BG_FILE, "#16202b")
        if len(bg) == 7 and bg.startswith("#"):
            self._bg = bg
        self._enabled = _read(DASH_FILE, "on") != "off"
        if self._enabled:
            self._async("system", system_status)
        else:
            self.changed.emit()

    @pyqtSlot(str)
    def spawn(self, cmd):
        ui.spawn(cmd)
