#!/usr/bin/python3
"""Fúzió — Lemezkezelő: lemezek és partíciók megtekintése, állapot (SMART), formázás, címke,
partíció létrehozása és törlése. A rendszerműveletek a szűk jogú segéden át mennek
(sudo -n fusion-admin disk …  →  fusion-disk); a Fúzió saját lemeze csak megtekinthető.

    fusion-disks              az ablak (ha már fut: előre hozza)
    fusion-disks --selftest   önteszt: a lemezlista, a rendszerlemez védelme, a felület betöltése
"""
import json
import os
import subprocess
import sys
import threading

HERE = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))
import fusion_ui as ui  # noqa: E402
from PyQt6.QtCore import QObject, QTimer, QUrl, pyqtProperty, pyqtSignal, pyqtSlot  # noqa: E402

FS_NAMES = {"vfat": "FAT32", "exfat": "exFAT", "ntfs": "NTFS", "ext4": "ext4", "ext3": "ext3", "ext2": "ext2",
            "btrfs": "Btrfs", "xfs": "XFS", "swap": "Linux swap", "iso9660": "CD/DVD-kép (ISO 9660)",
            "udf": "UDF", "erofs": "EROFS (Fúzió rendszerkép)", "crypto_LUKS": "titkosított (LUKS)",
            "LVM2_member": "LVM", "linux_raid_member": "RAID", "BitLocker": "titkosított (BitLocker)"}
MOUNTABLE = {"vfat", "exfat", "ntfs", "ext2", "ext3", "ext4", "btrfs", "xfs", "iso9660", "udf"}
KIND_NAMES = {"usb": "USB", "sd": "SD-kártya", "nvme": "NVMe SSD", "ssd": "SSD", "hdd": "merevlemez"}


def admin_disk(*args, timeout=120):
    return ui.admin("disk", *args, timeout=timeout)


def load_list(smart=False):
    rc, out = admin_disk("list", *(["--smart"] if smart else []), timeout=90)
    if rc != 0:
        return None, (out.strip().splitlines() or ["ismeretlen hiba"])[-1].replace("fusion-admin: ", "")
    try:
        return json.loads(out[out.index("{"):]), ""
    except ValueError:
        return None, "a lemezlista nem olvasható"


def decorate(data, smart_cache):
    """megjelenítéshez kiegészített lista (a QML egyszerű maradjon)"""
    disks = []
    for d in data.get("disks", []):
        d = dict(d)
        d["sizeText"] = ui.human_size(d["size"])
        d["kindText"] = KIND_NAMES.get(d["kind"], d["kind"])
        d["tableText"] = {"gpt": "GPT", "dos": "MBR"}.get(d["table"], "nincs partíciós tábla")
        if d.get("smart") is None and d["name"] in smart_cache:
            d["smart"] = smart_cache[d["name"]]
        segs = []
        for p in d["partitions"]:
            q = dict(p)
            q["seg"] = "part"
            q["sizeText"] = ui.human_size(p["size"])
            q["fsText"] = FS_NAMES.get(p["fstype"], p["fstype"] or "nincs fájlrendszer / ismeretlen")
            q["title"] = p["label"] or p["friendly"] or p["partlabel"] or p["name"]
            q["mountable"] = p["fstype"] in MOUNTABLE and not p["locked"] and not d["system"] and not p["fusionpart"]
            q["editable"] = not p["locked"] and not d["system"] and not p["fusionpart"] and not d["ro"] and not p["extended"]
            q["storage"] = bool(p.get("storage"))
            # Adatlemez lehet: belső lemez csatolható partíciója (a Fúzió saját lemezén kívül)
            q["storageOk"] = q["mountable"] and not d["removable"] and not q["storage"]
            if q["storage"]:
                q["title"] = q["title"] + " — Adatlemez"
            q["usedText"] = (ui.human_size(p["used"]) + " foglalt, " + ui.human_size(p["avail"]) + " szabad") if p["used"] is not None else ""
            q["usedPct"] = (p["used"] / (p["used"] + p["avail"])) if p["used"] is not None and (p["used"] + p["avail"]) > 0 else -1
            segs.append(q)
        for i, f in enumerate(d["free"]):
            segs.append({"seg": "free", "name": f"free{i}", "start": f["start"], "end": f["end"], "size": f["size"],
                         "sizeText": ui.human_size(f["size"]), "title": "Szabad terület",
                         "editable": not d["system"] and not d["ro"] and d["table"] in ("gpt", "dos")})
        segs = [s for s in segs if not s.get("extended")]       # a kiterjesztett MBR-partíció helyett a tartalma
        segs.sort(key=lambda s: s["start"])
        d["segments"] = segs
        disks.append(d)
    return disks


class Backend(QObject):
    changed = pyqtSignal()
    message = pyqtSignal(str, bool)     # szöveg, hiba-e
    jobDone = pyqtSignal(bool, str)

    def __init__(self):
        super().__init__()
        self._disks, self._error, self._busy, self._log = [], "", "", []
        self._smart = {}
        self._sig = ""
        self._lock = threading.Lock()
        self.reload(True)
        # változásfigyelés: új / kihúzott lemez, partíció, csatolás (olcsó: csak a kernel listái)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._poll)
        self._timer.start(2000)

    def _signature(self):
        try:
            with open("/proc/partitions") as a, open("/proc/self/mounts") as b:
                return a.read() + b.read()
        except OSError:
            return ""

    def _poll(self):
        s = self._signature()
        if s != self._sig and not self._busy:
            self.reload(False)

    def _load(self, smart):
        data, err = load_list(False)
        with self._lock:
            if data is not None:
                self._disks, self._error = decorate(data, self._smart), ""
            else:
                self._error = err
        self.changed.emit()
        if smart and data is not None:
            sdata, _ = load_list(True)
            if sdata:
                with self._lock:
                    self._smart.update({d["name"]: d["smart"] for d in sdata["disks"] if d.get("smart")})
                    self._disks = decorate(sdata, self._smart)
                self.changed.emit()

    @pyqtSlot(bool)
    def reload(self, smart):
        self._sig = self._signature()
        threading.Thread(target=self._load, args=(smart,), daemon=True).start()

    @pyqtProperty("QVariant", notify=changed)
    def disks(self):
        return self._disks

    @pyqtProperty(str, notify=changed)
    def error(self):
        return self._error

    @pyqtProperty(str, notify=changed)
    def busy(self):
        return self._busy

    @pyqtProperty("QVariant", notify=changed)
    def log(self):
        return self._log

    # --- műveletek -----------------------------------------------------------------------------
    def _job(self, title, cmd):
        def work():
            self._log = []
            ok = False
            try:
                p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                                     errors="replace", stdin=subprocess.DEVNULL)
                for line in p.stdout:
                    line = line.rstrip()
                    if line:
                        self._log = (self._log + [line.replace("fusion-admin: ", "").replace("fusion-disk: ", "")])[-12:]
                        self.changed.emit()
                ok = p.wait() == 0
            except OSError as e:
                self._log.append(str(e))
            last = self._log[-1] if self._log else ""
            self._busy = ""
            self.changed.emit()
            self.jobDone.emit(ok, last)
            self.message.emit(f"{title}: " + ("kész" if ok else last or "sikertelen"), not ok)
            self.reload(False)
        if self._busy:
            self.message.emit("egy művelet már folyamatban van", True)
            return
        self._busy = title
        self._log = []
        self.changed.emit()
        threading.Thread(target=work, daemon=True).start()

    def _admin(self, *args):
        return ["sudo", "-n", ui.ADMIN] + [str(a) for a in args]

    @pyqtSlot(str, str, str, str, str)
    def formatDisk(self, disk, table, fs, label, confirm):
        self._job("Lemez formázása", self._admin("disk", "format-disk", disk, table, fs, label, confirm))

    @pyqtSlot(str, str, str, str)
    def formatPart(self, part, fs, label, confirm):
        self._job("Formázás", self._admin("disk", "format", part, fs, label, confirm))

    @pyqtSlot(str, str)
    def setLabel(self, part, label):
        self._job("Átnevezés", self._admin("disk", "label", part, label))

    @pyqtSlot(str, int, int, str, str, str)
    def create(self, disk, start_mib, size_mib, fs, label, confirm):
        self._job("Új partíció", self._admin("disk", "create", disk, start_mib, size_mib, fs, label, confirm))

    @pyqtSlot(str, str)
    def delete(self, part, confirm):
        self._job("Partíció törlése", self._admin("disk", "delete", part, confirm))

    @pyqtSlot(str)
    def storageSet(self, part):
        self._job("Adatlemez", self._admin("disk", "storage-set", part))

    @pyqtSlot()
    def storageClear(self):
        self._job("Adatlemez megszüntetése", self._admin("disk", "storage-clear"))

    @pyqtSlot(str)
    def mount(self, part):
        self._job("Csatolás", self._admin("mount", part))

    @pyqtSlot(str)
    def unmount(self, part):
        self._job("Leválasztás", self._admin("unmount", part))

    @pyqtSlot(str)
    def eject(self, disk):
        self._job("Kiadás", self._admin("eject", disk))

    @pyqtSlot(str)
    def openFiles(self, path):
        ui.spawn(["fusion-files", path])


def selftest():
    ok = True

    def check(name, cond, extra=""):
        nonlocal ok
        print(f"FUSION-DISKS: {name} {'ok' if cond else 'HIBA'}{(' ' + extra) if extra else ''}", flush=True)
        ok = ok and bool(cond)

    data, err = load_list(True)
    check("LIST", data is not None and data.get("disks"), err or f"lemezek={','.join(d['name'] for d in data['disks'])}")
    if data:
        sysd = [d for d in data["disks"] if d["system"]]
        check("SYSTEM", len(sysd) == 1 and sysd[0]["name"] == data["bootDisk"], f"boot={data['bootDisk']}")
        if sysd:
            p = sysd[0]["partitions"][-1]["name"] if sysd[0]["partitions"] else sysd[0]["name"]
            rc, out = admin_disk("format", p, "vfat", "X", sysd[0]["name"])
            check("GUARD", rc != 0 and "saját lemeze" in out, out.strip().splitlines()[-1] if out.strip() else "")
        decorate(data, {})
    # a felület betöltése (képernyő nélkül)
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    app, engine = ui.create_app("fusion-disks", "Lemezkezelő", "disks")
    be = Backend()
    engine.rootContext().setContextProperty("disks", be)
    engine.load(QUrl.fromLocalFile(os.path.join(HERE, "qml", "Disks.qml")))
    check("QML", bool(engine.rootObjects()))
    print(f"FUSION-DISKS: RESULT {'ok' if ok else 'HIBA'}", flush=True)
    return 0 if ok else 1


def main():
    if sys.argv[1:2] == ["--selftest"]:
        return selftest()
    from PyQt6.QtNetwork import QLocalServer, QLocalSocket
    name = f"fusion-disks-{os.getuid()}"
    sock = QLocalSocket()
    sock.connectToServer(name)
    if sock.waitForConnected(300):          # már fut: előre hozzuk
        sock.write(b'{"raise": true}\n')
        sock.waitForBytesWritten(500)
        return 0
    app, engine = ui.create_app("fusion-disks", "Lemezkezelő", "disks")
    be = Backend()
    server = QLocalServer()
    QLocalServer.removeServer(name)
    server.listen(name)

    def on_conn():
        c = server.nextPendingConnection()
        if c is not None:
            c.readyRead.connect(lambda: be.message.emit("__raise__", False))
    server.newConnection.connect(on_conn)
    engine.rootContext().setContextProperty("disks", be)
    ui.load(engine, os.path.join(HERE, "qml", "Disks.qml"))
    app._keep = [server, be]
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
