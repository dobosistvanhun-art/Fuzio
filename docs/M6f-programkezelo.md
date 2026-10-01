# M6f — Fusion Programkezelő: ellenőrzés a ZBookon (0.0.19)

A Programkezelő a programok egységes kezelője: **minden program egy leírás a DATA-n**
(`/data/programs/<id>/program.fusion`), a felület (Start → **Programkezelő**, Beállítások → Programkezelő,
Start menü, Fájlkezelő) és a parancssor (`fusion-programs`, `fusion-run`) ugyanezt használja.
A QML csak kér — a műveletet a háttér (`fusion-programs`) végzi, külön folyamatban; a végén értesítés jön.

| típus | honnan | futtató |
|---|---|---|
| Windows (win64) | .exe / .msi telepítő, hordozható .exe | fwr — ma Wine-alapú, **kísérleti M4-megoldás** |
| Linux (Flatpak) — **fő formátum** | Flathub-keresés, .flatpakref, .flatpak | `flatpak run` (homokozó, portálok) |
| Linux (AppImage) | .AppImage | kibontva (FUSE nem kell) |
| Linux | tar.gz / tar.xz / zip, önálló bináris | a program saját indítófájlja |

## Frissítés (Mint) — a DATA megmarad

```bash
cd ~/Fusion
rm -rf fusionos-regi && mv fusionos fusionos-regi
tar xzf fusionos-m6f.tar.gz
cp -r fusionos-regi/build/cache fusionos/build/
cd fusionos
build/fusion-build all
sudo build/fusion-build update /dev/sdb      # megerősítés: sdb
```

Újraindítás → F9 → FusionOS. Bejelentkezéskor a Programkezelő **átköltözteti** a meglévő programokat
(újratelepítés nélkül): a LightBurn leírást kap a régi helyén (`/data/fwr/lightburn` marad), a korábban
parancssorból telepített Firefox (Flatpak) is bekerül a listába.

## A) Átköltöztetés

- [ ] Start menü: **LightBurn** (saját ikonnal, a programból kiolvasva) és **Firefox** (ha a mérés óta fent van) a lista elején
- [ ] Start → Programkezelő: LightBurn — „Windows”, Firefox — „Linux (Flatpak)”, mellettük a méret
- [ ] LightBurn sorára kattintva: Program `C:\Program Files\LightBurn\LightBurn.exe`, Windows-környezet
      `/data/fwr/lightburn`, **Eszköz: Lézer (GRBL) — hozzáfér, COM3**
- [ ] LightBurn **Indítás** → elindul, a lézer COM3-on (az első indításnál a környezet egyszer frissül)
- [ ] Firefox **Indítás** → elindul; **Frissítés** gomb → a napló a lap tetején, a végén értesítés

## B) Telepítés — Windows (próbatelepítő)

- [ ] Programkezelő → Telepítés fájlból: írja be `/usr/lib/fusion/programs/tests/fusionteszt-setup.exe` →
      alatta „Windows-program (x64)” → **Telepítés**
- [ ] Néhány mp múlva: „Telepítés: kész” értesítés; a listában **FusionTeszt** (Windows), saját ikonnal
- [ ] Start menü → FusionTeszt → 20 mp-re megnyílik egy „FusionTeszt” ablak
- [ ] Sorára kattintva: Eszköz: Lézer — „nem fér hozzá” → **Engedélyezés (COM3)** → „hozzáfér” (Tiltás vissza)
- [ ] **Eltávolítás** → megerősítés → eltűnik a listából és a Start menüből

## C) Telepítés — Linux

- [ ] Programkezelő → Flathub: keresés pl. `inkscape` → **Telepítés** (internet kell, percekig tarthat) →
      értesítés; a Start menüben megjelenik, indul
- [ ] Terminálból telepített Flatpak (`flatpak install flathub …`) **néhány másodpercen belül** megjelenik a
      Start menüben és az irányítópulton (0.0.19 — a 0.0.18 csak a következő bejelentkezéskor vette fel);
      a terminálból eltávolított eltűnik
- [ ] Fájlkezelőben egy `.exe` / `.msi` / `.AppImage` / `.flatpakref` fájlon **Enter** → a Programkezelő
      ezzel a fájllal nyílik; tar.gz-n jobb gomb → „Telepítés a Programkezelővel”

## D) Fájltársítás

A Fusion-társítás (`open =`, pl. `.lbrn` → LightBurn) Enterre mindig érvényes. A Linux-programok MIME-igénye
(pl. az Inkscape-é a PDF-re) csak ott, ahol a beépített nézőke nem tudja megmutatni a fájlt — kép, szöveg,
archívum Enterre a nézőkében nyílik (F3 ugyanaz).

- [ ] Fájlkezelő: egy `.lbrn` / `.lbrn2` fájlon **Enter** → a LightBurn nyitja meg — a fájl a `~/Projektek`
      mappában legyen (a LightBurn ezt látja **P:** meghajtóként; más mappából „nincs a program látókörében”
      értesítés jön)

## Parancssor

```bash
fusion-programs                    # a telepített programok
fusion-programs info lightburn     # részletek (JSON)
fusion-programs install <fájl>     # vagy: flathub:org.inkscape.Inkscape
fusion-programs remove <id> [--data]
fusion-run <id> [fájl]
```

## Visszajelzés

Fotó a Programkezelőről (LightBurn sora kinyitva) és a Start menüről, plusz ami furcsa vagy hiányzik.
Napló: `~/.local/share/fusion/programs-job.log` (az utolsó művelet), fwr: `~/.local/share/fusion/fwr/<id>.log`.
