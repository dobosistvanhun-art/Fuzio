"""Fúzió Shell — a kijelző kikapcsolása tétlenség után, és az ébren tartás (videó) fogadása

org.freedesktop.ScreenSaver (a /org/freedesktop/ScreenSaver és a /ScreenSaver objektumon): a programok (Firefox,
VLC, a Flatpak-portál) Inhibit-tel kérik, hogy a kijelző ne kapcsoljon ki, UnInhibit-tel engedik el; ha a kérő
kilép (vagy összeomlik), a kérése magától megszűnik. Amíg van kérés, a DPMS ki van kapcsolva; utána a beállított
idő (Beállítások → Rendszer → Energia) újra érvényes. Az időt maga az X-kiszolgáló méri (fusion.screen).
"""
import itertools

from PyQt6.QtCore import QObject, pyqtClassInfo, pyqtSlot
from PyQt6.QtDBus import QDBusAbstractAdaptor, QDBusConnection, QDBusMessage, QDBusServiceWatcher

from fusion import screen as fscreen

SERVICE = "org.freedesktop.ScreenSaver"
PATHS = ("/org/freedesktop/ScreenSaver", "/ScreenSaver")
INTROSPECT = """
<interface name="org.freedesktop.ScreenSaver">
  <method name="Inhibit">
    <arg direction="in" type="s" name="application_name"/><arg direction="in" type="s" name="reason_for_inhibit"/>
    <arg direction="out" type="u" name="cookie"/>
  </method>
  <method name="UnInhibit"><arg direction="in" type="u" name="cookie"/></method>
  <method name="SimulateUserActivity"/>
  <method name="GetActive"><arg direction="out" type="b"/></method>
</interface>
"""


@pyqtClassInfo("D-Bus Interface", SERVICE)
@pyqtClassInfo("D-Bus Introspection", INTROSPECT)
class ScreenSaverAdaptor(QDBusAbstractAdaptor):
    def __init__(self, parent, guard):
        super().__init__(parent)
        self.guard = guard

    @pyqtSlot(str, str, QDBusMessage, result="uint")
    def Inhibit(self, app, reason, msg):
        return self.guard.inhibit(app, reason, msg.service())

    @pyqtSlot("uint", QDBusMessage)
    @pyqtSlot(int, QDBusMessage)          # néhány kliens előjeles egészként küldi a sütit
    def UnInhibit(self, cookie, msg):
        self.guard.uninhibit(int(cookie))

    @pyqtSlot()
    def SimulateUserActivity(self):
        self.guard.activity()

    @pyqtSlot(result=bool)
    def GetActive(self):
        return False


class ScreenGuard(QObject):
    def __init__(self, parent=None, bus=None):
        super().__init__(parent)
        self.bus = bus if bus is not None else QDBusConnection.sessionBus()
        self._cookies = itertools.count(1)
        self._inhibit = {}           # süti → {app, reason, sender}
        self._objs = []
        self._watch = QDBusServiceWatcher(self)
        self._watch.setConnection(self.bus)
        self._watch.setWatchMode(QDBusServiceWatcher.WatchModeFlag.WatchForUnregistration)
        self._watch.serviceUnregistered.connect(self._gone)
        self.registered = False
        self.last = []               # az utolsó tick xset-parancsai (napló / önteszt)

    def register(self):
        """a D-Bus-szolgáltatás; hiba esetén szöveg (a Shell attól még fut)"""
        if not self.bus.isConnected():
            return "nincs munkamenet-busz (D-Bus) — a programok ébren tartási kérése nem érkezik meg"
        for p in PATHS:
            o = QObject(self)
            o._adaptor = ScreenSaverAdaptor(o, self)
            if not self.bus.registerObject(p, o):
                return f"a {p} objektum nem regisztrálható"
            self._objs.append(o)
        if not self.bus.registerService(SERVICE):
            return f"az {SERVICE} már foglalt"
        self.registered = True
        return ""

    def inhibit(self, app, reason, sender=""):
        c = next(self._cookies)
        self._inhibit[c] = {"app": str(app)[:60], "reason": str(reason)[:120], "sender": sender}
        if sender:
            self._watch.addWatchedService(sender)
        print(f"fusion-shell: kijelző ébren tartva — {app}: {reason} (#{c})", flush=True)
        self.tick()
        return c

    def uninhibit(self, cookie):
        d = self._inhibit.pop(cookie, None)
        if d:
            print(f"fusion-shell: ébren tartás vége — {d['app']} (#{cookie})", flush=True)
            self._unwatch(d["sender"])
            self.tick()

    def _unwatch(self, sender):
        if sender and not any(v["sender"] == sender for v in self._inhibit.values()):
            self._watch.removeWatchedService(sender)

    def _gone(self, sender):
        gone = [c for c, v in self._inhibit.items() if v["sender"] == sender]
        for c in gone:
            print(f"fusion-shell: ébren tartás vége (a program kilépett) — {self._inhibit[c]['app']} (#{c})", flush=True)
            del self._inhibit[c]
        self._watch.removeWatchedService(sender)
        if gone:
            self.tick()

    def activity(self):
        q = fscreen.query()
        if q and q["monitor"] == "On":
            fscreen._xset("s", "reset")

    def inhibited(self):
        return bool(self._inhibit)

    def tick(self):
        self.last = fscreen.apply(fscreen.off_minutes(), self.inhibited())
        return self.last

    def state(self):
        return {"offMinutes": fscreen.off_minutes(), "service": self.registered,
                "inhibit": [{"app": v["app"], "reason": v["reason"]} for v in self._inhibit.values()]}
