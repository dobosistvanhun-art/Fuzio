# FusionOS 0.0.40 (j8) — kamera, Bluetooth, papírnyomtatók

## Kamera

- A beépített webkamera (a ZBook HP HD kamerája UVC-eszköz) és az USB-kamerák a `uvcvideo` modullal jelennek meg.
- **Kamera** program (Start menü → Rendszer): élőkép, kameraváltás, ha több van, **Fénykép** gomb (vagy Szóköz).
  - A képek a Képek mappába kerülnek: `~/Képek/Kamera-ÉÉÉÉHHNN-ÓÓPPMM.jpg`.
  - A program Qt Multimedia-t használ, FFmpeg-háttérrel; a kamerát közvetlenül, V4L2-n olvassa.
  - Mérés (QEMU, virtuális kamera): a Qt 6.4 GStreamer-háttere Pythonból összeomlott, X alatt pedig nem adott képkockát. Az FFmpeg-háttér mindkét úton hibátlan volt.
  - A fénykép az élőkép aktuális képkockája.
  - 0.0.42 (ZBook, 0.0.41: fekete élőkép szoftveres felületnél, gyenge képminőség):
    - A Qt Quick szoftveres rajzolója a videót nem jeleníti meg (helyben mérve: szoftveresen üres, OpenGL-lel látszik).
      Ezért a Kamera program mindig OpenGL-lel rajzol, a Beállítások → Kijelző beállításától függetlenül.
    - A kamera formátuma: a legnagyobb felbontás 1280×720-ig, legalább 15 kép/mp, egyenlőnél a gyorsabb. Eddig a Qt
      választott, és gyakran a legkisebbet.
- **Beállítások → Eszközök és kamera → KAMERÁK**: a kamerák listája, Megnyitás gomb.
- A böngészők és a videohívó programok (Flatpak) maguk érik el a kamerát.
- Nincs kamera a listában? Egyes gépeken a BIOS-ban vagy egy billentyűvel ki lehet kapcsolni.
- LightBurn-kamera: a Wine-ban nem várható, hogy működjön. A LightBurn Windowson a WinRT MediaCapture felületet használja, a Fusion Windows Runtime pedig V4L2 nélkül készül. Ez külön döntés lesz, ha kell.

## Bluetooth

- **Beállítások → Bluetooth**: be- és kikapcsolás, **Keresés**, **Párosítás**, Csatlakozás / Bontás, Eltávolítás.
- Párosítás:
  - A FusionOS saját ügynöke felel az eszköznek.
  - Ha az eszköz kódot kér, a Beállítások nagy betűvel mutatja:
    - billentyűzetnél: gépelje be, majd Enter;
    - telefonnál: ellenőrizze, hogy egyezik.
  - Régi eszköz PIN-kódja: 0000.
  - Párosítás után az eszköz megbízható lesz, és csatlakozik.
- **Fejhallgató, hangszóró**: csatlakozás után a **Hang** oldalon kimenetként választható (PipeWire Bluetooth-modul).
- **Egér, billentyűzet**: a kernel HID-rétegén át, külön beállítás nélkül működik.
- Ha a rádió szoftveresen tiltva van (rfkill), a Bekapcsolás feloldja; ez a `fusion-admin rfkill-unblock` paranccsal történik.
  - A gép kapcsolójával (Fn-billentyűvel) kikapcsolt rádiót nem lehet szoftverből bekapcsolni; ezt az oldal jelzi.
- ZBook: Intel 7260 Bluetooth (`btusb` + `btintel`, firmware: `intel/ibt-hw-37.7*`).

## Papírnyomtatók (CUPS)

- **Beállítások → Nyomtatók**. A Klipper 3D nyomtató mostantól „3D nyomtató (Klipper)” néven szerepel.
  - **Keresés**: az USB-n csatlakoztatott és a hálózati nyomtatók (Avahi / mDNS).
  - **Felvétel**:
    - A korszerű nyomtatók meghajtó nélkül működnek (IPP Everywhere / AirPrint), USB-n is (`ipp-usb`).
    - A régebbiekhez a FusionOS a modellhez illő meghajtót választja: HP (hpcups), Gutenprint.
    - Ha nem talál, meghajtólistát mutat kereséssel.
  - **Próbaoldal**, **alapértelmezett** (csillag), **eltávolítás**, a leállított nyomtató **folytatása**, a várakozó **feladatok** törlése.
  - Az állapot és az ok magyarul jelenik meg: „nincs papír”, „papírelakadás”, „kevés a toner” …
  - **PDF-nyomtató**: bármely programból „nyomtatható” PDF-fájlba, ami a `~/PDF` mappába kerül.
- A felhasználó az `lpadmin` csoport tagja. A CUPS így jelszó nélkül engedi a nyomtatók kezelését.
- Haladó beállítások: Webes felület (http://localhost:631).

## Fusion API és hibajelentés

- Új modulok: `fusion.camera`, `fusion.bluetooth`, `fusion.printers`.
- Új parancsok: `fusion cameras`, `fusion bluetooth …`, `fusion printers …`, mind `--json`-nal is. Lásd: `docs/api/cli.md`.
- A párosítás, a nyomtató felvétele és a többi művelet a `fusion.permissions` kapun megy át (képességek: `system:bluetooth`, `system:printers`). Ezt a jogosultsági modell tölti meg tartalommal.
- A hibajelentés új részei:
  - **BLUETOOTH**: adapter, rfkill, modulok, eszközök, kernelsorok. A telefonok és számítógépek neve maszkolva, ahogy a MAC-címek is.
  - **KAMERA**: eszközök, formátumok.
  - **NYOMTATÓK (CUPS)**: lista, URI (a sorozatszám maszkolva), CUPS-hibák.
  - A gyors ellenőrzés kamera- és Bluetooth-sort kapott.

## Apró javítások

- Wi-Fi: a 30 másodpercen belül visszakapcsolódó szakadásról nem jön értesítés, csak a Shell naplójába kerül.
  - Kapcsolódáskor a frekvencia (csatorna) is a naplóba kerül.
  - A hibajelentés „Megszakadások közti idő” sora mutatja a mintázatot (pl. a router 90 percenkénti csatornaváltását).
- Naptár: a kezdeti „null” figyelmeztetés megszűnt.

## Ellenőrzés a ZBookon

1. **Kamera**: Start menü → Kamera. Látszik az élőkép? Fénykép → a Képek mappában megvan?
2. **Bluetooth**: Beállítások → Bluetooth. Bekapcsolás → Keresés → a fejhallgató (párosító módban) → Párosítás.
   - Utána: Hang oldal → a fejhallgató „Ez legyen” → Próba.
3. **Nyomtató**: ha van papírnyomtató, kapcsold be (USB vagy Wi-Fi). Beállítások → Nyomtatók → Keresés → Felvétel → Próbaoldal.
   - Nyomtató nélkül: PDF-nyomtató → Felvétel → Próbaoldal → a `~/PDF` mappában megjelenik.
4. Ha valami nem megy: Beállítások → Hibajelentés. A BLUETOOTH / KAMERA / NYOMTATÓK rész mutatja az okát.
