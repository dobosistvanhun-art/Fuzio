# M6 — Fusion Desktop: ellenőrzés a ZBookon

A Fusion Desktop Qt 6 / Qt Quick alapon (a mérés alapján, `docs/M6-meres.md`): **Fusion Shell** (panel,
Start menü, értesítések), **Fájlkezelő** (kétpaneles), **Beállítások**, automatikus kötetcsatolás.

## Frissítés (Mint) — a DATA megmarad, a LightBurn is

```bash
cd ~/Fusion
rm -rf fusionos-regi && mv fusionos fusionos-regi
tar xzf fusionos-m6b.tar.gz
cp -r fusionos-regi/build/cache fusionos/build/
cd fusionos
build/fusion-build deps --install
build/fusion-build all
sudo build/fusion-build update /dev/sdb      # megerősítés: sdb
```

Újraindítás → F9 → FusionOS. A korábbi „FusionOS” terminálablak már nem nyílik meg magától — a Desktop
üres, alul a panel. Terminál: Start → Terminál, vagy **Ctrl+Alt+T**.

## A) Fusion Shell

- [ ] Panel alul: **F** (Start), nyitott ablakok, jobbra lézer / nyomtató jel, Wi-Fi-jel + hálózat, harang, óra
- [ ] **Super** (Windows-gomb) vagy Alt+F1: Start menü; gépelés → szűr (pl. `wifi` → Wi-Fi beállítás), Enter indít
- [ ] Start menü alján: ⚙ Beállítások, ⏻ → Kijelentkezés / Újraindítás / Leállítás (kétszeri kattintás = biztos)
- [ ] Tálca: kattintás előre hoz / kis méretre tesz; középső gomb bezár
- [ ] Órára kattintás: naptár; harangra: értesítések
- [ ] Értesítés terminálból: `fusion-notify "Próba" "Helló"` → buborék jobb alul, a harangon szám
- [ ] Lézer (GRBL) be-/kihúzása → „Lézer (GRBL): csatlakoztatva / leválasztva” értesítés, a panelen a jel színes/halvány

## B) Fájlkezelő (Start → Fájlkezelő, vagy Ctrl+Alt+E)

- [ ] Két panel, Tab vált; Enter be, Backspace ki; betűk gépelésével ugrás
- [ ] Insert / Szóköz jelöl (Szóköz mappán: kiszámolja a méretét), Ctrl+A mind, Num + minta szerint
- [ ] F5 másolás / F6 mozgatás a másik panelbe (a cél szerkeszthető), már létező fájlnál kérdez
- [ ] F7 új mappa, Shift+F6 átnevezés, F8 / Del törlés (kérdez), Ctrl+H rejtett fájlok
- [ ] F3 nézőke (szöveg, kép, archívum tartalma), F4 szerkesztő (Ctrl+S mentés) — pl. `/data/printer/config/printer.cfg`
- [ ] Alt+F7 keresés (név minta, szöveg a fájlban), Shift+F2 könyvtár-összehasonlítás
- [ ] Alt+F5 ZIP-be tömörítés, Alt+F9 kicsomagolás
- [ ] Húzás egérrel a másik panelre = másolás (Shift = mozgatás); jobb gomb: helyi menü
- [ ] **Alt+F1 / Alt+F2: meghajtók** — itt látszik a Mint lemeze is (csatolatlanul); rákattintva csatolódik
- [ ] Pendrive bedugása → értesítés „Meghajtó csatlakoztatva”, kattintásra megnyílik; írható
- [ ] Meghajtó-menü → „Meghajtó kiadása” → a pendrive kihúzható

## C) Beállítások (Start → Beállítások, Ctrl+Alt+S)

- [ ] **Wi-Fi**: a hálózatok jelerősséggel; kapcsolódás jelszóval; bontás; elfelejtés
- [ ] **Kijelző**: a panel felbontása; más módra váltás → 15 mp alatt „Megtartás”, különben visszaáll
- [ ] **Eszközök**: Lézer (GRBL) szerep — csatlakoztatva: ttyUSB0 → /dev/fusion/laser, COM3
- [ ] **Nyomtató**: Klipper ready, a három szolgáltatás active; Fluidd / Mainsail gomb
- [ ] **Programkezelő**: LightBurn — Windows, Indítás gomb (részletek: `docs/M6f-programkezelo.md`)
- [ ] **Asztal**: háttérszín váltás (újraindítás után is megmarad)
- [ ] **Rendszer**: verzió 0.0.18, A slot, sdb, memória, lemezek

## D) Visszajelzés

Fotó a panelről nyitott Start menüvel és a Fájlkezelőről, plusz ami furcsa, lassú vagy hiányzik.
A LightBurn és a Klipper változatlanul működik (a Start menüből: LightBurn, Nyomtató).

Ha a panel nem jelenik meg: `fusion-shell` (állapot), napló: `~/.local/share/fusion/shell.log`.
