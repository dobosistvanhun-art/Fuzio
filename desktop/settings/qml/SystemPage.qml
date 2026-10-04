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
    Connections { target: settings; function onResult(tag, r) { if (tag === "system" && r.version) p.s = r } }
    Section {
        title: "FUSIONOS"
        InfoRow { icon: "info"; label: "Verzió"; value: "FusionOS " + p.s.version + (p.s.milestone ? " (" + p.s.milestone + ")" : "") }
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
    Flow {
        width: parent.width; spacing: 8
        FButton { text: "Rendszerfrissítés"; icon: "update"; onClicked: settings.pageRequested("update", "") }
        FButton { text: "Feladatkezelő"; icon: "tasks"; onClicked: settings.spawn("fusion-tasks") }
        FButton { text: "Hardverjelentés"; icon: "chip"; onClicked: settings.openTerminal("hwinfo") }
        FButton { text: "Figyelmeztetések (napló)"; icon: "terminal"; onClicked: settings.openTerminal("journal") }
        FButton { text: p.confirm === "reboot" ? "Újraindítás — biztosan?" : "Újraindítás"; icon: "restart"; danger: p.confirm === "reboot"
                  onClicked: p.confirm === "reboot" ? settings.power("reboot") : p.confirm = "reboot" }
        FButton { text: p.confirm === "poweroff" ? "Leállítás — biztosan?" : "Leállítás"; icon: "power"; danger: p.confirm === "poweroff"
                  onClicked: p.confirm === "poweroff" ? settings.power("poweroff") : p.confirm = "poweroff" }
    }
}
