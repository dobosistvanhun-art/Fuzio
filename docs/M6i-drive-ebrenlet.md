# M6i — Google Drive és „ébren tartás”: ellenőrzés a ZBookon (0.0.21)

## Frissítés (Mint) — a DATA megmarad

```bash
cd ~/Fusion
rm -rf fusionos-regi && mv fusionos fusionos-regi
tar xzf fusionos-m6i.tar.gz
cp -r fusionos-regi/build/cache fusionos/build/
cd fusionos
build/fusion-build all
sudo build/fusion-build update /dev/sdb      # megerősítés: sdb
```

## A) Ébren tartás, amíg lézer / nyomtató csatlakozik

- [ ] Lézer bedugva → fedél lecsukása: a gép **nem alszik el**, a kijelző kikapcsol, értesítés jön
      („Fedél lecsukva — a gép ébren marad”); felnyitáskor a kép visszajön
- [ ] Futó LightBurn-munka közben lecsukott fedél → a lézer dolgozik tovább
- [ ] Lézer és nyomtató kihúzva → fedél lecsukása: a gép elalszik; felnyitás / bekapcsoló gomb → visszajön
      (ha az NVIDIA-val az ébredés nem tökéletes, írd meg — ez külön téma)
- [ ] Terminál: `systemd-inhibit --list` — lézerrel benne van a „FusionOS … laser csatlakoztatva”, kihúzva nincs
- [ ] USB-altatás tiltva a lézeren:
      `d=$(readlink -f /sys/class/tty/$(basename $(readlink -f /dev/fusion/laser))/device/../..); cat $d/power/control` → `on`

## B) Google Drive (Start → Google Drive, vagy Beállítások → Google Drive)

- [ ] **Bejelentkezés** → megnyílik a Firefox a Google bejelentkező oldalával; fiók kiválasztása, „Engedélyezés”
      (a Google az „rclone” nevet mutatja) → a böngészőben „Success”, a Beállításokban: bejelentkezve, e-mail, tárhely
- [ ] A Drive csatolva: **Megnyitás** → a Fájlkezelőben a Drive fájljai (`~/GoogleDrive`)
- [ ] Fájlkezelő → meghajtók (Alt+F1): „Google Drive” a helyek között
- [ ] Másolás a Drive-ra (F5) és vissza; egy szöveges fájl szerkesztése (F4) a Drive-on → a weben is látszik (pár mp)
- [ ] Újraindítás után magától csatolódik (Wi-Fi kapcsolat után néhány mp — internet nélkül 30 mp-enként újrapróbálja)
- [ ] Leválasztás → a mappa eltűnik, a felhőben lévő fájlok megmaradnak

## Parancssor

```bash
fusion-drive            # állapot
fusion-drive mount      # csatolás most
fusion-drive login      # bejelentkezés (böngésző)
cat ~/.local/share/fusion/drive.log    # ha valami nem megy
```
