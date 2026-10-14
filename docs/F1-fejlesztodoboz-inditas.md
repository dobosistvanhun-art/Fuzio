# F1 — Fejlesztődoboz és Indítás (0.0.46)

A Mint kivezetésének első lépése (terv: `claude/Mint-kivezetes-terv.md` a projektben).

## Motoros Túra Naptár a FusionOS-ben — már most megy

A Node.js és a Wrangler a FusionOS-ben a DATA-n van (M6j: Programkezelő → Fejlesztői eszközök, `fusion-dev`).
Mérve a 0.0.45 rendszerképén (chroot, a fejlesztőgépen): Node 22.23.2 + npm 10.9.8, a projektben a
`wrangler` 4.151 települ (`npm install`), a `wrangler deploy --dry-run` és a **`wrangler dev --local` D1-gyel**
(a workerd natív programja) fut — `FUSION-WORKER ok`. A Chromium (Playwright) a rendszerkép könyvtáraival elindulhat,
ez a ZBookon ellenőrizendő.

Átköltöztetés (a Mint lemeze a FusionOS-ben: Fájlkezelő → Ez a gép → a 240 GB-os lemez csatolása):

```bash
mkdir -p ~/Projektek && git clone /run/media/fusion/<a Mint kötete>/home/dobos/motoros-projekt ~/Projektek/motoros-projekt
cd ~/Projektek/motoros-projekt && npm ci && npx wrangler login && npx wrangler whoami
```

## Fejlesztődoboz

Programkezelő → **Fejlesztődoboz** → Létrehozás (egyszer; internet kell, ~1 GB) → **Megnyitás (terminál)**,
vagy a Terminálban: `fusion-dev box`.

- Ubuntu 24.04 alaprendszer a DATA-n (`/data/dev/box`, debootstrap), benne **apt**: `sudo apt install …`
  (a dobozon belül a rendszergazda jelszó nélkül sudo-zhat). A FusionOS rendszerképe nem változik.
- systemd-nspawn: a **saját mappa közös** (ugyanazok a fájlok), közös hálózat, az X kijelző és a `/dev/kvm` átadva.
- Egyszerre egy példány fut (egy terminálban); `exit` → kilépés.
- `fusion-dev box run <parancs>` — egy parancs a dobozban, az aktuális mappában.
- Törlés: Programkezelő → Törlés… (a saját mappa megmarad), vagy `fusion-dev box remove`.

**A FusionOS buildje a dobozban** (a forrás pl. `~/Projektek/fusionos`, a `build/cache` a Mintről: `fusion-build
cache-export` → `cache-import`):

```bash
fusion-dev box
cd ~/Projektek/fusionos && build/fusion-build deps --install && build/fusion-build all
```

Az eredmény (`build/out/release/fusionos-….fupd`) → Beállítások → Rendszerfrissítés. A QEMU-teszt (`build/fusion-build
test`) a dobozban KVM-mel fut.

## Indítás (Beállítások → Indítás)

A gép UEFI-bejegyzései (F9 menü): mire mutatnak (lemez, fájl), melyik indult most, melyik az alapértelmezett,
melyik **elárvult** (a lemez vagy a fájl már nincs meg). Műveletek: **Legyen ez az alapértelmezett**, **Csak a
következő indításkor**, **Törlés** (a bejegyzés nevét be kell gépelni). Nem törölhető: a most futó rendszer, a gép
saját (lemez nélküli) bejegyzései, és a „Fusion meres - …” bejegyzések (azokat a FusionOS minden induláskor maga
igazítja a véglegesített rendszerhez). Parancssor: `sudo fusion-admin boot list` (a `fusion-bootentries`).

## Ellenőrzés a ZBookon

- [ ] Beállítások → Indítás: ubuntu (ALAPÉRTELMEZETT), FusionOS (MOST FUT), a három mérési bejegyzés; elárvult nincs
- [ ] FusionOS → „Legyen ez az alapértelmezett” → újraindítás F9 nélkül → FusionOS indul; vissza: ubuntu → alapértelmezett
- [ ] Programkezelő → Node.js telepítése → a motoros projekt klónozása a Mint lemezéről → `npm ci` → `npx wrangler dev`
      → a böngészőben `http://localhost:8787` → `npx wrangler login` (Firefox) → `npx wrangler deploy`
- [ ] Ha vannak Playwright-tesztek: `npx playwright install chromium && npx playwright test`
- [ ] Programkezelő → Fejlesztődoboz → Létrehozás (idő?) → Megnyitás → `sudo apt install -y htop && htop`
- [ ] A dobozban: `cd ~/Projektek/fusionos && build/fusion-build deps --install && build/fusion-build all` (idő a Minthez képest?)
