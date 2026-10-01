"""FusionOS — Google Drive a Fájlkezelőben (rclone, FUSE-csatolás)

A Drive egy kötetként látszik: ~/GoogleDrive — a Fájlkezelő, a LightBurn (ha a mappát látja) és minden
program úgy kezeli, mint egy mappát. A csatolást a fusion-drive.service felhasználói szolgáltatás végzi
(rclone mount, teljes helyi gyorsítótárral: a megnyitott / mentett fájl előbb helyben készül el, majd
a háttérben feltöltődik). Bejelentkezés: a böngészőben (Google OAuth, az rclone saját azonosítójával);
a hozzáférési jegy a felhasználó beállításai közt marad (~/.config/fusion/rclone.conf, csak a fusion olvassa).

A Fusion-felület csak ezt a modult hívja: connect / disconnect / status / start / stop.
"""
import json
import os
import re
import subprocess
import threading
import time
import urllib.request

HOME = os.path.expanduser("~")
CONF = os.environ.get("FUSION_DRIVE_CONF", os.path.join(HOME, ".config", "fusion", "rclone.conf"))
MOUNT = os.environ.get("FUSION_DRIVE_MOUNT", os.path.join(HOME, "GoogleDrive"))
CACHE = os.path.join(HOME, ".cache", "fusion", "drive")
LOG = os.path.join(HOME, ".local", "share", "fusion", "drive.log")
REMOTE = "gdrive"
UNIT = "fusion-drive.service"


def _run(cmd, timeout=15):
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, errors="replace", timeout=timeout)
        return p.returncode, p.stdout, p.stderr
    except (OSError, subprocess.TimeoutExpired) as e:
        return 1, "", str(e)


def configured():
    try:
        with open(CONF, encoding="utf-8") as f:
            return f"[{REMOTE}]" in f.read()
    except OSError:
        return False


def mounted():
    try:
        with open("/proc/self/mounts", encoding="utf-8") as f:
            for line in f:
                p = line.split()
                if len(p) > 2 and p[1].replace("\\040", " ") == MOUNT and p[2].startswith("fuse"):
                    return True
    except OSError:
        pass
    return False


def _systemctl(*args, timeout=30):
    return _run(["systemctl", "--user", *args], timeout=timeout)


def service_state():
    rc, out, _e = _systemctl("is-active", UNIT, timeout=5)
    return out.strip() or "?"


def _token():
    try:
        with open(CONF, encoding="utf-8") as f:
            for line in f:
                if line.startswith("token"):
                    return json.loads(line.split("=", 1)[1].strip())
    except (OSError, ValueError):
        pass
    return {}


def account():
    """a bejelentkezett Google-fiók (név, e-mail) és a tárhely — legjobb igyekezettel (internet kell)"""
    t = _token()
    if not t.get("access_token"):
        return {}
    req = urllib.request.Request("https://www.googleapis.com/drive/v3/about?fields=user(displayName,emailAddress),storageQuota",
                                 headers={"Authorization": "Bearer " + t["access_token"]})
    try:
        with urllib.request.urlopen(req, timeout=8) as r:
            d = json.load(r)
    except Exception:
        return {}
    q = d.get("storageQuota") or {}
    return {"name": (d.get("user") or {}).get("displayName", ""), "email": (d.get("user") or {}).get("emailAddress", ""),
            "used": int(q.get("usage") or 0), "total": int(q.get("limit") or 0)}


def status(with_account=False):
    st = {"configured": configured(), "mounted": mounted(), "service": service_state(), "path": MOUNT,
          "enabled": _systemctl("is-enabled", UNIT, timeout=5)[1].strip() == "enabled", "error": ""}
    if st["configured"] and not st["mounted"]:
        try:
            with open(LOG, encoding="utf-8", errors="replace") as f:
                lines = [ln.strip() for ln in f.readlines()[-30:] if "ERROR" in ln or "CRITICAL" in ln]
            st["error"] = re.sub(r"^\S+ \S+ ", "", lines[-1]) if lines else ""
        except OSError:
            pass
    if with_account and st["configured"]:
        st["account"] = account()
    return st


class Login:
    """bejelentkezés: rclone authorize → a böngészőben a Google-oldal → jegy → beállítás → csatolás"""

    def __init__(self, on_event):
        self.on_event = on_event          # on_event(kind, text): url | info | done | error
        self.proc = None

    def start(self):
        threading.Thread(target=self._work, daemon=True).start()

    def cancel(self):
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()

    def _work(self):
        try:
            self.proc = subprocess.Popen(["rclone", "authorize", "drive", "--auth-no-open-browser"],
                                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, errors="replace")
        except OSError as e:
            self.on_event("error", f"az rclone nem indul: {e}")
            return
        token, grab, buf = None, False, []
        for line in self.proc.stdout:
            m = re.search(r"(http://127\.0\.0\.1:\d+/auth\?state=\S+)", line)
            if m:
                url = m.group(1)
                self.on_event("url", url)
                open_browser(url)
                self.on_event("info", "Jelentkezzen be a böngészőben a Google-fiókjával, és engedélyezze a hozzáférést.")
            if "--->" in line:
                grab = True
                continue
            if "<---" in line:
                grab = False
                try:
                    token = json.loads("".join(buf).strip())
                except ValueError:
                    token = None
                continue
            if grab:
                buf.append(line.strip())
        rc = self.proc.wait()
        if not token:
            self.on_event("error", "a bejelentkezés megszakadt" + (f" (kód: {rc})" if rc else ""))
            return
        save_config(token)
        self.on_event("info", "Bejelentkezve — a Google Drive csatolása…")
        ok, msg = enable()
        self.on_event("done" if ok else "error", msg)


def save_config(token):
    os.makedirs(os.path.dirname(CONF), exist_ok=True)
    tmp = CONF + ".tmp"
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(f"[{REMOTE}]\ntype = drive\nscope = drive\ntoken = {json.dumps(token, separators=(',', ':'))}\n")
    os.replace(tmp, CONF)


def open_browser(url):
    """a böngésző (a http-kezelő program: pl. Firefox) — xdg-open a Programkezelő társításai szerint"""
    try:
        subprocess.Popen(["xdg-open", url], start_new_session=True, stdin=subprocess.DEVNULL,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError:
        pass


def wait_mounted(seconds=20):
    t0 = time.time()
    while time.time() - t0 < seconds:
        if mounted():
            return True
        if service_state() in ("failed",):
            return False
        time.sleep(0.5)
    return mounted()


def enable():
    """csatolás most és minden bejelentkezéskor"""
    os.makedirs(MOUNT, exist_ok=True)
    rc, out, err = _systemctl("enable", "--now", UNIT)
    if rc != 0:
        return False, (err or out).strip() or "a szolgáltatás nem indul"
    if wait_mounted():
        return True, "A Google Drive csatolva: " + MOUNT
    return False, "a csatolás nem sikerült — " + (status()["error"] or "lásd: ~/.local/share/fusion/drive.log")


def start():
    if not configured():
        return False, "nincs bejelentkezve (Beállítások → Google Drive)"
    _systemctl("reset-failed", UNIT)
    rc, out, err = _systemctl("start", UNIT)
    if rc != 0:
        return False, (err or out).strip()
    return (True, MOUNT) if wait_mounted() else (False, status()["error"] or "a csatolás nem sikerült")


def stop():
    _systemctl("stop", UNIT)
    return not mounted()


def set_autostart(on):
    rc, out, err = _systemctl("enable" if on else "disable", UNIT)
    return rc == 0


def disconnect(clear_cache=True):
    """leválasztás: csatolás le, automatikus indítás ki, a hozzáférési jegy és a gyorsítótár törlése
    (a Google Drive-on lévő fájlok érintetlenek)"""
    _systemctl("disable", "--now", UNIT)
    if mounted():
        _run(["fusermount3", "-uz", MOUNT], timeout=10)
    try:
        os.unlink(CONF)
    except OSError:
        pass
    if clear_cache:
        import shutil
        shutil.rmtree(CACHE, ignore_errors=True)
    try:
        if os.path.isdir(MOUNT) and not os.listdir(MOUNT):
            os.rmdir(MOUNT)
    except OSError:
        pass
    return not configured()


def cache_size():
    tot = 0
    for root, _d, files in os.walk(CACHE):
        for f in files:
            try:
                tot += os.lstat(os.path.join(root, f)).st_blocks * 512
            except OSError:
                pass
    return tot
