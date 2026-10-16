// jobb gombos szövegmenü (Visszavonás, Kivágás, Másolás, Beillesztés, Törlés, Mindent kijelöl)
// Használat: a szövegmező gyerekeként —  TextArea { ... FTextMenu {} }   (az FTextField-ben beépítve van)
// A bal gombot nem fogja el (kijelölés, kurzor marad a mezőé); csak a jobb gombra nyit menüt.
import QtQuick
import QtQuick.Controls

MouseArea {
    id: root
    property Item target: parent
    // a jelszómezőből nem másolunk ki
    readonly property bool secret: target && target.echoMode !== undefined && target.echoMode !== TextInput.Normal
    readonly property bool ro: !target || target.readOnly === true
    property int selStart: 0
    property int selEnd: 0
    anchors.fill: parent
    acceptedButtons: Qt.RightButton
    cursorShape: Qt.IBeamCursor

    onPressed: (m) => {
        if (!target) return
        // a menü megnyitásakor a mező elveszítheti a kijelölést — megjegyezzük
        selStart = target.selectionStart; selEnd = target.selectionEnd
        if (selStart === selEnd && target.positionAt !== undefined) {
            var pos = target.positionAt(m.x, m.y)
            if (pos >= 0) target.cursorPosition = pos
        }
        target.forceActiveFocus()
        menu.popup(root, m.x, m.y)
    }

    function restore() {
        if (!target) return
        target.forceActiveFocus()
        if (selStart !== selEnd) target.select(selStart, selEnd)
    }
    function hasSel() { return selStart !== selEnd }

    Menu {
        id: menu
        modal: false
        onClosed: if (root.target) root.target.forceActiveFocus()
        background: Rectangle {
            implicitWidth: 220; color: Theme.bg
            border.color: Theme.border; radius: Theme.radius
        }
        component TI: MenuItem {
            id: ti
            property string keys: ""
            implicitHeight: 30
            contentItem: Item {
                implicitWidth: 200; implicitHeight: 20
                Text { anchors.verticalCenter: parent.verticalCenter; text: ti.text
                       color: ti.enabled ? Theme.text : Theme.dim; font.family: Theme.font; font.pixelSize: 13 }
                Text { anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; text: ti.keys
                       color: Theme.dim; font.family: Theme.font; font.pixelSize: 12 }
            }
            background: Rectangle { color: ti.highlighted && ti.enabled ? Theme.selected : "transparent"; radius: 3 }
        }
        TI { text: "Visszavonás"; keys: "Ctrl+Z"; enabled: !root.ro && root.target && root.target.canUndo
             onTriggered: { root.target.forceActiveFocus(); root.target.undo() } }
        MenuSeparator { contentItem: Rectangle { implicitHeight: 1; color: Theme.border } }
        TI { text: "Kivágás"; keys: "Ctrl+X"; enabled: !root.ro && !root.secret && root.hasSel()
             onTriggered: { root.restore(); root.target.cut() } }
        TI { text: "Másolás"; keys: "Ctrl+C"; enabled: !root.secret && root.hasSel()
             onTriggered: { root.restore(); root.target.copy() } }
        TI { text: "Beillesztés"; keys: "Ctrl+V"; enabled: !root.ro && root.target && root.target.canPaste
             onTriggered: { root.restore(); root.target.paste() } }
        TI { text: "Törlés"; keys: "Del"; enabled: !root.ro && root.hasSel()
             onTriggered: { root.target.forceActiveFocus(); root.target.remove(root.selStart, root.selEnd) } }
        MenuSeparator { contentItem: Rectangle { implicitHeight: 1; color: Theme.border } }
        TI { text: "Mindent kijelöl"; keys: "Ctrl+A"; enabled: root.target && root.target.length > 0
             onTriggered: { root.target.forceActiveFocus(); root.target.selectAll() } }
    }
}
