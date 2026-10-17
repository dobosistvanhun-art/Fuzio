"""Vas & Króm — a motorok oldalnézeti rajza (SVG), az alkatrészekből összerakva

render(bike) → {"body": svg-út, "over": a kerekek elé kerülő réteg (kipufogó, féknyereg), "rear": svg-út, "front": svg-út,
                "w", "h", "rx", "ry", "rr", "fx", "fy", "fr", "ground"}
A kerekek külön képek (a verseny alatt forognak); a fájlok a tartalom szerinti néven a gyorsítótárba kerülnek.
Minden saját rajz: a márkák és a formák kitaláltak.

0.0.49: új rajzok — típusonként saját forma (bobber, café racer, cruiser, chopper, V8), bordázott hengerek, tolórudak,
primer-fedél, árnyalt fényezés csillanással, csíkozás, bőrülés varrással, küllős (keresztbe fűzött) és öntött kerekek
féktárcsával és szíjtárcsával, láncfeszítő, lábtartók, árnyék a talajon. A Qt SVG-rajzolója (SVG Tiny 1.2) szűrőt
és vágómaszkot nem tud — a térhatás színátmenetekből és rétegekből áll.
"""
import hashlib
import math
import os

from model import MODELS, PARTS

if os.name == "nt":
    CACHE = os.environ.get("VASKROM_CACHE", os.path.join(os.environ.get("LOCALAPPDATA") or os.path.expanduser("~"), "VasEsKrom", "cache"))
else:
    CACHE = os.environ.get("VASKROM_CACHE", os.path.join(os.path.expanduser("~"), ".cache", "vaskrom"))
W, H = 680, 380
CYL = 0.82              # a hengerek mérete a blokkhoz képest (a fej a tank alá férjen)
GROUND = 330
VERSION = "2"           # a gyorsítótár-név része: új rajzstílusnál a régi képek nem keverednek

BASE_DEFS = """
<linearGradient id="chrome" x1="0" y1="0" x2="0" y2="1">
 <stop offset="0" stop-color="#ffffff"/><stop offset="0.18" stop-color="#d7dde3"/><stop offset="0.42" stop-color="#7e8892"/>
 <stop offset="0.55" stop-color="#f4f7fa"/><stop offset="0.8" stop-color="#5d6670"/><stop offset="1" stop-color="#b9c1c9"/></linearGradient>
<linearGradient id="chromeh" x1="0" y1="0" x2="1" y2="0">
 <stop offset="0" stop-color="#5d6670"/><stop offset="0.35" stop-color="#f6f8fa"/><stop offset="0.6" stop-color="#9aa3ad"/>
 <stop offset="1" stop-color="#4c545c"/></linearGradient>
<radialGradient id="chromer" cx="0.38" cy="0.32" r="0.75">
 <stop offset="0" stop-color="#ffffff"/><stop offset="0.35" stop-color="#cfd6dc"/><stop offset="0.75" stop-color="#6f7882"/>
 <stop offset="1" stop-color="#3c434a"/></radialGradient>
<linearGradient id="gloss" x1="0" y1="0" x2="0" y2="1">
 <stop offset="0" stop-color="#4a5058"/><stop offset="0.3" stop-color="#1c1f23"/><stop offset="1" stop-color="#050506"/></linearGradient>
<linearGradient id="alu" x1="0" y1="0" x2="0" y2="1">
 <stop offset="0" stop-color="#e3e6e9"/><stop offset="0.45" stop-color="#a7aeb5"/><stop offset="1" stop-color="#5f666d"/></linearGradient>
<linearGradient id="fin" x1="0" y1="0" x2="1" y2="0">
 <stop offset="0" stop-color="#5a6067"/><stop offset="0.3" stop-color="#c9ced3"/><stop offset="0.55" stop-color="#eef1f3"/>
 <stop offset="1" stop-color="#6b7279"/></linearGradient>
<linearGradient id="finb" x1="0" y1="0" x2="1" y2="0">
 <stop offset="0" stop-color="#15171a"/><stop offset="0.45" stop-color="#3d4248"/><stop offset="1" stop-color="#121417"/></linearGradient>
<linearGradient id="leather" x1="0" y1="0" x2="0" y2="1">
 <stop offset="0" stop-color="#4a3a30"/><stop offset="0.25" stop-color="#2a201b"/><stop offset="1" stop-color="#0d0a08"/></linearGradient>
<linearGradient id="seatblk" x1="0" y1="0" x2="0" y2="1">
 <stop offset="0" stop-color="#4d5157"/><stop offset="0.3" stop-color="#202226"/><stop offset="1" stop-color="#070708"/></linearGradient>
<radialGradient id="lamp" cx="0.42" cy="0.4" r="0.62">
 <stop offset="0" stop-color="#ffffff"/><stop offset="0.35" stop-color="#fff6d0"/><stop offset="0.8" stop-color="#c9c09a"/>
 <stop offset="1" stop-color="#8d876c"/></radialGradient>
<radialGradient id="taillamp" cx="0.4" cy="0.35" r="0.7">
 <stop offset="0" stop-color="#ff9a8a"/><stop offset="0.5" stop-color="#d0160e"/><stop offset="1" stop-color="#5a0402"/></radialGradient>
<radialGradient id="shadow" cx="0.5" cy="0.5" r="0.5">
 <stop offset="0" stop-color="#000000" stop-opacity="0.55"/><stop offset="0.6" stop-color="#000000" stop-opacity="0.28"/>
 <stop offset="1" stop-color="#000000" stop-opacity="0"/></radialGradient>
<linearGradient id="flame" x1="1" y1="0" x2="0" y2="0">
 <stop offset="0" stop-color="#fff3a0"/><stop offset="0.25" stop-color="#ffd23a"/><stop offset="0.6" stop-color="#ff7a12"/>
 <stop offset="1" stop-color="#c8180c"/></linearGradient>
<linearGradient id="heat" x1="0" y1="0" x2="1" y2="0">
 <stop offset="0" stop-color="#c9a24a"/><stop offset="0.25" stop-color="#6a5aa8"/><stop offset="0.5" stop-color="#3b6fb0"/>
 <stop offset="0.75" stop-color="#d7dde3"/><stop offset="1" stop-color="#f4f7fa"/></linearGradient>
<linearGradient id="spring" x1="0" y1="0" x2="1" y2="0">
 <stop offset="0" stop-color="#7e8892"/><stop offset="0.5" stop-color="#ffffff"/><stop offset="1" stop-color="#6b7279"/></linearGradient>
<radialGradient id="tire" cx="0.5" cy="0.5" r="0.5">
 <stop offset="0.78" stop-color="#0b0b0c"/><stop offset="0.86" stop-color="#2a2b2e"/><stop offset="0.93" stop-color="#151517"/>
 <stop offset="1" stop-color="#050505"/></radialGradient>
<radialGradient id="disc" cx="0.45" cy="0.4" r="0.6">
 <stop offset="0" stop-color="#e6e9ec"/><stop offset="0.7" stop-color="#9aa1a8"/><stop offset="1" stop-color="#6c737a"/></radialGradient>
<linearGradient id="rubber" x1="0" y1="0" x2="0" y2="1">
 <stop offset="0" stop-color="#3b3d40"/><stop offset="1" stop-color="#0b0b0c"/></linearGradient>
"""


def _defs(extra=""):
    return "<defs>" + BASE_DEFS + extra + "</defs>"


def _shade(hexcol, f):
    h = hexcol.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    if f >= 0:
        r, g, b = (int(c + (255 - c) * f) for c in (r, g, b))
    else:
        r, g, b = (int(c * (1 + f)) for c in (r, g, b))
    return f"#{r:02x}{g:02x}{b:02x}"


def _paint_defs(col):
    """a fényezés színátmenetei (a szín világos / sötét árnyalataiból)"""
    light = 0.55 if _lum(col) < 0.5 else 0.35
    return (f'<linearGradient id="paint" x1="0" y1="0" x2="0" y2="1">'
            f'<stop offset="0" stop-color="{_shade(col, light)}"/><stop offset="0.22" stop-color="{_shade(col, 0.12)}"/>'
            f'<stop offset="0.55" stop-color="{col}"/><stop offset="0.85" stop-color="{_shade(col, -0.45)}"/>'
            f'<stop offset="1" stop-color="{_shade(col, -0.65)}"/></linearGradient>'
            f'<linearGradient id="paintf" x1="0" y1="0" x2="1" y2="1">'
            f'<stop offset="0" stop-color="{_shade(col, light * 0.8)}"/><stop offset="0.4" stop-color="{col}"/>'
            f'<stop offset="1" stop-color="{_shade(col, -0.6)}"/></linearGradient>'
            f'<radialGradient id="paintr" cx="0.4" cy="0.3" r="0.8">'
            f'<stop offset="0" stop-color="{_shade(col, light)}"/><stop offset="0.5" stop-color="{col}"/>'
            f'<stop offset="1" stop-color="{_shade(col, -0.6)}"/></radialGradient>')


def _lum(col):
    h = col.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    return 0.3 * r + 0.59 * g + 0.11 * b


def _f(v):
    return f"{v:.1f}"


# --- geometria ------------------------------------------------------------------------------------------------------

def geometry(bike):
    m = MODELS[bike["model"]]
    t = m["type"]
    tire = PARTS[bike["parts"]["tire"]["id"]]
    rr = 66 + (tire["w"] - 130) * 0.045
    fr = 76 if t == "chopper" else 64 if t == "cafe" else 68
    rx = 140
    fx = rx + m["wheelbase"] * 228
    return {"t": t, "rx": rx, "ry": GROUND - rr, "rr": rr, "fx": fx, "fy": GROUND - fr, "fr": fr}


# --- elemek ---------------------------------------------------------------------------------------------------------

def _tube(o, d, w, col="#111316", hi="#4a5058"):
    """csővázelem: sötét cső + fénycsík (térhatás)"""
    o.append(f'<path d="{d}" stroke="{col}" stroke-width="{_f(w)}" fill="none" stroke-linecap="round" stroke-linejoin="round"/>')
    o.append(f'<path d="{d}" stroke="{hi}" stroke-width="{_f(max(1.2, w * 0.28))}" fill="none" stroke-linecap="round" '
             f'stroke-linejoin="round" transform="translate(0,{_f(-w * 0.22)})" opacity="0.9"/>')


def _chrome_tube(o, d, w):
    o.append(f'<path d="{d}" stroke="#2c3238" stroke-width="{_f(w + 1.6)}" fill="none" stroke-linecap="round" stroke-linejoin="round"/>')
    o.append(f'<path d="{d}" stroke="url(#chrome)" stroke-width="{_f(w)}" fill="none" stroke-linecap="round" stroke-linejoin="round"/>')
    o.append(f'<path d="{d}" stroke="#ffffff" stroke-width="{_f(max(0.8, w * 0.2))}" fill="none" stroke-linecap="round" '
             f'stroke-linejoin="round" opacity="0.75" transform="translate(0,{_f(-w * 0.22)})"/>')


def _spring(o, x1, y1, x2, y2, coils=9, r=6):
    """rugóstag: rugó + tag"""
    dx, dy = x2 - x1, y2 - y1
    ln = math.hypot(dx, dy)
    ux, uy = dx / ln, dy / ln
    nx, ny = -uy, ux
    o.append(f'<line x1="{_f(x1)}" y1="{_f(y1)}" x2="{_f(x2)}" y2="{_f(y2)}" stroke="#2a2e33" stroke-width="{_f(r * 1.1)}" stroke-linecap="round"/>')
    pts = []
    n = coils * 2
    for i in range(n + 1):
        t = 0.12 + 0.76 * i / n
        side = r if i % 2 else -r
        pts.append(f"{_f(x1 + dx * t + nx * side)},{_f(y1 + dy * t + ny * side)}")
    o.append(f'<polyline points="{" ".join(pts)}" fill="none" stroke="url(#spring)" stroke-width="2.4" stroke-linejoin="round"/>')
    for t in (0.04, 0.96):
        cx, cy = x1 + dx * t, y1 + dy * t
        o.append(f'<circle cx="{_f(cx)}" cy="{_f(cy)}" r="{_f(r * 0.75)}" fill="url(#chromer)" stroke="#3a4046" stroke-width="0.8"/>')


def _bolt(o, x, y, r=2.2):
    o.append(f'<circle cx="{_f(x)}" cy="{_f(y)}" r="{_f(r)}" fill="url(#chromer)" stroke="#2c3136" stroke-width="0.5"/>')


def _fender(o, cx, cy, r_out, r_in, a0, a1, col):
    """szoknyás sárvédő: körgyűrű-cikk a kerék felső részén (szög: fok, 0 = jobbra, növekvő az óramutató szerint)"""
    def pt(r, a):
        return f"{_f(cx + r * math.cos(math.radians(a)))},{_f(cy + r * math.sin(math.radians(a)))}"
    large = 1 if (a1 - a0) > 180 else 0
    o.append(f'<path d="M{pt(r_out, a0)} A{_f(r_out)},{_f(r_out)} 0 {large} 1 {pt(r_out, a1)} L{pt(r_in, a1)} '
             f'A{_f(r_in)},{_f(r_in)} 0 {large} 0 {pt(r_in, a0)} Z" fill="url(#paintr)" stroke="{_shade(col, -0.65)}" stroke-width="1.2"/>')
    o.append(f'<path d="M{pt(r_out - 4, a0 + 14)} A{_f(r_out - 4)},{_f(r_out - 4)} 0 0 1 {pt(r_out - 4, (a0 + a1) / 2 + 10)}" '
             f'stroke="#ffffff" stroke-width="2.6" fill="none" opacity="0.5" stroke-linecap="round"/>')
    o.append(f'<path d="M{pt(r_in + 2, a0 + 4)} A{_f(r_in + 2)},{_f(r_in + 2)} 0 {large} 1 {pt(r_in + 2, a1 - 4)}" '
             f'stroke="{_shade(col, -0.7)}" stroke-width="2" fill="none"/>')


# --- motorblokk: V2 -------------------------------------------------------------------------------------------------

def _cylinder(o, ang, s, black=False):
    """egy henger (bordázott) + hengerfej + szelepfedél, a forgattyúház közepéről elforgatva"""
    s = s * CYL
    fin = "url(#finb)" if black else "url(#fin)"
    gap = "#0a0b0c" if black else "#454b52"
    o.append(f'<g transform="rotate({ang})">')
    # henger palást
    o.append(f'<rect x="{_f(-15 * s)}" y="{_f(-76 * s)}" width="{_f(30 * s)}" height="{_f(56 * s)}" fill="#2a2e33"/>')
    for k in range(9):                                   # bordák: lefelé keskenyebbek
        y = -74 * s + k * 5.4 * s
        hw = (25 - k * 0.55) * s
        o.append(f'<rect x="{_f(-hw)}" y="{_f(y)}" width="{_f(2 * hw)}" height="{_f(3.2 * s)}" rx="{_f(1.4 * s)}" fill="{fin}" '
                 f'stroke="{gap}" stroke-width="0.5"/>')
    # hengerfej (nagyobb bordák)
    o.append(f'<path d="M{_f(-27 * s)},{_f(-76 * s)} L{_f(-24 * s)},{_f(-100 * s)} L{_f(24 * s)},{_f(-100 * s)} L{_f(27 * s)},{_f(-76 * s)} Z" '
             f'fill="#33383e"/>')
    for k in range(5):
        y = -99 * s + k * 4.8 * s
        hw = (25 + k * 0.6) * s
        o.append(f'<rect x="{_f(-hw)}" y="{_f(y)}" width="{_f(2 * hw)}" height="{_f(3.1 * s)}" rx="{_f(1.2 * s)}" fill="{fin}" '
                 f'stroke="{gap}" stroke-width="0.5"/>')
    # szelepfedél (króm, lekerekített) + gyertya
    o.append(f'<path d="M{_f(-24 * s)},{_f(-101 * s)} Q{_f(-24 * s)},{_f(-118 * s)} {_f(-8 * s)},{_f(-120 * s)} L{_f(8 * s)},{_f(-120 * s)} '
             f'Q{_f(24 * s)},{_f(-118 * s)} {_f(24 * s)},{_f(-101 * s)} Z" fill="url(#chrome)" stroke="#3a4046" stroke-width="1"/>')
    o.append(f'<line x1="{_f(-20 * s)}" y1="{_f(-104 * s)}" x2="{_f(20 * s)}" y2="{_f(-104 * s)}" stroke="#5d6670" stroke-width="1"/>')
    for bx in (-15, 0, 15):
        _bolt(o, bx * s, -110 * s, 1.6 * s)
    o.append(f'<rect x="{_f(18 * s)}" y="{_f(-94 * s)}" width="{_f(9 * s)}" height="{_f(5 * s)}" rx="1.5" fill="#e9e4d8" stroke="#555"/>')
    o.append(f'<path d="M{_f(27 * s)},{_f(-92 * s)} Q{_f(36 * s)},{_f(-92 * s)} {_f(38 * s)},{_f(-80 * s)}" stroke="#111" '
             f'stroke-width="{_f(2.2 * s)}" fill="none"/>')
    o.append("</g>")


def _vtwin(o, ex, ey, cc, carb, blower, intake, t):
    s = (cc / 1200) ** 0.33
    black = t == "bobber"                              # a bobber feketére festett blokkal
    # forgattyúház
    o.append(f'<path d="M{_f(ex - 40 * s)},{_f(ey - 8 * s)} Q{_f(ex - 50 * s)},{_f(ey + 30 * s)} {_f(ex - 20 * s)},{_f(ey + 46 * s)} '
             f'L{_f(ex + 26 * s)},{_f(ey + 46 * s)} Q{_f(ex + 52 * s)},{_f(ey + 30 * s)} {_f(ex + 42 * s)},{_f(ey - 8 * s)} '
             f'Q{_f(ex)},{_f(ey - 22 * s)} {_f(ex - 40 * s)},{_f(ey - 8 * s)} Z" fill="url(#alu)" stroke="#30353a" stroke-width="1.4"/>')
    # váltóház (a blokk mögött)
    o.append(f'<path d="M{_f(ex - 46 * s)},{_f(ey + 2 * s)} L{_f(ex - 96 * s)},{_f(ey + 4 * s)} Q{_f(ex - 104 * s)},{_f(ey + 22 * s)} '
             f'{_f(ex - 92 * s)},{_f(ey + 40 * s)} L{_f(ex - 40 * s)},{_f(ey + 44 * s)} Z" fill="url(#alu)" stroke="#30353a" stroke-width="1.2"/>')
    o.append(f'<line x1="{_f(ex - 90 * s)}" y1="{_f(ey + 16 * s)}" x2="{_f(ex - 50 * s)}" y2="{_f(ey + 18 * s)}" stroke="#7d858d" stroke-width="1"/>')
    # hengerek: hátsó, majd első
    o.append(f'<g transform="translate({_f(ex)},{_f(ey)})">')
    _cylinder(o, -22.5, s, black)
    _cylinder(o, 22.5, s, black)
    o.append("</g>")
    # tolórudak (a vezérműfedéltől a hengerfejekig)
    cx, cy = ex + 16 * s, ey + 26 * s
    for ang in (-22.5, 22.5):
        a = math.radians(ang)
        hx = ex + math.sin(a) * 76 * CYL * s + 6 * s
        hy = ey - math.cos(a) * 76 * CYL * s
        _chrome_tube(o, f"M{_f(cx)},{_f(cy)} L{_f(hx)},{_f(hy)}", 2.4 * s)
    # vezérműfedél (króm könnycsepp)
    o.append(f'<path d="M{_f(ex + 2 * s)},{_f(ey + 18 * s)} Q{_f(ex + 6 * s)},{_f(ey + 2 * s)} {_f(ex + 26 * s)},{_f(ey + 8 * s)} '
             f'Q{_f(ex + 40 * s)},{_f(ey + 18 * s)} {_f(ex + 30 * s)},{_f(ey + 36 * s)} Q{_f(ex + 10 * s)},{_f(ey + 42 * s)} '
             f'{_f(ex + 2 * s)},{_f(ey + 18 * s)} Z" fill="url(#chrome)" stroke="#3a4046" stroke-width="1"/>')
    for (bx, by) in ((8, 14), (26, 12), (30, 30), (12, 34)):
        _bolt(o, ex + bx * s, ey + by * s, 1.7 * s)
    # karburátor + levegőszűrő (a jobb oldalon, a hengerek között)
    ax, ay = ex + 4 * s, ey - 40 * s
    o.append(f'<rect x="{_f(ax - 9 * s)}" y="{_f(ay - 6 * s)}" width="{_f(18 * s)}" height="{_f(16 * s)}" rx="3" fill="url(#alu)" stroke="#333"/>')
    if carb == "carb_dual":
        for dy in (-26, 4):
            o.append(f'<ellipse cx="{_f(ax + 14 * s)}" cy="{_f(ay + dy * s)}" rx="{_f(9 * s)}" ry="{_f(13 * s)}" fill="url(#chromeh)" stroke="#3a4046"/>')
    if intake == "in_open":                             # nyitott kúpszűrő (piros, hálós)
        o.append(f'<path d="M{_f(ax + 6 * s)},{_f(ay - 10 * s)} L{_f(ax + 36 * s)},{_f(ay - 20 * s)} Q{_f(ax + 42 * s)},{_f(ay)} '
                 f'{_f(ax + 36 * s)},{_f(ay + 20 * s)} L{_f(ax + 6 * s)},{_f(ay + 12 * s)} Z" fill="#9c1410" stroke="#3a0402" stroke-width="1"/>')
        for k in range(6):
            x = ax + (9 + k * 4.6) * s
            hh = (11 + k * 1.6) * s
            o.append(f'<line x1="{_f(x)}" y1="{_f(ay - hh)}" x2="{_f(x)}" y2="{_f(ay + hh)}" stroke="#3a0402" stroke-width="0.9"/>')
        o.append(f'<ellipse cx="{_f(ax + 38 * s)}" cy="{_f(ay)}" rx="{_f(5 * s)}" ry="{_f(20 * s)}" fill="url(#chromeh)" stroke="#3a4046"/>')
    else:
        big = 24 if intake == "in_big" else 18
        rx_ = big * s * (1.0 if intake == "in_big" else 1.15)
        ry_ = big * s
        o.append(f'<ellipse cx="{_f(ax + 10 * s)}" cy="{_f(ay)}" rx="{_f(rx_)}" ry="{_f(ry_)}" fill="url(#chromer)" stroke="#3a4046" stroke-width="1.4"/>')
        o.append(f'<ellipse cx="{_f(ax + 10 * s)}" cy="{_f(ay)}" rx="{_f(rx_ * 0.72)}" ry="{_f(ry_ * 0.72)}" fill="none" stroke="#8a939c" stroke-width="1.2"/>')
        if intake == "in_big":
            for k in range(8):
                a = k * math.pi / 4
                o.append(f'<line x1="{_f(ax + 10 * s + math.cos(a) * rx_ * 0.3)}" y1="{_f(ay + math.sin(a) * ry_ * 0.3)}" '
                         f'x2="{_f(ax + 10 * s + math.cos(a) * rx_ * 0.66)}" y2="{_f(ay + math.sin(a) * ry_ * 0.66)}" stroke="#6d7680" stroke-width="1.6"/>')
        _bolt(o, ax + 10 * s, ay, 3 * s)
    # feltöltő
    if blower == "bl_comp":                               # kompresszor a hengerek fölött, szíjjal, beömlő-kanállal
        bx, by = ex, ey - 110 * s
        o.append(f'<rect x="{_f(bx - 30 * s)}" y="{_f(by - 16 * s)}" width="{_f(60 * s)}" height="{_f(34 * s)}" rx="{_f(6 * s)}" '
                 f'fill="url(#chrome)" stroke="#30363c" stroke-width="1.2"/>')
        for k in range(7):
            x = bx - 25 * s + k * 8.3 * s
            o.append(f'<line x1="{_f(x)}" y1="{_f(by - 12 * s)}" x2="{_f(x)}" y2="{_f(by + 14 * s)}" stroke="#7e8892" stroke-width="1.4"/>')
        o.append(f'<path d="M{_f(bx - 18 * s)},{_f(by - 16 * s)} L{_f(bx - 14 * s)},{_f(by - 40 * s)} L{_f(bx + 22 * s)},{_f(by - 40 * s)} '
                 f'L{_f(bx + 30 * s)},{_f(by - 16 * s)} Z" fill="url(#gloss)" stroke="#000"/>')
        o.append(f'<rect x="{_f(bx - 12 * s)}" y="{_f(by - 38 * s)}" width="{_f(30 * s)}" height="{_f(5 * s)}" fill="#c9a24a"/>')
        o.append(f'<path d="M{_f(bx + 30 * s)},{_f(by)} Q{_f(ex + 60 * s)},{_f(ey - 40 * s)} {_f(ex + 32 * s)},{_f(ey + 20 * s)}" '
                 f'stroke="#111" stroke-width="{_f(5 * s)}" fill="none"/>')
    elif blower == "bl_turbo":                            # turbó elöl lent, csigaházzal, csővel a szívóhoz
        tx, ty = ex + 64 * s, ey + 30 * s
        _chrome_tube(o, f"M{_f(tx)},{_f(ty - 12 * s)} Q{_f(tx + 6 * s)},{_f(ay - 6 * s)} {_f(ax + 30 * s)},{_f(ay + 4 * s)}", 6 * s)
        o.append(f'<circle cx="{_f(tx)}" cy="{_f(ty)}" r="{_f(17 * s)}" fill="url(#chromer)" stroke="#30363c" stroke-width="1.2"/>')
        o.append(f'<path d="M{_f(tx)},{_f(ty)} m{_f(-11 * s)},0 a{_f(11 * s)},{_f(11 * s)} 0 1 1 {_f(11 * s)},{_f(11 * s)}" '
                 f'stroke="#5d6670" stroke-width="2" fill="none"/>')
        o.append(f'<circle cx="{_f(tx)}" cy="{_f(ty)}" r="{_f(5 * s)}" fill="url(#heat)"/>')
    return s


# --- motorblokk: V8 -------------------------------------------------------------------------------------------------

def _v8(o, ex, ey, blower, carb):
    # blokk
    o.append(f'<path d="M{_f(ex - 76)},{_f(ey - 30)} L{_f(ex + 76)},{_f(ey - 30)} L{_f(ex + 70)},{_f(ey + 40)} Q{_f(ex)},{_f(ey + 52)} '
             f'{_f(ex - 70)},{_f(ey + 40)} Z" fill="url(#alu)" stroke="#2f3439" stroke-width="1.5"/>')
    o.append(f'<rect x="{_f(ex - 70)}" y="{_f(ey + 30)}" width="140" height="16" rx="5" fill="url(#gloss)"/>')     # olajteknő
    # hengerfejek és szelepfedelek (két sor, a közelebbi takarja a távolabbit)
    o.append(f'<path d="M{_f(ex - 80)},{_f(ey - 30)} L{_f(ex - 66)},{_f(ey - 62)} L{_f(ex + 66)},{_f(ey - 62)} L{_f(ex + 80)},{_f(ey - 30)} Z" '
             f'fill="#3a3f45" stroke="#1d2024"/>')
    o.append(f'<rect x="{_f(ex - 72)}" y="{_f(ey - 78)}" width="144" height="20" rx="7" fill="url(#chrome)" stroke="#30363c"/>')
    for k in range(10):
        x = ex - 62 + k * 13.6
        o.append(f'<line x1="{_f(x)}" y1="{_f(ey - 75)}" x2="{_f(x)}" y2="{_f(ey - 61)}" stroke="#7e8892" stroke-width="1.6"/>')
    for k in range(4):                                 # gyújtókábelek
        o.append(f'<path d="M{_f(ex - 54 + k * 36)},{_f(ey - 38)} Q{_f(ex - 46 + k * 36)},{_f(ey - 22)} {_f(ex - 30 + k * 30)},{_f(ey - 20)}" '
                 f'stroke="#b01818" stroke-width="2.2" fill="none"/>')
    # elöl: vízpumpa, generátor, szíj
    o.append(f'<circle cx="{_f(ex + 86)}" cy="{_f(ey + 6)}" r="16" fill="url(#chromer)" stroke="#333"/>')
    o.append(f'<circle cx="{_f(ex + 92)}" cy="{_f(ey - 34)}" r="11" fill="url(#chromer)" stroke="#333"/>')
    o.append(f'<path d="M{_f(ex + 86)},{_f(ey - 10)} L{_f(ex + 92)},{_f(ey - 45)} M{_f(ex + 102)},{_f(ey + 6)} L{_f(ex + 103)},{_f(ey - 34)}" '
             f'stroke="#111" stroke-width="3"/>')
    if blower != "bl_none":                            # GMC-stílusú feltöltő, szíjjal, „kalap” beömlővel
        o.append(f'<rect x="{_f(ex - 46)}" y="{_f(ey - 128)}" width="92" height="50" rx="6" fill="url(#chrome)" stroke="#30363c" stroke-width="1.2"/>')
        for k in range(8):
            o.append(f'<line x1="{_f(ex - 40 + k * 11.5)}" y1="{_f(ey - 124)}" x2="{_f(ex - 40 + k * 11.5)}" y2="{_f(ey - 82)}" stroke="#7e8892" stroke-width="1.6"/>')
        o.append(f'<path d="M{_f(ex - 32)},{_f(ey - 128)} L{_f(ex - 26)},{_f(ey - 166)} L{_f(ex + 32)},{_f(ey - 166)} L{_f(ex + 40)},{_f(ey - 128)} Z" '
                 f'fill="url(#gloss)" stroke="#000"/>')
        o.append(f'<rect x="{_f(ex - 28)}" y="{_f(ey - 164)}" width="58" height="7" fill="#c9a24a"/>')
        o.append(f'<path d="M{_f(ex + 46)},{_f(ey - 104)} L{_f(ex + 92)},{_f(ey - 30)}" stroke="#111" stroke-width="5"/>')
    else:
        rx_ = 46 if carb == "carb_dual" else 36
        o.append(f'<rect x="{_f(ex - 10)}" y="{_f(ey - 96)}" width="20" height="18" fill="url(#alu)" stroke="#333"/>')
        o.append(f'<ellipse cx="{_f(ex)}" cy="{_f(ey - 98)}" rx="{rx_}" ry="12" fill="url(#chrome)" stroke="#30363c" stroke-width="1.2"/>')
        o.append(f'<ellipse cx="{_f(ex)}" cy="{_f(ey - 101)}" rx="{rx_ * 0.6}" ry="5" fill="none" stroke="#8a939c"/>')


# --- kipufogó (a kerekek előtti réteg) ------------------------------------------------------------------------------

def _exhaust(o, style, ex, ey, rx, ry, s, v8, t):
    if v8:                                             # V8: leömlők mindkét hengersorból, két hosszú cső
        heads = [(ex - 52 + k * 34, ey + 10) for k in range(4)]
        for i, (x, y) in enumerate(heads):
            _chrome_tube(o, f"M{_f(x)},{_f(y)} Q{_f(x - 4)},{_f(ey + 52)} {_f(ex - 70)},{_f(ey + 58 + i % 2 * 4)}", 6)
        y0 = ey + 60
    else:
        front = (ex + 46 * s, ey - 58 * s)
        rear = (ex - 46 * s, ey - 58 * s)
        y0 = ey + 58 * s
    if style == "drag":
        if v8:
            for i in range(2):
                _chrome_tube(o, f"M{_f(ex - 70)},{_f(y0 + i * 6)} L{_f(rx - 62 - i * 10)},{_f(ry - 2 - i * 12)}", 11)
        else:
            # egyenes, felfelé hajló csövek; a fejeknél hőfuttatott (kékes-arany)
            d1 = (f"M{_f(front[0])},{_f(front[1])} C{_f(ex + 74 * s)},{_f(ey - 40 * s)} {_f(ex + 50 * s)},{_f(ey + 44 * s)} "
                  f"{_f(ex - 20 * s)},{_f(ey + 46 * s)} L{_f(rx - 58)},{_f(ry - 24)}")
            d2 = (f"M{_f(rear[0])},{_f(rear[1])} C{_f(ex - 72 * s)},{_f(ey - 40 * s)} {_f(ex - 76 * s)},{_f(ey + 10 * s)} "
                  f"{_f(ex - 92 * s)},{_f(ey + 22 * s)} L{_f(rx - 52)},{_f(ry - 40)}")
            for d in (d2, d1):
                o.append(f'<path d="{d}" stroke="#2c3238" stroke-width="11.6" fill="none" stroke-linecap="round" stroke-linejoin="round"/>')
                o.append(f'<path d="{d}" stroke="url(#heat)" stroke-width="10" fill="none" stroke-linecap="round" stroke-linejoin="round"/>')
                o.append(f'<path d="{d}" stroke="#ffffff" stroke-width="2" fill="none" opacity="0.6" transform="translate(0,-2.5)"/>')
            for (x, y) in ((rx - 58, ry - 24), (rx - 52, ry - 40)):
                o.append(f'<ellipse cx="{_f(x)}" cy="{_f(y)}" rx="3" ry="5.5" fill="#111" transform="rotate(-18 {_f(x)} {_f(y)})"/>')
        return
    if not v8:
        # leömlők: az első lefelé, a blokk elé, a hátsó hátra
        _chrome_tube(o, f"M{_f(front[0])},{_f(front[1])} C{_f(ex + 74 * s)},{_f(ey - 48 * s)} {_f(ex + 66 * s)},{_f(ey + 14 * s)} "
                        f"{_f(ex + 36 * s)},{_f(y0 - 4 * s)} L{_f(ex - 60 * s)},{_f(y0)}", 7.5 * s)
        _chrome_tube(o, f"M{_f(rear[0])},{_f(rear[1])} C{_f(ex - 74 * s)},{_f(ey - 46 * s)} {_f(ex - 70 * s)},{_f(ey - 4 * s)} "
                        f"{_f(ex - 64 * s)},{_f(y0 - 14 * s)}", 7.5 * s)
        # hővédő lemez az első csövön
        o.append(f'<path d="M{_f(ex + 64 * s)},{_f(ey - 30 * s)} Q{_f(ex + 68 * s)},{_f(ey + 4 * s)} {_f(ex + 48 * s)},{_f(ey + 34 * s)}" '
                 f'stroke="#2c3238" stroke-width="{_f(13 * s)}" fill="none" stroke-linecap="round"/>')
        o.append(f'<path d="M{_f(ex + 64 * s)},{_f(ey - 30 * s)} Q{_f(ex + 68 * s)},{_f(ey + 4 * s)} {_f(ex + 48 * s)},{_f(ey + 34 * s)}" '
                 f'stroke="url(#chromeh)" stroke-width="{_f(11 * s)}" fill="none" stroke-linecap="round"/>')
        for k in range(3):
            o.append(f'<circle cx="{_f(ex + 66 * s - k * 4 * s)}" cy="{_f(ey - 20 * s + k * 18 * s)}" r="1.4" fill="#444"/>')
    if style == "21":                                  # 2-1: a csövek egyesülnek, felfelé álló megafon
        _chrome_tube(o, f"M{_f(ex - 60 * s)},{_f(y0)} L{_f(ex - 90 * s)},{_f(y0 - 2)}", 9)
        _chrome_tube(o, f"M{_f(ex - 60 * s)},{_f(y0 - 14 * s)} Q{_f(ex - 80 * s)},{_f(y0 - 10)} {_f(ex - 90 * s)},{_f(y0 - 2)}", 8)
        mx0, my0, mx1, my1 = ex - 90 * s, y0 - 2, rx - 40, ry - 20
        ang = math.degrees(math.atan2(my1 - my0, mx1 - mx0))
        ln = math.hypot(mx1 - mx0, my1 - my0)
        o.append(f'<g transform="translate({_f(mx0)},{_f(my0)}) rotate({_f(ang)})">')
        o.append(f'<path d="M0,-6 L{_f(ln * 0.35)},-7 L{_f(ln)},-15 L{_f(ln)},15 L{_f(ln * 0.35)},7 L0,6 Z" fill="url(#chrome)" stroke="#30363c" stroke-width="1.2"/>')
        o.append(f'<ellipse cx="{_f(ln)}" cy="0" rx="3.5" ry="15" fill="#2a2e33" stroke="#9aa3ad" stroke-width="1.5"/>')
        o.append(f'<line x1="{_f(ln * 0.38)}" y1="-6" x2="{_f(ln * 0.98)}" y2="-13" stroke="#ffffff" stroke-width="2" opacity="0.7"/>')
        o.append("</g>")
        return
    # gyári / ferde végű: két hangtompító-dob egymás felett (V8-nál is)
    for i, yy in enumerate((y0 - (14 * s if not v8 else 0), y0 + (0 if not v8 else 8))):
        x_in = ex - 60 * s if not v8 else ex - 70
        end = rx - 66 if style == "std" else rx - 54
        y_end = ry + 10 - i * 18 if t in ("chopper", "bobber") else yy + 4 - i * 4
        _chrome_tube(o, f"M{_f(x_in)},{_f(yy)} L{_f(rx + 46)},{_f(y_end + (yy - y_end) * 0.3)}", 8)
        ang = math.degrees(math.atan2(y_end - yy, (end + 6) - (rx + 46)))
        ln = abs(rx + 52 - end)
        o.append(f'<g transform="translate({_f(rx + 52)},{_f(y_end + (yy - y_end) * 0.3)}) rotate({_f(180 + ang)})">')
        o.append(f'<rect x="0" y="-9" width="{_f(ln)}" height="18" rx="9" fill="url(#chrome)" stroke="#30363c" stroke-width="1.2"/>')
        o.append(f'<line x1="6" y1="-5" x2="{_f(ln - 8)}" y2="-5" stroke="#ffffff" stroke-width="2.2" opacity="0.8"/>')
        o.append(f'<rect x="{_f(ln * 0.18)}" y="-9.5" width="3" height="19" fill="#7e8892"/>')
        if style == "slash":
            o.append(f'<path d="M{_f(ln - 14)},-9.5 L{_f(ln + 1)},-9.5 L{_f(ln + 1)},9.5 Z" fill="#1b1f23"/>')
            o.append(f'<line x1="{_f(ln - 14)}" y1="-9.5" x2="{_f(ln + 1)}" y2="9.5" stroke="#c9ced3" stroke-width="1.6"/>')
        else:
            o.append(f'<ellipse cx="{_f(ln - 1)}" cy="0" rx="2.5" ry="7.5" fill="#1b1f23" stroke="#9aa3ad"/>')
        o.append("</g>")


# --- kerék ----------------------------------------------------------------------------------------------------------

def _wheel(r, kind, tire_w, front, t):
    s = 2 * r + 8
    c = s / 2
    tread = 10 + tire_w * 0.045
    rim = r - tread
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{s:.0f}" height="{s:.0f}" viewBox="0 0 {s:.1f} {s:.1f}">', _defs()]
    # gumi: oldalfal-átmenet + futófelület mintázata
    o.append(f'<circle cx="{c}" cy="{c}" r="{_f(r)}" fill="url(#tire)"/>')
    o.append(f'<circle cx="{c}" cy="{c}" r="{_f(r - 1.6)}" fill="none" stroke="#1d1e20" stroke-width="3" stroke-dasharray="6 3.5"/>')
    o.append(f'<circle cx="{c}" cy="{c}" r="{_f(r - tread * 0.55)}" fill="none" stroke="#3a3c40" stroke-width="1" opacity="0.8"/>')
    if tire_w >= 240 and not front:                   # széles / slick: fehér felirat-ív helyett csík
        o.append(f'<circle cx="{c}" cy="{c}" r="{_f(r - tread * 0.45)}" fill="none" stroke="#d8d2b8" stroke-width="1.6" '
                 f'stroke-dasharray="40 30" opacity="0.8"/>')
    # felni
    o.append(f'<circle cx="{c}" cy="{c}" r="{_f(rim)}" fill="#141518"/>')
    o.append(f'<circle cx="{c}" cy="{c}" r="{_f(rim - 1.5)}" fill="none" stroke="url(#chrome)" stroke-width="5"/>')
    o.append(f'<circle cx="{c}" cy="{c}" r="{_f(rim - 4.5)}" fill="none" stroke="#5d6670" stroke-width="1"/>')
    hub = 14 if kind == "spoke" else 16
    if front:                                         # féktárcsa (furatokkal)
        dr = rim * (0.62 if kind == "spoke" else 0.66)
        o.append(f'<circle cx="{c}" cy="{c}" r="{_f(dr)}" fill="url(#disc)" stroke="#4c545c" stroke-width="1"/>')
        o.append(f'<circle cx="{c}" cy="{c}" r="{_f(dr * 0.62)}" fill="#20242a"/>')
        for k in range(12):
            a = k * math.pi / 6
            o.append(f'<circle cx="{_f(c + math.cos(a) * dr * 0.82)}" cy="{_f(c + math.sin(a) * dr * 0.82)}" r="1.8" fill="#3a4046"/>')
    else:                                             # szíjtárcsa / lánckerék
        pr = rim * 0.6
        o.append(f'<circle cx="{c}" cy="{c}" r="{_f(pr)}" fill="url(#chromer)" stroke="#3a4046" stroke-width="1"/>')
        o.append(f'<circle cx="{c}" cy="{c}" r="{_f(pr - 1.5)}" fill="none" stroke="#2a2e33" stroke-width="2.4" stroke-dasharray="2 2.4"/>')
        for k in range(5):
            a = k * 2 * math.pi / 5 + 0.3
            o.append(f'<circle cx="{_f(c + math.cos(a) * pr * 0.55)}" cy="{_f(c + math.sin(a) * pr * 0.55)}" r="{_f(pr * 0.17)}" fill="#20242a"/>')
    if kind == "spoke":
        # keresztbe fűzött küllők: két agyperem, érintő irányban
        n = 40
        for i in range(n):
            a = i * 2 * math.pi / n
            flange = 10 if i % 2 else 13
            tw = 0.62 if i % 4 < 2 else -0.62
            x1, y1 = c + flange * math.cos(a + tw), c + flange * math.sin(a + tw)
            x2, y2 = c + (rim - 4) * math.cos(a), c + (rim - 4) * math.sin(a)
            o.append(f'<line x1="{_f(x1)}" y1="{_f(y1)}" x2="{_f(x2)}" y2="{_f(y2)}" stroke="{"#e6eaee" if i % 2 else "#a9b1b9"}" stroke-width="1.05"/>')
            o.append(f'<circle cx="{_f(x2)}" cy="{_f(y2)}" r="1.1" fill="#d7dde3"/>')
    else:
        design = {"cafe": 3, "v8": 6, "cruiser": 9}.get(t, 5)
        for k in range(design):
            a = k * 2 * math.pi / design
            w0, w1 = (0.26, 0.09) if design <= 6 else (0.12, 0.05)
            if t == "v8":                              # ívelt (turbina) küllők
                pts = []
                for j in range(9):
                    f = j / 8
                    rad = hub + f * (rim - 6 - hub)
                    pts.append((a + f * 0.55 - (w0 - (w0 - w1) * f), rad))
                back = []
                for j in range(9):
                    f = 1 - j / 8
                    rad = hub + f * (rim - 6 - hub)
                    back.append((a + f * 0.55 + (w0 - (w0 - w1) * f), rad))
                d = " ".join(f"{'M' if i == 0 else 'L'}{_f(c + rr_ * math.cos(aa))},{_f(c + rr_ * math.sin(aa))}"
                             for i, (aa, rr_) in enumerate(pts + back)) + " Z"
                o.append(f'<path d="{d}" fill="url(#chromeh)" stroke="#4c545c" stroke-width="0.8"/>')
            else:
                pts = [(a - w0, hub), (a - w1, rim - 6), (a + w1, rim - 6), (a + w0, hub)]
                d = "M" + " L".join(f"{_f(c + rr_ * math.cos(aa))},{_f(c + rr_ * math.sin(aa))}" for aa, rr_ in pts) + " Z"
                o.append(f'<path d="{d}" fill="url(#chromeh)" stroke="#4c545c" stroke-width="0.8"/>')
                o.append(f'<line x1="{_f(c + (hub + 4) * math.cos(a))}" y1="{_f(c + (hub + 4) * math.sin(a))}" '
                         f'x2="{_f(c + (rim - 9) * math.cos(a))}" y2="{_f(c + (rim - 9) * math.sin(a))}" stroke="#ffffff" stroke-width="1.2" opacity="0.7"/>')
    # agy
    o.append(f'<circle cx="{c}" cy="{c}" r="{hub}" fill="url(#chromer)" stroke="#3a4046" stroke-width="1"/>')
    for k in range(6):
        a = k * math.pi / 3
        _bolt(o, c + math.cos(a) * hub * 0.62, c + math.sin(a) * hub * 0.62, 1.5)
    o.append(f'<circle cx="{c}" cy="{c}" r="4.5" fill="#2a2e33" stroke="#9aa3ad"/>')
    # csillanás a felnin (forgás közben is látszik a forgás)
    o.append(f'<path d="M{_f(c - rim * 0.75)},{_f(c - rim * 0.5)} A{_f(rim - 1.5)},{_f(rim - 1.5)} 0 0 1 {_f(c - rim * 0.2)},{_f(c - rim * 0.97)}" '
             f'stroke="#ffffff" stroke-width="2.4" fill="none" opacity="0.85"/>')
    o.append("</svg>")
    return "".join(o)


# --- a teljes motor -------------------------------------------------------------------------------------------------

def render_svgs(bike):
    g = geometry(bike)
    t = g["t"]
    p = {s: bike["parts"][s]["id"] for s in bike["parts"]}
    eng = PARTS[p["engine"]]
    v8 = eng["cyl"] == 8
    col = bike.get("color", "#b01818")
    rx, ry, rr, fx, fy, fr = g["rx"], g["ry"], g["rr"], g["fx"], g["fy"], g["fr"]
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">', _defs(_paint_defs(col))]
    ov = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">', _defs(_paint_defs(col))]
    fend = []                                        # sárvédők: a kerekek elé (a kerék tetejét takarják)
    ex = rx + (fx - rx) * (0.5 if not v8 else 0.52)
    ey = GROUND - (92 if not v8 else 104)
    seat_x = rx + (78 if t != "cafe" else 92)
    seat_y = GROUND - {"chopper": 150, "bobber": 148, "cafe": 172, "v8": 178}.get(t, 160)
    neck_x = fx - {"chopper": 128, "cafe": 72, "v8": 92}.get(t, 86)
    neck_y = GROUND - {"chopper": 262, "cafe": 222, "v8": 240}.get(t, 230)
    s = (eng["cc"] / 1200) ** 0.33 if not v8 else 1.0

    # árnyék a talajon
    o.append(f'<ellipse cx="{_f((rx + fx) / 2)}" cy="{GROUND + 3}" rx="{_f((fx - rx) / 2 + rr + 30)}" ry="11" fill="url(#shadow)"/>')

    # hátsó sárvédő
    if t in ("cruiser", "v8"):
        _fender(fend, rx, ry, rr + 11, rr * 0.74, 160, 300, col)
    elif t == "bobber":
        fend.append(f'<path d="M{_f(rx - rr * 0.78)},{_f(ry - rr * 0.6)} A{_f(rr + 9)},{_f(rr + 9)} 0 0 1 {_f(rx + rr * 0.45)},{_f(ry - rr - 5)} '
                 f'L{_f(rx + rr * 0.45)},{_f(ry - rr + 3)} A{_f(rr + 1)},{_f(rr + 1)} 0 0 0 {_f(rx - rr * 0.7)},{_f(ry - rr * 0.55)} Z" fill="url(#gloss)"/>')
    elif t == "cafe":                                 # rövid farok-idom a hátsó kerék fölött
        fend.append(f'<path d="M{_f(rx - 20)},{_f(ry - rr - 2)} Q{_f(rx + 10)},{_f(ry - rr - 10)} {_f(rx + 40)},{_f(ry - rr - 4)}" '
                 f'stroke="#1a1c1f" stroke-width="5" fill="none"/>')

    # lengővilla + rugóstag
    _tube(o, f"M{_f(rx)},{_f(ry)} L{_f(ex - 64 * s)},{_f(GROUND - 70)}", 10)
    if t == "chopper":                                 # merev (hardtail) váz: rugó nélkül
        _tube(o, f"M{_f(rx)},{_f(ry)} L{_f(seat_x - 6)},{_f(seat_y + 14)}", 8)
    else:
        _spring(o, rx + 16, ry - 4, seat_x + 4, seat_y + 22, coils=8, r=6)
    # szíj a hátsó kerékhez (a motor mögül)
    o.append(f'<path d="M{_f(ex - 70 * s)},{_f(GROUND - 84)} L{_f(rx - 2)},{_f(ry - rr * 0.38)}" stroke="#16171a" stroke-width="5" stroke-linecap="round"/>')
    # váz: gerinc, ülés alatti cső, alsó bölcső, nyakcső
    _tube(o, f"M{_f(seat_x - 2)},{_f(seat_y + 14)} L{_f(neck_x)},{_f(neck_y + 24)}", 10)
    _tube(o, f"M{_f(rx + 8)},{_f(ry + 4)} L{_f(seat_x - 4)},{_f(seat_y + 16)} L{_f(ex - 46 * s)},{_f(GROUND - 52)} "
             f"L{_f(ex + 40 * s)},{_f(GROUND - 48)} L{_f(neck_x + 2)},{_f(neck_y + 34)}", 9)
    o.append(f'<path d="M{_f(neck_x - 6)},{_f(neck_y + 2)} L{_f(neck_x + 12)},{_f(neck_y - 2)} L{_f(neck_x + 18)},{_f(neck_y + 40)} '
             f'L{_f(neck_x)},{_f(neck_y + 44)} Z" fill="url(#gloss)" stroke="#000" stroke-width="0.8"/>')

    # motor
    if v8:
        _v8(o, ex, ey, p["blower"], p["carb"])
        o.append(f'<path d="M{_f(rx + 24)},{_f(ry + 6)} L{_f(ex - 74)},{_f(GROUND - 46)}" stroke="#1b1d20" stroke-width="9" stroke-linecap="round"/>')
    else:
        _vtwin(o, ex, ey, eng["cc"], p["carb"], p["blower"], p["intake"], t)
        if t in ("cruiser", "chopper"):               # primer-fedél (króm, a blokk bal oldalán, hátrafelé)
            o.append(f'<path d="M{_f(ex - 34 * s)},{_f(ey + 8 * s)} Q{_f(ex - 92 * s)},{_f(ey - 2 * s)} {_f(ex - 112 * s)},{_f(ey + 26 * s)} '
                     f'Q{_f(ex - 110 * s)},{_f(ey + 48 * s)} {_f(ex - 70 * s)},{_f(ey + 50 * s)} L{_f(ex - 20 * s)},{_f(ey + 46 * s)} Z" '
                     f'fill="url(#chrome)" stroke="#30363c" stroke-width="1.2"/>')
            o.append(f'<circle cx="{_f(ex - 86 * s)}" cy="{_f(ey + 28 * s)}" r="{_f(12 * s)}" fill="url(#chromer)" stroke="#3a4046"/>')
            for k in range(5):
                a = k * 2 * math.pi / 5
                _bolt(o, ex - 86 * s + math.cos(a) * 9 * s, ey + 28 * s + math.sin(a) * 9 * s, 1.2)

    # lábtartók / előretett vezérlés, oldaltámasz
    if t in ("cruiser", "chopper", "v8"):
        fx_ctrl = ex + 70 * s if not v8 else ex + 104
        _chrome_tube(o, f"M{_f(ex + 30 * s)},{_f(GROUND - 46)} L{_f(fx_ctrl)},{_f(GROUND - 58)}", 3.5)
        o.append(f'<rect x="{_f(fx_ctrl - 10)}" y="{_f(GROUND - 64)}" width="22" height="8" rx="4" fill="url(#rubber)"/>')
        if t == "cruiser":                            # padló
            o.append(f'<rect x="{_f(ex - 30 * s)}" y="{_f(GROUND - 44)}" width="{_f(46 * s)}" height="7" rx="3" fill="url(#rubber)"/>')
    else:
        px = seat_x + 18
        _chrome_tube(o, f"M{_f(px)},{_f(seat_y + 54)} L{_f(px + 22)},{_f(seat_y + 66)}", 3)
        o.append(f'<rect x="{_f(px + 14)}" y="{_f(seat_y + 62)}" width="18" height="7" rx="3.5" fill="url(#rubber)"/>')
    o.append(f'<path d="M{_f(ex - 30 * s)},{_f(GROUND - 46)} L{_f(ex - 58 * s)},{_f(GROUND - 4)}" stroke="#1b1d20" stroke-width="3.5" stroke-linecap="round"/>')

    _exhaust(ov, PARTS[p["exhaust"]].get("style", "std"), ex, ey, rx, ry, s, v8, t)
    # féknyergek (a tárcsa előtt)
    ov_caliper = (f'<path d="M{_f(fx - fr * 0.28)},{_f(fy - fr * 0.5)} q-14,6 -12,24 l9,0 q-2,-14 9,-20 Z" fill="url(#alu)" stroke="#2f3439" stroke-width="1"/>')

    # ülés
    if t == "cafe":                                   # púpos szóló ülés, színre festett farokidommal
        o.append(f'<path d="M{_f(seat_x - 46)},{_f(seat_y + 6)} Q{_f(seat_x - 10)},{_f(seat_y - 6)} {_f(seat_x + 44)},{_f(seat_y - 2)} '
                 f'L{_f(seat_x + 46)},{_f(seat_y + 10)} L{_f(seat_x - 48)},{_f(seat_y + 16)} Z" fill="url(#seatblk)" stroke="#000"/>')
        o.append(f'<path d="M{_f(seat_x - 40)},{_f(seat_y + 4)} Q{_f(seat_x)},{_f(seat_y - 5)} {_f(seat_x + 40)},{_f(seat_y + 1)}" '
                 f'stroke="#6b7076" stroke-width="0.8" stroke-dasharray="2.5 2" fill="none"/>')
        o.append(f'<path d="M{_f(seat_x - 74)},{_f(seat_y + 14)} Q{_f(seat_x - 74)},{_f(seat_y - 22)} {_f(seat_x - 44)},{_f(seat_y - 8)} '
                 f'L{_f(seat_x - 44)},{_f(seat_y + 16)} Z" fill="url(#paint)" stroke="{_shade(col, -0.6)}"/>')
        o.append(f'<path d="M{_f(seat_x - 68)},{_f(seat_y + 2)} Q{_f(seat_x - 66)},{_f(seat_y - 14)} {_f(seat_x - 50)},{_f(seat_y - 6)}" '
                 f'stroke="#ffffff" stroke-width="2" fill="none" opacity="0.5"/>')
        o.append(f'<circle cx="{_f(seat_x - 60)}" cy="{_f(seat_y + 4)}" r="7" fill="#f4f1e6" stroke="#222"/>')     # rajtszám-kör
    elif t == "bobber":                               # szóló nyereg rugókon
        o.append(f'<path d="M{_f(seat_x - 22)},{_f(seat_y + 2)} Q{_f(seat_x - 24)},{_f(seat_y - 16)} {_f(seat_x - 4)},{_f(seat_y - 12)} '
                 f'Q{_f(seat_x + 24)},{_f(seat_y - 8)} {_f(seat_x + 40)},{_f(seat_y - 4)} Q{_f(seat_x + 44)},{_f(seat_y + 4)} '
                 f'{_f(seat_x + 30)},{_f(seat_y + 6)} Z" fill="url(#leather)" stroke="#000"/>')
        o.append(f'<path d="M{_f(seat_x - 18)},{_f(seat_y - 6)} Q{_f(seat_x + 10)},{_f(seat_y - 10)} {_f(seat_x + 36)},{_f(seat_y - 2)}" '
                 f'stroke="#8a6a50" stroke-width="0.8" stroke-dasharray="2.5 2" fill="none"/>')
        for k in range(2):
            x = seat_x - 14 + k * 12
            _spring(o, x, seat_y + 4, x - 2, seat_y + 22, coils=3, r=3)
    else:
        back = 36 if t in ("cruiser", "v8") else 22
        o.append(f'<path d="M{_f(seat_x - back)},{_f(seat_y)} Q{_f(seat_x - back + 2)},{_f(seat_y - 28)} {_f(seat_x - back + 22)},{_f(seat_y - 14)} '
                 f'Q{_f(seat_x + 6)},{_f(seat_y - 2)} {_f(seat_x + 46)},{_f(seat_y - 6)} Q{_f(seat_x + 56)},{_f(seat_y + 6)} '
                 f'{_f(seat_x + 42)},{_f(seat_y + 12)} L{_f(seat_x - back)},{_f(seat_y + 12)} Z" fill="url(#seatblk)" stroke="#000"/>')
        o.append(f'<path d="M{_f(seat_x - back + 6)},{_f(seat_y - 4)} Q{_f(seat_x + 10)},{_f(seat_y + 2)} {_f(seat_x + 44)},{_f(seat_y - 2)}" '
                 f'stroke="#6b7076" stroke-width="0.8" stroke-dasharray="2.5 2" fill="none"/>')
        if t == "chopper":                            # magas ülés-háttámla (sissy bar)
            _chrome_tube(o, f"M{_f(rx + 6)},{_f(ry - 20)} L{_f(rx - 2)},{_f(ry - 136)} Q{_f(rx - 4)},{_f(ry - 152)} {_f(rx + 12)},{_f(ry - 150)} "
                            f"L{_f(rx + 16)},{_f(ry - 128)}", 4)

    # tank
    tx0, tx1 = seat_x + 44, neck_x + 2
    if t == "chopper":                                # kis, felfelé álló könnycsepp-tank
        cx_, cy_ = (tx0 + tx1) / 2 + 6, (seat_y + neck_y) / 2 + 2
        tank = (f"M{_f(cx_ - 46)},{_f(cy_ + 12)} Q{_f(cx_ - 50)},{_f(cy_ - 16)} {_f(cx_ - 14)},{_f(cy_ - 22)} "
                f"Q{_f(cx_ + 38)},{_f(cy_ - 28)} {_f(cx_ + 50)},{_f(cy_ - 6)} Q{_f(cx_ + 52)},{_f(cy_ + 14)} {_f(cx_ + 26)},{_f(cy_ + 16)} "
                f"Q{_f(cx_ - 10)},{_f(cy_ + 20)} {_f(cx_ - 46)},{_f(cy_ + 12)} Z")
        ty, th = cy_, 34
    else:
        ty = (seat_y + neck_y) / 2 + (-4 if t not in ("cafe",) else 2)
        th = {"cruiser": 38, "v8": 42, "bobber": 30, "cafe": 32}.get(t, 34)
        top_rise = (tx1 - tx0) * 0.07
        tank = (f"M{_f(tx0 - 4)},{_f(ty + th * 0.55)} Q{_f(tx0 - 10)},{_f(ty - th * 0.55)} {_f(tx0 + 26)},{_f(ty - th * 0.72)} "
                f"L{_f(tx1 - 22)},{_f(ty - th * 0.8 - top_rise)} Q{_f(tx1 + 8)},{_f(ty - th * 0.78 - top_rise)} {_f(tx1 + 4)},{_f(ty - th * 0.05)} "
                f"Q{_f(tx1)},{_f(ty + th * 0.5)} {_f(tx1 - 26)},{_f(ty + th * 0.55)} "
                f"Q{_f((tx0 + tx1) / 2)},{_f(ty + th * 0.75)} {_f(tx0 - 4)},{_f(ty + th * 0.55)} Z")
    o.append(f'<path d="{tank}" fill="url(#paint)" stroke="{_shade(col, -0.7)}" stroke-width="1.4"/>')
    if t == "cafe":                                   # térdmélyedés
        o.append(f'<path d="M{_f(tx0 + 4)},{_f(ty + 4)} Q{_f(tx0 + 22)},{_f(ty - 10)} {_f(tx0 + 46)},{_f(ty + 2)} Q{_f(tx0 + 30)},{_f(ty + 16)} '
                 f'{_f(tx0 + 4)},{_f(ty + 4)} Z" fill="{_shade(col, -0.35)}" opacity="0.75"/>')
    if bike.get("flames"):                            # klasszikus lángnyelvek a tank elejéről hátrafelé
        x0 = tx1 + 2
        fl = []
        for k in range(6):
            y0 = ty - th * 0.55 + k * th * 0.2
            ln = 70 + (k % 3) * 22 - abs(k - 2.5) * 6
            fl.append(f"M{_f(x0)},{_f(y0 - 3)} C{_f(x0 - ln * 0.4)},{_f(y0 - 10)} {_f(x0 - ln * 0.7)},{_f(y0 + 6)} {_f(x0 - ln)},{_f(y0 - 4)} "
                      f"C{_f(x0 - ln * 0.75)},{_f(y0 + 8)} {_f(x0 - ln * 0.35)},{_f(y0 + 8)} {_f(x0)},{_f(y0 + th * 0.12)} Z")
        o.append(f'<path d="{" ".join(fl)}" fill="url(#flame)" stroke="#8a0c06" stroke-width="0.9" stroke-linejoin="round"/>')
    # csillanás, csíkozás, embléma, tanksapka
    o.append(f'<path d="M{_f(tx0 + 14)},{_f(ty - th * 0.42)} Q{_f((tx0 + tx1) / 2)},{_f(ty - th * 0.72)} {_f(tx1 - 18)},{_f(ty - th * 0.62)} '
             f'Q{_f((tx0 + tx1) / 2)},{_f(ty - th * 0.5)} {_f(tx0 + 14)},{_f(ty - th * 0.42)} Z" fill="#ffffff" opacity="0.38"/>')
    o.append(f'<path d="M{_f(tx0 + 30)},{_f(ty - th * 0.55)} L{_f(tx1 - 34)},{_f(ty - th * 0.66)}" stroke="#ffffff" stroke-width="2.2" '
             f'stroke-linecap="round" opacity="0.8"/>')
    if t != "chopper":
        o.append(f'<path d="M{_f(tx0 + 6)},{_f(ty + th * 0.38)} Q{_f((tx0 + tx1) / 2)},{_f(ty + th * 0.56)} {_f(tx1 - 20)},{_f(ty + th * 0.4)}" '
                 f'stroke="{"#c9a24a" if _lum(col) < 0.6 else "#1a1a1a"}" stroke-width="1.3" fill="none"/>')
    bx, by = (tx0 + tx1) / 2 + 6, ty + th * 0.05
    o.append(f'<ellipse cx="{_f(bx)}" cy="{_f(by)}" rx="15" ry="8" fill="url(#chromer)" stroke="#3a4046"/>')
    o.append(f'<ellipse cx="{_f(bx)}" cy="{_f(by)}" rx="10" ry="4.5" fill="{_shade(col, -0.5)}"/>')
    o.append(f'<path d="M{_f(bx - 8)},{_f(by)} L{_f(bx + 8)},{_f(by)}" stroke="#c9a24a" stroke-width="1.4"/>')
    o.append(f'<rect x="{_f(tx0 + 20)}" y="{_f(ty - th * 0.82 - 4)}" width="12" height="6" rx="2" fill="url(#chrome)" stroke="#333"/>')

    # villa
    fork_top = (neck_x + 6, neck_y - 10)
    fw = 8 if t == "cafe" else 9
    o.append(f'<line x1="{_f(fork_top[0])}" y1="{_f(fork_top[1])}" x2="{_f(fx)}" y2="{_f(fy)}" stroke="#2c3238" stroke-width="{fw + 1.8}" stroke-linecap="round"/>')
    o.append(f'<line x1="{_f(fork_top[0])}" y1="{_f(fork_top[1])}" x2="{_f(fx)}" y2="{_f(fy)}" stroke="url(#chromeh)" stroke-width="{fw}" stroke-linecap="round"/>')
    # alsó csúszószárak (sötét)
    lx = fork_top[0] + (fx - fork_top[0]) * 0.62
    ly = fork_top[1] + (fy - fork_top[1]) * 0.62
    o.append(f'<line x1="{_f(lx)}" y1="{_f(ly)}" x2="{_f(fx)}" y2="{_f(fy)}" stroke="url(#alu)" stroke-width="{fw + 3}" stroke-linecap="round"/>')
    o.append(f'<line x1="{_f(fork_top[0] + 3)}" y1="{_f(fork_top[1] + 2)}" x2="{_f(lx + 2)}" y2="{_f(ly)}" stroke="#ffffff" stroke-width="1.6" opacity="0.8"/>')
    # villahidak
    for f_ in (0.0, 0.16):
        x = fork_top[0] + (fx - fork_top[0]) * f_
        y = fork_top[1] + (fy - fork_top[1]) * f_
        o.append(f'<rect x="{_f(x - 14)}" y="{_f(y - 4)}" width="26" height="8" rx="3" fill="url(#chrome)" stroke="#333"/>')

    # első sárvédő
    if t in ("cruiser", "v8"):                        # mély, szoknyás sárvédő
        _fender(fend, fx, fy, fr + 10, fr * 0.76, 205, 385, col)
    elif t == "cafe":
        fend.append(f'<path d="M{_f(fx - fr * 0.62)},{_f(fy - fr * 0.72)} A{_f(fr + 6)},{_f(fr + 6)} 0 0 1 {_f(fx + fr * 0.66)},{_f(fy - fr * 0.72)} '
                 f'L{_f(fx + fr * 0.6)},{_f(fy - fr * 0.64)} A{_f(fr)},{_f(fr)} 0 0 0 {_f(fx - fr * 0.56)},{_f(fy - fr * 0.64)} Z" fill="url(#chrome)"/>')
    elif t == "bobber":
        fend.append(f'<path d="M{_f(fx - fr * 0.5)},{_f(fy - fr * 0.8)} A{_f(fr + 5)},{_f(fr + 5)} 0 0 1 {_f(fx + fr * 0.6)},{_f(fy - fr * 0.78)} '
                 f'L{_f(fx + fr * 0.55)},{_f(fy - fr * 0.7)} A{_f(fr)},{_f(fr)} 0 0 0 {_f(fx - fr * 0.45)},{_f(fy - fr * 0.72)} Z" fill="url(#gloss)"/>')

    # kormány, markolatok, karok
    bars = p["bars"]
    hx, hy = fork_top
    if bars == "ape":
        d = f"M{_f(hx)},{_f(hy)} L{_f(hx - 6)},{_f(hy - 74)} Q{_f(hx - 8)},{_f(hy - 88)} {_f(hx - 24)},{_f(hy - 88)} L{_f(hx - 34)},{_f(hy - 86)}"
        grip = (hx - 34, hy - 86, hx - 50, hy - 84)
    elif bars == "beach":
        d = f"M{_f(hx)},{_f(hy)} Q{_f(hx + 6)},{_f(hy - 28)} {_f(hx - 22)},{_f(hy - 32)} L{_f(hx - 40)},{_f(hy - 28)}"
        grip = (hx - 40, hy - 28, hx - 58, hy - 24)
    elif bars == "clip":
        d = f"M{_f(hx + 2)},{_f(hy + 12)} L{_f(hx - 22)},{_f(hy + 18)}"
        grip = (hx - 22, hy + 18, hx - 40, hy + 22)
    else:
        d = f"M{_f(hx)},{_f(hy)} L{_f(hx + 2)},{_f(hy - 12)} L{_f(hx - 30)},{_f(hy - 12)}"
        grip = (hx - 30, hy - 12, hx - 48, hy - 12)
    _chrome_tube(o, d, 5)
    o.append(f'<line x1="{_f(grip[0])}" y1="{_f(grip[1])}" x2="{_f(grip[2])}" y2="{_f(grip[3])}" stroke="url(#rubber)" stroke-width="8" stroke-linecap="round"/>')
    o.append(f'<path d="M{_f(grip[0] + 4)},{_f(grip[1] - 3)} q-10,-6 -22,-2" stroke="url(#chrome)" stroke-width="2.4" fill="none"/>')
    if t in ("cruiser", "v8"):                        # tükör
        _chrome_tube(o, f"M{_f(grip[0] + 2)},{_f(grip[1] - 2)} L{_f(grip[0] - 4)},{_f(grip[1] - 34)}", 2)
        o.append(f'<ellipse cx="{_f(grip[0] - 6)}" cy="{_f(grip[1] - 40)}" rx="9" ry="6" fill="url(#chromer)" stroke="#333"/>')

    # fényszóró (+ cruisernél kiegészítő lámpák)
    lr = {"cafe": 13, "chopper": 13, "bobber": 12}.get(t, 17)
    lx_, ly_ = hx + 22, hy + 10
    o.append(f'<path d="M{_f(lx_ - lr - 4)},{_f(ly_)} A{_f(lr + 2)},{_f(lr + 2)} 0 0 1 {_f(lx_ + 2)},{_f(ly_ - lr - 2)} L{_f(lx_ + 2)},{_f(ly_ + lr + 2)} '
             f'A{_f(lr + 2)},{_f(lr + 2)} 0 0 1 {_f(lx_ - lr - 4)},{_f(ly_)} Z" fill="url(#chrome)" stroke="#30363c"/>')
    o.append(f'<ellipse cx="{_f(lx_ + 3)}" cy="{_f(ly_)}" rx="{_f(lr * 0.42)}" ry="{_f(lr + 1)}" fill="url(#lamp)" stroke="#8a939c" stroke-width="1.6"/>')
    if t in ("cruiser", "v8"):
        for dy in (24, 24):
            o.append(f'<circle cx="{_f(lx_ - 4)}" cy="{_f(ly_ + dy)}" r="8" fill="url(#chrome)" stroke="#333"/>')
            o.append(f'<ellipse cx="{_f(lx_ + 1)}" cy="{_f(ly_ + dy)}" rx="3.5" ry="7" fill="url(#lamp)"/>')
    # hátsó lámpa, rendszámtábla
    tlx, tly = rx - rr * 0.62, ry - rr * 0.74
    if t == "cafe":
        tlx, tly = seat_x - 80, seat_y + 4
    o.append(f'<rect x="{_f(tlx - 9)}" y="{_f(tly - 5)}" width="16" height="9" rx="3" fill="url(#taillamp)" stroke="#3a0402"/>')
    o.append(f'<rect x="{_f(tlx - 12)}" y="{_f(tly + 6)}" width="5" height="16" rx="1" fill="#e8e4d4" stroke="#333" stroke-width="0.8"/>')
    o.append("</svg>")
    ov.extend(fend)
    ov.append(ov_caliper)
    ov.append("</svg>")
    tire_w = PARTS[p["tire"]]["w"]
    wk = MODELS[bike["model"]]["wheel"]
    return {"body": "".join(o), "over": "".join(ov), "rear": _wheel(rr, wk, tire_w, False, t),
            "front": _wheel(fr, wk, 120, True, t)}, g


def _url(path):
    """fájlútvonal → file:// cím (Windowson: file:///C:/…)"""
    return ("file:///" + path.replace("\\", "/")) if os.name == "nt" else "file://" + path


def _store(text):
    os.makedirs(CACHE, exist_ok=True)
    h = hashlib.sha1((VERSION + text).encode()).hexdigest()[:16]
    path = os.path.join(CACHE, h + ".svg")
    if not os.path.exists(path):
        with open(path + ".tmp", "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(path + ".tmp", path)
    return _url(path)


def render(bike):
    sp = render_sprite(bike)
    if sp:
        return sp
    svgs, g = render_svgs(bike)
    return {"body": _store(svgs["body"]), "over": _store(svgs["over"]), "rear": _store(svgs["rear"]), "front": _store(svgs["front"]),
            "w": W, "h": H, "rx": g["rx"], "ry": g["ry"], "rr": g["rr"], "fx": g["fx"], "fy": g["fy"], "fr": g["fr"],
            "ground": GROUND}


# --- rajzolt motorképek (img/bikes, art-src/make_sprites.py) — 0.0.50 ---------------------------------------------
SPRITES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "img", "bikes")
_META = None


def sprite_meta():
    global _META
    if _META is None:
        try:
            import json
            with open(os.path.join(SPRITES, "meta.json"), encoding="utf-8") as f:
                _META = json.load(f)
        except (OSError, ValueError):
            _META = {}
    return _META


def _flame_mask(w, h, m):
    """lángnyelvek az első kerék fölötti magasságban, a tank elejétől hátrafelé (a fényezésre vágva)"""
    from PyQt6.QtGui import QColor, QImage, QLinearGradient, QPainter, QPainterPath
    from PyQt6.QtCore import QPointF
    img = QImage(w, h, QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(0)
    sx = w / m["w"]
    x0 = (m["fx"] - m["fr"] * 1.05) * sx               # a tank eleje kb. az első kerék hátsó széle fölött
    ytop, ybot = h * 0.18, h * 0.62
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    gr = QLinearGradient(QPointF(x0, 0), QPointF(x0 - w * 0.45, 0))
    for t, c in ((0, "#fff3a0"), (0.2, "#ffd23a"), (0.55, "#ff7a12"), (1, "#c8180c")):
        gr.setColorAt(t, QColor(c))
    path = QPainterPath()
    n = 7
    for k in range(n):
        y0 = ytop + (ybot - ytop) * k / (n - 1)
        ln = w * (0.24 + 0.1 * ((k * 5) % 3) / 2)
        path.moveTo(x0 + 10 * sx, y0 - 8 * sx)
        path.cubicTo(x0 - ln * 0.4, y0 - 22 * sx, x0 - ln * 0.7, y0 + 14 * sx, x0 - ln, y0 - 6 * sx)
        path.cubicTo(x0 - ln * 0.75, y0 + 22 * sx, x0 - ln * 0.35, y0 + 20 * sx, x0 + 10 * sx, y0 + 16 * sx)
    p.fillPath(path, gr)
    p.end()
    return img


def compose_sprite(model, color, flames):
    """a rajzolt motor a választott színnel: alap + (szín × árnyalat) + csillanás → PNG a gyorsítótárban"""
    m = sprite_meta().get(model)
    if not m:
        return None
    key = hashlib.sha1(f"S1|{model}|{color}|{bool(flames)}".encode()).hexdigest()[:16]
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, key + ".png")
    if not os.path.exists(path):
        from PyQt6.QtGui import QColor, QImage, QPainter
        base = QImage(os.path.join(SPRITES, model + "_base.png"))
        shade = QImage(os.path.join(SPRITES, model + "_shade.png")).convertToFormat(QImage.Format.Format_ARGB32_Premultiplied)
        hi = QImage(os.path.join(SPRITES, model + "_hi.png"))
        if base.isNull() or shade.isNull():
            return None
        w, h = base.width(), base.height()
        # festék: az árnyalat-kép színnel szorozva (Multiply), majd a fényezés alakjára vágva (DestinationIn)
        paint = QImage(w, h, QImage.Format.Format_ARGB32_Premultiplied)
        paint.fill(QColor(color))
        if flames:
            pp = QPainter(paint)
            pp.drawImage(0, 0, _flame_mask(w, h, m))
            pp.end()
        pp = QPainter(paint)
        pp.setCompositionMode(QPainter.CompositionMode.CompositionMode_Multiply)
        pp.drawImage(0, 0, shade)
        pp.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationIn)
        pp.drawImage(0, 0, shade)
        pp.end()
        out = QImage(w, h, QImage.Format.Format_ARGB32_Premultiplied)
        out.fill(0)
        p = QPainter(out)
        p.drawImage(0, 0, base)
        p.drawImage(0, 0, paint)
        p.drawImage(0, 0, hi)
        p.end()
        tmp = path + ".tmp.png"
        out.save(tmp, "PNG")
        os.replace(tmp, path)
    return path


def render_sprite(bike):
    m = sprite_meta().get(bike["model"])
    if not m:
        return None
    path = compose_sprite(bike["model"], bike.get("color", "#b01818"), bike.get("flames"))
    if not path:
        return None
    # a játék 680 széles koordinátarendszere; az árnyék külön (SVG), a kerekek a képen (nem forognak)
    sh = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{_f(m["h"] + 14)}" viewBox="0 0 {W} {_f(m["h"] + 14)}">'
          f'<defs>{BASE_DEFS}</defs><ellipse cx="{_f((m["rx"] + m["fx"]) / 2)}" cy="{_f(m["ground"] + 2)}" '
          f'rx="{_f((m["fx"] - m["rx"]) / 2 + m["rr"] + 20)}" ry="10" fill="url(#shadow)"/></svg>')
    return {"body": _url(path), "shadow": _store(sh), "over": "", "rear": "", "front": "",
            "w": W, "h": m["h"], "rx": m["rx"], "ry": m["ry"], "rr": m["rr"], "fx": m["fx"], "fy": m["fy"], "fr": m["fr"],
            "ground": m["ground"], "sprite": True}
