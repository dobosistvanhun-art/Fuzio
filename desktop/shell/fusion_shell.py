#!/usr/bin/python3
"""FusionOS — Fusion Shell: a Fusion Desktop panelje, Start menüje és értesítései (Qt Quick)

Egy folyamat, több ablak:
  Panel          a képernyő alján (dock, 40 px foglalás): Start, tálca, eszközök, Wi-Fi, értesítések, óra
  Start menü     keresés, programok, beállítás-oldalak, kikapcsolás
  Értesítések    buborék a jobb alsó sarokban + értesítésközpont (előzmények)
  Naptár         az órára kattintva

Értesítések: a szabványos org.freedesktop.Notifications D-Bus-szolgáltatás (bármely program
küldhet: fusion-notify, notify-send), és a Shell saját eseményei: eszköz (lézer, nyomtató)
csatlakozott/levált, USB-meghajtó, Wi-Fi-kapcsolat, rendszerfrissítés.

Jelzések: SIGUSR1 = Start menü nyitása/zárása (fusion-shell menu, Super / Alt+F1).
Állapot a tesztekhez: $XDG_RUNTIME_DIR/fusion-shell.state (JSON).
"""
import glob
import json
import os
import signal
import subprocess
import sys
import threading
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), "lib"))
sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))

import fusion_ui as ui  # noqa: E402  (a környezeti változókat a Qt betöltése előtt állítja)
import fusion  # noqa: E402
import fusion_apps  # noqa: E402
import fusion_net  # noqa: E402
import fusion_sound  # noqa: E402
from fusion.x11 import PANEL_HEIGHT, X11  # noqa: E402
from fusion import devices as fdev  # noqa: E402
from dashboard import Dashboard  # noqa: E402

from PyQt6.QtCore import (QObject, Qt, QTimer, QUrl, pyqtClassInfo, pyqtProperty,  # noqa: E402
                          pyqtSignal, pyqtSlot)
from PyQt6.QtDBus import QDBusAbstractAdaptor, QDBusConnection, QDBusMessage  # noqa: E402
from PyQt6.QtGui import QColor  # noqa: E402
from PyQt6.QtQuick import QQuickView  # noqa: E402

HERE = os.path.dirname(os.path.realpath(__file__))
QML = os.path.join(HERE, "qml")
MENU_W, MENU_H = 640, 580
CENTER_W, CENTER_H = 400, 520
CAL_W, CAL_H = 300, 300
SOUND_W, SOUND_H = 340, 300
TOAST_W = 380
STATE_FILE = os.path.join(ui.RUNTIME, "fusion-shell.state")
MEDIA_DIR = fusion.MEDIA
HU_DAYS = ["hétfő", "kedd", "szerda", "csütörtök", "péntek", "szombat", "vasárnap"]
HU_MONTHS = ["jan.", "febr.", "márc.", "ápr.", "máj.", "jún.", "júl.", "aug.", "szept.", "okt.", "nov.", "dec."]
TILE_ALIAS = {"drive-usb": "usb", "download": "settings", "power": "settings", "bell": "app", "dialog-information": "app"}
CLASS_ICONS = {"xterm": "terminal", "fusion-files": "files", "fusion-settings": "settings",
               "fusion-web": "web", "lightburn.exe": "laser"}


# ---------------------------------------------------------------------------
# D-Bus: org.freedesktop.Notifications (Desktop Notifications Specification 1.2)
# ---------------------------------------------------------------------------
INTROSPECT = """
<interface name="org.freedesktop.Notifications">
  <method name="GetCapabilities"><arg direction="out" type="as"/></method>
  <method name="Notify">
    <arg direction="in" type="s" name="app_name"/><arg direction="in" type="u" name="replaces_id"/>
    <arg direction="in" type="s" name="app_icon"/><arg direction="in" type="s" name="summary"/>
    <arg direction="in" type="s" name="body"/><arg direction="in" type="as" name="actions"/>
    <arg direction="in" type="a{sv}" name="hints"/><arg direction="in" type="i" name="expire_timeout"/>
    <arg direction="out" type="u"/>
  </method>
  <method name="CloseNotification"><arg direction="in" type="u" name="id"/></method>
  <method name="GetServerInformation">
    <arg direction="out" type="s" name="name"/><arg direction="out" type="s" name="vendor"/>
    <arg direction="out" type="s" name="version"/><arg direction="out" type="s" name="spec_version"/>
  </method>
  <signal name="NotificationClosed"><arg type="u" name="id"/><arg type="u" name="reason"/></signal>
  <signal name="ActionInvoked"><arg type="u" name="id"/><arg type="s" name="action_key"/></signal>
</interface>
"""


@pyqtClassInfo("D-Bus Interface", "org.freedesktop.Notifications")
@pyqtClassInfo("D-Bus Introspection", INTROSPECT)
class NotifyAdaptor(QDBusAbstractAdaptor):
    NotificationClosed = pyqtSignal("uint", "uint")
    ActionInvoked = pyqtSignal("uint", str)

    def __init__(self, parent, shell):
        super().__init__(parent)
        self.shell = shell
        self.setAutoRelaySignals(True)

    @pyqtSlot(result="QStringList")
    def GetCapabilities(self):
        return ["body", "actions", "persistence"]

    @pyqtSlot(str, "uint", str, str, str, "QStringList", "QVariantMap", int, result="uint")
    def Notify(self, app, replaces, icon, summary, body, actions, hints, timeout):
        urg = 1
        try:
            u = hints.get("urgency")
            urg = int(u) if u is not None else 1
        except (TypeError, ValueError):
            pass
        return self.shell.add_notification(app, int(replaces), icon, summary, body, list(actions), urg, timeout)

    @pyqtSlot("uint")
    def CloseNotification(self, nid):
        self.shell.close_notification(int(nid), 3)

    @pyqtSlot(QDBusMessage)
    def GetServerInformation(self, msg):
        # négy kimenő érték: késleltetett válasz a D-Bus-üzenetre
        msg.setDelayedReply(True)
        QDBusConnection.sessionBus().send(msg.createReply(["Fusion Shell", "FusionOS", "1.0", "1.2"]))


class NotifyObject(QObject):
    pass


# ---------------------------------------------------------------------------
# a Shell háttérrésze (a QML ezt látja: "shell")
# ---------------------------------------------------------------------------
class Shell(QObject):
    windowsChanged = pyqtSignal()
    clockChanged = pyqtSignal()
    wifiChanged = pyqtSignal()
    devicesChanged = pyqtSignal()
    notificationsChanged = pyqtSignal()
    toastsChanged = pyqtSignal()
    menuOpenChanged = pyqtSignal()
    appsChanged = pyqtSignal()
    popupChanged = pyqtSignal()
    soundChanged = pyqtSignal()
    _soundReady = pyqtSignal("QVariant")     # a figyelő szálból a fő szálra

    def __init__(self, app):
        super().__init__()
        self.app = app
        self.x = X11()
        self._windows = []
        self._clock = {"time": "", "date": "", "year": 0, "month": 0, "day": 0}
        self._wifi = {"state": "?", "ssid": "", "ok": False}
        self._devices = []           # [{"role","name","dev","present"}]
        self._media = []             # [{"name","path"}]
        self._notes = []             # értesítésközpont (legújabb elöl)
        self._toasts = []            # éppen látható buborékok
        self._next_id = 1
        self._menu_open = False
        self._popup = ""             # "center" | "calendar" | ""
        self._hidden_at = {}
        self._apps = []
        self._programs_mtime = None
        self._lid = ""
        self._sound = {"ok": False, "volume": 0, "mute": False, "sinks": [], "sources": [], "icon": "volume-mute"}
        self._soundReady.connect(self._set_sound)
        self._sound_dirty = threading.Event()
        self._syncing = False
        self._first = True
        self.reload_apps()
        self.dash = Dashboard(lambda icon, title, body="", urg=1: self.local_note(icon, title, body, None, urg))

    # --- tulajdonságok a QML-nek ---
    @pyqtProperty("QVariant", notify=windowsChanged)
    def windows(self):
        return self._windows

    @pyqtProperty("QVariant", notify=clockChanged)
    def clock(self):
        return self._clock

    @pyqtProperty("QVariant", notify=wifiChanged)
    def wifi(self):
        return self._wifi

    @pyqtProperty("QVariant", notify=devicesChanged)
    def devices(self):
        return self._devices

    @pyqtProperty("QVariant", notify=devicesChanged)
    def media(self):
        return self._media

    @pyqtProperty("QVariant", notify=notificationsChanged)
    def notifications(self):
        return self._notes

    @pyqtProperty(int, notify=notificationsChanged)
    def unread(self):
        return sum(1 for n in self._notes if not n["read"])

    @pyqtProperty("QVariant", notify=toastsChanged)
    def toasts(self):
        return self._toasts

    @pyqtProperty(bool, notify=menuOpenChanged)
    def menuOpen(self):
        return self._menu_open

    @pyqtProperty(str, notify=popupChanged)
    def popup(self):
        return self._popup

    @pyqtProperty("QVariant", notify=soundChanged)
    def sound(self):
        return self._sound

    # --- hang: a kiszolgáló eseményeire (pactl subscribe) frissül, nem lekérdezéssel ---
    def start_sound(self):
        def refresher():
            while True:
                self._sound_dirty.wait()
                time.sleep(0.08)           # egy hangerő-húzás sok eseménye → egy frissítés
                self._sound_dirty.clear()
                try:
                    st = fusion_sound.state()
                except Exception as e:
                    st = {"ok": False, "error": str(e), "sinks": [], "sources": [], "volume": 0, "mute": False}
                st["icon"] = fusion_sound.icon_for(st)
                self._soundReady.emit(st)

        def watcher():
            while True:
                self._sound_dirty.set()
                try:
                    p = subprocess.Popen(["pactl", "subscribe"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                         text=True, errors="replace", env=fusion_sound.ENV)
                    for line in p.stdout:
                        if " on sink" in line or " on source" in line or " on server" in line or " on card" in line:
                            self._sound_dirty.set()
                    p.wait()
                except OSError:
                    pass
                time.sleep(3)              # a kiszolgáló még nem fut / újraindult
        threading.Thread(target=refresher, daemon=True).start()
        threading.Thread(target=watcher, daemon=True).start()

    def _set_sound(self, st):
        if st != self._sound:
            self._sound = st
            self.soundChanged.emit()
            self.write_state()

    def _sound_do(self, fn, *args):
        threading.Thread(target=lambda: (fn(*args), self._sound_dirty.set()), daemon=True).start()

    @pyqtSlot(int)
    def soundStep(self, d):
        self._sound_do(fusion_sound.step, d)

    @pyqtSlot(int)
    def soundSet(self, v):
        self._sound_do(fusion_sound.set_volume, v)

    @pyqtSlot()
    def soundToggleMute(self):
        self._sound_do(fusion_sound.toggle_mute)

    @pyqtSlot(str)
    def soundSetSink(self, name):
        self._sound_do(fusion_sound.set_default, name)

    @pyqtSlot(int)
    def micSet(self, v):
        self._sound_do(fusion_sound.set_volume, v, True)

    @pyqtSlot()
    def micToggleMute(self):
        self._sound_do(fusion_sound.toggle_mute, True)

    @pyqtSlot()
    def soundTest(self):
        self._sound_do(fusion_sound.test_sound)

    @pyqtProperty("QVariant", notify=appsChanged)
    def apps(self):
        return self._apps

    @pyqtProperty("QVariant", notify=appsChanged)
    def groups(self):
        return fusion_apps.groups(self._apps)

    @pyqtProperty("QVariant", constant=True)
    def allGroups(self):
        return [{"id": g, "name": n, "icon": i} for g, n, i in fusion_apps.GROUPS]

    @pyqtSlot(str, str)
    def setAppGroup(self, app_id, group):
        """kézi csoport a Start menüben (üres: az automatikus)"""
        fusion_apps.set_group(app_id, group)
        self.reload_apps()

    @pyqtProperty(str, constant=True)
    def version(self):
        return ui.fusion_version()

    @pyqtProperty(str, constant=True)
    def user(self):
        return os.environ.get("USER") or "fusion"

    # --- ablakok ---
    def build_windows(self):
        sw, sh = self.x.screen_size()
        self.sw, self.sh = sw, sh
        ctx = [("shell", self), ("dash", self.dash)]

        def view(qml, title, flags):
            v = QQuickView()
            for k, o in ctx:
                v.rootContext().setContextProperty(k, o)
            v.rootContext().setContextProperty("fusionIconDir", QUrl.fromLocalFile(ui.ICON_DIR + "/").toString())
            v.engine().addImportPath(ui.QML_DIR)
            v.setTitle(title)
            v.setFlags(flags)
            v.setColor(QColor("#11161c"))      # nincs fehér villanás / rés
            v.setResizeMode(QQuickView.ResizeMode.SizeRootObjectToView)
            v.setSource(QUrl.fromLocalFile(os.path.join(QML, qml)))
            if v.status() == QQuickView.Status.Error:
                sys.exit("fusion-shell: " + "; ".join(e.toString() for e in v.errors()))
            return v

        F = Qt.WindowType
        # irányítópult: asztal típusú ablak a panel fölötti teljes területen, minden más ablak alatt
        self.desk = view("Desktop.qml", "Fusion Irányítópult", F.FramelessWindowHint | F.WindowStaysOnBottomHint)
        self.desk.setGeometry(0, 0, sw, sh - PANEL_HEIGHT)
        self.x.setup_desktop(int(self.desk.winId()))
        self.dash.tick_slow()
        if self.dash.enabled:
            self.desk.show()
        self.panel = view("Panel.qml", "Fusion Panel", F.FramelessWindowHint | F.WindowStaysOnTopHint | F.WindowDoesNotAcceptFocus)
        self.panel.setGeometry(0, sh - PANEL_HEIGHT, sw, PANEL_HEIGHT)
        self.x.setup_panel(int(self.panel.winId()), PANEL_HEIGHT)

        pop = F.FramelessWindowHint | F.WindowStaysOnTopHint
        self.menu = view("StartMenu.qml", "Fusion Start", pop)
        self.menu.setGeometry(0, sh - PANEL_HEIGHT - MENU_H, MENU_W, MENU_H)
        self.x.setup_floating(int(self.menu.winId()), "dialog")
        self.menu.activeChanged.connect(lambda: self._focus_lost(self.menu, "menu"))

        self.center = view("NotifyCenter.qml", "Fusion Értesítések", pop)
        self.center.setGeometry(sw - CENTER_W, sh - PANEL_HEIGHT - CENTER_H, CENTER_W, CENTER_H)
        self.x.setup_floating(int(self.center.winId()), "popup")
        self.center.activeChanged.connect(lambda: self._focus_lost(self.center, "center"))

        self.cal = view("Calendar.qml", "Fusion Naptár", pop)
        self.cal.setGeometry(sw - CAL_W, sh - PANEL_HEIGHT - CAL_H, CAL_W, CAL_H)
        self.x.setup_floating(int(self.cal.winId()), "popup")
        self.cal.activeChanged.connect(lambda: self._focus_lost(self.cal, "calendar"))

        self.snd = view("SoundPopup.qml", "Fusion Hang", pop)
        self.snd.setGeometry(sw - SOUND_W - 150, sh - PANEL_HEIGHT - SOUND_H, SOUND_W, SOUND_H)
        self.x.setup_floating(int(self.snd.winId()), "popup")
        self.snd.activeChanged.connect(lambda: self._focus_lost(self.snd, "sound"))
        self.snd.rootObject().implicitHeightChanged.connect(self._place_sound)
        self._place_sound()

        # buborék: felülíró (override-redirect) ablak — nem veszi el a fókuszt, nincs kerete
        self.toast = view("Toasts.qml", "Fusion értesítés", F.ToolTip | F.FramelessWindowHint | F.WindowStaysOnTopHint | F.WindowDoesNotAcceptFocus)
        self.toast.rootObject().implicitHeightChanged.connect(self._place_toast)
        self._ready = False
        self.panel.frameSwapped.connect(self._first_frame)
        self.panel.show()

    def _place_sound(self):
        sw, sh = self.x.screen_size()
        h = max(120, int(self.snd.rootObject().property("implicitHeight") or SOUND_H))
        self.snd.setGeometry(sw - SOUND_W - 150, sh - PANEL_HEIGHT - h, SOUND_W, h)

    def _first_frame(self):
        if not self._ready:
            self._ready = True
            try:
                with open(os.path.join(ui.RUNTIME, "fusion-shell.ready"), "w") as f:
                    f.write(f"{time.time():.3f}\n")
            except OSError:
                pass
            self.write_state()

    def _focus_lost(self, v, name):
        if not v.isActive() and v.isVisible():
            v.hide()
            self._hidden_at[name] = time.monotonic()
            if name == "menu":
                self._set_menu(False)
            elif self._popup == name:
                self._popup = ""
                self.popupChanged.emit()
            self.write_state()

    def _recent(self, name):
        return time.monotonic() - self._hidden_at.get(name, 0) < 0.35

    def _set_menu(self, on):
        if self._menu_open != on:
            self._menu_open = on
            self.menuOpenChanged.emit()

    # --- Start menü ---
    @pyqtSlot()
    def toggleMenu(self):
        if self.menu.isVisible():
            self.hideMenu()
        elif not self._recent("menu"):
            self.reload_apps()
            self.menu.rootObject().reset()
            self.menu.show(); self.menu.raise_(); self.menu.requestActivate()
            self._set_menu(True)
        self.write_state()

    @pyqtSlot()
    def hideMenu(self):
        if self.menu.isVisible():
            self.menu.hide()
        self._set_menu(False)
        self.write_state()

    def tick_programs(self):
        """a Programkezelő változásai: új / eltávolított program (a /data/programs mappája), illetve
        kívülről (parancssorból) telepített Flatpak — ez utóbbi előbb leírást kap (sync, külön szálon)"""
        try:
            m = os.stat(fusion_apps.fp.PROGRAMS).st_mtime_ns if fusion_apps.fp else 0
        except OSError:
            m = 0
        if fusion_apps.fp and fusion_apps.fp.changed_outside() and not self._syncing:
            self._syncing = True

            def work():
                try:
                    fusion_apps.fp.sync()
                except Exception:
                    pass
                self._syncing = False
            threading.Thread(target=work, daemon=True).start()
        if m != self._programs_mtime:
            self._programs_mtime = m
            self.reload_apps()

    def reload_apps(self):
        apps = fusion_apps.load()
        if apps != self._apps:
            self._apps = apps
            self.appsChanged.emit()

    @pyqtSlot(str)
    def launch(self, app_id):
        for a in self._apps:
            if a["id"] == app_id:
                ui.spawn(a["exec"])
                try:
                    fusion_apps.record_launch(app_id)
                except OSError:
                    pass
                break
        self.hideMenu()

    @pyqtSlot(str)
    def run(self, cmd):
        ui.spawn(cmd)
        self.hideMenu()
        self._hide_popups()

    @pyqtSlot(str)
    def power(self, action):
        self.hideMenu()
        if action == "logout":
            # a munkamenet vége: az ablakkezelő kilép → az X leáll → újra bejelentkezik (automatikus)
            ui.run(["pkill", "-TERM", "-u", str(os.getuid()), "-x", "jwm"])
        elif action in ("reboot", "poweroff"):
            rc, out = ui.admin("power", action)
            if rc != 0:
                self.add_notification("FusionOS", 0, "power", "Nem sikerült: " + action, out.strip()[:200], [], 2, -1)

    # --- felugrók: értesítésközpont, naptár ---
    def _hide_popups(self):
        for name, v in (("center", self.center), ("calendar", self.cal), ("sound", self.snd)):
            if v.isVisible():
                v.hide()
        if self._popup:
            self._popup = ""
            self.popupChanged.emit()

    @pyqtSlot(str)
    def togglePopup(self, name):
        v = {"center": self.center, "calendar": self.cal, "sound": self.snd}[name]
        if v.isVisible():
            self._hide_popups()
        elif not self._recent(name):
            self._hide_popups()
            self.hideMenu()
            if name == "calendar":
                self.cal.rootObject().reset()
            # a felugró ablak idejére a buborékok eltűnnek (az értesítésközpontban úgyis látszanak)
            if self._toasts:
                self._toasts = []
                self.toastsChanged.emit()
                self._show_toast()
            v.show(); v.raise_(); v.requestActivate()
            self._popup = name
            self.popupChanged.emit()
            if name == "center":
                for n in self._notes:
                    n["read"] = True
                self._notes = list(self._notes)
                self.notificationsChanged.emit()
        self.write_state()

    # --- tálca ---
    @pyqtSlot(int)
    def toggleWindow(self, wid):
        self.x.toggle(wid)
        QTimer.singleShot(120, self.poll_windows)

    @pyqtSlot(int)
    def closeWindow(self, wid):
        self.x.close(wid)
        QTimer.singleShot(200, self.poll_windows)

    def poll_windows(self):
        try:
            self.x.pending()
            w = self.x.windows(skip_pids=(os.getpid(),))
        except Exception:
            return
        for i in w:
            i["icon"] = CLASS_ICONS.get(i["cls"].lower(), CLASS_ICONS.get(i["inst"].lower(), "app"))
        if w != self._windows:
            self._windows = w
            self.windowsChanged.emit()
            self.write_state()

    # --- értesítések ---
    def add_notification(self, app, replaces, icon, summary, body, actions, urgency, timeout, local_action=None):
        now = time.strftime("%H:%M")
        if replaces:
            nid = replaces
            self._notes = [n for n in self._notes if n["id"] != nid]
            self._toasts = [t for t in self._toasts if t["id"] != nid]
        else:
            nid = self._next_id
            self._next_id += 1
        acts = [{"key": actions[i], "label": actions[i + 1]} for i in range(0, len(actions) - 1, 2)]
        tile = TILE_ALIAS.get(icon, icon)
        if not tile or "/" in tile or not os.path.exists(os.path.join(ui.ICON_DIR, f"app-{tile}.svg")):
            tile = "app"
        n = {"id": nid, "app": app or "", "icon": icon or "bell", "tile": tile, "summary": summary or "", "body": body or "",
             "actions": [a for a in acts if a["key"] != "default"], "hasDefault": any(a["key"] == "default" for a in acts),
             "urgency": urgency, "time": now, "read": self._popup == "center", "local": local_action or ""}
        self._notes = ([n] + self._notes)[:50]
        self.notificationsChanged.emit()
        # buborék: kritikus marad, amíg be nem zárják; egyébként a kért ideig (alapból 6 mp)
        self._toasts = ([n] + self._toasts)[:3]
        self.toastsChanged.emit()
        ms = 6000 if timeout is None or timeout < 0 else timeout
        if urgency < 2 and ms > 0:
            QTimer.singleShot(ms, lambda: self._expire(nid))
        self._show_toast()
        self.write_state(last=n)
        return nid

    def _expire(self, nid):
        if any(t["id"] == nid for t in self._toasts):
            self._toasts = [t for t in self._toasts if t["id"] != nid]
            self.toastsChanged.emit()
            self.notify_obj_adaptor.NotificationClosed.emit(nid, 1)
            self._show_toast()
            self.write_state()

    def close_notification(self, nid, reason=2):
        before = len(self._toasts) + len(self._notes)
        self._toasts = [t for t in self._toasts if t["id"] != nid]
        self._notes = [n for n in self._notes if n["id"] != nid]
        if len(self._toasts) + len(self._notes) != before:
            self.toastsChanged.emit()
            self.notificationsChanged.emit()
            self.notify_obj_adaptor.NotificationClosed.emit(nid, reason)
            self._show_toast()
            self.write_state()

    @pyqtSlot(int)
    def dismissToast(self, nid):
        self._toasts = [t for t in self._toasts if t["id"] != nid]
        self.toastsChanged.emit()
        self._show_toast()
        self.write_state()

    @pyqtSlot(int)
    def dismiss(self, nid):
        self.close_notification(nid, 2)

    @pyqtSlot()
    def clearAll(self):
        for n in list(self._notes):
            self.notify_obj_adaptor.NotificationClosed.emit(n["id"], 2)
        self._notes = []
        self._toasts = []
        self.notificationsChanged.emit()
        self.toastsChanged.emit()
        self._show_toast()
        self.write_state()

    @pyqtSlot(int, str)
    def invoke(self, nid, key):
        for n in self._notes:
            if n["id"] == nid:
                if n["local"]:
                    ui.spawn(n["local"])
                else:
                    self.notify_obj_adaptor.ActionInvoked.emit(nid, key or "default")
                break
        self._hide_popups()
        self.close_notification(nid, 2)

    def _show_toast(self):
        if self._toasts:
            self._place_toast()
            if not self.toast.isVisible():
                self.toast.show()
            self.toast.raise_()
        elif self.toast.isVisible():
            self.toast.hide()

    def _place_toast(self):
        h = max(10, int(self.toast.rootObject().property("implicitHeight") or 10))
        self.toast.setGeometry(self.sw - TOAST_W - 10, self.sh - PANEL_HEIGHT - h - 10, TOAST_W, h)

    def local_note(self, icon, summary, body="", action=None, urgency=1):
        self.add_notification("FusionOS", 0, icon, summary, body, [], urgency, -1, local_action=action)

    # --- időzített lekérdezések ---
    def tick_clock(self):
        t = time.localtime()
        c = {"time": time.strftime("%H:%M", t),
             "date": f"{t.tm_year}. {HU_MONTHS[t.tm_mon - 1]} {t.tm_mday}.",
             "long": f"{t.tm_year}. {HU_MONTHS[t.tm_mon - 1]} {t.tm_mday}., {HU_DAYS[t.tm_wday]}",
             "year": t.tm_year, "month": t.tm_mon, "day": t.tm_mday}
        if c != self._clock:
            self._clock = c
            self.clockChanged.emit()

    def tick_wifi(self):
        st = fusion_net.state()
        w = {"ok": st.get("ok", False), "state": st.get("state", ""), "ssid": st.get("ssid", ""),
             "device": st.get("device", ""), "ip": st.get("ip", ""), "level": 0}
        if w["state"] == "connected":
            for n in fusion_net.networks(st):
                if n["connected"]:
                    w["level"] = n["level"]
                    break
        old = self._wifi
        if w != old:
            self._wifi = w
            self.wifiChanged.emit()
            if not self._first and old.get("state") != w["state"]:
                if w["state"] == "connected":
                    self.local_note("wifi", "Wi-Fi: kapcsolódva", w["ssid"] + (f"  ({w['ip']})" if w["ip"] else ""))
                elif old.get("state") == "connected":
                    self.local_note("wifi", "Wi-Fi: a kapcsolat megszakadt", old.get("ssid", ""), "fusion-settings wifi")

    def tick_lid(self, devs):
        """fedél: ha lecsukták, de a gép ébren marad (lézer / nyomtató csatlakozik → fusion-keepawake),
        a kijelző kikapcsol; felnyitáskor visszakapcsol"""
        state = ""
        for f in glob.glob("/proc/acpi/button/lid/*/state"):
            try:
                state = open(f).read().split(":")[-1].strip()
            except OSError:
                pass
        if not state or state == self._lid:
            return
        prev, self._lid = self._lid, state
        if state == "closed" and prev == "open":
            # külső kijelzővel a munka a külső képernyőn folytatódik — ott nem kapcsolunk ki semmit
            rc, out = ui.run(["xrandr", "--query"], timeout=3)
            if out.count(" connected") <= 1:
                ui.run(["xset", "+dpms"], timeout=3)
                ui.run(["xset", "dpms", "force", "off"], timeout=3)
            names = [d["name"] for d in devs if d["present"]]
            if names:
                self.local_note("laser" if any(d["role"] == "laser" and d["present"] for d in devs) else "printer",
                                "Fedél lecsukva — a gép ébren marad", ", ".join(names) + " csatlakoztatva; a kijelző kikapcsolt")
        elif prev == "closed":
            ui.run(["xset", "dpms", "force", "on"], timeout=3)
            ui.run(["xset", "s", "off", "-dpms"], timeout=3)

    def tick_devices(self):
        devs = fdev.present()      # Fusion API: minden .role szerep (egy új szerep kódváltozás nélkül megjelenik)
        media = []
        try:
            with open("/proc/self/mounts") as f:
                for line in f:
                    parts = line.split()
                    mp = parts[1].replace("\\040", " ")
                    if mp.startswith(MEDIA_DIR + "/"):
                        media.append({"name": os.path.basename(mp), "path": mp})
        except OSError:
            pass
        self.tick_lid(devs)
        if devs != self._devices or media != self._media:
            if not self._first:
                old = {d["role"]: d for d in self._devices}
                for d in devs:
                    o = old.get(d["role"])
                    if o and o["present"] != d["present"]:
                        if d["present"]:
                            self.local_note(d["role"], f"{d['name']}: csatlakoztatva", f"{d['dev']} — /dev/fusion/{d['role']}")
                        else:
                            self.local_note(d["role"], f"{d['name']}: leválasztva", "", "fusion-settings devices")
                oldm = {m["path"] for m in self._media}
                for m in media:
                    if m["path"] not in oldm:
                        self.local_note("drive-usb", f"Meghajtó csatlakoztatva: {m['name']}",
                                        "Kattintson a megnyitáshoz", f"fusion-files {m['path']}")
                newm = {m["path"] for m in media}
                for m in self._media:
                    if m["path"] not in newm:
                        self.local_note("drive-usb", f"Meghajtó leválasztva: {m['name']}")
            self._devices, self._media = devs, media
            self.devicesChanged.emit()

    def tick_dash(self):
        self.dash.tick_slow()
        if self.dash.enabled and not self.desk.isVisible():
            self.desk.show()
        elif not self.dash.enabled and self.desk.isVisible():
            self.desk.hide()

    def startup_notes(self):
        if os.path.exists("/run/fusion/image-changed"):
            self.local_note("download", "FusionOS frissült", ui.fusion_version())
        self._first = False

    def write_state(self, last=None):
        st = {"pid": os.getpid(), "ready": getattr(self, "_ready", False), "menu": self._menu_open,
              "popup": self._popup, "windows": len(self._windows), "notifications": len(self._notes),
              "dashboard": bool(getattr(self, "desk", None) and self.desk.isVisible()), "printer": self.dash.printer.get("state", ""),
              "unread": self.unread, "toasts": len(self._toasts),
              "wifi": self._wifi.get("state", ""), "devices": [d["role"] for d in self._devices if d["present"]],
              "media": [m["path"] for m in self._media],
              "sound": {"ok": self._sound.get("ok", False), "volume": self._sound.get("volume", 0), "mute": self._sound.get("mute", False),
                        "sinks": len(self._sound.get("sinks", [])), "server": self._sound.get("server", "")}}
        if last is not None:
            st["last"] = {"app": last["app"], "summary": last["summary"], "body": last["body"]}
        else:
            old = ui.load_json(STATE_FILE, {})
            if "last" in old:
                st["last"] = old["last"]
        ui.save_json(STATE_FILE, st)


def main():
    app, _engine = ui.create_app("fusion-shell", "Fusion Shell", "app")
    app.setQuitOnLastWindowClosed(False)
    shell = Shell(app)

    # értesítés-szolgáltatás a munkamenet-buszon
    bus = QDBusConnection.sessionBus()
    nobj = NotifyObject()
    shell.notify_obj_adaptor = NotifyAdaptor(nobj, shell)
    if not bus.isConnected():
        print("fusion-shell: nincs munkamenet-busz (D-Bus) — értesítések csak belsőleg", file=sys.stderr)
    elif not bus.registerObject("/org/freedesktop/Notifications", nobj):
        print("fusion-shell: az értesítés-objektum nem regisztrálható", file=sys.stderr)
    elif not bus.registerService("org.freedesktop.Notifications"):
        print("fusion-shell: az org.freedesktop.Notifications már foglalt", file=sys.stderr)

    shell.build_windows()
    ui.on_signal(app, signal.SIGUSR1, shell.toggleMenu)
    try:
        with open(os.path.join(ui.RUNTIME, "fusion-shell.pid"), "w") as f:
            f.write(f"{os.getpid()}\n")
    except OSError:
        pass

    shell.tick_clock(); shell.poll_windows(); shell.tick_devices(); shell.tick_wifi(); shell.start_sound()
    shell.startup_notes()
    shell.write_state()
    timers = []
    for ms, fn in ((1000, shell.tick_clock), (500, shell.poll_windows), (2000, shell.tick_devices), (5000, shell.tick_wifi),
                   (2000, shell.dash.tick_fast), (5000, shell.tick_dash), (3000, shell.tick_programs)):
        t = QTimer(app)
        t.timeout.connect(fn)
        t.start(ms)
        timers.append(t)
    app._timers = timers

    # Lomtár: automatikus ürítés a beállítás szerint (Beállítások → Rendszer) — 1 perc után, majd 6 óránként, háttérszálon
    def trash_auto():
        def work():
            try:
                import fusion_trash
                n = fusion_trash.auto_purge()
                if n:
                    print(f"fusion-shell: Lomtár — {n} régi elem automatikusan törölve", flush=True)
            except Exception as e:      # a Lomtár hibája nem állíthatja meg a Shellt
                print(f"fusion-shell: Lomtár automatikus ürítése: {e}", flush=True)
        threading.Thread(target=work, daemon=True).start()
    QTimer.singleShot(60000, trash_auto)
    tt = QTimer(app)
    tt.timeout.connect(trash_auto)
    tt.start(6 * 3600 * 1000)
    timers.append(tt)

    def teardown():
        """leállításkor (pl. újraindítás a rajzolási mód váltása után) előbb a QML-felületek ürülnek ki, amíg a
        Shell-objektum még él — különben a kötések „Cannot read property … of null” sorokkal töltik a naplót"""
        for t in timers:
            t.stop()
        for name in ("toast", "snd", "cal", "center", "menu", "panel", "desk"):
            v = getattr(shell, name, None)
            if v is not None:
                v.hide()
                v.setSource(QUrl())
    app.aboutToQuit.connect(teardown)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
