# FusionOS

Saját felhasználói és rendszerabsztrakcióval rendelkező operációs rendszer.
A Linux kernel itt infrastruktúra és driver-alap, nem a FusionOS identitása.
Célgép: HP ZBook 15 G2 (Quadro K1100M, diszkrét mód).

**Állapot: M1 — bootolható alaprendszer.**
Az M0 (build-környezet, EFI-boot pendrive-ról és VirtualBoxból) lezárva.

## Mit tud az M1

- A boot menüben két bejegyzés van:
  - **FusionOS 0.0.2 (m1) — A**: az alapértelmezett, 5 mp után magától indul;
  - **FusionOS diagnosztika**: az M0 ellenőrző képernyője (hardver, partíciók). Nem ír semmit.
- A FusionOS az **A slot** rendszerképéről indul: minimális Ubuntu 24.04 alap,
  **csak olvasható, tömörített EROFS** (~100 MB), systemd-vel, bejelentkezésig.
- Minden változás a **FUSION_DATA** partícióra kerül: a gyökér egyetlen overlay
  (alul a rendszerkép, felül a DATA), így az `/etc`, a `/var` és a `/home` írható, és
  újraindítás után megmarad. A `/usr` közvetlenül a rendszerkép: **csak olvasható**.
- Tiszta leállítás: a DATA fájlrendszert a rendszer a legvégén zárja le.
- Magyar nyelv (hu_HU.UTF-8), magyar billentyűzet, Europe/Budapest időzóna.
- Vezetékes hálózat DHCP-vel (systemd-networkd).
- A **Fusion Hardware Layer** a bootnál kiválasztja a grafikus profilt, és a profil
  szerint tölti be a kijelződrivert (az udev automatikus driverbetöltése tiltva).
- Nincs csomagkezelő a rendszeren: a rendszer a buildből jön, egészben.

Fejlesztői bejelentkezés: **fusion / fusion** (sudo joggal). A root zárolva.

## Gyors kezdés (a ZBookon, a Linux Mintben)

```bash
build/fusion-build deps --install     # egyszer (új függőség: mmdebstrap, erofs-utils)
build/fusion-build all                # ~1,5 perc; a rendszerképhez sudo jelszót kér

build/fusion-build vm && build/fusion-build vm-start   # VirtualBox
sudo build/fusion-build usb /dev/sdX                   # pendrive / SD-kártya USB-olvasóban
```

Ha a letöltés „Unable to locate package” hibát ad: `sudo apt update`.

## Parancsok

| Parancs | Mit csinál |
| --- | --- |
| `deps [--install]` | build-függőségek ellenőrzése / telepítése |
| `fetch` | Ubuntu 6.8.0-142 kernel + modulok, busybox, konzolfont (root nélkül) |
| `rootfs [--force]` | a FusionOS rendszerkép (EROFS) — root kell; az `all` sudo-val hívja, ha a forrás változott |
| `build` | két initramfs + két UKI (FusionOS, diagnosztika) + ESP |
| `image` | GPT lemezkép: ESP, A slot (rendszerkép), B (üres), DATA |
| `vdi` | lemezkép → VDI |
| `vm [--usb]` | FusionOS-dev VM létrehozása / lemezcsere (`--usb`: lézer és nyomtató átadása, Extension Pack kell) |
| `vm-start` | a VM indítása |
| `all` | fetch + rootfs + build + image + vdi |
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
  systemd → fusion-hardware.service (Hardware Layer) → getty (bejelentkezés)
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

- `--apply`: a kiválasztott profil `display.kernel_modules` moduljait betölti.
  Állapot: `loaded` / `none` / `missing` (pl. az NVIDIA driver az M2 előtt) / `failed`.
- `--status` / `fusion-hwinfo`: a legutóbbi eredmény emberi nyelven.
- A kijelződriverek udev-es automatikus betöltése tiltva (`/etc/modprobe.d/fusion-display.conf`).

| Profil | Illeszkedik | Driver |
| --- | --- | --- |
| `nvidia-kepler-470` | 10de:0ff6 (Quadro K1100M) | nvidia (M2-től) |
| `vmware-svga` | 15ad:0405 (VirtualBox VMSVGA) | vmwgfx |
| `virtualbox-vga` | 80ee:beef | vboxvideo |
| `intel-kms` | 8086:* | i915 |
| `generic-kms` | bármely PCI grafika | — (firmware framebuffer) |
| `firmware-fb` | nincs PCI grafika | — |

Tesztek: `sh tests/hwprobe-test.sh` (16 eset, hamis sysfs-sel és modulkezelővel).

## Automatikus teszt (`build/fusion-build test`)

QEMU + OVMF, KVM nélkül is (lassabb). A FusionOS-t háromféleképp indítja
(std VGA + SATA, VMware SVGA + SATA, std VGA + USB-pendrive), és a soros konzolon ellenőrzi:
systemd „running”, gyökér-overlay, /usr csak olvasható (EROFS), /data ext4, A slot,
hardverprofil és driver, getty, magyar locale és billentyűzet, `fusion` felhasználó,
machine-id, nincs hibás szolgáltatás. Ezen felül a diagnosztikai bejegyzést is elindítja.

Megjegyzés: QEMU `-vga vmware` alatt a vmwgfx maga jelzi, hogy ez nem támogatott környezet
(a képernyő fekete maradhat); a VirtualBox VMSVGA a támogatott környezete.

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

## Ismert korlátok (M1)

- Nincs grafikus felület és NVIDIA driver (M2); nincs Wi-Fi (később).
- A DATA fájlrendszer-ellenőrzése (fsck) még nincs az initramfs-ben.
- A gyökér-overlay felső rétege egy rendszerképhez tartozik; a frissítéskori
  állapotkezelést (mi marad meg, mi áll vissza) az M7 (A/B frissítés) rendezi.
- `loader.conf`: `editor yes` — fejlesztői beállítás, később kikapcsol.
