// Fúzió — képernyőkép: terület kijelölése a fagyasztott képen (fusion-screenshot terulet)
// egérrel húzva: a terület; Enter / dupla kattintás: a teljes képernyő; Esc: mégse
import QtQuick
import FusionUI

Item {
    id: root
    focus: true
    Keys.onEscapePressed: shot.cancel()
    Keys.onReturnPressed: shot.chosen(0, 0, 0, 0)
    Keys.onEnterPressed: shot.chosen(0, 0, 0, 0)
    property real x0: 0
    property real y0: 0
    property real x1: 0
    property real y1: 0
    property bool dragging: false
    readonly property real sx: Math.min(x0, x1)
    readonly property real sy: Math.min(y0, y1)
    readonly property real sw: Math.abs(x1 - x0)
    readonly property real sh: Math.abs(y1 - y0)

    Image { anchors.fill: parent; source: shotImage; fillMode: Image.Stretch; cache: false }
    // sötétítés a kijelölésen kívül (négy sáv)
    Rectangle { color: "#80000000"; x: 0; y: 0; width: parent.width; height: root.sy }
    Rectangle { color: "#80000000"; x: 0; y: root.sy + root.sh; width: parent.width; height: parent.height - root.sy - root.sh }
    Rectangle { color: "#80000000"; x: 0; y: root.sy; width: root.sx; height: root.sh }
    Rectangle { color: "#80000000"; x: root.sx + root.sw; y: root.sy; width: parent.width - root.sx - root.sw; height: root.sh }
    Rectangle { x: root.sx; y: root.sy; width: root.sw; height: root.sh; color: "transparent"
                border.color: Theme.accent; border.width: 2; visible: root.sw > 0 }
    Rectangle {
        visible: root.sw > 0
        x: Math.min(root.sx, parent.width - width - 4); y: root.sy > 30 ? root.sy - 28 : root.sy + root.sh + 4
        width: dim.implicitWidth + 16; height: 24; radius: 4; color: "#d0161b22"
        Text { id: dim; anchors.centerIn: parent; text: Math.round(root.sw) + " × " + Math.round(root.sh)
               color: "white"; font.family: Theme.font; font.pixelSize: 12 }
    }
    Rectangle {
        visible: !root.dragging && root.sw === 0
        anchors.horizontalCenter: parent.horizontalCenter; y: 40
        width: help.implicitWidth + 28; height: 36; radius: 6; color: "#e0161b22"; border.color: Theme.border
        Text { id: help; anchors.centerIn: parent; color: "white"; font.family: Theme.font; font.pixelSize: 14
               text: "Képernyőkép: jelölje ki a területet az egérrel  ·  Enter: teljes képernyő  ·  Esc: mégse" }
    }
    MouseArea {
        anchors.fill: parent
        cursorShape: Qt.CrossCursor
        onPressed: (m) => { root.x0 = root.x1 = m.x; root.y0 = root.y1 = m.y; root.dragging = true }
        onPositionChanged: (m) => { if (root.dragging) { root.x1 = m.x; root.y1 = m.y } }
        onReleased: { root.dragging = false; if (root.sw > 3 && root.sh > 3) shot.chosen(root.sx, root.sy, root.sw, root.sh) }
        onDoubleClicked: shot.chosen(0, 0, 0, 0)
    }
}
