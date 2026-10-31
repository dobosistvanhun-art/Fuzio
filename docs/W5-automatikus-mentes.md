# W5 — Automatikus heti mentés a Tárhelyre (0.0.70)

## Mit csinál
- A DATA (programok, beállítások, Wi-Fi, saját fájlok) hetente magától a **Tárhelyre** (az Adatlemezre) mentődik,
  ugyanabban a formában, mint a kézi mentés (`fusion-backup create`; visszaállítás a Fúzió Telepítőben).
- Be-/kikapcsolás: **Beállítások → Mentés → „Hetente automatikus mentés a Tárhelyre”**. Alapból ki van kapcsolva.
- A `fusion-backup-auto.timer` naponta egyszer (12:30 körül, ill. indítás után 20 perccel, ha kimaradt) indítja a
  `fusion-backup auto`-t. Az csak akkor ment, ha be van kapcsolva, a gép töltőn van (`ConditionACPower`), és a
  legutóbbi mentés a Tárhelyen 7 napnál régebbi. Mentés közben a gép nem alszik el és a fedél lecsukása sem altat
  (`systemd-inhibit`); alacsony prioritással fut (Nice 15, idle IO).
- A régi **automatikus** mentésekből a beállított számú marad (1–20, alapból 4); a kézi mentésekhez nem nyúl.
- A végén értesítés (siker vagy hiba).
- „Automatikus mentés most” gomb: azonnal ment (a 7 napot nem nézi), a régieket ugyanígy ritkítja.

## Fájlok
| Fájl | Szerep |
| --- | --- |
| `rootfs/overlay/usr/lib/fusion/bin/fusion-backup` | `auto [--most]`, `auto-get`, `auto-set on\|off [n]`; beállítás: `/data/system/backup-auto.json` |
| `rootfs/overlay/usr/lib/systemd/system/fusion-backup-auto.{service,timer}` | az ütemezés |
| `rootfs/overlay/usr/lib/fusion/bin/fusion-admin` | `backup auto-get \| auto-set on\|off [1-20] \| auto-now` |
| `rootfs/customize.sh` | `systemctl enable fusion-backup-auto.timer` |
| `desktop/settings/…backend.py`, `qml/BackupPage.qml` | a Beállítások szakasza |

## Ellenőrzés
| Mit | Hol | Eredmény |
| --- | --- | --- |
| auto-logika: kihagyás 7 napon belül, `--most`, ritkítás (keep=2), auto-get JSON, hiányzó Tárhely hibaüzenete | fejlesztőgép, tmpfs DATA + Tárhely | ok |
| `fusion-admin` szintaxis (`bash -n`) | fejlesztőgép | ok |
| Beállítások → Mentés felület (bekapcsolva / Tárhely nélkül) | fejlesztőgép, offscreen képernyőkép | ok |
| `fusion-settings --selftest` (QML) | fejlesztőgép | ok |
| timer a valódi rendszeren, értesítés, Tárhely-csatolás, altatás-tiltás | ZBook | **nincs ellenőrizve** |

ZBook-próba:
```sh
systemctl list-timers fusion-backup-auto.timer      # a következő futás ideje
sudo -n /usr/lib/fusion/bin/fusion-admin backup auto-get
journalctl -u fusion-backup-auto.service -n 50      # egy futás után
```

## Visszavonás
Kikapcsolás a Beállításokban (a timer fut, de nem ment). Teljesen: a 0.0.69-es rendszerre visszaállás (A/B), vagy a
fenti fájlok változásának visszavonása (`git revert <commit>`). A meglévő mentések megmaradnak.
