# FusionOS 0.0.34 (m8a) — Fusion API, 1. lépés: rendrakás

Terv és döntések: `claude/M8-Fusion-API-terv.md` (D1: most Python + parancssor, D-Bus később; D2: a `fusion-admin`
marad a root-kapu; D3: belső API; D4: M8a → M8b → (M8c) → M8d — István, 2026-10-09).

A felhasználó számára **nincs látható változás** (egy kivétel: a Beállítások → Eszközök most azt is mutatja, melyik
Windows-program melyik COM-porton éri el a szerepet, pl. „LightBurn → COM3”).

## Mi került egy helyre

| | Előtte | Most |
| --- | --- | --- |
| Fusion API csomag | — | `fusion` Python-csomag (`/usr/lib/fusion/desktop/lib/fusion`, minden Python-program látja: `import fusion`), `fusion.API_VERSION = 1` |
| kulcs = érték fájlok | 4 külön olvasó | `fusion.kv` (program.fusion, *.fwr, *.role, display.env — shell-idézéssel is) |
| Hardware Layer állapota | 3 féle olvasás (az egyik az idézőjeleket is benne hagyta) | `fusion.hardware.display()` / `summary()` — Hibajelentés, Telepítő |
| Eszközszerepek | a Shell beégetett „laser/printer” listája, a Beállítások saját olvasója | `fusion.devices` — minden `.role` szerep (új szerep kódváltozás nélkül megjelenik), rögzítés/elfelejtés a `fusion-admin`-on át |
| COM-port | a szerepfájl `windows.com` és a program leírója eltérhetett | a program leírója (`port.COMn`) a tényleges; a szerepfájl csak javaslat — leírva, a felület is így mutatja |
| Értesítés | 2 küldő (csak az egyik tudott sürgősséget) | `fusion.notify` — a `fusion-notify` parancs és a Fusion-programok is ezt használják |
| Ablakok (X11) | 2 külön réteg (Shell, Feladatkezelő) | `fusion.x11` közös alap; a Feladatkezelő erre épül (ping, bezárás) |
| Modulok helye | környezeti változók + tartalék útvonalak | `fusion.PROGRAMS_LIB`, `fusion.add_paths()` |
| Jogosultság | — | `fusion.permissions.check()` — a helye kijelölve (most mindent engedélyez) |
| Tesztek | — | `tests/fusion-api-test.py` (16 eset) + `tests/hwprobe-test.sh` a build `test` lépésének elején; QEMU: `FUSION-API` sorok (felhasználóként és rootként) |

## Ellenőrzés a ZBookon

Szokásos frissítés (`fusionos-m8a.tar.gz`, `build/fusion-build all`, `.fupd`). Utána minden úgy működjön, mint eddig:
Start menü, értesítések (pl. a lézer be-/kihúzásakor), Feladatkezelő, Beállítások → Eszközök (új: „Windows-programok:
LightBurn → COM3”), Hibajelentés (a kijelzőprofil idézőjelek nélkül), LightBurn a lézerrel.
