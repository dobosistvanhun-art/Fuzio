#!/usr/bin/python3
"""FusionOS — Kamera: a beépített webkamera (vagy USB-kamera) élőképe és fénykép készítése

Qt Multimedia, FFmpeg-háttérrel (a kamerát közvetlenül, V4L2-n olvassa). Mérés (0.0.40, QEMU, vivid): a Qt 6.4
GStreamer-háttere Pythonból összeomlik (QMediaCaptureSession.setCamera), X alatt a QML-élőkép sem adott képkockát;
az FFmpeg-háttér mindkét úton hibátlan. Az eszközlista a Fusion API-ból (fusion.camera) is elérhető.
A képek a Képek mappába kerülnek (XDG_PICTURES_DIR, alapértelmezés: ~/Képek).

    fusion-camera               az ablak (ha már fut: előre hozza)
    fusion-camera --selftest    önteszt: kameralista, a felület betöltése; ha van kamera, egy kép rögzítése
"""
import os
import sys
import time

HERE = os.path.dirname(os.path.realpath(__file__))
os.environ.setdefault("QT_MEDIA_BACKEND", "ffmpeg")      # a Qt Multimedia betöltése előtt
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))
from fusion import camera  # noqa: E402
import fusion_ui as ui  # noqa: E402
from PyQt6.QtCore import QObject, QUrl, pyqtSignal, pyqtSlot  # noqa: E402


def save_frame(sink, path):
    """a videó-fogadó (QVideoSink) aktuális képkockája JPEG-be; a mentett út vagy "" """
    if sink is None:
        return ""
    from PyQt6.QtMultimedia import QVideoSink
    if not isinstance(sink, QVideoSink):             # a QML-ből QObject-ként érkezik
        from PyQt6 import sip
        sink = sip.cast(sink, QVideoSink)
    fr = sink.videoFrame()
    if not fr.isValid():
        return ""
    img = fr.toImage()
    if img.isNull():
        return ""
    return path if img.save(path, "JPG", 92) else ""


def pictures_dir():
    d = ""
    try:
        with open(os.path.expanduser("~/.config/user-dirs.dirs"), encoding="utf-8") as f:
            for line in f:
                if line.startswith("XDG_PICTURES_DIR="):
                    d = line.split("=", 1)[1].strip().strip('"').replace("$HOME", os.path.expanduser("~"))
    except OSError:
        pass
    if not d or d.rstrip("/") == os.path.expanduser("~"):
        d = os.path.expanduser("~/Képek")
    return d


class Backend(QObject):
    message = pyqtSignal(str, bool)

    shot = ""

    @pyqtSlot(QObject)
    def selftestShot(self, sink):
        self.shot = save_frame(sink, os.path.join(os.environ.get("XDG_RUNTIME_DIR", "/tmp"), "fusion-camera-selftest.jpg"))

    @pyqtSlot(QObject, result=str)
    def saveFrame(self, sink):
        d = pictures_dir()
        os.makedirs(d, exist_ok=True)
        return save_frame(sink, os.path.join(d, time.strftime("Kamera-%Y%m%d-%H%M%S.jpg")))

    @pyqtSlot(result="QVariant")
    def devices(self):
        return camera.cameras()

    @pyqtSlot(str)
    def showFile(self, path):
        ui.spawn(["fusion-files", os.path.dirname(path)])

    @pyqtSlot()
    def openSettings(self):
        ui.spawn(["fusion-settings", "devices"])


def selftest():
    ok = True

    def check(name, cond, extra=""):
        nonlocal ok
        ok = ok and bool(cond)
        print(f"FUSION-CAMERA: {name} {'ok' if cond else 'HIBA'} {extra}".rstrip(), flush=True)
    cams = camera.cameras()
    print("FUSION-CAMERA: LIST " + (", ".join(f"{c['dev']}={c['name']}" for c in cams) or "nincs"), flush=True)
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app, engine = ui.create_app("fusion-camera", "Kamera", "camera")
    be = Backend()
    engine.rootContext().setContextProperty("cam", be)
    engine.rootContext().setContextProperty("selftestMode", True)
    engine.load(QUrl.fromLocalFile(os.path.join(HERE, "qml", "Camera.qml")))
    check("QML", bool(engine.rootObjects()))
    if not cams:
        return 0 if ok else 1
    # élőkép és fénykép: a valódi ablak, a valódi úton (VideoOutput → képkocka → JPEG); a QML 8 mp után lő és kilép
    from PyQt6.QtCore import QTimer
    from PyQt6.QtMultimedia import QMediaDevices
    inputs = QMediaDevices.videoInputs()
    check("QTDEVICES", len(inputs) > 0, ",".join(d.description() for d in inputs) + f" ({os.environ.get('QT_MEDIA_BACKEND')})")
    if not inputs:
        return 1
    QTimer.singleShot(40000, app.quit)            # biztosíték
    app.exec()
    size = os.path.getsize(be.shot) if be.shot and os.path.isfile(be.shot) else 0
    check("FRAMES", bool(be.shot), "az élőképben van képkocka" if be.shot else "nincs képkocka az élőképben")
    check("CAPTURE", size > 1000, f"{size} bájt")
    return 0 if ok else 1


def main():
    args = sys.argv[1:]
    if args[:1] == ["--selftest"]:
        return selftest()
    from PyQt6.QtNetwork import QLocalServer, QLocalSocket
    name = f"fusion-camera-{os.getuid()}"
    sock = QLocalSocket()
    sock.connectToServer(name)
    if sock.waitForConnected(300):          # már fut: előre hozzuk
        sock.write(b'{"raise": true}\n')
        sock.waitForBytesWritten(500)
        return 0
    app, engine = ui.create_app("fusion-camera", "Kamera", "camera")
    be = Backend()
    server = QLocalServer()
    QLocalServer.removeServer(name)
    server.listen(name)

    def on_conn():
        c = server.nextPendingConnection()
        if c is not None:
            c.readyRead.connect(lambda: be.message.emit("__raise__", False))
    server.newConnection.connect(on_conn)
    engine.rootContext().setContextProperty("cam", be)
    engine.rootContext().setContextProperty("selftestMode", False)
    ui.load(engine, os.path.join(HERE, "qml", "Camera.qml"))
    app._keep = [server, be]
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
