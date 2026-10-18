// Fúzió — vágólap-előzmények (Ctrl+Alt+V, 0.0.55): az utolsó másolások; kattintás / Enter → újra a vágólapra,
// utána Ctrl+V-vel beilleszthető. Csak a memóriában tárolja (kijelentkezéskor törlődik), fájlba nem ír.
import QtQuick
import QtQuick.Controls
import FusionUI

Rectangle {
    id: ch
    color: Theme.bg
    border.color: Theme.border
    focus: true
    readonly property var items: shell ? shell.clips : []
    Keys.onEscapePressed: shell.togglePopup("clip")
    Keys.onReturnPressed: if (items.length) shell.pickClip(lv.currentIndex)
    Keys.onEnterPressed: if (items.length) shell.pickClip(lv.currentIndex)
    Keys.onUpPressed: lv.decrementCurrentIndex()
    Keys.onDownPressed: lv.incrementCurrentIndex()
    Keys.onDeletePressed: if (items.length) shell.dropClip(lv.currentIndex)
    onVisibleChanged: if (visible) { lv.currentIndex = 0; ch.forceActiveFocus() }

    Row {
        id: head
        x: 16; y: 12; width: parent.width - 32; height: 30
        Text { text: "Vágólap-előzmények"; color: Theme.text; font.family: Theme.font; font.pixelSize: 15; font.bold: true
               width: parent.width - clr.width; anchors.verticalCenter: parent.verticalCenter }
        FButton { id: clr; text: "Mind törlése"; flat: true; visible: ch.items.length > 0; onClicked: shell.clearClips() }
    }
    Text {
        id: hint
        x: 16; anchors.top: head.bottom; anchors.topMargin: 2; width: parent.width - 32; wrapMode: Text.Wrap
        text: "Kattintás vagy Enter: újra a vágólapra, utána Ctrl+V.  Del: törlés a listából.  Csak a memóriában tárolódik."
        color: Theme.dim; font.family: Theme.font; font.pixelSize: 11
    }
    ListView {
        id: lv
        anchors.top: hint.bottom; anchors.topMargin: 8; anchors.bottom: parent.bottom; anchors.bottomMargin: 10
        x: 8; width: parent.width - 16
        clip: true; spacing: 2
        model: ch.items
        highlightMoveDuration: 0
        ScrollBar.vertical: ScrollBar {}
        delegate: Rectangle {
            width: lv.width - 10; height: 46; radius: Theme.radius
            color: index === lv.currentIndex ? Theme.selected : (ma.containsMouse ? Theme.hover : "transparent")
            Text { x: 10; y: 6; width: parent.width - 20; text: modelData.short; elide: Text.ElideRight
                   color: Theme.text; font.family: Theme.font; font.pixelSize: 13 }
            Text { x: 10; y: 26; text: (modelData.lines > 1 ? modelData.lines + " sor · " : "") + modelData.chars + " karakter"
                   color: Theme.dim; font.family: Theme.font; font.pixelSize: 10 }
            MouseArea { id: ma; anchors.fill: parent; hoverEnabled: true
                        onEntered: lv.currentIndex = index; onClicked: shell.pickClip(index) }
        }
        Text { anchors.centerIn: parent; visible: ch.items.length === 0; color: Theme.dim; font.family: Theme.font; font.pixelSize: 13
               text: "Még nincs másolás.\nAmit kimásol (Ctrl+C), itt megjelenik."; horizontalAlignment: Text.AlignHCenter }
    }
}
