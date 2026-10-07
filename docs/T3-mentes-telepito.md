# T3 — Mentés, visszaállítás, telepítő pendrive a FusionOS-ből (0.0.29)

Ezzel a Mint csak a buildhez kell: a telepítő pendrive a FusionOS-ből is elkészül, a DATA menthető és
visszaállítható.

## Frissítés (mint eddig)

Minten: a csomag kibontása és `build/fusion-build all` (lásd `docs/T2-telepito.md`), majd a `.fupd` → pendrive →
Beállítások → Rendszerfrissítés → Telepítés → Újraindítás most.
Fontos: a 0.0.29-es `.fupd` már a telepítő részeit is tartalmazza (kb. 50 MB-tal nagyobb) — ebből lehet telepítő
pendrive-ot készíteni. A régebbi `.fupd`-kből nem.

## 1. Mentés (Beállítások → Mentés)

- Dugj be egy külső lemezt vagy pendrive-ot (exFAT, NTFS vagy ext4 ajánlott; FAT32-n 3,9 GB-os darabokban ment).
- Válaszd ki a kötetet → **Mentés most**. A mentés: `FusionOS-mentes/fusion-data-<dátum>.tar.zst` (+ `.info.json`).
- Benne: a telepített programok (LightBurn, Flatpak), beállítások, Wi-Fi, Google Drive-bejelentkezés, saját fájlok,
  a nyomtató adatai. **Jelszavakat is tartalmaz — tartsd biztonságban.**
- 18 GB adat kb. 10–30 perc (a pendrive sebességétől függ); közben a gép használható.

## 2. Telepítő pendrive a FusionOS-ből (Beállítások → Rendszerfrissítés)

- A `.fupd` legyen a Letöltésekben (vagy egy másik pendrive-on — nem azon, amelyikből a telepítő lesz).
- Jelöld ki → **Telepítő pendrive készítése…** → válaszd ki a pendrive-ot (legalább 4 GB, a tartalma törlődik) →
  írd be a nevét → Készítés. Kb. 5–10 perc.

## 3. Visszaállítás (Fusion Telepítő)

- A mentést tartalmazó lemezt is dugd be. Telepítő → Céllemez → **Új telepítés** → „Visszaállítás mentésből: …”
  → Megerősítés → Telepítés. A végén a rendszer pontosan úgy indul, mint a mentéskor.
- **Wi-Fi átvétele:** ha a telepítőben a Wi-Fi gombbal csatlakozol egy hálózathoz, az új telepítés ezt is megkapja
  („A telepítőben beállított Wi-Fi átvétele”).

## Ellenőrzés a ZBookon

- [ ] Beállítások → Mentés: egy külső lemezre (vagy pendrive-ra) mentés → a „Meglévő mentések” között megjelenik
- [ ] Rendszerfrissítés → Telepítő pendrive készítése… (egy másik pendrive-ra) → F9 → arról a Fusion Telepítő elindul
- [ ] a telepítőből: **új telepítés egy pendrive-ra a mentésből** (NEM az sdb-re) → arról indítva a LightBurn, a Wi-Fi,
      a beállítások megvannak
- [ ] (opcionális) a telepítőben Wi-Fi → csatlakozás → új telepítés „Wi-Fi átvétele” → az új rendszer magától csatlakozik
