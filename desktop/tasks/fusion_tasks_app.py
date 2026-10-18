#!/usr/bin/python3
"""Fúzió — Feladatkezelő (Ctrl+Alt+Del)

    fusion-tasks              az ablak (ha már fut: előre hozza)
    fusion-tasks --selftest   önteszt: egy válaszoló és egy „lefagyott” próbaablak felismerése, bezárása
"""
import json
import os
import queue
import subprocess
import sys
import threading
import time

HERE = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))
import fusion_ui as ui  # noqa: E402
import fusion_tasks as ft  # noqa: E402
from PyQt6.QtCore import QObject, pyqtProperty, pyqtSignal, pyqtSlot  # noqa: E402

TESTWIN = os.path.join(HERE, "fusion-tasks-testwin")


class Backend(QObject):
    changed = pyqtSignal()
    message = pyqtSignal(str, bool)     # szöveg, hiba-e

    def __init__(self):
        super().__init__()
        self._programs, self._processes, self._summary = [], [], {}
        self._q = queue.Queue()
        self._busy = ""
        threading.Thread(target=self._loop, daemon=True).start()

    # egyetlen szál használja az X-kapcsolatot: a frissítés és a műveletek is itt futnak
    def _loop(self):
        t = ft.Tasks()
        last = 0.0
        while True:
            try:
                act, arg = self._q.get(timeout=0.3)
            except queue.Empty:
                act, arg = None, None
            if act:
                self._busy = act
                self.changed.emit()
                try:
                    self._do(t, act, arg)
                except Exception as e:      # a Feladatkezelő ne álljon le egy hiba miatt
                    self.message.emit(f"hiba: {e}", True)
                self._busy = ""
                last = 0
            if time.monotonic() - last >= 2.0:
                try:
                    self._programs = t.refresh(ping=True)
                    self._processes = t.processes()
                    self._summary = t.summary()
                except Exception as e:
                    self.message.emit(f"frissítési hiba: {e}", True)
                last = time.monotonic()
                self.changed.emit()

    def _group(self, key):
        return next((g for g in self._programs if g["key"] == key), None)

    def _do(self, t, act, arg):
        if act == "activate":
            g = self._group(arg)
            if g:
                t.activate(g)
        elif act == "close":
            g = self._group(arg)
            if g:
                t.close(g)
                self.message.emit(f"bezárás kérve: {g['name']}", False)
        elif act == "force":
            g = self._group(arg)
            if g:
                ok = t.force(g)
                self.message.emit(f"{g['name']}: " + ("leállítva" if ok else "nem minden folyamata állt le"), not ok)
        elif act == "kill":
            ok = t.kill_process(int(arg))
            self.message.emit(f"folyamat {arg}: " + ("leállítva" if ok else "nem állítható le"), not ok)

    @pyqtProperty("QVariant", notify=changed)
    def programs(self):
        return self._programs

    @pyqtProperty("QVariant", notify=changed)
    def processes(self):
        return self._processes

    @pyqtProperty("QVariant", notify=changed)
    def summary(self):
        return self._summary

    @pyqtProperty(str, notify=changed)
    def busy(self):
        return self._busy

    @pyqtSlot(str, str)
    def act(self, action, arg):
        if action in ("activate", "close", "force", "kill"):
            self._q.put((action, arg))


def selftest():
    """a QEMU-teszt: egy válaszoló és egy lefagyott próbaablak; a lefagyott felismerése és leállítása"""
    ok = True

    def check(name, cond, extra=""):
        nonlocal ok
        print(f"FUSION-TASKS: {name} {'ok' if cond else 'HIBA'}{(' ' + extra) if extra else ''}", flush=True)
        ok = ok and bool(cond)

    import faulthandler
    import signal
    # ha valami beakad: 75 mp után a Python-veremkép a naplóba, és kilépés (a próbaablakok is leállnak)
    faulthandler.dump_traceback_later(75, exit=False)
    kids = []

    def cleanup(*_):
        for k in kids:
            try:
                k.kill()
            except OSError:
                pass
    signal.signal(signal.SIGALRM, lambda *_: (print("FUSION-TASKS: TIMEOUT", flush=True), cleanup(), os._exit(3)))
    signal.alarm(80)
    quiet = dict(stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    pa = subprocess.Popen([sys.executable, TESTWIN, "ok"], **quiet)
    pb = subprocess.Popen([sys.executable, TESTWIN, "hung"], **quiet)
    kids += [pa, pb]
    t = ft.Tasks()
    print("FUSION-TASKS: X " + ("ok" if t.x else "nincs"), flush=True)
    # megvárjuk, amíg mindkét próbaablak megjelenik (lassú, KVM nélküli gépen a Python indulása is sokáig tart)
    t0 = time.monotonic()
    while time.monotonic() - t0 < 40:
        pids = {p for g in t.refresh(ping=False) for p in g["pids"]}
        if pa.pid in pids and pb.pid in pids:
            break
        time.sleep(1)
    time.sleep(2)            # a „lefagyott” ablak 2 mp után hagyja abba az üzenetek feldolgozását
    print(f"FUSION-TASKS: WINDOWS {time.monotonic() - t0:.0f}s", flush=True)
    gs = t.refresh(ping=True)
    a = next((g for g in gs if pa.pid in g["pids"]), None)
    b = next((g for g in gs if pb.pid in g["pids"]), None)
    check("LIST", a is not None and b is not None, f"programok={len(gs)}")
    check("ALIVE", a is not None and a["status"] == "ok")
    check("HUNG", b is not None and b["status"] == "hung")
    try:
        if b:
            t0 = time.monotonic()
            forced = t.force(b)
            check("FORCE", forced and pb.wait(timeout=5) is not None, f"{time.monotonic() - t0:.1f}s")
        if a:
            t.close(a)
            check("CLOSE", pa.wait(timeout=5) == 0)
    except subprocess.TimeoutExpired as e:
        check("FORCE/CLOSE", False, f"nem állt le: {e}")
    finally:
        cleanup()
    check("PROCESSES", len(t.processes()) > 0 and t.summary()["memTotal"] > 0)
    signal.alarm(0)
    faulthandler.cancel_dump_traceback_later()
    print(f"FUSION-TASKS: RESULT {'ok' if ok else 'HIBA'}", flush=True)
    return 0 if ok else 1


def main():
    if sys.argv[1:2] == ["--selftest"]:
        return selftest()
    from PyQt6.QtNetwork import QLocalServer, QLocalSocket
    name = f"fusion-tasks-{os.getuid()}"
    sock = QLocalSocket()
    sock.connectToServer(name)
    if sock.waitForConnected(300):          # már fut: előre hozzuk
        sock.write(b'{"raise": true}\n')
        sock.waitForBytesWritten(500)
        return 0
    app, engine = ui.create_app("fusion-tasks", "Feladatkezelő", "tasks")
    be = Backend()
    server = QLocalServer()
    QLocalServer.removeServer(name)
    server.listen(name)

    def on_conn():
        c = server.nextPendingConnection()
        if c is not None:
            c.readyRead.connect(lambda: be.message.emit("__raise__", False))
    server.newConnection.connect(on_conn)
    engine.rootContext().setContextProperty("tasks", be)
    ui.load(engine, os.path.join(HERE, "qml", "Tasks.qml"))
    app._keep = [server, be]
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
