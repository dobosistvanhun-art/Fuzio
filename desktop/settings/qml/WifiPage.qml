// Wi-Fi és hálózat: állapot, elérhető hálózatok, kapcsolódás jelszóval, megjegyzett hálózatok
import QtQuick
import QtQuick.Controls
import FusionUI

SettingsPage {
    id: p
    title: "Wi-Fi és hálózat"
    subtitle: st.device ? ("Eszköz: " + st.device + (st.ip ? "   ·   Cím: " + st.ip : "")) : (st.error || "")
    property var st: ({})
    property var nets: []
    property var wired: []
    property string msg: ""
    property bool scanning: false
    property bool connecting: false
    busy: scanning || connecting
    onRefresh: settings.wifiScan()
    Component.onCompleted: { settings.wifiRefresh(); scanning = true; settings.wifiScan() }
    Timer { interval: 4000; running: true; repeat: true; onTriggered: settings.wifiRefresh() }
    Connections {
        target: settings
        function onResult(tag, r) {
            if (tag === "wifi" || tag === "wifi-scan") {
                if (r.state) { p.st = r.state; p.nets = r.networks || []; p.wired = r.wired || [] }
                if (tag === "wifi-scan") p.scanning = false
            } else if (tag === "wifi-connect") {
                p.connecting = false
                p.msg = r.ok ? ("Kapcsolódva: " + r.name) : ("Nem sikerült: " + r.name + " — " + r.msg)
                settings.wifiRefresh()
            } else if (tag === "wifi-action") { settings.wifiRefresh() }
        }
    }
    function isKnown(n) { return (p.st.known || []).some(k => k.name === n) }

    Section {
        title: "ÁLLAPOT"
        InfoRow {
            icon: "wifi"; label: "Wi-Fi"
            value: p.st.state === "connected" ? ("Kapcsolódva: " + p.st.ssid) : (p.st.state === "connecting" ? "Kapcsolódás…" : (p.st.ok === false ? (p.st.error || "nem érhető el") : "Nincs kapcsolat"))
            valueColor: p.st.state === "connected" ? Theme.ok : Theme.text
            FButton { visible: p.st.state === "connected"; text: "Bontás"; onClicked: settings.wifiDisconnect() }
        }
        Repeater {
            model: p.wired
            InfoRow { icon: "web"; label: "Vezetékes: " + modelData.name; value: modelData.ip ? (modelData.ip + "  (" + modelData.state + ")") : modelData.state }
        }
    }
    Text { visible: p.msg !== ""; text: p.msg; color: p.msg.indexOf("Nem") === 0 ? Theme.danger : Theme.ok; font.family: Theme.font; font.pixelSize: 13 }

    Section {
        title: "ELÉRHETŐ HÁLÓZATOK" + (p.scanning ? "  —  keresés…" : "")
        Repeater {
            model: p.nets
            Rectangle {
                width: parent.width; height: 48; color: nma.containsMouse ? Theme.hover : "transparent"
                Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: "#232c38" }
                FSignal { x: 16; anchors.verticalCenter: parent.verticalCenter; level: modelData.level; on: modelData.connected ? Theme.ok : Theme.text }
                Column {
                    x: 50; anchors.verticalCenter: parent.verticalCenter
                    Text { text: modelData.name; color: Theme.text; font.family: Theme.font; font.pixelSize: 14; font.bold: modelData.connected }
                    Text { text: (modelData.connected ? "Kapcsolódva · " : "") + (modelData.type === "open" ? "nyílt (jelszó nélkül)" : "védett (" + modelData.type + ")")
                                 + (modelData.known ? " · megjegyzett" : "") + " · " + Math.round(modelData.signal / 100) + " dBm"
                           color: Theme.dim; font.family: Theme.font; font.pixelSize: 11 }
                }
                MouseArea { id: nma; anchors.fill: parent; hoverEnabled: true; z: -1 }
                Row {
                    anchors.right: parent.right; anchors.rightMargin: 10; anchors.verticalCenter: parent.verticalCenter; spacing: 6
                    FButton { visible: !modelData.connected; text: "Kapcsolódás"; primary: true; enabled: !p.connecting
                        onClicked: {
                            if (modelData.known || modelData.type === "open") { p.connecting = true; p.msg = ""; settings.wifiConnect(modelData.name, "") }
                            else { passDlg.ssid = modelData.name; passDlg.open() }
                        } }
                    FButton { visible: modelData.known; text: "Elfelejtés"; onClicked: settings.wifiForget(modelData.name) }
                }
            }
        }
        Text { visible: p.nets.length === 0; padding: 14; text: p.scanning ? "Keresés…" : "Nem található hálózat"; color: Theme.dim; font.family: Theme.font }
    }
    Section {
        title: "MEGJEGYZETT HÁLÓZATOK (a DATA-n tárolva, automatikusan kapcsolódik)"
        visible: (p.st.known || []).length > 0
        Repeater {
            model: p.st.known || []
            InfoRow { icon: "lock"; label: modelData.name; value: modelData.type
                FButton { text: "Elfelejtés"; onClicked: settings.wifiForget(modelData.name) } }
        }
    }

    FDialog {
        id: passDlg
        property string ssid: ""
        title: "Kapcsolódás: " + ssid
        buttons: [["Mégse", ""], ["Kapcsolódás", "primary"]]
        width: 460
        onOpened: { pass.text = ""; pass.forceActiveFocus() }
        onButtonClicked: (i) => { close(); if (i === 1 && pass.text) { p.connecting = true; p.msg = ""; settings.wifiConnect(ssid, pass.text) } }
        Column {
            x: 20; y: 16; width: 420; spacing: 8
            Text { text: "Jelszó:"; color: Theme.text; font.family: Theme.font; font.pixelSize: 13 }
            FTextField { id: pass; width: parent.width; echoMode: show.checked ? TextInput.Normal : TextInput.Password
                         Keys.onReturnPressed: passDlg.press(1) }
            FCheck { id: show; text: "Jelszó megjelenítése" }
        }
    }
}
