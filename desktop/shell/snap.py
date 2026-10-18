"""Fúzió Shell — ablakok igazítása a képernyő széléhez (0.0.55)

Az ablakot a címsoránál fogva a képernyő bal / jobb szélére húzva a terület fele, a felső szélére húzva a teljes
terület lesz (a panel fölött). Húzás közben keret mutatja, hová kerül. Egy igazított ablakot elhúzva a szélről
visszakapja a korábbi méretét. Ablakkezelőtől független: EWMH (_NET_MOVERESIZE_WINDOW, _NET_WM_STATE, _NET_WORKAREA).

Működés: a mutató helyét figyeli (XQueryPointer); ha a bal gomb le van nyomva és közben az aktív ablak helye
megváltozik, az ablakot húzzák — ilyenkor a mutató a szélen kijelöli a célterületet, a gomb elengedésekor az ablak
oda kerül. Más esetben nem csinál semmit (nincs billentyű- vagy egérfoglalás).
"""
import os

from PyQt6.QtCore import QObject, QRect, QTimer, QUrl
from PyQt6.QtGui import QColor, QRegion
from PyQt6.QtQuick import QQuickView

from fusion.x11 import X11

EDGE = 2           # képpont: ennyire a széltől számít a mutató a szélen
IDLE_MS, DRAG_MS = 120, 40
BORDER = 4         # az előnézeti keret vastagsága


class Snapper(QObject):
    def __init__(self, qml_dir, parent=None):
        super().__init__(parent)
        self.x = X11()
        self.qml_dir = qml_dir
        self.down = False
        self.wid = 0
        self.start = None          # a húzott ablak kerete a gomb lenyomásakor
        self.moving = False
        self.start_max = False
        self.zone = ""
        self.snapped = {}          # ablak → (eredeti szélesség, magasság, igazított szélesség, magasság)
        self.preview = None
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(IDLE_MS)

    # --- előnézet: csak a keret látszik (a köztes rész átlátszó: maszk) ---
    def _show_preview(self, r):
        if self.preview is None:
            v = QQuickView()
            v.setTitle("Fusion Snap")
            from PyQt6.QtCore import Qt
            F = Qt.WindowType
            v.setFlags(F.FramelessWindowHint | F.WindowStaysOnTopHint | F.WindowDoesNotAcceptFocus | F.WindowTransparentForInput)
            v.setColor(QColor("#2f81f7"))
            v.setSource(QUrl.fromLocalFile(os.path.join(self.qml_dir, "SnapPreview.qml")))
            self.preview = v
        x, y, w, h = r
        self.preview.setGeometry(x, y, w, h)
        outer = QRegion(QRect(0, 0, w, h))
        inner = QRegion(QRect(BORDER, BORDER, max(1, w - 2 * BORDER), max(1, h - 2 * BORDER)))
        self.preview.setMask(outer.subtracted(inner))
        if not self.preview.isVisible():
            self.preview.show()

    def _hide_preview(self):
        if self.preview is not None and self.preview.isVisible():
            self.preview.hide()

    def _zone_rect(self, zone):
        ax, ay, aw, ah = self.x.workarea()
        return {"left": (ax, ay, aw // 2, ah), "right": (ax + aw - aw // 2, ay, aw // 2, ah), "max": (ax, ay, aw, ah)}[zone]

    def _zone_at(self, px, py):
        sw, _sh = self.x.screen_size()
        if py <= EDGE:
            return "max"
        if px <= EDGE:
            return "left"
        if px >= sw - 1 - EDGE:
            return "right"
        return ""

    def tick(self):
        try:
            px, py, b1 = self.x.pointer()
            if b1 and not self.down:                       # gomb le: melyik ablak, hol van
                self.down, self.moving, self.zone = True, False, ""
                self.wid = self.x.active()
                self.start = self.x.frame(self.wid)[0] if self.wid else None
                self.start_max = bool(self.wid) and self.x.is_maximized(self.wid)
                self.timer.setInterval(DRAG_MS)
            elif b1 and self.down and self.wid:
                if not self.moving:
                    cur = self.x.frame(self.wid)[0]
                    # helyváltozás változatlan mérettel = mozgatás (az átméretezés nem számít); a teljes méretű ablakot
                    # húzáskor az ablakkezelő maga visszaállítja — ott a méret is változik
                    self.moving = self.start is not None and cur[:2] != self.start[:2] and (cur[2:] == self.start[2:] or self.start_max)
                if self.moving:
                    z = self._zone_at(px, py)
                    if z != self.zone:
                        self.zone = z
                        if z:
                            self._show_preview(self._zone_rect(z))
                        else:
                            self._hide_preview()
            elif not b1 and self.down:                     # gomb fel
                self.down = False
                self.timer.setInterval(IDLE_MS)
                self._hide_preview()
                if self.moving and self.wid:
                    self._release(self.wid, self.zone)
                self.zone = ""
            self.x.pending()
        except Exception:
            self.down, self.moving, self.zone = False, False, ""
            self._hide_preview()

    def _release(self, wid, zone):
        (fx, fy, fw, fh), _ext = self.x.frame(wid)
        if zone:
            if wid not in self.snapped:
                self.snapped[wid] = (fw, fh)
            if zone == "max":
                self.x.set_maximized(wid, True)
            else:
                if self.x.is_maximized(wid):
                    self.x.set_maximized(wid, False)
                self.x.place(wid, *self._zone_rect(zone))
        elif wid in self.snapped:                          # elhúzták a szélről: vissza a korábbi méretre
            ow, oh = self.snapped.pop(wid)
            if self.x.is_maximized(wid):
                self.x.set_maximized(wid, False)
            self.x.place(wid, fx, fy, ow, oh)
