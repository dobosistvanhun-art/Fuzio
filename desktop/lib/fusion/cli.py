"""fusion — a Fusion API parancssora (M8b): egy belépési pont, minden lekérdezés `--json`-nal is

    fusion api-version                        az API változata (1)
    fusion system [--json]                    verzió, alap, slot, A/B-állapot, Hardware Layer, rajzolási mód
    fusion hardware [--json]                  a kijelzőprofil (Hardware Layer, csak olvas)
    fusion devices [list] [--json]            eszközszerepek: állapot, eszköz, rögzítés, ki használja (COM)
    fusion devices assign <szerep> <eszköz>   pl. assign laser ttyUSB0 (a fusion-admin kapun át)
    fusion devices forget <szerep>
    fusion volumes [--json]                   csatolt cserélhető kötetek (pendrive, SD) és a DATA
    fusion power [--json]                     akkumulátor (töltöttség, töltés / merülés, becsült idő, állapot)
    fusion trash [--json]                     Lomtár: méret, elemek, automatikus ürítés (napok)
    fusion trash auto <0|7|30|90>             automatikus ürítés beállítása (0 = ki)
    fusion trash purge-old | empty            ürítés a beállítás szerint / teljes ürítés
    fusion cameras [--json]                   kamerák (V4L2: beépített webkamera, USB-kamera)
    fusion bluetooth [--json]                 Bluetooth-adapter és eszközök
    fusion bluetooth on | off | scan [mp]     rádió be / ki, eszközök keresése
    fusion bluetooth pair | connect | disconnect | remove <cím>
    fusion printers [--json]                  papírnyomtatók (CUPS): állapot, alapértelmezett
    fusion printers discover [--json]         csatlakoztatott és hálózati nyomtatók keresése
    fusion printers add <uri> [modell] | add-pdf | remove | default | test | enable <név>
    fusion printers jobs [--json] | cancel <feladat>
    fusion users [--json]                     felhasználók (név, rendszergazda, automatikus belépés)
    fusion permissions [id] [--json]          a programok jogai: eszközök, mappák, hálózat, homokozó (M9)
    fusion programs …                         = fusion-programs … (list --json, info, install, run …)
    fusion notify [-i ikon] [-u sürgősség] [-a program] [-t ms] <cím> [szöveg]
    fusion jobs [list] [--json]               a hosszú műveletek állapota (feladat-protokoll)
    fusion jobs show <név> [--json]
    fusion schema [--json]                    a leírók sémái (program.fusion = *.fwr recept, *.role)
    fusion validate <fájl>… [--json]          leíró ellenőrzése a séma szerint (kilépési kód: 1, ha hibás)

Kilépési kód: 0 = rendben, 1 = hiba, 2 = hibás használat. `--json` esetén hiba: {"error": "…"}.
A JSON-kimenetek leírása: docs/api/cli.md.
"""
import json
import os
import shutil
import sys

from . import (API_VERSION, MEDIA, PREFIX, RUN, bluetooth, camera, devices, hardware, jobs, kv, notify, permissions,
               power, printers, programs, schema, trash, ui, users)


class UsageError(Exception):
    pass


def _out(data, as_json, text):
    if as_json:
        print(json.dumps(data, ensure_ascii=False, indent=1))
    else:
        print(text() if callable(text) else text)


def _read(path, default=""):
    try:
        with open(path, encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        return default


def system_info():
    rel = kv.read(os.path.join(PREFIX, "fusion-release"), shell=True)
    bs = _read(os.path.join(RUN, "boot-state"))
    return {"api": API_VERSION, "version": rel.get("FUSION_VERSION", ""), "milestone": rel.get("FUSION_MILESTONE", ""),
            "image": rel.get("FUSION_IMAGE_ID", ""), "base": rel.get("FUSION_BASE", "Ubuntu 24.04 LTS (noble)"),
            "kernel": os.uname().release, "slot": _read(os.path.join(RUN, "slot")),
            "bootDisk": _read(os.path.join(RUN, "boot-disk")), "bootState": bs.splitlines()[0] if bs else "",
            "display": {k: v for k, v in hardware.display().items() if k != "raw"}, "render": ui.render_mode()}


def volumes():
    """csatolt cserélhető kötetek (a fusion-admin a MEDIA alá csatol) és a DATA"""
    out = []
    try:
        with open("/proc/self/mounts", encoding="utf-8") as f:
            mounts = [l.split() for l in f]
    except OSError:
        mounts = []
    dec = lambda s: s.encode().decode("unicode_escape").encode("latin-1").decode("utf-8", "replace")  # noqa: E731
    for m in mounts:
        if len(m) < 3:
            continue
        mp = dec(m[1])
        kind = "data" if mp == "/data" else "removable" if mp.startswith(MEDIA + "/") else None
        if not kind:
            continue
        try:
            st = os.statvfs(mp)
            size, free = st.f_blocks * st.f_frsize, st.f_bavail * st.f_frsize
        except OSError:
            size = free = 0
        out.append({"kind": kind, "name": os.path.basename(mp) if kind == "removable" else "DATA", "path": mp,
                    "device": m[0], "fstype": m[2], "size": size, "free": free,
                    "readonly": "ro" in m[3].split(",") if len(m) > 3 else False})
    return out


def _result(ok, msg, as_json, extra=None):
    d = {"ok": bool(ok), "message": msg or ""}
    d.update(extra or {})
    _out(d, as_json, msg or ("rendben" if ok else "nem sikerült"))
    return 0 if ok else 1


def _bluetooth(rest, as_json):
    sub = rest[0] if rest else "list"
    if sub == "list" and len(rest) <= 1:
        a = bluetooth.adapter()
        ds = bluetooth.devices() if a["present"] else []
        _out({"adapter": a, "devices": ds}, as_json, lambda: "\n".join(
            [bluetooth.summary()] + [f"  {d['address']}  {d['name']} ({d['kind']})"
                                     + (" — párosítva" if d["paired"] else "") + (", csatlakozva" if d["connected"] else "")
                                     + (f", akku {d['battery']}%" if d["battery"] is not None else "") for d in ds]))
        return 0
    if sub in ("on", "off") and len(rest) == 1:
        return _result(*bluetooth.power(sub == "on"), as_json)
    if sub == "scan" and len(rest) <= 2:
        ok, msg = bluetooth.scan(int(rest[1]) if len(rest) == 2 and rest[1].isdigit() else 10)
        return _result(ok, msg, as_json, {"devices": bluetooth.devices()})
    if sub in ("pair", "connect", "disconnect", "remove", "trust") and len(rest) == 2:
        fn = getattr(bluetooth, sub)
        try:
            if sub == "pair":
                ok, msg = fn(rest[1], event=None if as_json else
                             lambda kind, code: print(f"kód: {code}" + (" — gépelje be az eszközön, majd Enter"
                                                                         if kind == "passkey" else "")))
            else:
                ok, msg = fn(rest[1])
        except ValueError as e:
            raise UsageError(str(e))
        return _result(ok, msg, as_json)
    raise UsageError("fusion bluetooth [on | off | scan [mp] | pair | connect | disconnect | remove <cím>]")


def _printers(rest, as_json):
    sub = rest[0] if rest else "list"
    if sub == "list" and len(rest) <= 1:
        ps = printers.printers()
        _out(ps, as_json, lambda: "\n".join(
            f"{'*' if p['default'] else ' '} {p['name']:<24} {p['stateText']:<10} {p['connection']:<8} {p['info']}"
            + (f" [{', '.join(p['reasons'])}]" if p["reasons"] else "") for p in ps) or "nincs felvett nyomtató")
        return 0
    if sub == "discover":
        ds = printers.discover()
        _out(ds, as_json, lambda: "\n".join(
            f"{d['connection']:<8} {d['info']}{' (felvéve)' if d['added'] else ''}\n         {d['uri']}" for d in ds)
            or "nem található nyomtató")
        return 0
    if sub == "add" and len(rest) in (2, 3):
        ok, msg, name = printers.add(rest[1], rest[2] if len(rest) == 3 else "")
        return _result(ok, msg or (f"felvéve: {name}" if ok else ""), as_json, {"name": name})
    if sub == "add-pdf" and len(rest) == 1:
        ok, msg, name = printers.add_pdf()
        return _result(ok, msg or (f"felvéve: {name}" if ok else ""), as_json, {"name": name})
    if sub in ("remove", "default", "enable") and len(rest) == 2:
        fn = {"remove": printers.remove, "default": printers.set_default, "enable": printers.enable}[sub]
        return _result(*fn(rest[1]), as_json)
    if sub == "test" and len(rest) == 2:
        ok, msg, job = printers.test_page(rest[1])
        return _result(ok, msg or (f"elküldve: {job}" if ok else ""), as_json, {"job": job})
    if sub == "jobs" and len(rest) == 1:
        js = printers.jobs()
        _out(js, as_json, lambda: "\n".join(f"{j['id']:<20} {j['user']:<10} {j['size']:>9} B  {j['time']}" for j in js)
             or "nincs várakozó feladat")
        return 0
    if sub == "cancel" and len(rest) == 2:
        return _result(*printers.cancel(rest[1]), as_json)
    raise UsageError("fusion printers [discover | add <uri> [modell] | add-pdf | remove | default | test | enable <név>"
                     " | jobs | cancel <feladat>]")


def _gb(n):
    return f"{n / 1e9:.1f} GB"


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    as_json = "--json" in argv
    args = [a for a in argv if a != "--json"]
    cmd = args[0] if args else "help"
    rest = args[1:]
    try:
        if cmd in ("help", "-h", "--help"):
            print(__doc__.strip())
            return 0
        if cmd == "api-version":
            _out({"api": API_VERSION}, as_json, str(API_VERSION))
            return 0
        if cmd == "system":
            s = system_info()
            _out(s, as_json, lambda: "\n".join([
                f"FusionOS {s['version']} ({s['milestone']}), alap: {s['base']}, kernel: {s['kernel']}",
                f"slot: {s['slot'] or '?'}, indulás: {s['bootState'] or '?'}",
                f"kijelző: {s['display']['profile'] or '?'} ({s['display']['status'] or '?'}), felület: {s['render'] or '?'}",
                f"Fusion API: {s['api']}"]))
            return 0
        if cmd == "hardware":
            d = {k: v for k, v in hardware.display().items() if k != "raw"}
            _out(d, as_json, lambda: hardware.summary())
            return 0
        if cmd == "devices":
            sub = rest[0] if rest else "list"
            if sub == "list":
                r = devices.roles()
                _out(r, as_json, lambda: "\n".join(
                    f"{d['name']:<24} [{d['role']}] " + (f"csatlakoztatva ({d['dev']})" if d["present"] else "nincs csatlakoztatva")
                    + ("".join(f", {p['name']} → {p['com']}" for p in d["programs"])) for d in r) or "nincs szerep")
                return 0
            if sub in ("assign", "forget"):
                if (sub == "assign" and len(rest) != 3) or (sub == "forget" and len(rest) != 2):
                    raise UsageError("használat: fusion devices assign <szerep> <eszköz> | forget <szerep>")
                rc, msg = devices.assign(rest[1], rest[2]) if sub == "assign" else devices.forget(rest[1])
                _out({"ok": rc == 0, "message": msg}, as_json, msg)
                return 0 if rc == 0 else 1
            raise UsageError("fusion devices [list | assign | forget]")
        if cmd == "volumes":
            v = volumes()
            _out(v, as_json, lambda: "\n".join(
                f"{x['name']:<20} {x['path']:<32} {x['fstype']:<6} szabad: {_gb(x['free'])} / {_gb(x['size'])}" for x in v)
                or "nincs csatolt kötet")
            return 0
        if cmd == "power":
            b = power.batteries()
            _out({"ac": power.ac_online(), "batteries": b}, as_json, lambda: power.summary() or "nincs akkumulátor")
            return 0
        if cmd == "trash":
            sub = rest[0] if rest else "state"
            if sub == "state":
                t = trash.state()
                _out(t, as_json, lambda: f"Lomtár: {t['count']} elem, {t['size'] / 1e6:.1f} MB; automatikus ürítés: "
                     + (f"{t['autoDays']} napnál régebbi elemek" if t["autoDays"] else "ki"))
                return 0
            if sub == "auto" and len(rest) == 2 and rest[1].isdigit():
                trash.set_auto_days(int(rest[1]))
                _out({"ok": True, "autoDays": int(rest[1])}, as_json, "rendben")
                return 0
            if sub in ("purge-old", "empty") and len(rest) == 1:
                n = trash.auto_purge() if sub == "purge-old" else trash.empty()
                _out({"ok": True, "removed": n}, as_json, f"törölve: {n} elem")
                return 0
            raise UsageError("fusion trash [auto <0|7|30|90> | purge-old | empty]")
        if cmd == "cameras":
            c = camera.cameras()
            _out(c, as_json, lambda: "\n".join(f"{x['dev']:<12} {x['name']} [{x['bus']}{' ' + x['usb'] if x['usb'] else ''}]"
                                               for x in c) or "nincs kamera")
            return 0
        if cmd == "bluetooth":
            return _bluetooth(rest, as_json)
        if cmd == "users" and not rest:
            st = users.state()
            if st.get("error"):
                raise ValueError(st["error"])
            _out(st, as_json, lambda: "\n".join(
                f"{u['name']:<16} {'rendszergazda' if u['admin'] else 'felhasználó':<14}"
                f"{'automatikus belépés  ' if u['autologin'] else ''}{u['fullname']}" for u in st["users"]))
            return 0
        if cmd == "permissions":
            if len(rest) > 1:
                raise UsageError("fusion permissions [id]")
            ids = rest or [p["id"] for p in programs.list_programs()]
            res = [x for x in (permissions.summary(i, with_flatpak=True) for i in ids) if x]
            if rest and not res:
                raise ValueError(f"nincs ilyen program: {rest[0]}")

            def txt(p):
                fl = ", ".join((f["letter"] + ": " if f["letter"] else "") + f["path"] + (" (csak olvas)" if f["readonly"] else "")
                               for f in p["folders"]) or "—"
                lines = [f"{p['name']} [{p['id']}, {p['type']}]", f"  védelem:  {p['protection']}",
                         f"  eszközök: " + (", ".join(f"{c} → {r}" for c, r in sorted(p['ports'].items())) or "—"),
                         f"  mappák:   {fl}", f"  hálózat:  {'igen' if p['net'] else 'nem'}"]
                if p.get("flatpak"):
                    lines.append("  Flatpak:  " + "; ".join(f"{k}={','.join(v)}" for k, v in sorted(p["flatpak"].items())))
                return "\n".join(lines)
            _out(res if not rest else res[0], as_json, lambda: "\n".join(txt(p) for p in res) or "nincs telepített program")
            return 0
        if cmd == "printers":
            return _printers(rest, as_json)
        if cmd == "programs":
            exe = shutil.which("fusion-programs") or os.path.join(PREFIX, "programs", "fusion-programs")
            os.execv(sys.executable, [sys.executable, exe] + rest + (["--json"] if as_json else []))
        if cmd == "notify":
            return notify.main(rest)
        if cmd == "jobs":
            sub = rest[0] if rest else "list"
            if sub == "list":
                js = jobs.list_jobs()
                _out(js, as_json, lambda: "\n".join(
                    f"{j['name']:<10} {'fut' if j['running'] else 'kész' if j['rc'] == 0 else 'sikertelen' if j['rc'] is not None else '?':<11}"
                    f" {j['title']}" + (f" — {j['step'].get('i')}/{j['step'].get('n')}: {j['step'].get('text')}" if j['step'] else "")
                    for j in js) or "nincs feladat")
                return 0
            if sub == "show" and len(rest) == 2:
                j = jobs.state(rest[1], lines=200)
                _out(j, as_json, lambda: "\n".join([f"{j['title']} — " + ("fut" if j["running"] else f"RC={j['rc']}")]
                                                   + j["lines"]))
                return 0
            raise UsageError("fusion jobs [list | show <név>]")
        if cmd == "schema":
            d = schema.describe()
            _out(d, as_json, lambda: "\n".join(
                [f"Fusion-leírók, {d['version']}. változat", "", "program.fusion (= *.fwr recept):"]
                + [f"  {k:<14} {'*' if f['required'] else ' '} {f['desc']}" + (f" [{', '.join(f['types'])}]" if f["types"] else "")
                   for k, f in d["program"]["fields"].items()]
                + ["", "*.role (eszközszerep):"]
                + [f"  {k:<14} {'*' if f['required'] else ' '} {f['desc']}" for k, f in d["role"]["fields"].items()]
                + ["", "* = kötelező"]))
            return 0
        if cmd == "validate":
            if not rest:
                raise UsageError("használat: fusion validate <fájl>…")
            res = []
            for f in rest:
                probs = schema.validate_file(f)
                res.append({"file": f, "kind": schema.kind_of(f), "ok": not any(p[0] == "hiba" for p in probs),
                            "problems": [{"level": p[0], "key": p[1], "message": p[2]} for p in probs]})
            _out(res, as_json, lambda: "\n".join(
                f"{r['file']}: {'rendben' if r['ok'] else 'HIBÁS'}" + "".join(
                    f"\n  {p['level']}: {p['key'] or '-'}: {p['message']}" for p in r["problems"]) for r in res))
            return 0 if all(r["ok"] for r in res) else 1
        raise UsageError(f"ismeretlen parancs: {cmd} (fusion help)")
    except UsageError as e:
        if as_json:
            print(json.dumps({"error": str(e)}, ensure_ascii=False))
        else:
            print(f"fusion: {e}", file=sys.stderr)
        return 2
    except (OSError, ValueError, RuntimeError) as e:
        if as_json:
            print(json.dumps({"error": str(e)}, ensure_ascii=False))
        else:
            print(f"fusion: {e}", file=sys.stderr)
        return 1
