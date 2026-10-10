# Feladat-protokoll — hosszú műveletek

Programtelepítés, rendszerfrissítés, DATA mentése, telepítő pendrive, hibajelentés: külön folyamatban futnak, így az
ablak bezárása nem szakítja meg őket. Az állapotuk fájlban van, ezért egy újranyitott ablak, a Shell vagy egy szkript is látja.

## A parancs kimenete (soronként)

```text
LÉPÉS <i>/<n>: <szöveg>     a felület lépésszövege (pl. LÉPÉS 4/6: Rendszerkép írása)
PROGRESS <0–100>            haladás százalékban
<bármi más sor>             napló
kilépési kód 0 = kész, ≠0 = sikertelen; ilyenkor az utolsó naplósor az ok
```

## Állapot

| Fájl | Tartalom |
| --- | --- |
| `<JOBS_DIR>/<név>.json` | `name`, `title`, `app`, `icon`, `cmd`, `pid`, `started`, `finished`, `rc`, `step` {`i`, `n`, `text`}, `progress` |
| `<JOBS_DIR>/<név>.log` | a teljes napló; az utolsó sora `RC=<kód>` |

`JOBS_DIR`: felhasználóként `$XDG_RUNTIME_DIR/fusion/jobs`, rootként `/run/fusion/jobs` (vagy `FUSION_JOBS_DIR`).
A `/run` memóriában van, ezért egy korábbi indítás feladata nem látszik „frissnek”.

A mai feladatnevek: `programs` (telepítés, eltávolítás, frissítés), `update` (rendszerfrissítés), `backup` (mentés),
`media` (telepítő pendrive), `report` (hibajelentés). Egy névből egyszerre egy futhat.

A feladat végén értesítés megy (`fusion.notify`):
- „<cím>: kész” — a naplóból az `okpat` mintájú utolsó sor;
- „<cím>: sikertelen” — az utolsó naplósor.

## Használat

```python
from fusion import jobs
err, proc = jobs.start("backup", "DATA mentése", ["sudo", "-n", ADMIN, "backup", "create", mp],
                       app="Mentés", icon="archive-in", okpat="^kész")
jobs.state("backup")   # {"running", "rc", "title", "recent", "step", "progress", "lines", …}
```

```bash
fusion jobs --json
fusion jobs show backup
```
