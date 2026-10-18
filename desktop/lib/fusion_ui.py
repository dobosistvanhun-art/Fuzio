"""Fúzió — Fúzió Desktop: közös Python-rész a QML-programokhoz (Qt 6 / PyQt6)

A Fúzió Desktop programjai (Fúzió Shell, Fájlkezelő, Beállítások) ugyanígy indulnak:
  - Qt Quick (QML) felület, a közös FusionUI QML-modullal (téma, gombok, ikonok)
  - Python háttérrész (QObject), a QML ezt hívja
Ez a modul adja az indítást, a téma színeit Pythonnak, és néhány rendszerhívást
(értesítés küldése, a szűk jogú rendszersegéd: fusion-admin).
"""
import json
import os
import shlex
import signal
import socket
import subprocess
import sys

# a telepített hely: /usr/lib/fusion/desktop; fejlesztéskor a forrásfa (FUSION_DESKTOP_DIR)
DESKTOP_DIR = os.environ.get("FUSION_DESKTOP_DIR") or os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
QML_DIR = os.path.join(DESKTOP_DIR, "qml")
ICON_DIR = os.path.join(DESKTOP_DIR, "icons")
ADMIN = os.environ.get("FUSION_ADMIN", "/usr/lib/fusion/bin/fusion-admin")
RUNTIME = os.environ.get("XDG_RUNTIME_DIR") or "/tmp"
CONFIG = os.path.join(os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config"), "fusion")

os.environ.setdefault("QT_QPA_PLATFORM", "xcb")
os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")
# a Wayland-/akadálymentesítési busz hiánya ne írjon feleslegesen a naplóba
os.environ.setdefault("QT_LOGGING_RULES", "qt.qpa.xcb.warning=false;qt.accessibility.atspi.warning=false")
os.environ.setdefault("NO_AT_BRIDGE", "1")
if "DBUS_SESSION_BUS_ADDRESS" not in os.environ and os.path.exists(os.path.join(RUNTIME, "bus")):
    os.environ["DBUS_SESSION_BUS_ADDRESS"] = "unix:path=" + os.path.join(RUNTIME, "bus")

from PyQt6.QtCore import QObject, QSocketNotifier, QUrl, pyqtSlot  # noqa: E402
from PyQt6.QtGui import QFont, QGuiApplication, QIcon  # noqa: E402
from PyQt6.QtQml import QQmlApplicationEngine  # noqa: E402


def fusion_release():
    try:
        with open("/usr/lib/fusion/fusion-release") as f:
            return {k: v.strip().strip("'") for k, v in (l.strip().split("=", 1) for l in f if "=" in l)}
    except OSError:
        return {}


def fusion_version():
    v = fusion_release().get("FUSION_VERSION", "")
    return ("Fúzió " + v).strip()


def run(cmd, timeout=10, env=None):
    """parancs futtatása: (visszatérési kód, kimenet) — a hibák nem dobnak kivételt"""
    if isinstance(cmd, str):
        cmd = shlex.split(cmd)
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                           env=env, errors="replace")
        return r.returncode, (r.stdout or "") + (r.stderr or "")
    except (OSError, subprocess.TimeoutExpired) as e:
        return 127, str(e)


def spawn(cmd, cwd=None):
    """program indítása a háttérben, a hívótól függetlenül"""
    if isinstance(cmd, str):
        cmd = shlex.split(cmd)
    try:
        subprocess.Popen(cmd, cwd=cwd, start_new_session=True, stdin=subprocess.DEVNULL,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except OSError:
        return False


def admin(*args, timeout=60):
    """a szűk jogú rendszersegéd (root): sudo -n fusion-admin <parancs> …"""
    return run(["sudo", "-n", ADMIN] + [str(a) for a in args], timeout=timeout)


def notify(summary, body="", icon="", app="Fúzió", timeout_ms=-1, urgency="normal"):
    """értesítés a Fúzió Shellnek — a Fúzió API egyetlen küldőjén át (fusion.notify)"""
    from fusion import notify as _n
    return _n.send(summary, body, icon, app, urgency, timeout_ms)


def load_json(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def save_json(path, data):
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
        os.replace(tmp, path)
    except OSError:
        pass


class Sys(QObject):
    """a QML-ből is elérhető apróságok: program indítása, értesítés, ikon elérési útja"""

    @pyqtSlot(str, result=bool)
    def spawn(self, cmd):
        return spawn(cmd)

    @pyqtSlot(str, str)
    def notify(self, summary, body):
        notify(summary, body)

    @pyqtSlot(result=str)
    def version(self):
        return fusion_version()


# a rajzolási mód a Fúzió API-ban (Qt nélkül, a parancssor és a hibajelentés is ezt használja)
from fusion.ui import RENDER_FILE, render_forced, render_mode  # noqa: E402,F401


def create_app(name, title, icon="app", software_ok=True):
    """QGuiApplication + QML-motor a FusionUI modullal. software_ok=False: a program mindig OpenGL-lel rajzol
    (a Qt Quick szoftveres rajzolója a videót — VideoOutput — nem jeleníti meg; ZBook, 0.0.41: fekete kamera-élőkép)"""
    if render_mode() == "software" and software_ok:
        # mérés (0.0.30): a Qt Quick szoftveres rajzolója OpenGL nélkül — kevesebb memória, több CPU.
        # API-hívás, nem környezeti változó: a Fúzió-programokból indított más programokat nem érinti.
        from PyQt6.QtQuick import QQuickWindow, QSGRendererInterface
        QQuickWindow.setGraphicsApi(QSGRendererInterface.GraphicsApi.Software)
    app = QGuiApplication(sys.argv)
    app.setApplicationName(name)
    app.setApplicationDisplayName(title)
    app.setDesktopFileName(name)
    app.setOrganizationName("FusionOS")
    app.setFont(QFont("DejaVu Sans", 10))
    ic = os.path.join(ICON_DIR, f"app-{icon}.svg")
    if os.path.exists(ic):
        app.setWindowIcon(QIcon(ic))
    engine = QQmlApplicationEngine()
    engine.addImportPath(QML_DIR)
    engine.rootContext().setContextProperty("fusionIconDir", QUrl.fromLocalFile(ICON_DIR + "/").toString())
    sysobj = Sys()
    engine.rootContext().setContextProperty("fusionSys", sysobj)
    app._fusion_keep = [sysobj]
    _quit_on_signals(app)
    return app, engine


def load(engine, qml_file):
    engine.load(QUrl.fromLocalFile(qml_file))
    if not engine.rootObjects():
        sys.exit(f"hiba: a felület nem tölthető be: {qml_file}")
    return engine.rootObjects()[0]


def _quit_on_signals(app, extra=None):
    """SIGTERM/SIGINT: szabályos kilépés; extra: {signum: függvény} (pl. SIGUSR1)"""
    rsock, wsock = socket.socketpair()
    rsock.setblocking(False)
    wsock.setblocking(False)
    signal.set_wakeup_fd(wsock.fileno())
    handlers = {signal.SIGTERM: app.quit, signal.SIGINT: app.quit}
    handlers.update(extra or {})
    for s in handlers:
        signal.signal(s, lambda *_: None)
    sn = QSocketNotifier(rsock.fileno(), QSocketNotifier.Type.Read, app)

    def on_sig():
        try:
            data = rsock.recv(64)
        except BlockingIOError:
            return
        for b in data:
            h = handlers.get(b)
            if h:
                h()
    sn.activated.connect(on_sig)
    app._fusion_sig = (rsock, wsock, sn, handlers)


def on_signal(app, signum, func):
    """további jelzés kezelése (a create_app után)"""
    app._fusion_sig[3][signum] = func
    signal.signal(signum, lambda *_: None)


def human_size(n):
    n = float(n)
    for u in ("B", "kB", "MB", "GB", "TB"):
        if n < 1024 or u == "TB":
            if u == "B":
                return f"{int(n)} B"
            return f"{n:.1f} {u}".replace(".", ",")
        n /= 1024
    return str(n)
