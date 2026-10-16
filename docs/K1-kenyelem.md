# 0.0.47 (k1) — kényelmi kiadás

## 1. Jobb gombos szövegmenü

Új FusionUI-elem: `FTextMenu` (`desktop/qml/FusionUI/FTextMenu.qml`). Jobb gombra menüt nyit:
Visszavonás, Kivágás, Másolás, Beillesztés, Törlés, Mindent kijelöl (a billentyűparancsok mellette).

- Az `FTextField` beépítve tartalmazza, így minden Fusion-program minden egysoros mezője tudja.
- Külön bekötve: a Fájlkezelő szerkesztője (F4) és nézője (F3), a Hibajelentés két szövegdoboza, a Start menü keresőmezője.
- A bal gombot nem fogja el (kijelölés, kurzor a mezőé marad). A jobb gomb a kattintás helyére teszi a kurzort, ha nincs kijelölés (a beillesztés oda kerül).
- Jelszómezőből nem lehet kivágni vagy másolni; csak olvasható mezőben csak a Másolás és a Mindent kijelöl él.
- Új programban: `TextArea { … FTextMenu {} }`.

## 2. Terminál: LXTerminal

Az xterm nem tud jobb gombos Másolás / Beillesztés menüt. A jelöltek mérése a FusionOS 0.0.46 csomaglistáján
(noble, `--no-install-recommends`, a képben már meglévő csomagok nélkül):

| Terminál | új csomag | kb. méret | megjegyzés |
|---|---|---|---|
| **LXTerminal** | lxterminal, libvte-2.91-0, libvte-2.91-common | ~1,3 MB | GTK3 + VTE; a GTK3 már a képben van; magyar fordítás |
| Sakura | sakura + a két VTE-csomag | ~1,0 MB | kevesebb menüpont, gyengébb fordítás |
| Xfce Terminal | + xfconf, libxfce4ui, exo… (~10 csomag) | több MB | Xfce-könyvtárakat hoz |
| QTerminal | + a teljes Qt 5 | ~40 MB+ | a képben csak Qt 6 van |

Választás: **LXTerminal**. Indítása mindenhol a `fusion-terminal` parancson át történik (`desktop/bin/fusion-terminal`):

- Sötét GTK-téma (`GTK_THEME=Adwaita:dark`) csak a terminálnak. A rendszer többi GTK-programját, például a Firefoxot, nem érinti.
- Paraméterek: `-t cím`, `--working-directory=MAPPA`, `-e parancs …`.
- Ha az LXTerminal hiányzik, xterm indul ugyanezekkel.

A Fusion-színek a rendszerszintű beállításban vannak: `/usr/share/lxterminal/lxterminal.conf`.
A felhasználó a Terminál → Beállítások menüben átírhatja; ez a `~/.config/lxterminal/` mappába kerül.

Billentyűk: Ctrl+Shift+C / Ctrl+Shift+V (másolás / beillesztés), Ctrl+Shift+T (új fül).
Az F10 a programoké (pl. mc), nem a menüé.

Az xterm a képben marad tartaléknak, és a telepítő is ezt használja.

## 3. Tálca: a futó programok ikonjai

A tálcagomb ikonját a Fusion Shell ablakosztályonként egyszer keresi meg, ebben a sorrendben:

1. a Fusion saját programjai (apps.json, a parancs neve szerint);
2. a Programkezelőben telepített program saját ikonja (a program azonosítója, neve vagy Flatpak-azonosítója szerint);
3. az ablak saját ikonja (`_NET_WM_ICON`). PNG-ként a `$XDG_RUNTIME_DIR/fusion-winicons/` mappába kerül; így látszik a Firefox, a PrusaSlicer és a Wine-programok saját ikonja is;
4. általános programikon.

Ha a program az ikonját csak később adja meg, a Shell 5 másodpercig újra próbálja.

## Ellenőrzés a ZBookon

- [ ] Beállítások → bármelyik szövegmező: jobb gomb → menü; Másolás, majd Beillesztés egy másik mezőbe.
- [ ] Fájlkezelő → F4 egy szövegfájlon: jobb gomb → Kivágás / Beillesztés.
- [ ] Start menü keresőmező: jobb gomb → Beillesztés.
- [ ] Terminál (Start → Terminál, vagy Ctrl+Alt+T): sötét, magyar menü; jelölés → jobb gomb → Másolás; jobb gomb → Beillesztés.
- [ ] Fájlkezelő → Terminál itt: a terminál a megnyitott mappában indul.
- [ ] Tálca: a Firefox, a PrusaSlicer és a LightBurn a saját ikonjával látszik.
