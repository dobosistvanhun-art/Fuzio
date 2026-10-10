# FusionOS 0.0.31 (j2) — a mérési bejegyzések a gép UEFI-menüjében (F9) + asztali Programok javítás

## Mi volt a hiba (0.0.30)

- A 0.0.30 új mérési bejegyzései (Intel, Nouveau, szoftveres felület) nem jelentek meg: a frissítést mindig a
  **futó** (régi, 0.0.29-es) rendszer frissítője írja fel, és az még nem ismerte a bejegyzések pótlását.
  A QEMU-teszt ezt nem fogta meg, mert ott a frissítő is az új volt.
- Asztal → Programok, „Összes”: sok programnál a kártya alját a tálca takarta (a magasság egy rögzített becslés volt).

## Mi változott

| | |
| --- | --- |
| Boot-bejegyzések | A lista egy helyen van: `/usr/lib/fusion/boot/measure-entries` (a rendszerképben). Minden normál indításkor a `fusion-boot-check` **pótolja** a lemezen hiányzó bejegyzéseket — így a frissítés után az új rendszer maga veszi fel őket, bármelyik régi frissítő írta fel. |
| UEFI-bejegyzések (F9) | A mérési bejegyzések a gép **UEFI-listájába** is bekerülnek: „Fusion meres - Intel grafika”, „Fusion meres - Nouveau”, „Fusion meres - szoftveres felulet” (ékezet nélkül — a firmware-menü nem mindig tud ékezetet). Ezek a systemd-boot nélkül, közvetlenül a véglegesített rendszert indítják a kiegészített parancssorral. A boot-sorrend eleje (a Mint) **nem változik**, az új bejegyzések a sor végére kerülnek; csak akkor ír a UEFI-be, ha valami változott (pl. frissítés után az új rendszerre állítja őket). Pendrive-ról futva nem ír. |
| Állapot | Beállítások → Rendszerfrissítés / Hibajelentés: a boot menü további bejegyzései és a UEFI-bejegyzések listája. |
| Asztal → Programok | A kártya magassága a tényleges helyéből számolódik: a tálca felett ér véget, a többi görgethető. |

## Frissítés

Minten (~/Fusion), a szokásos módon (`fusionos-j2.tar.gz`, `build/fusion-build all`), majd a `.fupd` →
Beállítások → Rendszerfrissítés → Telepítés → Újraindítás most.
Az első normál indítás után (a véglegesítéskor) a bejegyzések felkerülnek — egy újraindítás után az F9-menüben látszanak.

## Mérések

Bekapcsolás → **F9** → a „Fusion meres - …” bejegyzések egyike. (A systemd-boot menüjében is ott vannak: „FusionOS — mérés: …”.)

1. **Fusion meres - szoftveres felulet** — a BIOS-hoz nem kell nyúlni. Feladatkezelő: a fusion_shell memóriája (PSS);
   a Start menü, az ablakok, az asztal gördülékeny-e.
2. **Fusion meres - Nouveau** — BIOS marad (Hybrid Graphics = Disable). Desktop indul-e, LightBurn 2.1 vászon, Firefox-videó.
3. **Fusion meres - Intel grafika** — előtte BIOS (bekapcsoláskor F10) → Advanced → Hybrid Graphics = **Enable**;
   a mérés után vissza **Disable**-re.

Minden mérés után: Beállítások → Hibajelentés (a profil, a memória és a naplók egyben).
