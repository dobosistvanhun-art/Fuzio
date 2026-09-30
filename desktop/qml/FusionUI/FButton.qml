// gomb: FButton { text: "Mentés"; icon: "check"; primary: true; onClicked: … }
import QtQuick

Rectangle {
    id: b
    property string text: ""
    property string icon: ""
    property bool primary: false
    property bool danger: false
    property bool flat: false
    property bool checked: false
    property string tip: ""
    signal clicked()
    enabled: true
    implicitHeight: 30
    implicitWidth: Math.max(implicitHeight, row.implicitWidth + (text ? 24 : 12))
    radius: Theme.radius
    opacity: enabled ? 1 : 0.45
    color: primary ? (ma.pressed ? Theme.accentDim : (ma.containsMouse ? "#3b8cf8" : Theme.accent))
         : danger ? (ma.containsMouse ? "#b62324" : "#8e1519")
         : checked ? Theme.selected
         : (ma.pressed ? Theme.selected : (ma.containsMouse ? Theme.hover : (flat ? "transparent" : "#1b222c")))
    border.color: (primary || danger || flat) ? "transparent" : (activeFocus ? Theme.accent : Theme.border)
    border.width: 1
    activeFocusOnTab: !flat
    Keys.onReturnPressed: b.clicked()
    Keys.onSpacePressed: b.clicked()
    Row {
        id: row
        anchors.centerIn: parent
        spacing: 6
        FIcon { visible: b.icon !== ""; name: b.icon; size: 16; anchors.verticalCenter: parent.verticalCenter }
        Text {
            visible: b.text !== ""
            text: b.text; anchors.verticalCenter: parent.verticalCenter
            color: (b.primary || b.danger) ? "white" : Theme.text
            font.family: Theme.font; font.pixelSize: Theme.fs
        }
    }
    MouseArea { id: ma; anchors.fill: parent; hoverEnabled: true; enabled: b.enabled
        onClicked: b.clicked() }
    ToolTipLite { text: b.tip; show: ma.containsMouse && b.tip !== "" }
}
