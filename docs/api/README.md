# Fusion API — 1-es változat

A FusionOS saját képességeinek közös belépési pontja. A Fusion-programok, a szkriptek és a FusionOS saját
programjai (Shell, Beállítások, Fájlkezelő, Telepítő) ezen keresztül érik el a rendszert.
A Linux-szabványos részeket (fájlok, hálózat, systemd, Qt) nem fedi el, csak ott ad saját felületet, ahol a
FusionOS-nek saját tudása van: eszközszerepek, Hardware Layer, programleírók, hosszú műveletek, értesítések.

Döntések (2026-10-09, `M8-Fusion-API-terv.md`):
- **D1**: Python és parancssor. D-Bus később lesz, ha egy program igényli.
- **D2**: a root-kapu a `fusion-admin`.
- **D3**: belső API, de úgy van leírva, hogy később nyilvánossá tehető.

| Elérés | Hogyan |
| --- | --- |
| Python | `import fusion` — a rendszerképben mindenhol látszik (`/usr/lib/python3/dist-packages/fusion`) |
| Parancssor | `fusion <terület> <művelet> [--json]` — [cli.md](cli.md) |
| Root-műveletek | csak a `fusion-admin` kapun át (`sudo -n`), engedélyezett paraméterekkel |

## Leírások

- [cli.md](cli.md) — a `fusion` parancs, és minden `--json` kimenet kulcsai
- [leirok.md](leirok.md) — a `program.fusion` 1, a `*.fwr` recept (ugyanaz a séma) és a `*.role` szerepfájl 1;
  az elsőbbségi szabály
- [feladatok.md](feladatok.md) — a feladat-protokoll (hosszú műveletek: `LÉPÉS`, `PROGRESS`, kilépési kód)
- [python.md](python.md) — a `fusion` csomag moduljai

## Változatkezelés

- `fusion.API_VERSION` / `fusion api-version` → `1`.
- Bővítés (új kulcs, új parancs, új JSON-mező): a változat marad. Ezért a kliensek az ismeretlen mezőket hagyják figyelmen kívül.
- Meglévő kulcs vagy mező jelentésének változása, vagy törlése: új változat. Ilyenkor ezek a leírások is frissülnek.
- A leírókban az ismeretlen kulcs **figyelmeztetés**, nem hiba: egy újabb változat kulcsa lehet.
