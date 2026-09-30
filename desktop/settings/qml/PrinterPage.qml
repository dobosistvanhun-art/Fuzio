// Nyomtató (Klipper): szolgáltatások, állapot, webes felületek, újraindítás
import QtQuick
import QtQuick.Controls
import FusionUI

SettingsPage {
    id: p
    title: "Nyomtató (Klipper)"
    subtitle: "A Klipper rendszerszolgáltatásként fut; a kezelőfelület a Fluidd vagy a Mainsail"
    property var d: ({ services: {}, klipper: {} })
    property string msg: ""
    property bool working: false
    busy: working
    onRefresh: settings.printerRefresh()
    Component.onCompleted: settings.printerRefresh()
    Timer { interval: 4000; running: true; repeat: true; onTriggered: settings.printerRefresh() }
    Connections {
        target: settings
        function onResult(tag, r) {
            if (tag === "printer" && r.services) p.d = r
            else if (tag === "printer-action") { p.working = false; p.msg = r.rc === 0 ? "kész" + (r.msg ? ": " + r.msg.trim() : "") : "hiba: " + r.msg; settings.printerRefresh() }
        }
    }
    function col(s) { return s === "active" ? Theme.ok : (s === "activating" ? Theme.warn : Theme.danger) }
    Section {
        title: "ÁLLAPOT"
        InfoRow { icon: "printer"; label: "Klipper"; value: (p.d.klipper.state || "?") + (p.d.klipper.message ? "\n" + p.d.klipper.message : "")
                  valueColor: p.d.klipper.state === "ready" ? Theme.ok : Theme.warn
                  FButton { text: "FIRMWARE_RESTART"; enabled: !p.working; onClicked: { p.working = true; settings.printerFirmwareRestart() } } }
        InfoRow { label: "Nyomtató (USB)"; value: p.d.printerPresent ? "csatlakoztatva: /dev/fusion/printer" : "nincs csatlakoztatva"
                  valueColor: p.d.printerPresent ? Theme.ok : Theme.dim }
        InfoRow { label: "Soros port a konfigban"; value: p.d.serial || "—"; mono: true }
        InfoRow { label: "Verzió"; value: p.d.klipper.version || "—"; mono: true }
    }
    Section {
        title: "SZOLGÁLTATÁSOK"
        Repeater {
            model: [["klipper", "Klipper"], ["moonraker", "Moonraker (API)"], ["nginx", "Webszerver (Fluidd :80, Mainsail :81)"]]
            InfoRow { label: modelData[1]; value: p.d.services[modelData[0]] || "?"; valueColor: p.col(p.d.services[modelData[0]])
                      FButton { text: "Újraindítás"; enabled: !p.working; onClicked: { p.working = true; p.msg = ""; settings.printerService(modelData[0]) } } }
        }
    }
    Text { visible: p.msg !== ""; text: p.msg; color: p.msg.indexOf("hiba") === 0 ? Theme.danger : Theme.ok; font.family: Theme.font; width: parent.width; wrapMode: Text.Wrap }
    Flow {
        width: parent.width; spacing: 8
        FButton { text: "Fluidd megnyitása"; icon: "web"; primary: true; onClicked: settings.spawn("fusion-printer ui") }
        FButton { text: "Mainsail megnyitása"; icon: "web"; onClicked: settings.spawn("fusion-printer ui mainsail") }
        FButton { text: "Konfiguráció (Fájlkezelő)"; icon: "files"; onClicked: settings.spawn("fusion-files /data/printer/config") }
        FButton { text: "G-kódok"; icon: "file-code"; onClicked: settings.spawn("fusion-files /data/printer/gcodes") }
        FButton { text: "Napló"; icon: "terminal"; onClicked: settings.openTerminal("printerlog") }
    }
}
