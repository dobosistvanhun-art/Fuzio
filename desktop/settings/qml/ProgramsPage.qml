// Programok: Windows-programok (Fusion Windows Runtime) — telepítés, indítás
import QtQuick
import QtQuick.Controls
import FusionUI

SettingsPage {
    id: p
    title: "Programok"
    subtitle: "Windows-programok telepítése: a program saját, elkülönített futtatókörnyezetet kap"
    property var apps: []
    property var inst: []
    property string chosen: win.param && /\.(exe|msi)$/i.test(win.param) ? win.param : ""
    property string msg: ""
    onRefresh: settings.programsRefresh()
    Component.onCompleted: settings.programsRefresh()
    Connections {
        target: settings
        function onResult(tag, r) { if (tag === "programs" && r.apps) { p.apps = r.apps; p.inst = r.installers || [] } }
    }
    Section {
        title: "WINDOWS-PROGRAMOK"
        Repeater {
            model: p.apps
            InfoRow {
                icon: modelData.icon === "laser" ? "laser" : "app"
                label: modelData.name
                value: modelData.installed ? "Telepítve — indítás a Start menüből" : "Nincs telepítve"
                valueColor: modelData.installed ? Theme.ok : Theme.dim
                FButton { visible: modelData.installed; text: "Indítás"; primary: true; onClicked: settings.programLaunch(modelData.fwr) }
                FButton { text: modelData.installed ? "Újratelepítés / frissítés" : "Telepítés"; enabled: p.chosen !== ""
                          tip: p.chosen ? p.chosen : "Előbb válassza ki a telepítőt lent"
                          onClicked: { var e = settings.programInstall(modelData.fwr, p.chosen); p.msg = e ? "hiba: " + e : "A telepítő elindult: " + p.chosen.split("/").pop() + " — a végén értesítés jön." } }
            }
        }
        Text { visible: p.apps.length === 0; padding: 14; text: "Nincs Windows-program profil"; color: Theme.dim; font.family: Theme.font }
    }
    Text { visible: p.msg !== ""; text: p.msg; color: p.msg.indexOf("hiba") === 0 ? Theme.danger : Theme.ok; font.family: Theme.font; width: parent.width; wrapMode: Text.Wrap }
    Section {
        title: "TELEPÍTŐ KIVÁLASZTÁSA (saját mappa, Letöltések, /data/import, USB-meghajtók)"
        InfoRow { icon: "file-exe"; label: "Kiválasztva"; value: p.chosen || "—"; mono: true
                  FButton { text: "Fájlkezelő"; icon: "files"; onClicked: settings.spawn("fusion-files /data/import") } }
        Repeater {
            model: p.inst
            Rectangle {
                width: parent.width; height: 34; color: modelData.path === p.chosen ? Theme.selected : (ima.containsMouse ? Theme.hover : "transparent")
                FIcon { x: 14; anchors.verticalCenter: parent.verticalCenter; name: "file-exe"; size: 16 }
                Text { x: 40; anchors.verticalCenter: parent.verticalCenter; width: parent.width - 220; elide: Text.ElideMiddle
                       text: modelData.path; color: Theme.text; font.family: Theme.font; font.pixelSize: 12 }
                Text { anchors.right: parent.right; anchors.rightMargin: 14; anchors.verticalCenter: parent.verticalCenter
                       text: modelData.size + "   " + modelData.date; color: Theme.dim; font.family: Theme.font; font.pixelSize: 11 }
                MouseArea { id: ima; anchors.fill: parent; hoverEnabled: true; onClicked: p.chosen = modelData.path }
            }
        }
        Text { visible: p.inst.length === 0; padding: 14; text: "Nem található telepítő (.exe, .msi). Másolja a /data/import mappába, vagy nyissa meg a Fájlkezelőben (Enter a telepítőn)."
               color: Theme.dim; font.family: Theme.font; width: parent.width; wrapMode: Text.Wrap }
    }
    FButton { text: "A futtatókörnyezet ellenőrzése (fwr check)"; icon: "check"; onClicked: settings.openTerminal("fwrcheck") }
}
