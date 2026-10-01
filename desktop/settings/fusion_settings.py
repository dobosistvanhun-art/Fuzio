#!/usr/bin/python3
"""FusionOS — Beállítások (fusion-settings)

    fusion-settings [oldal] [paraméter]
        oldal: wifi | display | devices | printer | sound | programs | store | desktop | system
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
PAGES = ["wifi", "display", "devices", "printer", "sound", "programs", "store", "desktop", "system"]


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
    all_apps = fusion_apps.load()
    print("FUSION-SETTINGS: APPS " + ",".join(a["id"] for a in all_apps if not a["search_only"]), flush=True)
    return 0


def main():
    args = sys.argv[1:]
    if args[:1] == ["--selftest"]:
        return selftest()
    page = args[0] if args and args[0] in PAGES else "wifi"
    param = args[1] if len(args) > 1 else ""

    from PyQt6.QtNetwork import QLocalServer, QLocalSocket
    name = f"fusion-settings-{os.getuid()}"
    # már fut? → oldalváltás kérése, és kilépés
    sock = QLocalSocket()
    sock.connectToServer(name)
    if sock.waitForConnected(300):
        sock.write(json.dumps({"page": page, "param": param}).encode() + b"\n")
        sock.waitForBytesWritten(500)
        sock.disconnectFromServer()
        return 0

    app, engine = ui.create_app("fusion-settings", "Beállítások", "settings")
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
    ui.load(engine, os.path.join(HERE, "qml", "Settings.qml"))
    app._keep = [server, settings]
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
