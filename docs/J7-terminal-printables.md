# FusionOS 0.0.39 (j7) — Terminál: másolás és beillesztés; Printables → PrusaSlicer a Firefoxból

## Terminál (xterm)

| | |
| --- | --- |
| Beillesztés | **Ctrl+V** vagy **Ctrl+Shift+V** (és Shift+Insert, középső egérgomb). Más programokból (Firefox, Claude) kimásolt szöveg is beilleszthető. |
| Másolás | Kijelöléssel (azonnal a vágólapra kerül), vagy **Ctrl+Shift+C**. |
| Ctrl+C | Marad a futó parancs megszakítása. |
| Több soros beillesztés | Soronként lefut; nem kerülnek a sorba „^[[200~” jelek. A bash „bracketed paste” módja ki van kapcsolva (`/etc/inputrc`). |

## Printables → PrusaSlicer

Mért ok (0.0.38, ZBook):
- A PrusaSlicer Printables fülének beépített böngészője (WebKitGTK) a 3D-előnézethez olyan rajzolási módot kér, amit az NVIDIA 470-es driver nem tud.
- NVIDIA-drivert erőltetve leáll („EGL_BAD_PARAMETER”). Enélkül a processzor rajzol, és akadozik.
- Ezen beállítással nem lehet segíteni, és a Flatpakon kívüli PrusaSlicerrel sem lenne jobb.
- A Firefoxban a Printables 3D-nézete sima.

Ezért:
- **A Printables „Open in PrusaSlicer” gombja a Firefoxból a PrusaSlicerbe tölti a modellt.** A FusionOS bejegyzi a PrusaSlicert a `prusaslicer://` linkekhez. Ha a PrusaSlicer már fut, az a példány veszi át (`--single-instance-on-url`), nem nyílik második ablak.
- Általános megoldás:
  - A Linux-programoknak is lehet **receptje** (`/usr/lib/fusion/programs/recipes/<Flatpak-azonosító>.recipe`). A séma ugyanaz, mint a `program.fusion`-é.
  - Új kulcsok: `scheme` (a kezelt URL-sémák) és `url_args` (kapcsolók URL-es indításhoz).
  - A már telepített PrusaSlicer a következő szinkronnál megkapja: ez bejelentkezéskor vagy a Programkezelő megnyitásakor történik.

## Ellenőrzés a ZBookon

1. **Terminál**: másolj ki egy parancsot innen, és illeszd be Ctrl+V-vel. Több sor is működik.
2. **Firefox → printables.com → egy modell → „Open in PrusaSlicer”**:
   - Ha a böngésző rákérdez, hogy megnyissa-e: Megnyitás (érdemes bepipálni, hogy megjegyezze).
   - Ezután a PrusaSlicerben letöltődik és betöltődik a modell.
