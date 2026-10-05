# T1 — Lemezkezelő és Hibajelentés (0.0.27)

A telepítő-szakasz („T”) első lépése: a telepítő ugyanerre a lemez-háttérre (`fusion-disk`) épül majd.

## Frissítés

FusionOS: Beállítások → **Rendszerfrissítés** → `fusionos-0.0.27-t1-….fupd` → **Telepítés** → **Újraindítás most**.

Minten (a build):
```bash
cd ~/Fusion
rm -rf fusionos-regi && mv fusionos fusionos-regi
tar xzf fusionos-t1.tar.gz
cp -r fusionos-regi/build/cache fusionos/build/
cd fusionos
build/fusion-build all
```
A `build/out/release/fusionos-0.0.27-t1-….fupd` fájlt másold pendrive-ra (Fájlkezelővel is jó).

## Lemezkezelő (Start → Lemezkezelő, vagy Beállítások → Rendszer → Lemezkezelő)

- Bal oldalt a lemezek; jobbra a kijelölt lemez: típus, kapcsolat, partíciós tábla, **állapot (SMART)**,
  partíciósáv (kattintható), a kijelölt partíció adatai.
- Műveletek: **Csatolás / Leválasztás / Megnyitás**, **Átnevezés…** (címke), **Formázás…**, **Partíció törlése…**,
  szabad helyen **Új partíció…**, és a teljes lemezre **Lemez formázása…** (új MBR- vagy GPT-tábla, egy partícióval
  vagy üresen), **Kiadás**.
- Minden lemezíró műveletnél a lemez nevét (pl. `sdc`) be kell gépelni.
- **Védelem:** a FusionOS saját lemeze (lakat) csak megtekinthető. Egy másik FusionOS-lemez (pl. régi pendrive)
  partíciói külön nem módosíthatók, csak a teljes lemez törölhető. Amit a rendszer máshol használ, az nem módosítható.
  EFI-partíciós lemeznél (pl. a Mint lemeze) figyelmeztetés.
- Fájlrendszerek: **FAT32** (minden eszköz, max. 4 GB-os fájl, a címke legfeljebb 11 karakter, ékezet nélkül),
  **exFAT** (pendrive-ra ajánlott), **NTFS** (Windows), **ext4** (Linux / FusionOS, a gyökérmappa a tiéd).
- Átméretezés és mozgatás szándékosan nincs.

## Hibajelentés (Beállítások → Hibajelentés)

- Hibaleírás (nem kötelező) → **Hibajelentés készítése** → `~/Letöltések/fusion-hibajelentes-<dátum>.txt`.
- Tartalom: verzió, alap, kernel, gép, grafika és driver, gyors ellenőrzés ([OK]/[FIGY]/[HIBA]), szolgáltatások,
  eszközök (USB, soros, eszközszerepek), lemezek (SMART), hálózat, A/B-állapot, programok, memória (PSS), naplók hibái.
- **Nem küld adatot sehova.** Mentés előtt maszkolás: jelszavak, kulcsok, tokenek, Wi-Fi-nevek, e-mail-címek,
  MAC-címek, sorozatszámok, nyilvános IP-címek, személyes fájlnevek (a mappa és a kiterjesztés marad). A végén:
  mit maszkolt. Megosztás előtt érdemes átolvasni (az oldalon előnézet van).
- Ha a felület nem indul: **Ctrl+Alt+F2**, bejelentkezés (fusion), majd `fusion-report -o /run/media/<pendrive>`.

## Ellenőrzés a ZBookon

- [ ] Lemezkezelő: az **sdb** (ADATA, FusionOS) lakattal, csak megtekinthető; partíciói: indítópartíció, A, B, DATA
- [ ] az **sda** (Mint): figyelmeztetés (EFI-partíció); **ne módosítsd** — csak nézd meg az állapotát (SMART)
- [ ] egy **pendrive** (amin nincs fontos adat): Lemez formázása → MBR + exFAT, címke → a Fájlkezelőben megjelenik
- [ ] ugyanott: Átnevezés, Partíció törlése, két Új partíció (pl. FAT32 + ext4), mindkettő írható
- [ ] Hibajelentés készítése egy rövid leírással → a fájl a Letöltésekben; az előnézetben nincs jelszó, Wi-Fi-név,
      e-mail-cím; a GYORS ELLENŐRZÉS sorai értelmesek
- [ ] Ctrl+Alt+F2 → bejelentkezés → `fusion-report` → a fájl a Letöltésekben (Ctrl+Alt+F1: vissza a felületre)
