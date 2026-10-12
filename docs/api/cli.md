# A `fusion` parancs

```text
fusion <terület> <művelet> [--json]        fusion help
```

- Kilépési kód: 0 = rendben, 1 = hiba (érvénytelen leírónál is), 2 = hibás használat.
- `--json` esetén hiba: `{"error": "…"}`.
- A JSON mindig UTF-8. A kliens az ismeretlen mezőket hagyja figyelmen kívül: bővítéskor az API-változat nem változik.
- A régi parancsok (`fusion-programs`, `fusion-notify`, `fusion-run`, `fwr`) megmaradnak.
  A `fusion programs …` és a `fusion notify …` ugyanazt a kódot hívja.

## Parancsok és JSON-kimenet

| Parancs | JSON | Kulcsok |
| --- | --- | --- |
| `fusion api-version` | objektum | `api` (szám) |
| `fusion system` | objektum | `api`, `version`, `milestone`, `image`, `base`, `kernel`, `slot` (A/B), `bootDisk`, `bootState`, `display` (mint a `hardware`), `render` (`gpu` / `software`) |
| `fusion hardware` | objektum | `profile`, `profileName`, `status` (`ok`, `manual`, `warning`, `fallback`, `none`), `driverState`, `adapter`, `adapterId`, `adapterCount`, `message` |
| `fusion devices [list]` | lista | `role`, `name`, `present` (bool), `dev` (pl. `ttyUSB0`), `key` (rögzített azonosító), `com` (javasolt COM), `match`, `identify`, `programs` [{`id`, `name`, `com`}] |
| `fusion devices assign <szerep> <eszköz>` | objektum | `ok`, `message` |
| `fusion devices forget <szerep>` | objektum | `ok`, `message` |
| `fusion volumes` | lista | `kind` (`removable` / `data`), `name`, `path`, `device`, `fstype`, `size`, `free` (bájt), `readonly` |
| `fusion power` | objektum | `ac` (bool / null), `batteries` [{`name`, `percent`, `status`, `statusText`, `plugged`, `minutes`, `health`, `cycles`, `model`, `technology`}] — akkumulátor nélkül üres lista |
| `fusion trash` | objektum | `size` (bájt), `count`, `autoDays` (0 = ki), `autoChoices` |
| `fusion trash auto <0\|7\|30\|90>` | objektum | `ok`, `autoDays` |
| `fusion trash purge-old` / `empty` | objektum | `ok`, `removed` |
| `fusion cameras` | lista | `dev` (pl. `/dev/video0`), `name`, `bus` (`USB` / `virtuális` / `egyéb`), `usb` (vendor:product), `driver`, `index` |
| `fusion bluetooth` | objektum | `adapter` {`present`, `address`, `name`, `powered`, `discoverable`, `pairable`, `discovering`, `blocked`, `hardBlocked`, `service`}, `devices` [{`address`, `name`, `icon`, `kind`, `paired`, `trusted`, `connected`, `battery`}] |
| `fusion bluetooth on` / `off` / `scan [mp]` | objektum | `ok`, `message` (a `scan` után: `devices` is) |
| `fusion bluetooth pair` / `connect` / `disconnect` / `remove <cím>` | objektum | `ok`, `message` — a párosítás saját ügynökkel; a kért kódot szövegesen kiírja |
| `fusion printers` | lista | `name`, `info`, `model`, `uri`, `connection` (`USB` / `hálózat` / `PDF-fájl`), `state` (3 kész, 4 nyomtat, 5 leállítva), `stateText`, `reasons`, `reasonsText`, `accepting`, `default`, `shared` |
| `fusion printers discover` | lista | `uri`, `info`, `model`, `connection`, `driverless`, `added`, `class` |
| `fusion printers add <uri> [modell]` / `add-pdf` | objektum | `ok`, `message`, `name` — driverless (IPP Everywhere), vagy a modellhez illő meghajtó |
| `fusion printers remove` / `default` / `enable` / `test <név>` | objektum | `ok`, `message` (a `test`: `job` is) |
| `fusion printers jobs` / `cancel <feladat>` | lista / objektum | `id`, `printer`, `user`, `size`, `time` / `ok`, `message` |
| `fusion permissions [id]` | lista / objektum | `id`, `name`, `type`, `devices`, `ports` {COMn: szerep}, `folders` [{`path`, `letter`, `readonly`}], `net`, `sandbox`, `enforcement` (`flatpak` / `sandbox` / `win64` / `full`), `protection` (szöveg), `flatpak` (a csomag kért jogai) |
| `fusion programs list` | lista | `id`, `name`, `type`, `typeName`, `version`, `icon`, `exe`, `prefix`, `open`, `devices` {COMn: szerep}, `folders` {betű: mappa} … (= `fusion-programs list --json`) |
| `fusion programs info <id>` | objektum | mint a lista egy eleme |
| `fusion jobs [list]` | lista | `name`, `title`, `app`, `icon`, `running`, `rc` (null, ha még fut), `started`, `finished`, `recent`, `step` {`i`, `n`, `text`}, `progress`, `lines` |
| `fusion jobs show <név>` | objektum | mint a lista egy eleme, a napló utolsó 200 sorával |
| `fusion schema` | objektum | `version`, `program` {`fields`, `requiredByType`, `recipe`}, `role` {`fields`} |
| `fusion validate <fájl>…` | lista | `file`, `kind` (`program` / `recipe` / `role`), `ok`, `problems` [{`level` (`hiba` / `figyelmeztetés`), `key`, `message`}] |
| `fusion notify [-i ikon] [-u sürgősség] [-a program] [-t ms] <cím> [szöveg]` | — | kilépési kód |

## Példák

```bash
fusion system
fusion devices --json | python3 -c 'import json,sys; print([d["role"] for d in json.load(sys.stdin) if d["present"]])'
fusion validate /data/programs/*/program.fusion
fusion jobs show update
```
