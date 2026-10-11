# FusionOS 0.0.38 (j6) — a Programkezelő külön ablakban, a Lomtár automatikus ürítése

## Mi változott

| | |
| --- | --- |
| Programkezelő | **Saját ablakban** nyílik meg („Programkezelő” címmel, oldalsáv nélkül). Felül két fül: Programkezelő és Programbolt; jobbra egy Beállítások gomb. Így indul a Start menüből, a Fájlkezelő „Telepítés” parancsából és a Lézer állapotból is. A Beállítások oldalsávjában továbbra is elérhető. |
| Lomtár | **Automatikus ürítés**: a 30 napnál régebben lomtárba tett elemek végleg törlődnek, bejelentkezés után 1 perccel és 6 óránként. A csatlakoztatott pendrive-ok lomtára is ürül. |
| Beállítások → Rendszer | Új **LOMTÁR** rész: a tartalom (elemek, méret). Automatikus ürítés: Ki / 7 / 30 / 90 nap (alapértelmezés: 30). „Lomtár ürítése most” gomb, megerősítéssel. |
| Parancssor | `fusion trash` (`--json`), `fusion trash auto <0\|7\|30\|90>`, `fusion trash purge-old`, `fusion trash empty` |

## Ellenőrzés a ZBookon

1. **Start → Programkezelő**: külön ablakban nyílik, a Programbolt fül működik.
2. **Beállítások → Rendszer → LOMTÁR**: a lomtár tartalma látszik, és az ürítési idő átállítható.
