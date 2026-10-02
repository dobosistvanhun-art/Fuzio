# M6j — Csoportos Start menü, fejlesztői eszközök (Node.js, Wrangler), Lomtár, gyors törlés Drive mellett: ellenőrzés a ZBookon (0.0.22)

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

## C) Lomtár (Fájlkezelő)

A törlés (F8 / Del) mostantól a **Lomtárba** tesz: ugyanazon a meghajtón belül átnevezés, ezért azonnali,
akármekkora a fájl. A szabványos (freedesktop) lomtár: `~/.local/share/Trash`, USB-meghajtón `.Trash-1000`.

- [ ] Egy fájl → **F8** → megerősítés nélkül, azonnal eltűnik; **Ctrl+Z** → visszajön
- [ ] Bal oldali kötetlista: **Lomtár** → a törölt elemek; kijelölve felül: eredeti hely, törlés ideje
- [ ] **Visszaállítás** gomb → az eredeti helyére kerül (ha ott már van ilyen nevű: „(visszaállítva)” utótaggal)
- [ ] **Ürítés** gomb → megerősítés után végleges törlés; a Lomtárban az F8 is véglegesen töröl
- [ ] **Shift+Del**: végleges törlés a lomtár kihagyásával (megerősítéssel)
- [ ] Google Drive-on a törlés megerősítést kér, és a Drive **saját** lomtárába kerül (drive.google.com → Kuka)

## D) Lassú törlés, ha a másik panel a Google Drive

Ok: a művelet utáni frissítés és a szabad hely lekérdezése a Drive-panelen az internetre várt.
Mostantól hálózati / Drive-panelen ez a háttérben fut.

- [ ] Egyik panel: Google Drive, másik: saját mappa → egy kis fájl törlése / másolása azonnal kész
- [ ] A Drive-panel szabad helye pár másodperc múlva jelenik meg (nem akasztja meg az ablakot)
- [ ] Ha valami mégis lassú: `~/.local/share/fusion/files.log` (a 0,5 s-nál lassabb lépések)

## Parancssor

```bash
fusion-dev                      # állapot
fusion-dev update node          # új LTS
fusion-dev update wrangler
```
