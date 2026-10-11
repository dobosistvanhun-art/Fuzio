# Leírók — 1-es változat

Mindhárom fájl formátuma (`fusion.kv`): `kulcs = érték` sorok, `#` megjegyzés, UTF-8. Az érték a sor végéig tart,
a szélein lévő szóközök nélkül. Ellenőrzés: `fusion validate <fájl>…`, Pythonból `fusion.schema.validate_file()`.

| Fájl | Hely | Ki írja |
| --- | --- | --- |
| `program.fusion` | `/data/programs/<id>/program.fusion` | a Programkezelő (telepítéskor, a Beállításokban) |
| `<id>.fwr` — recept | `/usr/lib/fusion/fwr/profiles/` | a FusionOS (rendszerkép): ismert Windows-programok gyári beállításai |
| `<Flatpak-azonosító>.recipe` — Linux-recept | `/usr/lib/fusion/programs/recipes/` | a FusionOS (rendszerkép): ismert Linux-programok kiegészítései (pl. URL-séma) |
| `NN-<szerep>.role` | `/usr/lib/fusion/devices/roles/` | a FusionOS (rendszerkép): eszközszerepek |

## program.fusion és *.fwr recept

**Egy séma.** A recept a `program.fusion` sémája: a `type` alapértelmezése `win64`, és csak benne van `match` kulcs
(a telepítőfájl nevének mintája, erről ismeri fel a Programkezelő).

| Kulcs | Kötelező | Alak | Típusnál | Leírás |
| --- | --- | --- | --- | --- |
| `id` | igen | id | mind | azonosító: kisbetű, szám, . _ - (max. 64); egyezik a mappa nevével |
| `name` | igen | text | mind | a program neve a felületen |
| `type` | igen | enum (win64, flatpak, appimage, native) | mind | a program típusa (recept: alapértelmezés win64) |
| `version` |  | text | mind | verzió (tájékoztató) |
| `comment` |  | text | mind | rövid leírás |
| `icon` |  | text | mind | ikon: fájl a program mappájában vagy a Fusion ikonkészlet neve |
| `icon_tile` |  | text | mind | a csempe ikonneve, ha az icon fájl |
| `categories` |  | list; | mind | freedesktop-kategóriák pontosvesszővel (a Start menü csoportja) |
| `open` |  | exts | mind | fájltársítás: kiterjesztések szóközzel (.lbrn .svg) |
| `mime` |  | list; | mind | fájltársítás: MIME-típusok pontosvesszővel |
| `installed` |  | text | mind | a telepítés ideje (a Programkezelő írja) |
| `source` |  | text | mind | honnan települt (fájlnév, flathub …) |
| `recipe` |  | text | mind | a recept fájlneve, amelyből a leírás készült |
| `exe` |  | winpath | win64 | a program Windows-útja (C:\…\x.exe) |
| `windows` |  | enum (win7, win8, win81, win10, win11) | win64 | a jelentett Windows-verzió |
| `prefix` |  | abspath | win64 | a Windows-környezet mappája (alapértelmezés: /data/fwr/<id>) |
| `dlloverrides` |  | text | win64 | Wine DLL-felülírások (kísérleti futtató) |
| `places` |  | enum (standard, none) | win64 | a Fusion helyei a fájlválasztóban (D: Adatok, E: pendrive, Asztal) |
| `port.COMn` |  | role | win64 | soros port → eszközszerep (port.COM3 = laser) |
| `drive.X` |  | dir | win64 | meghajtóbetű → mappa (abszolút, vagy a saját mappához képest) |
| `match` |  | text | win64 (csak recept) | recept: a telepítőfájl nevének mintája (LightBurn*.exe) |
| `appid` |  | appid | flatpak | Flatpak-azonosító (com.prusa3d.PrusaSlicer) |
| `installation` |  | enum (user, system) | flatpak | Flatpak-telepítés helye |
| `exec` |  | relpath | appimage, native | az indítófájl a program mappájához képest |

A `scheme` és az `url_args` kulcs (0.0.39): a program által kezelt URL-sémák (`prusaslicer`) és az URL-es indítás kapcsolói (`--single-instance-on-url`); az XDG-bejegyzésbe `x-scheme-handler/<séma>` kerül.

Típusonként kötelező: `win64`: `exe`; `flatpak`: `appid`; `appimage`, `native`: `exec`.
`port.COMn`: n = 1…9, az érték egy szerep neve (`port.COM3 = laser`). `drive.X`: X = D…Y.
Ha `places = standard` (alapértelmezés), a Fusion helyei: D: Adatok, E: pendrive, Asztal. Ezekkel a betűkkel a
`drive.X` nem ütközik, mert a profil saját betűje elsőbbséget kap.

### Elsőbbségi szabály (egy helyen: `fusion.schema.apply_recipe`)

1. Telepítéskor és újratelepítéskor a Programkezelő a recept kulcsait a leírásba írja (`recipe = <fájlnév>`).
   A recept `match` kulcsa nem kerül át.
2. A felhasználó beállításai — `port.*`, `drive.*`, `places` — a leírásból maradnak, ha ott már van ilyen családú
   kulcs. Például a Beállításokban átállított COM-port egy újratelepítés után is megmarad.
3. Futáskor a leírás önmagában teljes: az `fwr` és a Programkezelő csak a leírást olvassa.
   Recept nélküli (általános) Windows-programnál csak a leírás van.

## *.role — eszközszerep

| Kulcs | Kötelező | Alak | Típusnál | Leírás |
| --- | --- | --- | --- | --- |
| `role` | igen | role | mind | a szerep neve: kisbetű, szám, _ - (max. 32); /dev/fusion/<szerep> |
| `name` | igen | text | mind | a szerep neve a felületen |
| `match.usb` | igen | usbids | mind | illeszkedő USB-eszközök: vid:pid szóközzel |
| `identify` |  | enum (serial, path) | mind | azonosítás: serial (sorozatszám) vagy path (fizikai USB-port) |
| `windows.com` |  | com | mind | javasolt COM-port a Windows-programoknak (a program leírója dönt) |

A szerep a `/dev/fusion/<szerep>` néven érhető el. Új szerep (pl. CNC, kamera) egy új szerepfájllal jön létre,
kódváltozás nélkül. A `windows.com` csak javaslat: a Windows-programok ténylegesen használt COM-portja a program
leírójában van (`port.COMn`).
