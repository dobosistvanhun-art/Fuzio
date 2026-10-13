# FusionOS 0.0.43 (j10) — videófelvétel, felhasználókezelés, apt-vizsgálat

## Kamera: videófelvétel

- **Videó** gomb (vagy R): felvétel indítása / leállítása. Futás közben piros „FELVÉTEL 00:12” jelzés az élőképen.
- **hanggal** jelölő: a mikrofon hangja is rákerül (ha van mikrofon; ha nincs, hang nélkül rögzít).
- A videók a Videók mappába kerülnek: `~/Videók/Kamera-ÉÉÉÉHHNN-ÓÓPPMM.mp4` (H.264 + AAC, bármely lejátszó lejátssza).
- Bezáráskor a futó felvétel lezárul.
- Miért saját: a Qt 6.4 beépített rögzítője üres fájlt ír (mérés, QEMU: 44–48 bájt, MP4-ben és MKV-ban is).
  Ezért a FusionOS az élőkép képkockáit (ugyanazokat, amelyeket az ablak mutat) adja át az `ffmpeg`-nek, állandó
  30 kép/mp-es ütemben. A kamerát így nem kell kétszer megnyitni, az élőkép a felvétel alatt is látszik, a videó
  hossza pedig a valós idő.

## Felhasználók (Beállítások → Felhasználók)

- **fusion / fusion marad**, mint eddig: nem törölhető, a jelszava és a jogai innen nem módosíthatók, és alapból ő lép
  be automatikusan.
- Új felhasználó: név, teljes név, jelszó, rendszergazda igen / nem. Saját mappát és saját beállításokat kap.
  - **Rendszergazda**: programtelepítés, rendszerfrissítés, lemezek, felhasználók, nyomtatók.
  - **Felhasználó**: a mindennapi dolgok — pendrive csatolása, kikapcsolás, Wi-Fi, Bluetooth, a saját jelszava.
    A rendszerműveleteket a `fusion-admin` megtagadja tőle.
- Jelszócsere: a sajáthoz a régi jelszó kell; rendszergazda más jelszavát régi nélkül cseréli.
- **Automatikus belépés**: választható felhasználó, vagy „Jelszóval lépjen be” (a tty1-en felhasználónév + jelszó).
  A következő indítástól érvényes.
- **Rendszerfrissítés után is megmaradnak.** A felhasználó-adatbázis frissítéskor a rendszerképé lesz, ezért a
  felvett felhasználók a DATA-n is tárolódnak (`/data/system/users.json`, csak root olvassa, a jelszó csak hash-ként),
  és indításkor a `fusion-users.service` ugyanazzal az azonosítóval visszaállítja őket.
- Tudnivaló: a programok (LightBurn, Flatpak-programok) a telepítő felhasználóé; egy új felhasználó a sajátjait
  telepíti. A pendrive-ok a FusionOS saját Fájlkezelőjében minden felhasználónak látszanak.
- Parancssor: `fusion users`, `sudo fusion-admin users …`.

## apt — kell-e?

**Nem kell, és most nem is tenném bele.** Indok:

- A rendszer `/usr` része csak olvasható (EROFS-kép, A/B frissítés). Az apt a csomagokat oda telepítené, tehát a futó
  rendszerben nem tud működni; a build szándékosan el is távolítja (`customize.sh`).
- Ha működne is, egy kézzel telepített csomag a következő rendszerfrissítéssel eltűnne vagy ütközne. Ez éppen a
  visszaállítható, kiszámítható frissítést rontaná el.
- Minden, amire eddig szükség volt, megvan más úton:
  - **programok** → Programkezelő / Programbolt (Flatpak, AppImage, Windows-programok);
  - **rendszerösszetevő** (pl. CUPS, Bluetooth, ffmpeg) → a rendszerképbe kerül (`rootfs/packages.list`), a
    következő `.fupd` frissítéssel;
  - **fejlesztői eszközök** → `fusion-dev` (Node.js, Wrangler a `/data/dev` alatt).
- Ha egyszer mégis kell egy csomag gyorsan, kipróbálásra: egy terminálban futó, eldobható Ubuntu-konténer
  (pl. `distrobox`) adható hozzá, ami a rendszert nem érinti. Ezt csak igény esetén, külön döntéssel.

## Ellenőrzés a ZBookon

1. Kamera → Videó → 10 mp beszéd → Leállítás → a Videók mappában lejátszható, hanggal?
2. Beállítások → Felhasználók → Új felhasználó (pl. „proba”, nem rendszergazda) → Automatikus belépés: proba →
   újraindítás → proba asztala jön? Utána vissza: fusion → Automatikus belépés.
3. Ha végeztél: proba törlése.
