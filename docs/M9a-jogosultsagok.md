# FusionOS 0.0.41 (m9a) — jogosultságok, első lépés

Terv és döntések: projekt-dokumentum `claude/M9-Jogosultsagi-modell-terv.md` (7a. fejezet).
István feltétele: **a Klipper és a LightBurn nem módosul** — ez a csomag egyiket sem érinti.

## Mi változott

- **`input` csoport kikerült** a felhasználóból.
  - Eddig bármely program olvashatta a billentyűzet és az egér nyers eseményeit, így egy rossz program a
    billentyűleütéseket is gyűjthette volna.
  - Az Xorg nélküle is megnyitja a bemeneti eszközöket (root nélkül a logind-on át, rootként magától). QEMU-ban mérve.
- **Hibajelentés → JOGOSULTSÁGOK**: a felhasználó csoportjai, a homokozó beállítása, a nem csak helyi figyelő portok
  és a programok jogai (eszköz, mappák, hálózat, védelem).
- **Programkezelő → program → „Védelem”**: hogyan fut a program.
  - Flatpak: a saját homokozójában.
  - Windows-program: homokozó nélkül; a Windowsban csak a megadott meghajtók látszanak.
  - AppImage / archív program: teljes hozzáféréssel.
- **Leíró (program.fusion)**: új kulcsok `allow.files`, `allow.net`, `sandbox` (lásd `docs/api/leirok.md`).
  Újratelepítéskor megmaradnak, mint a COM-port beállítása.
- **Fusion API**: a `fusion.permissions.check` mostantól a leírás szerint dönt. A FusionOS saját programjai és a
  szkriptek mindent elérnek, ismeretlen program semmit. `fusion permissions [id] --json`.

## Ami szándékosan nem változott

- A 3D nyomtató webes elérése (Moonraker, Fluidd) — a Klipper-csomag része. A hibajelentés mutatja a figyelő portokat.
- A LightBurn futtatása és beállításai.

## Ellenőrzés a ZBookon

1. Billentyűzet, érintőpad, USB-egér, hangerőgombok, Ctrl+Alt+Del — működnek-e (az `input` csoport nélkül).
2. Programkezelő → LightBurn → a „Védelem” sor látszik; a LightBurn indul, a lézer COM3-on elérhető, ahogy eddig.
3. Beállítások → Hibajelentés → a JOGOSULTSÁGOK rész.
