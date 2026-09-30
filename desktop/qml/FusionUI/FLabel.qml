import QtQuick
Text {
    property bool dim: false
    property bool bold: false
    color: dim ? Theme.dim : Theme.text
    font.family: Theme.font; font.pixelSize: Theme.fs; font.bold: bold
    elide: Text.ElideRight
    verticalAlignment: Text.AlignVCenter
}
