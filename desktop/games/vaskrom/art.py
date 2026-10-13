"""Vas & Króm — a motorok oldalnézeti rajza (SVG), az alkatrészekből összerakva

render(bike) → {"body": svg-út, "over": a kerekek elé kerülő réteg (kipufogó), "rear": svg-út, "front": svg-út, "w", "h", "rx", "ry", "rr", "fx", "fy", "fr"}
A kerekek külön képek (a verseny alatt forognak); a fájlok a tartalom szerinti néven a gyorsítótárba kerülnek.
Minden saját rajz: a márkák és a formák kitaláltak.
"""
import hashlib
import math
import os

from model import MODELS, PARTS

CACHE = os.environ.get("VASKROM_CACHE", os.path.join(os.path.expanduser("~"), ".cache", "vaskrom"))
W, H = 680, 380
GROUND = 330

DEFS = """<defs>
<linearGradient id="chrome" x1="0" y1="0" x2="0" y2="1">
 <stop offset="0" stop-color="#fbfbfb"/><stop offset="0.35" stop-color="#9aa3ad"/><stop offset="0.5" stop-color="#e9edf1"/>
 <stop offset="0.75" stop-color="#6d7680"/><stop offset="1" stop-color="#cfd5db"/></linearGradient>
<linearGradient id="chromeh" x1="0" y1="0" x2="1" y2="0">
 <stop offset="0" stop-color="#6d7680"/><stop offset="0.4" stop-color="#f4f6f8"/><stop offset="1" stop-color="#8a939c"/></linearGradient>
<linearGradient id="black" x1="0" y1="0" x2="0" y2="1">
 <stop offset="0" stop-color="#3a3f45"/><stop offset="1" stop-color="#0c0d0f"/></linearGradient>
<linearGradient id="engine" x1="0" y1="0" x2="0" y2="1">
 <stop offset="0" stop-color="#c9ced3"/><stop offset="0.5" stop-color="#7d858d"/><stop offset="1" stop-color="#454b52"/></linearGradient>
<radialGradient id="lamp" cx="0.4" cy="0.4" r="0.6"><stop offset="0" stop-color="#fffbe6"/><stop offset="1" stop-color="#b9b29a"/></radialGradient>
<linearGradient id="flame" x1="0" y1="0" x2="1" y2="0">
 <stop offset="0" stop-color="#ffe14a"/><stop offset="0.5" stop-color="#ff8a1c"/><stop offset="1" stop-color="#d4220f"/></linearGradient>
</defs>"""


def _shade(hexcol, f):
    h = hexcol.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    if f >= 0:
        r, g, b = (int(c + (255 - c) * f) for c in (r, g, b))
    else:
        r, g, b = (int(c * (1 + f)) for c in (r, g, b))
    return f"#{r:02x}{g:02x}{b:02x}"


def geometry(bike):
    m = MODELS[bike["model"]]
    t = m["type"]
    tire = PARTS[bike["parts"]["tire"]["id"]]
    rr = 66 + (tire["w"] - 130) * 0.045
    fr = 74 if t == "chopper" else 64 if t == "cafe" else 68
    rx = 140
    fx = rx + m["wheelbase"] * 228
    return {"t": t, "rx": rx, "ry": GROUND - rr, "rr": rr, "fx": fx, "fy": GROUND - fr, "fr": fr}


def _wheel(r, kind, tire_w, rim_col="url(#chrome)"):
    s = 2 * r + 8
    c = s / 2
    tread = 10 + tire_w * 0.045
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{s:.0f}" height="{s:.0f}" viewBox="0 0 {s:.1f} {s:.1f}">', DEFS]
    o.append(f'<circle cx="{c}" cy="{c}" r="{r - tread / 2:.1f}" fill="none" stroke="#141414" stroke-width="{tread:.1f}"/>')
    o.append(f'<circle cx="{c}" cy="{c}" r="{r - 2:.1f}" fill="none" stroke="#2c2c2c" stroke-width="2" stroke-dasharray="5 4"/>')
    rim = r - tread - 1
    o.append(f'<circle cx="{c}" cy="{c}" r="{rim:.1f}" fill="none" stroke="{rim_col}" stroke-width="5"/>')
    if kind == "spoke":
        for i in range(36):
            a = i * math.pi * 2 / 36
            a2 = a + (0.35 if i % 2 else -0.35)
            o.append(f'<line x1="{c + 9 * math.cos(a2):.1f}" y1="{c + 9 * math.sin(a2):.1f}" '
                     f'x2="{c + (rim - 2) * math.cos(a):.1f}" y2="{c + (rim - 2) * math.sin(a):.1f}" stroke="#c9ced3" stroke-width="1"/>')
    else:
        for i in range(5):
            a = i * math.pi * 2 / 5
            pts = []
            for da, rad in ((-0.18, 12), (-0.07, rim - 3), (0.07, rim - 3), (0.18, 12)):
                pts.append(f"{c + rad * math.cos(a + da):.1f},{c + rad * math.sin(a + da):.1f}")
            o.append(f'<polygon points="{" ".join(pts)}" fill="url(#chromeh)" stroke="#5c646c" stroke-width="0.8"/>')
    o.append(f'<circle cx="{c}" cy="{c}" r="13" fill="url(#chrome)" stroke="#555" stroke-width="1"/>')
    o.append(f'<circle cx="{c}" cy="{c}" r="4" fill="#333"/>')
    o.append("</svg>")
    return "".join(o)


def _vtwin(o, ex, ey, cc, carb, blower, intake):
    s = (cc / 1200) ** 0.33
    # forgattyúház
    o.append(f'<ellipse cx="{ex}" cy="{ey + 18 * s}" rx="{44 * s:.1f}" ry="{30 * s:.1f}" fill="url(#engine)" stroke="#2f3439" stroke-width="1.5"/>')
    for ang in (-22, 22):                         # hengerek V-ben
        o.append(f'<g transform="translate({ex},{ey}) rotate({ang})">')
        o.append(f'<rect x="{-17 * s:.1f}" y="{-68 * s:.1f}" width="{34 * s:.1f}" height="{62 * s:.1f}" rx="3" fill="url(#engine)" stroke="#2f3439"/>')
        for k in range(7):
            y = -64 * s + k * 8.5 * s
            o.append(f'<rect x="{-21 * s:.1f}" y="{y:.1f}" width="{42 * s:.1f}" height="{3.2 * s:.1f}" fill="#aab1b8" stroke="#545b62" stroke-width="0.5"/>')
        o.append(f'<rect x="{-19 * s:.1f}" y="{-80 * s:.1f}" width="{38 * s:.1f}" height="{14 * s:.1f}" rx="4" fill="url(#chrome)" stroke="#555"/>')
        o.append("</g>")
    # levegőszűrő a jobb oldalon
    big = {"in_std": 17, "in_open": 15, "in_big": 21}.get(intake, 17)
    cx, cy = ex + 34 * s, ey - 40 * s
    if intake == "in_open":
        o.append(f'<path d="M{cx - 6},{cy - 10} L{cx + 26},{cy - 18} L{cx + 26},{cy + 18} L{cx - 6},{cy + 10} Z" fill="#a01818" stroke="#300"/>')
        for k in range(5):
            o.append(f'<line x1="{cx + 2 + k * 5}" y1="{cy - 12 + k * 0.5}" x2="{cx + 2 + k * 5}" y2="{cy + 12 - k * 0.5}" stroke="#300" stroke-width="1"/>')
    else:
        o.append(f'<circle cx="{cx + 6}" cy="{cy}" r="{big * s:.1f}" fill="url(#chrome)" stroke="#555" stroke-width="1.5"/>')
        o.append(f'<circle cx="{cx + 6}" cy="{cy}" r="{big * s * 0.45:.1f}" fill="none" stroke="#777"/>')
    if carb == "carb_dual":
        o.append(f'<circle cx="{cx + 6}" cy="{cy - 30 * s:.1f}" r="{12 * s:.1f}" fill="url(#chrome)" stroke="#555"/>')
    if blower != "bl_none":
        # feltöltő a hengerek között, felfelé álló beömlővel
        o.append(f'<rect x="{ex - 26 * s:.1f}" y="{ey - 120 * s:.1f}" width="{52 * s:.1f}" height="{34 * s:.1f}" rx="5" fill="url(#chrome)" stroke="#444"/>')
        o.append(f'<rect x="{ex - 14 * s:.1f}" y="{ey - 140 * s:.1f}" width="{28 * s:.1f}" height="{22 * s:.1f}" fill="#222" stroke="#000"/>')
        if blower == "bl_turbo":
            o.append(f'<circle cx="{ex - 50 * s:.1f}" cy="{ey + 30 * s:.1f}" r="{14 * s:.1f}" fill="url(#chrome)" stroke="#444"/>')


def _v8(o, ex, ey, blower, carb):
    o.append(f'<rect x="{ex - 70}" y="{ey - 40}" width="140" height="78" rx="6" fill="url(#engine)" stroke="#2f3439" stroke-width="1.5"/>')
    o.append(f'<path d="M{ex - 74},{ey - 40} L{ex - 60},{ey - 70} L{ex + 60},{ey - 70} L{ex + 74},{ey - 40} Z" fill="#454b52" stroke="#222"/>')
    o.append(f'<rect x="{ex - 64}" y="{ey - 82}" width="128" height="16" rx="5" fill="url(#chrome)" stroke="#555"/>')
    for k in range(4):
        o.append(f'<rect x="{ex - 58 + k * 30}" y="{ey + 2}" width="20" height="10" rx="2" fill="#9aa3ad"/>')
    if blower != "bl_none":
        o.append(f'<rect x="{ex - 40}" y="{ey - 128}" width="80" height="46" rx="5" fill="url(#chrome)" stroke="#444"/>')
        for k in range(6):
            o.append(f'<line x1="{ex - 34 + k * 13}" y1="{ey - 124}" x2="{ex - 34 + k * 13}" y2="{ey - 86}" stroke="#777"/>')
        o.append(f'<path d="M{ex - 26},{ey - 128} L{ex - 20},{ey - 160} L{ex + 26},{ey - 160} L{ex + 32},{ey - 128} Z" fill="#1a1a1a" stroke="#000"/>')
        o.append(f'<rect x="{ex - 22}" y="{ey - 156}" width="46" height="6" fill="#555"/>')
    else:
        o.append(f'<ellipse cx="{ex}" cy="{ey - 92}" rx="{34 if carb != "carb_dual" else 46}" ry="11" fill="url(#chrome)" stroke="#555"/>')


def _exhaust(o, style, ex, ey, rx, ry, s, v8):
    start = [(ex - 18, ey - 52 * s), (ex + 18, ey - 52 * s)] if not v8 else [(ex - 40, ey + 10), (ex + 40, ey + 10)]
    pipe = 'stroke="url(#chrome)" stroke-linecap="round" fill="none"'
    if style == "drag":
        for i, (x, y) in enumerate(start):
            o.append(f'<path d="M{x:.1f},{y:.1f} Q{x - 30:.1f},{y + 45:.1f} {rx + 20 - i * 6:.1f},{ry + 8 - i * 14:.1f} L{rx - 55 - i * 8:.1f},{ry - 18 - i * 16:.1f}" {pipe} stroke-width="{9 if not v8 else 11}"/>')
    elif style == "21":
        for x, y in start:
            o.append(f'<path d="M{x:.1f},{y:.1f} Q{x - 10:.1f},{ey + 40:.1f} {ex - 70:.1f},{ey + 48:.1f}" {pipe} stroke-width="8"/>')
        o.append(f'<path d="M{ex - 70:.1f},{ey + 48:.1f} L{rx - 10:.1f},{ry + 6:.1f}" {pipe} stroke-width="11"/>')
        o.append(f'<rect x="{rx - 60:.1f}" y="{ry - 10:.1f}" width="74" height="22" rx="10" fill="url(#chrome)" stroke="#555" transform="rotate(-8 {rx - 23:.1f} {ry:.1f})"/>')
    else:
        for i, (x, y) in enumerate(start):
            yy = ey + 46 + i * 12
            o.append(f'<path d="M{x:.1f},{y:.1f} Q{x - 6:.1f},{yy:.1f} {ex - 60:.1f},{yy:.1f} L{rx + 10:.1f},{yy + 2:.1f}" {pipe} stroke-width="8"/>')
            end = rx - 60 if style == "std" else rx - 48
            o.append(f'<rect x="{end:.1f}" y="{yy - 8:.1f}" width="{rx + 30 - end:.1f}" height="16" rx="8" fill="url(#chrome)" stroke="#555"/>')
            if style == "slash":
                o.append(f'<path d="M{end:.1f},{yy - 8:.1f} L{end + 12:.1f},{yy + 8:.1f} L{end:.1f},{yy + 8:.1f} Z" fill="#20252a"/>')


def render_svgs(bike):
    g = geometry(bike)
    t = g["t"]
    p = {s: bike["parts"][s]["id"] for s in bike["parts"]}
    eng = PARTS[p["engine"]]
    v8 = eng["cyl"] == 8
    col = bike.get("color", "#b01818")
    rx, ry, rr, fx, fy, fr = g["rx"], g["ry"], g["rr"], g["fx"], g["fy"], g["fr"]
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">', DEFS]
    ex = rx + (fx - rx) * (0.47 if not v8 else 0.5)
    ey = GROUND - 92 if not v8 else GROUND - 100
    seat_x, seat_y = rx + 70, GROUND - (150 if t in ("chopper", "bobber") else 165 if t == "cafe" else 160)
    neck_x = fx - (110 if t == "chopper" else 70 if t == "cafe" else 85)
    neck_y = GROUND - (255 if t == "chopper" else 215 if t == "cafe" else 225)
    if v8:
        seat_y -= 15
    s = (eng["cc"] / 1200) ** 0.33 if not v8 else 1.0
    # hátsó sárvédő
    if t == "cruiser" or t == "v8":
        o.append(f'<path d="M{rx - rr - 14},{ry + 10} A{rr + 14},{rr + 14} 0 0 1 {rx + rr * 0.6},{ry - rr - 6} L{rx + rr * 0.6},{ry - rr + 6} A{rr + 6},{rr + 6} 0 0 0 {rx - rr - 4},{ry + 10} Z" fill="{col}" stroke="{_shade(col, -0.5)}"/>')
    elif t == "bobber":
        o.append(f'<path d="M{rx - rr * 0.7},{ry - rr * 0.65} A{rr + 10},{rr + 10} 0 0 1 {rx + rr * 0.5},{ry - rr - 4} L{rx + rr * 0.5},{ry - rr + 4} A{rr + 2},{rr + 2} 0 0 0 {rx - rr * 0.62},{ry - rr * 0.6} Z" fill="#1a1a1a"/>')
    # lengővilla, váz
    tube = 'stroke="url(#black)" stroke-linecap="round" stroke-linejoin="round" fill="none"'
    o.append(f'<path d="M{rx},{ry} L{ex - 30},{GROUND - 62}" {tube} stroke-width="11"/>')
    o.append(f'<path d="M{rx},{ry} L{seat_x},{seat_y + 10} L{neck_x},{neck_y + 25}" {tube} stroke-width="9"/>')
    o.append(f'<path d="M{neck_x},{neck_y + 30} L{ex + 40},{GROUND - 58} L{ex - 30},{GROUND - 54} L{rx + 20},{ry + 5}" {tube} stroke-width="9"/>')
    o.append(f'<path d="M{rx + 30},{ry - 5} L{seat_x + 20},{seat_y + 18}" stroke="url(#chrome)" stroke-width="6"/>')   # rugóstag
    # motor
    if v8:
        _v8(o, ex, ey, p["blower"], p["carb"])
        o.append(f'<path d="M{rx + 25},{ry + 6} L{ex - 60},{GROUND - 48}" stroke="#222" stroke-width="7"/>')   # kardán
    else:
        _vtwin(o, ex, ey, eng["cc"], p["carb"], p["blower"], p["intake"])
        o.append(f'<rect x="{ex - 95 * s:.1f}" y="{ey - 8:.1f}" width="{70 * s:.1f}" height="{36 * s:.1f}" rx="6" fill="url(#engine)" stroke="#333"/>')  # váltó
    ov = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">', DEFS]
    _exhaust(ov, PARTS[p["exhaust"]].get("style", "std"), ex, ey, rx, ry, s, v8)     # a kerekek elé kerül
    ov.append("</svg>")
    # ülés
    if t == "cafe":
        o.append(f'<path d="M{seat_x - 50},{seat_y + 4} Q{seat_x - 10},{seat_y - 4} {seat_x + 40},{seat_y - 2} L{seat_x + 40},{seat_y + 10} L{seat_x - 52},{seat_y + 14} Z" fill="#141414"/>')
        o.append(f'<path d="M{seat_x - 70},{seat_y - 18} Q{seat_x - 60},{seat_y - 30} {seat_x - 45},{seat_y + 6} L{seat_x - 70},{seat_y + 10} Z" fill="{col}" stroke="{_shade(col, -0.5)}"/>')
    else:
        back = 34 if t in ("cruiser", "v8") else 18
        o.append(f'<path d="M{seat_x - back},{seat_y - 2} Q{seat_x - back + 4},{seat_y - 26} {seat_x - back + 20},{seat_y - 12} Q{seat_x + 10},{seat_y - 4} {seat_x + 45},{seat_y - 6} Q{seat_x + 52},{seat_y + 6} {seat_x + 40},{seat_y + 10} L{seat_x - back},{seat_y + 10} Z" fill="url(#black)" stroke="#000"/>')
    # tank
    tx0, tx1 = seat_x + 42, neck_x + 4
    ty = (seat_y + neck_y) / 2 + (-6 if t != "chopper" else 4)
    th = 34 if t in ("cruiser", "v8") else 28 if t != "bobber" else 26
    o.append(f'<path d="M{tx0},{ty + th * 0.6} Q{tx0 - 6},{ty - th * 0.6} {tx0 + 30},{ty - th * 0.75} L{tx1 - 14},{ty - th * 0.9 - (tx1 - tx0) * 0.06} Q{tx1 + 6},{ty - th * 0.6} {tx1},{ty + th * 0.4} Q{(tx0 + tx1) / 2},{ty + th * 0.85} {tx0},{ty + th * 0.6} Z" fill="{col}" stroke="{_shade(col, -0.55)}" stroke-width="1.5"/>')
    o.append(f'<path d="M{tx0 + 12},{ty - th * 0.45} L{tx1 - 20},{ty - th * 0.62} " stroke="{_shade(col, 0.55)}" stroke-width="4" stroke-linecap="round" opacity="0.8"/>')
    if bike.get("flames"):
        fl = []
        for k in range(5):
            x0 = tx1 - 6
            y0 = ty - th * 0.35 + k * th * 0.2
            fl.append(f'M{x0},{y0} Q{x0 - 30 - k * 4},{y0 - 10} {x0 - 60 - k * 10},{y0 + 2 - k} Q{x0 - 40},{y0 + 4} {x0},{y0 + th * 0.12} Z')
        o.append(f'<path d="{" ".join(fl)}" fill="url(#flame)" stroke="#a01010" stroke-width="0.6"/>')
    # villa
    fork_top = (neck_x + 4, neck_y - 8)
    o.append(f'<line x1="{fork_top[0]}" y1="{fork_top[1]}" x2="{fx}" y2="{fy}" stroke="url(#chromeh)" stroke-width="{9 if t != "cafe" else 8}" stroke-linecap="round"/>')
    o.append(f'<line x1="{fork_top[0] + 6}" y1="{fork_top[1] + 4}" x2="{fx + 5}" y2="{fy + 2}" stroke="#7d858d" stroke-width="3" stroke-linecap="round"/>')
    o.append(f'<rect x="{neck_x - 8}" y="{neck_y - 4}" width="22" height="30" rx="4" fill="url(#black)" transform="rotate(28 {neck_x} {neck_y})"/>')
    # első sárvédő
    if t in ("cruiser", "v8"):
        o.append(f'<path d="M{fx - fr * 0.75},{fy - fr * 0.55} A{fr + 10},{fr + 10} 0 0 1 {fx + fr + 8},{fy + 4} L{fx + fr},{fy + 4} A{fr + 2},{fr + 2} 0 0 0 {fx - fr * 0.7},{fy - fr * 0.48} Z" fill="{col}" stroke="{_shade(col, -0.5)}"/>')
    elif t == "cafe":
        o.append(f'<path d="M{fx - fr * 0.6},{fy - fr * 0.7} A{fr + 6},{fr + 6} 0 0 1 {fx + fr * 0.6},{fy - fr * 0.75} L{fx + fr * 0.55},{fy - fr * 0.65} A{fr},{fr} 0 0 0 {fx - fr * 0.55},{fy - fr * 0.62} Z" fill="#222"/>')
    # kormány
    bars = p["bars"]
    hx, hy = fork_top
    if bars == "ape":
        d = f"M{hx},{hy} L{hx - 6},{hy - 70} Q{hx - 8},{hy - 82} {hx - 26},{hy - 82} L{hx - 40},{hy - 80}"
    elif bars == "beach":
        d = f"M{hx},{hy} Q{hx + 4},{hy - 26} {hx - 26},{hy - 30} L{hx - 52},{hy - 26}"
    elif bars == "clip":
        d = f"M{hx},{hy + 10} L{hx - 30},{hy + 18}"
    else:
        d = f"M{hx},{hy} L{hx + 2},{hy - 12} L{hx - 40},{hy - 12}"
    o.append(f'<path d="{d}" stroke="url(#chrome)" stroke-width="5" fill="none" stroke-linecap="round"/>')
    o.append(f'<path d="{d}" stroke="#d9dee3" stroke-width="1.2" fill="none" opacity="0.7"/>')
    # lámpa
    o.append(f'<circle cx="{hx + 22}" cy="{hy + 8}" r="{15 if t != "cafe" else 13}" fill="url(#chrome)" stroke="#444"/>')
    o.append(f'<circle cx="{hx + 27}" cy="{hy + 8}" r="{10 if t != "cafe" else 9}" fill="url(#lamp)"/>')
    # hátsó lámpa
    o.append(f'<rect x="{rx - rr * 0.55 - 8}" y="{ry - rr * 0.7 - 6}" width="14" height="8" rx="2" fill="#d81b1b" stroke="#600"/>')
    o.append("</svg>")
    tire_w = PARTS[p["tire"]]["w"]
    wk = MODELS[bike["model"]]["wheel"]
    return {"body": "".join(o), "over": "".join(ov), "rear": _wheel(rr, wk, tire_w), "front": _wheel(fr, wk, 120)}, g


def _store(text):
    os.makedirs(CACHE, exist_ok=True)
    h = hashlib.sha1(text.encode()).hexdigest()[:16]
    path = os.path.join(CACHE, h + ".svg")
    if not os.path.exists(path):
        with open(path + ".tmp", "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(path + ".tmp", path)
    return "file://" + path


def render(bike):
    svgs, g = render_svgs(bike)
    return {"body": _store(svgs["body"]), "over": _store(svgs["over"]), "rear": _store(svgs["rear"]), "front": _store(svgs["front"]),
            "w": W, "h": H, "rx": g["rx"], "ry": g["ry"], "rr": g["rr"], "fx": g["fx"], "fy": g["fy"], "fr": g["fr"],
            "ground": GROUND}
