# FusionOS a ZBook optikai helyén lévő SSD-re (120 GB) — telepítés és frissítés

Ettől kezdve a FusionOS a belső, 120 GB-os SSD-n fut (ADATA SP900, a Mintben általában `sdb`).
A Mint (Kingston, `sda`) érintetlen marad; a FusionOS indítása: **F9 → az ADATA SSD bejegyzése**.

Két parancs van:

| Parancs | Mit csinál | A DATA (programok, Wi-Fi, nyomtató-adatok) |
| --- | --- | --- |
| `install <lemez> --internal …` | első telepítés: a teljes lemez újraparticionálva | új — vagy **átvéve a pendrive-ról** (`--data-from`) |
| `update <lemez>` | rendszerfrissítés: ESP + A slot újraírva | **megmarad** — a LightBurnt nem kell újratelepíteni |

## 0) Mentés — az SSD teljes tartalma törlődik

Az SSD-n most kb. 25 GB adat van (ext4). **Előbb mentsd le**, pl. a Mint lemezére:

```bash
lsblk -o NAME,SIZE,TRAN,MODEL,FSTYPE,LABEL,MOUNTPOINTS
```

Keresd az ADATA SP900 sort (kb. 111,8 G). Ha csatolva van (pl. `/media/dobos/…` vagy `/mnt/…`),
a mentés (a célmappát te választod, legyen rajta elég hely):

```bash
mkdir -p ~/ssd-mentes
sudo rsync -aHAX --info=progress2 <az SSD csatolási pontja>/ ~/ssd-mentes/
```

**Ha az SSD partíciója az `/etc/fstab`-ban szerepel** (a Mint indításkor csatolja), azt a sort
kommenteld ki (`#`) — különben a telepítés után a Mint indításkor a régi partícióra várna:

```bash
grep -n -v '^#' /etc/fstab            # van-e sor az SSD partíciójára (UUID=… vagy /dev/sdb…)?
sudo nano /etc/fstab                  # ha van: a sor elé #, mentés
```

Végül válaszd le: `sudo umount <csatolási pont>` (a telepítő más csatolt partíció esetén megáll).

## 1) A FusionOS elkészítése (Mint)

```bash
cd ~/Fusion
rm -rf fusionos-regi && mv fusionos fusionos-regi
tar xzf fusionos-m5b.tar.gz
cp -r fusionos-regi/build/cache fusionos/build/
cd fusionos
build/fusion-build deps --install
build/fusion-build all
```

## 2) Wi-Fi előre beállítva

Egy kis fájl a `~/Fusion` mappában (a jelszó csak ide és az SSD DATA-jára kerül, a csomagba nem):

```bash
printf 'SSID=Telekom-635385_24GHz\nPSK=<a Wi-Fi jelszava>\n' > ~/Fusion/wifi.conf
chmod 600 ~/Fusion/wifi.conf
```

## 3) Telepítés az SSD-re, a pendrive DATA-jának átvételével

A pendrive (a mostani FusionOS, rajta a telepített LightBurn) legyen bedugva; a Mint a DATA
partícióját magától csatolja: `/media/dobos/FUSION_DATA`. Ellenőrzés:

```bash
lsblk -o NAME,SIZE,TRAN,MODEL,LABEL,MOUNTPOINTS
ls /media/$USER/FUSION_DATA          # overlay  fwr  printer ...
```

Telepítés (az `sdb` legyen az ADATA SP900 — a fenti listából ellenőrizd!):

```bash
sudo build/fusion-build install /dev/sdb --internal \
     --data-from /media/$USER/FUSION_DATA \
     --wifi-file ~/Fusion/wifi.conf
```

Kiírja a lemez adatait és tartalmát; megerősítés: `sdb` begépelése. A DATA átvétele a pendrive
sebességétől függ (a LightBurn-környezet 1–2 GB) — néhány perc.

Az átvett DATA-val a FusionOS pontosan onnan folytatja, ahol a pendrive tartott:
a LightBurn telepítve (licenc, beállítások), a Wi-Fi megjegyezve, a nyomtató-konfiguráció és a
Moonraker-adatbázis megvan.

## 4) Indítás

Újraindítás → **F9** → az ADATA SSD UEFI-bejegyzése. (A pendrive maradhat bedugva is: a FusionOS
mindig arról a lemezről veszi a rendszert és a DATA-t, amelyikről elindult.)

- [ ] a Desktop elindul, a Wi-Fi magától kapcsolódik (`fusion-wifi`)
- [ ] `fwr list` → `LightBurn [lightburn]: telepítve` → `fwr launch lightburn` (az első indítás
      a frissített futtató miatt 1–2 perccel tovább tart)
- [ ] `fusion-printer` → `Klipper: ready`

## Később: frissítés (a DATA megmarad)

```bash
cd ~/Fusion/fusionos          # az új csomag kibontása után, ahogy eddig
build/fusion-build all
sudo build/fusion-build update /dev/sdb     # megerősítés: sdb
```

Az `update` csak FusionOS-lemezen fut (ellenőrzi a FUSION_ESP/A/B/DATA partíciókat), és a DATA-hoz
nem nyúl. A pendrive ugyanígy frissíthető (`update /dev/sdc`).

Frissítés után az első indításkor a FusionOS a DATA-n maradt régi felhasználó-adatbázist
(`/etc/passwd` stb.) félreteszi (`/data/overlay/stale/…`), hogy az új rendszer felhasználói
(pl. egy új szolgáltatás) biztosan érvényesek legyenek.
