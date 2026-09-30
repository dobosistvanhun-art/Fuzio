"""FusionOS — Fusion Shell közös háttérrésze (M6 mérőprototípus)

A panel és a Start menü két felülettel készül (QML / webes), hogy a ZBookon mérhessük,
melyik a jobb alap a Fusion Desktophoz. A felületek ugyanezt a háttérrészt használják,
így a mérés csak a felületi technikát hasonlítja össze.

Feladatok:
  - ablaklista az X11/EWMH szabvány szerint (_NET_CLIENT_LIST, _NET_ACTIVE_WINDOW)
  - ablak aktiválása / kis méretre tétele
  - állapot: óra, dátum, Wi-Fi
  - alkalmazások listája (/usr/lib/fusion/shell/apps.json) és indításuk
  - a panel/menü X11-tulajdonságai (dock típus, képernyő-foglalás, tálcán nem látszik)

Az állapot JSON-ként megy a felületnek; a felület ugyanazzal a formával hív vissza.
"""
import json
import os
import shlex
import subprocess
import time

from Xlib import X, Xatom, display, protocol

APPS_FILE = os.environ.get("FUSION_SHELL_APPS", "/usr/lib/fusion/shell/apps.json")
PANEL_HEIGHT = 40
HU_DAYS = ["hétfő", "kedd", "szerda", "csütörtök", "péntek", "szombat", "vasárnap"]
HU_MONTHS = ["jan.", "febr.", "márc.", "ápr.", "máj.", "jún.", "júl.", "aug.", "szept.", "okt.", "nov.", "dec."]


class ShellCore:
    def __init__(self):
        self.d = display.Display()
        self.root = self.d.screen().root
        self.a = {n: self.d.intern_atom(n) for n in (
            "_NET_CLIENT_LIST", "_NET_ACTIVE_WINDOW", "_NET_WM_NAME", "UTF8_STRING",
            "_NET_WM_WINDOW_TYPE", "_NET_WM_WINDOW_TYPE_DOCK", "_NET_WM_WINDOW_TYPE_NORMAL",
            "_NET_WM_WINDOW_TYPE_DIALOG", "_NET_WM_STATE", "_NET_WM_STATE_SKIP_TASKBAR",
            "_NET_WM_STATE_SKIP_PAGER", "_NET_WM_STATE_ABOVE", "_NET_WM_STATE_HIDDEN",
            "_NET_WM_STRUT", "_NET_WM_STRUT_PARTIAL", "WM_CHANGE_STATE", "_NET_WM_DESKTOP")}
        self._last_state = None
        self._wifi = {"state": "?", "ssid": ""}
        self._wifi_t = 0.0
        self.apps = self._load_apps()

    # --- képernyő ---
    def screen_size(self):
        g = self.root.get_geometry()
        return g.width, g.height

    # --- X11-tulajdonságok a saját ablakainkra ---
    def _set_atoms(self, win, prop, atoms):
        win.change_property(self.a[prop], Xatom.ATOM, 32, [self.a[x] for x in atoms])

    def setup_panel_window(self, xid, height=PANEL_HEIGHT):
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

    def setup_menu_window(self, xid):
        win = self.d.create_resource_object("window", xid)
        self._set_atoms(win, "_NET_WM_WINDOW_TYPE", ["_NET_WM_WINDOW_TYPE_DIALOG"])
        self._set_atoms(win, "_NET_WM_STATE", ["_NET_WM_STATE_SKIP_TASKBAR", "_NET_WM_STATE_SKIP_PAGER", "_NET_WM_STATE_ABOVE"])
        self.d.flush()

    # --- ablaklista ---
    def _prop(self, win, name, typ=X.AnyPropertyType):
        try:
            p = win.get_full_property(self.a[name], typ)
            return p.value if p else None
        except Exception:
            return None

    def _title(self, win):
        v = self._prop(win, "_NET_WM_NAME", self.a["UTF8_STRING"])
        if v:
            return v.decode("utf-8", "replace") if isinstance(v, bytes) else str(v)
        try:
            n = win.get_wm_name()
            return n.decode("latin-1") if isinstance(n, bytes) else (n or "")
        except Exception:
            return ""

    def windows(self):
        ids = self._prop(self.root, "_NET_CLIENT_LIST") or []
        act = self._prop(self.root, "_NET_ACTIVE_WINDOW")
        active = int(act[0]) if act is not None and len(act) else 0
        out = []
        for i in ids:
            win = self.d.create_resource_object("window", int(i))
            types = self._prop(win, "_NET_WM_WINDOW_TYPE") or []
            if self.a["_NET_WM_WINDOW_TYPE_DOCK"] in types:
                continue
            state = self._prop(win, "_NET_WM_STATE") or []
            if self.a["_NET_WM_STATE_SKIP_TASKBAR"] in state:
                continue
            try:
                cls = win.get_wm_class() or ("", "")
            except Exception:
                cls = ("", "")
            out.append({"id": int(i), "title": self._title(win) or cls[1] or "ablak",
                        "cls": cls[1] if len(cls) > 1 else "", "active": int(i) == active,
                        "hidden": self.a["_NET_WM_STATE_HIDDEN"] in state})
        return out

    def activate(self, wid):
        win = self.d.create_resource_object("window", int(wid))
        ev = protocol.event.ClientMessage(window=win, client_type=self.a["_NET_ACTIVE_WINDOW"],
                                          data=(32, [2, X.CurrentTime, 0, 0, 0]))
        self.root.send_event(ev, event_mask=X.SubstructureRedirectMask | X.SubstructureNotifyMask)
        self.d.flush()

    def minimize(self, wid):
        win = self.d.create_resource_object("window", int(wid))
        ev = protocol.event.ClientMessage(window=win, client_type=self.a["WM_CHANGE_STATE"],
                                          data=(32, [3, 0, 0, 0, 0]))   # IconicState
        self.root.send_event(ev, event_mask=X.SubstructureRedirectMask | X.SubstructureNotifyMask)
        self.d.flush()

    def toggle(self, wid):
        """tálcagomb: ha aktív → kis méret, különben előre"""
        for w in self.windows():
            if w["id"] == int(wid) and w["active"] and not w["hidden"]:
                return self.minimize(wid)
        return self.activate(wid)

    # --- Wi-Fi (5 mp-enként, a fusion-wifi mögötti iwd-ből) ---
    def _wifi_state(self):
        now = time.monotonic()
        if now - self._wifi_t < 5:
            return self._wifi
        self._wifi_t = now
        try:
            out = subprocess.run(["fusion-wifi"], capture_output=True, text=True, timeout=3).stdout
            st = {"state": "nincs", "ssid": ""}
            for line in out.splitlines():
                line = line.strip()
                if line.startswith("Állapot:"):
                    st["state"] = line.split(":", 1)[1].strip()
                elif line.startswith("Hálózat:"):
                    st["ssid"] = line.split(":", 1)[1].strip()
            self._wifi = st
        except Exception:
            self._wifi = {"state": "nincs", "ssid": ""}
        return self._wifi

    # --- alkalmazások ---
    def _load_apps(self):
        try:
            with open(APPS_FILE, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return [{"id": "terminal", "name": "Terminál", "icon": ">_", "exec": "xterm"}]

    def launch(self, app_id):
        for a in self.apps:
            if a["id"] == app_id:
                subprocess.Popen(shlex.split(a["exec"]), start_new_session=True,
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return True
        return False

    # --- állapot: csak ha változott (a felületek ugyanígy, 0,5 mp-enként kérdezik) ---
    def poll(self, force=False):
        t = time.localtime()
        st = {
            "windows": self.windows(),
            "clock": time.strftime("%H:%M", t),
            "date": f"{t.tm_year}. {HU_MONTHS[t.tm_mon - 1]} {t.tm_mday}., {HU_DAYS[t.tm_wday]}",
            "wifi": self._wifi_state(),
        }
        s = json.dumps(st, ensure_ascii=False)
        if force or s != self._last_state:
            self._last_state = s
            return s
        return None

    def apps_json(self):
        return json.dumps(self.apps, ensure_ascii=False)

    def handle(self, msg):
        """a felület üzenete: {"cmd": "toggle|activate|launch|menu", ...}"""
        try:
            m = json.loads(msg) if isinstance(msg, str) else msg
        except Exception:
            return
        cmd = m.get("cmd")
        if cmd == "toggle":
            self.toggle(m["id"])
        elif cmd == "activate":
            self.activate(m["id"])
        elif cmd == "launch":
            self.launch(m["id"])


def mark_ready(variant):
    """a mérőszkriptnek: mikor lett kész a panel (ms-ban a folyamat indulásától)"""
    rt = os.environ.get("XDG_RUNTIME_DIR", "/tmp")
    try:
        with open(os.path.join(rt, f"fusion-shell-{variant}.ready"), "w") as f:
            f.write(f"{time.time():.3f}\n")
    except OSError:
        pass
