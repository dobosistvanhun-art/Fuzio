# M7b — Frissítés fájlból (Beállítások), Feladatkezelő: ellenőrzés a ZBookon (0.0.25)

## 1. Frissítés 0.0.24 → 0.0.25 — utoljára Minten

```bash
cd ~/Fusion
rm -rf fusionos-regi && mv fusionos fusionos-regi
tar xzf fusionos-m7c.tar.gz
cp -r fusionos-regi/build/cache fusionos/build/
cd fusionos
build/fusion-build all
sudo build/fusion-build update /dev/sdb      # megerősítés: sdb
```

Újraindítás, F9 → FusionOS → az asztalon pár másodperc múlva értesítés: **„Rendszerfrissítés kész”**.

## 2. Feladatkezelő (Ctrl+Alt+Del)

- [ ] **Ctrl+Alt+Del** (vagy Ctrl+Shift+Esc, vagy Start → Rendszer → Feladatkezelő) → megnyílik
- [ ] Felül: processzor, memória, futó programok száma
- [ ] **Programok**: a nyitott programok (LightBurn, Firefox, Fájlkezelő …) — Windows-program a Programkezelő
      nevén, a Wine minden folyamatával együtt
- [ ] Ha egy program lefagy: piros **„Nem válaszol”** címke, a lista elején
- [ ] **Bezárás**: mint az ablak X gombja (a program rákérdezhet a mentésre)
- [ ] **Kényszerített bezárás** → megerősítés → a program azonnal leáll (Windows-programnál a teljes Wine-környezete)
- [ ] **Folyamatok** fül: a saját folyamatok CPU és memória szerint; „Folyamat leállítása”
- [ ] Ha már nyitva van, a Ctrl+Alt+Del előre hozza
- [ ] A szöveges konzolon (Ctrl+Alt+F2) a Ctrl+Alt+Del nem indítja újra a gépet

## 3. Rendszerfrissítés fájlból — az ezutáni frissítések így mennek, Mint nélkül

A build mostantól egyetlen fájlt is készít: `build/out/release/fusionos-0.0.25-m7-<idő>.fupd` (~900 MB).
A ZBook-próbához egy **újabb build** kell (ugyanazt a buildet nem telepíti újra — nem újabb a futónál):

```bash
cd ~/Fusion/fusionos
build/fusion-build all       # új build (új időbélyeg), új .fupd
cp build/out/release/fusionos-*.fupd /media/$USER/<pendrive>/      # vagy a FusionOS DATA-jára: /data/import
```

- [ ] FusionOS: a pendrive bedugva → Beállítások → **Rendszerfrissítés** (vagy Rendszer → Rendszerfrissítés)
- [ ] Látszik: futó rendszer (verzió, slot), a két slot állapota, és a talált `.fupd` fájl
- [ ] **Telepítés** → napló: ellenőrzés (SHA-256), írás %, visszaolvasás, „KÉSZ”; értesítés
- [ ] **Újraindítás most** → a gép a FusionOS-be indul vissza (nem a Mintbe), az új rendszer próbaként,
      utána értesítés: „Rendszerfrissítés kész”
- [ ] Rendszerfrissítés oldal: az új slot „véglegesített — fut”, a régi tartaléknak megmaradt

Parancssorból ugyanez: `sudo /usr/lib/fusion/bin/fusion-admin update-apply /data/import/fusionos-….fupd`,
majd `sudo /usr/lib/fusion/bin/fusion-admin update-reboot`.
