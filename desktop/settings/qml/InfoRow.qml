// címke – érték sor (opcionális gombokkal a jobb szélen)
import QtQuick
import FusionUI
Rectangle {
    property string label: ""
    property string value: ""
    property color valueColor: Theme.text
    property string icon: ""
    property bool mono: false
    default property alias actions: act.data
    width: parent ? parent.width : 400; height: Math.max(40, vt.implicitHeight + 16)
    color: "transparent"
    Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: "#232c38" }
    FIcon { id: ic; visible: parent.icon !== ""; name: parent.icon; size: 18; x: 14; anchors.verticalCenter: parent.verticalCenter }
    Text { id: lt; x: 44; width: 180; anchors.verticalCenter: parent.verticalCenter; text: parent.label
           color: Theme.dim; font.family: Theme.font; font.pixelSize: 13; elide: Text.ElideRight }
    Text { id: vt; anchors.left: lt.right; anchors.leftMargin: 10; anchors.right: act.left; anchors.rightMargin: 10
           anchors.verticalCenter: parent.verticalCenter; text: parent.value; color: parent.valueColor; wrapMode: Text.Wrap
           font.family: parent.mono ? Theme.mono : Theme.font; font.pixelSize: parent.mono ? 12 : 13; textFormat: Text.PlainText }
    Row { id: act; anchors.right: parent.right; anchors.rightMargin: 10; anchors.verticalCenter: parent.verticalCenter; spacing: 6 }
}
