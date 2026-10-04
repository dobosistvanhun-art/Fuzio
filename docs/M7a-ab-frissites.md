# M7a — A/B frissítés, automatikus visszaállás: ellenőrzés a ZBookon (0.0.24)

Mostantól a frissítés **nem írja felül a futó rendszert**. Az új változat a másik slotba kerül, és
**próbaként** indul. Ha a Fusion Desktop rendben elindul, néhány másodperc múlva véglegessé válik
(„véglegesítés”). Ha háromszor nem indul el, a gép **magától** a korábbi rendszert indítja. A DATA
(programok, beállítások, Wi-Fi, nyomtató) mindkét rendszerből ugyanaz.

## 1. Frissítés 0.0.23 → 0.0.24 (Minten) — az első A/B frissítés

```bash
cd ~/Fusion
rm -rf fusionos-regi && mv fusionos fusionos-regi
tar xzf fusionos-m7a.tar.gz
cp -r fusionos-regi/build/cache fusionos/build/
cd fusionos
build/fusion-build all
sudo build/fusion-build update /dev/sdb      # megerősítés: sdb
```

A kiírásban: „Új rendszer: FusionOS 0.0.24 (m7) → a(z) **B** slotba”, és „A mostani rendszer (A slot)
megmarad tartaléknak”.

- [ ] Újraindítás, F9 → FusionOS. A boot menüben (5 mp) két rendszer: **FusionOS 0.0.24 (m7) — B** (kijelölve)
      és **FusionOS 0.0.23 (m6) — A**
- [ ] A 0.0.24 elindul, megjelenik a Fusion Desktop
- [ ] Terminál (Ctrl+Alt+T): `sudo /usr/lib/fusion/bin/fusion-admin update-status`
      → `B: fusionos-0.0.24-…-B.efi [véglegesített] ← fut`, `A: fusionos-0.0.23-m6-A.efi [véglegesített]`
- [ ] Ugyanott az „állapot:” sor: `VÉGLEGESÍTVE: … (slot B)`
- [ ] Minden program, beállítás, Wi-Fi megvan (a DATA közös)
- [ ] A boot menüben a régi A is választható (kézi visszalépés)

## 2. Automatikus visszaállás próbája — szándékosan hibás frissítés

Ez az A slotba (a régi 0.0.23 helyére) sérült rendszerképet ír. Minten:

```bash
cd ~/Fusion/fusionos
sudo build/fusion-build update /dev/sdb --hibas-proba
```

- [ ] F9 → FusionOS. A menüben a legújabb (A, hibás) van kijelölve
- [ ] Piros üzenet: „Ez egy frissítés utáni próba-indítás … Újraindítás 15 mp múlva”, és „A következő
      indítás is innen (UEFI BootNext)” → a gép újraindul (**nem** a Mintbe)
- [ ] Ez **háromszor** ismétlődik, utána magától a **B** (0.0.24) indul, a Fusion Desktop megjelenik
- [ ] `sudo /usr/lib/fusion/bin/fusion-admin update-status` → `A: …-A+0-3.efi [HIBÁS (nem indult el)]`
- [ ] Ha a gép a 2. vagy 3. újraindításkor mégis a Mintbe indulna: F9 → FusionOS — kérlek írd meg
      (akkor a HP firmware nem veszi figyelembe a BootNext-et)

Az A slot ezután a következő normál frissítéskor kap újra rendes rendszert
(`sudo build/fusion-build update /dev/sdb` → a(z) A slotba).

## Mi számít sikeres indulásnak

A rendszer elindult, a DATA írható, és — ha a Desktop be van kapcsolva — a Fusion Shell 5 percen belül
megjelent. Ha nem: újraindítás (egy próba elhasználva). Kernelpánik után 30 mp-cel magától újraindul
(`panic=30`); az initramfs hibájánál (pl. sérült rendszerkép) 15 mp-cel.

## Parancsok

```bash
sudo /usr/lib/fusion/bin/fusion-admin update-status   # FusionOS-en: slotok, bejegyzések, állapot
sudo build/fusion-build update /dev/sdb               # Minten: frissítés a nem aktív slotba
```
