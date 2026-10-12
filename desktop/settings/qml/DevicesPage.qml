// Eszközök: a Fusion eszközréteg szerepei (lézer, 3D nyomtató), soros eszközök, kamerák, USB-eszközök
import QtQuick
import QtQuick.Controls
import FusionUI

SettingsPage {
    id: p
    title: "Eszközök és kamera"
    subtitle: "A soros eszközök szerepet kapnak (/dev/fusion/…) — a programok ezen a néven érik el őket"
    property var d: ({ roles: [], serial: [], usb: [], cameras: [] })
    property string msg: ""
    onRefresh: settings.devicesRefresh()
    Component.onCompleted: settings.devicesRefresh()
    Timer { interval: 3000; running: true; repeat: true; onTriggered: settings.devicesRefresh() }
    Connections {
        target: settings
        function onResult(tag, r) {
            if (tag === "devices" && r.roles) p.d = r
            else if (tag === "devices-action") { p.msg = (r.msg || "").trim(); settings.devicesRefresh() }
        }
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
