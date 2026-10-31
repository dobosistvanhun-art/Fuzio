"""Fúzió — Beállítások háttere: Eszközök, touchpad, hang, nyomtatók (CUPS), 3D nyomtató (Klipper)

A Settings osztály (fusion_settings_backend) ezekből a részekből áll össze; a QML ugyanazt a `settings`
objektumot látja, mint a szétszedés előtt."""
import glob
import json
import os
import re
import threading
import urllib.request
from PyQt6.QtCore import pyqtSlot
import fusion_sound
import fusion_ui as ui
from fusion import devices as fdev
from fusion import touchpad as ftp
from fusion import printers as fprn
from fusion import camera as fcam
from fusion_settings_parts.base import _read

MOONRAKER = "http://127.0.0.1:7125"


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
    roles = fdev.roles()        # Fúzió API: szerepek, állapot, rögzített azonosító, mely programok érik el (COM)
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


class DevicesMixin:
    """Eszközök, touchpad, hang, nyomtatók (CUPS), 3D nyomtató (Klipper) — a Settings része (a slotok a QML-nek)"""

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

    # --- Touchpad (0.0.53) ---
    @pyqtSlot()
    def touchpadRefresh(self):
        self._async("touchpad", ftp.status)

    @pyqtSlot(str, "QVariant")
    def touchpadSet(self, key, value):
        def f():
            if key not in ftp.DEFAULTS:
                return {"ok": False, "error": f"ismeretlen kulcs: {key}"}
            try:
                s = ftp.save({key: value})
            except (OSError, ValueError, TypeError) as e:
                return {"ok": False, "error": str(e)}
            errs = ftp.apply(s)
            st = ftp.status()
            if errs:
                st["error"] = "; ".join(errs)
            return st
        self._async("touchpad", f)

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
