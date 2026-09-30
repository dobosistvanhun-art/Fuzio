# M6 — Fusion Desktop: a felületi technika mérése (döntés előtt)

A Fusion Desktop (panel, Start menü, később a kétpaneles fájlkezelő, beállítások) alapja két
technika egyike lesz. A döntés **mérés alapján** születik; ehhez a képben mindkét változat benne van,
ugyanazzal a tudással és ugyanazzal a háttérrésszel (ablaklista, Wi-Fi, óra, programok):

| Változat | Technika | Erősség (várható) | Kérdés (ezt mérjük) |
| --- | --- | --- | --- |
| `qml` | Qt 6 / Qt Quick (QML) | natív, a GPU-n rajzol, kevés memória | elég gyorsan fejleszthető-e a mockupok stílusa |
| `web` | HTML/CSS a WebKitGTK-ban | a mockupok stílusa egyszerűen hozható, a webes felületekkel (Fluidd, Mainsail) egy technika | memória és indulási idő a ZBookon |

A ablakokat továbbra is a JWM kezeli (új, lapos FusionDark stílus, saját tálca nélkül); a panelt és a
Start menüt a Fusion Shell adja.

## Frissítés (Mint) — a DATA megmarad

```bash
cd ~/Fusion
rm -rf fusionos-regi && mv fusionos fusionos-regi
tar xzf fusionos-m6a.tar.gz
cp -r fusionos-regi/build/cache fusionos/build/
cd fusionos
build/fusion-build deps --install
build/fusion-build all
sudo build/fusion-build update /dev/sdb      # megerősítés: sdb
```

(Ez a csomag a `bootentry` parancsot is tartalmazza: `sudo build/fusion-build bootentry /dev/sdb`.)

## A) Ránézésre (ZBook, F9 → FusionOS)

A Desktop alján a **Fusion Shell panelje**: Start gomb (F), a nyitott ablakok, jobbra Wi-Fi és óra.
Start menü: kattintás az F-re, vagy **Alt+F1**; gépeléssel keres, Enter indítja az elsőt, Esc zár.

```bash
fusion-shell                 # melyik változat fut
fusion-shell use web         # átváltás (azonnal) — vissza: fusion-shell use qml
```

- [ ] mindkét változatban: a panel alul, az ablakok nem lógnak alá (maximalizálva sem)
- [ ] a tálcagombok: kattintás → előre / kis méretre; az aktív ablak kék aláhúzással
- [ ] Start menü: keresés, programindítás (Terminál, LightBurn, Nyomtató…)
- [ ] melyik „érződik” jobbnak (gyorsaság, betűk, élesség) — ez is a döntés része

## B) Mérés

```bash
fusion-uimeasure
```

Kb. 5 perc; közben a panel többször eltűnik és megjelenik — ne nyúlj a géphez. A végén egy táblázat:

| sor | jelentése |
| --- | --- |
| indulás (ms) | a program indításától az első kirajzolt panelig |
| memória PSS (MiB) | a változat összes folyamatának tényleges memóriája |
| CPU üresjáratban (%) | érintés nélkül, 30 mp átlag |
| Start menü nyitás (ms) | a kéréstől a menü megjelenéséig |

Az eredmény a `~/uimeasure-….txt` fájlba is mentődik. **Visszajelzés:** fotó a táblázatról + melyik
változat tetszett jobban. Összehasonlításul a felhős (szoftveres rajzolású) mérés: QML 261 ms / 164 MiB,
web 502 ms / 361 MiB, Start menü 5 / 8 ms — a ZBookon (NVIDIA) ettől eltérhet.

A döntés után a választott technikával épül a teljes Fusion Desktop (a mockupok szerint): panel és
Start menü véglegesen, kétpaneles fájlkezelő, beállítások, értesítések.
