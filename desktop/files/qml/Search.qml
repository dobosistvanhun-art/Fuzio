// Fúzió — Fájlkezelő: keresés (Alt+F7) — név minta és/vagy szöveg a fájlokban
import QtQuick
import QtQuick.Controls
import FusionUI

FWindow {
    id: s
    property string root: "/"
    property var panel
    width: 760; height: 620
    visible: true
    title: "Keresés — " + root
    Component.onCompleted: { nameField.forceActiveFocus(); s.raise(); s.requestActivate() }
    onClosing: { files.stopSearch(); destroy() }
    Shortcut { sequence: "Esc"; onActivated: s.close() }
    function start() { files.startSearch(whereField.text, nameField.text, textField.text); list.currentIndex = 0 }
    function jump(i) {
        var p = files.searchState.results[i]
        if (!p) return
        var dir = p.substring(0, p.lastIndexOf("/")) || "/"
        panel.go(dir, p.split("/").pop()); panel.focusList()
        s.close()
    }
    Column {
        id: form
        x: 16; y: 14; width: parent.width - 32; spacing: 8
        Grid {
            columns: 2; columnSpacing: 10; rowSpacing: 8; verticalItemAlignment: Grid.AlignVCenter
            FLabel { text: "Hol:"; dim: true; width: 110 }
            FTextField { id: whereField; text: s.root; width: form.width - 120 }
            FLabel { text: "Fájlnév:"; dim: true }
            FTextField { id: nameField; width: form.width - 120; placeholderText: "pl. *.gcode  vagy  lézer (részlet)"
                         Keys.onReturnPressed: s.start() }
            FLabel { text: "Szöveg benne:"; dim: true }
            FTextField { id: textField; width: form.width - 120; placeholderText: "(nem kötelező)"; Keys.onReturnPressed: s.start() }
        }
        Row {
            spacing: 8
            FButton { text: "Keresés"; icon: "search"; primary: true; enabled: !files.searchState.running; onClicked: s.start() }
            FButton { text: "Leállítás"; enabled: files.searchState.running === true; onClicked: files.stopSearch() }
            FLabel { text: files.searchState.status || ""; dim: true; width: form.width - 260; height: 30 }
        }
    }
    Rectangle {
        anchors.top: form.bottom; anchors.topMargin: 10; anchors.bottom: parent.bottom; anchors.left: parent.left; anchors.right: parent.right
        anchors.margins: 12; color: Theme.base; border.color: Theme.border
        ListView {
            id: list
            anchors.fill: parent; anchors.margins: 1; clip: true
            model: files.searchState.results || []
            ScrollBar.vertical: ScrollBar {}
            keyNavigationEnabled: true
            delegate: Rectangle {
                width: list.width; height: 24
                color: index === list.currentIndex ? Theme.selected : (index % 2 ? Theme.alt : Theme.base)
                Text { x: 8; anchors.verticalCenter: parent.verticalCenter; width: parent.width - 16; elide: Text.ElideMiddle
                       text: modelData; color: Theme.text; font.family: Theme.font; font.pixelSize: 12 }
                MouseArea { anchors.fill: parent; onClicked: list.currentIndex = index; onDoubleClicked: s.jump(index) }
            }
            Keys.onReturnPressed: s.jump(currentIndex)
        }
    }
}
