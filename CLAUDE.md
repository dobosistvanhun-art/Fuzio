# Fúzió — útmutató a Claude-nak (Claude Code / FusionAI)

Ezt a fájlt a Claude Code minden munkamenet elején magától beolvassa. A claude.ai-os beszélgetések és a
projektdokumentumok ide nem látnak be: ami tartósan fontos, az ide vagy a `docs/` alá kerül.

## A felhasználó
- István (a gép: HP ZBook 15 G2, Quadro K1100M, NVIDIA 470). **Mindig magyarul válaszolj.**
- Közvetlen, teljes megoldást kér; a végén sorban, pontos parancsokkal: mi a következő lépés.
- **A Tab billentyűje nem működik** — semmilyen funkció ne épüljön a Tabra.
- Csak azt állítsd, amit ténylegesen lefuttattál / ellenőriztél; ami a ZBookon még nincs kipróbálva, azt mondd ki.

## A projekt
- Saját rendszer Ubuntu 24.04 (noble) alapon; a Linux kernel csak driveralap. Korábbi neve FusionOS
  (a parancsok, a `fusion-…` nevek és a `fusion` felhasználó maradnak). A forrás a ZBookon: `~/Projektek/fusionos`.
- A **SolidCraft** és a **Motoros Túra Naptár** (Wrangler / Cloudflare) külön projekt — ne keverd ide.
- Felület: Qt 6 / QML + Python (PyQt6), a közös `FusionUI` modullal (`desktop/qml/FusionUI`, `desktop/lib/fusion_ui.py`).
  Program = `desktop/<név>/fusion_<név>_app.py` + `qml/`; bejegyzés: `desktop/apps.json`; a képbe: `rootfs/customize.sh`
  (a másolási lista, a chmod-lista, `ln -sf … /usr/bin/fusion-<név>`). A QML csak felület, a műveletet a háttér végzi.
- A Fúzió API: a `fusion` Python-csomag (`desktop/lib/fusion`), leírás: `docs/api/`. D-Bus-szolgáltatás egyelőre nincs.
- A rendszerkép (`/usr`) **csak olvasható** (A/B frissítés): apt a futó rendszerben nincs. Rendszerösszetevő →
  `rootfs/packages.list`; fejlesztői eszköz → `fusion-dev` (root nélkül); fordítás → Fejlesztődoboz:
  `fusion-dev box run <parancs>` (Ubuntu 24.04, apt-tal, a saját mappa közös).
- Root csak a szűk jogú `fusion-admin` segéden át (`sudo -n /usr/lib/fusion/bin/fusion-admin …`).
- X11 + JWM (a Wayland a 470-es meghajtóval nem járható). Grafika: NVIDIA 470 / Kepler.

## Nem módosítható / óvatosan
- **A Klipper-csomag (Klipper, Moonraker, Fluidd/Mainsail, nginx) és a LightBurn nem módosul** (István döntése).
- A Firefoxot (Flatpak) nem piszkáljuk.
- A Hardware Layer általános marad (nincs „ha ZBook / ha VirtualBox, akkor…” logika).

## Változtatás menete
- Kis lépések; minden változtatásnál: mely fájlok, miért, milyen teszt futott, mi maradt ellenőrizetlen, hogyan
  vonható vissza.
- Új változat: `VERSION` (`FUSION_VERSION=0.0.N`) + egy sor a `README.md` változatlistájának tetejére
  (`- **0.0.N (mérföldkő)**: …`); nagyobb témához ellenőrzési leírás: `docs/<kód>-<téma>.md`.
- A programok öntesztje: `<program> --selftest` (QEMU-ban és a ZBookon is fut).
- Commit és push **csak István kifejezett kérésére**. Commit-üzenet: magyarul, `0.0.N (mérföldkő): rövid összefoglaló`.
- A nem commitolt munkát soha ne dobd el (reset --hard, checkout --, clean, stash drop).

## Átadás a webes Claude-nak (claude.ai)
A claude.ai-os beszélgetések a GitHubról látják a repót, a helyi munkameneteket nem. Ezért egy munka végén
(ha István kéri a commitot) frissítsd a `docs/ATADAS.md`-t: dátum, mi készült (fájlok, commit), mi lett kipróbálva
és hogyan, mi maradt nyitva / ellenőrizetlen, döntések, amiket István hozott. Rövid, a legfrissebb bejegyzés felül;
a régieket 10 bejegyzés fölött tömörítsd.

## Build és frissítés (a ZBookon)
```sh
cd ~/Projektek/fusionos && git pull
build/fusion-build fetch
build/fusion-build all          # → .fupd; telepítés: Beállítások → Rendszerfrissítés
```

## Fontos dokumentumok
- `docs/` — mérföldkövenként az ellenőrzési leírások és döntések (pl. `docs/W3-fusionai.md`: a FusionAI).
- `README.md` — állapot és változatlista.
