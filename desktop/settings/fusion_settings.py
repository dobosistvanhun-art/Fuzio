#!/usr/bin/python3
"""FusionOS — Beállítások (fusion-settings)

    fusion-settings [oldal] [paraméter]
        oldal: wifi | bluetooth | display | devices | printers | printer | drive | sound | programs | store | desktop | users | system
        store search:<szó>: a Programbolt ezzel a kereséssel nyílik
        programs <fájl>: a Programkezelő ezzel a telepítővel / programfájllal nyílik
    fusion-settings --selftest      az oldalak adatainak lekérdezése felület nélkül (FUSION-SETTINGS sorok)

Egy példányban fut: ha már nyitva van, az új hívás csak oldalt vált és előre hozza.
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), "lib"))

import fusion_ui as ui  # noqa: E402

HERE = os.path.dirname(os.path.realpath(__file__))
PAGES = ["wifi", "bluetooth", "display", "devices", "printers", "printer", "drive", "sound", "programs", "store", "desktop", "users", "update", "backup", "report", "system"]


def selftest():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    import fusion_settings_backend as sb
    import fusion_net
    import fusion_apps
    st = fusion_net.state()
    nets = fusion_net.networks(st)
    print(f"FUSION-SETTINGS: WIFI ok={st.get('ok')} device={st.get('device') or '-'} state={st.get('state')} ssid={st.get('ssid') or '-'} "
          f"networks={','.join(n['name'] + ('*' if n['connected'] else '') for n in nets) or '-'} "
          f"known={','.join(k['name'] for k in st.get('known', [])) or '-'}", flush=True)
    outs, ok = sb.displays()
    print(f"FUSION-SETTINGS: DISPLAY ok={ok} " + " ".join(f"{o['name']}={o['current'] or '?'}({len(o['modes'])} mód)" for o in outs), flush=True)
    d = sb.devices()
    print("FUSION-SETTINGS: DEVICES " + " ".join(f"{r['role']}={'on:' + r['dev'] if r['present'] else 'off'}" for r in d["roles"])
          + f" serial={len(d['serial'])} usb={len(d['usb'])}", flush=True)
    p = sb.printer()
    print(f"FUSION-SETTINGS: PRINTER " + " ".join(f"{k}={v}" for k, v in p["services"].items())
          + f" klipper={p['klipper']['state'] or '-'} serial={p['serial'] or '-'}", flush=True)
    apps = fusion_apps.program_apps()
    print("FUSION-SETTINGS: PROGRAMS " + (" ".join(f"{a['pid']}={'telepítve' if a['installed'] else 'nincs'}" for a in apps) or "-")
          + f" installers={len(sb.installers())}", flush=True)
    import fusion_sound
    snd = fusion_sound.state()
    print(f"FUSION-SETTINGS: SOUND ok={snd['ok']} server={(snd.get('server') or '-').replace(' ', '_')} sinks={len(snd['sinks'])} "
          f"sources={len(snd['sources'])} default={snd['sink'] or '-'} volume={snd['volume']}", flush=True)
    import fusion_store
    t = fusion_store._text("<p>Első <b>bekezdés</b>.</p><ul><li>egy</li><li>kettő</li></ul>")
    want = "Első bekezdés.\n\n  • egy\n  • kettő"
    print(f"FUSION-SETTINGS: STORE categories={len(fusion_store.CATEGORIES)} text={'ok' if t == want else repr(t)}", flush=True)
    s = sb.system()
    print(f"FUSION-SETTINGS: SYSTEM version={s['version']} slot={s['slot']} bootdisk={s['bootdisk']} mem={s['memUsed']}/{s['memTotal']} "
          f"disks={','.join(x['name'] + ':' + str(x['pct']) + '%' for x in s['disks'])}", flush=True)
    u = sb.update_state()
    print(f"FUSION-SETTINGS: UPDATE version={u['version']} slot={u['slot']} entries="
          + (",".join(f"{e['slot']}:{e['state']}{'*' if e['running'] else ''}" for e in u["entries"]) or "-")
          + f" files={len(u['files'])} error={u['error'] or '-'}", flush=True)
    b = sb.backup_state()
    print(f"FUSION-SETTINGS: BACKUP error={b['error'] or '-'} data={b.get('dataUsedText', '-')} targets={len(b.get('targets', []))} backups={len(b.get('backups', []))}", flush=True)
    r = sb.report_files()
    print(f"FUSION-SETTINGS: REPORT dir={sb.report_dir()} files={len(r)}", flush=True)
    # 0.0.40: Bluetooth, nyomtatók (CUPS), kamera — a Fusion API-n át
    from fusion import bluetooth as fbt, camera as fcam, printers as fprn
    a = fbt.adapter()
    print(f"FUSION-SETTINGS: BLUETOOTH present={a['present']} powered={a.get('powered')} service={a['service']} "
          f"blocked={a['blocked']}", flush=True)
    print(f"FUSION-SETTINGS: PRINTERS service={fprn.service()} printers={len(fprn.printers())} cameras={len(fcam.cameras())}",
          flush=True)
    # az oldalak felülete: minden oldal QML-je betölthető (a háttérrel, ablak nélkül)
    from PyQt6.QtCore import QUrl
    from PyQt6.QtQml import QQmlComponent
    app, engine = ui.create_app("fusion-settings-selftest", "Beállítások", "settings")
    be = sb.Settings()
    engine.rootContext().setContextProperty("settings", be)
    engine.rootContext().setContextProperty("appMode", "")
    bad = []
    for page in sorted(f for f in os.listdir(os.path.join(HERE, "qml")) if f.endswith("Page.qml") and f != "SettingsPage.qml"):
        c = QQmlComponent(engine, QUrl.fromLocalFile(os.path.join(HERE, "qml", page)))
        if c.status() != QQmlComponent.Status.Ready:
            bad.append(page + ": " + "; ".join(e.toString() for e in c.errors())[:300])
    print("FUSION-SETTINGS: QML " + ("ok" if not bad else "HIBA " + " | ".join(bad)), flush=True)
    all_apps = fusion_apps.load()
    print("FUSION-SETTINGS: APPS " + ",".join(a["id"] for a in all_apps if not a["search_only"]), flush=True)
    return 0


def main():
    args = sys.argv[1:]
    if args[:1] == ["--selftest"]:
        return selftest()
    # a Programkezelő külön ablakban: fusion-settings --app programs [programs|store] [paraméter]
    app_mode = ""
    if args[:2] == ["--app", "programs"]:
        app_mode, args = "programs", args[2:]
    elif args[:1] in (["programs"], ["store"]):          # a Programkezelő / Programbolt mindig a saját ablakában
        app_mode = "programs"
    page = args[0] if args and args[0] in PAGES else ("programs" if app_mode else "wifi")
    param = args[1] if len(args) > 1 else ""

    from PyQt6.QtNetwork import QLocalServer, QLocalSocket
    name = f"fusion-{app_mode or 'settings'}-{os.getuid()}"
    # már fut? → oldalváltás kérése, és kilépés
    sock = QLocalSocket()
    sock.connectToServer(name)
    if sock.waitForConnected(300):
        sock.write(json.dumps({"page": page, "param": param}).encode() + b"\n")
        sock.waitForBytesWritten(500)
        sock.disconnectFromServer()
        return 0

    app, engine = (ui.create_app("fusion-programkezelo", "Programkezelő", "package") if app_mode
                   else ui.create_app("fusion-settings", "Beállítások", "settings"))
    import fusion_settings_backend as sb
    settings = sb.Settings()
    server = QLocalServer()
    QLocalServer.removeServer(name)
    server.listen(name)

    def on_conn():
        c = server.nextPendingConnection()
        if c is None:
            return

        def read():
            try:
                req = json.loads(bytes(c.readAll()).decode().strip() or "{}")
            except ValueError:
                return
            settings.pageRequested.emit(req.get("page", ""), req.get("param", ""))
        c.readyRead.connect(read)
    server.newConnection.connect(on_conn)

    ctx = engine.rootContext()
    ctx.setContextProperty("settings", settings)
    ctx.setContextProperty("startPage", page)
    ctx.setContextProperty("startParam", param)
    ctx.setContextProperty("appMode", app_mode)
    ui.load(engine, os.path.join(HERE, "qml", "Settings.qml"))
    app._keep = [server, settings]
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
