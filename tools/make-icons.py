#!/usr/bin/env python3
"""FusionOS — a Fusion Desktop ikonjai (egyszerű, saját rajzolású SVG-k).

    tools/make-icons.py [kimeneti könyvtár]      (alapértelmezés: desktop/icons)

Két fajta:
  - vonalas ikon (24×24, 1,8 px vonal) a felülethez: <név>.svg
  - programcsempe (színes, lekerekített négyzet, fehér rajzolattal): app-<név>.svg
A rajzolatok szándékosan egyszerűek (a GUI-elv: ne legyen csicsás).
"""
import math
import os
import sys

FG = "#c9d1d9"

# vonalas rajzolatok (stroke) — 24×24 koordináták
G = {
    "file": "M6 3h8l4 4v14H6z M14 3v4h4",
    "file-text": "M6 3h8l4 4v14H6z M14 3v4h4 M9 11h6 M9 14h6 M9 17h4",
    "file-image": "M5 4h14v16H5z M5 16l4-4 3 3 2-2 5 5 M14.5 8.5h.01",
    "file-archive": "M6 3h12v18H6z M12 3v2 M11 5h2 M11 7h2 M11 9h2 M11 11h2 M10.5 13h3v3h-3z",
    "file-exe": "M4 5h16v14H4z M4 9h16 M7 7h.01 M9 7h.01",
    "file-code": "M6 3h8l4 4v14H6z M14 3v4h4 M10 12l-2 2 2 2 M14 12l2 2-2 2",
    "folder-up": "M3 7h6l2 2h10v10H3z M12 17v-6 M9.5 13.5 12 11l2.5 2.5",
    "terminal": "M3 5h18v14H3z M7 10l3 2-3 2 M12 15h5",
    "laser": "M8 3h8v5H8z M12 8v7 M12 18v3 M9 15l-2-1 M15 15l2-1 M8.5 18.5l-2 1 M15.5 18.5l2 1 M12 15.5l.01 0",
    "printer": "M4 3v18 M20 3v18 M4 6h16 M10 6v4h4V6 M11 10l1 2 1-2 M6 18h12",
    "files": "M3 4h18v16H3z M12 4v16 M5.5 8h4 M5.5 11h4 M14.5 8h4 M14.5 11h4",
    "wifi": "M2.5 9a14 14 0 0 1 19 0 M5.5 12.5a9.5 9.5 0 0 1 13 0 M8.5 16a5 5 0 0 1 7 0 M12 19.5h.01",
    "usb": "M12 21V5 M9 7l3-4 3 4 M12 17l-5-3v-3 M12 14l5-3V8 M5.5 9.5h3v1.5h-3z M17 6.5a1.2 1.2 0 1 1 0 .01",
    "chip": "M7 7h10v10H7z M10 10h4v4h-4z M9 3v4 M15 3v4 M9 17v4 M15 17v4 M3 9h4 M3 15h4 M17 9h4 M17 15h4",
    "power": "M12 3v8 M7 6a8 8 0 1 0 10 0",
    "restart": "M20 12a8 8 0 1 1-2.3-5.6 M20 4v5h-5",
    "logout": "M14 4H5v16h9 M10 12h10 M17 9l3 3-3 3",
    "bell": "M6 16V11a6 6 0 0 1 12 0v5l2 2H4z M10 20a2 2 0 0 0 4 0",
    "search": "M10.5 4a6.5 6.5 0 1 1 0 13 6.5 6.5 0 0 1 0-13z M15.5 15.5 20 20",
    "close": "M6 6l12 12 M18 6 6 18",
    "check": "M5 12l5 5 9-10",
    "lock": "M6 11h12v9H6z M8.5 11V8a3.5 3.5 0 0 1 7 0v3",
    "refresh": "M20 11a8 8 0 0 0-14.6-4 M4 4v4h4 M4 13a8 8 0 0 0 14.6 4 M20 20v-4h-4",
    "eye": "M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12z M12 9a3 3 0 1 1 0 6 3 3 0 0 1 0-6z",
    "edit": "M4 20h4L19 9l-4-4L4 16z M13.5 6.5l4 4",
    "copy": "M8 8h12v12H8z M16 8V4H4v12h4",
    "move": "M4 12h11 M11 8l4 4-4 4 M18 4v16",
    "trash": "M4 7h16 M9 7V4h6v3 M6 7l1 13h10l1-13 M10 11v6 M14 11v6",
    "new-folder": "M3 7h6l2 2h10v10H3z M12 11v6 M9 14h6",
    "display": "M3 4h18v12H3z M8 20h8 M12 16v4",
    "info": "M12 3a9 9 0 1 1 0 18 9 9 0 0 1 0-18z M12 11v6 M12 7.5h.01",
    "desktop": "M3 4h18v12H3z M3 13h18 M8 20h8 M12 16v4 M5 14.5h2",
    "home": "M4 11l8-7 8 7 M6 9.5V20h12V9.5 M10 20v-6h4v6",
    "drive": "M3 13l3-8h12l3 8v6H3z M3 13h18 M17 16h.01 M14 16h.01",
    "drive-usb": "M8 9h8v12H8z M9.5 3h5v6h-5z M11 5h.01 M13 5h.01",
    "app": "M3 5h18v14H3z M3 9h18 M6 7h.01 M8.5 7h.01",
    "web": "M12 3a9 9 0 1 1 0 18 9 9 0 0 1 0-18z M3 12h18 M12 3c3 3 3 15 0 18 M12 3c-3 3-3 15 0 18",
    "up": "M12 19V5 M6 11l6-6 6 6",
    "plus": "M12 5v14 M5 12h14",
    "minus": "M5 12h14",
    "menu": "M4 6h16 M4 12h16 M4 18h16",
    "star": "M12 3l2.7 5.6 6.1.9-4.4 4.3 1 6.1L12 17l-5.4 2.9 1-6.1-4.4-4.3 6.1-.9z",
    "download": "M12 4v11 M7 10l5 5 5-5 M4 20h16",
    "eject": "M5 14h14L12 5z M5 18h14",
    "compare": "M4 4h7v16H4z M13 4h7v16h-7z M6.5 8h2 M6.5 12h2 M15.5 8h2 M15.5 14h2",
    "archive-in": "M4 4h16v5H4z M5 9v11h14V9 M12 12v6 M9 15l3 3 3-3",
    "archive-out": "M4 4h16v5H4z M5 9v11h14V9 M12 18v-6 M9 15l3-3 3 3",
    "calendar": "M4 5h16v15H4z M4 9h16 M8 3v4 M16 3v4",
    "package": "M12 3l8 4v10l-8 4-8-4V7z M4 7l8 4 8-4 M12 11v10 M8 5l8 4",
}

# kitöltött rajzolatok (fill) — nem vonalasak
F = {
    "folder": ("M3 6.5A1.5 1.5 0 0 1 4.5 5h4.3l2 2h8.7A1.5 1.5 0 0 1 21 8.5v10a1.5 1.5 0 0 1-1.5 1.5h-15A1.5 1.5 0 0 1 3 18.5z", "#d9a441"),
    "folder-open": ("M3 6.5A1.5 1.5 0 0 1 4.5 5h4.3l2 2h8.7A1.5 1.5 0 0 1 21 8.5V10H6.5L3 18z M6.5 11H22l-3.2 9H3z", "#d9a441"),
    "dot": ("M12 7a5 5 0 1 1 0 10 5 5 0 0 1 0-10z", "#3fb950"),
}


def gear(cx=12, cy=12, r1=5.8, r2=8.2, teeth=8):
    pts = []
    for i in range(teeth * 4):
        a = 2 * math.pi * i / (teeth * 4) - math.pi / (teeth * 4)
        r = r2 if (i % 4) in (1, 2) else r1
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    d = "M" + " L".join(f"{x:.2f} {y:.2f}" for x, y in pts) + "z"
    return d + f" M{cx} {cy - 2.6}a2.6 2.6 0 1 1 0 5.2 2.6 2.6 0 0 1 0-5.2z"


G["settings"] = gear()

# programcsempék: (rajzolat, háttérszín)
APPS = {
    "terminal": ("terminal", "#30363d"),
    "laser": ("laser", "#c2410c"),
    "printer": ("printer", "#15803d"),
    "files": ("files", "#b7791f"),
    "settings": ("settings", "#4b5563"),
    "wifi": ("wifi", "#1d4ed8"),
    "usb": ("usb", "#0e7490"),
    "chip": ("chip", "#6d28d9"),
    "web": ("web", "#0369a1"),
    "app": ("app", "#374151"),
    "package": ("package", "#be185d"),
}


def stroke_svg(d, color=FG, sw=1.8):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24">'
            f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{sw}" '
            f'stroke-linecap="round" stroke-linejoin="round"/></svg>\n')


def fill_svg(d, color):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24">'
            f'<path d="{d}" fill="{color}" fill-rule="evenodd"/></svg>\n')


def tile_svg(d, bg):
    # a rajzolat 0,72-es méretben a csempe közepén
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24">'
            f'<rect x="0.5" y="0.5" width="23" height="23" rx="4" fill="{bg}"/>'
            f'<g transform="translate(3.36 3.36) scale(0.72)">'
            f'<path d="{d}" fill="none" stroke="#ffffff" stroke-width="2.1" '
            f'stroke-linecap="round" stroke-linejoin="round"/></g></svg>\n')


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "..", "desktop", "icons")
    os.makedirs(out, exist_ok=True)
    n = 0
    for name, d in G.items():
        open(os.path.join(out, f"{name}.svg"), "w").write(stroke_svg(d)); n += 1
    for name, (d, c) in F.items():
        open(os.path.join(out, f"{name}.svg"), "w").write(fill_svg(d, c)); n += 1
    for name, (g, bg) in APPS.items():
        open(os.path.join(out, f"app-{name}.svg"), "w").write(tile_svg(G[g], bg)); n += 1
    print(f"{n} ikon: {os.path.realpath(out)}")


if __name__ == "__main__":
    main()
