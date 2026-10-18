// Fúzió — Fájlkezelő: megtekintés (F3) — szöveg, kép, archívum tartalma, bináris (hexa)
import QtQuick
import QtQuick.Controls
import FusionUI

FWindow {
    id: v
    property string path: ""
    property var info: ({})
    property bool fit: true
    width: 1000; height: 760
    visible: true
    title: "Megtekintés — " + (info.name || "")
    Component.onCompleted: { info = files.readFile(path); if (info.kind !== "image") body.forceActiveFocus(); v.raise(); v.requestActivate() }
    onClosing: destroy()

    Shortcut { sequences: ["Esc", "F3", "F10"]; onActivated: v.close() }
    Shortcut { sequence: "F4"; enabled: v.info.kind === "text"; onActivated: { win.openEditor(v.path); v.close() } }
    Shortcut { sequence: "Ctrl+F"; enabled: v.info.kind !== "image"; onActivated: { findField.visible = true; findField.forceActiveFocus() } }

    header: Rectangle {
        height: 38; color: Theme.panel
        Row {
            x: 10; anchors.verticalCenter: parent.verticalCenter; spacing: 10
            FIcon { name: v.info.kind === "image" ? "file-image" : v.info.kind === "archive" ? "file-archive" : "file-text"; size: 18; anchors.verticalCenter: parent.verticalCenter }
            Text { text: v.path; color: Theme.text; font.family: Theme.font; font.pixelSize: 13; anchors.verticalCenter: parent.verticalCenter
                   width: Math.min(implicitWidth, v.width - 520); elide: Text.ElideMiddle }
            Text { text: (v.info.info || "") + (v.info.truncated ? " · csak az eleje látszik" : "") + (v.info.binary ? " · hexa nézet" : "")
                   color: Theme.dim; font.family: Theme.font; font.pixelSize: 11; anchors.verticalCenter: parent.verticalCenter }
        }
        Row {
            anchors.right: parent.right; anchors.rightMargin: 8; anchors.verticalCenter: parent.verticalCenter; spacing: 6
            FTextField { id: findField; visible: false; width: 200; placeholderText: "Keresés (Enter: következő)"
                         Keys.onReturnPressed: v.findNext(text); Keys.onEscapePressed: { visible = false; body.forceActiveFocus() } }
            FButton { visible: v.info.kind === "image"; text: v.fit ? "1:1" : "Ablakhoz"; onClicked: v.fit = !v.fit }
            FButton { visible: v.info.kind === "text"; text: "Szerkesztés (F4)"; icon: "edit"; onClicked: { win.openEditor(v.path); v.close() } }
            FButton { visible: v.info.kind === "archive"; text: "Kicsomagolás a másik panelbe"; icon: "archive-out"
                      onClicked: { files.extract([v.path], win.other.model.path, "all"); v.close() } }
            FButton { text: "Bezárás"; onClicked: v.close() }
        }
    }
    function findNext(t) {
        if (!t) return
        var s = body.text.toLowerCase(), i = s.indexOf(t.toLowerCase(), body.cursorPosition + 1)
        if (i < 0) i = s.indexOf(t.toLowerCase())
        if (i >= 0) { body.select(i, i + t.length); body.cursorPosition = i + t.length }
    }

    Text { anchors.centerIn: parent; visible: !!v.info.error; text: v.info.error || ""; color: Theme.danger; font.family: Theme.font }

    Flickable {
        id: imgView
        visible: v.info.kind === "image"
        anchors.fill: parent; clip: true
        contentWidth: v.fit ? width : Math.max(width, img.implicitWidth); contentHeight: v.fit ? height : Math.max(height, img.implicitHeight)
        ScrollBar.vertical: ScrollBar {}
        ScrollBar.horizontal: ScrollBar {}
        Rectangle { anchors.fill: parent; color: "#0b0f14" }
        Image {
            id: img
            anchors.centerIn: parent
            width: v.fit ? Math.min(parent.width - 20, implicitWidth) : implicitWidth
            height: v.fit ? Math.min(parent.height - 20, implicitHeight) : implicitHeight
            fillMode: Image.PreserveAspectFit
            source: v.info.kind === "image" ? files.imageUrl(v.path) : ""
            asynchronous: true
        }
        Text { anchors.bottom: parent.bottom; anchors.right: parent.right; anchors.margins: 8
               text: img.status === Image.Ready ? img.implicitWidth + " × " + img.implicitHeight + " px" : (img.status === Image.Error ? "a kép nem nyitható meg" : "")
               color: Theme.dim; font.family: Theme.font; font.pixelSize: 11 }
    }
    ScrollView {
        visible: v.info.kind !== "image" && !v.info.error
        anchors.fill: parent
        TextArea {
            id: body
            readOnly: true
            text: v.info.text || ""
            color: Theme.text; selectionColor: Theme.accent; selectedTextColor: "white"
            font.family: Theme.mono; font.pixelSize: 13
            wrapMode: v.info.binary || v.info.kind === "archive" ? TextEdit.NoWrap : TextEdit.WrapAnywhere
            background: Rectangle { color: Theme.base }
            textFormat: TextEdit.PlainText
            selectByMouse: true
            persistentSelection: true
            FTextMenu {}
        }
    }
}
