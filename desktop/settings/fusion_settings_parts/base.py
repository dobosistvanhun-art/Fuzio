"""Fúzió — Beállítások háttere: Közös rész: segédfüggvények, a Settings alaposztálya (szál, feladat-protokoll)

A Settings osztály (fusion_settings_backend) ezekből a részekből áll össze; a QML ugyanazt a `settings`
objektumot látja, mint a szétszedés előtt."""
import os
import re
import threading
import time
from PyQt6.QtCore import QObject, pyqtSignal
import fusion_ui as ui
from fusion import jobs as fjobs


SAFE = re.compile(r"^[A-Za-z0-9_.:+-]+$")


def _read(path, default=""):
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return f.read().strip()
    except OSError:
        return default


def _timing(what, secs):
    """mérés: mennyi ideig tartott egy lista (a hibajelentés és a selftest is látja)"""
    try:
        with open(os.path.join(ui.RUNTIME, "fusion-timing.log"), "a") as f:
            f.write(f"{time.strftime('%H:%M:%S')} {what} {secs:.1f}s\n")
    except OSError:
        pass


class SettingsBase(QObject):
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


    # a hosszú műveletek (telepítés, eltávolítás, frissítés) külön folyamatban futnak: a Beállítások
    # bezárása nem szakítja meg őket; a végén értesítés jön, a felület a naplót mutatja
    # (a Fúzió API feladat-protokollja: fusion.jobs — az állapot a $XDG_RUNTIME_DIR/fusion/jobs alatt)
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
