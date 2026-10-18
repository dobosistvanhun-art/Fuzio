// Rendszer: névjegy, hardver, memória, lemezek, újraindítás / leállítás
import QtQuick
import QtQuick.Controls
import FusionUI

SettingsPage {
    id: p
    title: "Rendszer"
    property var s: ({ disks: [], blk: [] })
    property string confirm: ""
    onRefresh: settings.systemRefresh()
    Component.onCompleted: settings.systemRefresh()
    Timer { interval: 5000; running: true; repeat: true; onTriggered: settings.systemRefresh() }
    Connections { target: settings; function onResult(tag, r) { if ((tag === "system" || tag === "trash-empty") && r.version) p.s = r } }
    Section {
        title: "FUSIONOS"
        InfoRow { icon: "info"; label: "Verzió"; value: "Fúzió " + p.s.version + (p.s.milestone ? " (" + p.s.milestone + ")" : "") }
        InfoRow { label: "Rendszerkép"; value: (p.s.image || "?") + "   ·   slot: " + p.s.slot + "   ·   lemez: " + p.s.bootdisk; mono: true }
        InfoRow { label: "Kernel (driveralap)"; value: p.s.kernel || ""; mono: true }
        InfoRow { label: "Bekapcsolva"; value: p.s.uptime || "" }
    }
    Section {
        title: "HARDVER"
        InfoRow { icon: "chip"; label: "Processzor"; value: p.s.cpu || "" }
        InfoRow { label: "Memória"; value: (p.s.memUsed || "") + " / " + (p.s.memTotal || "") + "  (" + (p.s.memPctText || "0") + " %)" }
        InfoRow { icon: "display"; label: "Grafika"; value: p.s.gpu || "—"; mono: true }
        InfoRow { icon: "drive"; label: "Lemezek"; value: (p.s.blk || []).join("\n"); mono: true }
        Repeater {
            model: p.s.disks
            InfoRow {
                label: modelData.name + " (" + modelData.path + ")"
                value: modelData.used + " / " + modelData.total + "  (" + modelData.pctText + " %)"
                valueColor: modelData.pct > 90 ? Theme.danger : Theme.text
            }
        }
    }
    Section {
        title: "LOMTÁR"
        InfoRow { icon: "trash"; label: "Tartalom"; value: p.s.trash ? (p.s.trash.count + " elem, " + p.s.trash.sizeText) : "" }
        Column {
        x: 12; width: parent.width - 24; spacing: 8; topPadding: 6; bottomPadding: 10
        Flow {
            width: parent.width
            spacing: 8
            FLabel { width: 200; height: 30; text: "Automatikus ürítés"; dim: true }
            Repeater {
                model: p.s.trash ? p.s.trash.autoChoices : []
                FButton { text: modelData === 0 ? "Ki" : modelData + " napnál régebbi"; flat: !checked
                          checked: p.s.trash && p.s.trash.autoDays === modelData
                          onClicked: settings.trashSetAuto(modelData) }
            }
        }
        FLabel { width: parent.width; wrapMode: Text.Wrap; elide: Text.ElideNone; dim: true
                 text: "A beállított időnél régebben lomtárba tett elemek végleg törlődnek (bejelentkezés után és 6 óránként). "
                       + "A pendrive-ok lomtára is, ha éppen csatlakoztatva vannak." }
        FButton { text: p.confirm === "trash" ? "Lomtár ürítése — biztosan? (végleges)" : "Lomtár ürítése most"; icon: "trash"
                  danger: p.confirm === "trash"; enabled: !!p.s.trash && p.s.trash.count > 0
                  onClicked: { if (p.confirm === "trash") { settings.trashEmpty(); p.confirm = "" } else p.confirm = "trash" } }
        }
    }
    Flow {
        width: parent.width; spacing: 8
        FButton { text: "Rendszerfrissítés"; icon: "update"; onClicked: settings.pageRequested("update", "") }
        FButton { text: "Feladatkezelő"; icon: "tasks"; onClicked: settings.spawn("fusion-tasks") }
        FButton { text: "Lemezkezelő"; icon: "disks"; onClicked: settings.spawn("fusion-disks") }
        FButton { text: "Hibajelentés"; icon: "report"; onClicked: settings.pageRequested("report", "") }
        FButton { text: "Hardverjelentés"; icon: "chip"; onClicked: settings.openTerminal("hwinfo") }
        FButton { text: "Figyelmeztetések (napló)"; icon: "terminal"; onClicked: settings.openTerminal("journal") }
        FButton { text: p.confirm === "reboot" ? "Újraindítás — biztosan?" : "Újraindítás"; icon: "restart"; danger: p.confirm === "reboot"
                  onClicked: p.confirm === "reboot" ? settings.power("reboot") : p.confirm = "reboot" }
        FButton { text: p.confirm === "poweroff" ? "Leállítás — biztosan?" : "Leállítás"; icon: "power"; danger: p.confirm === "poweroff"
                  onClicked: p.confirm === "poweroff" ? settings.power("poweroff") : p.confirm = "poweroff" }
    }
}
