// Eszközök: touchpad (koppintás, görgetés, sebesség), a Fúzió eszközréteg szerepei (lézer, 3D nyomtató), soros eszközök, kamerák, USB-eszközök
import QtQuick
import QtQuick.Controls
import FusionUI

SettingsPage {
    id: p
    title: "Eszközök és kamera"
    subtitle: "A soros eszközök szerepet kapnak (/dev/fusion/…) — a programok ezen a néven érik el őket"
    property var d: ({ roles: [], serial: [], usb: [], cameras: [] })
    property string msg: ""
    property var tp: ({ ok: false, error: "", devices: [], settings: {}, available: {} })
    readonly property var ts: p.tp.settings || {}
    onRefresh: { settings.devicesRefresh(); settings.touchpadRefresh() }
    Component.onCompleted: { settings.devicesRefresh(); settings.touchpadRefresh() }
    Timer { interval: 3000; running: true; repeat: true; onTriggered: settings.devicesRefresh() }
    Connections {
        target: settings
        function onResult(tag, r) {
            if (tag === "devices" && r.roles) p.d = r
            else if (tag === "touchpad") p.tp = r
            else if (tag === "devices-action") { p.msg = (r.msg || "").trim(); settings.devicesRefresh() }
        }
    }
    Section {
        title: "TOUCHPAD"
        visible: p.tp.ok && p.tp.devices.length > 0 || p.tp.error !== ""
        InfoRow {
            icon: "touchpad"; label: "Touchpad"
            value: p.tp.devices.length ? p.tp.devices.map(x => x.name).join(", ") : (p.tp.error || "nincs touchpad")
            valueColor: p.ts.enabled === false ? Theme.warn : Theme.text
            FCheck { text: "bekapcsolva"; checked: p.ts.enabled !== false; onToggled: settings.touchpadSet("enabled", checked) }
        }
        InfoRow {
            label: "Kattintás"; value: "Koppintás = bal gomb, két ujjal koppintás = jobb gomb, három ujjal = középső gomb"
            FCheck { text: "koppintással"; checked: p.ts.tap !== false; onToggled: settings.touchpadSet("tap", checked) }
        }
        InfoRow {
            label: "Görgetés"
            value: p.ts.scroll === "edge" ? "Egy ujjal a touchpad jobb (és alsó) szélén húzva"
                 : p.ts.scroll === "none" ? "Nincs görgetés a touchpadon"
                 : "Két ujjal húzva, függőlegesen és vízszintesen"
            FButton { text: "Két ujjal"; checked: p.ts.scroll === "twofinger"; visible: (p.tp.available.scroll || []).indexOf("twofinger") >= 0
                      onClicked: settings.touchpadSet("scroll", "twofinger") }
            FButton { text: "A szélén"; checked: p.ts.scroll === "edge"; visible: (p.tp.available.scroll || []).indexOf("edge") >= 0
                      onClicked: settings.touchpadSet("scroll", "edge") }
            FButton { text: "Ki"; checked: p.ts.scroll === "none"; onClicked: settings.touchpadSet("scroll", "none") }
        }
        InfoRow {
            label: "Görgetés iránya"; value: p.ts.natural ? "Természetes: a tartalom az ujjal együtt mozog (mint a telefonon)" : "Hagyományos: mint az egér görgője"
            FCheck { text: "természetes"; checked: p.ts.natural === true; onToggled: settings.touchpadSet("natural", checked) }
        }
        InfoRow {
            label: "Gépelés közben"; value: "A touchpad gépelés közben (és utána egy pillanatig) nem mozgatja az egeret"
            FCheck { text: "tiltva"; checked: p.ts.dwt !== false; onToggled: settings.touchpadSet("dwt", checked) }
        }
        InfoRow {
            label: "Sebesség"; value: ""
            Timer { id: spt; interval: 250; onTriggered: settings.touchpadSet("speed", Math.round(sps.value * 100) / 100) }
            FSlider { id: sps; width: 220; from: -1; to: 1; value: p.ts.speed || 0; onMoved: spt.restart() }
            Text { width: 54; text: (sps.value >= 0 ? "+" : "") + sps.value.toFixed(2); color: Theme.text
                   font.family: Theme.font; font.pixelSize: 13; anchors.verticalCenter: parent.verticalCenter }
        }
        Text { visible: p.tp.error !== ""; padding: 14; width: parent.width; wrapMode: Text.Wrap; color: Theme.warn; font.family: Theme.font
               text: p.tp.error }
    }
    Section {
        title: "SZEREPEK"
        Repeater {
            model: p.d.roles
            InfoRow {
                icon: modelData.role === "laser" ? "laser" : modelData.role === "printer" ? "printer" : "usb"
                label: modelData.name
                value: (modelData.present ? "Csatlakoztatva: " + modelData.dev + "  →  /dev/fusion/" + modelData.role
                                          : (modelData.key ? "Nincs csatlakoztatva" : "Nincs hozzárendelve (az első illeszkedő eszköz automatikusan megkapja)"))
                       + ((modelData.programs || []).length
                          ? "\nWindows-programok: " + modelData.programs.map(x => (x.name || x.id) + " → " + x.com).join(", ")
                          : (modelData.com ? "\nWindows-programoknak ajánlott: " + modelData.com + " (Programkezelő → Eszközök)" : ""))
                       + (modelData.key ? "\nAzonosító: " + modelData.key : "")
                valueColor: modelData.present ? Theme.ok : Theme.text
                FButton { visible: modelData.key !== ""; text: "Elfelejtés"; onClicked: settings.deviceForget(modelData.role) }
            }
        }
    }
    Text { visible: p.msg !== ""; text: p.msg; color: Theme.dim; font.family: Theme.mono; font.pixelSize: 12; width: parent.width; wrapMode: Text.Wrap }
    Section {
        title: "SOROS ESZKÖZÖK (USB-soros átalakítók, vezérlők)"
        Repeater {
            model: p.d.serial
            InfoRow {
                icon: "usb"; label: modelData.dev
                value: modelData.id + "  " + (modelData.vendor ? modelData.vendor + " " : "") + modelData.model
                       + (modelData.role ? "\nSzerep: " + modelData.role : "") + (modelData.port ? "\nPort: " + modelData.port : "")
                       + (modelData.serial ? "  ·  sorozatszám: " + modelData.serial : "")
                FButton { visible: modelData.role === ""; text: "Legyen: lézer"; onClicked: settings.deviceAssign("laser", modelData.dev) }
                FButton { visible: modelData.role === ""; text: "Legyen: nyomtató"; onClicked: settings.deviceAssign("printer", modelData.dev) }
            }
        }
        Text { visible: p.d.serial.length === 0; padding: 14; text: "Nincs csatlakoztatott soros eszköz"; color: Theme.dim; font.family: Theme.font }
    }
    Section {
        title: "KAMERÁK"
        Repeater {
            model: p.d.cameras || []
            InfoRow { icon: "camera"; label: modelData.dev; value: modelData.name + "  ·  " + modelData.bus + (modelData.usb ? " " + modelData.usb : "")
                      FButton { text: "Megnyitás"; icon: "camera"; onClicked: settings.cameraOpen() } }
        }
        Text { visible: (p.d.cameras || []).length === 0; padding: 14; width: parent.width; wrapMode: Text.Wrap; color: Theme.dim; font.family: Theme.font
               text: "Nincs kamera. A beépített webkamera egyes gépeken a BIOS-ban kapcsolható ki; USB-kamera: dugja be." }
    }
    Section {
        title: "USB-ESZKÖZÖK"
        Repeater {
            model: p.d.usb
            InfoRow { label: modelData.id; value: modelData.name; mono: false }
        }
    }
    FButton { text: "Részletes jelentés (terminálban)"; icon: "terminal"; onClicked: settings.openTerminal("devices") }
}
