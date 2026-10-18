"""Fúzió — Programbolt: a Flathub katalógusa (böngészés, keresés, részletek)

A Programkezelő része: a bolt csak a katalógust mutatja, a telepítést ugyanaz a háttér végzi
(fusion-programs install flathub:<azonosító>), mint a Programkezelőben.

Forrás: a Flathub nyilvános API-ja (https://flathub.org/api/v2) — magyar fordítással, ahol van
(locale=hu). Az ikonok és képernyőképek a ~/.cache/fusion/store mappába kerülnek (gyorsítótár).
Nincs fiók, nincs központi Fúzió-szerver.
"""
import hashlib
import html
import json
import os
import re
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

API = os.environ.get("FUSION_STORE_API", "https://flathub.org/api/v2")
LOCALE = "hu"
CACHE = os.path.join(os.environ.get("XDG_CACHE_HOME") or os.path.expanduser("~/.cache"), "fusion", "store")
UA = "Fuzio-Programbolt/1.0"
PER_PAGE = 30

# a Flathub fő kategóriái (az API kisbetűs nevei) — magyar név, Fúzió-ikon
CATEGORIES = [
    ("graphics", "Grafika", "file-image"),
    ("office", "Iroda", "file-text"),
    ("development", "Fejlesztés", "file-code"),
    ("network", "Internet", "web"),
    ("audiovideo", "Hang és videó", "display"),
    ("education", "Oktatás", "info"),
    ("science", "Tudomány", "chip"),
    ("game", "Játékok", "star"),
    ("utility", "Segédprogramok", "settings"),
    ("system", "Rendszer", "terminal"),
]


class StoreError(Exception):
    pass


_mem = {}
_lock = threading.Lock()


def _request(path, params=None, body=None, timeout=20):
    url = API + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    key = url + (json.dumps(body, sort_keys=True) if body is not None else "")
    with _lock:
        hit = _mem.get(key)
    if hit and time.time() - hit[0] < 300:
        return hit[1]
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, headers={"User-Agent": UA, "Accept": "application/json",
                                                         **({"Content-Type": "application/json"} if data else {})})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            res = json.load(r)
    except urllib.error.HTTPError as e:
        raise StoreError(f"a Flathub hibát adott ({e.code})")
    except (urllib.error.URLError, OSError) as e:
        reason = getattr(e, "reason", e)
        raise StoreError(f"a Flathub nem érhető el ({reason}) — van internet?")
    except ValueError:
        raise StoreError("a Flathub válasza nem értelmezhető")
    with _lock:
        _mem[key] = (time.time(), res)
    return res


def _hit(h):
    return {"appid": h.get("app_id") or h.get("id", ""), "name": h.get("name", ""), "summary": h.get("summary", ""),
            "icon": h.get("icon") or "", "developer": h.get("developer_name") or "",
            "verified": bool(h.get("verification_verified")), "free": bool(h.get("is_free_license", True)),
            "type": h.get("type", "")}


def _hits(res):
    hits = [_hit(h) for h in res.get("hits", []) if (h.get("type") or "desktop-application") != "addon"]
    return {"apps": [h for h in hits if h["appid"]], "page": res.get("page", 1), "pages": res.get("totalPages", 1),
            "total": res.get("totalHits", len(hits))}


def popular(page=1):
    return _hits(_request("/collection/popular", {"page": page, "per_page": PER_PAGE, "locale": LOCALE}))


def category(cat, page=1):
    if cat not in {c[0] for c in CATEGORIES}:
        raise StoreError("ismeretlen kategória: " + cat)
    return _hits(_request("/collection/category/" + cat, {"page": page, "per_page": PER_PAGE, "locale": LOCALE}))


def search(query, page=1):
    q = query.strip()
    if not q:
        return {"apps": [], "page": 1, "pages": 1, "total": 0}
    return _hits(_request("/search", {"locale": LOCALE}, {"query": q, "hits_per_page": PER_PAGE, "page": page}))


def _text(desc):
    """az AppStream-leírás (egyszerű HTML) → olvasható szöveg: bekezdések üres sorral, felsorolás •-tel"""
    t = re.sub(r"\s+", " ", desc or "")                     # a HTML-ben a sortörés szóköz
    t = re.sub(r"(?i)\s*<li[^>]*>\s*", "\n  • ", t)
    t = re.sub(r"(?i)\s*(</p>|</ul>|</ol>)\s*", "\n\n", t)
    t = re.sub(r"(?i)\s*<br\s*/?>\s*", "\n", t)
    t = html.unescape(re.sub(r"<[^>]+>", "", t))
    t = "\n".join(ln.rstrip() for ln in t.split("\n"))
    return re.sub(r"\n{3,}", "\n\n", t).strip("\n ")


def _shot(s, want=752):
    sizes = s.get("sizes") or []
    best = None
    for z in sizes:
        try:
            w = int(str(z.get("width", "0")).rstrip("px") or 0)
        except ValueError:
            w = 0
        if best is None or abs(w - want) < abs(best[0] - want):
            best = (w, z.get("src", ""))
    return best[1] if best else ""


def details(appid):
    if not re.match(r"^[A-Za-z_][\w.-]{5,254}$", appid):
        raise StoreError("érvénytelen azonosító")
    a = _request("/appstream/" + appid, {"locale": LOCALE})
    try:
        s = _request("/summary/" + appid)
    except StoreError:
        s = {}
    rel = (a.get("releases") or [{}])[0] or {}
    urls = a.get("urls") or {}
    icon = a.get("icon") or ""
    for ic in a.get("icons") or []:
        if ic.get("url") and (ic.get("width") or 0) >= 128:
            icon = ic["url"]
    return {"appid": appid, "name": a.get("name", appid), "summary": a.get("summary", ""),
            "description": _text(a.get("description", "")), "developer": a.get("developer_name") or "",
            "license": a.get("project_license") or "", "free": bool(a.get("is_free_license", True)),
            "version": rel.get("version") or "", "date": str(rel.get("date") or rel.get("timestamp") or "")[:10],
            "homepage": urls.get("homepage", ""), "icon": icon,
            "screenshots": [u for u in (_shot(x) for x in (a.get("screenshots") or [])[:4]) if u],
            "download": s.get("download_size") or 0, "installed": s.get("installed_size") or 0,
            "verified": bool((a.get("metadata") or {}).get("flathub::verification::verified"))}


def _cache_file(url):
    ext = os.path.splitext(urllib.parse.urlparse(url).path)[1].lower()
    ext = ext if ext in (".png", ".jpg", ".jpeg", ".svg", ".webp") else ".png"
    return os.path.join(CACHE, hashlib.sha1(url.encode()).hexdigest() + ext)


def cached_path(url):
    """a már letöltött kép helyi útja, letöltés nélkül ('' ha még nincs)"""
    if not url:
        return ""
    fn = _cache_file(url)
    return fn if os.path.isfile(fn) and os.path.getsize(fn) > 0 else ""


def cached(url, timeout=20):
    """kép letöltése a gyorsítótárba → helyi út ('' ha nem sikerült)"""
    if not url or not url.startswith(("https://", "http://127.0.0.1")):
        return ""
    fn = _cache_file(url)
    if os.path.isfile(fn) and os.path.getsize(fn) > 0:
        return fn
    os.makedirs(CACHE, exist_ok=True)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = r.read(20 * 1048576)
    except (urllib.error.URLError, OSError, ValueError):
        return ""
    tmp = fn + ".tmp"
    with open(tmp, "wb") as f:
        f.write(data)
    os.replace(tmp, fn)
    return fn


def prune_cache(max_mib=200):
    """a gyorsítótár ne nőjön korlátlanul: a legrégebben használt képek mennek"""
    try:
        files = [(os.path.getatime(p), os.path.getsize(p), p) for p in
                 (os.path.join(CACHE, f) for f in os.listdir(CACHE))]
    except OSError:
        return
    total = sum(s for _a, s, _p in files)
    for _a, s, p in sorted(files):
        if total <= max_mib * 1048576:
            break
        try:
            os.unlink(p)
            total -= s
        except OSError:
            pass
