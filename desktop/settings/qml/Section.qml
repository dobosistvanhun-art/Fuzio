// szakasz: cím + keretes tartalom
import QtQuick
import FusionUI
Column {
    property string title: ""
    default property alias content: box.data
    property alias boxColumn: box
    width: parent ? parent.width : 400
    spacing: 8
    Text { text: parent.title; color: Theme.dim; font.family: Theme.font; font.pixelSize: 12; font.bold: true; visible: text !== "" }
    Rectangle {
        width: parent.width; height: box.implicitHeight + 2; color: "#1b222c"; border.color: Theme.border; radius: Theme.radius
        Column { id: box; x: 1; y: 1; width: parent.width - 2 }
    }
}
