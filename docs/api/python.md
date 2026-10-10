# A `fusion` Python-csomag

| Modul | Mit ad |
| --- | --- |
| `fusion` | `API_VERSION`, útvonalak: `PREFIX`, `RUN`, `ADMIN`, `MEDIA` (`/run/media/fusion`), `CONFIG`; `add_paths()` |
| `fusion.kv` | `parse(szöveg, shell=False)`, `read(út)`, `write(út, adatok, header, order)` — atomikus |
| `fusion.schema` | `validate_program()`, `validate_role()`, `validate_file()`, `apply_recipe()`, `describe()` — [leirok.md](leirok.md) |
| `fusion.hardware` | `display()` (profil, állapot, driver, adapterek), `summary()` — csak olvas |
| `fusion.devices` | `roles()`, `present()`, `com_usage()`, `assign(szerep, eszköz)`, `forget(szerep)` (a `fusion-admin` kapun át) |
| `fusion.programs` | `list_programs()`, `info(id)`, `run(id, fájlok)`, `opener(fájl)`, `users_of(szerep)` — a Programkezelő felülete |
| `fusion.power` | `batteries()` (töltöttség, töltés / merülés, becsült idő, állapot a gyárihoz képest, ciklusok), `ac_online()`, `summary()` |
| `fusion.jobs` | `start()`, `state()`, `list_jobs()`, `parse_line()` — [feladatok.md](feladatok.md) |
| `fusion.notify` | `send(cím, szöveg, ikon, program, sürgősség, ms)` — `org.freedesktop.Notifications` |
| `fusion.ui` | `render_mode()`, `render_forced()`, `RENDER_FILE` — a felület rajzolása (Qt nélkül) |
| `fusion.x11` | `X11` — ablakok (EWMH); a Shell és a Feladatkezelő közös alapja |
| `fusion.permissions` | `check(program, képesség)` — a jogosultság-ellenőrzés helye (most mindent engedélyez) |
| `fusion.cli` | a `fusion` parancs — [cli.md](cli.md) |

Egy hely, egy igazság:
- a COM-hozzárendelést a program leírója tartalmazza; a szerepfájl `windows.com` kulcsa csak javaslat;
- a kijelzőprofilt a `fusion-hwprobe` választja, az API csak olvassa;
- a rajzolási mód a `fusion.ui`-ban van.
