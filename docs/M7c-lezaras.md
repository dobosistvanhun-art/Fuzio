# M7c — az M7 lezárása (0.0.26): javítások, frissítés már a Beállításokból

## Frissítés — mostantól fájlból (nem kell a `fusion-build update`)

Minten:
```bash
cd ~/Fusion
rm -rf fusionos-regi && mv fusionos fusionos-regi
tar xzf fusionos-m7d.tar.gz
cp -r fusionos-regi/build/cache fusionos/build/
cd fusionos
build/fusion-build all
```
A `build/out/release/fusionos-0.0.26-m7-….fupd` fájlt másold pendrive-ra (Fájlkezelővel is jó; kiadás ⏏ a végén).
FusionOS: Beállítások → **Rendszerfrissítés** → a fájl kijelölése → **Telepítés** → **Újraindítás most**.

(A `sudo build/fusion-build update /dev/sdb` továbbra is működik — tartaléknak.)

## Ellenőrzés

- [ ] Frissítés után értesítés: „Rendszerfrissítés kész”; a Rendszerfrissítés oldalon az új slot „véglegesített — fut”
- [ ] Az újraindítás után a „KÉSZ … Újraindítás most” sáv már nem látszik
- [ ] Rendszerfrissítés oldal, „Indulás” sor: **nincs „degraded”** (kábel nélkül sem) — vagy Terminálban:
      `systemctl --failed` → 0 egység
- [ ] Fájlkezelő: a pendrive-ról a `/data/import` mappába másolás működik
- [ ] Ha a Rendszerfrissítés oldalon nincs frissítőfájl, a Telepítés gomb nem látszik
