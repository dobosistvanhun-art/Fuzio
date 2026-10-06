# T2 — Telepítő pendrive és Fusion Telepítő (0.0.28)

Terv: `claude/Telepito-terv.md` (projekt). A telepítő pendrive ugyanazt a FusionOS-t indítja **telepítő módban**:
a rendszerkép a pendrive-ról, az írható réteg a memóriában — a pendrive-ra nem ír, többször használható.
Internet nem kell.

## 1. Build (Mint)

```bash
cd ~/Fusion
rm -rf fusionos-regi && mv fusionos fusionos-regi
tar xzf fusionos-t2.tar.gz
cp -r fusionos-regi/build/cache fusionos/build/
cd fusionos
build/fusion-build all
```
A build végén két új fájl: `build/out/release/fusionos-telepito.img` (a telepítő, ~2,4 GB) és — mint eddig — a `.fupd`.

## 2. Frissítés (a mostani FusionOS-en, ahogy eddig)

A `.fupd` → pendrive → Beállítások → Rendszerfrissítés → Telepítés → Újraindítás most.

## 3. Telepítő pendrive (Mint) — legalább 4 GB-os pendrive, a tartalma törlődik

```bash
lsblk -d -o NAME,TRAN,SIZE,MODEL          # melyik a pendrive? (TRAN = usb)
sudo build/fusion-build installer /dev/sdX
```
A pendrive-on egy **FUSIONINST** kötet is látszik (Windowson / Macen is): rajta a `.fupd` (kicserélhető egy
újabbra — egyszerre csak egy legyen ott), az `esp-static.tar` és a `hibajelentes` mappa.

## 4. Használat

F9 (boot menü) → a pendrive → **FusionOS telepítő**:
1. Üdvözlés — a telepítendő verzió, a gép; ha akkuról megy, figyelmeztet (csatlakoztasd a töltőt).
2. Céllemez — a lemezek a tartalmukkal (FusionOS + DATA foglaltsága / másik rendszer / üres); a telepítő pendrive nem választható.
3. Mód — **Újratelepítés, a DATA megőrzésével** (csak FusionOS-lemezen) vagy **Új telepítés** (a lemez törlődik).
4. Megerősítés — a lemez nevét be kell gépelni.
5. Telepítés — folyamatjelző, napló; a végén: vedd ki a pendrive-ot → Újraindítás.

Belső lemezre UEFI-bejegyzés is készül „FusionOS” néven; a mostani alapértelmezett (a ZBookon a Mint) marad
elöl, a FusionOS F9-cel választható — mint eddig. Hiba esetén: „Hibajelentés a pendrive-ra”.

## 5. Ellenőrzés a ZBookon — sorrendben

- [ ] a telepítő elindul (F9 → pendrive): a kijelző, egér, billentyűzet rendben; a Céllemez listán a Mint (sda)
      „másik operációs rendszer”, az ADATA (sdb) „FusionOS 0.0.27 — DATA: … foglalt”
- [ ] **új telepítés egy másik pendrive-ra** (legalább 16 GB, a tartalma törlődik) — NEM az sdb-re → F9 → arról a
      FusionOS elindul (üres DATA: Wi-Fi-t újra kell adni)
- [ ] csak ezután, mentéssel: **újratelepítés az sdb-re a DATA megőrzésével** — előtte a Minten mentsd a DATA-t:
      ```bash
      sudo mkdir -p /mnt/fdata && sudo mount -o ro /dev/disk/by-partlabel/FUSION_DATA /mnt/fdata
      sudo rsync -aHAX --info=progress2 /mnt/fdata/ ~/fusion-data-mentes/
      sudo umount /mnt/fdata
      ```
      (ha a telepítő pendrive is be van dugva, a `by-partlabel` a belső lemez DATA-ját adja — a pendrive-on nincs ilyen)
      → telepítő → sdb → Újratelepítés, a DATA megőrzésével → a FusionOS elindul, a LightBurn, a Wi-Fi és a
      beállítások megvannak; a Beállítások → Rendszer verziója 0.0.28
