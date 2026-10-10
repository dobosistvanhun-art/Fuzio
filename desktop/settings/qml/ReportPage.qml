// Hibajelentés: a rendszer állapota egy maszkolt szövegfájlban (Letöltések). Nem küld adatot sehova —
// a felhasználó maga dönti el, kinek adja oda (szerviz, fórum, bármilyen elemző eszköz).
import QtQuick
import QtQuick.Controls
import FusionUI

SettingsPage {
    id: p
    title: "Hibajelentés"
    subtitle: "A rendszer állapota egy szövegfájlban — a gépen marad, nem küld adatot sehova"
    property var s: ({ files: [], dir: "" })
    property var job: ({ running: false, lines: [], rc: null, title: "" })
    property string chosen: ""
    property string preview: ""
    property string msg: ""
    busy: job.running
    onRefresh: settings.reportRefresh()
    Component.onCompleted: { settings.reportRefresh(); settings.reportJobWatch() }
    Connections {
        target: settings
        function onResult(tag, r) {
            if (tag === "report" && r.files !== undefined) {
                p.s = r
                if (r.job && !p.job.running) p.job = r.job
                if (!p.chosen && r.files.length) p.show(r.files[0].path)
            } else if (tag === "report-job") {
                var was = p.job.running
                p.job = r
                if (was && !r.running) { p.chosen = ""; settings.reportRefresh() }
            }
        }
    }
    function show(path) { p.chosen = path; p.preview = settings.reportPreview(path) }

    Section {
        title: "ÚJ HIBAJELENTÉS"
        Column {
            x: 14; width: parent.width - 28; spacing: 10; topPadding: 10; bottomPadding: 12
            Text { width: parent.width; wrapMode: Text.Wrap; color: Theme.dim; font.family: Theme.font; font.pixelSize: 12
                   text: "Írja le röviden, mi a hiba (nem kötelező) — pl. „A LightBurn nem látja a lézert.” A jelentés tartalma: verzió, " +
                         "hardver, szolgáltatások, eszközök, hálózat, lemezek, programok, memória és a naplók hibái. Mentés előtt a " +
                         "jelszavak, kulcsok, Wi-Fi-nevek, e-mail-címek, sorozatszámok és személyes fájlnevek maszkolva lesznek." }
            Rectangle {
                width: parent.width; height: 90; color: Theme.base; radius: Theme.radius
                border.color: desc.activeFocus ? Theme.accent : Theme.border
                ScrollView {
                    anchors.fill: parent; anchors.margins: 1
                    TextArea {
                        id: desc
                        placeholderText: "A hiba leírása…"
                        color: Theme.text; placeholderTextColor: Theme.dim
                        font.family: Theme.font; font.pixelSize: 13; wrapMode: TextEdit.Wrap
                        background: null
                    }
                }
            }
            Row {
                spacing: 10
                FButton { text: "Hibajelentés készítése"; icon: "report"; primary: true; enabled: !p.job.running
                          onClicked: { var e = settings.reportCreate(desc.text); p.msg = e ? "hiba: " + e : "" } }
                Text { visible: p.msg !== ""; text: p.msg; color: Theme.danger; font.family: Theme.font; font.pixelSize: 12
                       anchors.verticalCenter: parent.verticalCenter }
            }
        }
    }

    Section {
        visible: p.job.title !== "" && p.job.recent === true && (p.job.running || p.job.rc !== null)
        title: p.job.running ? "KÉSZÜL…" : (p.job.rc === 0 ? "KÉSZ" : "SIKERTELEN")
        Column {
            x: 14; width: parent.width - 28; topPadding: 8; bottomPadding: 8
            Repeater {
                model: p.job.lines
                Text { width: parent.width; text: modelData; elide: Text.ElideMiddle; textFormat: Text.PlainText
                       color: /^(hiba|fusion-report:|Traceback)|sikertelen/i.test(modelData) ? Theme.danger : Theme.dim
                       font.family: Theme.mono; font.pixelSize: 11 }
            }
        }
    }

    Section {
        title: "JELENTÉSEK (" + (p.s.dir || "").replace(/^\/home\/[^/]+/, "~") + ")"
        Repeater {
            model: p.s.files
            Rectangle {
                width: parent.width; height: 44
                color: p.chosen === modelData.path ? Theme.selected : (rma.containsMouse ? Theme.hover : "transparent")
                MouseArea { id: rma; anchors.fill: parent; hoverEnabled: true; onClicked: p.show(modelData.path) }
                FIcon { x: 14; anchors.verticalCenter: parent.verticalCenter; size: 20; name: "file-text" }
                Text { x: 46; anchors.verticalCenter: parent.verticalCenter; width: parent.width - 46 - 200; elide: Text.ElideMiddle
                       text: modelData.name; color: Theme.text; font.family: Theme.font; font.pixelSize: 13 }
                Text { anchors.right: parent.right; anchors.rightMargin: 14; anchors.verticalCenter: parent.verticalCenter
                       text: modelData.time + "   ·   " + modelData.size; color: Theme.dim; font.family: Theme.font; font.pixelSize: 11 }
            }
        }
        InfoRow { visible: p.s.files.length === 0; label: "Még nincs"; value: "A „Hibajelentés készítése” gomb a Letöltések mappába menti." }
    }
    Row {
        visible: p.chosen !== ""; spacing: 8
        FButton { text: "Megjelenítés a Fájlkezelőben"; icon: "files"; onClicked: settings.reportShow(p.chosen) }
    }
    Rectangle {
        visible: p.chosen !== "" && p.preview !== ""
        width: parent.width; height: 380; color: Theme.base; border.color: Theme.border
        ScrollView {
            anchors.fill: parent; anchors.margins: 1
            TextArea {
                readOnly: true; text: p.preview; textFormat: TextEdit.PlainText
                color: Theme.text; selectionColor: Theme.accent; selectedTextColor: "white"
                font.family: Theme.mono; font.pixelSize: 11; wrapMode: TextEdit.NoWrap; selectByMouse: true
                background: null
            }
        }
    }
    Text {
        width: parent.width; wrapMode: Text.Wrap; color: Theme.dim; font.family: Theme.font; font.pixelSize: 11
        text: "Ha a felület nem indul: Ctrl+Alt+F2, bejelentkezés, majd: fusion-report -o /run/media/fusion/<pendrive>  " +
              "(a jelentés a pendrive-ra kerül). Megosztás előtt érdemes átolvasni."
    }
}
