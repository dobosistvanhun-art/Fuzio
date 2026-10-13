"""Bluetooth — adapter és eszközök (BlueZ, a szabványos bluetoothctl-on át)

    adapter()                {present, address, name, powered, discoverable, pairable, discovering, blocked, hardBlocked,
                              service}  — adapter nélkül present = False
    devices()                [{address, name, icon, kind, paired, trusted, connected, battery}] (párosítottak elöl)
    power(on)                (ok, üzenet) — ha a rádió tiltva (rfkill), előbb feloldja (fusion-admin)
    scan(mp)                 keresés mp másodpercig; utána a devices() a talált eszközöket is mutatja
    pair(cím, esemény=None)  párosítás + megbízható + csatlakozás; az esemény(típus, szöveg) hívja a kódot, ha a
                             másik eszköz kijelzésre kér („passkey”: gépelje be a billentyűzeten, „confirm”: egyezik-e)
    connect / disconnect / remove(cím)

Általános: bármely BlueZ-adaptert kezel (Intel, Realtek, Broadcom, USB-s hardverkulcs). A hang (fejhallgató,
hangszóró) a PipeWire Bluetooth-modulján át a Hang oldalon jelenik meg, a beviteli eszközök (egér, billentyűzet)
a kernel HID-rétegén át.
"""
import os
import re
import select
import subprocess
import time

from . import ADMIN, permissions

CTL = os.environ.get("FUSION_BLUETOOTHCTL", "bluetoothctl")
RFKILL_DIR = os.environ.get("FUSION_RFKILL", "/sys/class/rfkill")
ADDR = re.compile(r"^[0-9A-Fa-f]{2}(:[0-9A-Fa-f]{2}){5}$")
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]|\x01|\x02|\r")

# a BlueZ „Icon” mezője → a felület fajtája
KINDS = {"audio-headset": "fejhallgató", "audio-headphones": "fejhallgató", "audio-card": "hangszóró",
         "input-keyboard": "billentyűzet", "input-mouse": "egér", "input-tablet": "rajztábla",
         "input-gaming": "játékvezérlő", "phone": "telefon", "computer": "számítógép", "printer": "nyomtató",
         "camera-photo": "fényképező", "camera-video": "kamera", "modem": "modem", "network-wireless": "hálózat"}


def _ctl(*args, timeout=15):
    try:
        r = subprocess.run([CTL] + list(args), capture_output=True, text=True, timeout=timeout,
                           stdin=subprocess.DEVNULL)
        return r.returncode, ANSI.sub("", r.stdout + r.stderr)
    except FileNotFoundError:
        return 127, "a bluetoothctl nincs telepítve"
    except subprocess.TimeoutExpired:
        return 124, "időtúllépés"


def _fields(text):
    """„  Kulcs: érték” sorok → {kulcs: érték} (az ismétlődő UUID-sorok közül az első marad)"""
    d = {}
    for line in text.splitlines():
        m = re.match(r"^\s+([A-Za-z][A-Za-z ]*):\s*(.*)$", line)
        if m and m.group(1) not in d:
            d[m.group(1)] = m.group(2).strip()
    return d


def _yes(v):
    return v == "yes"


def rfkill():
    """(soft, hard) tiltás a bluetooth rádiókra; (None, None), ha nincs ilyen"""
    soft = hard = None
    try:
        names = os.listdir(RFKILL_DIR)
    except OSError:
        names = []
    for n in names:
        d = os.path.join(RFKILL_DIR, n)
        try:
            with open(os.path.join(d, "type")) as f:
                if f.read().strip() != "bluetooth":
                    continue
            with open(os.path.join(d, "soft")) as f:
                s = f.read().strip() == "1"
            with open(os.path.join(d, "hard")) as f:
                h = f.read().strip() == "1"
        except OSError:
            continue
        soft = bool(soft) or s
        hard = bool(hard) or h
    return soft, hard


def _service():
    try:
        r = subprocess.run(["systemctl", "is-active", "bluetooth.service"], capture_output=True, text=True, timeout=5)
        return r.stdout.strip() or "unknown"
    except (OSError, subprocess.TimeoutExpired):
        return "unknown"


def adapter():
    soft, hard = rfkill()
    rc, out = _ctl("show", timeout=8)
    m = re.search(r"Controller ([0-9A-F:]{17})", out)
    a = {"present": bool(m), "address": m.group(1) if m else "", "blocked": bool(soft), "hardBlocked": bool(hard),
         "service": _service()}
    if not m:
        a.update(name="", powered=False, discoverable=False, pairable=False, discovering=False,
                 message="nincs Bluetooth-adapter" if "No default controller" in out or rc == 0 else out.strip()[-200:])
        return a
    f = _fields(out)
    a.update(name=f.get("Alias") or f.get("Name", ""), powered=_yes(f.get("Powered")),
             discoverable=_yes(f.get("Discoverable")), pairable=_yes(f.get("Pairable")),
             discovering=_yes(f.get("Discovering")), message="")
    return a


def info(addr):
    rc, out = _ctl("info", addr, timeout=8)
    f = _fields(out)
    bat = None
    m = re.search(r"Battery Percentage:\s*0x[0-9a-fA-F]+\s*\((\d+)\)", out)
    if m:
        bat = int(m.group(1))
    icon = f.get("Icon", "")
    return {"address": addr, "name": f.get("Alias") or f.get("Name") or addr, "icon": icon,
            "kind": KINDS.get(icon, "eszköz"), "paired": _yes(f.get("Paired")) or _yes(f.get("Bonded")),
            "trusted": _yes(f.get("Trusted")), "connected": _yes(f.get("Connected")),
            "blocked": _yes(f.get("Blocked")), "battery": bat}


def devices():
    rc, out = _ctl("devices", timeout=8)
    addrs = re.findall(r"^Device ([0-9A-F:]{17})", out, re.M)
    res = [info(a) for a in addrs]
    res.sort(key=lambda d: (not d["connected"], not d["paired"], d["name"] == d["address"], d["name"].lower()))
    return res


def _admin(*args):
    try:
        r = subprocess.run(["sudo", "-n", ADMIN] + list(args), capture_output=True, text=True, timeout=30)
        return r.returncode, (r.stdout + r.stderr).strip()
    except (OSError, subprocess.TimeoutExpired) as e:
        return 1, str(e)


def _check_addr(addr):
    if not ADDR.match(addr or ""):
        raise ValueError(f"érvénytelen Bluetooth-cím: {addr}")


def power(on, program="fusion"):
    if not permissions.check(program, "system:bluetooth"):
        return False, "nincs engedély"
    if on:
        soft, hard = rfkill()
        if hard:
            return False, "a Bluetooth-rádió kapcsolóval ki van kapcsolva (Fn-billentyű / vezeték nélküli kapcsoló)"
        if soft:
            rc, msg = _admin("rfkill-unblock", "bluetooth")
            if rc != 0:
                return False, msg
            time.sleep(1.5)
    rc, out = _ctl("power", "on" if on else "off")
    ok = rc == 0 and "succeeded" in out
    return ok, "" if ok else (out.strip().splitlines() or ["nem sikerült"])[-1]


def scan(seconds=10):
    seconds = max(3, min(int(seconds), 60))
    rc, out = _ctl("--timeout", str(seconds), "scan", "on", timeout=seconds + 10)
    ok = "Discovery started" in out or rc == 0
    return ok, "" if ok else (out.strip().splitlines() or ["a keresés nem indult"])[-1]


def _simple(cmd, addr, good, program):
    _check_addr(addr)
    if not permissions.check(program, "system:bluetooth"):
        return False, "nincs engedély"
    rc, out = _ctl(cmd, addr, timeout=30)
    ok = any(g in out for g in good)
    return ok, "" if ok else (out.strip().splitlines() or ["nem sikerült"])[-1]


def connect(addr, program="fusion"):
    return _simple("connect", addr, ("Connection successful",), program)


def disconnect(addr, program="fusion"):
    return _simple("disconnect", addr, ("Successful disconnected", "Disconnection successful"), program)


def _known(addr):
    rc, out = _ctl("devices", timeout=8)
    return addr.upper() in out.upper()


def remove(addr, program="fusion"):
    """eltávolítás (a párosítás törlése); ha az eszköz épp kapcsolódik, a BlueZ „InProgress”-szel elutasíthatja —
    ilyenkor bontás után még egyszer; a siker mércéje: az eszköz eltűnt a listából"""
    ok, msg = _simple("remove", addr, ("Device has been removed",), program)
    if ok or msg == "nincs engedély":
        return ok, msg
    for _ in range(2):
        if not _known(addr):
            return True, ""
        _ctl("disconnect", addr, timeout=15)
        time.sleep(2)
        ok, msg = _simple("remove", addr, ("Device has been removed",), program)
        if ok:
            return True, ""
    return (True, "") if not _known(addr) else (False, msg)


def trust(addr, program="fusion"):
    return _simple("trust", addr, ("trust succeeded",), program)


def pair(addr, event=None, timeout=60, program="fusion"):
    """párosítás a bluetoothctl párbeszédén át, saját ügynökkel (KeyboardDisplay): a kérdésekre a felület helyett
    válaszol — megerősítés: igen (a kódot az esemény mutatja), PIN-kód (régi eszköz): 0000"""
    _check_addr(addr)
    if not permissions.check(program, "system:bluetooth"):
        return False, "nincs engedély"
    try:
        p = subprocess.Popen([CTL], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, bufsize=0)
    except FileNotFoundError:
        return False, "a bluetoothctl nincs telepítve"
    buf, ok, msg, stage = "", False, "időtúllépés — az eszköz nem válaszolt (párosítható módban van?)", "pair"

    def send(s):
        try:
            p.stdin.write((s + "\n").encode())
            p.stdin.flush()
        except OSError:
            pass
    send("agent KeyboardDisplay")
    time.sleep(0.4)
    send("default-agent")
    time.sleep(0.4)
    send(f"pair {addr}")
    end = time.time() + timeout
    try:
        while time.time() < end:
            r, _, _ = select.select([p.stdout], [], [], 0.5)
            if not r:
                continue
            chunk = os.read(p.stdout.fileno(), 4096)
            if not chunk:
                break
            buf += ANSI.sub("", chunk.decode("utf-8", "replace"))
            while True:
                m = re.search(r"Confirm passkey (\d+)[^\n]*\(yes/no\):", buf)
                if m:
                    if event:
                        event("confirm", m.group(1))
                    send("yes")
                    buf = buf[m.end():]
                    continue
                m = re.search(r"Passkey: (\d+)", buf)
                if m:
                    if event:
                        event("passkey", m.group(1))
                    buf = buf[m.end():]
                    continue
                m = re.search(r"Enter (PIN code|passkey)[^:]*:", buf)
                if m:
                    send("0000")
                    if event:
                        event("pin", "0000")
                    buf = buf[m.end():]
                    continue
                m = re.search(r"Authorize service[^\n]*\(yes/no\):", buf)
                if m:
                    send("yes")
                    buf = buf[m.end():]
                    continue
                break
            if stage == "pair":
                if "Pairing successful" in buf or "AlreadyExists" in buf:
                    stage, buf = "trust", ""
                    send(f"trust {addr}")
                    end = max(end, time.time() + 25)
                elif re.search(r"Failed to pair[^\n]*\n", buf):
                    msg = re.search(r"Failed to pair:?\s*([^\n]*)", buf).group(1).strip() or "a párosítás nem sikerült"
                    break
                elif "not available" in buf:
                    msg = "az eszköz nem látható — keressen újra"
                    break
            elif stage == "trust" and ("trust succeeded" in buf or "Trusted: yes" in buf):
                stage, buf = "connect", ""
                send(f"connect {addr}")
            elif stage == "connect":
                if "Connection successful" in buf:
                    ok, msg = True, ""
                    break
                if re.search(r"Failed to connect[^\n]*\n", buf):
                    # párosítva van, csak most nem csatlakozott (pl. a fejhallgató máshoz kapcsolódott)
                    ok, msg = True, "párosítva, de a csatlakozás nem sikerült: " + \
                        re.search(r"Failed to connect:?\s*([^\n]*)", buf).group(1).strip()
                    break
    finally:
        send("quit")
        try:
            p.wait(timeout=3)
        except subprocess.TimeoutExpired:
            p.kill()
    if not ok:
        # a bluetoothctl üzenetei néha elmaradnak (QEMU: párosítva lett, de a „Pairing successful” nem jött) —
        # a mérce a BlueZ állapota: ha párosítva van, a megbízhatóság és a csatlakozás külön parancsokkal
        inf = info(addr)
        if inf["paired"]:
            if not inf["trusted"]:
                _ctl("trust", addr, timeout=15)
            if not inf["connected"]:
                rc, out = _ctl("connect", addr, timeout=20)
                if "Connection successful" not in out:
                    return True, "párosítva, de a csatlakozás nem sikerült"
            return True, ""
    return ok, msg


def summary():
    a = adapter()
    if not a["present"]:
        return "nincs Bluetooth-adapter" + (" (a rádió tiltva)" if a["blocked"] else "")
    con = [d["name"] for d in devices() if d["connected"]]
    return (f"{a['name']} ({a['address']}): " + ("bekapcsolva" if a["powered"] else "kikapcsolva")
            + (", csatlakozva: " + ", ".join(con) if con else ""))
