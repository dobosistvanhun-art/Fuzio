#!/usr/bin/python3
"""Fúzió — Kamera: a beépített webkamera (vagy USB-kamera) élőképe, fénykép és videó készítése

Qt Multimedia, FFmpeg-háttérrel (a kamerát közvetlenül, V4L2-n olvassa). Mérés (0.0.40, QEMU, vivid): a Qt 6.4
GStreamer-háttere Pythonból összeomlik (QMediaCaptureSession.setCamera), X alatt a QML-élőkép sem adott képkockát;
az FFmpeg-háttér mindkét úton hibátlan. Az eszközlista a Fúzió API-ból (fusion.camera) is elérhető.
A képek a Képek mappába kerülnek (XDG_PICTURES_DIR, alapértelmezés: ~/Képek), a videók a Videók mappába.

Videó: a Qt 6.4 FFmpeg-hátterének rögzítője üres fájlt ír (mérés 0.0.42, QEMU, vivid: 44–48 bájt). Ezért a felvétel
saját: az élőkép képkockái (ugyanazok, amelyeket az ablak mutat) az ffmpeg parancsnak mennek (H.264 + AAC, MP4),
a hang a mikrofonról (PulseAudio / PipeWire) — így a kamerát nem kell kétszer megnyitni, az élőkép közben is látszik.

    fusion-camera               az ablak (ha már fut: előre hozza)
    fusion-camera --selftest    önteszt: kameralista, a felület betöltése; ha van kamera, egy kép rögzítése
"""
import os
import shutil
import subprocess
import sys
import threading
import time

HERE = os.path.dirname(os.path.realpath(__file__))
os.environ.setdefault("QT_MEDIA_BACKEND", "ffmpeg")      # a Qt Multimedia betöltése előtt
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))
from fusion import camera  # noqa: E402
import fusion_ui as ui  # noqa: E402
from PyQt6.QtCore import QObject, QUrl, pyqtProperty, pyqtSignal, pyqtSlot  # noqa: E402


def save_frame(sink, path):
    """a videó-fogadó (QVideoSink) aktuális képkockája JPEG-be; a mentett út vagy "" """
    if sink is None:
        return ""
    sink = _as_sink(sink)                            # a QML-ből QObject-ként érkezik
    fr = sink.videoFrame()
    if not fr.isValid():
        return ""
    img = fr.toImage()
    if img.isNull():
        return ""
    return path if img.save(path, "JPG", 92) else ""


def _xdg_dir(key, default):
    d = ""
    try:
        with open(os.path.expanduser("~/.config/user-dirs.dirs"), encoding="utf-8") as f:
            for line in f:
                if line.startswith(key + "="):
                    d = line.split("=", 1)[1].strip().strip('"').replace("$HOME", os.path.expanduser("~"))
    except OSError:
        pass
    if not d or d.rstrip("/") == os.path.expanduser("~"):
        d = os.path.expanduser("~/" + default)
    return d


def pictures_dir():
    return _xdg_dir("XDG_PICTURES_DIR", "Képek")


def videos_dir():
    return _xdg_dir("XDG_VIDEOS_DIR", "Videók")


def _as_sink(sink):
    from PyQt6.QtMultimedia import QVideoSink
    if sink is not None and not isinstance(sink, QVideoSink):
        from PyQt6 import sip
        sink = sip.cast(sink, QVideoSink)
    return sink


def audio_source():
    """a hangbemenet (mikrofon) neve, vagy "" ha nincs (a felvétel ekkor hang nélküli)"""
    try:
        r = subprocess.run(["pactl", "get-default-source"], capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.TimeoutExpired):
        return ""
    src = r.stdout.strip()
    return "" if r.returncode or not src or src.endswith(".monitor") or src == "auto_null" else src


class Recorder:
    """videófelvétel az élőkép képkockáiból: QVideoSink → (külön szál, állandó 30 kép/mp-es ütem: a legutóbbi
    képkocka — ha a kamera lassabb, ismétli, ha gyorsabb, kihagy) → ffmpeg (stdin: nyers BGRA) + mikrofon (pulse)
    → MP4 (H.264, AAC). Így a videó hossza a valós idő, és a hang együtt fut a képpel."""

    FPS = 30

    def __init__(self):
        self.proc = None
        self.sink = None
        self.path = ""
        self.size = None
        self.latest = None
        self.lock = threading.Lock()
        self.stopping = threading.Event()
        self.thread = None
        self.started = 0.0
        self.frames = 0          # a kamerától kapott képkockák
        self.written = 0         # a videóba írt képkockák
        self.audio = ""
        self.error = ""

    def running(self):
        return self.sink is not None

    def start(self, sink, path, audio=True):
        if self.running():
            return False
        if not shutil.which("ffmpeg"):
            self.error = "az ffmpeg nincs telepítve"
            return False
        self.sink, self.path, self.size, self.latest, self.error = _as_sink(sink), path, None, None, ""
        self.audio = audio_source() if audio else ""
        self.frames = self.written = 0
        self.stopping.clear()
        self.started = time.monotonic()
        self.sink.videoFrameChanged.connect(self._frame)
        return True

    def audio_input(self):
        """az ffmpeg hangbemenete (a teszt felülírhatja)"""
        return ["-f", "pulse", "-i", self.audio]

    def _spawn(self, w, h):
        base = os.path.splitext(self.path)[0]
        self.vtmp, self.atmp = base + ".kep.mp4", base + ".hang.wav"
        vcmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                "-f", "rawvideo", "-pix_fmt", "bgra", "-s", f"{w}x{h}", "-framerate", str(self.FPS), "-i", "pipe:0",
                "-c:v", "libx264", "-preset", "superfast", "-crf", "23", "-pix_fmt", "yuv420p",
                "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2", "-movflags", "+faststart", self.vtmp]
        self.proc = subprocess.Popen(vcmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        # a hang külön folyamatban (a mikrofon ütemében), a végén egy gyors összefűzés: így a videó hossza mindig a
        # valós idő, akkor is, ha a hangeszköz akadozik (QEMU: a hangsáv 0,3 mp-re vágta a közös felvételt)
        self.aproc = None
        if self.audio:
            acmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y"] + self.audio_input() + \
                   ["-c:a", "pcm_s16le", "-ar", "48000", "-ac", "2", self.atmp]
            self.aproc = subprocess.Popen(acmd, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                          stderr=subprocess.PIPE)
        self.thread = threading.Thread(target=self._writer, daemon=True)
        self.thread.start()

    def _frame(self, fr):
        if not fr.isValid():
            return
        from PyQt6.QtGui import QImage
        img = fr.toImage()
        if img.isNull():
            return
        img = img.convertToFormat(QImage.Format.Format_RGB32)        # B G R A sorrend (little-endian)
        if self.size is None:
            self.size = (img.width(), img.height())
        elif (img.width(), img.height()) != self.size:
            img = img.scaled(*self.size)
        data = img.constBits().asstring(img.sizeInBytes())
        with self.lock:
            self.latest = data
        self.frames += 1
        if self.proc is None:
            self.t0 = time.monotonic()
            self._spawn(*self.size)

    def _writer(self):
        tick = 1.0 / self.FPS
        while not self.stopping.is_set():
            due = int((time.monotonic() - self.t0) / tick) + 1
            if due - self.written > self.FPS:            # nagy lemaradás (pl. a gép elakadt): nem pótoljuk mind
                self.written = due - 1
            while self.written < due:
                with self.lock:
                    data = self.latest
                try:
                    self.proc.stdin.write(data)
                except (OSError, ValueError):
                    return
                self.written += 1
            time.sleep(max(0.0, self.t0 + self.written * tick - time.monotonic()))

    def elapsed(self):
        return time.monotonic() - self.started if self.running() else 0.0

    def stop(self):
        """leállítás; (ok, üzenet)"""
        if not self.running():
            return False, "nincs felvétel"
        try:
            self.sink.videoFrameChanged.disconnect(self._frame)
        except TypeError:
            pass
        self.sink = None
        if self.proc is None:
            return False, "nem érkezett képkocka a kamerától"
        self.stopping.set()
        self.thread.join(timeout=30)            # lassú gépen a kódoló lemaradhat: a puffer kiírása
        err = b""
        if self.aproc:
            self.aproc.send_signal(2)           # SIGINT: az ffmpeg lezárja a WAV-fájlt
        try:
            self.proc.stdin.close()
            self.proc.wait(timeout=60)
            err = self.proc.stderr.read() or b""
        except (OSError, ValueError):
            pass
        except subprocess.TimeoutExpired:
            self.proc.kill()
            self.proc.wait()
        rc, self.proc = self.proc.returncode, None
        audio_ok = False
        if self.aproc:
            try:
                self.aproc.wait(timeout=15)
            except subprocess.TimeoutExpired:
                self.aproc.kill()
                self.aproc.wait()
            audio_ok = os.path.isfile(self.atmp) and os.path.getsize(self.atmp) > 4096
            self.aproc = None
        ok = rc == 0 and os.path.isfile(self.vtmp) and os.path.getsize(self.vtmp) > 1000
        if ok:
            if audio_ok:
                r = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", self.vtmp, "-i", self.atmp,
                                    "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "128k",
                                    "-movflags", "+faststart", self.path], capture_output=True, timeout=300)
                if r.returncode != 0:            # a hang nélküli videó akkor is megmarad
                    os.replace(self.vtmp, self.path)
                    self.audio = ""
            else:
                os.replace(self.vtmp, self.path)
                self.audio = ""
        for t in (self.vtmp, self.atmp):
            try:
                os.unlink(t)
            except OSError:
                pass
        ok = ok and os.path.isfile(self.path) and os.path.getsize(self.path) > 1000
        self.error = "" if ok else (err.decode("utf-8", "replace").strip().splitlines() or [f"ffmpeg: {rc}"])[-1]
        return ok, self.error


class Backend(QObject):
    message = pyqtSignal(str, bool)
    recordingChanged = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.rec = Recorder()

    @pyqtProperty(bool, notify=recordingChanged)
    def recording(self):
        return self.rec.running()

    @pyqtSlot(QObject, bool, result=str)
    def startRecording(self, sink, audio):
        d = videos_dir()
        os.makedirs(d, exist_ok=True)
        path = os.path.join(d, time.strftime("Kamera-%Y%m%d-%H%M%S.mp4"))
        ok = self.rec.start(sink, path, audio)
        self.recordingChanged.emit()
        return "" if ok else (self.rec.error or "a felvétel nem indult")

    @pyqtSlot(result="QVariant")
    def stopRecording(self):
        path = self.rec.path
        ok, msg = self.rec.stop()
        self.recordingChanged.emit()
        return {"ok": ok, "path": path if ok else "", "message": msg}

    @pyqtSlot(result=str)
    def recordingTime(self):
        t = int(self.rec.elapsed())
        return f"{t // 60:02d}:{t % 60:02d}"

    @pyqtSlot(result=bool)
    def hasMicrophone(self):
        return bool(audio_source())

    shot = ""

    fmt = ""

    @pyqtSlot(QObject, str)
    def selftestShot(self, sink, fmt):
        """önteszt: fénykép, majd 5 mp videó (hanggal, ha van mikrofon), utána kilépés"""
        from PyQt6.QtCore import QCoreApplication, QTimer
        self.fmt = fmt
        rd = os.environ.get("XDG_RUNTIME_DIR", "/tmp")
        self.shot = save_frame(sink, os.path.join(rd, "fusion-camera-selftest.jpg"))
        self.rec.path = ""
        video = os.path.join(rd, "fusion-camera-selftest.mp4")
        if os.path.exists(video):
            os.unlink(video)
        if not self.rec.start(sink, video, audio=True):
            self.recResult = (False, self.rec.error, "")
            QCoreApplication.quit()
            return

        def fin():
            ok, msg = self.rec.stop()
            self.recResult = (ok, msg, video)
            QCoreApplication.quit()
        QTimer.singleShot(5000, fin)

    recResult = (False, "nem futott", "")

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
    app, engine = ui.create_app("fusion-camera", "Kamera", "camera", software_ok=False)
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
    QTimer.singleShot(60000, app.quit)            # biztosíték
    app.exec()
    size = os.path.getsize(be.shot) if be.shot and os.path.isfile(be.shot) else 0
    check("FRAMES", bool(be.shot), "az élőképben van képkocka" if be.shot else "nincs képkocka az élőképben")
    check("CAPTURE", size > 1000, f"{size} bájt")
    rok, rmsg, rpath = be.recResult
    dur = ""
    if rok and shutil.which("ffprobe"):
        r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,codec_name:format=duration",
                            "-of", "compact=p=0:nk=1", rpath], capture_output=True, text=True, timeout=30)
        dur = " ".join(r.stdout.split())
    try:
        dsec = float(dur.split()[-1]) if dur else 0.0
    except ValueError:
        dsec = 0.0
    # QEMU-ban (KVM nélkül) a H.264-kódoló sokszor lassabb a valós időnél, így a videó rövidebb a felvétel idejénél —
    # itt a mérce: elkészült, lejátszható, van kép- és (ha volt mikrofon) hangsáv; a valós idejű hossz a ZBookon mérendő
    has_streams = "h264" in dur and ("aac" in dur or not be.rec.audio)
    check("VIDEO", rok and os.path.getsize(rpath) > 10000 and (not dur or (has_streams and dsec > 0.3)),
          (f"{os.path.getsize(rpath)} bájt, a kamerától: {be.rec.frames}, a videóban: {be.rec.written} képkocka, "
           f"hang: {be.rec.audio or 'nincs'}, {dur}") if rok else rmsg)
    from PyQt6.QtQuick import QQuickWindow, QSGRendererInterface
    api = QQuickWindow.graphicsApi()
    check("RENDER", api != QSGRendererInterface.GraphicsApi.Software,
          f"{api.name} (felület: {ui.render_mode()}) formátum: {be.fmt or '?'}")
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
    app, engine = ui.create_app("fusion-camera", "Kamera", "camera", software_ok=False)
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
