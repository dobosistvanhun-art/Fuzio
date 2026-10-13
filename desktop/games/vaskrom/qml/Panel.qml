// sötét fém panel, csavarokkal
import QtQuick
Rectangle {
    id: p
    property string title: ""
    default property alias content: inner.data
    property alias inner: inner
    color: "#1b1d21"; radius: 6
    border.color: "#5b4632"; border.width: 2
    Rectangle { anchors.fill: parent; anchors.margins: 3; radius: 4; color: "transparent"; border.color: "#2c2f34" }
    Repeater { model: 4
        Rectangle { width: 7; height: 7; radius: 3.5; color: "#8a8f96"; border.color: "#3a3d42"
                    x: index % 2 ? p.width - 13 : 6; y: index < 2 ? 6 : p.height - 13 } }
    Text { id: tt; visible: p.title !== ""; x: 18; y: 10; text: p.title; color: "#ffcf3a"; font.family: "DejaVu Sans"
           font.bold: true; font.pixelSize: 15; font.letterSpacing: 1 }
    Item { id: inner; anchors.fill: parent; anchors.margins: 14; anchors.topMargin: p.title !== "" ? 36 : 14 }
}
