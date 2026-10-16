import QtQuick
import QtQuick.Controls

TextField {
    id: f
    color: Theme.text
    placeholderTextColor: Theme.dim
    selectionColor: Theme.accent
    selectedTextColor: "white"
    font.family: Theme.font; font.pixelSize: Theme.fs
    implicitHeight: 30
    leftPadding: 8; rightPadding: 8
    verticalAlignment: TextInput.AlignVCenter
    background: Rectangle {
        color: Theme.base; radius: Theme.radius
        border.color: f.activeFocus ? Theme.accent : Theme.border
    }
    FTextMenu {}
}
