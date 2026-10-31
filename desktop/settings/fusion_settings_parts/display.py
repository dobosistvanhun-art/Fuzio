"""Fúzió — Beállítások háttere: Kijelző, a felület rajzolása, Asztal

A Settings osztály (fusion_settings_backend) ezekből a részekből áll össze; a QML ugyanazt a `settings`
objektumot látja, mint a szétszedés előtt."""
import os
import re
import shlex
from PyQt6.QtCore import pyqtSlot
import fusion_ui as ui
from fusion_settings_parts.base import _read, SAFE

BG_FILE = os.path.join(ui.CONFIG, "background")
DISPLAY_FILE = os.path.join(ui.CONFIG, "display.sh")
BG_DEFAULT = "#16202b"


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


class DisplayMixin:
    """Kijelző, a felület rajzolása, Asztal — a Settings része (a slotok a QML-nek)"""

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
                f.write(f"# Fúzió — Beállítások → Kijelző\nxrandr --output {shlex.quote(output)} --mode {shlex.quote(mode)}\n")

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
        # a Fúzió Shell (panel, Start menü, asztal) azonnal az új móddal indul újra; a többi Fúzió-program a
        # következő megnyitáskor
        ui.spawn(["fusion-shell", "restart"])
        return ""

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
