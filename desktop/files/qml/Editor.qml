// FusionOS — Fájlkezelő: egyszerű szövegszerkesztő (F4) — konfigurációk, G-kód, jegyzetek
import QtQuick
import QtQuick.Controls
import FusionUI

FWindow {
    id: ed
    property string path: ""
    property var info: ({})
    property bool modified: false
    property bool loading: true
    property bool allowClose: false
    width: 1100; height: 800
    visible: true
    title: (modified ? "● " : "") + (info.name || "") + " — Szerkesztés"
    Component.onCompleted: {
        info = files.readFile(path)
        area.text = info.text || ""
        loading = false; modified = false
        area.forceActiveFocus(); area.cursorPosition = 0
        ed.raise(); ed.requestActivate()
    }
    onClosing: (close) => {
        if (modified && !allowClose) { close.accepted = false; askSave.open(); return }
        destroy()
    }
    function save() {
        var e = files.writeFile(path, area.text)
        if (e) { status.text = "Nem menthető: " + e; status.color = Theme.danger; return false }
        modified = false; status.text = "Mentve: " + new Date().toLocaleTimeString(Qt.locale("hu_HU"), "HH:mm:ss"); status.color = Theme.ok
        return true
    }
    function findNext(t) {
        if (!t) return
        var s = area.text.toLowerCase(), i = s.indexOf(t.toLowerCase(), area.cursorPosition)
        if (i < 0) i = s.indexOf(t.toLowerCase())
        if (i >= 0) { area.select(i, i + t.length) } else { status.text = "nem található: " + t; status.color = Theme.warn }
    }
    readonly property bool readOnly: info.binary === true || info.truncated === true || !!info.error

    Shortcut { sequence: "Ctrl+S"; onActivated: ed.save() }
    Shortcut { sequences: ["Esc", "F10"]; onActivated: ed.close() }
    Shortcut { sequence: "Ctrl+F"; onActivated: { findField.forceActiveFocus(); findField.selectAll() } }
    Shortcut { sequence: "F3"; onActivated: ed.findNext(findField.text) }

    header: Rectangle {
        height: 40; color: Theme.panel
        Row {
            x: 8; anchors.verticalCenter: parent.verticalCenter; spacing: 6
            FButton { text: "Mentés (Ctrl+S)"; icon: "check"; primary: ed.modified; enabled: !ed.readOnly; onClicked: ed.save() }
            FTextField { id: findField; width: 220; placeholderText: "Keresés (Ctrl+F, F3: következő)"
                         Keys.onReturnPressed: ed.findNext(text); Keys.onEscapePressed: area.forceActiveFocus() }
            Text { anchors.verticalCenter: parent.verticalCenter; text: ed.path; color: Theme.dim; font.family: Theme.font; font.pixelSize: 11
                   width: ed.width - 700; elide: Text.ElideMiddle }
        }
        Text {
            id: status
            anchors.right: parent.right; anchors.rightMargin: 12; anchors.verticalCenter: parent.verticalCenter
            text: ed.readOnly ? (ed.info.error ? "hiba: " + ed.info.error : "csak olvasható (bináris vagy túl nagy fájl)") : ""
            color: ed.readOnly ? Theme.warn : Theme.dim; font.family: Theme.font; font.pixelSize: 12
        }
    }
    footer: Rectangle {
        height: 22; color: Theme.panel
        Text { x: 10; anchors.verticalCenter: parent.verticalCenter; color: Theme.dim; font.family: Theme.font; font.pixelSize: 11
               text: "sor: " + (area.text.substring(0, area.cursorPosition).split("\n").length) + "   ·   " + area.length + " karakter   ·   UTF-8" }
    }
    ScrollView {
        anchors.fill: parent
        TextArea {
            id: area
            readOnly: ed.readOnly
            color: Theme.text; selectionColor: Theme.accent; selectedTextColor: "white"
            font.family: Theme.mono; font.pixelSize: 13
            wrapMode: TextEdit.NoWrap
            textFormat: TextEdit.PlainText
            selectByMouse: true; persistentSelection: true
            tabStopDistance: 32
            background: Rectangle { color: Theme.base }
            onTextChanged: if (ed && !ed.loading) ed.modified = true
        }
    }
    FDialog {
        id: askSave
        title: "Nem mentett változások"
        buttons: [["Mégse", ""], ["Elvetés", "danger"], ["Mentés", "primary"]]
        onButtonClicked: (i) => {
            close()
            if (i === 2 && !ed.save()) return
            if (i >= 1) { ed.allowClose = true; ed.close() }
        }
        Text { x: 20; y: 16; text: "Menti a módosításokat?\n" + ed.path; color: Theme.text; font.family: Theme.font; font.pixelSize: 13 }
    }
}
