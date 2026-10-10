# FusionOS 0.0.30 (j1) — javító kör + az alaprendszer-vizsgálat első lépései

István megfigyelései (0.0.29 után) és az elfogadott A1–A6 javaslatok (`Alaprendszer-vizsgalat.md`).

## Mi változott

| | Változás |
| --- | --- |
| Programkezelő | A telepített programok listája **azonnal** megjelenik; a Flatpak-szinkron és a telepítőfájlok keresése utána, a háttérben fut. A keresés kihagyja a csatolt köteteket (Google Drive, pendrive), és legfeljebb 5 mp-ig tart — eddig a Google Drive bejárása okozta az 1–2 perces várakozást. Időmérés: `$XDG_RUNTIME_DIR/fusion-timing.log`. |
| Asztal → Programok | Nagyobb kártya (max. 780 px széles) és nagyobb csempék (128×96, 42 px-es ikon, kétsoros név); **csoportok** a Start menü szerint (Műhely, Internet, Rendszer…) — „Összes” fülön csoportcímekkel; sok programnál **görgethető**. |
| Feladatkezelő | A memória **PSS** (arányos memória): a megosztott könyvtárakat (Qt, Python) a használók között osztja el — az RSS ezeket minden folyamatnál teljesen számolta, ezért túlbecsült. A fejlécben: megosztott (tmpfs), kernel, gyorsítótár. |
| Mérés: felület memóriája | Új boot-bejegyzés: **„mérés: Fusion-felület szoftveres rajzolással”** — a Fusion Shell és a Fusion-programok OpenGL nélkül rajzolnak. A fejlesztői gépen (Xvfb): Fusion Shell **229 MB → 98 MB** PSS. A ZBookon (NVIDIA) mérni kell: memória, és hogy a felület elég gyors-e. Döntés a mérés után. |
| A3 — cache mentése | `build/fusion-build cache-export` → `~/Fusion/fusionos-cache-<dátum>.tar.zst` (+ `.sha256`): a rögzített NVIDIA 470-server csomagok, a kernel, a Wine-, Klipper-forrás, a lefordított modulok. Visszatöltés: `build/fusion-build cache-import <fájl>`. |
| A4 — mérési bejegyzések | **„mérés: Intel grafika”** (`fusion.display.profile=intel-kms`) és **„mérés: Nouveau”** (`fusion.display.profile=nvidia-nouveau`). A Hardware Layer kézi profilválasztása általános: bármely profilazonosító kérhető; ha nem illeszkedik, marad az automatikus választás, figyelmeztetéssel. Az i915 és a nouveau modul bekerült a rendszerképbe (automatikusan nem töltődnek be). |
| Frissítés | A .fupd a hiányzó boot-bejegyzéseket is pótolja (a meglévőket nem bántja) — így a 0.0.29-ről frissítve is megjelennek az új mérési bejegyzések. |

## Build és frissítés (Minten, ~/Fusion)

```bash
cd ~/Fusion
rm -rf fusionos-regi && mv fusionos fusionos-regi
tar xzf fusionos-j1.tar.gz
cp -r fusionos-regi/build/cache fusionos/build/
cd fusionos
build/fusion-build all
build/fusion-build cache-export
```
Az utolsó parancs az A3: a rögzített csomagok mentése → `~/Fusion/fusionos-cache-<dátum>.tar.zst` (kb. 1–2 GB) +
`.sha256` — mindkettőt másold a Google Drive-ra vagy egy külső lemezre.

Utána a szokásos frissítés: a `.fupd` → pendrive → Beállítások → Rendszerfrissítés → Telepítés → Újraindítás most.
A frissítés az új mérési bejegyzéseket is felveszi a boot menübe.

## Ellenőrzés a ZBookon

1. **Programkezelő**: megnyitás → a lista azonnal ott van (nem 1–2 perc). Ha mégis lassú: Terminál →
   `cat $XDG_RUNTIME_DIR/fusion-timing.log`.
2. **Asztal**: a Programok kártya nagyobb, a csoportfülek működnek, sok programnál görgethető.
3. **Feladatkezelő**: Memória (PSS) oszlop; a fejlécben a részletek. Írd fel: a fusion_shell PSS-e és az
   üresjárati „Memória” érték.
4. **Mérés — szoftveres rajzolás**: újraindítás → boot menü (F9 / a FusionOS menüje) → „mérés: Fusion-felület
   szoftveres rajzolással” → Feladatkezelő: a fusion_shell PSS-e; a Start menü, az ablakok, az asztal gördülékeny-e.
5. **Mérés — Nouveau** (a BIOS marad: Hybrid Graphics = **Disable**): boot menü → „mérés: Nouveau” →
   Fusion Desktop indul-e; Beállítások → Kijelző / Hibajelentés: a profil `nvidia-nouveau (manual)`;
   LightBurn 2.1 vászon (nagyítás, mozgatás) sebessége; Firefox: egy videó.
6. **Mérés — Intel HD 4600**:
   - BIOS (bekapcsoláskor **F10**) → Advanced → **Hybrid Graphics = Enable** → mentés (F10).
   - Boot menü → „mérés: Intel grafika” → ugyanazok a próbák; a profil `intel-kms (manual)`.
   - **Utána vissza**: BIOS → Hybrid Graphics = **Disable** — a normál FusionOS (NVIDIA 470) ezt kéri.
   - Ha Enable módban a normál „FusionOS” bejegyzés indul, a Hardware Layer figyelmeztet (több grafikus adapter).
7. **A3**: a `fusionos-cache-….tar.zst` és a `.sha256` biztonságos helyen (lásd fent).

Minden mérés után egy Hibajelentés (Beállítások → Hibajelentés) a legjobb összefoglaló — a kijelzőprofilt,
a memóriát (PSS) és a naplókat is tartalmazza.
