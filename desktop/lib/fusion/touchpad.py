"""touchpad — a beépített érintőpad beállításai (koppintás, görgetés, sebesség …), X11 + libinput

    devices()        [{id, name}] — a libinput-touchpadok (amelyeknek van „libinput Tapping Enabled” tulajdonsága)
    status()         {ok, error, devices, settings, available: {scroll: [...], click: [...]}}
    load() / save(s) a felhasználó beállításai: ~/.config/fusion/touchpad.json
    apply(s=None)    a beállítások érvényesítése minden touchpadon (xinput set-prop) → [hibaüzenetek]

Általános: bármely libinput-touchpadot kezel (Synaptics, Elan, ALPS, I²C-HID …), név szerinti feltétel nélkül.
Az alapértékek a rendszerképben is megvannak (/etc/X11/xorg.conf.d/40-fusion-touchpad.conf), így a touchpad a
beállítófájl nélkül is koppintással kattint és két ujjal görget; ez a modul a felhasználó egyéni választását teszi rá.
"""
import json
import os
import re
import subprocess

CONFIG = os.path.join(os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config"), "fusion", "touchpad.json")

DEFAULTS = {
    "enabled": True,        # a touchpad be van kapcsolva
    "tap": True,            # koppintás = kattintás (2 ujj: jobb gomb, 3 ujj: középső)
    "scroll": "twofinger",  # twofinger | edge | none
    "natural": False,       # természetes (fordított) görgetés
    "horizontal": True,     # vízszintes görgetés is
    "dwt": True,            # gépelés közben tiltva
    "speed": 0.0,           # -1 … 1
    "middle": False,        # két gomb együtt = középső gomb
}
SCROLL = ("twofinger", "edge", "none")
P_TAP = "libinput Tapping Enabled"


def _xinput(*args, timeout=5):
    try:
        r = subprocess.run(["xinput", *args], capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout + r.stderr
    except (OSError, subprocess.TimeoutExpired) as e:
        return 127, str(e)


def _props(dev_id):
    """{tulajdonság: [értékek]}"""
    rc, out = _xinput("list-props", str(dev_id))
    props = {}
    if rc != 0:
        return props
    for line in out.splitlines():
        m = re.match(r"\s+(.+?) \(\d+\):\s*(.*)$", line)
        if m:
            props[m.group(1)] = [v.strip() for v in m.group(2).split(",") if v.strip()]
    return props


def devices():
    if not os.environ.get("DISPLAY"):
        return []
    rc, out = _xinput("list", "--short")
    if rc != 0:
        return []
    res = []
    for line in out.splitlines():
        m = re.search(r"↳?\s*(.+?)\s+id=(\d+)\s+\[slave\s+pointer", line)
        if not m:
            continue
        name, dev_id = m.group(1).strip("⎜↳ \t"), int(m.group(2))
        pr = _props(dev_id)
        if P_TAP in pr:
            res.append({"id": dev_id, "name": name, "props": pr})
    return res


def load():
    s = dict(DEFAULTS)
    try:
        with open(CONFIG, encoding="utf-8") as f:
            d = json.load(f)
        if isinstance(d, dict):
            for k, v in d.items():
                if k in DEFAULTS and type(v) is type(DEFAULTS[k]) or (k == "speed" and isinstance(v, (int, float))):
                    s[k] = v
    except (OSError, ValueError):
        pass
    if s["scroll"] not in SCROLL:
        s["scroll"] = DEFAULTS["scroll"]
    s["speed"] = max(-1.0, min(1.0, float(s["speed"])))
    return s


def save(s):
    cur = load()
    for k, v in (s or {}).items():
        if k in DEFAULTS:
            cur[k] = v
    if cur["scroll"] not in SCROLL:
        raise ValueError(f"ismeretlen görgetési mód: {cur['scroll']}")
    cur["speed"] = max(-1.0, min(1.0, float(cur["speed"])))
    for k in ("enabled", "tap", "natural", "horizontal", "dwt", "middle"):
        cur[k] = bool(cur[k])
    os.makedirs(os.path.dirname(CONFIG), exist_ok=True)
    with open(CONFIG + ".tmp", "w", encoding="utf-8") as f:
        json.dump(cur, f, ensure_ascii=False, indent=1)
    os.replace(CONFIG + ".tmp", CONFIG)
    return cur


def _avail(pr, name, n):
    v = pr.get(name)
    return [int(x) for x in v[:n]] if v and len(v) >= n and all(x in ("0", "1") for x in v[:n]) else None


def apply(s=None):
    s = s or load()
    errs = []
    for d in devices():
        pr, i = d["props"], str(d["id"])

        def setp(prop, *vals):
            if prop not in pr:
                return
            a = ["set-prop", i, prop] + [str(v) for v in vals]      # a típust (egész / valós) az xinput a tulajdonságból veszi
            rc, out = _xinput(*a)
            if rc != 0:
                errs.append(f"{d['name']}: {prop}: {out.strip()[:160]}")

        setp("Device Enabled", int(s["enabled"]))
        setp(P_TAP, int(s["tap"]))
        setp("libinput Tapping Button Mapping Enabled", 1, 0)          # 2 ujj: jobb, 3 ujj: középső
        setp("libinput Natural Scrolling Enabled", int(s["natural"]))
        setp("libinput Horizontal Scroll Enabled", int(s["horizontal"]))
        setp("libinput Disable While Typing Enabled", int(s["dwt"]))
        setp("libinput Middle Emulation Enabled", int(s["middle"]))
        setp("libinput Accel Speed", f"{s['speed']:.2f}")
        av = _avail(pr, "libinput Scroll Methods Available", 3)
        if av:
            want = {"twofinger": [1, 0, 0], "edge": [0, 1, 0], "none": [0, 0, 0]}[s["scroll"]]
            if any(w and not a for w, a in zip(want, av)):           # a kért mód nincs: a másik görgetés
                want = [av[0], 0 if av[0] else av[1], 0]
            setp("libinput Scroll Method Enabled", *want)
    return errs


def status():
    if not os.environ.get("DISPLAY"):
        return {"ok": False, "error": "nincs grafikus munkamenet (DISPLAY)", "devices": [], "settings": load(), "available": {}}
    rc, _ = _xinput("version")
    if rc == 127:
        return {"ok": False, "error": "az xinput nem érhető el", "devices": [], "settings": load(), "available": {}}
    devs = devices()
    avail = {"scroll": []}
    for d in devs:
        av = _avail(d["props"], "libinput Scroll Methods Available", 3) or [0, 0, 0]
        avail["scroll"] = [m for m, a in zip(("twofinger", "edge"), av[:2]) if a]
    out = []
    for d in devs:
        pr = d["props"]
        cur = {"tap": (pr.get(P_TAP) or ["?"])[0] == "1",
               "enabled": (pr.get("Device Enabled") or ["1"])[0] == "1",
               "scroll": {"1, 0, 0": "twofinger", "0, 1, 0": "edge", "0, 0, 0": "none"}.get(
                   ", ".join((pr.get("libinput Scroll Method Enabled") or [])[:3]), "?"),
               "natural": (pr.get("libinput Natural Scrolling Enabled") or ["0"])[0] == "1",
               "speed": float((pr.get("libinput Accel Speed") or ["0"])[0])}
        out.append({"id": d["id"], "name": d["name"], "current": cur})
    return {"ok": True, "error": "", "devices": out, "settings": load(), "available": avail}
