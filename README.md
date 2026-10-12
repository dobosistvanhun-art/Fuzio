# FusionOS

Saját felhasználói és rendszerabsztrakcióval rendelkező operációs rendszer.
A Linux kernel itt infrastruktúra és driver-alap, nem a FusionOS identitása.
Célgép: HP ZBook 15 G2 (Quadro K1100M, diszkrét mód).

**Állapot: M6 — Fusion Desktop** (folyamatban).
Lezárva: M4 (LightBurn 2.1 + COM3 + GRBL), M5 (Klipper), M0 (build-környezet, EFI-boot), M1 (alaprendszer), M2 (grafika, NVIDIA 470 — ZBook:
OpenGL 4.6, Vulkan 1.2.175), M3 (USB/hardverréteg — ZBook: `/dev/fusion/laser` → `Grbl 1.1h`).

## M6 — Fusion Desktop

A felületi technika a ZBookon mért adatok alapján: **Qt 6 / Qt Quick (QML)**, Python háttérrésszel
(a mérés és a döntés: `docs/M6-meres.md`). Az ablakokat a JWM kezeli (FusionDark, saját tálca nélkül).
Ellenőrzés a ZBookon: `docs/M6-ellenorzes.md`.

- **Fusion Shell** (`fusion-shell`): panel (Start, tálca, lézer/nyomtató/meghajtó jelzés, Wi-Fi, értesítések,
  óra + naptár), Start menü (keresés programokra és beállításokra, kikapcsolás), értesítések a szabványos
  `org.freedesktop.Notifications` szolgáltatással (`fusion-notify`, `notify-send`), értesítésközpont
- **Fájlkezelő** (`fusion-files`): kétpaneles; F3–F8, Tab, jelölés, vágólap, húzás, keresés (Alt+F7),
  könyvtár-összehasonlítás, rejtett fájlok, ZIP/TAR, nézőke és szerkesztő, meghajtók (csatolás, kiadás)
- **Beállítások** (`fusion-settings [oldal]`): Wi-Fi, Kijelző, Eszközök, Nyomtató, Hang, Programkezelő, Programbolt, Asztal, Rendszerfrissítés, Hibajelentés, Rendszer
- **Programbolt** (Start → Programbolt): a Flathub katalógusa (népszerű, kategóriák, keresés, részletek,
  képernyőképek) — a telepítést a Programkezelő végzi. Ellenőrzés: `docs/M6h-programbolt-hang.md`
- **Start menü csoportokkal** (Műhely, Grafika, Iroda, Internet, … Rendszer; Gyakran használt; jobb gomb: áthelyezés)
- **Fejlesztői eszközök** (Programkezelő; `fusion-dev`): Node.js LTS a DATA-n, Wrangler, git. Ellenőrzés: `docs/M6j-startmenu-fejlesztes.md`
- **Lomtár** (Fájlkezelő): a törlés a szabványos lomtárba tesz (Ctrl+Z visszavonás, visszaállítás az eredeti helyre, Shift+Del végleges törlés); Drive-panel mellett sem lassú. Ellenőrzés: `docs/M6j-startmenu-fejlesztes.md`
- **Letöltések** mappa (XDG — a Flatpak-programok, pl. a Firefox ide mentenek) és **Megnyitás ezzel…** (Shift+Enter, „mindig ezzel”) a Fájlkezelőben. Ellenőrzés: `docs/M6k-letoltes-tarsitas.md`
- **A/B frissítés** (M7): az új rendszer a nem aktív slotba kerül és próbaként indul (systemd-boot boot-számlálás, 3 lehetőség); sikeres indulás után véglegesül, különben magától a korábbi indul. `fusion-update`, Minten `fusion-build update` (A/B) és `--hibas-proba`. Ellenőrzés: `docs/M7a-ab-frissites.md`
- **Rendszerfrissítés fájlból** (Beállítások → Rendszerfrissítés): `.fupd` a Letöltésekből / pendrive-ról, újraindítás a FusionOS-be, értesítés véglegesítéskor / visszaálláskor. **Feladatkezelő** (Ctrl+Alt+Del): „nem válaszol” felismerés, bezárás, kényszerített bezárás. Ellenőrzés: `docs/M7b-frissites-feladatkezelo.md`, lezárás: `docs/M7c-lezaras.md`
- **Lemezkezelő** (Start → Lemezkezelő; `fusion-disks`): lemezek és partíciók, állapot (SMART), formázás (FAT32, exFAT, NTFS, ext4), címke, partíció létrehozása / törlése — gépelt megerősítéssel; a FusionOS saját lemeze csak megtekinthető. **Hibajelentés** (Beállítások → Hibajelentés; `fusion-report`): a rendszer állapota egy maszkolt szövegfájlban, nem küld adatot sehova. Ellenőrzés: `docs/T1-lemezkezelo-hibajelentes.md`
- **Telepítő pendrive** (T2; Minten: `sudo build/fusion-build installer /dev/sdX`): a **Fusion Telepítő** — új telepítés egy lemezre, vagy egy meglévő FusionOS újratelepítése a DATA (programok, Wi-Fi, beállítások) megőrzésével; Mint nélkül, bármelyik gépen. Ellenőrzés: `docs/T2-telepito.md`. **T3:** telepítő pendrive a FusionOS-ből is (Rendszerfrissítés → „Telepítő pendrive készítése…”), **Mentés** (Beállítások → Mentés: a DATA egy külső lemezre), visszaállítás a telepítőben, Wi-Fi átvétele — `docs/T3-mentes-telepito.md`
- **0.0.30 (j1) javító kör**: gyors Programkezelő-lista, nagyobb / csoportosított / görgethető Programok az asztalon, PSS-memória a Feladatkezelőben, `build/fusion-build cache-export` (a rögzített csomagok mentése), mérési boot-bejegyzések (Intel grafika, Nouveau, szoftveres felület) — `docs/J1-javitasok.md`
- **0.0.31 (j2)**: a mérési boot-bejegyzéseket a rendszer maga pótolja, és UEFI-bejegyzésként (F9: „Fusion meres - …”) is felveszi; az asztali Programok a tálca felett ér véget — `docs/J2-boot-bejegyzesek.md`
- **0.0.32 (j3)**: Beállítások → Kijelző → Felület rajzolása (grafikus kártya / szoftveres); az Xorg csak a kiválasztott adaptert használja; pam_lastlog-hiba javítva — `docs/J3-felulet-rajzolas.md`
- **0.0.33 (j4)**: rendszerkép-írás 32 MiB-os adagokban, kiesett pendrive = azonnali, érthető hiba; a Rendszerfrissítés oldal nem vár a pendrive-ra; tisztább naplók — `docs/J4-pendrive-iras.md`
- **0.0.34 (m8a)**: Fusion API 1. lépés — a `fusion` Python-csomag (kv, hardware, devices, notify, x11, permissions), a kettőzések megszüntetése, látható változás nélkül — `docs/M8a-rendrakas.md`
- **0.0.35 (m8a1)**: a pendrive-ok helye `/run/media/fusion/<címke>` — így a Flatpak-programok (PrusaSlicer …) fájlválasztójában is eszközként látszanak — `docs/M8a1-pendrive-flatpak.md`
- **0.0.36 (m8b)**: Windows-programok (LightBurn) fájlválasztója: Adatok (D:, a DATA felhasználói mappái), pendrive (E:), Asztal-hivatkozások, Dokumentumok → Projektek, a „/” elrejtve; hibajelentés: WI-FI szakasz (iwd, kernel, energiatakarékosság) — `docs/J5-lightburn-fajlok-wifi.md`; M8b: a Fusion API leírása (`docs/api/`), `fusion` parancs `--json`-nal, leíró-sémák, feladat-protokoll — `docs/M8b-leiras-cli.md`
- **0.0.37 (m8d)**: Lézer állapot (Start → Műhely) — az első program kizárólag a Fusion API-n át; akkumulátor az Asztal Rendszer kártyáján, a hibajelentésben és a `fusion power` parancsban — `docs/M8d-lezer-allapot.md`
- **0.0.38 (j6)**: a Programkezelő külön ablakban (fülek: Programkezelő, Programbolt); a Lomtár automatikus ürítése (Beállítások → Rendszer: ki / 7 / 30 / 90 nap), `fusion trash` — `docs/J6-programkezelo-lomtar.md`
- **0.0.39 (j7)**: Terminál: Ctrl+V / Ctrl+Shift+V beillesztés, Ctrl+Shift+C másolás, többsoros beillesztés; Printables „Open in PrusaSlicer” a Firefoxból (URL-séma, Linux-receptek) — `docs/J7-terminal-printables.md`
- **0.0.40 (j8)**: beépített kamera (Kamera program, Eszközök és kamera), Bluetooth (Beállítások → Bluetooth: párosítás, fejhallgató, egér, billentyűzet), papírnyomtatók (Beállítások → Nyomtatók: CUPS, driverless, PDF-nyomtató); `fusion cameras | bluetooth | printers` — `docs/J8-kamera-bluetooth-nyomtato.md`
- **0.0.41 (m9a)**: jogosultságok első lépése — `input` csoport ki, hibajelentés: JOGOSULTSÁGOK, Programkezelő: Védelem, leíró: `allow.files` / `allow.net` / `sandbox`, `fusion permissions` (Klipper és LightBurn változatlan) — `docs/M9a-jogosultsagok.md`
- **Google Drive** (Start → Google Drive): rclone-csatolás a `~/GoogleDrive` mappába, a Fájlkezelőben kötetként;
  bejelentkezés a böngészőben (`fusion-drive`). **Ébren tartás**: amíg lézer / nyomtató csatlakozik, a gép nem
  alszik el (a fedél lecsukására sem), és az USB-juk nem altatható. Ellenőrzés: `docs/M6i-drive-ebrenlet.md`
- **Hang**: PipeWire (PulseAudio-felülettel, a Flatpak-programoknak is), WirePlumber; a panelen hangerő-felugró,
  hangerő-billentyűk, Beállítások → Hang, `fusion-sound`
- **Irányítópult** az asztalon: lézer, 3D nyomtató (Klipper, nyomtatás állása, hőmérsékletek), hálózat,
  rendszer, meghajtók, programok — Beállítások → Asztal
- **Fusion Programkezelő** (Start → Programkezelő; `fusion-programs`, `fusion-run`): minden program egy
  leírás a DATA-n (`/data/programs/<id>/program.fusion`) — telepítés fájlból (Windows .exe/.msi, AppImage,
  Linux-archívum, Flatpak) és a Flathubról, eltávolítás, frissítés, Start menü, ikon, fájltársítás,
  Windows-programoknál eszköz-hozzáférés (COM3 lézer, COM4 nyomtató). A Linux-programok fő formátuma a
  **Flatpak**; a Windows-futtató ma az fwr (kísérleti M4-megoldás). Ellenőrzés: `docs/M6f-programkezelo.md`,
  terv: projekt → `claude/Programkezelo-architektura.md`, mérés: `docs/M6c-programkezelo-meres.md`
- **Kötetek**: a cserélhető meghajtók (USB, SD) bedugáskor a `/run/media/<címke>` alá csatolódnak
  (FAT32, exFAT, NTFS, ext4); a belső lemezek kérésre (Fájlkezelő → meghajtó). A rendszerműveletek
  a szűk jogú `fusion-admin` segéden át mennek (sudo szabály csak erre).

## Telepítés az SSD-re és frissítés (a DATA megmarad)

- `sudo build/fusion-build install /dev/sdb --internal --data-from /media/$USER/FUSION_DATA --wifi-file ~/Fusion/wifi.conf`
  — első telepítés belső lemezre (a ZBook optikai helyén lévő SSD), a pendrive DATA-jának átvételével
- `sudo build/fusion-build update /dev/sdb` — rendszerfrissítés: ESP + A slot újraírva, a DATA
  (LightBurn, Wi-Fi, nyomtató-adatok) megmarad
- a fusion-init a boot-lemezről veszi a slotot és a DATA-t (systemd-boot `LoaderDevicePartUUID`),
  így több FusionOS-lemez (SSD + pendrive) sem keveredik

Részletek: `docs/SSD-telepites.md`.

## M5 — Klipper (3D nyomtató)

A Klipper és a Moonraker **rendszerszolgáltatás** (`fusion-klipper`, `fusion-moonraker`), a webes
felületet nginx szolgálja ki: **Fluidd** a 80-as, **Mainsail** a 81-es porton (a választás használat után).
A Klipper-gazdaprogram ugyanarra a commitra van rögzítve, mint a Minten (`v0.13.0-770-gce7002be`), így a
nyomtató MCU-ját nem kell újraflashelni. A nyomtató az M3 eszközréteg `printer` szerepe
(`/dev/fusion/printer`); bedugáskor a Klipper magától újracsatlakozik. Adatok: `/data/printer`.

- `fusion-printer` — állapot, webcímek; `fusion-printer ui [fluidd|mainsail]` — a felület saját ablakban
- `sudo fusion-printer import <printer.cfg>` — meglévő konfiguráció átvétele (serial és gcodes útvonal átírva)
- a Python-környezet build-chrootban készül, rögzített requirements-ből (`build/steps/printer.sh`)
- a QEMU-teszt a Klipper „Linux MCU”-jával (szoftveres MCU) viszi végig a láncot: Klipper ready, G-kód, makrók, mindkét felület

Kézi ellenőrzés: `docs/M5-ellenorzes.md`.

## M4 — cél és a jelenlegi megvalósítás

**Követelmény:** a Windows-os LightBurn x64 fusson a FusionOS alatt, és a valódi GRBL
lézervezérlőt USB-n keresztül **COM3**-ként érje el.

| Réteg | Mi ez | Státusz |
| --- | --- | --- |
| USB/hardverréteg (M3) | `/dev/fusion/laser` a lézer szerephez kötve | FusionOS-rész, lezárva |
| COM3 → `/dev/fusion/laser` | a Windows-program portja a Fusion szerepre mutat | M4-követelmény |
| `fwr` + profil (`fwr/profiles/lightburn.fwr`) | a program indítása, portok, meghajtók egy helyen | M4 proof-of-concept |
| **Wine 11.0 (WoW64), forrásból** + `fwr/wine-patches/` | a Windows-program tényleges futtatója | **kísérleti M4-megoldás — nem a FusionOS végleges architektúrája** |

Használat (M4 PoC):
- `fwr install lightburn <telepítő.exe>` · `fwr launch lightburn` · `fwr list` · `fwr check`
- a futtatókörnyezet a DATA-n: `/data/fwr/<program>/`; napló: `~/.local/share/fusion/fwr/<program>.log`
- a program csak a profil COM-portjait látja (a kísérleti Wine-javítás kikapcsolja a Wine
  automatikus portkeresését), a `SERIALCOMM` ebből töltődik ki
- meghajtók: `C:` (a környezet) és `P:` = `~/Projektek`; a Linux-fájlrendszer (`Z:`) nem látszik
- `fwr check`: tesztprogramok (`fwr/tools/`) — SERIALCOMM, COM3 megnyitása és írása
  (GRBL-megjegyzéssel, a gép nem mozdul), OpenGL-renderelő

**Wi-Fi** (Intel Wireless 7260, `iwlwifi`): `fusion-wifi list` · `fusion-wifi connect "<hálózat>"` ·
`fusion-wifi`. A kapcsolódást az iwd végzi, a címet a systemd-networkd adja; a megjegyzett
hálózatok a DATA-n maradnak. A vezetékes kapcsolat, ha van, elsőbbséget kap. (iwd: jelenlegi
megoldás; a NetworkManager/iwd végleges döntése a Fusion Desktop felületével együtt.)

Kézi ellenőrzés: `docs/M4-ellenorzes.md`.

## Mit tud az M3 (lezárva)

- A **Fusion eszközréteg** (`fusion-devd`) a soros eszközöket szerephez köti, és stabil nevet
  ad nekik a ttyUSB-sorszámtól és a bedugási sorrendtől függetlenül:

  | Szerep | Eszköz (Phase 0b) | Azonosítás | Név | Kinek |
  | --- | --- | --- | --- | --- |
  | Lézer (GRBL) | CH340 1a86:7523, nincs sorozatszáma | USB-port szerint | `/dev/fusion/laser` | LightBurn → COM3 (M4) |
  | 3D nyomtató (Klipper) | CP2102 10c4:ea60 | sorozatszám szerint | `/dev/fusion/printer` | Klipper (M5) |

- Az első illeszkedő eszköz automatikusan megkapja a szabad szerepet; a hozzárendelés
  az `/etc/fusion/devices.conf`-ba kerül (a DATA-n megmarad).
- A bejelentkezett felhasználó root nélkül megnyitja az eszközöket (udev `uaccess`).
- Kihúzás és visszadugás után az eszköz ugyanazzal a névvel tér vissza.
- `fusion-devices`: szerepek, csatlakozás, ki használja a portot, szerep nélküli eszközök;
  `sudo fusion-devices assign laser ttyUSB0` — áthelyezés (pl. másik USB-port);
  `sudo fusion-devices forget <szerep>`.
- Adatvezérelt: a szerepeket a `devices/roles/*.role` fájlok írják le (USB-azonosítók,
  azonosítási mód, Windows COM-port); a kódban nincs eszközspecifikus ág.
- A soros driverek (ch341, cp210x, ftdi_sio, pl2303, cdc-acm) a `linux-modules-extra`-ból
  kerülnek a képbe, csak ezek (`build.conf`: `EXTRA_MODULES`). ModemManager / brltty nincs.

Kézi ellenőrzés: `docs/M3-ellenorzes.md`.

## Mit tud az M2

## Mit tud az M2 (lezárva)

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

A boot menüben a FusionOS és a diagnosztika mellett fejlesztői **mérési bejegyzések** is
vannak (KMS nélkül, Xorg root-joggal, szöveges konzol) — `build.conf`: `BOOT_MEASURE_ENTRIES`.

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
| `wine` | kísérleti M4-futtató: Wine 11.0 (WoW64) fordítása (root; első alkalommal ~1 óra; az `all` magától hívja) |
| `rootfs [--force]` | a FusionOS rendszerkép (EROFS) — root kell; az `all` sudo-val hívja, ha a forrás változott |
| `build` | két initramfs + két UKI (FusionOS, diagnosztika) + ESP |
| `image` | GPT lemezkép: ESP, A slot (rendszerkép), B (üres), DATA |
| `vdi` | lemezkép → VDI |
| `vm [--usb]` | FusionOS-dev VM létrehozása / lemezcsere (`--usb`: lézer és nyomtató átadása, Extension Pack kell) |
| `vm-start` | a VM indítása |
| `all` | fetch + drivers + wine + rootfs + build + image + vdi |
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
| FUSION_B | 4 GiB | 4 GiB | a második rendszer-slot (A/B frissítés, M7) |
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
| `nvidia-kepler-470` | 10de:0ff6 (Quadro K1100M) | nvidia 470 (+ nvidia-drm modeset=1), Xorg: nvidia, root nélkül |
| `vmware-svga` | 15ad:0405 (VirtualBox VMSVGA) | vmwgfx, Xorg: modesetting |
| `virtualbox-vga` | 80ee:beef | vboxvideo |
| `intel-kms` | 8086:* | i915 |
| `generic-kms` | bármely PCI grafika | — (firmware framebuffer) |
| `firmware-fb` | nincs PCI grafika | — |

Tesztek: `sh tests/hwprobe-test.sh` (32 eset, hamis sysfs-sel, modulkezelővel és kernel parancssorral),
`sh tests/devices-test.sh` (21 eset: automatikus hozzárendelés, port / sorozatszám, jelölt,
egyszerre bedugott eszközök, assign, forget).

## Automatikus teszt (`build/fusion-build test`)

QEMU + OVMF, KVM nélkül is (lassabb). A FusionOS-t háromféleképp indítja
(std VGA + SATA, VMware SVGA + SATA, std VGA + USB-pendrive), és a soros konzolon ellenőrzi:
systemd „running”, gyökér-overlay, /usr csak olvasható (EROFS), /data ext4, A slot,
hardverprofil és driver, getty, magyar locale és billentyűzet, `fusion` felhasználó,
machine-id, nincs hibás szolgáltatás; std VGA-n a Fusion Desktopot is (Xorg, OpenGL,
ablakkezelő, magyar kiosztás az X-ben). Az std + SATA futásban egy emulált USB-soros eszköz
(FTDI) is van: `/dev/fusion/laser` létrejön, a `fusion` felhasználó root nélkül megnyitja,
és a teszt a QEMU monitorán át **kihúzza és visszadugja** — a név ugyanúgy visszatér.
A Wi-Fi-t virtuális rádiókkal (`mac80211_hwsim`) teszteli: az egyik hozzáférési pont, a másikról
a `fusion` felhasználó jelszóval kapcsolódik (`fusion-wifi connect`).
Ugyanitt egy háromkötetes emulált USB-pendrive (FAT32, exFAT, NTFS) automatikus csatolását, írhatóságát
és a biztonságos eltávolítást is ellenőrzi; std VGA-n a Fusion Desktopot (panel, Start menü, értesítés
a D-Buson, a Fájlkezelő műveletei és ablaka, a Beállítások oldalai és ablaka).
Ugyanebben a futásban az `fwr check` is lefut: a Windows-program csak a COM3-at látja a
SERIALCOMM-ban, megnyitja, és a kiírt sor megérkezik az emulált eszközre; az OpenGL a Wine-on
át működik. Ezen felül a mérési és a diagnosztikai bejegyzést is elindítja.

Megjegyzés: QEMU `-vga vmware` alatt a vmwgfx nem veszi át az eszközt („unsupported
hypervisor”) — a Hardware Layer ezt `failed`-ként jelzi, és ott a teszt grafikus felületet
nem vár. A VMSVGA támogatott környezete a VirtualBox.

## Tárolószerkezet

```
build/        fusion-build, lépések (steps/), konfiguráció (config/)
rootfs/       a rendszerkép: csomaglista, testreszabás, FusionOS fájlok (overlay/)
hardware/     Fusion Hardware Layer: fusion-hwprobe + profilok
devices/      Fusion eszközréteg: fusion-devd (fusion-devices) + szerepek (roles/)
fwr/          M4 PoC: fwr, profilok, diagnosztikai Windows-programok; wine-patches/ = kísérleti
desktop/      M6: Fusion Desktop — lib/ (közös Python), qml/FusionUI (téma, elemek), icons/, shell/, files/, settings/
printer/      M5: fusion-printer, szolgáltatások, Moonraker- és nginx-beállítás, alapkonfiguráció (defaults/)
initramfs/    fusion/init (FusionOS), m0/init (diagnosztika)
tests/        automatikus tesztek
tools/        fusion-hardware-discovery.sh (Phase 0)
docs/         ellenőrzőlisták
```

## Ismert korlátok (M2)

- Mért döntések (ZBook, 2026-09-27): `nvidia-drm.modeset=1`, Xorg root-jog nélkül
  (`docs/M2-ellenorzes.md`, C). Tartalék bejegyzések a boot menüben.
- NVIDIA csomagforrás: a `470-server` sorozat (a sima `-470` a noble-updates-ben már a
  535-ös driverre mutató átmeneti csomag, az nem támogatja a Keplert).
- A DATA fájlrendszer-ellenőrzése (fsck) még nincs az initramfs-ben.
- A gyökér-overlay felső rétegének frissítéskori kezelése: M7 (A/B frissítés).
- `loader.conf`: `editor yes` — fejlesztői beállítás, később kikapcsol.
