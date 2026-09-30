// jelerősség oszlopokkal (Wi-Fi): FSignal { level: 0..4 }
import QtQuick
Row {
    property int level: 0
    property color on: Theme.text
    spacing: 2
    Repeater {
        model: 4
        Rectangle { width: 3; height: 4 + index * 3; anchors.bottom: parent.bottom
            color: index < level ? parent.on : "#3a4552" }
    }
    height: 13
}
