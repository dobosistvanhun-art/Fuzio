# M4 — ellenőrzőlista (LightBurn + COM3 + GRBL, proof-of-concept)

**Követelmény:** a Windows-os LightBurn x64 fusson a FusionOS alatt, és a valódi GRBL
lézervezérlőt USB-n keresztül COM3-ként érje el.

Az M4 kapuja: a LightBurn települ és elindul, a licenc aktiválható, a COM3 megjelenik
(és a lézerre mutat, `/dev/fusion/laser`), a lézer csatlakozik, és egy keretezés (Frame) lefut.

A futtató réteg ebben a mérföldkőben **kísérleti** (Wine 11.0, WoW64, forrásból fordítva);
nem a FusionOS végleges architektúrája. Az M4 mérései ennek a kísérletnek az eredményei.

## Előkészítés (Mint)

A csomag (`fusionos-m4c.tar.gz`) és a LightBurn telepítője (`LightBurn-v2.1.04.exe`) a `~/Fusion` mappában van, a pendrive az `sdc`.

```bash
cd ~/Fusion
rm -rf fusionos-regi && mv fusionos fusionos-regi
tar xzf fusionos-m4c.tar.gz
cp -r fusionos-regi/build/cache fusionos/build/
cd fusionos
build/fusion-build deps --install
build/fusion-build all
```

Az `all` a kísérleti futtatót, a **Wine-t forrásból fordítja** (Wine 11.0, WoW64, a két kísérleti
kiegészítéssel: COM-portok, kamera-felsoroló). Új kiegészítés után ez újra lefut — a ZBookon kb. **1 óra**.
A végén: `kész: …/fusionos-dev.vdi`.

A LightBurn telepítőjét a pendrive DATA partíciójára kell másolni (a felírás a DATA-t is újra létrehozza):

```bash
lsblk -d -o NAME,SIZE,TRAN,MODEL          # az sdc legyen az usb
sudo umount /media/$USER/FUSION_* 2>/dev/null
sudo build/fusion-build usb /dev/sdc      # megerősítés: sdc
# a felírás után a pendrive-ot húzd ki és dugd vissza, hogy a Mint csatolja, majd:
sudo mkdir -p /media/$USER/FUSION_DATA/import
sudo cp ~/Fusion/LightBurn-v2.1.04.exe /media/$USER/FUSION_DATA/import/
sudo umount /media/$USER/FUSION_*
```

(A FusionOS-en ez a `/data/import/` mappa.)

## 0) Wi-Fi (a LightBurn licencaktiválásához hálózat kell)

A Desktop terminálja kiírja a Wi-Fi állapotát. Kapcsolódás:

```bash
fusion-wifi list                         # elérhető hálózatok
fusion-wifi connect "Hálózat neve"       # a jelszót bekéri
fusion-wifi                              # állapot: connected, cím
ping -c3 1.1.1.1
```

- [ ] `Állapot: connected`, és van `Cím:` (DHCP)
- [ ] újraindítás után magától kapcsolódik (a hálózatot megjegyzi, a DATA-n)

## A) A runtime ellenőrzése a ZBookon

Lézer a szokásos portjában (bekapcsolva), indítás a kártyáról, a Desktop terminálja:

```bash
fwr check
```

Elvárt:
- [ ] `Wine: wine-11.0`
- [ ] `COM3 -> /dev/fusion/laser (ttyUSB…)`
- [ ] `SERIALCOMM: COM3` — **csak** a COM3 (a nyomtató portja és a ttyS-ek nem látszanak)
- [ ] `COM3: megnyitva, 115200 8N1, … bájt kiírva`
      (a próbasor GRBL-megjegyzés, a gép nem mozdul)
- [ ] `CAM: DeviceWatcher OK (kamerák: 0)` és `CAM: MediaFrameSourceGroup.FindAllAsync OK, kamerák: 0`
      (a Windows kamera-felsoroló — a LightBurn 2.x induláskor ezt hívja; kísérleti kiegészítés)
- [ ] `GL_RENDERER: Quadro K1100M/PCIe/SSE2`, `GL_VERSION: 4.6…`
      (a Wine OpenGL-útja az NVIDIA 470-re — ez a döntési dokumentum nyitott kockázata)

Az első `fwr check` létrehozza az ellenőrző környezetet; a pendrive lassú írása miatt ez több perc is lehet.
Közben ne gépelj a terminálba (a begépelt sorok a futás után végrehajtódnak).

## B) LightBurn telepítése

```bash
ls /data/import/
fwr install lightburn /data/import/LightBurn-v2.1.04.exe
```

- [ ] a LightBurn telepítője elindul (Windows-ablak), végigkattintható
- [ ] a végén: `fwr: telepítve — indítás: fwr launch lightburn`

## C) LightBurn indítása és a kapu

```bash
fwr launch lightburn
```

- [ ] a LightBurn elindul, a licencablak megjelenik (a felhős próbában így volt)
- [ ] licenc: aktiválás a kulcsoddal (vagy a próbaidőszak indítása) — hálózati kapcsolat kell
- [ ] Eszközök (Devices) → **Find My Laser** vagy kézzel: GRBL, **COM3**, 115200
- [ ] a lézer csatlakozik (a konzolban `Grbl 1.1h`, állapot: Alarm/Idle)
- [ ] `$X` vagy homing után egy kis tervre **Frame** → a fej körbejárja a keretet
      (lézer kikapcsolva / alacsony teljesítmény — a keretezés nem éget)

Ha valami nem megy: a napló `~/.local/share/fusion/fwr/lightburn.log`.
Fotó a LightBurn ablakáról (csatlakozva) és az `fwr check` kimenetéről elég visszajelzésnek.
