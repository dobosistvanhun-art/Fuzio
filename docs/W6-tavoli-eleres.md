# W6 — Távoli elérés (0.0.78): Tailscale, SSH, képernyő

István kérése (2026-11-13): a Fúzió távolról, pl. a munkahelyi gépről is elérhető legyen — parancssor (pl. a
naptár deployja), fájlok és képernyő —, portnyitás nélkül. Döntés: **Tailscale** (külső szolgáltatás, de nem kell
portot nyitni; a saját WireGuard portnyitást kérne, a Cloudflare Tunnel saját domaint).

## Mi került be

| rész | hol |
| --- | --- |
| Tailscale (hivatalos statikus binárisok, SHA256-tal ellenőrizve) | `build/config/build.conf` (`TAILSCALE_*`), `build/steps/fetch.sh` (`fetch_tailscale`), `rootfs/customize.sh` → `/usr/bin/tailscale`, `/usr/sbin/tailscaled` |
| a tailscaled szolgáltatás (alapból ki) | `rootfs/overlay/usr/lib/systemd/system/tailscaled.service`; állapot: `/var/lib/tailscale` (DATA) |
| SSH-szerver (alapból ki) | `openssh-server` a `packages.list`-ben; `rootfs/overlay/etc/ssh/sshd_config.d/fusion.conf` |
| képernyő-megosztás (alapból ki) | `x11vnc`; `rootfs/overlay/usr/lib/systemd/user/fusion-vnc.service` (a felhasználó saját szolgáltatása) |
| ébren tartás | `rootfs/overlay/usr/lib/systemd/system/fusion-remote-awake.service` |
| rendszersegéd | `rootfs/overlay/usr/lib/fusion/bin/fusion-remote`; `fusion-admin remote …` (csak rendszergazdának) |
| felület | Beállítások → **Távoli elérés** (`desktop/settings/qml/RemotePage.qml`, `fusion_settings_parts/remote.py`) |

## Biztonság

- Semmi nem figyel a nyilvános internet felé, és **alapból minden ki van kapcsolva**.
- SSH: **csak kulccsal** (a `fusion` felhasználó gyári jelszava ismert — jelszóval ezért nem lehet belépni), root
  nem léphet be, csak rendszergazda (`sudo` csoport), és csak a Tailscale-hálózat (100.64.0.0/10,
  fd7a:115c:a1e0::/48) vagy maga a gép felől (`AllowUsers *@…`). A gépkulcsok az első bekapcsoláskor készülnek
  (`ssh-keygen -A`), nem a rendszerképben: minden telepítésnek saját kulcsa van.
- VNC: jelszóval (a VNC-protokoll csak az első 8 karaktert nézi), és csak a 100.x és a 127.0.0.1 címről
  (`x11vnc -allow`). A forgalmat a Tailscale (WireGuard) titkosítja.
- A Tailscale tűzfal-szabályokat nem állít (`--netfilter-mode=off`): a Fúzió nem útválasztó, csak a saját gépét
  osztja meg.
- A belépésre jogosító kulcsok a felhasználó saját `~/.ssh/authorized_keys` fájljában (0600, a mappa 0700); a
  FusionAI ezt a mappát továbbra sem olvassa.

## Használat (István)

1. **A Fúzión:** Beállítások → Távoli elérés → „Tailscale bekapcsolva” → a megjelenő címet megnyitni, bejelentkezni
   (pl. Google-fiókkal). Utána: „SSH-szerver bekapcsolva”, és ha kell, „Képernyő megosztása” jelszóval, „A gép ne
   aludjon el”.
2. **A munkahelyi gépen (Windows):** a Tailscale telepítése (tailscale.com/download), belépés **ugyanazzal a
   fiókkal**. PowerShell:
   ```powershell
   ssh-keygen -t ed25519
   Get-Content $env:USERPROFILE\.ssh\id_ed25519.pub
   ```
   A kiírt egyetlen sort (ssh-ed25519 … kezdetű) a Fúzión: Távoli elérés → Belépésre jogosító kulcsok →
   Hozzáadás.
3. **Belépés:** `ssh fusion@<a gép neve>` (a név a Távoli elérés oldalon, a „Belépés” sorban), utána pl.
   ```sh
   cd ~/Projektek/motoros-projekt && npm run deploy:staging
   fusion-dev rebuild
   ```
   Fájlok: WinSCP (SFTP; a kulcsot a WinSCP be tudja olvasni), VS Code „Remote - SSH”, vagy `scp`.
   Képernyő: VNC-néző (TigerVNC, RealVNC Viewer) → `<a gép neve>:5900`.
4. **Telefonról:** a Tailscale app ugyanazzal a fiókkal; SSH-hoz pl. Termius, VNC-hez RealVNC Viewer.

## Ellenőrzés

Felhőben, forrásból (2026-11-13):
- `fusion-settings --selftest` (offscreen): `QML ok`, `SLOTS ok`,
  `REMOTE ok parse,private,junk,mismatch,add,dup,mode,remove,vncshort,vnc` (a kulcs-ellenőrzés, a hozzáadás /
  törlés, a jogosultságok, a VNC-jelszó egy ideiglenes saját mappában);
- a Távoli elérés oldal képernyőképe kitalált állapottal (bekapcsolt Tailscale, két másik gép, egy kulcs);
- `sh -n` / `py_compile` a segédekre és a build-lépésekre.

**Nem próbált** (a felhőből a pkgs.tailscale.com nem érhető el, és nincs Fúzió-futtatókörnyezet):
- a `fetch_tailscale` (a `?mode=json` lista, a `.sha256`), a build és a rendszerkép;
- a QEMU-önteszt új sorai (`FUSION-REMOTE:` — SSH jelszóval elutasítva, kulccsal belép; a Tailscale és a VNC
  indul-e);
- a ZBookon: a Tailscale bejelentkezés, a munkahelyi gépről SSH / WinSCP / VNC, az ébren tartás.

A ZBookon a build után:
```sh
sudo /usr/lib/fusion/bin/fusion-selftest 2>&1 | grep FUSION-REMOTE   # ha a QEMU-önteszt nem futott
sudo -n /usr/lib/fusion/bin/fusion-admin remote status
```

## Visszavonás

A Beállításokban mindent ki lehet kapcsolni (a Tailscale-ből ki is lehet jelentkezni). A kódból: a
`packages.list` két sora, a `build.conf` Tailscale-blokkja és a `fetch_tailscale`, a `customize.sh` „távoli
elérés” része, az overlay öt új fájlja, a `fusion-admin remote` ága és a Beállítások `remote` része.
