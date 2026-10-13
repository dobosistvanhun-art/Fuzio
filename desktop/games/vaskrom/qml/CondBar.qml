// állapotsáv (0–100 %)
import QtQuick
Rectangle {
    property int value: 100
    implicitWidth: 80; implicitHeight: 8; radius: 3; color: "#0d0e10"; border.color: "#3a3d42"
    Rectangle { x: 1; y: 1; height: parent.height - 2; radius: 2; width: Math.max(0, (parent.width - 2) * parent.value / 100)
                color: parent.value > 70 ? "#3fb950" : parent.value > 40 ? "#d29922" : "#e5534b" }
}
