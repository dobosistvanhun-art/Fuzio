"""FusionOS — Fusion API: ablakok (X11, EWMH) — a Fusion Shell és a Feladatkezelő közös alapja (M8)

A Fusion Shell ezen át látja és kezeli az ablakokat — ablakkezelőtől függetlenül,
az EWMH szabvány szerint (_NET_CLIENT_LIST, _NET_ACTIVE_WINDOW, _NET_CLOSE_WINDOW):
  - ablaklista a tálcához (cím, osztály, aktív, kis méretre tett), az ablak saját ikonja
  - ablak aktiválása, kis méretre tétele, bezárása
  - a Shell saját ablakainak típusa: panel (dock + képernyősáv-foglalás),
    lebegő ablak (Start menü, értesítés, felugró)
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
         "WM_PROTOCOLS", "_NET_WM_PING", "WM_DELETE_WINDOW", "_NET_WM_ICON")


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
        self.d.flush()

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
            out.append({"id": int(i), "title": self._title(win) or (cls[1] if len(cls) > 1 else "") or "ablak",
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
