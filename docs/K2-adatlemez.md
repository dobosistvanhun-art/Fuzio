# 0.0.48 (k2): Adatlemez, Fejlesztő terminál, a saját build a frissítésben

## 1. Adatlemez (a Mint kivezetése, F4 „b” út)

A FusionOS marad az ADATA SSD-n (sdb). A Kingston SSD (sda, eddig a Mint) **Adatlemez** lesz.
A FusionOS minden induláskor csatolja, és a saját mappában **Tárhely** néven látszik.

- **Lemezkezelő → egy belső lemez partíciója → „Legyen ez az Adatlemez”.**
  - Feltételek: csatolható fájlrendszer (ext4 ajánlott), nem a FusionOS saját lemeze, nem pendrive vagy kártya.
  - A beállítás a DATA-n van (`/data/system/storage.json`, a partíció UUID-ja). Rendszerfrissítés után is megmarad.
- **Indításkor** a `fusion-storage.service` csatolja (`fusion-disk storage-mount`).
  - A csatolás helye: `/run/media/fusion/<címke>`, a Fájlkezelőben és a Windows-programoknak (E:) is látszik.
  - Minden felhasználó mappájában létrejön a `~/Tárhely` hivatkozás.
- **Megszüntetés:** „Adatlemez megszüntetése”. A kötet és a tartalma megmarad, csak induláskor nem csatolódik.
  Ha a partíciót újraformázzák vagy törlik, a beállítás magától megszűnik.
- Parancssorból: `sudo fusion-admin disk storage-set sda1`, illetve `sudo fusion-admin disk storage-clear`.

### A Mint lemezének átállítása (ZBook, a FusionOS-ben)

1. **Beállítások → Indítás:** törölni az `ubuntu` bejegyzést (Törlés…, a név begépelésével).
   A FusionOS legyen az ALAPÉRTELMEZETT.
2. **Lemezkezelő → a 240 GB-os Kingston (sda) → Lemez formázása…:**
   GPT, ext4, címke: `Tárhely`. Megerősítés: `sda`. Ez a Mintet véglegesen törli.
3. **Lemezkezelő → sda1 (Tárhely) → „Legyen ez az Adatlemez”.**
4. Ellenőrzés: Fájlkezelő → Saját mappa → `Tárhely`. Újraindítás után is ott van.

## 2. Fejlesztő terminál a Start menüben

**Start → Rendszer → Fejlesztő terminál** (`fusion-devterm`). Egy Terminál-ablakot nyit a Fejlesztődoboz
parancssorával (`fusion-dev box`), a saját mappában.
- Ha a doboz még nincs, megmondja, hol hozható létre: Beállítások → Programkezelő → Fejlesztődoboz.
- A Beállítások „Parancssor a dobozban” gombja is ezt nyitja.

## 3. Rendszerfrissítés: a saját build kimenete

A frissítőfájlok listájában magától megjelenik a `~/*/build/out/release` és a `~/*/*/build/out/release` mappa `.fupd`-je
(például `~/Projektek/fusionos/build/out/release`). Nem kell a Letöltésekbe másolni.

## Tapasztalat a ZBookon (2026-10-17): „No bootable device” a Mint törlése után

- Az UEFI-bejegyzések rendben voltak: a FusionOS volt az első, mind az ADATA-ra (sdb) mutatott. A HP firmware mégsem indította.
- Az ok: az ADATA az optikai helyen (Upgrade Bay) ül, és a BIOS-ban az „Upgrade Bay Hard Drive boot” ki volt kapcsolva. Eddig a fő helyen lévő Mint eltakarta a gondot.
- A pipa bekapcsolása önmagában nem volt elég. A megoldás: F10 → Advanced → Boot Options → **Customized Boot → Add → `\EFI\BOOT\BOOTX64.EFI`**. Ez a FusionOS ESP-jén lévő systemd-boot.
- A HP BIOS amerikai kiosztással gépel. Magyar billentyűzeten a `\` az **Ű** gombon van (vagy az **Í**-n).
