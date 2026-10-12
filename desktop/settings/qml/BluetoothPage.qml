// Bluetooth: adapter be / ki, eszközök keresése, párosítás, csatlakozás, eltávolítás (BlueZ)
import QtQuick
import QtQuick.Controls
import FusionUI

SettingsPage {
    id: p
    title: "Bluetooth"
    subtitle: a.present ? (a.name + "   ·   " + a.address) : ""
    property var a: ({ present: false, powered: false, blocked: false, hardBlocked: false })
    property var devs: []
    property bool loaded: false
    property bool scanning: false
    property string pairing: ""          // a párosítás alatt álló eszköz címe
    property string code: ""             // a másik eszköz által kért kód
    property string codeKind: ""
    property string msg: ""
    property bool msgErr: false
    busy: scanning || pairing !== ""
    onRefresh: settings.btRefresh()
    Component.onCompleted: settings.btRefresh()
    Timer { interval: 3000; running: true; repeat: true; onTriggered: settings.btRefresh() }
    function say(t, err) { msg = t; msgErr = err }
    Connections {
        target: settings
        function onResult(tag, r) {
            if (tag === "bt") {
                if (r.adapter) { p.a = r.adapter; p.devs = r.devices || [] }
                p.loaded = true
            } else if (tag === "bt-scan") {
                p.scanning = false
                if (!r.ok) p.say("A keresés nem sikerült: " + r.msg, true)
                settings.btRefresh()
            } else if (tag === "bt-code") {
                p.code = r.code; p.codeKind = r.kind
            } else if (tag === "bt-pair") {
                var n = p.nameOf(p.pairing)
                p.pairing = ""; p.code = ""
                p.say(r.ok ? (r.msg ? n + ": " + r.msg : "Párosítva és csatlakozva: " + n) : "A párosítás nem sikerült: " + r.msg, !r.ok)
                settings.btRefresh()
            } else if (tag === "bt-action") {
                if (!r.ok) p.say(r.msg, true); else p.msg = ""
                settings.btRefresh()
            } else if (tag === "service-restart") {
                p.say(r.rc === 0 ? "A Bluetooth-szolgáltatás újraindult." : "Hiba: " + r.msg, r.rc !== 0)
                settings.btRefresh()
            }
        }
    }
    function nameOf(addr) { var d = p.devs.find(x => x.address === addr); return d ? d.name : addr }
    function iconFor(d) {
        return /audio/.test(d.icon) ? "volume" : /input-keyboard/.test(d.icon) ? "file-text"
             : /input/.test(d.icon) ? "move" : /phone/.test(d.icon) ? "dot" : "bluetooth"
    }
    readonly property var paired: devs.filter(d => d.paired)
    readonly property var found: devs.filter(d => !d.paired)

    Text {
        visible: p.loaded && !p.a.present; width: parent.width; wrapMode: Text.Wrap; color: Theme.warn
        font.family: Theme.font; font.pixelSize: 13
        text: p.a.hardBlocked ? "A Bluetooth-rádió a gép kapcsolójával (Fn-billentyű / vezeték nélküli kapcsoló) ki van kapcsolva."
            : "Nem található Bluetooth-adapter. A beépített Bluetooth egyes gépeken a BIOS-ban kapcsolható ki; "
              + "USB-s Bluetooth-adapter is használható — dugja be, és ez az oldal magától frissül."
              + (p.a.blocked ? " (A rádió szoftveresen tiltva — a bekapcsolás feloldja.)" : "")
    }

    Section {
        title: "ADAPTER"
        visible: p.a.present
        InfoRow {
            icon: "bluetooth"; label: "Bluetooth"
            value: p.a.powered ? "bekapcsolva" : "kikapcsolva"
            valueColor: p.a.powered ? Theme.ok : Theme.dim
            FButton { text: p.a.powered ? "Kikapcsolás" : "Bekapcsolás"; primary: !p.a.powered
                      onClicked: { p.msg = ""; settings.btPower(!p.a.powered) } }
        }
    }
    Text { visible: p.msg !== ""; width: parent.width; wrapMode: Text.Wrap; text: p.msg
           color: p.msgErr ? Theme.danger : Theme.ok; font.family: Theme.font; font.pixelSize: 13 }

    // párosítás közben: a másik eszköz kódja
    Rectangle {
        visible: p.pairing !== ""
        width: parent.width; height: pc.implicitHeight + 24; radius: Theme.radius
        color: "#1d2a3a"; border.color: Theme.accent
        Column {
            id: pc; x: 16; y: 12; width: parent.width - 32; spacing: 6
            FLabel { text: "Párosítás: " + p.nameOf(p.pairing) + " …"; bold: true }
            FLabel { visible: p.code === ""; dim: true; width: parent.width; wrapMode: Text.Wrap
                     text: "Ha az eszköz (pl. fejhallgató) gombot kér, nyomja meg rajta a párosítás gombot." }
            FLabel { visible: p.code !== ""; width: parent.width; wrapMode: Text.Wrap
                     text: p.codeKind === "passkey" ? "Gépelje be ezt a kódot a billentyűzeten, majd nyomjon Entert:"
                         : p.codeKind === "pin" ? "Ha az eszköz PIN-kódot kér, ez az:"
                         : "Ellenőrizze, hogy az eszközön is ez a kód látszik:" }
            Text { visible: p.code !== ""; text: p.code; color: Theme.text; font.family: Theme.mono; font.pixelSize: 30; font.bold: true }
        }
    }

    Section {
        title: "PÁROSÍTOTT ESZKÖZÖK"
        visible: p.a.present
        Repeater {
            model: p.paired
            InfoRow {
                icon: p.iconFor(modelData)
                label: modelData.name
                value: (modelData.connected ? "csatlakozva" : "nincs csatlakozva") + "  ·  " + modelData.kind
                       + (modelData.battery !== null && modelData.battery !== undefined ? "  ·  akku " + modelData.battery + "%" : "")
                valueColor: modelData.connected ? Theme.ok : Theme.dim
                FButton { text: modelData.connected ? "Bontás" : "Csatlakozás"; enabled: p.a.powered
                          onClicked: { p.msg = ""; modelData.connected ? settings.btDisconnect(modelData.address) : settings.btConnect(modelData.address) } }
                FButton { text: "Eltávolítás"; flat: true; onClicked: { p.msg = ""; settings.btRemove(modelData.address) } }
            }
        }
        Text { visible: p.paired.length === 0; padding: 14; color: Theme.dim; font.family: Theme.font
               text: "Még nincs párosított eszköz." }
    }

    Section {
        title: "ESZKÖZ HOZZÁADÁSA" + (p.scanning ? "  —  keresés…" : "")
        visible: p.a.present
        InfoRow {
            icon: "search"; label: "Keresés"
            value: "Tegye az eszközt párosítható módba (a legtöbb fejhallgatón: a bekapcsológomb hosszan nyomva), majd keressen."
            FButton { text: p.scanning ? "Keresés…" : "Keresés"; primary: true; enabled: p.a.powered && !p.scanning && p.pairing === ""
                      onClicked: { p.msg = ""; p.scanning = true; settings.btScan() } }
        }
        Repeater {
            model: p.found
            InfoRow {
                icon: p.iconFor(modelData)
                label: modelData.name
                value: modelData.kind + (modelData.name === modelData.address ? "" : "  ·  " + modelData.address)
                valueColor: Theme.dim
                FButton { text: p.pairing === modelData.address ? "Párosítás…" : "Párosítás"
                          enabled: p.a.powered && p.pairing === ""
                          onClicked: { p.msg = ""; p.code = ""; p.pairing = modelData.address; settings.btPair(modelData.address) } }
            }
        }
        Text { visible: p.found.length === 0 && !p.scanning; padding: 14; color: Theme.dim; font.family: Theme.font
               text: p.a.powered ? "Nincs talált eszköz — Keresés." : "Kapcsolja be a Bluetooth-t." }
    }

    Section {
        title: "SZOLGÁLTATÁS"
        InfoRow { icon: "info"; label: "BlueZ"; value: p.a.service || "—"; mono: true
                  FButton { text: "Újraindítás"; icon: "restart"; onClicked: { p.msg = ""; settings.serviceRestart("bluetooth") } } }
        InfoRow { icon: "volume"; label: "Hang"; value: "a csatlakoztatott fejhallgató / hangszóró a Hang oldalon választható kimenetként" }
    }
}
