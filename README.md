# FusionOS

Saját felhasználói és rendszerabsztrakcióval rendelkező operációs rendszer.
A Linux kernel itt infrastruktúra és driver-alap, nem a FusionOS identitása.
Célgép: HP ZBook 15 G2 (Quadro K1100M, diszkrét mód).

**Állapot: M0 — build-környezet és bootolható pendrive / VirtualBox-image.**

## Az M0 célja

Bizonyítani, hogy ugyanabból a buildből:

- a **VirtualBox** EFI-ből elindítja a Fusion image-et, és
- a ZBook a **16 GB-os pendrive-ról** (F9 boot menü) ugyanígy bootol,

majd a systemd-boot betölti a Fusion UKI-t, a kernel elindul, a **Fusion Hardware Layer**
azonosítja a grafikus hardvert, és a rendszer megtalálja a négy FusionOS partíciót.
Az M0 semmit nem ír a lemezekre, és nem módosítja a Mintet.

## Gyors kezdés (a ZBookon, a Linux Mintben)

```bash
# 1. függőségek (egyszer)
build/fusion-build deps            # ellenőrzés
build/fusion-build deps --install  # vagy: telepítés sudo-val

# 2. build (root nélkül)
build/fusion-build all             # letöltés + initramfs + UKI + lemezkép + VDI

# 3a. VirtualBox
build/fusion-build vm              # FusionOS-dev VM létrehozása / lemezcsere
build/fusion-build vm-start

# 3b. pendrive (a TELJES pendrive törlődik!)
lsblk -d -o NAME,TRAN,SIZE,MODEL   # melyik a pendrive? (TRAN = usb)
sudo build/fusion-build usb /dev/sdc
```

Újraépítés után elég: `build/fusion-build all && build/fusion-build vm`.

## Parancsok

| Parancs | Mit csinál |
| --- | --- |
| `deps [--install]` | build-függőségek ellenőrzése / telepítése |
| `fetch` | Ubuntu 6.8.0-142 kernel + modulok, busybox, konzolfont letöltése (root nélkül, `apt-get download`) |
| `build` | initramfs + UKI (ukify) + ESP-fa (systemd-boot) |
| `image` | GPT lemezkép: ESP 512M, A 4G, B 4G, DATA 1G — ritka fájl, ~25 MB valós méret |
| `vdi` | lemezkép → VDI (qemu-img, tartalék: VBoxManage) |
| `vm [--usb]` | FusionOS-dev VM (EFI, 4 GB, 2 CPU, VMSVGA, soros napló); `--usb`: lézer (CH340) és nyomtató (CP2102) USB-szűrő — fejlesztői követelmény: VirtualBox Extension Pack |
| `vm-start` | a VM indítása |
| `all` | fetch + build + image + vdi |
| `test` | automatikus EFI boot-teszt QEMU + OVMF alatt: std VGA/SATA, VMware SVGA/SATA, std VGA/USB-pendrive |
| `usb <eszköz>` | felírás pendrive-ra (root) |
| `clean` | build/out törlése |

## A pendrive-író biztonsága

A `usb` lépés csak akkor ír, ha minden feltétel teljesül:

- teljes lemezt kapott (`/dev/sdc`, nem `/dev/sdc1`);
- az eszköz **USB-n** csatlakozik (belső SATA/NVMe lemezt elutasít);
- a mérete 10–256 GiB között van;
- nincs rajta a futó rendszer egyetlen része sem (`/`, `/boot`, `/home` …);
- a felhasználó **begépeli az eszköz nevét** megerősítésként.

Az ESP-re csatolás nélkül ír (mtools), így nem ütközik a Mint automatikus csatolásával.

## Lemezelrendezés

| Partíció (GPT név) | Pendrive (16 GB) | VM-image |
| --- | --- | --- |
| FUSION_ESP | 512 MiB, FAT32 | 512 MiB |
| FUSION_A | 4 GiB (az M1-től rendszerkép) | 4 GiB |
| FUSION_B | 4 GiB (az M1-től rendszerkép) | 4 GiB |
| FUSION_DATA | a maradék (~6,5 GiB), ext4 | 1 GiB |

A rendszer a partíciókat **GPT név szerint** keresi, nem eszköznév szerint
(a `/dev/sdc` bedugásonként változhat).

## Fusion Hardware Layer

`hardware/fusion-hwprobe` + `hardware/profiles/*.profile`

Rendszerindításkor azonosítja a grafikus hardvert, és a hozzá illő profilt aktiválja.
Az azonosítás **általános és adatvezérelt**: PCI-osztály, gyártó- és eszközazonosító
alapján választ a profilok közül — a kódban nincs „ha VirtualBox, akkor…” ág.
Új hardver támogatása = új profilfájl. Ebből nő ki a Fusion Hardware API.

| Profil | Illeszkedik | Hol |
| --- | --- | --- |
| `nvidia-kepler-470` | 10de:0ff6 (Quadro K1100M) | ZBook, diszkrét mód |
| `vmware-svga` | 15ad:0405 | VirtualBox VMSVGA, QEMU `-vga vmware` |
| `virtualbox-vga` | 80ee:beef | VirtualBox VBoxVGA/VBoxSVGA |
| `intel-kms` | 8086:* | Intel iGPU (pl. ZBook hibrid módban) |
| `generic-kms` | bármely PCI grafika | tartalék |
| `firmware-fb` | nincs PCI grafika | UEFI GOP framebuffer |

Ha egy profil `requires_sole_adapter = yes` (pl. az NVIDIA 470), de több grafikus adapter
látszik (ZBook hibrid mód), az állapot `warning`, és a profil saját üzenete jelenik meg
(„kapcsold ki a Hybrid Graphics opciót”).

Kimenet: `/run/fusion/hardware/display.env` (shell-lel betölthető `KEY='érték'` sorok).

Tesztek: `sh tests/hwprobe-test.sh` (hamis sysfs-fákkal; bash és busybox sh alatt is).

## Tárolószerkezet

```
build/        fusion-build, lépések (steps/), konfiguráció (config/)
hardware/     Fusion Hardware Layer: fusion-hwprobe + profilok
initramfs/m0/ az M0 boot-teszt init
tests/        automatikus tesztek
tools/        fusion-hardware-discovery.sh (Phase 0)
docs/         M0 ellenőrzőlista
```

## Ismert korlátok (M0)

- A modulok közül csak a lemezekhez és az USB-billentyűzethez kellők vannak az initramfsben
  (ahci, xhci-pci, usb-storage, uas, usbhid). A ZBook belső billentyűzete PS/2, az beépített.
- Az NVIDIA 470 driver még nincs a rendszerben (M2). Az M0 a firmware framebufferen fut,
  a hardverprofil kiválasztása ettől függetlenül már a valódi PCI-azonosítók alapján történik.
- A `loader.conf`-ban `editor yes` — fejlesztői beállítás, a 17. pont szerint később kikapcsol.
