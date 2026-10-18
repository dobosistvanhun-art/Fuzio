"""papírnyomtatók — CUPS (a szabványos lpstat / lpinfo / lpadmin / lp parancsokon át)

    printers()                 [{name, info, model, uri, connection, state, stateText, reasons, accepting, default, shared}]
    discover(timeout=8)        a géphez csatlakoztatott és a hálózaton talált nyomtatók, amelyek még nincsenek felvéve
                               [{uri, info, model, connection, driverless, added}]
    drivers(model)             a modellhez illő meghajtók [{ppd, name}] — a legjobb elöl
    add(uri, model, name="", ppd="")   felvétel: driverless (IPP Everywhere) vagy a modellhez illő meghajtó
    remove(név) / set_default(név) / test_page(név) / enable(név)
    jobs()                     [{id, printer, user, size, time}] — a még ki nem nyomtatott feladatok
    cancel(id) / cancel_all(név)

A felhasználó az lpadmin csoport tagja: a CUPS a helyi felhasználónak jelszó nélkül engedi a nyomtatókezelést.
A USB-s, IPP-over-USB-képes nyomtatókat az ipp-usb a hálózatiakhoz hasonlóan, driverless módon teszi elérhetővé.
Általános: nem géphez kötött; a meghajtók: driverless (IPP Everywhere / AirPrint), HP (hpcups), Gutenprint, PDF.
"""
import os
import re
import shlex
import shutil
import subprocess

from . import permissions

STATE_TEXT = {3: "kész", 4: "nyomtat", 5: "leállítva"}
# az IPP printer-state-reasons gyakori értékei (az -error / -warning / -report utótag nélkül)
REASONS = {"paused": "szüneteltetve", "media-empty": "nincs papír", "media-needed": "nincs papír",
           "media-jam": "papírelakadás", "toner-low": "kevés a toner", "toner-empty": "kifogyott a toner",
           "marker-supply-low": "kevés a tinta / toner", "marker-supply-empty": "kifogyott a tinta / toner",
           "door-open": "nyitva a fedél", "cover-open": "nyitva a fedél", "offline": "nem elérhető",
           "connecting-to-device": "kapcsolódás…", "cups-missing-filter": "hiányzó szűrő (meghajtó)",
           "input-tray-missing": "hiányzik a papírtálca", "output-area-full": "tele a kimeneti tálca",
           "other": "egyéb hiba", "shutdown": "kikapcsolva", "timed-out": "nem válaszol"}
TESTPRINT = ("/usr/share/cups/data/testprint", "/usr/share/cups/data/default-testpage.pdf")
NAME_OK = re.compile(r"^[A-Za-z0-9_.-]{1,127}$")
URI_OK = re.compile(r"^[a-z][a-z0-9+.-]*:/\S*$")          # usb://…, ipp://…, dnssd://…, cups-pdf:/
CUPS_PDF_PPDS = ("/usr/share/ppd/cups-pdf/CUPS-PDF_opt.ppd", "/usr/share/ppd/cups-pdf/CUPS-PDF_noopt.ppd")


def _exe(cmd):
    """a CUPS kezelőparancsai (lpadmin, lpinfo, cupsenable …) a /usr/sbin-ben vannak — a felhasználó PATH-jában
    (Debian / Ubuntu) ez nincs benne"""
    return shutil.which(cmd) or shutil.which(cmd, path="/usr/sbin:/sbin:/usr/bin:/bin") or cmd


def _run(args, timeout=20, inp=None):
    args = [_exe(args[0])] + list(args[1:])
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=timeout, input=inp,
                           env=dict(os.environ, LC_ALL="C", LANG="C"))
        return r.returncode, r.stdout, r.stderr.strip()
    except FileNotFoundError:
        return 127, "", f"{args[0]}: nincs telepítve (CUPS)"
    except subprocess.TimeoutExpired:
        return 124, "", "időtúllépés"


def _err(rc, out, err, default="nem sikerült"):
    t = (err or out).strip().splitlines()
    return re.sub(r"^\w+: ", "", t[-1]) if t else default


def service():
    try:
        r = subprocess.run(["systemctl", "is-active", "cups.service"], capture_output=True, text=True, timeout=5)
        return r.stdout.strip() or "unknown"
    except (OSError, subprocess.TimeoutExpired):
        return "unknown"


def connection(uri):
    s = uri.split(":", 1)[0]
    if s == "usb" or "ipp-usb" in uri or re.match(r"^ipps?://(localhost|127\.0\.0\.1):6\d{4}", uri):
        return "USB"
    if s in ("ipp", "ipps", "dnssd", "socket", "lpd", "http", "https", "smb"):
        return "hálózat"
    if s == "cups-pdf":
        return "PDF-fájl"
    if s in ("hp", "hpfax"):
        return "HP"
    return s or "?"


def default_printer():
    rc, out, err = _run(["lpstat", "-d"], timeout=8)
    m = re.search(r"system default destination:\s*(\S+)", out)
    return m.group(1) if m else ""


def _options(name):
    rc, out, err = _run(["lpoptions", "-p", name], timeout=8)
    d = {}
    try:
        parts = shlex.split(out)
    except ValueError:
        parts = out.split()
    for p in parts:
        k, _, v = p.partition("=")
        d[k] = v
    return d


def printers():
    rc, out, err = _run(["lpstat", "-e"], timeout=8)
    names = [n.strip() for n in out.splitlines() if n.strip()]
    dflt = default_printer()
    res = []
    for n in names:
        o = _options(n)
        try:
            st = int(o.get("printer-state", "0"))
        except ValueError:
            st = 0
        reasons = [r for r in o.get("printer-state-reasons", "none").split(",") if r and r != "none"]
        uri = o.get("device-uri", "")
        texts = []
        for r in reasons:
            base = re.sub(r"-(error|warning|report)$", "", r)
            t = REASONS.get(base, base)
            if t not in texts:
                texts.append(t)
        res.append({"name": n, "info": o.get("printer-info") or n, "model": o.get("printer-make-and-model", ""),
                    "uri": uri, "connection": connection(uri), "state": st,
                    "stateText": STATE_TEXT.get(st, "ismeretlen"), "reasons": reasons, "reasonsText": texts,
                    "accepting": o.get("printer-is-accepting-jobs", "true") == "true",
                    "shared": o.get("printer-is-shared", "false") == "true", "default": n == dflt})
    res.sort(key=lambda p: (not p["default"], p["info"].lower()))
    return res


def _parse_long(out):
    devs, cur = [], None
    for line in out.splitlines():
        m = re.match(r"^Device: uri = (.*)$", line)
        if m:
            cur = {"uri": m.group(1).strip()}
            devs.append(cur)
            continue
        m = re.match(r"^\s+([a-z-]+) = (.*)$", line)
        if m and cur is not None:
            cur[m.group(1)] = m.group(2).strip()
    return devs


def _driverless_uri(uri):
    return bool(re.match(r"^ipps?://", uri)) or (uri.startswith("dnssd://") and "._ipp" in uri)


def discover(timeout=8):
    """lpinfo -l -v: a backendek által talált eszközök (usb, dnssd/ipp a hálózaton, ipp-usb)"""
    rc, out, err = _run(["lpinfo", "-l", "-v", "--timeout", str(int(timeout))], timeout=timeout + 90)
    if rc != 0 and not out:
        raise RuntimeError(_err(rc, out, err, "a keresés nem sikerült"))
    have = {p["uri"] for p in printers()}
    res, seen = [], set()
    for d in _parse_long(out):
        uri = d["uri"]
        if "://" not in uri or uri in seen or uri.startswith("cups-pdf"):
            continue
        seen.add(uri)
        model = d.get("make-and-model", "")
        if model.lower() in ("unknown", ""):
            model = ""
        res.append({"uri": uri, "info": d.get("info") or model or uri, "model": model,
                    "connection": connection(uri), "driverless": _driverless_uri(uri), "added": uri in have,
                    "class": d.get("class", "")})
    # a driverless (IPP) változat elöl: egy USB-s nyomtató ipp-usb-vel kétszer is látszhat
    res.sort(key=lambda x: (x["added"], not x["driverless"], x["info"].lower()))
    return res


def drivers(model):
    if not model:
        return []
    rc, out, err = _run(["lpinfo", "-m", "--make-and-model", model], timeout=180)
    res = []
    for line in out.splitlines():
        ppd, _, name = line.partition(" ")
        if ppd and ppd not in ("everywhere", "raw"):
            res.append({"ppd": ppd, "name": name.strip()})
    words = [w.lower() for w in re.findall(r"[A-Za-z0-9]+", model)]

    def score(d):
        n = d["name"].lower()
        hit = sum(1 for w in words if w in n)
        pref = 0 if "hpcups" in n or "hpijs" in d["ppd"] else 1 if "gutenprint" in n else 2
        return (-hit, pref, n)
    res.sort(key=score)
    return res


def make_name(text):
    n = re.sub(r"[^A-Za-z0-9_.-]+", "_", text or "").strip("_")[:60]
    return n or "Nyomtato"


def add(uri, model="", name="", ppd="", info="", program="fusion"):
    if not permissions.check(program, "system:printers"):
        return False, "nincs engedély", ""
    if not URI_OK.match(uri or ""):
        return False, f"érvénytelen eszközcím: {uri}", ""
    name = name or make_name(model or info or uri.split("://", 1)[1])
    if not NAME_OK.match(name):
        return False, f"érvénytelen nyomtatónév: {name}", ""
    tries = [ppd] if ppd else (["everywhere"] if _driverless_uri(uri) else []) + [d["ppd"] for d in drivers(model)[:1]]
    if not tries:
        return False, "nincs ehhez a nyomtatóhoz meghajtó — válasszon a listából, vagy próbálja a hálózati (IPP) címet", ""
    msg = ""
    for m in tries:
        args = ["lpadmin", "-p", name, "-E", "-v", uri, "-m", m, "-o", "printer-is-shared=false"]
        if info or model:
            args += ["-D", info or model]
        rc, out, err = _run(args, timeout=90)
        if rc == 0:
            _run(["cupsenable", name], timeout=10)
            _run(["cupsaccept", name], timeout=10)
            if not default_printer():
                _run(["lpadmin", "-d", name], timeout=10)
            return True, "", name
        msg = _err(rc, out, err)
    return False, msg, name


def add_pdf(program="fusion"):
    """„PDF” nyomtató (cups-pdf): a nyomtatás a ~/PDF mappába ment PDF-fájlt"""
    # a meghajtó ismert helyről (az lpinfo -m az összes meghajtót végigjárja — lassú gépen percekig tart)
    ppd = next(("lsb/usr/" + f.split("/usr/share/ppd/", 1)[1] for f in CUPS_PDF_PPDS if os.path.isfile(f)), "")
    if not ppd:
        rc, out, err = _run(["lpinfo", "-m"], timeout=180)
        ppd = next((l.split(" ", 1)[0] for l in out.splitlines() if "cups-pdf" in l.lower()), "")
    if not ppd:
        return False, "a PDF-nyomtató meghajtója (cups-pdf) nincs telepítve", ""
    return add("cups-pdf:/", "Generic CUPS-PDF Printer", name="PDF", ppd=ppd, info="PDF-fájlba (~/PDF)",
               program=program)


def remove(name, program="fusion"):
    if not NAME_OK.match(name or "") or not permissions.check(program, "system:printers"):
        return False, "érvénytelen név vagy nincs engedély"
    rc, out, err = _run(["lpadmin", "-x", name])
    return rc == 0, "" if rc == 0 else _err(rc, out, err)


def set_default(name, program="fusion"):
    if not NAME_OK.match(name or "") or not permissions.check(program, "system:printers"):
        return False, "érvénytelen név vagy nincs engedély"
    rc, out, err = _run(["lpadmin", "-d", name])
    return rc == 0, "" if rc == 0 else _err(rc, out, err)


def enable(name, program="fusion"):
    """leállított nyomtató újraindítása (pl. papírelakadás után) és a feladatok fogadása"""
    if not NAME_OK.match(name or "") or not permissions.check(program, "system:printers"):
        return False, "érvénytelen név vagy nincs engedély"
    rc, out, err = _run(["cupsenable", name])
    rc2, out2, err2 = _run(["cupsaccept", name])
    ok = rc == 0 and rc2 == 0
    return ok, "" if ok else _err(rc or rc2, out + out2, err or err2)


TEST_TEXT = """Fúzió — próbaoldal

Nyomtató: {name}
Ha ez az oldal olvasható, a nyomtató működik.

ÁRVÍZTŰRŐ TÜKÖRFÚRÓGÉP — árvíztűrő tükörfúrógép
0123456789
"""


def test_page(name):
    if not NAME_OK.match(name or ""):
        return False, "érvénytelen név", ""
    f = next((t for t in TESTPRINT if os.path.isfile(t)), None)
    if f:
        rc, out, err = _run(["lp", "-d", name, "-t", "Fúzió-probaoldal", f])
    else:
        rc, out, err = _run(["lp", "-d", name, "-t", "Fúzió-probaoldal", "-o", "document-format=text/plain", "-"],
                            inp=TEST_TEXT.format(name=name))
    m = re.search(r"request id is (\S+)", out)
    return rc == 0, "" if rc == 0 else _err(rc, out, err), m.group(1) if m else ""


def jobs():
    rc, out, err = _run(["lpstat", "-o"], timeout=8)
    res = []
    for line in out.splitlines():
        m = re.match(r"^(\S+)-(\d+)\s+(\S+)\s+(\d+)\s+(.*)$", line)
        if m:
            res.append({"id": f"{m.group(1)}-{m.group(2)}", "printer": m.group(1), "user": m.group(3),
                        "size": int(m.group(4)), "time": m.group(5).strip()})
    return res


def cancel(job_id):
    if not re.match(r"^[A-Za-z0-9_.-]+-\d+$", job_id or ""):
        return False, "érvénytelen feladat"
    rc, out, err = _run(["cancel", job_id])
    return rc == 0, "" if rc == 0 else _err(rc, out, err)


def cancel_all(name):
    if not NAME_OK.match(name or ""):
        return False, "érvénytelen név"
    rc, out, err = _run(["cancel", "-a", name])
    return rc == 0, "" if rc == 0 else _err(rc, out, err)


def summary():
    ps = printers()
    if not ps:
        return "nincs felvett nyomtató"
    return ", ".join(f"{p['info']} ({p['connection']}, {p['stateText']}{', alapértelmezett' if p['default'] else ''})"
                     for p in ps)
