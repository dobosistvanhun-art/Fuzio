"""filesearch — fájlkeresés név szerint (a Start menü gyorskeresője, 0.0.55)

    build(roots=None)        index: [(kereső-név, út, mappa-e)] — a saját mappa és a Tárhely (Adatlemez)
    search(index, q, n=12)   a legjobb találatok: [{name, path, dir, folder}]
    norm(s)                  kisbetűs, ékezet nélküli alak (a „fuzio” a „Fúzió”-t is megtalálja)

Csak a fájlneveket nézi (a tartalmat nem), a memóriában tartja, fájlba nem ír. Kihagyja a rejtett mappákat
és a nagy, felhasználónak érdektelen fákat (Windows-környezetek, gyorsítótárak, build-kimenet, node_modules);
a Google Drive-ot (hálózat) sem járja be.
"""
import os
import time
import unicodedata

SKIP = {"node_modules", "__pycache__", "site-packages", "drive_c", "GoogleDrive", "cache", ".cache", "lost+found",
        "dosdevices", "proc", "sys"}
MAX_ENTRIES = 300000
MAX_DEPTH = 9


def norm(s):
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c)).lower()


def default_roots():
    home = os.path.expanduser("~")
    roots = [home]
    st = os.path.join(home, "Tárhely")
    if os.path.islink(st) and os.path.ismount(os.path.realpath(st)):
        roots.append(os.path.realpath(st))
    return roots


def build(roots=None, budget_s=60):
    roots = roots or default_roots()
    out = []
    t0 = time.monotonic()
    for r in roots:
        base = r.rstrip("/").count("/")
        for dirpath, dirs, files in os.walk(r):
            depth = dirpath.count("/") - base
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in SKIP
                       and not (d == "out" and os.path.basename(dirpath) == "build")
                       and not os.path.ismount(os.path.join(dirpath, d))]
            if depth >= MAX_DEPTH:
                dirs[:] = []
            for d in dirs:
                out.append((norm(d), os.path.join(dirpath, d), True))
            for f in files:
                if not f.startswith("."):
                    out.append((norm(f), os.path.join(dirpath, f), False))
            if len(out) >= MAX_ENTRIES or time.monotonic() - t0 > budget_s:
                return out
    return out


def search(index, q, n=12):
    q = norm(q.strip())
    if len(q) < 2:
        return []
    words = q.split()
    best = []
    for name, path, isdir in index:
        if not all(w in name for w in words):
            continue
        # pontozás: pontos egyezés < a név eleje < szó eleje < bárhol; rövidebb út előrébb
        if name == q or os.path.splitext(name)[0] == q:
            sc = 0
        elif name.startswith(words[0]):
            sc = 1
        elif any(name[i - 1] in " _-." for i in range(1, len(name)) if name.startswith(words[0], i)):
            sc = 2
        else:
            sc = 3
        best.append((sc, path.count("/"), len(name), path, isdir))
        if len(best) > 4000:
            break
    best.sort()
    home = os.path.expanduser("~")
    return [{"name": os.path.basename(p), "path": p, "dir": d,
             "folder": os.path.dirname(p).replace(home, "~", 1)} for _s, _d, _l, p, d in best[:n]]
