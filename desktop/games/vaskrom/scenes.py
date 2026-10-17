"""Vas & Króm — a jelenetek hátterei (SVG): garázs, kocsma, bontó, versenypálya (égbolt, város, lelátó)

python3 scenes.py → a képek az img/ mappába (a játék ezeket tölti be; a forrás ez a fájl).
Minden saját rajz, kitalált nevekkel. A Qt SVG-rajzolója (SVG Tiny 1.2) miatt csak színátmenet és réteg, szűrő nincs.
"""
import math
import os
import random

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "img")


def svg(w, h, body, defs=""):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" preserveAspectRatio="xMidYMid slice">'
            f'<defs>{defs}</defs>{"".join(body)}</svg>')


def f(v):
    return f"{v:.1f}"


# --- garázs -------------------------------------------------------------------------------------------------------

def garage():
    W, H = 1600, 900
    FY = 630                                           # a padló vonala (a magasság 70 %-a)
    rnd = random.Random(11)
    defs = """
<linearGradient id="wall" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#1c1714"/><stop offset="1" stop-color="#3b2d24"/></linearGradient>
<linearGradient id="floor" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#55575a"/><stop offset="0.4" stop-color="#3a3b3e"/>
 <stop offset="1" stop-color="#18191b"/></linearGradient>
<radialGradient id="cone" cx="0.5" cy="0" r="1"><stop offset="0" stop-color="#fff2c4" stop-opacity="0.38"/>
 <stop offset="0.6" stop-color="#ffe7a0" stop-opacity="0.10"/><stop offset="1" stop-color="#ffe7a0" stop-opacity="0"/></radialGradient>
<radialGradient id="pool" cx="0.5" cy="0.5" r="0.5"><stop offset="0" stop-color="#ffeec0" stop-opacity="0.22"/>
 <stop offset="1" stop-color="#ffeec0" stop-opacity="0"/></radialGradient>
<radialGradient id="stain" cx="0.5" cy="0.5" r="0.5"><stop offset="0" stop-color="#000" stop-opacity="0.45"/>
 <stop offset="1" stop-color="#000" stop-opacity="0"/></radialGradient>
<linearGradient id="steel" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#e8ecef"/><stop offset="0.5" stop-color="#9aa3ad"/>
 <stop offset="1" stop-color="#5d6670"/></linearGradient>
<linearGradient id="red" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#d4372b"/><stop offset="1" stop-color="#7a120c"/></linearGradient>
<linearGradient id="wood" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#8a6440"/><stop offset="1" stop-color="#4e3720"/></linearGradient>
<linearGradient id="peg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#7a6146"/><stop offset="1" stop-color="#5a462f"/></linearGradient>
<linearGradient id="win" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#0d1a33"/><stop offset="0.7" stop-color="#2b3d63"/>
 <stop offset="1" stop-color="#c9773a"/></linearGradient>
<linearGradient id="tire" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#3a3b3e"/><stop offset="0.5" stop-color="#141416"/>
 <stop offset="1" stop-color="#0a0a0b"/></linearGradient>
"""
    b = [f'<rect width="{W}" height="{FY}" fill="url(#wall)"/>']
    # téglafal (enyhén eltérő téglák)
    for row, y in enumerate(range(0, FY, 28)):
        off = 0 if row % 2 else 44
        for x in range(-88 + off, W, 88):
            c = rnd.choice(["#3e2c22", "#47322a", "#3a2a20", "#4a3628", "#352720"])
            b.append(f'<rect x="{x + 2}" y="{y + 2}" width="84" height="24" rx="2" fill="{c}" opacity="0.85"/>')
    b.append(f'<rect width="{W}" height="{FY}" fill="#000" opacity="0.18"/>')
    # ablak (esti ég)
    b.append('<rect x="1150" y="70" width="300" height="190" fill="#1b1d21"/>')
    b.append('<rect x="1162" y="82" width="276" height="166" fill="url(#win)"/>')
    for k in range(25):
        b.append(f'<circle cx="{1170 + rnd.random() * 260:.0f}" cy="{90 + rnd.random() * 90:.0f}" r="{0.8 + rnd.random():.1f}" fill="#fff" opacity="0.7"/>')
    b.append('<path d="M1162,248 L1200,214 L1236,232 L1290,196 L1340,226 L1390,206 L1438,236 L1438,248 Z" fill="#0b0d12"/>')
    b.append('<path d="M1300,82 L1300,248 M1162,165 L1438,165" stroke="#1b1d21" stroke-width="10"/>')
    # szerszámfal (lyukacsos lap) szerszámokkal
    b.append('<rect x="60" y="60" width="520" height="300" rx="4" fill="url(#peg)" stroke="#3a2a1a" stroke-width="3"/>')
    for y in range(80, 350, 18):
        for x in range(80, 570, 18):
            b.append(f'<circle cx="{x}" cy="{y}" r="2.3" fill="#2c2015"/>')
    # villáskulcsok (méret szerint)
    for i in range(7):
        x, ln = 100 + i * 34, 120 + i * 12
        b.append(f'<g transform="translate({x},92)">'
                 f'<rect x="-4" y="14" width="8" height="{ln - 28}" rx="3" fill="url(#steel)" stroke="#3a4046"/>'
                 f'<path d="M-11,0 L-4,16 L4,16 L11,0 L5,0 L2,8 L-2,8 L-5,0 Z" fill="url(#steel)" stroke="#3a4046"/>'
                 f'<circle cx="0" cy="{ln - 8}" r="10" fill="url(#steel)" stroke="#3a4046"/><circle cx="0" cy="{ln - 8}" r="5" fill="#5a462f"/></g>')
    # kalapács
    b.append('<g transform="translate(372,90) rotate(8)"><rect x="-5" y="20" width="10" height="150" rx="4" fill="url(#wood)"/>'
             '<rect x="-26" y="0" width="52" height="24" rx="3" fill="#2a2e33"/><rect x="-26" y="2" width="52" height="5" fill="#5d6670"/></g>')
    # csavarhúzók
    for i, c in enumerate(["#c4271b", "#e0a40c", "#1d5fb0", "#2a7a2a"]):
        x = 430 + i * 30
        b.append(f'<rect x="{x - 7}" y="90" width="14" height="56" rx="6" fill="{c}" stroke="#000" stroke-width="0.8"/>'
                 f'<rect x="{x - 2}" y="146" width="4" height="80" fill="url(#steel)"/>')
    # fogó
    b.append('<g transform="translate(470,250)"><path d="M-6,0 L-14,80 L-6,82 L2,6 Z M6,0 L14,80 L6,82 L-2,6 Z" fill="#c4271b"/>'
             '<path d="M-8,-46 L-3,0 L3,0 L8,-46 L2,-50 L0,-10 L-2,-50 Z" fill="url(#steel)"/></g>')
    # polc olajos kannákkal
    b.append('<rect x="640" y="200" width="420" height="12" fill="url(#wood)"/>')
    for i in range(7):
        x = 652 + i * 58
        c = ["#c4271b", "#1d5fb0", "#e0a40c", "#2a7a2a", "#c4271b", "#3a3d42", "#e0a40c"][i]
        h = 52 + (i % 3) * 10
        b.append(f'<rect x="{x}" y="{200 - h}" width="44" height="{h}" rx="4" fill="{c}" stroke="#000" stroke-width="0.8"/>'
                 f'<rect x="{x + 6}" y="{200 - h + 14}" width="32" height="18" fill="#efe9dc" opacity="0.85"/>'
                 f'<rect x="{x + 16}" y="{200 - h - 8}" width="12" height="9" fill="#888"/>'
                 f'<rect x="{x + 3}" y="{200 - h + 2}" width="6" height="{h - 6}" fill="#fff" opacity="0.18"/>')
    # plakát (kitalált verseny)
    b.append('<g transform="translate(700,260) rotate(-2)"><rect width="200" height="270" fill="#efe2c4" stroke="#2a2018" stroke-width="3"/>'
             '<rect x="12" y="12" width="176" height="150" fill="#c4271b"/>'
             '<circle cx="100" cy="100" r="44" fill="#ffd23a"/><path d="M40,140 L160,140 L130,110 L70,110 Z" fill="#1a1a1a"/>'
             '<circle cx="62" cy="140" r="16" fill="#1a1a1a"/><circle cx="140" cy="140" r="16" fill="#1a1a1a"/>'
             '<text x="100" y="196" text-anchor="middle" font-family="DejaVu Sans" font-weight="bold" font-size="22" fill="#1a1a1a">GYORSULÁSI</text>'
             '<text x="100" y="222" text-anchor="middle" font-family="DejaVu Sans" font-weight="bold" font-size="22" fill="#1a1a1a">VERSENY</text>'
             '<text x="100" y="252" text-anchor="middle" font-family="DejaVu Sans" font-size="15" fill="#7a120c">402 MÉTER · 1977</text></g>')
    # gumik halomban (jobb oldalt)
    for i in range(4):
        y = FY - 30 - i * 44
        b.append(f'<ellipse cx="1500" cy="{y}" rx="92" ry="26" fill="url(#tire)" stroke="#000"/>'
                 f'<ellipse cx="1500" cy="{y - 6}" rx="50" ry="12" fill="#0a0a0b"/>')
    # munkapad szerszámosládával (bal)
    b.append(f'<rect x="40" y="{FY - 170}" width="560" height="22" fill="url(#wood)" stroke="#2a1a0a"/>')
    b.append(f'<rect x="60" y="{FY - 148}" width="18" height="148" fill="#3a2a1a"/><rect x="560" y="{FY - 148}" width="18" height="148" fill="#3a2a1a"/>')
    b.append(f'<rect x="380" y="{FY - 300}" width="200" height="130" rx="6" fill="url(#red)" stroke="#3a0602" stroke-width="2"/>')
    for k in range(4):
        y = FY - 290 + k * 30
        b.append(f'<rect x="390" y="{y}" width="180" height="24" rx="3" fill="#b22a1f" stroke="#5a0a05"/>'
                 f'<rect x="450" y="{y + 9}" width="60" height="6" rx="3" fill="url(#steel)"/>')
    b.append(f'<g transform="translate(150,{FY - 200})"><rect x="0" y="0" width="90" height="30" fill="#2a2e33"/>'
             '<rect x="-10" y="-14" width="40" height="18" fill="#3a3f45"/><rect x="60" y="-14" width="40" height="18" fill="#3a3f45"/>'
             '<rect x="38" y="-30" width="14" height="40" fill="url(#steel)"/></g>')
    # padló: beton, dilatációs fugák, olajfoltok, a fal tövében sárga csík
    b.append(f'<rect y="{FY}" width="{W}" height="{H - FY}" fill="url(#floor)"/>')
    b.append(f'<rect y="{FY - 6}" width="{W}" height="6" fill="#c79a1e"/>')
    for x in range(0, W + 400, 400):
        b.append(f'<path d="M{x},{FY} L{x - 260},{H}" stroke="#202124" stroke-width="2" opacity="0.6"/>')
    b.append(f'<path d="M0,{FY + 120} L{W},{FY + 120}" stroke="#202124" stroke-width="2" opacity="0.5"/>')
    for (x, y, rx, ry) in ((300, FY + 80, 120, 20), (820, FY + 170, 160, 26), (1260, FY + 60, 90, 14), (560, FY + 230, 130, 22)):
        b.append(f'<ellipse cx="{x}" cy="{y}" rx="{rx}" ry="{ry}" fill="url(#stain)"/>')
    # lámpák és fénykúpok
    for x in (420, 1100):
        b.append(f'<line x1="{x}" y1="0" x2="{x}" y2="40" stroke="#111" stroke-width="3"/>')
        b.append(f'<path d="M{x - 46},{70} L{x - 18},{40} L{x + 18},{40} L{x + 46},{70} Z" fill="#1f5a3a" stroke="#0a2015"/>')
        b.append(f'<ellipse cx="{x}" cy="70" rx="20" ry="6" fill="#fff6d0"/>')
        b.append(f'<path d="M{x - 40},{72} L{x - 380},{H} L{x + 380},{H} L{x + 40},{72} Z" fill="url(#cone)"/>')
        b.append(f'<ellipse cx="{x}" cy="{FY + 150}" rx="360" ry="70" fill="url(#pool)"/>')
    return svg(W, H, b, defs)


# --- kocsma -------------------------------------------------------------------------------------------------------

def bar():
    W, H = 1600, 900
    rnd = random.Random(5)
    defs = """
<linearGradient id="panel" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#3a2416"/><stop offset="0.5" stop-color="#4a2e1c"/>
 <stop offset="1" stop-color="#2e1c10"/></linearGradient>
<linearGradient id="counter" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#6a4426"/><stop offset="0.15" stop-color="#3a2414"/>
 <stop offset="1" stop-color="#1a0f08"/></linearGradient>
<radialGradient id="neon" cx="0.5" cy="0.5" r="0.5"><stop offset="0" stop-color="#ff4a30" stop-opacity="0.35"/>
 <stop offset="1" stop-color="#ff4a30" stop-opacity="0"/></radialGradient>
<radialGradient id="back" cx="0.5" cy="0.5" r="0.5"><stop offset="0" stop-color="#ffcf7a" stop-opacity="0.35"/>
 <stop offset="1" stop-color="#ffcf7a" stop-opacity="0"/></radialGradient>
<linearGradient id="glass" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#fff" stop-opacity="0.05"/>
 <stop offset="0.3" stop-color="#fff" stop-opacity="0.45"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>
"""
    b = [f'<rect width="{W}" height="{H}" fill="#1a100a"/>']
    for x in range(0, W, 80):                          # lambéria
        b.append(f'<rect x="{x}" y="0" width="78" height="{H}" fill="url(#panel)"/>')
    b.append(f'<rect y="430" width="{W}" height="14" fill="#2a1a0e"/>')
    # polcok italokkal, hátsó fénnyel
    b.append('<ellipse cx="1200" cy="300" rx="420" ry="220" fill="url(#back)"/>')
    for sy in (210, 330):
        b.append(f'<rect x="860" y="{sy}" width="700" height="10" fill="#6a4426"/>')
        x = 875
        while x < 1540:
            h = 60 + rnd.random() * 40
            w = 18 + rnd.random() * 10
            c = rnd.choice(["#3a6a2a", "#7a3a12", "#c9a24a", "#2a4a7a", "#8a1a12", "#d8d2b8"])
            b.append(f'<rect x="{x:.0f}" y="{sy - h:.0f}" width="{w:.0f}" height="{h:.0f}" rx="4" fill="{c}" opacity="0.9"/>'
                     f'<rect x="{x + w * 0.3:.0f}" y="{sy - h - 16:.0f}" width="{w * 0.4:.0f}" height="18" fill="{c}"/>'
                     f'<rect x="{x:.0f}" y="{sy - h:.0f}" width="{w:.0f}" height="{h:.0f}" rx="4" fill="url(#glass)"/>')
            x += w + 6 + rnd.random() * 8
    # neon fénye (a felirat a játékban, QML-ben)
    b.append('<ellipse cx="420" cy="60" rx="520" ry="200" fill="url(#neon)"/>')
    # bekeretezett fotók, darts
    for i, (x, y) in enumerate(((120, 520), (300, 500), (480, 530))):
        b.append(f'<rect x="{x}" y="{y}" width="140" height="100" fill="#d8c9a4" stroke="#2a1a0e" stroke-width="8"/>'
                 f'<rect x="{x + 14}" y="{y + 14}" width="112" height="72" fill="#5a4a3a"/>'
                 f'<circle cx="{x + 50}" cy="{y + 60}" r="14" fill="#1a1a1a"/><circle cx="{x + 92}" cy="{y + 60}" r="14" fill="#1a1a1a"/>'
                 f'<path d="M{x + 50},{y + 60} L{x + 70},{y + 40} L{x + 92},{y + 60}" stroke="#1a1a1a" stroke-width="5" fill="none"/>')
    for k, c in enumerate(["#1a1a1a", "#e8dcb8", "#1a1a1a", "#c4271b", "#2a7a2a", "#c4271b"]):
        b.append(f'<circle cx="720" cy="560" r="{80 - k * 13}" fill="{c}"/>')
    # pult, csapok, poharak
    b.append(f'<rect y="700" width="{W}" height="200" fill="url(#counter)"/>')
    b.append(f'<rect y="690" width="{W}" height="16" rx="6" fill="#8a5a30"/>')
    for x in (1000, 1060, 1120):
        b.append(f'<rect x="{x}" y="610" width="14" height="80" fill="#c9ced3"/><rect x="{x - 8}" y="600" width="30" height="14" rx="5" fill="#d7dde3"/>'
                 f'<rect x="{x + 2}" y="570" width="10" height="32" rx="4" fill="#1a1a1a"/>')
    for x in (200, 640, 1300):
        b.append(f'<path d="M{x},640 L{x + 34},640 L{x + 30},690 L{x + 4},690 Z" fill="#e0a40c" opacity="0.9"/>'
                 f'<path d="M{x},640 L{x + 34},640 L{x + 33},650 L{x + 1},650 Z" fill="#fff8e8"/>'
                 f'<path d="M{x + 4},648 L{x + 8},688" stroke="#fff" stroke-width="3" opacity="0.4"/>')
    b.append(f'<rect width="{W}" height="{H}" fill="#000" opacity="0.25"/>')
    return svg(W, H, b, defs)


# --- bontó --------------------------------------------------------------------------------------------------------

def junk():
    W, H = 1600, 900
    rnd = random.Random(9)
    defs = """
<linearGradient id="sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#4a6a8a"/><stop offset="1" stop-color="#c9b48a"/></linearGradient>
<linearGradient id="dirt" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#5a4430"/><stop offset="1" stop-color="#241a10"/></linearGradient>
<linearGradient id="rust" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#a0602a"/><stop offset="1" stop-color="#4a2a10"/></linearGradient>
<linearGradient id="tire" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#3a3b3e"/><stop offset="1" stop-color="#0a0a0b"/></linearGradient>
"""
    b = [f'<rect width="{W}" height="{H}" fill="url(#sky)"/>']
    # daru sziluett
    b.append('<path d="M1250,330 L1270,60 L1290,330 Z M1270,70 L1560,90 L1560,100 L1270,90 Z" fill="#3a3530"/>'
             '<line x1="1500" y1="98" x2="1500" y2="230" stroke="#2a2520" stroke-width="3"/><rect x="1470" y="230" width="60" height="22" fill="#2a2520"/>')
    # roncshalmok
    for layer, (base, cols) in enumerate(((330, ["#6a5040", "#5a4436", "#7a5a40"]), (400, ["#7a4a24", "#8a5a2a", "#5a3a20"]))):
        for i in range(14):
            x = rnd.random() * W
            s = 80 + rnd.random() * 120
            c = rnd.choice(cols)
            b.append(f'<path d="M{x - s:.0f},{base + 20} L{x - s * 0.5:.0f},{base - s * 0.5:.0f} L{x - s * 0.1:.0f},{base - s * 0.62:.0f} '
                     f'L{x + s * 0.4:.0f},{base - s * 0.4:.0f} L{x + s:.0f},{base + 20} Z" fill="{c}"/>')
            for k in range(3):                          # kerekek, csövek a halomban
                cx, cy = x + (rnd.random() - 0.5) * s, base - rnd.random() * s * 0.4
                b.append(f'<circle cx="{cx:.0f}" cy="{cy:.0f}" r="{10 + rnd.random() * 18:.0f}" fill="none" stroke="#2a2018" stroke-width="5"/>')
    # drótkerítés oszlopokkal
    b.append(f'<rect y="420" width="{W}" height="{H - 420}" fill="url(#dirt)"/>')
    for x in range(-400, W, 22):
        b.append(f'<line x1="{x}" y1="420" x2="{x + 300}" y2="120" stroke="#2a2a2a" stroke-width="1.2" opacity="0.55"/>'
                 f'<line x1="{x}" y1="120" x2="{x + 300}" y2="420" stroke="#2a2a2a" stroke-width="1.2" opacity="0.55"/>')
    for x in range(20, W, 200):
        b.append(f'<rect x="{x}" y="110" width="8" height="320" fill="#4a4a4a"/>')
    b.append(f'<line x1="0" y1="118" x2="{W}" y2="118" stroke="#4a4a4a" stroke-width="4"/>')
    # gumihalom, hordók elöl
    for i in range(5):
        b.append(f'<ellipse cx="140" cy="{820 - i * 36}" rx="100" ry="26" fill="url(#tire)" stroke="#000"/>')
    for x in (1380, 1480):
        b.append(f'<rect x="{x}" y="700" width="80" height="120" rx="6" fill="url(#rust)" stroke="#2a1a0a"/>'
                 f'<rect x="{x}" y="730" width="80" height="6" fill="#3a2010"/><rect x="{x}" y="784" width="80" height="6" fill="#3a2010"/>')
    b.append(f'<rect width="{W}" height="{H}" fill="#000" opacity="0.15"/>')
    return svg(W, H, b, defs)


# --- versenypálya: égbolt, város (csempe), lelátó (csempe) -----------------------------------------------------------

def sky():
    W, H = 1600, 400
    defs = """
<linearGradient id="sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#121e3a"/><stop offset="0.45" stop-color="#3a3a6a"/>
 <stop offset="0.75" stop-color="#c9673a"/><stop offset="1" stop-color="#f6b45a"/></linearGradient>
<radialGradient id="sun" cx="0.5" cy="0.5" r="0.5"><stop offset="0" stop-color="#fff2c0"/><stop offset="0.25" stop-color="#ffd27a" stop-opacity="0.9"/>
 <stop offset="1" stop-color="#ff9a4a" stop-opacity="0"/></radialGradient>
<linearGradient id="cloud" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#ffb07a" stop-opacity="0.85"/>
 <stop offset="1" stop-color="#7a3a5a" stop-opacity="0.6"/></linearGradient>
"""
    rnd = random.Random(4)
    b = [f'<rect width="{W}" height="{H}" fill="url(#sky)"/>', '<circle cx="1180" cy="330" r="220" fill="url(#sun)"/>',
         '<circle cx="1180" cy="340" r="44" fill="#fff0c8" opacity="0.95"/>']
    for k in range(40):
        b.append(f'<circle cx="{rnd.random() * W:.0f}" cy="{rnd.random() * 120:.0f}" r="{0.6 + rnd.random():.1f}" fill="#fff" opacity="{0.3 + rnd.random() * 0.5:.2f}"/>')
    for (x, y, s) in ((200, 170, 1.0), (620, 120, 0.8), (980, 210, 1.2), (1420, 150, 0.9)):
        b.append(f'<g transform="translate({x},{y}) scale({s})">'
                 '<path d="M-160,20 Q-150,-10 -110,-6 Q-90,-34 -40,-24 Q-10,-46 40,-26 Q90,-34 110,-6 Q160,-6 170,20 Z" fill="url(#cloud)"/></g>')
    return svg(W, H, b, defs)


def city():
    """város-sziluett, vízszintesen ismételhető csempe (800 × 160)"""
    W, H = 800, 160
    rnd = random.Random(3)
    b = []
    x = 0
    while x < W:
        bw = 34 + rnd.random() * 60
        bh = 40 + rnd.random() * 100
        b.append(f'<rect x="{x:.0f}" y="{H - bh:.0f}" width="{bw:.0f}" height="{bh:.0f}" fill="#24182a"/>')
        if rnd.random() < 0.25:
            b.append(f'<rect x="{x + bw * 0.4:.0f}" y="{H - bh - 18:.0f}" width="4" height="18" fill="#24182a"/>'
                     f'<circle cx="{x + bw * 0.4 + 2:.0f}" cy="{H - bh - 19:.0f}" r="2.5" fill="#ff3a2a"/>')
        for yy in range(int(H - bh + 8), H - 10, 14):
            for xx in range(int(x + 6), int(x + bw - 8), 12):
                if rnd.random() < 0.35:
                    b.append(f'<rect x="{xx}" y="{yy}" width="5" height="7" fill="#ffd27a" opacity="{0.4 + rnd.random() * 0.5:.2f}"/>')
        x += bw + 3
    # víztorony
    b.append('<g transform="translate(520,20)"><rect x="-4" y="40" width="4" height="100" fill="#1c1222"/><rect x="40" y="40" width="4" height="100" fill="#1c1222"/>'
             '<path d="M-10,10 Q20,-8 50,10 L50,44 L-10,44 Z" fill="#1c1222"/></g>')
    return svg(W, H, b)


def stands():
    """lelátó tetővel és nézőkkel, kerítéssel; ismételhető csempe (800 × 220)"""
    W, H = 800, 220
    rnd = random.Random(8)
    defs = """
<linearGradient id="roof" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#b8321e"/><stop offset="1" stop-color="#6a160c"/></linearGradient>
<linearGradient id="grass" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#3d5a34"/><stop offset="1" stop-color="#22351e"/></linearGradient>
<linearGradient id="tier" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#6b7178"/><stop offset="1" stop-color="#3a3f45"/></linearGradient>
"""
    b = ['<g transform="translate(0,20)">', f'<rect y="120" width="{W}" height="{H - 140}" fill="url(#grass)"/>']
    for gx in (20, 420):                               # két lelátó csempénként
        b.append(f'<rect x="{gx}" y="34" width="360" height="92" fill="url(#tier)"/>')
        for r in range(5):
            b.append(f'<rect x="{gx}" y="{44 + r * 16}" width="360" height="3" fill="#2a2e33"/>')
        for k in range(120):                           # nézők: fej + test, színes ruhák
            px = gx + 6 + (k % 40) * 8.8 + rnd.random() * 3
            py = 40 + (k // 40) * 26 + rnd.random() * 6
            c = rnd.choice(["#d9773a", "#3a6ea5", "#e8e8e8", "#c4271b", "#2a7a2a", "#e0c040", "#6a3a8a", "#1a1a1a"])
            b.append(f'<rect x="{px:.1f}" y="{py + 6:.1f}" width="6" height="9" rx="2" fill="{c}"/>'
                     f'<circle cx="{px + 3:.1f}" cy="{py + 3:.1f}" r="3" fill="{rnd.choice(["#e8c4a0", "#c49a6c", "#8a5a3a"])}"/>')
        b.append(f'<path d="M{gx - 10},34 L{gx + 370},34 L{gx + 360},14 L{gx},14 Z" fill="url(#roof)"/>')
        for px in range(gx, gx + 361, 60):
            b.append(f'<rect x="{px}" y="30" width="4" height="96" fill="#2a2e33"/>')
        for k in range(6):                             # zászlók
            fx = gx + 30 + k * 60
            b.append(f'<line x1="{fx}" y1="14" x2="{fx}" y2="-6" stroke="#2a2e33" stroke-width="2"/>'
                     f'<path d="M{fx},-6 L{fx + 16},-1 L{fx},4 Z" fill="{["#ffd23a", "#c4271b", "#3a6ea5"][k % 3]}"/>')
    # villanyoszlop reflektorral
    b.append('<rect x="398" y="-40" width="5" height="170" fill="#2a2e33"/><rect x="384" y="-46" width="34" height="12" fill="#3a3f45"/>'
             '<rect x="388" y="-44" width="26" height="6" fill="#fff2c0"/>')
    # kerítés a pálya mellett
    b.append(f'<rect y="126" width="{W}" height="6" fill="#9aa0a6"/><rect y="150" width="{W}" height="4" fill="#9aa0a6"/>')
    for x in range(0, W, 25):
        b.append(f'<rect x="{x}" y="126" width="3" height="40" fill="#7d858d"/>')
    for x in range(30, W, 200):                        # reklámtáblák (kitalált nevek)
        name = ["OLAJOS KANNA", "VASLÓ", "KENTAUR", "PANNON"][(x // 200) % 4]
        b.append(f'<rect x="{x}" y="160" width="160" height="34" fill="#efe9dc" stroke="#1a1a1a" stroke-width="2"/>'
                 f'<text x="{x + 80}" y="183" text-anchor="middle" font-family="DejaVu Sans" font-weight="bold" font-size="14" fill="#b01818">{name}</text>')
    b.append("</g>")
    return svg(W, H, b, defs)


SCENES = {"garage": garage, "bar": bar, "junk": junk, "sky": sky, "city": city, "stands": stands}


def build(out=OUT):
    os.makedirs(out, exist_ok=True)
    for name, fn in SCENES.items():
        with open(os.path.join(out, name + ".svg"), "w", encoding="utf-8") as fh:
            fh.write(fn())
    return sorted(SCENES)


if __name__ == "__main__":
    print("kész:", ", ".join(build()))
