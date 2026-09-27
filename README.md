# FusionOS

Saját felhasználói és rendszerabsztrakcióval rendelkező operációs rendszer.
A Linux kernel itt infrastruktúra és driver-alap, nem a FusionOS identitása.
Célgép: HP ZBook 15 G2 (Quadro K1100M, diszkrét mód).

**Állapot: M2 — grafikus felület, NVIDIA 470.**
Az M0 (build-környezet, EFI-boot) és az M1 (bootolható alaprendszer) lezárva.

## Mit tud az M2

- A FusionOS a **Fusion Desktopra** indul: a tty1-en automatikus belépés (`fusion`),
  majd X11 + ideiglenes ablakkezelő (**JWM**, a Fusion Shell az M6-ban váltja) és egy
  terminál a hardverprofillal.
- **NVIDIA 470.256.02** (Kepler, Quadro K1100M): a kernelmodul a buildben fordul a rögzített
  kernelhez, eldobható build-chrootban; a rendszerképbe csak a kész modulok és a
  felhasználói könyvtárak (GL/GLX/EGL/Vulkan, Xorg-driver, `nvidia-smi`) kerülnek.
- A grafikus szerver beállítását a **Fusion Hardware Layer** adja a hardverprofilból:
  modulparaméterek (pl. `nvidia-drm modeset=1`), Xorg-driver, modulútvonal, Xorg root-jog.
  Virtuális gépen és ismeretlen grafikán Mesa (llvmpipe) / modesetting.
- Magyar billentyűzet a grafikus felületen is.
- Az M1 alaprendszere változatlan: csak olvasható EROFS rendszerkép, a változások a
  FUSION_DATA-ra kerülnek, magyar nyelv, hálózat, tiszta leállítás.

A kézi ellenőrzés és a nyitott döntésekhez tartozó mérések: `docs/M2-ellenorzes.md`.

Fejlesztői bejelentkezés: **fusion / fusion** (sudo joggal). A root zárolva.

## Gyors kezdés (a ZBookon, a Linux Mintben)

```bash
build/fusion-build deps --install     # egyszer (új függőség: mmdebstrap, erofs-utils)
build/fusion-build all                # először ~6–8 perc (NVIDIA modul fordítása); sudo jelszót kér

build/fusion-build vm && build/fusion-build vm-start   # VirtualBox
sudo build/fusion-build usb /dev/sdX                   # pendrive / SD-kártya USB-olvasóban
```

Ha a letöltés „Unable to locate package” hibát ad: `sudo apt update`.

## Parancsok

| Parancs | Mit csinál |
| --- | --- |
| `deps [--install]` | build-függőségek ellenőrzése / telepítése |
| `fetch` | Ubuntu 6.8.0-142 kernel + modulok, busybox, konzolfont, NVIDIA 470 csomagok (root nélkül, SHA256-tal) |
| `drivers` | NVIDIA 470 kernelmodul fordítása a rögzített kernelhez (root; az `all` magától hívja) |
| `rootfs [--force]` | a FusionOS rendszerkép (EROFS) — root kell; az `all` sudo-val hívja, ha a forrás változott |
| `build` | két initramfs + két UKI (FusionOS, diagnosztika) + ESP |
| `image` | GPT lemezkép: ESP, A slot (rendszerkép), B (üres), DATA |
| `vdi` | lemezkép → VDI |
| `vm [--usb]` | FusionOS-dev VM létrehozása / lemezcsere (`--usb`: lézer és nyomtató átadása, Extension Pack kell) |
| `vm-start` | a VM indítása |
| `all` | fetch + drivers + rootfs + build + image + vdi |
| `test` | automatikus EFI boot-teszt QEMU + OVMF alatt (lásd lent) |
| `usb <eszköz>` | felírás pendrive-ra / USB-s kártyaolvasóba (root) |
| `clean` | build/out törlése |

## Rendszerindítás

```
UEFI → systemd-boot (ESP) → UKI: kernel 6.8.0-142 + fusion-init (initramfs)
  fusion-init:
    1. lemez- és USB-modulok (ahci, xhci-pci, usb-storage, uas, erofs, overlay)
    2. slot a kernel parancssorából: fusion.slot=A
    3. FUSION_A (GPT-név szerint) → EROFS, csak olvasható → /
    4. FUSION_DATA → /data (ext4)
    5. gyökér = overlay (alul a rendszerkép, felül /data/overlay/root)
       /usr  = a rendszerkép /usr-je, csak olvasható
    6. switch_root → systemd
  systemd → fusion-hardware.service (Hardware Layer: driver + Xorg-beállítás)
          → getty@tty1 (automatikus belépés) → fusion-session → Xorg + JWM (Fusion Desktop)
```

Hiba esetén a fusion-init érthető magyar üzenettel és mentőhéjjal áll meg.

## Lemezelrendezés

| Partíció (GPT név) | Pendrive (16 GB) | VM-image | Tartalom |
| --- | --- | --- | --- |
| FUSION_ESP | 512 MiB | 512 MiB | systemd-boot, UKI-k |
| FUSION_A | 4 GiB | 4 GiB | rendszerkép (EROFS, ~100 MB) |
| FUSION_B | 4 GiB | 4 GiB | üres (A/B frissítés: M7) |
| FUSION_DATA | a maradék | 1 GiB | a gyökér írható rétege (/etc, /var, /home …) |

## A pendrive-író biztonsága

A `usb` lépés csak akkor ír, ha: teljes lemezt kapott (nem partíciót), az eszköz USB-n
csatlakozik, 10–256 GiB közötti, nincs rajta a futó rendszer, és a felhasználó begépeli
az eszköz nevét. A rendszerkép felírása után **visszaolvasással ellenőrzi** a slotot
(gyorsítótár ürítése után), így egy hibás vagy hamis kapacitású pendrive azonnal kiderül.

## Fusion Hardware Layer

`hardware/fusion-hwprobe` + `hardware/profiles/*.profile`

Általános, adatvezérelt azonosítás PCI-osztály, gyártó- és eszközazonosító alapján;
a kódban nincs gép- vagy hipervizor-specifikus ág. Új hardver = új profilfájl.

- `--apply`: a kiválasztott profil `display.kernel_modules` moduljait betölti, a
  `display.module_options` paraméterekkel (ezek a `/run/modprobe.d`-be is kerülnek), és
  ellenőrzi, hogy a driver átvette-e az eszközt.
  Állapot: `loaded` / `none` / `missing` / `failed` (nem tölthető be, vagy nem vette át az eszközt).
- Xorg-beállítás a profilból: `display.xorg_driver`, `display.xorg_module_path`,
  `display.xorg_root_rights` → `/run/fusion/hardware/xorg-display.conf`, `Xwrapper.config`.
- Kernel parancssori felülírás (mérésekhez): `<modul>.<param>=…` (pl. `nvidia-drm.modeset=0`),
  `fusion.xorg.root=yes|no|auto`, `fusion.desktop=0` (nincs grafikus felület).
- `--status` / `fusion-hwinfo`: a legutóbbi eredmény emberi nyelven.
- A kijelződriverek udev-es automatikus betöltése tiltva (`/etc/modprobe.d/fusion-display.conf`).

| Profil | Illeszkedik | Driver |
| --- | --- | --- |
| `nvidia-kepler-470` | 10de:0ff6 (Quadro K1100M) | nvidia 470 (+ nvidia-drm modeset=1), Xorg: nvidia |
| `vmware-svga` | 15ad:0405 (VirtualBox VMSVGA) | vmwgfx, Xorg: modesetting |
| `virtualbox-vga` | 80ee:beef | vboxvideo |
| `intel-kms` | 8086:* | i915 |
| `generic-kms` | bármely PCI grafika | — (firmware framebuffer) |
| `firmware-fb` | nincs PCI grafika | — |

Tesztek: `sh tests/hwprobe-test.sh` (29 eset, hamis sysfs-sel, modulkezelővel és kernel parancssorral).

## Automatikus teszt (`build/fusion-build test`)

QEMU + OVMF, KVM nélkül is (lassabb). A FusionOS-t háromféleképp indítja
(std VGA + SATA, VMware SVGA + SATA, std VGA + USB-pendrive), és a soros konzolon ellenőrzi:
systemd „running”, gyökér-overlay, /usr csak olvasható (EROFS), /data ext4, A slot,
hardverprofil és driver, getty, magyar locale és billentyűzet, `fusion` felhasználó,
machine-id, nincs hibás szolgáltatás; std VGA-n a Fusion Desktopot is (Xorg, OpenGL,
ablakkezelő, magyar kiosztás az X-ben). Ezen felül a diagnosztikai bejegyzést is elindítja.

Megjegyzés: QEMU `-vga vmware` alatt a vmwgfx nem veszi át az eszközt („unsupported
hypervisor”) — a Hardware Layer ezt `failed`-ként jelzi, és ott a teszt grafikus felületet
nem vár. A VMSVGA támogatott környezete a VirtualBox.

## Tárolószerkezet

```
build/        fusion-build, lépések (steps/), konfiguráció (config/)
rootfs/       a rendszerkép: csomaglista, testreszabás, FusionOS fájlok (overlay/)
hardware/     Fusion Hardware Layer: fusion-hwprobe + profilok
initramfs/    fusion/init (FusionOS), m0/init (diagnosztika)
tests/        automatikus tesztek
tools/        fusion-hardware-discovery.sh (Phase 0)
docs/         ellenőrzőlisták
```

## Ismert korlátok (M2)

- Nyitott, mérésre váró döntések (`docs/M2-ellenorzes.md`, C): `nvidia-drm.modeset` (most: 1),
  az Xorg root-joga NVIDIA-n (most: yes).
- A JWM ideiglenes; a Fusion Shell az M6-ban jön. Nincs Wi-Fi (később).
- NVIDIA csomagforrás: a `470-server` sorozat (a sima `-470` a noble-updates-ben már a
  535-ös driverre mutató átmeneti csomag, az nem támogatja a Keplert).
- A DATA fájlrendszer-ellenőrzése (fsck) még nincs az initramfs-ben.
- A gyökér-overlay felső rétegének frissítéskori kezelése: M7 (A/B frissítés).
- `loader.conf`: `editor yes` — fejlesztői beállítás, később kikapcsol.
