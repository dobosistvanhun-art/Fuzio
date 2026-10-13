// gomb: piros (fő), sötét (másodlagos), arany (kiemelt)
import QtQuick
Rectangle {
    id: b
    property string text: ""
    property string kind: "dark"          // dark | red | gold | ghost
    property bool active: false
    property int fs: 14
    signal clicked()
    implicitWidth: lbl.implicitWidth + 28; implicitHeight: 34
    radius: 4
    opacity: enabled ? 1 : 0.4
    border.width: kind === "ghost" ? 1 : 2
    border.color: kind === "red" ? "#ffcf3a" : kind === "gold" ? "#7a4b00" : active ? "#ffcf3a" : "#5a5f66"
    gradient: Gradient {
        GradientStop { position: 0; color: b.kind === "red" ? (ma.pressed ? "#7d1010" : "#d42a1c") : b.kind === "gold" ? "#ffd54a"
                                            : b.kind === "ghost" ? "transparent" : (b.active ? "#5a1414" : ma.containsMouse ? "#4a4f56" : "#34383e") }
        GradientStop { position: 1; color: b.kind === "red" ? (ma.pressed ? "#4a0808" : "#8e1410") : b.kind === "gold" ? "#d99a12"
                                            : b.kind === "ghost" ? "transparent" : (b.active ? "#2a0606" : "#1d2024") }
    }
    Text { id: lbl; anchors.centerIn: parent; text: b.text; font.family: "DejaVu Sans"; font.bold: true; font.pixelSize: b.fs
           color: b.kind === "gold" ? "#2a1800" : b.kind === "red" || b.active ? "#ffe9a8" : "#e8e8e8" }
    MouseArea { id: ma; anchors.fill: parent; hoverEnabled: true; enabled: b.enabled; cursorShape: Qt.PointingHandCursor; onClicked: b.clicked() }
}
