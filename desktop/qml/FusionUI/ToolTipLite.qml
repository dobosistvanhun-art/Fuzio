// egyszerű buborék (késleltetve jelenik meg, a szülő fölött)
import QtQuick
import QtQuick.Controls
ToolTip {
    id: tt
    property bool show: false
    visible: show && text !== ""
    delay: 600
    contentItem: Text { text: tt.text; color: Theme.text; font.family: Theme.font; font.pixelSize: Theme.fsSmall }
    background: Rectangle { color: Theme.panel; border.color: Theme.border }
}
