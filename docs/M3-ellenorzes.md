# M3 — ellenőrzőlista (eszközréteg)

Az M3 kapuja: a ZBookon a lézer és a 3D nyomtató vezérlője stabil néven jelenik meg
(`/dev/fusion/laser`, `/dev/fusion/printer`), a `fusion` felhasználó root nélkül
megnyitja őket, és kihúzás–visszadugás után ugyanazzal a névvel térnek vissza.

## Előkészítés (Mint)

```bash
cd ~/Fusion
rm -rf fusionos-m2b && mv fusionos fusionos-m2c
tar xzf fusionos-m3.tar.gz
cp -r fusionos-m2c/build/cache fusionos/build/
cd fusionos
build/fusion-build all      # új letöltés: linux-modules-extra (~110 MB, egyszer)
sudo umount /media/$USER/FUSION_* 2>/dev/null; sudo build/fusion-build usb /dev/sdc
```

## A) Első indítás a ZBookon

1. A lézert (CH340) dugd a **szokásos USB-portjába** (a Minten is ez volt: port 2),
   a Klipper-alaplapot (CP2102) bármelyik portba.
2. Indítás a pendrive-ról (F9). A Desktop terminálja a hardverprofil alatt kiírja az
   eszközöket is (`fusion-devices`). Elvárt:
   - [ ] `Lézer (GRBL) (laser)` → `csatlakoztatva: /dev/fusion/laser -> ttyUSB…`, `Windows: COM3`
   - [ ] `3D nyomtató (Klipper) (printer)` → `csatlakoztatva: /dev/fusion/printer -> ttyUSB…`
3. A hozzárendelés megmarad (az első bedugáskor automatikusan jött létre):
   ```bash
   cat /etc/fusion/devices.conf
   ```
   - [ ] `laser path:1a86:7523:pci-…` (port szerint — a CH340-nek nincs sorozatszáma)
   - [ ] `printer serial:10c4:ea60:…` (sorozatszám szerint)

## B) Megnyitás root nélkül

GRBL állapotlekérdezés (a gép nem mozdul, csak az állapotát írja ki):
```bash
stty -F /dev/fusion/laser 115200 raw -echo
( sleep 2; printf '?' > /dev/fusion/laser ) & timeout 4 cat /dev/fusion/laser
```
- [ ] a válaszban `Grbl 1.1…` és/vagy `<Idle|MPos:…>` látszik

Nyomtató (csak megnyitás — a Klipper az M5-ben jön):
```bash
sh -c 'exec 3<>/dev/fusion/printer' && echo "nyomtató: megnyitható"
```
- [ ] `nyomtató: megnyitható`

## C) Kihúzás és visszadugás

1. Húzd ki a lézert → `ls /dev/fusion/` → a `laser` eltűnik.
2. Dugd vissza **ugyanabba a portba** → `fusion-devices`:
   - [ ] a lézer ugyanúgy `csatlakoztatva: /dev/fusion/laser`, a B) próba újra működik
3. Ugyanez a nyomtatóval — **másik portba** dugva is:
   - [ ] a nyomtató `csatlakoztatva: /dev/fusion/printer` (a sorozatszám azonosítja)

## D) A lézer másik portban (opcionális)

1. Dugd a lézert egy másik portba → `fusion-devices`: a `laser` „nincs csatlakoztatva”,
   lent a „Szerep nélküli soros eszközök” között ott a CH340 (`ttyUSB…`).
2. Áthelyezés: `sudo fusion-devices assign laser ttyUSB0` (a kiírt névvel)
   - [ ] `/dev/fusion/laser` azonnal megjelenik; ezentúl ez a port a lézeré

Visszajelzésnek a `fusion-devices` kimenete és a B) próba fotója elég.
