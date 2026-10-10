"""FusionOS — Feladatkezelő: futó programok és folyamatok, „nem válaszol” felismerés, bezárás

Programok = a látható ablakok (X11 _NET_CLIENT_LIST) a folyamatuk szerint csoportosítva, a Fusion
Programkezelő neveivel (Windows-program: a Wine-környezete, Flatpak: az azonosítója alapján).

„Nem válaszol”: a szabványos _NET_WM_PING — az ablaknak küldött pingre a működő program azonnal
válaszol (Qt, GTK, Wine, Java …); amelyik ~2 mp alatt nem, az nem dolgozza fel az üzeneteit.

Bezárás: udvarias (WM_DELETE_WINDOW — mint az ablak X gombja), majd kényszerített:
  Windows-program  → fwr stop <id> (a Wine-környezet összes folyamata)
  Flatpak          → flatpak kill <azonosító>
  egyéb            → SIGTERM a folyamatnak és a gyermekeinek, 3 mp múlva SIGKILL; az X-kapcsolat bontása
Csak a felhasználó saját folyamataihoz nyúl (rendszerfolyamatokhoz nem).
"""
import os
import select
import signal
import subprocess
import sys
import time

try:
    from Xlib import X, display, protocol
    from Xlib.error import XError
    sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
    from fusion.x11 import X11 as BaseX11
except ImportError:      # Xlib nélkül csak a folyamatlista működik
    display = None
    BaseX11 = object

UID = os.getuid()
CLK = os.sysconf("SC_CLK_TCK")
PAGE = os.sysconf("SC_PAGE_SIZE")
# a Fusion Desktop saját, mindig futó ablakai — ezek nem „programok”
SKIP_CLASSES = {"fusion-shell", "Fusion Panel", "Fusion Start", "fusion-tasks"}
SKIP_TYPES = {"_NET_WM_WINDOW_TYPE_DOCK", "_NET_WM_WINDOW_TYPE_DESKTOP", "_NET_WM_WINDOW_TYPE_NOTIFICATION",
              "_NET_WM_WINDOW_TYPE_TOOLTIP", "_NET_WM_WINDOW_TYPE_POPUP_MENU", "_NET_WM_WINDOW_TYPE_DROPDOWN_MENU"}

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
try:
    import fusion_apps  # noqa: F401  (a fusion_programs útvonala)
    import fusion_programs as fp
except Exception:
    fp = None


# ---------------------------------------------------------------------------
# folyamatok
# ---------------------------------------------------------------------------
def _stat(pid):
    try:
        with open(f"/proc/{pid}/stat") as f:
            s = f.read()
    except OSError:
        return None
    name = s[s.index("(") + 1:s.rindex(")")]
    rest = s[s.rindex(")") + 2:].split()
    return {"name": name, "state": rest[0], "ppid": int(rest[1]), "pgrp": int(rest[2]),
            "ticks": int(rest[11]) + int(rest[12]), "rss": int(rest[21]) * PAGE}


def _pss(pid, fallback):
    """PSS (arányos memória): a megosztott lapok (Qt-, Python-könyvtárak) a használók között elosztva — az RSS
    ezeket minden folyamatnál teljes egészében számolja, ezért túlbecsül. Csak a saját folyamatoknál olvasható."""
    try:
        with open(f"/proc/{pid}/smaps_rollup") as f:
            for line in f:
                if line.startswith("Pss:"):
                    return int(line.split()[1]) * 1024
    except (OSError, ValueError, IndexError):
        pass
    return fallback


def _uid(pid):
    try:
        return os.stat(f"/proc/{pid}").st_uid
    except OSError:
        return -1


def _environ(pid, key):
    try:
        with open(f"/proc/{pid}/environ", "rb") as f:
            for item in f.read().split(b"\0"):
                if item.startswith(key.encode() + b"="):
                    return item.split(b"=", 1)[1].decode(errors="replace")
    except OSError:
        pass
    return ""


def _cmdline(pid):
    try:
        with open(f"/proc/{pid}/cmdline", "rb") as f:
            return [a.decode(errors="replace") for a in f.read().split(b"\0") if a]
    except OSError:
        return []


class Sampler:
    """CPU-használat két mérés különbségéből"""
    def __init__(self):
        self.prev = {}
        self.prev_t = time.monotonic()

    def sample(self):
        now = time.monotonic()
        dt = max(now - self.prev_t, 0.001)
        out = {}
        for d in os.listdir("/proc"):
            if not d.isdigit():
                continue
            pid = int(d)
            st = _stat(pid)
            if not st:
                continue
            st["uid"] = _uid(pid)
            old = self.prev.get(pid)
            st["cpu"] = round(100.0 * (st["ticks"] - old) / CLK / dt, 1) if old is not None and st["ticks"] >= old else 0.0
            out[pid] = st
        self.prev = {p: s["ticks"] for p, s in out.items()}
        self.prev_t = now
        return out


def children(procs, pid):
    """a folyamat összes leszármazottja"""
    kids, todo = set(), [pid]
    while todo:
        p = todo.pop()
        for q, s in procs.items():
            if s["ppid"] == p and q not in kids:
                kids.add(q)
                todo.append(q)
    return kids


# ---------------------------------------------------------------------------
# a programok azonosítása (Programkezelő)
# ---------------------------------------------------------------------------
def _program_of(pid):
    """(kind, pid-azonosító, név) — kind: windows | flatpak | linux"""
    prefix = _environ(pid, "WINEPREFIX")
    if prefix and fp is not None:
        for m in fp.programs():
            if m.get("type") == "win64":
                try:
                    i = fp.info(m)
                except Exception:
                    i = {"name": m.get("name", m["id"])}
                pre = m.get("prefix") or os.path.join(fp.PROGRAMS, m["id"], "win64")
                if os.path.realpath(pre) == os.path.realpath(prefix):
                    return "windows", m["id"], i.get("name") or m["id"]
        return "windows", "", "Windows-program"
    fid = _environ(pid, "FLATPAK_ID")
    if fid:
        name = fid
        if fp is not None:
            for m in fp.programs():
                if m.get("appid") == fid:
                    name = m.get("name") or fid
        return "flatpak", fid, name
    return "linux", "", ""


# ---------------------------------------------------------------------------
# ablakok (X11)
# ---------------------------------------------------------------------------
class TaskX11(BaseX11):
    """a közös fusion.x11 alap + a Feladatkezelő része: ping („nem válaszol”), udvarias bezárás, kill"""
    def __init__(self):
        super().__init__(events=True)

    def windows(self):
        ids = self._prop(self.root, "_NET_CLIENT_LIST") or []
        out = []
        for wid in ids:
            w = self.d.create_resource_object("window", int(wid))
            try:
                cls = w.get_wm_class() or ("", "")
                protos = [p for p in (w.get_wm_protocols() or [])]
            except XError:
                continue
            types = [self.d.get_atom_name(t) for t in (self._prop(w, "_NET_WM_WINDOW_TYPE") or [])]
            if set(types) & SKIP_TYPES or (cls[0] in SKIP_CLASSES or cls[1] in SKIP_CLASSES):
                continue
            pid = self._prop(w, "_NET_WM_PID")
            out.append({"wid": int(wid), "title": self._title(w), "pid": int(pid[0]) if pid else 0,
                        "cls": cls[1] or cls[0], "ping": self.a["_NET_WM_PING"] in protos,
                        "delete": self.a["WM_DELETE_WINDOW"] in protos})
        return out

    def ping(self, wins, timeout=2.0):
        """{wid: True (válaszolt) | False (nem) | None (nem támogatja)}"""
        res = {}
        pending = {}
        ts = int(time.time() * 1000) & 0xffffffff
        for w in wins:
            if not w["ping"]:
                res[w["wid"]] = None
                continue
            win = self.d.create_resource_object("window", w["wid"])
            ev = protocol.event.ClientMessage(window=win, client_type=self.a["WM_PROTOCOLS"],
                                              data=(32, [self.a["_NET_WM_PING"], ts, w["wid"], 0, 0]))
            try:
                win.send_event(ev, event_mask=0)
                pending[w["wid"]] = True
            except XError:
                res[w["wid"]] = None
        self.d.flush()
        end = time.monotonic() + timeout
        while pending and time.monotonic() < end:
            if not self.d.pending_events():
                r, _, _ = select.select([self.d.fileno()], [], [], max(0.0, end - time.monotonic()))
                if not r:
                    break
            while self.d.pending_events():
                e = self.d.next_event()
                if e.type == X.ClientMessage and e.client_type == self.a["WM_PROTOCOLS"]:
                    data = e.data[1]
                    if data[0] == self.a["_NET_WM_PING"] and data[2] in pending:
                        res[data[2]] = True
                        pending.pop(data[2], None)
        for wid in pending:
            res[wid] = False
        return res

    def close(self, wid):
        win = self.d.create_resource_object("window", wid)
        ev = protocol.event.ClientMessage(window=win, client_type=self.a["WM_PROTOCOLS"],
                                          data=(32, [self.a["WM_DELETE_WINDOW"], X.CurrentTime, 0, 0, 0]))
        try:
            win.send_event(ev, event_mask=0)
            self.d.flush()
            return True
        except XError:
            return False

    def activate(self, wid):
        win = self.d.create_resource_object("window", wid)
        ev = protocol.event.ClientMessage(window=win, client_type=self.a["_NET_ACTIVE_WINDOW"],
                                          data=(32, [2, X.CurrentTime, 0, 0, 0]))
        self.root.send_event(ev, event_mask=X.SubstructureRedirectMask | X.SubstructureNotifyMask)
        self.d.flush()

    def kill_client(self, wid):
        try:
            self.d.kill_client(wid)
            self.d.sync()
        except XError:
            pass


# ---------------------------------------------------------------------------
# a Feladatkezelő modellje
# ---------------------------------------------------------------------------
class Tasks:
    def __init__(self):
        self.sampler = Sampler()
        self.x = TaskX11() if display is not None and os.environ.get("DISPLAY") else None
        self.procs = self.sampler.sample()
        self.alive = {}       # wid → utolsó ping-eredmény

    def refresh(self, ping=True):
        self.procs = procs = self.sampler.sample()
        wins = self.x.windows() if self.x else []
        if ping and self.x:
            self.alive.update(self.x.ping(wins))
        groups = {}
        for w in wins:
            pid = w["pid"]
            kind, key, name = _program_of(pid) if pid and pid in procs else ("linux", "", "")
            if not key:
                # Linux-program: az ablak folyamata (egy program több ablaka egy sor)
                key = f"pid:{pid}" if pid in procs else f"win:{w['wid']}"
                name = name or (w["cls"] or (procs[pid]["name"] if pid in procs else "?"))
            g = groups.setdefault(key, {"key": key, "kind": kind, "name": name, "windows": [], "pids": set()})
            g["windows"].append({"wid": w["wid"], "title": w["title"], "alive": self.alive.get(w["wid"])})
            if pid:
                g["pids"].add(pid)
        out = []
        for g in groups.values():
            allp = set(g["pids"])
            for p in list(g["pids"]):
                allp |= children(procs, p)
            if g["kind"] == "windows":
                pre = _environ(next(iter(g["pids"])), "WINEPREFIX") if g["pids"] else ""
                allp |= {p for p in procs if procs[p]["uid"] == UID and pre and _environ(p, "WINEPREFIX") == pre}
            alive = [w["alive"] for w in g["windows"]]
            g["status"] = "hung" if False in alive else ("ok" if True in alive else "unknown")
            g["cpu"] = round(sum(procs[p]["cpu"] for p in allp if p in procs), 1)
            g["mem"] = sum(_pss(p, procs[p]["rss"]) for p in allp if p in procs)
            g["memText"] = f"{g['mem'] / 1048576:.0f} MB"
            g["pids"] = sorted(allp)
            g["mine"] = all(procs.get(p, {}).get("uid") == UID for p in g["pids"]) if g["pids"] else True
            g["titles"] = " · ".join(w["title"] for w in g["windows"] if w["title"])[:160]
            out.append(g)
        out.sort(key=lambda g: (g["status"] != "hung", g["name"].lower()))
        return out

    def processes(self, limit=60):
        out = []
        for pid, s in self.procs.items():
            if s["uid"] != UID or s["state"] == "Z":
                continue
            cmd = _cmdline(pid)
            pss = _pss(pid, s["rss"])
            out.append({"pid": pid, "name": s["name"], "cmd": " ".join(cmd)[:140], "cpu": s["cpu"],
                        "mem": pss, "rss": s["rss"], "memText": f"{pss / 1048576:.0f} MB"})
        out.sort(key=lambda p: (-p["cpu"], -p["mem"]))
        return out[:limit]

    def summary(self):
        mem = {}
        try:
            for line in open("/proc/meminfo"):
                k, v = line.split(":", 1)
                mem[k] = int(v.split()[0]) * 1024
        except OSError:
            pass
        tot = mem.get("MemTotal", 0)
        used = tot - mem.get("MemAvailable", 0)
        try:
            load = open("/proc/loadavg").read().split()[0]
        except OSError:
            load = "?"
        ncpu = os.cpu_count() or 1
        cpu = sum(s["cpu"] for s in self.procs.values()) / ncpu
        mb = lambda k: f"{mem.get(k, 0) / 1048576:.0f} MB"  # noqa: E731
        return {"cpu": round(min(cpu, 100.0), 0), "load": load, "memUsed": used, "memTotal": tot,
                "memText": f"{used / 1073741824:.1f} / {tot / 1073741824:.1f} GB",
                # a „foglalt” részletei: a megosztott memória (tmpfs, pl. /run, /tmp) és a kernel saját része
                "memDetail": f"megosztott (tmpfs) {mb('Shmem')}  ·  kernel {mb('Slab')}  ·  gyorsítótár {mb('Cached')}"}

    # --- műveletek ---
    def close(self, group):
        n = 0
        for w in group.get("windows", []):
            if self.x and self.x.close(w["wid"]):
                n += 1
        return n

    def force(self, group):
        """kényszerített bezárás; visszaadja: leállt-e minden folyamata"""
        kind, key = group.get("kind"), group.get("key", "")
        pids = [p for p in group.get("pids", []) if _uid(p) == UID]
        if kind == "windows" and key and not key.startswith(("pid:", "win:")):
            subprocess.run(["fwr", "stop", key], capture_output=True, timeout=20)
        elif kind == "flatpak" and key:
            subprocess.run(["flatpak", "kill", key], capture_output=True, timeout=20)
        for p in pids:
            try:
                os.kill(p, signal.SIGTERM)
            except OSError:
                pass
        end = time.monotonic() + 3
        while time.monotonic() < end and any(_alive(p) for p in pids):
            time.sleep(0.2)
        left = [p for p in pids if _alive(p)]
        for p in left:
            try:
                os.kill(p, signal.SIGKILL)
            except OSError:
                pass
        if self.x:      # ha az ablak más folyamaté (pl. nincs _NET_WM_PID): az X-kapcsolat bontása
            for w in group.get("windows", []):
                if not pids:
                    self.x.kill_client(w["wid"])
        time.sleep(0.3)
        return not any(_alive(p) for p in pids)

    def kill_process(self, pid):
        if _uid(pid) != UID:
            return False
        try:
            os.kill(pid, signal.SIGTERM)
        except OSError:
            return True
        end = time.monotonic() + 3
        while time.monotonic() < end and _alive(pid):
            time.sleep(0.2)
        if _alive(pid):
            try:
                os.kill(pid, signal.SIGKILL)
            except OSError:
                pass
        time.sleep(0.2)
        return not _alive(pid)

    def activate(self, group):
        if self.x and group.get("windows"):
            self.x.activate(group["windows"][0]["wid"])


def _alive(pid):
    st = _stat(pid)
    return bool(st) and st["state"] != "Z"
