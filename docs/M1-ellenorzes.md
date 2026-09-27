# M1 — ellenőrzőlista

Az M1 kapuja: a ZBook és a VirtualBox is a FusionOS rendszerképről bejelentkezésig jut,
és a változások újraindítás után megmaradnak.

## Előkészítés (Mint)

```bash
cd ~/Fusion/fusionos        # az új tároló kicsomagolva ide
build/fusion-build deps --install
build/fusion-build all      # a rendszerképnél sudo jelszót kér
```

A végén: `kész: … rootfs.erofs — ~99 MiB tömörítve`.

## A) VirtualBox

1. `build/fusion-build vm && build/fusion-build vm-start`
2. Elvárt:
   - [ ] boot menü: **FusionOS 0.0.2 (m1) — A** és **FusionOS diagnosztika**
   - [ ] rövid indulás után: `FusionOS 0.0.2 — fusionos (tty1)` és `fusionos login:`
   - [ ] belépés: `fusion` / `fusion`
   - [ ] `fusion-hwinfo` → `Profil: vmware-svga`, `Driver: betöltve (vmwgfx)`
   - [ ] magyar billentyűzet: a `z` és az `y` a magyar helyen, `ő ű á é` gépelhető
3. Megmaradás:
   ```bash
   echo "helló" > ~/proba.txt
   sudo reboot
   ```
   újraindulás és belépés után: `cat ~/proba.txt` → `helló`
4. Csak olvasható rendszer: `sudo touch /usr/proba` → `Read-only file system` (ez a helyes)
5. Kilépés: `sudo poweroff` — a leállításkor nem lehet `[FAILED]` sor

Ha a VirtualBoxban a login helyett fekete a képernyő: a VM újraindításakor a boot menüben
válaszd a **FusionOS diagnosztika** bejegyzést, és szólj — a vmwgfx driver a gyanús.

## B) ZBook (pendrive / SD-kártya USB-olvasóban)

1. `sudo build/fusion-build usb /dev/sdX`
   — a végén: `A slot: ellenőrizve (visszaolvasás egyezik)`
2. Újraindítás → **F9** → az USB-eszköz UEFI-bejegyzése.
3. Elvárt:
   - [ ] `fusionos login:` → `fusion` / `fusion`
   - [ ] `fusion-hwinfo` → `Adapter: 0000:01:00.0 10de:0ff6`, `Profil: nvidia-kepler-470`,
         `Driver: NINCS TELEPÍTVE: nvidia … — a firmware framebuffer marad`
         (ez az M1-ben a helyes állapot; az NVIDIA driver az M2-ben jön)
   - [ ] hálózat (ha van Ethernet-kábel): `ip -br addr` → az `enp0s25` kap címet; `ping -c3 1.1.1.1`
   - [ ] a „Megmaradás” próba ugyanúgy, mint a VirtualBoxban
4. Vissza a Mintbe: `sudo reboot` (a pendrive kihúzásával, vagy F9 → a belső lemez).

A képernyőről fotó vagy a `fusion-hwinfo` kimenete elég visszajelzésnek.
