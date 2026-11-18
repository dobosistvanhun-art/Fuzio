# W2 — Frissítés a forrásból a Programkezelőben (0.0.78)

István kérése (2026-11-18): a két játék (Vas & Króm, Ördögös Motoros) — és a SolidCraft — frissüljön a
Programkezelőből, mint a többi program, ne kelljen kézzel fordítani és telepíteni.

## Hogyan működik
- Telepítéskor a projekt szkriptje átadja a forrást: `fusion-programs install CSOMAG --name NÉV --from-source MAPPA
  --build PARANCS --version V`. A leíróba (`/data/programs/<id>/program.fusion`) kerül: `build.dir`, `build.cmd`,
  `version`. Újratelepítéskor a korábbi forrás megmarad, ha most nincs megadva.
- A Programkezelő az ilyen programnál „Frissítés a forrásból” gombot mutat (Programok → a program sora). A gomb
  (`fusion-programs update <id>`):
  1. ha a forrásban commitolatlan módosítás van: megáll, nem frissít („nem mentett módosítás van”) — semmi nem vész el;
  2. `git pull --ff-only` (csak előre; eltérő történetnél megáll);
  3. a fordító parancs a forrás mappájában (`bash -lc`), naplóval — ez fordít a Fejlesztődobozban és újratelepít;
  4. a végén: „kész (változat)”.
- `fusion-programs source <id>` (JSON): hány új commit van a távoli ágon (`git fetch` után).

## A projektek
| Program | Fordító parancs (a forrás mappájában) |
|---|---|
| SolidCraft | `bash scripts/fuzio-build.sh` |
| Ördögös Motoros | `bash scripts/fuzio-build.sh` |
| Vas & Króm (új) | `sh tools/fusion-install.sh --build` |

A szkriptek csak akkor adják át a forrást, ha a Programkezelő már ismeri (`fusion-programs help` → `--from-source`);
a régebbin a megszokott módon telepítenek.

## Ellenőrzés
- Felhőben (forrásból): hamis projekt helyi git-tárolóval: telepítés → `source` → 1 új commit → `update` → „kész
  (1.1)”, az új változat fut; commitolatlan módosításnál „nem frissítek”. A három szkript hamis Programkezelővel: az
  újjal átadja a forrást, a régivel nem. `fusion-settings --selftest` → QML ok, SLOTS ok.
- Rendszerkép-önteszt: `fusion-selftest` → `FUSION-PROG: SOURCE behind=1 update=[kész (1.1)] dirty-refused=1 run=1.1`.
- **A ZBookon (még nem próbált):** a 0.0.78 telepítése után egyszer kézzel újra kell telepíteni a három programot
  (hogy a forrás bekerüljön), utána: Programok → „Frissítés a forrásból”.

## Visszavonás
`git revert` a commitra; a már telepített programok leírásában maradó `build.*` sorokat a régi Programkezelő figyelmen
kívül hagyja.
