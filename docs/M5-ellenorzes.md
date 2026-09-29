# M5 — ellenőrzőlista (Klipper, 3D nyomtató)

**Követelmény (specifikáció 9. pont):** a Klipper rendszerszolgáltatásként fusson
(boot → Klipper → Moonraker → webes felület), a FusionOS kezelje az MCU USB-kapcsolatát,
a soros kommunikációt és a hálózatot.

Az M5 kapuja: a ZBookon, a FusionOS alatt a Klipper csatlakozik a nyomtatóhoz (4Max, CP2102 → `/dev/fusion/printer`),
a webes felület (Fluidd vagy Mainsail) mutatja a nyomtatót, a hőmérsékletek élnek,
a gép hazamegy (G28), és egy kis tesztnyomtatás (vagy legalább a fűtés + mozgás) lefut.
Közben a LightBurn (M4) is használható — a két gép párhuzamosan.

## Ami a képben van

| Rész | Változat | Megjegyzés |
| --- | --- | --- |
| Klipper (gazdaprogram) | `v0.13.0-770-gce7002be` | **ugyanaz a commit, mint a Minten** — az MCU-t nem kell újraflashelni |
| Moonraker | `v0.11.0-1-g1cfb0c4` | ugyanaz, mint a Minten |
| Fluidd | v1.37.6 | `http://<gép>/` — a specifikáció ezt írja |
| Mainsail | v2.17.0 | `http://<gép>:81/` — a Minten ezt használod |
| kliens-makrók | mainsail-config, fluidd-config | a `[include mainsail.cfg]` működik |

A Fluidd és a Mainsail közötti választás a használat után dől el (mindkettő a képben).

Adatok: `/data/printer` (config, gcodes, logs, database) — a DATA partíción, újraindítás után megmarad.
Alapkonfiguráció: a Minten futó `printer.cfg`, a FusionOS útvonalaira átírva
(`[mcu] serial: /dev/fusion/printer`, `[virtual_sdcard] path: /data/printer/gcodes`);
a SAVE_CONFIG blokk (PID, bed mesh) változatlan.

## Előkészítés (Mint)

```bash
cd ~/Fusion
rm -rf fusionos-regi && mv fusionos fusionos-regi
tar xzf fusionos-m5.tar.gz
cp -r fusionos-regi/build/cache fusionos/build/
cd fusionos
build/fusion-build deps --install     # új: unzip
build/fusion-build all
```

Az `all` most a Klipper + Moonraker Python-környezetét is elkészíti (build-chrootban, a PyPI-ról,
rögzített változatokkal) — első alkalommal kb. 10 perc, hálózat kell. A Wine a gyorsítótárból jön.

```bash
lsblk -d -o NAME,SIZE,TRAN,MODEL
sudo umount /media/$USER/FUSION_* 2>/dev/null
sudo build/fusion-build usb /dev/sdc
```

A felírás a DATA-t újra létrehozza: a LightBurnt újra kell telepíteni (a telepítő újramásolása
a `import` mappába, ahogy az M4-nél).

**Fontos:** a Minten a Klipper ne fusson egyszerre ugyanazzal a nyomtatóval — itt nem gond, mert
a ZBook vagy Mintet, vagy FusionOS-t futtat.

## A) Indítás a ZBookon

A nyomtató USB-n csatlakoztatva, bekapcsolva; indítás a pendrive-ról. A Desktop terminálja
kiírja a nyomtató állapotát is (`fusion-printer`):

- [ ] `Szolgáltatások: klipper=active moonraker=active web=active`
- [ ] `Eszköz: /dev/fusion/printer -> /dev/ttyUSB…`
- [ ] `Klipper: ready (v0.13.0-770-gce7002be)` — ha `error`/`startup`: `fusion-printer log`

Ha a nyomtatót később kapcsolod be / dugod be: a FusionOS észleli, és a Klipper magától
újracsatlakozik (nem kell FIRMWARE_RESTART).

## B) Webes felület

```bash
fusion-printer ui            # Fluidd, saját ablakban
fusion-printer ui mainsail   # Mainsail
```

- [ ] a felület betölt, a nyomtató „Ready”, a fej- és asztalhőmérséklet élő
- [ ] hálózatról (telefon, Mint-gép): a `fusion-printer` által kiírt címen is elérhető

## C) A gép

- [ ] Home (G28) — mindhárom tengely
- [ ] fűtés: extruder 200 °C, asztal 60 °C — a PID (a SAVE_CONFIG-ból) tartja
- [ ] opcionális: egy kis tesztnyomtatás (a PrusaSlicer feltöltése Moonrakerre/OctoPrintre: `http://<ZBook IP>`)
- [ ] a LightBurn közben is fut, a lézer COM3-on elérhető (a két soros eszköz nem zavarja egymást)

Visszajelzésnek: `fusion-printer` kimenete + fotó a felületről (Ready, hőmérsékletek).

## Hibakeresés

```bash
fusion-printer                    # állapot
fusion-printer log                # a klippy.log vége
journalctl -u fusion-klipper -u fusion-moonraker -b --no-pager | tail -n 40
sudo fusion-printer import <printer.cfg>   # másik konfiguráció átvétele (az előzőt elmenti)
```
