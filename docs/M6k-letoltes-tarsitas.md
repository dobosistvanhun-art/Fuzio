# M6k — Letöltések mappa (Flatpak-programok), „Megnyitás ezzel…”: ellenőrzés a ZBookon (0.0.23)

## Frissítés (Mint) — a DATA megmarad

```bash
cd ~/Fusion
rm -rf fusionos-regi && mv fusionos fusionos-regi
tar xzf fusionos-m6k.tar.gz
cp -r fusionos-regi/build/cache fusionos/build/
cd fusionos
build/fusion-build all
sudo build/fusion-build update /dev/sdb      # megerősítés: sdb
```

## A) Letöltés a Firefoxból (és minden Flatpak-programból)

Ok: a rendszerben nem volt kijelölve a Letöltések mappa (XDG `user-dirs.dirs`). Ilyenkor a homokozóban
futó Firefox a saját, ideiglenes `~/Downloads` mappájába ment — ez a valódi saját mappában nem létezik,
és a Firefox bezárásakor elvész. (A „Mentés másként” ablakon át mentett kép azért látszott, mert azt a
fájlválasztó a kiválasztott valódi mappába írja.) Mostantól a munkamenet indulásakor:
`~/.config/user-dirs.dirs` → `XDG_DOWNLOAD_DIR="$HOME/Letöltések"`, és a mappa létrejön.

- [ ] A Firefoxot **teljesen zárd be és indítsd újra** (a beállítást induláskor olvassa)
- [ ] Tölts le egy AppImage-et → megjelenik a **Letöltések** mappában (Fájlkezelő)
- [ ] A Fájlkezelő bal oldali listájában új hely: **Letöltések**
- [ ] Programkezelő → Telepítés fájlból: a letöltött AppImage a listában
- [ ] A korábban „eltűnt” letöltés sajnos nem állítható vissza — újra le kell tölteni

## B) Megnyitás ezzel… (Fájlkezelő)

- [ ] Jobb gomb egy fájlon → **Megnyitás ezzel…** (vagy **Shift+Enter**)
- [ ] A listában: Fusion nézőke, majd a programok — amelyik jelzi, hogy ismeri a típust, „ajánlott” és elöl
- [ ] Program kiválasztása → Megnyitás: egyszeri megnyitás
- [ ] **„Mindig ezzel nyissa meg a(z) .svg fájlokat”** bepipálva → ezentúl az Enter / dupla kattintás ezzel nyitja
- [ ] Újra Shift+Enter: „Most beállítva: …” → **Alapértelmezés visszaállítása**

## C) Felmérés az M7-hez (A/B frissítés) — nem módosít semmit

1. FusionOS-en, Terminál (Ctrl+Alt+T): `bash /usr/lib/fusion/tools/m7-felmeres.sh` → `m7-felmeres.txt` a saját mappában
2. Minten: `cd ~/Fusion/fusionos && sudo bash tools/m7-felmeres.sh /dev/sdb` → `m7-felmeres.txt` itt

A két `m7-felmeres.txt` tartalmát kérem visszaküldeni.
