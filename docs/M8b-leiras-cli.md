# FusionOS 0.0.36 — M8b: a Fusion API leírása, a `fusion` parancs, sémák, feladat-protokoll

A `M8-Fusion-API-terv.md` 7. fejezete szerint (D1–D4 elfogadva).
A felhasználó számára **kevés látható változás**: a Beállítások hosszú műveletei most a közös feladat-protokollon futnak.

## Mi változott

| | |
| --- | --- |
| `docs/api/` | a Fusion API leírása magyarul: áttekintés, `fusion` parancs a JSON-kimenetekkel, leírók (`program.fusion` 1, `*.fwr`, `*.role` 1), feladat-protokoll, Python-modulok |
| `fusion` parancs | `fusion system / hardware / devices / volumes / programs / notify / jobs / schema / validate`, minden lekérdezés `--json`-nal is |
| `fusion.schema` | a leírók formális sémája és ellenőrzése. A recept = a `program.fusion` sémája. Az elsőbbségi szabály egy helyen (`apply_recipe`): újratelepítéskor a recept technikai kulcsai frissülnek, a felhasználó beállításai (`port.*`, `drive.*`, `places`) megmaradnak — eddig a recept felülírta a Beállításokban átállított COM-portot |
| `fusion.jobs` | feladat-protokoll (`LÉPÉS i/n:`, `PROGRESS`, kilépési kód). Állapot: `$XDG_RUNTIME_DIR/fusion/jobs/<név>.json`. A Beállítások telepítés / eltávolítás / frissítés / rendszerfrissítés / mentés / telepítő pendrive / hibajelentés műveletei ezen futnak (eddig: saját shell-szkript, `~/.local/share/fusion/*-job.*`) |
| `fusion.ui` | a rajzolási mód Qt nélkül (a parancssor és a hibajelentés is innen olvassa — eddig két helyen volt) |

## Ellenőrzés

- Egységtesztek (`tests/fusion-api-test.py`, a build `test` lépésében): 40 teszt — sémák, elsőbbség, feladatok, parancssor.
- QEMU: minden `fusion … --json` kimenet a `docs/api/cli.md` kulcsaival; `fusion validate` a rendszerkép receptjein
  és szerepfájljain; a Beállítások hibajelentése a `fusion.jobs`-on át.

## A ZBookon (nem kötelező)

Terminál:
```bash
fusion system
fusion devices
fusion validate /data/programs/*/program.fusion
```
