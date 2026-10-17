"""Vas & Króm — a rajzolt motorképek (art-src/*.jpg, bíbor háttér, zöld fényezés) feldolgozása a játéknak

Fejlesztői eszköz (numpy + PIL kell hozzá, a FusionOS-képben nem fut): python3 make_sprites.py
Kimenet: ../img/bikes/<modell>_base.png  — a motor a fényezés nélkül (átlátszó háttér)
                      <modell>_shade.png — a fényezés árnyalata (szürke, alfa = a fényezés helye)
                      <modell>_hi.png    — a fényezés csillanása (fehér, alfa = erősség)
         ../img/bikes/meta.json          — méret, talajvonal, kerékközéppontok (a 680 széles koordinátarendszerben)
A játék futáskor (Qt, QPainter) ebből rakja össze a választott színű motort — numpy nélkül.
"""
import json
import os

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "img", "bikes")
BIKES = ["bobber883", "cafe1000", "cruiser1200", "chopper1340", "cruiser1800", "v8giant"]
OUT_W = 1000                     # a tárolt kép szélessége (képpont)
GAME_W = 680                     # a játék koordinátarendszere (art.W)


def key_alpha(rgb):
    """bíbor háttér → átlátszó; a széleken a háttérszín kivonása (despill)"""
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    m = np.minimum(r, b) - g                         # „bíborság”
    a = np.clip(1.0 - (m - 55.0) / (125.0 - 55.0), 0.0, 1.0)
    bg = np.array([255.0, 0.0, 255.0])
    safe = np.maximum(a, 0.05)[..., None]
    col = np.clip((rgb - (1.0 - a)[..., None] * bg) / safe, 0, 255)
    col = np.where(a[..., None] > 0.98, rgb, col)
    # maradék bíbor árnyalat (JPEG-színátfolyás a küllők, csövek mentén) → szürke
    m2 = np.minimum(col[..., 0], col[..., 2]) - col[..., 1]
    lum = (0.299 * col[..., 0] + 0.587 * col[..., 1] + 0.114 * col[..., 2])[..., None]
    k = np.clip((m2 - 6.0) / 20.0, 0, 1)[..., None]
    col = col * (1 - k) + lum * k
    return col, a


def paint_weight(rgb):
    """zöld fényezés: árnyalat 75–165°, telítettség; puha széllel"""
    r, g, b = rgb[..., 0] / 255, rgb[..., 1] / 255, rgb[..., 2] / 255
    mx, mn = np.maximum(np.maximum(r, g), b), np.minimum(np.minimum(r, g), b)
    d = mx - mn + 1e-6
    hue = np.where(mx == g, 60 * ((b - r) / d) + 120, np.where(mx == r, (60 * ((g - b) / d)) % 360, 60 * ((r - g) / d) + 240))
    sat = d / (mx + 1e-6)
    hw = np.clip(1 - np.maximum(np.abs(hue - 120) - 35, 0) / 15, 0, 1)
    sw = np.clip((sat - 0.12) / 0.15, 0, 1)        # a csillanás (halvány zöld) is a fényezéshez tartozik
    vw = np.clip((mx - 0.06) / 0.08, 0, 1)
    return hw * sw * vw


def wheels(alpha, lum, ground):
    """a két kerék közepe és sugara: a talajt érő sötét (gumi) tartományok, a gumi bal / jobb széle alapján"""
    h, w = alpha.shape
    dark = (alpha > 0.5) & (lum < 75)
    row = dark[max(0, ground - 3):ground + 1].any(axis=0)
    xs = np.where(row)[0]
    groups, cur = [], [xs[0]]
    for x in xs[1:]:
        if x - cur[-1] > 12:
            groups.append(cur)
            cur = [x]
        else:
            cur.append(x)
    groups.append(cur)
    groups = sorted(groups, key=len, reverse=True)[:2]
    groups.sort(key=lambda g: g[0])
    res = []
    for i, g in enumerate(groups):
        cx = (g[0] + g[-1]) / 2
        best = None
        for r in range(int(h * 0.12), int(h * 0.42)):      # a kör, amelyen a legtöbb sötét pont van
            cy = ground - r
            ang = np.linspace(np.pi * 0.05, np.pi * 0.95, 60) if i == 0 else np.linspace(np.pi * 0.05, np.pi * 0.95, 60)
            px = (cx + np.cos(ang + np.pi / 2 if i == 0 else ang - np.pi / 2) * (r - 6)).astype(int)
            py = (cy + np.sin(ang + np.pi / 2 if i == 0 else ang - np.pi / 2) * (r - 6)).astype(int)
            ok = (px >= 0) & (px < w) & (py >= 0) & (py < h)
            score = dark[py[ok], px[ok]].mean() if ok.any() else 0
            if best is None or score > best[0] + 0.02:
                best = (score, r)
        res.append((cx, ground - best[1], best[1]))
    return res


def process(name):
    im = Image.open(os.path.join(HERE, name + ".jpg")).convert("RGB")
    rgb = np.asarray(im).astype(np.float64)
    col, a = key_alpha(rgb)
    lum = 0.299 * col[..., 0] + 0.587 * col[..., 1] + 0.114 * col[..., 2]
    # talajvonal: a legalsó sor, ahol sok sötét (gumi) képpont van; alatta minden (árnyék) átlátszó
    dark = (a > 0.6) & (lum < 75)
    rows = np.where(dark.sum(axis=1) > 6)[0]
    ground = int(rows.max())
    a[ground + 2:, :] = 0
    p = paint_weight(col) * a
    # árnyalat: a fényezés világossága a fényezés középértékéhez képest
    lref = np.median(lum[p > 0.6]) if (p > 0.6).any() else 120.0
    s = lum / lref
    shade = np.clip(s, 0, 1.15) / 1.15 * 255.0
    hi = np.clip((s - 1.15) / 0.55, 0, 1)
    base_a = a * (1 - p)
    # vágás
    ys, xs = np.where(a > 0.1)
    x0, x1, y0, y1 = max(0, xs.min() - 6), min(a.shape[1], xs.max() + 7), max(0, ys.min() - 6), ground + 2
    sc = OUT_W / (x1 - x0)
    size = (OUT_W, int(round((y1 - y0) * sc)))

    def save(arr_rgb, arr_a, suffix):
        out = np.dstack([np.clip(arr_rgb, 0, 255), np.clip(arr_a * 255, 0, 255)]).astype(np.uint8)[y0:y1, x0:x1]
        Image.fromarray(out, "RGBA").resize(size, Image.LANCZOS).save(os.path.join(OUT, f"{name}_{suffix}.png"), optimize=True)
    save(col, base_a, "base")
    save(np.dstack([shade] * 3), p, "shade")
    save(np.full_like(col, 255.0), p * hi, "hi")
    wh = wheels(a, lum, ground)
    g = GAME_W / (x1 - x0)
    (rx, ry, rr), (fx, fy, fr) = wh
    return {"file": name, "w": GAME_W, "h": round((y1 - y0) * g, 1), "ground": round((ground - y0) * g, 1),
            "rx": round((rx - x0) * g, 1), "ry": round((ry - y0) * g, 1), "rr": round(rr * g, 1),
            "fx": round((fx - x0) * g, 1), "fy": round((fy - y0) * g, 1), "fr": round(fr * g, 1),
            "paint_ref": round(float(lref), 1)}


def main():
    os.makedirs(OUT, exist_ok=True)
    meta = {n: process(n) for n in BIKES}
    with open(os.path.join(OUT, "meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=1)
    for n, m in meta.items():
        print(n, m)


if __name__ == "__main__":
    main()
