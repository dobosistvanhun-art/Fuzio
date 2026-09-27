# M0 — ellenőrzőlista a ZBookon

Az M0 kapuja: a ZBook F9 boot menüjéből a pendrive elindul, és a Fusion UKI lefut.

## A) VirtualBox (gyors próba)

1. `build/fusion-build all && build/fusion-build vm && build/fusion-build vm-start`
2. Elvárt:
   - [ ] systemd-boot menü: **FusionOS 0.0.1 (m0)**, 5 mp után magától indul
   - [ ] a képernyőn: `Rendszerindítás: UEFI (64-bit)`, `Bootloader: systemd-boot …`
   - [ ] `Profil: vmware-svga` (a VirtualBox VMSVGA adaptere), `Állapot: ok`
   - [ ] mind a 4 partíció megvan (`FUSION-M0: PARTITIONS 4/4`)
   - [ ] a magyar ékezetek helyesek (Á, í, ú …)
3. Kilépés: `k` + Enter (kikapcsolás).

## B) ZBook, pendrive

1. `sudo build/fusion-build usb /dev/sdX` (a pendrive neve: `lsblk -d -o NAME,TRAN,SIZE,MODEL`)
2. Újraindítás → **F9** → a pendrive UEFI-bejegyzése.
3. Elvárt:
   - [ ] systemd-boot menü: **FusionOS 0.0.1 (m0)**
   - [ ] `Gép: Hewlett-Packard HP ZBook 15 G2`
   - [ ] `Adapter: 0000:01:00.0  10de:0ff6` → `Profil: nvidia-kepler-470`, `Állapot: ok`
         (hibrid módban `warning` + a Hybrid Graphics üzenet — ez is helyes viselkedés)
   - [ ] mind a 4 partíció megvan, a DATA ~6,5 GiB
   - [ ] a belső billentyűzet működik (Enter → parancssor, `exit` → vissza)
4. Kilépés: `u` (újraindítás vissza a Mintbe) vagy `k` (kikapcsolás).

Ha a gép nem ajánlja fel a pendrive-ot: BIOS (F10) → Advanced → Boot Options →
**USB Boot** engedélyezve, **Legacy Support** kikapcsolva (UEFI).

A képernyőről egy fotó elég visszajelzésnek.
