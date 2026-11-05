"""kijelző — kikapcsolás gombra és tétlenség után; amíg videó megy (egy program ébren tartást kér), nem kapcsol ki

    CHOICES                  a választható idők percben (0 = soha)
    off_minutes()            a beállítás: ennyi perc tétlenség után kikapcsol a kijelző (0 = soha)
    set_off_minutes(n)       beállítás (a Fúzió Shell 5 mp-en belül alkalmazza)
    query(text=None)         az X-kiszolgáló állapota (`xset q`): {dpms, standby, suspend, off, monitor, saver}
    wanted(minutes, inhibited)   amit beállítani kell: {dpms, off}
    commands(cur, want)      a hiányzó xset-parancsok (üres lista: minden rendben, vagy a kijelző épp ki van kapcsolva)
    off_now(delay=0.8)       a kijelző azonnal ki; egérmozdításra / billentyűre visszajön
    inhibitors()             a Fúzió Shell szerint most ébren tartó programok [{app, reason}]

Az időzítést maga az X-kiszolgáló végzi (DPMS): a bemenet (egér, billentyű, touchpad) nullázza. Ébren tartás:
(1) a programok org.freedesktop.ScreenSaver.Inhibit kérése (Firefox, VLC, a Flatpak-portálon át is) — ezt a Fúzió
Shell fogadja, és amíg tart, kikapcsolja a DPMS-t; (2) az XScreenSaverSuspend (pl. mpv) — azt az X maga tartja be.
"""
import json
import os
import re
import subprocess
import time

CHOICES = (0, 5, 10, 15, 30, 60)
MAX_MINUTES = 240
_CONFIG = os.path.join(os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config"), "fusion")
CONF_FILE = os.path.join(_CONFIG, "screen-off")
STATE_FILE = os.path.join(os.environ.get("XDG_RUNTIME_DIR") or "/tmp", "fusion-shell.state")


def off_minutes():
    try:
        with open(CONF_FILE) as f:
            n = int(f.read().strip() or "0")
    except (OSError, ValueError):
        return 0
    return n if 0 <= n <= MAX_MINUTES else 0


def set_off_minutes(minutes):
    n = int(minutes)
    if not 0 <= n <= MAX_MINUTES:
        raise ValueError(f"0 és {MAX_MINUTES} perc között lehet (kapott: {n})")
    os.makedirs(_CONFIG, exist_ok=True)
    tmp = CONF_FILE + ".tmp"
    with open(tmp, "w") as f:
        f.write(f"{n}\n")
    os.replace(tmp, CONF_FILE)


def _xset(*args, timeout=3):
    try:
        p = subprocess.run(["xset", *args], capture_output=True, text=True, timeout=timeout)
        return p.returncode, p.stdout
    except (OSError, subprocess.SubprocessError):
        return 1, ""


def query(text=None):
    """`xset q` értelmezése; None, ha nincs X (vagy nincs DPMS-bővítmény)"""
    if text is None:
        rc, text = _xset("q")
        if rc != 0:
            return None
    m = re.search(r"Standby:\s*(\d+)\s+Suspend:\s*(\d+)\s+Off:\s*(\d+)", text)
    if not m:
        return None
    mon = re.search(r"Monitor is (\w+)", text)
    saver = re.search(r"timeout:\s*(\d+)", text)
    return {"dpms": "DPMS is Enabled" in text, "standby": int(m.group(1)), "suspend": int(m.group(2)),
            "off": int(m.group(3)), "monitor": mon.group(1) if mon else "On",
            "saver": int(saver.group(1)) if saver else 0}


def wanted(minutes, inhibited):
    on = minutes > 0 and not inhibited
    return {"dpms": on, "off": minutes * 60 if on else 0}


def commands(cur, want):
    if cur is None or cur["monitor"] != "On":
        return []          # kikapcsolt kijelzőnél (gomb, lecsukott fedél) nem nyúlunk hozzá: a DPMS kikapcsolása felkapcsolná
    out = []
    if cur["saver"] != 0:
        out.append(["s", "off"])            # az X saját képernyőkímélője (elsötétítés) nem kell
    if want["dpms"]:
        if (cur["standby"], cur["suspend"], cur["off"]) != (0, 0, want["off"]):
            out.append(["dpms", "0", "0", str(want["off"])])
        if not cur["dpms"]:
            out.append(["+dpms"])
    elif cur["dpms"]:
        out.append(["-dpms"])
    return out


def apply(minutes, inhibited):
    """a beállítás érvényesítése; a lefuttatott xset-parancsok listája"""
    cmds = commands(query(), wanted(minutes, inhibited))
    for c in cmds:
        _xset(*c)
    return cmds


def off_now(delay=0.8):
    """kijelző ki; a késleltetés alatt a kattintás / billentyű felengedése ne kapcsolja vissza"""
    if delay > 0:
        time.sleep(delay)
    _xset("+dpms")
    rc, _ = _xset("dpms", "force", "off")
    return rc == 0


def inhibitors():
    try:
        with open(STATE_FILE) as f:
            st = json.load(f)
    except (OSError, ValueError):
        return []
    return list((st.get("screen") or {}).get("inhibit") or [])
