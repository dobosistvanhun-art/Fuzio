#!/usr/bin/python3
"""Fúzió — Lézer állapot (M8d): az első Fúzió-natív próba-program, KIZÁRÓLAG a Fúzió API-n át.

Bizonyítja, hogy az API elég egy valódi programhoz: a szerep állapota (fusion.devices), melyik program melyik
COM-porton éri el (fusion.devices / fusion.programs), a program indítása (fusion.programs), a felület
(fusion_ui + FusionUI QML). Általános: bármely eszközszerepre működik (fusion-laser printer).

    fusion-laser [szerep]       az ablak (alapértelmezés: laser; ha már fut: előre hozza)
    fusion-laser --selftest     önteszt: az API-hívások és a felület betöltése
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))
from fusion import devices, programs  # noqa: E402  — a Fúzió API
import fusion_ui as ui  # noqa: E402               — a Fúzió API felület-része (Qt)
from PyQt6.QtCore import QObject, QTimer, pyqtProperty, pyqtSignal, pyqtSlot  # noqa: E402


def key_text(key):
    """a rögzített azonosító emberi olvasásra"""
    if key.startswith("serial:"):
        p = key.split(":", 3)
        return f"sorozatszám alapján ({p[3] if len(p) > 3 else '?'}; {p[1]}:{p[2]})" if len(p) > 2 else key
    if key.startswith("path:"):
        p = key.split(":", 3)
        port = p[3].rsplit("-usb-", 1)[-1].split(":")[1] if len(p) > 3 and "-usb-" in p[3] and ":" in p[3].rsplit("-usb-", 1)[-1] else "?"
        return f"a fizikai USB-port alapján (port {port}; {p[1]}:{p[2]})" if len(p) > 2 else key
    return "még nincs rögzítve (az első bedugott illeszkedő eszköz lesz az)" if not key else key


def role_state(role):
    r = next((x for x in devices.roles() if x["role"] == role), None)
    if not r:
        return {"known": False, "role": role, "name": role}
    return {"known": True, "role": role, "name": r["name"], "present": r["present"], "dev": r["dev"],
            "key": r["key"], "keyText": key_text(r["key"]), "comSuggested": r["com"],
            "programs": [dict(p, installed=programs.info(p["id"]) is not None) for p in r["programs"]]}


class Backend(QObject):
    changed = pyqtSignal()
    message = pyqtSignal(str, bool)

    def __init__(self, role):
        super().__init__()
        self._role = role
        self._state = role_state(role)
        self._sig = self._signature()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._poll)
        self._timer.start(2000)

    def _signature(self):
        return json.dumps([(p["role"], p["present"], p["dev"]) for p in devices.present()])

    def _poll(self):
        sig = self._signature()
        if sig != self._sig:                  # be- vagy kihúzták: teljes frissítés
            was = self._state.get("present")
            self._sig = sig
            self.refresh()
            now = self._state.get("present")
            if was is not None and now != was:
                self.message.emit(f"{self._state['name']}: " + ("csatlakoztatva" if now else "kihúzva"), not now)

    @pyqtSlot()
    def refresh(self):
        self._state = role_state(self._role)
        self.changed.emit()

    @pyqtProperty("QVariant", notify=changed)
    def state(self):
        return self._state

    @pyqtSlot(str)
    def launch(self, pid):
        try:
            programs.run(pid)
            self.message.emit("Indul: " + ((programs.info(pid) or {}).get("name") or pid), False)
        except (programs.ProgramError, OSError) as e:
            self.message.emit(str(e), True)

    @pyqtSlot()
    def openSettings(self):
        ui.spawn(["fusion-settings", "devices"])

    @pyqtSlot()
    def openPrograms(self):
        ui.spawn(["fusion-settings", "programs"])


def selftest():
    ok = True

    def check(name, cond, extra=""):
        nonlocal ok
        ok = ok and bool(cond)
        print(f"FUSION-LASER: {name} {'ok' if cond else 'HIBA'} {extra}".rstrip())
    st = role_state("laser")
    check("STATE", st.get("known"), f"present={st.get('present')} dev={st.get('dev') or '-'} programs="
          + ",".join(f"{p['id']}:{p['com']}" for p in st.get("programs", [])))
    check("KEYTEXT", key_text("path:1a86:7523:pci-0000:00:14.0-usb-0:2:1.0").startswith("a fizikai USB-port alapján (port 2;"))
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app, engine = ui.create_app("fusion-laser", "Lézer állapot", "laser")
    be = Backend("laser")
    engine.rootContext().setContextProperty("laser", be)
    from PyQt6.QtCore import QUrl
    engine.load(QUrl.fromLocalFile(os.path.join(HERE, "qml", "Laser.qml")))
    check("QML", bool(engine.rootObjects()))
    return 0 if ok else 1


def main():
    args = sys.argv[1:]
    if args[:1] == ["--selftest"]:
        return selftest()
    role = args[0] if args else "laser"
    from PyQt6.QtNetwork import QLocalServer, QLocalSocket
    name = f"fusion-laser-{role}-{os.getuid()}"
    sock = QLocalSocket()
    sock.connectToServer(name)
    if sock.waitForConnected(300):          # már fut: előre hozzuk
        sock.write(b'{"raise": true}\n')
        sock.waitForBytesWritten(500)
        return 0
    app, engine = ui.create_app("fusion-laser", "Lézer állapot", "laser")
    be = Backend(role)
    server = QLocalServer()
    QLocalServer.removeServer(name)
    server.listen(name)

    def on_conn():
        c = server.nextPendingConnection()
        if c is not None:
            c.readyRead.connect(lambda: be.message.emit("__raise__", False))
    server.newConnection.connect(on_conn)
    engine.rootContext().setContextProperty("laser", be)
    ui.load(engine, os.path.join(HERE, "qml", "Laser.qml"))
    app._keep = [server, be]
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
