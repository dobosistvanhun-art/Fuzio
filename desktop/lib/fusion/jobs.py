"""feladat-protokoll (M8b) — a hosszú műveletek (telepítés, rendszerfrissítés, mentés, telepítő pendrive, hibajelentés)

A futtatott parancs kimenete (soronként):

    LÉPÉS <i>/<n>: <szöveg>     a felület lépésszövege
    PROGRESS <0–100>            haladás
    <bármi más>                 napló
    kilépési kód: 0 = kész, más = sikertelen (az utolsó naplósor az ok)

A feladat külön folyamatban fut (a felület bezárása nem szakítja meg); az állapota fájlban van, így egy újranyitott
ablak, a Shell vagy egy szkript is látja:

    <JOBS_DIR>/<név>.json     {name, title, app, icon, cmd, pid, started, finished, rc, step, progress}
    <JOBS_DIR>/<név>.log      a teljes napló (a végén RC=<kód>)

JOBS_DIR: a felhasználónak $XDG_RUNTIME_DIR/fusion/jobs, rootnak /run/fusion/jobs — indításkor üres (a /run
memóriában van), ezért egy korábbi indítás feladata nem látszik „frissnek”.

    from fusion import jobs
    jobs.start("backup", "DATA mentése", ["sudo", "-n", ADMIN, "backup", "create", mp], app="Mentés", okpat="^kész")
    jobs.state("backup")   → {running, rc, title, recent, lines, step, progress, …}
    jobs.list_jobs()
A végén értesítés megy (fusion.notify): kész / sikertelen.
"""
import json
import os
import re
import subprocess
import sys
import time

from . import DESKTOP_LIB, RUN

NAME_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,31}$")
STEP_RE = re.compile(r"^LÉPÉS\s+(\d+)\s*/\s*(\d+)\s*:\s*(.*)$")
PROGRESS_RE = re.compile(r"^PROGRESS\s+(\d{1,3})\s*$")
RECENT_SECS = 600


def jobs_dir():
    env = os.environ.get("FUSION_JOBS_DIR")
    if env:
        return env
    if os.getuid() == 0:
        return os.path.join(RUN, "jobs")
    rt = os.environ.get("XDG_RUNTIME_DIR") or f"/run/user/{os.getuid()}"
    return os.path.join(rt, "fusion", "jobs")


def _paths(name):
    if not NAME_RE.match(name or ""):
        raise ValueError("érvénytelen feladatnév: " + str(name))
    d = jobs_dir()
    return os.path.join(d, name + ".json"), os.path.join(d, name + ".log")


def parse_line(line):
    """("step", i, n, szöveg) | ("progress", p) | ("log", sor)"""
    m = STEP_RE.match(line)
    if m:
        return ("step", int(m.group(1)), int(m.group(2)), m.group(3).strip())
    m = PROGRESS_RE.match(line)
    if m:
        return ("progress", max(0, min(100, int(m.group(1)))))
    return ("log", line)


def _write_json(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    os.replace(tmp, path)


def _read_json(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _alive(pid):
    """fut-e a feladat futtatója (zombi és újrahasznosított pid nem számít)"""
    if not pid:
        return False
    try:
        with open(f"/proc/{pid}/stat") as f:
            if f.read().split(")")[-1].split()[:1] == ["Z"]:
                return False
        with open(f"/proc/{pid}/cmdline", "rb") as f:
            return b"fusion.jobs" in f.read()
    except OSError:
        return False


def state(name, lines=14):
    """a feladat állapota (a felületeknek); nem létező feladat: running = False, rc = None"""
    fj, fl = _paths(name)
    j = _read_json(fj)
    try:
        with open(fl, encoding="utf-8", errors="replace") as f:
            log = f.read().splitlines()
    except OSError:
        log = []
    running = _alive(j.get("pid"))
    rc = j.get("rc")
    if rc is None:
        rc = next((int(x[3:]) for x in reversed(log) if re.match(r"^RC=-?\d+$", x)), None)
    if not running and rc is None and j.get("pid"):
        rc = -1                                   # a futtató váratlanul leállt
    fin = j.get("finished") or 0
    return {"name": name, "title": j.get("title", ""), "app": j.get("app", ""), "icon": j.get("icon", ""),
            "running": running, "rc": rc, "started": j.get("started", 0), "finished": fin,
            "recent": running or bool(fin and time.time() - fin < RECENT_SECS),
            "step": j.get("step") or {}, "progress": j.get("progress"),
            "lines": [x for x in log if not x.startswith("RC=")][-lines:]}


def list_jobs():
    try:
        names = sorted(f[:-5] for f in os.listdir(jobs_dir()) if f.endswith(".json") and NAME_RE.match(f[:-5]))
    except OSError:
        names = []
    return [state(n) for n in names]


def start(name, title, cmd, app="FusionOS", icon="settings", okpat="", env=None):
    """a feladat indítása külön folyamatban → (hibaszöveg | "", Popen | None)
    A hívó tartsa meg a Popen-t és hívja a poll()-t (ne maradjon zombi), vagy hagyja a init-re."""
    fj, fl = _paths(name)
    if state(name)["running"]:
        return "már fut egy művelet — várja meg a végét", None
    os.makedirs(os.path.dirname(fj), exist_ok=True)
    _write_json(fj, {"name": name, "title": title, "app": app, "icon": icon, "cmd": list(cmd), "okpat": okpat,
                     "pid": 0, "started": time.time(), "finished": 0, "rc": None, "step": {}, "progress": None})
    with open(fl, "w", encoding="utf-8"):
        pass
    e = dict(os.environ if env is None else env)
    e["PYTHONPATH"] = DESKTOP_LIB + (os.pathsep + e["PYTHONPATH"] if e.get("PYTHONPATH") else "")
    e["FUSION_JOBS_DIR"] = os.path.dirname(fj)
    pr = subprocess.Popen([sys.executable, "-m", "fusion.jobs", "_run", name], env=e, start_new_session=True,
                          stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    j = _read_json(fj)
    if not j.get("pid"):
        j["pid"] = pr.pid
        _write_json(fj, j)
    return "", pr


def _run(name):
    """a futtató (külön folyamat): a parancs kimenetét a protokoll szerint feldolgozza"""
    fj, fl = _paths(name)
    j = _read_json(fj)
    j["pid"] = os.getpid()
    _write_json(fj, j)
    rc = 127
    last_write = 0.0
    with open(fl, "a", encoding="utf-8") as log:
        try:
            p = subprocess.Popen(j["cmd"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL)
            for raw in p.stdout:
                line = raw.decode("utf-8", errors="replace").rstrip("\r\n")
                log.write(line + "\n")
                log.flush()
                ev = parse_line(line)
                if ev[0] == "step":
                    j["step"] = {"i": ev[1], "n": ev[2], "text": ev[3]}
                elif ev[0] == "progress":
                    j["progress"] = ev[1]
                else:
                    continue
                now = time.time()
                if now - last_write > 0.3:
                    _write_json(fj, j)
                    last_write = now
            rc = p.wait()
        except OSError as e:
            log.write(f"{j['cmd'][0] if j.get('cmd') else '?'}: {e}\n")
            rc = 127
        log.write(f"RC={rc}\n")
    j.update(rc=rc, finished=time.time())
    _write_json(fj, j)
    # értesítés a végén
    try:
        with open(fl, encoding="utf-8", errors="replace") as f:
            lines = [x for x in f.read().splitlines() if x.strip() and not x.startswith("RC=")
                     and parse_line(x)[0] == "log"]
        from . import notify
        if rc == 0:
            pat = re.compile(j["okpat"]) if j.get("okpat") else None
            ok = [x for x in lines if pat and pat.search(x)]
            notify.send(j.get("title", name) + ": kész", ok[-1] if ok else "", icon=j.get("icon") or "",
                        app=j.get("app") or "FusionOS")
        else:
            err = lines[-1] if lines else f"kilépési kód: {rc}"
            notify.send(j.get("title", name) + ": sikertelen", err.split(": ", 1)[-1], icon=j.get("icon") or "",
                        app=j.get("app") or "FusionOS", urgency="critical")
    except Exception:          # az értesítés hiánya nem teheti tönkre a feladat eredményét
        pass
    return rc


def main(argv=None):
    """fusion.jobs _run <név>  (belső: a futtató)"""
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) == 2 and argv[0] == "_run":
        return _run(argv[1])
    print("használat: python3 -m fusion.jobs _run <név> (belső)", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
