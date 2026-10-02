# M6j — Csoportos Start menü, fejlesztői eszközök (Node.js, Wrangler): ellenőrzés a ZBookon (0.0.22)

## Frissítés (Mint) — a DATA megmarad

```bash
sudo apt update
cd ~/Fusion
rm -rf fusionos-regi && mv fusionos fusionos-regi
tar xzf fusionos-m6j.tar.gz
cp -r fusionos-regi/build/cache fusionos/build/
cd fusionos
build/fusion-build all
sudo build/fusion-build update /dev/sdb      # megerősítés: sdb
```

## A) Start menü csoportokkal

Bal oldalt a csoportok, jobbra a csoport programjai. A csoportot a program saját kategóriái adják
(Flatpak / Linux: a .desktop-fájl, Windows: a recept); a Fusion saját programjai a Rendszer csoportban vannak.

| csoport | mi kerül bele (automatikusan) |
|---|---|
| Műhely | lézer, 3D nyomtatás, CAD, elektronika (LightBurn, PrusaSlicer, FreeCAD, KiCad, Nyomtató) |
| Grafika · Iroda · Internet · Hang és videó · Fejlesztés · Oktatás és tudomány · Játékok · Segédprogramok | a kategóriák szerint |
| Rendszer | Fájlkezelő, Beállítások, Programkezelő, Programbolt, Terminál |
| Egyéb | aminek nincs kategóriája |

- [ ] Megnyitás (Super): balra a csoportok darabszámmal, jobbra a kiválasztott csoport
- [ ] Néhány indítás után felül megjelenik a **Gyakran használt** csoport (alapból ez nyílik)
- [ ] **Jobb gomb egy programon** → csoport választása (pl. a LightBurn → Műhely); „(automatikus)” = vissza az eredetire
- [ ] **← / →** (vagy PageUp / PageDown) csoportváltás billentyűvel; gépelés → keresés minden csoportban
- [ ] **Összes program**: ábécérendben minden

## B) Fejlesztői eszközök (Programkezelő → lent: Fejlesztői eszközök)

- [ ] **Node.js → Telepítés**: terminálablak — a legújabb LTS letöltése a nodejs.org-ról, ellenőrzőösszeg,
      kicsomagolás a `/data/dev` alá (root nélkül)
- [ ] **Wrangler → Telepítés**: `npm install -g wrangler` a saját mappába (~/.local) — pár perc
- [ ] **Wrangler → Bejelentkezés**: a böngészőben (Firefox) a Cloudflare-fiók, „Allow” → a terminálban a fiók neve
- [ ] Terminál (Ctrl+Alt+T): `node --version`, `npm --version`, `wrangler --version`, `git --version`
- [ ] A motoros program mappájában: `npm install`, `wrangler dev` / `wrangler deploy`

## Parancssor

```bash
fusion-dev                      # állapot
fusion-dev update node          # új LTS
fusion-dev update wrangler
```
