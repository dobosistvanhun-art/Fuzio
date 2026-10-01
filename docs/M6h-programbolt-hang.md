# M6h — Programbolt és hang: ellenőrzés a ZBookon (0.0.20)

## Frissítés (Mint) — a DATA megmarad

```bash
cd ~/Fusion
rm -rf fusionos-regi && mv fusionos fusionos-regi
tar xzf fusionos-m6h.tar.gz
cp -r fusionos-regi/build/cache fusionos/build/
cd fusionos
build/fusion-build all
sudo build/fusion-build update /dev/sdb      # megerősítés: sdb
```

## A) Programbolt (Start → Programbolt, vagy Beállítások → Programbolt)

A Flathub katalógusa magyarul, ahol van fordítás. A telepítést a Programkezelő háttere végzi
(`fusion-programs install flathub:<azonosító>`), a végén értesítés jön, a program a Start menübe kerül.

- [ ] Megnyitáskor: **Népszerű programok** ikonokkal (az ikonok pár mp alatt töltődnek be)
- [ ] Kategóriagombok: Grafika, Iroda, Fejlesztés, Internet, … — a lista vált
- [ ] Keresés: pl. `inkscape`, `freecad`, `kicad` → találatok; „Továbbiak” a lista alján
- [ ] Egy programra kattintva: nagy ikon, leírás, változat, letöltési / telepített méret, licenc, képernyőképek
- [ ] **Telepítés** → felül a folyamat sora; a végén „Telepítés: kész” értesítés; a gomb **Indítás** lesz
- [ ] Már telepített program (pl. Inkscape) mellett „Telepítve”, a részleteknél **Indítás**
- [ ] Internet nélkül: érthető hibaüzenet („a Flathub nem érhető el — van internet?”)

## B) Hang (PipeWire)

- [ ] Panel: hangszóró-jel a harang mellett; fölé víve: hangerő és a kimenet neve
- [ ] Görgetés a jelen: hangerő ±5%; középső gomb: némítás
- [ ] Kattintás: felugró — csúszka, némítás, kimenetek (hangszóró / HDMI), mikrofon, **Próbahang**
- [ ] A gép **hangerőgombjai** (Fn + hangerő): fel / le / némítás — a panel jele követi
- [ ] Beállítások → **Hang**: kimenetek (Ez legyen, Próba), csatlakozók (hangszóró / fejhallgató), mikrofon,
      100% fölötti erősítés, a hangkiszolgáló újraindítása
- [ ] Fejhallgató bedugása → a hang átvált (a csatlakozó a Beállításokban is látszik)
- [ ] **Firefox (Flatpak): YouTube-videó hanggal**
- [ ] LightBurn és a Klipper változatlanul működik

## Parancssor

```bash
fusion-sound                 # állapot: kiszolgáló, kimenetek, bemenetek
fusion-sound test            # próbahang
fusion-sound set 60          # hangerő
cat /proc/asound/cards       # a hangkártyák a kernelben
```

## Visszajelzés

Fotó a Programboltról (egy program részleteivel) és a hang-felugróról; ha nincs hang: a `fusion-sound`
és a `cat /proc/asound/cards` kimenete.
