# M2 — ellenőrzőlista

Az M2 kapuja: a ZBookon a FusionOS a **Fusion Desktopra** (grafikus felület) indul,
és az NVIDIA 470 driverrel a Quadro K1100M teljes gyorsítást ad:
**OpenGL 4.6** és **Vulkan 1.2**.

## Előkészítés (Mint)

```bash
cd ~/Fusion/fusionos        # az új csomag kicsomagolva ide (a build/cache-t érdemes megtartani)
build/fusion-build deps --install     # új függőség: curl, binutils
build/fusion-build all
```

Az `all` most két helyen kér sudo jelszót:
- **NVIDIA kernelmodul fordítása** (csak először, ~3–6 perc): `kész: …/drivers/nvidia-470.256.02-6.8.0-142-generic`
- **rendszerkép**: `kész: … rootfs.erofs — ~300–400 MiB tömörítve`

A letöltés ~250 MB (NVIDIA csomagok), a gazdagép apt-jától független.

## A) VirtualBox

1. `build/fusion-build vm && build/fusion-build vm-start`
2. Elvárt:
   - [ ] rövid indulás után **magától** megjelenik a Fusion Desktop: sötétkék háttér,
         alul a JWM tálcája, egy „FusionOS” terminálablak a hardverprofillal
   - [ ] a terminálban: `Profil: vmware-svga`, `Driver: betöltve (vmwgfx)`,
         `Xorg: driver=modesetting root=auto`
   - [ ] `glxinfo -B` → `OpenGL renderer string: llvmpipe …` (szoftveres; a VM-ben ez a helyes)
   - [ ] magyar billentyűzet a terminálban: `ő ű á é`, a `z` és az `y` a helyén
3. Kilépés: `sudo poweroff` — nincs `[FAILED]`

## B) ZBook (pendrive / SD-kártya USB-olvasóban)

1. `sudo umount /media/$USER/FUSION_* 2>/dev/null; sudo build/fusion-build usb /dev/sdX`
2. Újraindítás → **F9** → az USB-eszköz.
3. Elvárt:
   - [ ] a Fusion Desktop magától elindul (a kijelző natív felbontásában)
   - [ ] a terminálban (`fusion-hwinfo`):
         `Profil: nvidia-kepler-470`,
         `Driver: betöltve (nvidia nvidia-modeset nvidia-drm)`,
         `Paraméter: nvidia_drm.modeset=Y`,
         `Xorg: driver=nvidia root=yes`
   - [ ] `glxinfo -B` →
         `OpenGL renderer string: Quadro K1100M/PCIe/SSE2`,
         `OpenGL core profile version string: 4.6.0 NVIDIA 470.256.02`
   - [ ] `vulkaninfo --summary | grep -iE 'devicename|apiversion'` → `Quadro K1100M`, `1.2.…`
   - [ ] `nvidia-smi` → a kártya, a driver 470.256.02
   - [ ] `sudo cat /sys/module/nvidia_drm/parameters/modeset` → `Y`

A fenti kimenetek fotója vagy szövege elég visszajelzésnek.

## C) Mérések a nyitott döntésekhez (a ZBookon)

Két beállítás tesztadat nélkül nincs véglegesítve. Mindkettőhöz kész bejegyzés van a
boot menüben (nyilakkal kiválasztható, nem kell a parancssort szerkeszteni):

| Próba | Boot menü bejegyzés | Mit nézz |
| --- | --- | --- |
| C1 — KMS nélkül | **FusionOS — mérés: KMS nélkül** | elindul-e a Desktop; `sudo cat /sys/module/nvidia_drm/parameters/modeset` → `N`; `glxinfo -B \| grep renderer` |
| C2 — Xorg root nélkül | **FusionOS — mérés: Xorg root-jog nélkül** | elindul-e a Desktop; `ps -o user= -C Xorg` → `fusion` vagy `root`; `glxinfo -B \| grep renderer` |

Minden próbánál először: `cat /proc/cmdline` — a sor végén ott kell lennie a próba elemének.

Ha valamelyik próbánál a Desktop nem jön fel: **Ctrl+Alt+F2** → belépés (`fusion`/`fusion`),
és a napló: `tail -n 30 ~/.local/share/fusion/session.log` és
`grep EE /var/log/Xorg.0.log ~/.local/share/xorg/Xorg.0.log`.

Megjegyzés: a boot menü szerkesztője (`e`) UEFI alatt amerikai kiosztású — magyar
billentyűzeten az `=` az `ó` billentyű. A kész bejegyzésekkel erre nincs szükség.

## Hasznos tudnivalók

- Szöveges konzol a Desktop nélkül: a boot menüben **FusionOS — szöveges konzol**.
- Ha a Desktop kilép, a tty1-en a konzol marad; újraindítás: `fusion-session`.
- A többi konzol (Ctrl+Alt+F2 …) jelszót kér.
