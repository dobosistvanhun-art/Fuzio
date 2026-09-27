# M4 — ellenőrzőlista (LightBurn + COM3 + GRBL, proof-of-concept)

**Követelmény:** a Windows-os LightBurn x64 fusson a FusionOS alatt, és a valódi GRBL
lézervezérlőt USB-n keresztül COM3-ként érje el.

Az M4 kapuja: a LightBurn települ és elindul, a licenc aktiválható, a COM3 megjelenik
(és a lézerre mutat, `/dev/fusion/laser`), a lézer csatlakozik, és egy keretezés (Frame) lefut.

A futtató réteg ebben a mérföldkőben **kísérleti** (Wine 11.0, WoW64, forrásból fordítva);
nem a FusionOS végleges architektúrája. Az M4 mérései ennek a kísérletnek az eredményei.

## Előkészítés (Mint)

```bash
cd ~/Fusion
rm -rf fusionos-m2c && mv fusionos fusionos-m3
tar xzf fusionos-m4.tar.gz
cp -r fusionos-m3/build/cache fusionos/build/
cd fusionos
build/fusion-build deps --install     # új: git, patch
build/fusion-build all
```

Az `all` most a kísérleti futtatót, a **Wine-t is lefordítja** forrásból (Wine 11.0,
WoW64 mód, a kísérleti portjavítással). Ez első alkalommal hosszú — a ZBookon kb. **1 óra** —, utána a
gyorsítótárból jön. A végén: `kész: …/wine/wine-11.0-db11d0fe-…`.

A LightBurn telepítőjét (Windows, 64 bites `.exe`, lightburnsoftware.com) a pendrive
DATA partíciójára másold, mert a FusionOS-en még nincs böngésző:

```bash
sudo umount /media/$USER/FUSION_* 2>/dev/null
sudo build/fusion-build usb /dev/sdc
# a felírás után a kártyát húzd ki és dugd vissza, hogy a Mint csatolja, majd:
sudo mkdir -p /media/$USER/FUSION_DATA/import
sudo cp ~/Letöltések/LightBurn*.exe /media/$USER/FUSION_DATA/import/
sudo umount /media/$USER/FUSION_*
```

(A FusionOS-en ez a `/data/import/` mappa.)

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
- [ ] `GL_RENDERER: Quadro K1100M/PCIe/SSE2`, `GL_VERSION: 4.6…`
      (a Wine OpenGL-útja az NVIDIA 470-re — ez a döntési dokumentum nyitott kockázata)

Az első `fwr check` létrehozza az ellenőrző környezetet, ez 1–2 perc.

## B) LightBurn telepítése

```bash
ls /data/import/
fwr install lightburn /data/import/LightBurn-…-x64.exe      # a pontos fájlnévvel
```

- [ ] a LightBurn telepítője elindul (Windows-ablak), végigkattintható
- [ ] a végén: `fwr: telepítve — indítás: fwr launch lightburn`

## C) LightBurn indítása és a kapu

```bash
fwr launch lightburn
```

- [ ] a LightBurn elindul (egy induláskori WMI-hibaüzenet ismert — ha jön, OK-val tovább)
- [ ] licenc: aktiválás a kulcsoddal (vagy a próbaidőszak indítása) — hálózati kapcsolat kell
- [ ] Eszközök (Devices) → **Find My Laser** vagy kézzel: GRBL, **COM3**, 115200
- [ ] a lézer csatlakozik (a konzolban `Grbl 1.1h`, állapot: Alarm/Idle)
- [ ] `$X` vagy homing után egy kis tervre **Frame** → a fej körbejárja a keretet
      (lézer kikapcsolva / alacsony teljesítmény — a keretezés nem éget)

Ha valami nem megy: a napló `~/.local/share/fusion/fwr/lightburn.log`.
Fotó a LightBurn ablakáról (csatlakozva) és az `fwr check` kimenetéről elég visszajelzésnek.
