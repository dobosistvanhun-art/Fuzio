#!/usr/bin/python3
"""FusionOS — Fusion Telepítő (a telepítő pendrive-on, telepítő módban indul a Fusion Shell helyett)

    fusion-installer              az ablak
    fusion-installer --selftest   önteszt: a csomag, a lemezlista (sudo fusion-admin install list), a felület
"""
import json
import os
import re
import subprocess
import sys
import threading

HERE = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))
import fusion_ui as ui  # noqa: E402
from PyQt6.QtCore import QObject, QUrl, pyqtProperty, pyqtSignal, pyqtSlot  # noqa: E402

KIND = {"usb": "USB", "sd": "SD-kártya", "nvme": "NVMe SSD", "ssd": "SSD", "hdd": "merevlemez"}


def admin_cmd(*args):
    return ["sudo", "-n", ui.ADMIN] + [str(a) for a in args]


def load_list():
    rc, out = ui.run(admin_cmd("install", "list"), timeout=180)
    try:
        d = json.loads(out[out.index("{"):])
    except ValueError:
        return {"error": (out.strip().splitlines() or ["ismeretlen hiba"])[-1].replace("fusion-admin: ", ""),
                "disks": [], "payload": {}, "machine": {}}
    for x in d.get("disks", []):
        x["sizeText"] = ui.human_size(x["size"])
        x["kindText"] = KIND.get(x["kind"], x["kind"])
        f = x.get("fusion")
        if f:
            x["content"] = "FusionOS" + (" " + f["version"] if f.get("version") else "") + \
                (f" — DATA: {ui.human_size(f['dataUsed'])} foglalt" if f.get("dataUsed") is not None else "")
        elif x.get("otheros"):
            x["content"] = "másik operációs rendszer (EFI-partíció) — pl. Linux Mint vagy Windows"
        elif x["parts"]:
            x["content"] = ", ".join(f"{p['label'] or p['name']} ({p['fstype'] or '?'}, {ui.human_size(p['size'])})"
                                     for p in x["parts"][:4]) + (" …" if len(x["parts"]) > 4 else "")
        else:
            x["content"] = "üres"
    for b in d.get("backups", []):
        b["sizeText"] = ui.human_size(b.get("bytes", 0))
        b["dataText"] = ui.human_size(b.get("dataUsed", 0))
        b["when"] = b.get("date", "")[:16].replace("T", " ")
        b["where"] = b.get("volume", "").replace("/run/media/", "")
    m = d.get("machine", {})
    if m.get("memory"):
        m["memoryText"] = ui.human_size(m["memory"])
    return d


class Backend(QObject):
    changed = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._data = {"disks": [], "payload": {}, "machine": {}, "error": ""}
        self._loading = False
        self._state, self._step, self._pct, self._log, self._result = "", "", 0, [], ""
        self.refresh()

    def _load(self):
        d = load_list()
        self._data, self._loading = d, False
        self.changed.emit()

    @pyqtSlot()
    def refresh(self):
        if self._loading:
            return
        self._loading = True
        self.changed.emit()
        threading.Thread(target=self._load, daemon=True).start()

    @pyqtProperty("QVariant", notify=changed)
    def data(self):
        return self._data

    @pyqtProperty(bool, notify=changed)
    def loading(self):
        return self._loading

    @pyqtProperty(str, notify=changed)
    def state(self):          # "" | running | done | failed
        return self._state

    @pyqtProperty(str, notify=changed)
    def stepText(self):
        return self._step

    @pyqtProperty(int, notify=changed)
    def percent(self):
        return self._pct

    @pyqtProperty("QVariant", notify=changed)
    def log(self):
        return self._log

    @pyqtProperty(str, notify=changed)
    def result(self):
        return self._result

    @pyqtSlot(str, str, str, str, bool)
    def install(self, disk, mode, confirm, restore, wifi):
        if self._state == "running":
            return
        self._state, self._step, self._pct, self._log, self._result = "running", "indítás…", 0, [], ""
        self.changed.emit()

        def work():
            ok, last = False, ""
            try:
                extra = (["--restore", restore] if restore else []) + (["--wifi"] if wifi else [])
                p = subprocess.Popen(admin_cmd("install", "run", disk, mode, confirm, *extra), stdout=subprocess.PIPE,
                                     stderr=subprocess.STDOUT, text=True, errors="replace", stdin=subprocess.DEVNULL)
                for line in p.stdout:
                    line = line.rstrip()
                    if not line:
                        continue
                    m = re.match(r"^PROGRESS (\d+)$", line)
                    if m:
                        self._pct = int(m.group(1))
                    else:
                        if line.startswith("LÉPÉS "):
                            self._step = line.split(": ", 1)[-1]
                        line = line.replace("fusion-admin: ", "").replace("fusion-install: ", "HIBA: ")
                        self._log = (self._log + [line])[-200:]
                        last = line
                    self.changed.emit()
                ok = p.wait() == 0
            except OSError as e:
                last = f"HIBA: {e}"
                self._log.append(last)
            self._state = "done" if ok else "failed"
            self._result = last
            self.changed.emit()
        threading.Thread(target=work, daemon=True).start()

    @pyqtSlot(result=str)
    def report(self):
        rc, out = ui.run(admin_cmd("install", "report"), timeout=360)
        return out.strip().replace("fusion-admin: ", "").replace("fusion-install: ", "") or ("kész" if rc == 0 else "hiba")

    @pyqtSlot(str)
    def power(self, action):
        if action in ("reboot", "poweroff"):
            ui.run(admin_cmd("power", action), timeout=20)

    @pyqtSlot(str)
    def tool(self, name):
        cmd = {"disks": ["fusion-disks"], "terminal": ["xterm"], "tasks": ["fusion-tasks"],
               "wifi": ["fusion-settings", "wifi"]}.get(name)
        if cmd:
            ui.spawn(cmd)


def selftest():
    ok = True

    def check(name, cond, extra=""):
        nonlocal ok
        print(f"FUSION-INSTALLER: {name} {'ok' if cond else 'HIBA'}{(' ' + extra) if extra else ''}", flush=True)
        ok = ok and bool(cond)

    d = load_list()
    pay = d.get("payload") or {}
    check("PAYLOAD", not pay.get("error") and pay.get("version"), pay.get("error") or f"{pay.get('name')} ({pay.get('version')})")
    el = [x["name"] for x in d.get("disks", []) if x["eligible"]]
    sysd = [x["name"] for x in d.get("disks", []) if not x["eligible"] and x["reason"] == "ez a telepítő pendrive"]
    check("DISKS", d.get("disks") and len(sysd) == 1, f"választható={','.join(el) or '-'} telepítő={','.join(sysd) or '-'} {d.get('error', '')}")
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    app, engine = ui.create_app("fusion-installer", "FusionOS telepítő", "disks")
    be = Backend()
    engine.rootContext().setContextProperty("inst", be)
    engine.load(QUrl.fromLocalFile(os.path.join(HERE, "qml", "Installer.qml")))
    check("QML", bool(engine.rootObjects()))
    print(f"FUSION-INSTALLER: RESULT {'ok' if ok else 'HIBA'}", flush=True)
    return 0 if ok else 1


def main():
    if sys.argv[1:2] == ["--selftest"]:
        return selftest()
    app, engine = ui.create_app("fusion-installer", "FusionOS telepítő", "disks")
    be = Backend()
    engine.rootContext().setContextProperty("inst", be)
    ui.load(engine, os.path.join(HERE, "qml", "Installer.qml"))
    app._keep = [be]
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
