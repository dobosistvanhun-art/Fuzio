// FusionOS — Fusion Shell Start menü (QML változat, M6 mérőprototípus)
import QtQuick

Rectangle {
    id: menu
    color: "#161b22"
    border.color: "#2a3441"; border.width: 1
    property var apps: []
    property string version: ""
    property string filter: ""
    property int openCount: 0
    onOpenCountChanged: { search.text = ""; search.forceActiveFocus() }
    function send(msg) { bridge.send(msg) }
    function close() { bridge.send(JSON.stringify({ cmd: "closemenu" })) }
    function shown() {
        var f = filter.toLowerCase()
        return apps.filter(function (a) {
            return f === "" || a.name.toLowerCase().indexOf(f) >= 0 || a.desc.toLowerCase().indexOf(f) >= 0
        })
    }
    function launch(id) { send(JSON.stringify({ cmd: "launch", id: id })); close() }

    // keresés
    Rectangle {
        id: box
        x: 14; y: 14; width: parent.width - 28; height: 36; radius: 4
        color: "#0d1117"; border.color: search.activeFocus ? "#2f81f7" : "#2a3441"
        TextInput {
            id: search
            anchors.fill: parent; anchors.leftMargin: 10; anchors.rightMargin: 10
            verticalAlignment: TextInput.AlignVCenter
            color: "#e6edf3"; font.family: "DejaVu Sans"; font.pixelSize: 14
            onTextChanged: menu.filter = text
            Keys.onEscapePressed: menu.close()
            Keys.onReturnPressed: { var l = menu.shown(); if (l.length) menu.launch(l[0].id) }
            Text { anchors.verticalCenter: parent.verticalCenter; visible: !search.text; text: "Keresés a programok között…"
                   color: "#8b949e"; font.family: "DejaVu Sans"; font.pixelSize: 14 }
        }
    }

    Text { x: 16; y: 62; text: "Programok"; color: "#8b949e"; font.family: "DejaVu Sans"; font.pixelSize: 11; font.bold: true }

    Column {
        x: 8; y: 82; width: parent.width - 16
        spacing: 2
        Repeater {
            model: menu.filter, menu.shown()
            delegate: Rectangle {
                width: parent.width; height: 46; radius: 4
                color: itemMa.containsMouse ? "#1f2933" : "transparent"
                Rectangle {
                    id: ico; x: 8; anchors.verticalCenter: parent.verticalCenter
                    width: 30; height: 30; radius: 6; color: "#243447"
                    Text { anchors.centerIn: parent; text: modelData.name.substring(0, 2); color: "#2f81f7"
                           font.family: "DejaVu Sans"; font.bold: true; font.pixelSize: 12 }
                }
                Column {
                    anchors.left: ico.right; anchors.leftMargin: 12; anchors.verticalCenter: parent.verticalCenter
                    Text { text: modelData.name; color: "#e6edf3"; font.family: "DejaVu Sans"; font.pixelSize: 14 }
                    Text { text: modelData.desc; color: "#8b949e"; font.family: "DejaVu Sans"; font.pixelSize: 11 }
                }
                MouseArea { id: itemMa; anchors.fill: parent; hoverEnabled: true; onClicked: menu.launch(modelData.id) }
            }
        }
    }

    // lábléc
    Rectangle {
        anchors.bottom: parent.bottom; width: parent.width; height: 44; color: "#11161c"
        Rectangle { width: parent.width; height: 1; color: "#2a3441" }
        Text { x: 16; anchors.verticalCenter: parent.verticalCenter; text: "fusion"; color: "#e6edf3"; font.family: "DejaVu Sans"; font.pixelSize: 13 }
        Text { anchors.right: parent.right; anchors.rightMargin: 16; anchors.verticalCenter: parent.verticalCenter
               text: menu.version; color: "#8b949e"; font.family: "DejaVu Sans"; font.pixelSize: 11 }
    }
}
