# FusionOS 0.0.33 (j4) — megbízhatóbb pendrive-írás, tisztább naplók

A 0.0.32 a ZBookon (2026-10-09): a telepítő pendrive írása közben a pendrive leesett az USB-ről („device offline
error, dev sdc”), a felület „LÉPÉS 4/6”-on maradt, és közben a Rendszerfrissítés oldal 20 mp után hibát adott.

| | |
| --- | --- |
| Rendszerkép-írás (telepítő pendrive, frissítés, telepítés) | 32 MiB-onként a lemezre kerül (eddig: az egész a gyorsítótárba, majd egyben). A haladás így valós, a gép többi része nem vár egy lassú pendrive-ra, és ha a lemez eltűnik vagy írási hibát ad, a művelet azonnal leáll érthető hibaüzenettel („a lemez nem válaszol: kihúzták, kilazult, vagy meghibásodott — másik USB-port vagy pendrive”). |
| Rendszerfrissítés oldal | az állapotlekérdezés csak a rendszerlemez EFI-partícióját üríti (eddig a teljes `sync` a pendrive-írást is kivárta → 20 mp-es hiba). |
| Hibajelentés | a lemezfoglaltság (`df`) a Google Drive-csatolás nélkül — az néha megakasztotta („df: TimeoutExpired”). |
| Fusion Shell | leállításkor (pl. a rajzolási mód váltása után) nincs több „Cannot read property … of null” sor a naplóban. |

## Frissítés

Minten (~/Fusion): `fusionos-j4.tar.gz` kibontása, `build/fusion-build all`, a `.fupd` → Beállítások → Rendszerfrissítés.

## Kipróbálás

- Telepítő pendrive készítése (lehetőleg másik USB-portban, vagy egy másik pendrive-val) — a haladásjelző most egyenletesen
  megy, közben a Rendszerfrissítés oldal frissíthető.
- Ha a pendrive mégis kiesik: a művelet „SIKERTELEN”-nel és az okkal áll le (nem marad 4/6-on).
