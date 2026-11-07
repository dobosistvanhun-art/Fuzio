# W2 — 7z-archívumok kicsomagolása (0.0.77)

**Mi készült:** a rendszerképbe bekerült a `7zip` csomag (`7z` parancs, a parancssorban is). A Fájlkezelő
Kicsomagolás (Alt+F9, jobb gomb) a `.7z`-t is kibontja, a megnézése (F3) kilistázza a tartalmát.

**Hogyan:** a 7-Zip a cél mappán belüli rejtett ideiglenes mappába (`.fusion-7z-…`) bont ki, onnan kerül minden a
helyére. A célon kívülre mutató hivatkozás kimarad (a hibalistában látszik), a meglévő fájlokra a felülírás-beállítás
érvényes. Közben folyamatjelzés van, és megszakítható; a végén az ideiglenes mappa törlődik.

**Korlátok:**
- jelszavas 7z: a Fájlkezelő jelszót még nem kér, ezt hibaként kiírja. Megoldás a Terminálban, az archívum mappájában:
  `7z x "név.7z"` (ott kérdezi a jelszót);
- RAR: az Ubuntu 7zip csomagja nem bontja ki (a `7zip-rar` a multiverse-ben van, nem szabad licencű, nincs benne).

## Ellenőrzés

| Mit | Hol | Eredmény |
| --- | --- | --- |
| `fusion-files --selftest`: 7Z (kibontás, egyező tartalom, nem marad ideiglenes mappa), 7ZLIST, 7ZSKIP (kihagyás meglévőnél) | felhőben, Ubuntu 24.04, 7-Zip 23.01 | ok |
| jelszavas 7z (fejléc-titkosítással és anélkül): érthető hibaüzenet, nem akad meg | felhőben | ok |
| a telepített 0.0.77 a ZBookon: Alt+F9 egy letöltött .7z-n, F3 megnézés | ZBook | **nincs ellenőrizve** |
