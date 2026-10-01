"""FusionOS — hang: a hangkiszolgáló (PipeWire, PulseAudio-felülettel) kezelése

A Fusion Shell (panel, hangerő-felugró), a Beállítások → Hang és a fusion-sound parancs ezt használja.
A kiszolgáló felé a szabványos PulseAudio-protokollon beszél (pactl) — így ugyanaz működne PulseAudióval is;
a programok (Flatpak is) ugyanezen a felületen játszanak le.
A pactl kimenete LC_ALL=C mellett kerül feldolgozásra (a JSON-kimenete a nem ASCII neveken elakad).
"""
import math
import os
import re
import struct
import subprocess
import tempfile

ENV = dict(os.environ, LC_ALL="C", LANG="C")
MAX = 150      # %: a 100 fölötti erősítés csak a Beállításokból


def _pactl(*args, timeout=4):
    try:
        p = subprocess.run(["pactl", *args], capture_output=True, text=True, errors="replace", timeout=timeout, env=ENV)
        return p.returncode, p.stdout, p.stderr.strip()
    except (OSError, subprocess.TimeoutExpired) as e:
        return 1, "", str(e)


def _blocks(text, head):
    out, cur, section = [], None, ""
    for line in text.splitlines():
        if line.startswith(head + " #"):
            cur = {"index": int(line.split("#")[1]), "ports": [], "props": {}}
            out.append(cur)
            section = ""
            continue
        if cur is None:
            continue
        s = line.strip()
        if line.startswith("\t") and not line.startswith("\t\t") and ":" in s:
            k, v = s.split(":", 1)
            section = k
            cur[k.strip()] = v.strip()
        elif line.startswith("\t\t") and section == "Ports":
            m2 = re.match(r"\s*([^:]+):\s*(.*)$", line)
            if m2:
                name, rest = m2.group(1).strip(), m2.group(2)
                desc = re.sub(r"\s*\(type:.*$|\s*\(priority:.*$", "", rest).strip()
                avail = "not available" not in rest
                cur["ports"].append({"name": name, "desc": desc, "available": avail})
        elif line.startswith("\t\t") and section == "Properties" and "=" in s:
            k, v = s.split("=", 1)
            cur["props"][k.strip()] = v.strip().strip('"')
    return out


def _volume(v):
    pcts = [int(x) for x in re.findall(r"(\d+)%", v or "")]
    return round(sum(pcts) / len(pcts)) if pcts else 0


def _devs(kind):
    rc, out, err = _pactl("list", kind + "s")
    if rc != 0:
        return None
    res = []
    for b in _blocks(out, "Sink" if kind == "sink" else "Source"):
        name = b.get("Name", "")
        if kind == "source" and (name.endswith(".monitor") or b["props"].get("device.class") == "monitor"):
            continue
        res.append({"name": name, "desc": b.get("Description", name), "volume": _volume(b.get("Volume")),
                    "mute": b.get("Mute") == "yes", "state": b.get("State", ""),
                    "port": b.get("Active Port", ""), "ports": b["ports"],
                    "bus": b["props"].get("device.bus", ""), "icon": b["props"].get("device.icon_name", "")})
    return res


def state():
    """{ok, server, sinks, sources, sink, source, volume, mute, micVolume, micMute, error}"""
    rc, out, err = _pactl("info")
    if rc != 0:
        return {"ok": False, "error": err or "a hangkiszolgáló nem fut", "sinks": [], "sources": [],
                "sink": "", "source": "", "volume": 0, "mute": False, "micVolume": 0, "micMute": False, "server": ""}
    info = {}
    for line in out.splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            info[k.strip()] = v.strip()
    sinks = _devs("sink") or []
    sources = _devs("source") or []
    ds, dsrc = info.get("Default Sink", ""), info.get("Default Source", "")
    cur = next((s for s in sinks if s["name"] == ds), sinks[0] if sinks else None)
    mic = next((s for s in sources if s["name"] == dsrc), sources[0] if sources else None)
    # a PipeWire „Dummy Output”/automatikus null-kimenete nem valódi eszköz
    real = [s for s in sinks if s["name"] not in ("auto_null",)]
    return {"ok": True, "server": info.get("Server Name", ""), "sinks": sinks, "sources": sources,
            "sink": cur["name"] if cur else "", "source": mic["name"] if mic else "",
            "sinkDesc": cur["desc"] if cur else "", "volume": cur["volume"] if cur else 0,
            "mute": cur["mute"] if cur else False, "micVolume": mic["volume"] if mic else 0,
            "micMute": mic["mute"] if mic else False, "hasOutput": bool(real), "error": ""}


def set_volume(pct, source=False):
    pct = max(0, min(MAX, int(pct)))
    return _pactl("set-source-volume" if source else "set-sink-volume",
                  "@DEFAULT_SOURCE@" if source else "@DEFAULT_SINK@", f"{pct}%")[0] == 0


def step(delta):
    """hangerő-billentyű: ±lépés, legfeljebb 100% (a némítás feloldódik)"""
    st = state()
    if not st["ok"]:
        return st
    v = max(0, min(100 if delta > 0 and st["volume"] <= 100 else MAX, st["volume"] + delta))
    if st["mute"] and delta > 0:
        _pactl("set-sink-mute", "@DEFAULT_SINK@", "0")
    set_volume(v)
    return state()


def toggle_mute(source=False):
    return _pactl("set-source-mute" if source else "set-sink-mute",
                  "@DEFAULT_SOURCE@" if source else "@DEFAULT_SINK@", "toggle")[0] == 0


def set_mute(on, source=False):
    return _pactl("set-source-mute" if source else "set-sink-mute",
                  "@DEFAULT_SOURCE@" if source else "@DEFAULT_SINK@", "1" if on else "0")[0] == 0


def set_default(name, source=False):
    if not re.match(r"^[\w.:@+-]+$", name):
        return False
    return _pactl("set-default-source" if source else "set-default-sink", name)[0] == 0


def set_port(sink, port):
    if not re.match(r"^[\w.:@+-]+$", sink) or not re.match(r"^[\w.:@+-]+$", port):
        return False
    return _pactl("set-sink-port", sink, port)[0] == 0


def _tone_file():
    """rövid, kellemes próbahang (két szinusz, le-felfutással) — egyszer készül el"""
    fn = os.path.join(tempfile.gettempdir(), f"fusion-sound-test-{os.getuid()}.wav")
    if os.path.isfile(fn):
        return fn
    rate, frames = 48000, []
    for f0, dur in ((660, 0.18), (880, 0.28)):
        n = int(rate * dur)
        for i in range(n):
            env = min(1.0, i / 600, (n - i) / 2400)
            v = int(0.35 * 32767 * env * math.sin(2 * math.pi * f0 * i / rate))
            frames.append(struct.pack("<hh", v, v))
    data = b"".join(frames)
    hdr = b"RIFF" + struct.pack("<I", 36 + len(data)) + b"WAVEfmt " + struct.pack("<IHHIIHH", 16, 1, 2, rate, rate * 4, 4, 16) \
        + b"data" + struct.pack("<I", len(data))
    with open(fn + ".tmp", "wb") as f:
        f.write(hdr + data)
    os.replace(fn + ".tmp", fn)
    return fn


def test_sound(sink=""):
    """próbahang a megadott (vagy az alapértelmezett) kimeneten; visszaadja a paplay kilépési kódját"""
    args = ["paplay"] + (["--device=" + sink] if sink and re.match(r"^[\w.:@+-]+$", sink) else []) + [_tone_file()]
    try:
        return subprocess.run(args, capture_output=True, timeout=10, env=ENV).returncode
    except (OSError, subprocess.TimeoutExpired):
        return 1


def icon_for(st):
    if not st.get("ok") or not st.get("hasOutput"):
        return "volume-mute"
    if st["mute"] or st["volume"] == 0:
        return "volume-mute"
    return "volume-low" if st["volume"] < 50 else "volume"
