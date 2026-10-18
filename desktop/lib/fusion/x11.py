"""Fúzió — Fúzió API: ablakok (X11, EWMH) — a Fúzió Shell és a Feladatkezelő közös alapja (M8)

A Fúzió Shell ezen át látja és kezeli az ablakokat — ablakkezelőtől függetlenül,
az EWMH szabvány szerint (_NET_CLIENT_LIST, _NET_ACTIVE_WINDOW, _NET_CLOSE_WINDOW):
  - ablaklista a tálcához (cím, osztály, aktív, kis méretre tett), az ablak saját ikonja
  - ablak aktiválása, kis méretre tétele, bezárása
  - a Shell saját ablakainak típusa: panel (dock + képernyősáv-foglalás),
    lebegő ablak (Start menü, értesítés, felugró)
  - asztalok (munkaterületek, 0.0.54): az aktuális asztal, váltás, ablak áthelyezése másik asztalra
    (_NET_CURRENT_DESKTOP, _NET_NUMBER_OF_DESKTOPS, _NET_WM_DESKTOP)
"""
from Xlib import X, Xatom, display, protocol

PANEL_HEIGHT = 40

ATOMS = ("_NET_CLIENT_LIST", "_NET_ACTIVE_WINDOW", "_NET_WM_NAME", "UTF8_STRING",
         "_NET_WM_WINDOW_TYPE", "_NET_WM_WINDOW_TYPE_DOCK", "_NET_WM_WINDOW_TYPE_NORMAL",
         "_NET_WM_WINDOW_TYPE_DIALOG", "_NET_WM_WINDOW_TYPE_NOTIFICATION",
         "_NET_WM_WINDOW_TYPE_POPUP_MENU", "_NET_WM_WINDOW_TYPE_UTILITY",
         "_NET_WM_STATE", "_NET_WM_STATE_SKIP_TASKBAR", "_NET_WM_STATE_SKIP_PAGER",
         "_NET_WM_STATE_ABOVE", "_NET_WM_STATE_HIDDEN", "_NET_WM_STRUT", "_NET_WM_STRUT_PARTIAL",
         "WM_CHANGE_STATE", "_NET_WM_DESKTOP", "_NET_CLOSE_WINDOW", "_NET_WM_PID",
         "_NET_WM_WINDOW_TYPE_DESKTOP", "_NET_WM_STATE_BELOW",
         "WM_PROTOCOLS", "_NET_WM_PING", "WM_DELETE_WINDOW", "_NET_WM_ICON",
         "_NET_CURRENT_DESKTOP", "_NET_NUMBER_OF_DESKTOPS", "_NET_WM_STATE_STICKY",
         "_NET_WORKAREA", "_NET_FRAME_EXTENTS", "_NET_MOVERESIZE_WINDOW",
         "_NET_WM_STATE_MAXIMIZED_VERT", "_NET_WM_STATE_MAXIMIZED_HORZ")
ALL_DESKTOPS = 0xFFFFFFFF


class X11:
    def __init__(self, events=False):
        """events=True: a gyökérablak szerkezeti eseményei is (a Feladatkezelő pingjéhez)"""
        self.d = display.Display()
        self.root = self.d.screen().root
        self.a = {n: self.d.intern_atom(n) for n in ATOMS}
        if events:
            self.root.change_attributes(event_mask=X.SubstructureNotifyMask)

    def screen_size(self):
        g = self.root.get_geometry()
        return g.width, g.height

    def pending(self):
        """az X-kapcsolat eseményeit kiürítjük (csak kérdezünk, eseményre nem figyelünk)"""
        while self.d.pending_events():
            self.d.next_event()

    def fileno(self):
        return self.d.fileno()

    # --- a Shell saját ablakai ---
    def _set_atoms(self, win, prop, atoms):
        win.change_property(self.a[prop], Xatom.ATOM, 32, [self.a[x] for x in atoms])

    def setup_panel(self, xid, height=PANEL_HEIGHT):
        """dock típus + a képernyő alján foglalt sáv (az ablakkezelő nem tesz alá ablakot)"""
        w, _h = self.screen_size()
        win = self.d.create_resource_object("window", xid)
        self._set_atoms(win, "_NET_WM_WINDOW_TYPE", ["_NET_WM_WINDOW_TYPE_DOCK"])
        self._set_atoms(win, "_NET_WM_STATE", ["_NET_WM_STATE_SKIP_TASKBAR", "_NET_WM_STATE_SKIP_PAGER", "_NET_WM_STATE_ABOVE"])
        win.change_property(self.a["_NET_WM_STRUT"], Xatom.CARDINAL, 32, [0, 0, 0, height])
        win.change_property(self.a["_NET_WM_STRUT_PARTIAL"], Xatom.CARDINAL, 32,
                            [0, 0, 0, height, 0, 0, 0, 0, 0, 0, 0, w - 1])
        win.change_property(self.a["_NET_WM_DESKTOP"], Xatom.CARDINAL, 32, [0xFFFFFFFF])
        self.d.flush()

    def setup_desktop(self, xid):
        """az irányítópult: asztal típusú ablak — minden más ablak alatt, a tálcán nem látszik"""
        win = self.d.create_resource_object("window", xid)
        self._set_atoms(win, "_NET_WM_WINDOW_TYPE", ["_NET_WM_WINDOW_TYPE_DESKTOP"])
        self._set_atoms(win, "_NET_WM_STATE", ["_NET_WM_STATE_SKIP_TASKBAR", "_NET_WM_STATE_SKIP_PAGER", "_NET_WM_STATE_BELOW"])
        win.change_property(self.a["_NET_WM_DESKTOP"], Xatom.CARDINAL, 32, [0xFFFFFFFF])
        self.d.flush()

    def setup_floating(self, xid, kind="dialog"):
        """Start menü, értesítés, felugró: nincs a tálcán, mindig felül"""
        t = {"dialog": "_NET_WM_WINDOW_TYPE_DIALOG", "notification": "_NET_WM_WINDOW_TYPE_NOTIFICATION",
             "popup": "_NET_WM_WINDOW_TYPE_UTILITY"}[kind]
        win = self.d.create_resource_object("window", xid)
        self._set_atoms(win, "_NET_WM_WINDOW_TYPE", [t])
        self._set_atoms(win, "_NET_WM_STATE", ["_NET_WM_STATE_SKIP_TASKBAR", "_NET_WM_STATE_SKIP_PAGER", "_NET_WM_STATE_ABOVE"])
        win.change_property(self.a["_NET_WM_DESKTOP"], Xatom.CARDINAL, 32, [ALL_DESKTOPS])    # minden asztalon
        self.d.flush()

    # --- asztalok (munkaterületek) ---
    def desktop(self):
        """(aktuális asztal 0-tól, asztalok száma)"""
        cur = self._prop(self.root, "_NET_CURRENT_DESKTOP")
        num = self._prop(self.root, "_NET_NUMBER_OF_DESKTOPS")
        return (int(cur[0]) if cur is not None and len(cur) else 0), (int(num[0]) if num is not None and len(num) else 1)

    def set_desktop(self, n):
        cur, num = self.desktop()
        if 0 <= n < num and n != cur:
            ev = protocol.event.ClientMessage(window=self.root, client_type=self.a["_NET_CURRENT_DESKTOP"],
                                              data=(32, [n, X.CurrentTime, 0, 0, 0]))
            self.root.send_event(ev, event_mask=X.SubstructureRedirectMask | X.SubstructureNotifyMask)
            self.d.flush()

    def window_desktop(self, wid):
        v = self._prop(self.d.create_resource_object("window", int(wid)), "_NET_WM_DESKTOP")
        return int(v[0]) if v is not None and len(v) else ALL_DESKTOPS

    def move_to_desktop(self, wid, n):
        """az ablak áthelyezése az n. asztalra (EWMH: _NET_WM_DESKTOP kérés az ablakkezelőnek)"""
        self._client_msg(wid, "_NET_WM_DESKTOP", [n, 2, 0, 0, 0])

    # --- ablakok igazítása a képernyő széléhez (0.0.55) ---
    def pointer(self):
        """(x, y, bal gomb lenyomva)"""
        q = self.root.query_pointer()
        return q.root_x, q.root_y, bool(q.mask & X.Button1Mask)

    def active(self):
        a = self._prop(self.root, "_NET_ACTIVE_WINDOW")
        return int(a[0]) if a is not None and len(a) and int(a[0]) else 0

    def workarea(self):
        """a panel nélküli terület (x, y, szélesség, magasság) — az aktuális asztalé"""
        v = self._prop(self.root, "_NET_WORKAREA")
        cur = self.desktop()[0]
        if v is not None and len(v) >= 4 * (cur + 1):
            return tuple(int(i) for i in v[4 * cur:4 * cur + 4])
        w, h = self.screen_size()
        return 0, 0, w, h - PANEL_HEIGHT

    def frame(self, wid):
        """az ablak kerettel együtti helye: (x, y, szélesség, magasság) és a keret (bal, jobb, fent, lent)"""
        win = self.d.create_resource_object("window", int(wid))
        g = win.get_geometry()
        t = win.translate_coords(self.root, 0, 0)
        cx, cy = -t.x, -t.y
        e = self._prop(win, "_NET_FRAME_EXTENTS")
        l, r, tp, b = (int(i) for i in e[:4]) if e is not None and len(e) >= 4 else (0, 0, 0, 0)
        return (cx - l, cy - tp, g.width + l + r, g.height + tp + b), (l, r, tp, b)

    def is_maximized(self, wid):
        st = self._prop(self.d.create_resource_object("window", int(wid)), "_NET_WM_STATE") or []
        return self.a["_NET_WM_STATE_MAXIMIZED_VERT"] in st and self.a["_NET_WM_STATE_MAXIMIZED_HORZ"] in st

    def set_maximized(self, wid, on):
        self._client_msg(wid, "_NET_WM_STATE", [1 if on else 0, self.a["_NET_WM_STATE_MAXIMIZED_VERT"],
                                                self.a["_NET_WM_STATE_MAXIMIZED_HORZ"], 2, 0])

    def place(self, wid, x, y, w, h):
        """a keret bal felső sarka (x, y), a teljes (kerettel együtti) méret w × h"""
        (_fx, _fy, _fw, _fh), (l, r, tp, b) = self.frame(wid)
        flags = 1 | (0xF << 8) | (2 << 12)            # NorthWest gravitáció, x+y+w+h, felhasználói kérés
        self._client_msg(wid, "_NET_MOVERESIZE_WINDOW", [flags, int(x), int(y), max(50, int(w) - l - r), max(50, int(h) - tp - b)])

    # --- ablaklista ---
    def _prop(self, win, name, typ=X.AnyPropertyType):
        try:
            p = win.get_full_property(self.a[name] if isinstance(name, str) else name, typ)
            return p.value if p else None
        except Exception:
            return None

    def _title(self, win):
        v = self._prop(win, "_NET_WM_NAME", self.a["UTF8_STRING"])
        if v:
            return v.decode("utf-8", "replace") if isinstance(v, bytes) else str(v)
        try:
            n = win.get_wm_name()
        except Exception:
            return ""
        if isinstance(n, bytes):
            n = n.decode("latin-1")
        # a python-xlib a WM_NAME-et latin-1-ként adja; az UTF-8 címeket (pl. xterm) visszaalakítjuk
        try:
            return (n or "").encode("latin-1").decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            return n or ""

    def windows(self, skip_pids=()):
        ids = self._prop(self.root, "_NET_CLIENT_LIST") or []
        act = self._prop(self.root, "_NET_ACTIVE_WINDOW")
        active = int(act[0]) if act is not None and len(act) else 0
        out = []
        for i in ids:
            win = self.d.create_resource_object("window", int(i))
            types = self._prop(win, "_NET_WM_WINDOW_TYPE") or []
            if any(self.a[t] in types for t in ("_NET_WM_WINDOW_TYPE_DOCK", "_NET_WM_WINDOW_TYPE_NOTIFICATION", "_NET_WM_WINDOW_TYPE_DESKTOP")):
                continue
            state = self._prop(win, "_NET_WM_STATE") or []
            if self.a["_NET_WM_STATE_SKIP_TASKBAR"] in state:
                continue
            pid = self._prop(win, "_NET_WM_PID")
            if skip_pids and pid is not None and len(pid) and int(pid[0]) in skip_pids:
                continue
            try:
                cls = win.get_wm_class() or ("", "")
            except Exception:
                cls = ("", "")
            dk = self._prop(win, "_NET_WM_DESKTOP")
            dk = int(dk[0]) if dk is not None and len(dk) else ALL_DESKTOPS
            out.append({"id": int(i), "title": self._title(win) or (cls[1] if len(cls) > 1 else "") or "ablak",
                        "desktop": -1 if dk == ALL_DESKTOPS or self.a["_NET_WM_STATE_STICKY"] in state else dk,
                        "cls": (cls[1] if len(cls) > 1 else "") or "", "inst": cls[0] if cls else "",
                        "active": int(i) == active,
                        "hidden": self.a["_NET_WM_STATE_HIDDEN"] in state})
        return out

    def icon(self, wid, want=32):
        """az ablak saját ikonja (_NET_WM_ICON): (szélesség, magasság, [ARGB, …]) — a kívánt mérethez
        legközelebbi (inkább nagyobb) változat; None, ha a program nem ad ikont"""
        win = self.d.create_resource_object("window", int(wid))
        v = self._prop(win, "_NET_WM_ICON", Xatom.CARDINAL)
        if v is None or len(v) < 3:
            return None
        v = list(v)
        best, i = None, 0
        while i + 2 <= len(v):
            w, h = int(v[i]), int(v[i + 1])
            n = w * h
            if w <= 0 or h <= 0 or w > 1024 or h > 1024 or i + 2 + n > len(v):
                break
            score = (0 if w >= want else 1, abs(w - want))
            if best is None or score < best[0]:
                best = (score, w, h, i + 2)
            i += 2 + n
        if best is None:
            return None
        _, w, h, off = best
        return w, h, [int(x) & 0xFFFFFFFF for x in v[off:off + w * h]]

    def _client_msg(self, wid, atom, data):
        win = self.d.create_resource_object("window", int(wid))
        ev = protocol.event.ClientMessage(window=win, client_type=self.a[atom], data=(32, data))
        self.root.send_event(ev, event_mask=X.SubstructureRedirectMask | X.SubstructureNotifyMask)
        self.d.flush()

    def activate(self, wid):
        """előre hozás — ha az ablak egy másik asztalon van, előbb arra az asztalra vált"""
        dk = self.window_desktop(wid)
        if dk != ALL_DESKTOPS:
            self.set_desktop(dk)
        self._client_msg(wid, "_NET_ACTIVE_WINDOW", [2, X.CurrentTime, 0, 0, 0])

    def minimize(self, wid):
        self._client_msg(wid, "WM_CHANGE_STATE", [3, 0, 0, 0, 0])   # IconicState

    def close(self, wid):
        self._client_msg(wid, "_NET_CLOSE_WINDOW", [X.CurrentTime, 2, 0, 0, 0])

    def toggle(self, wid):
        """tálcagomb: ha aktív → kis méret, különben előre"""
        for w in self.windows():
            if w["id"] == int(wid) and w["active"] and not w["hidden"]:
                return self.minimize(wid)
        return self.activate(wid)
