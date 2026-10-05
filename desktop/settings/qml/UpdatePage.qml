// Rendszerfrissítés (M7): a futó rendszer és a két slot állapota, frissítés .fupd fájlból
// (Letöltések, pendrive, /data/import). A frissítés a NEM futó slotba kerül, próbaként indul;
// ha rendben elindul, véglegesül — ha háromszor nem, magától a mostani rendszer indul.
import QtQuick
import QtQuick.Controls
import FusionUI

SettingsPage {
    id: p
    title: "Rendszerfrissítés"
    subtitle: "A FusionOS frissítése fájlból (.fupd) — a frissítés a másik rendszer-slotba kerül, a mostani tartalék marad"
    property var s: ({ entries: [], files: [], version: "", slot: "", state: "" })
    property var job: ({ running: false, lines: [], rc: null, title: "" })
    property string msg: ""
    property string chosen: ""
    property bool pending: false
    busy: job.running
    onRefresh: settings.updateRefresh()
    Component.onCompleted: { settings.updateRefresh(); settings.updateJobWatch() }
    Timer { interval: 8000; running: p.visible && !p.job.running; repeat: true; onTriggered: settings.updateRefresh() }
    Connections {
        target: settings
        function onResult(tag, r) {
            if (tag === "update" && r.version !== undefined) {
                p.s = r
                if (r.job && !p.job.running) p.job = r.job
                if (p.chosen && !r.files.find(f => f.path === p.chosen)) p.chosen = ""
                if (!p.chosen && r.files.length && r.files[0].newer) p.chosen = r.files[0].path
            } else if (tag === "update-job") {
                var was = p.job.running || p.pending
                p.job = r
                if (was && !r.running) { p.pending = false; settings.updateRefresh() }
            }
        }
    }
    function stateText(e) {
        return e.state === "bad" ? "nem indult el (hibás)" : e.state === "trial" ? "próba — még " + e.left + " indítási lehetőség" : "véglegesített"
    }
    readonly property bool done: !job.running && job.rc === 0 && job.recent === true

    Section {
        title: "FUTÓ RENDSZER"
        InfoRow { icon: "chip"; label: "Verzió"; value: "FusionOS " + p.s.version + (p.s.milestone ? " (" + p.s.milestone + ")" : "") + "   ·   slot: " + p.s.slot }
        InfoRow { label: "Indulás"; value: p.s.state || "—"; mono: true
                  valueColor: /^HIBA/.test(p.s.state) ? Theme.danger : /^VÉGLEGESÍTVE/.test(p.s.state) ? Theme.ok : Theme.text }
        InfoRow { visible: p.s.error !== undefined && p.s.error !== ""; label: "Hiba"; value: p.s.error || ""; valueColor: Theme.danger }
    }
    Section {
        title: "RENDSZER-SLOTOK (BOOT MENÜ)"
        Repeater {
            model: p.s.entries
            InfoRow {
                icon: modelData.running ? "check" : ""
                label: "Slot " + modelData.slot + (modelData.running ? " — fut" : "")
                value: "FusionOS " + modelData.version + "   ·   " + p.stateText(modelData) + "\n" + modelData.name
                valueColor: modelData.state === "bad" ? Theme.danger : Theme.text
            }
        }
        InfoRow { visible: p.s.entries.length === 0; label: "—"; value: "nincs adat (a lista root-jogot igényel: fusion-admin update-status)" }
    }

    // --- folyamatban / kész ---
    Section {
        visible: p.job.title !== "" && p.job.recent === true && (p.job.running || p.job.rc !== null)
        title: p.job.running ? "FOLYAMATBAN: " + p.job.title.toUpperCase()
                             : (p.job.rc === 0 ? "KÉSZ: " : "SIKERTELEN: ") + p.job.title.toUpperCase()
        Rectangle {
            width: parent.width; height: logCol.implicitHeight + 16; color: "transparent"
            Column {
                id: logCol; x: 12; y: 8; width: parent.width - 24
                Repeater {
                    model: p.job.lines
                    Text { width: logCol.width; text: modelData; color: /hiba|nem sikerült|sikertelen|eltér|nem egyezik|fusion-(update|admin):/i.test(modelData) ? Theme.danger : Theme.dim
                           font.family: Theme.mono; font.pixelSize: 11; elide: Text.ElideRight; textFormat: Text.PlainText }
                }
            }
        }
        Rectangle {
            visible: p.done; width: parent.width; height: 56; color: "#14301f"
            Text { x: 14; anchors.verticalCenter: parent.verticalCenter; width: parent.width - rb.width - 40; wrapMode: Text.Wrap
                   text: "Az új rendszer a következő indításkor próbaként indul. Ha a felület rendben megjelenik, véglegessé válik."
                   color: Theme.text; font.family: Theme.font; font.pixelSize: 13 }
            FButton { id: rb; anchors.right: parent.right; anchors.rightMargin: 10; anchors.verticalCenter: parent.verticalCenter
                      text: "Újraindítás most"; primary: true; icon: "restart"; onClicked: settings.updateReboot() }
        }
    }

    Section {
        title: "FRISSÍTŐFÁJL (.fupd)"
        Repeater {
            model: p.s.files
            Rectangle {
                width: parent.width; height: 52
                color: p.chosen === modelData.path ? Theme.selected : (fma.containsMouse ? Theme.hover : "transparent")
                MouseArea { id: fma; anchors.fill: parent; hoverEnabled: true; onClicked: p.chosen = modelData.path }
                FIcon { x: 14; anchors.verticalCenter: parent.verticalCenter; size: 26; name: "app-chip" }
                Column {
                    x: 52; anchors.verticalCenter: parent.verticalCenter; width: parent.width - 52 - 140
                    Text { text: "FusionOS " + modelData.version + (modelData.milestone ? " (" + modelData.milestone + ")" : "") +
                                 (modelData.newer ? "" : "   — nem újabb a futó rendszernél")
                           color: modelData.newer ? Theme.text : Theme.dim; font.family: Theme.font; font.pixelSize: 14; font.bold: modelData.newer }
                    Text { width: parent.width; elide: Text.ElideMiddle; text: modelData.place + "/" + modelData.name + "   ·   " + modelData.size
                           color: Theme.dim; font.family: Theme.font; font.pixelSize: 11 }
                }
            }
        }
        InfoRow { visible: p.s.files.length === 0; label: "Nincs frissítőfájl"
                  value: "Másolja a .fupd fájlt a Letöltések mappába vagy egy pendrive-ra, majd: Frissítés (jobb felső gomb)." }
    }
    Flow {
        width: parent.width; spacing: 8
        FButton { text: "Telepítés"; primary: true; icon: "update"; visible: p.s.files.length > 0
                  enabled: p.chosen !== "" && !p.job.running && (p.s.files.find(f => f.path === p.chosen) || {}).newer === true
                  onClicked: { var e = settings.updateInstall(p.chosen); p.msg = e ? "hiba: " + e : ""; if (!e) p.pending = true } }
        Text { visible: p.msg !== ""; text: p.msg; color: Theme.danger; font.family: Theme.font; font.pixelSize: 12; anchors.verticalCenter: parent.verticalCenter }
    }
    Text {
        width: parent.width; wrapMode: Text.Wrap; color: Theme.dim; font.family: Theme.font; font.pixelSize: 11
        text: "A telepítés a DATA-hoz (programok, beállítások, Wi-Fi) nem nyúl. A boot menüben (indításkor 5 mp) mindkét rendszer " +
              "választható. Ha az új rendszer háromszor sem indul el, a gép magától a mostanit indítja, és értesítést kap."
    }
}
