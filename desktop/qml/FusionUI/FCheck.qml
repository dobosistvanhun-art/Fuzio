import QtQuick
import QtQuick.Controls.Basic
CheckBox {
    id: c
    font.family: Theme.font; font.pixelSize: Theme.fs
    indicator: Rectangle {
        x: c.leftPadding; anchors.verticalCenter: parent.verticalCenter
        width: 16; height: 16; radius: 2
        color: c.checked ? Theme.accent : Theme.base
        border.color: c.checked ? Theme.accent : Theme.border
        FIcon { anchors.centerIn: parent; visible: c.checked; name: "check"; size: 12 }
    }
    contentItem: Text { leftPadding: c.indicator.width + 8; text: c.text; color: Theme.text
        font: c.font; verticalAlignment: Text.AlignVCenter }
}
