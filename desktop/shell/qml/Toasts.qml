// FusionOS — értesítés-buborékok (jobb alsó sarok, a panel fölött)
import QtQuick
import FusionUI

Rectangle {
    id: root
    color: "transparent"
    implicitHeight: col.implicitHeight
    Column {
        id: col
        width: parent.width
        spacing: 8
        Repeater {
            model: shell.toasts
            delegate: Rectangle {
                id: toastItem
                width: col.width
                height: Math.max(64, body.implicitHeight + 24)
                color: Theme.bg
                border.color: modelData.urgency >= 2 ? Theme.danger : Theme.border
                Rectangle { width: 3; height: parent.height; color: modelData.urgency >= 2 ? Theme.danger : Theme.accent }
                FIcon { id: ic; x: 14; y: 14; size: 28; name: "app-" + modelData.tile }
                Column {
                    id: body
                    anchors.left: ic.right; anchors.leftMargin: 12; anchors.right: closeBtn.left; anchors.rightMargin: 6
                    y: 12; spacing: 3
                    Text { width: parent.width; text: modelData.summary; color: Theme.text; font.family: Theme.font
                           font.pixelSize: 13; font.bold: true; wrapMode: Text.Wrap; maximumLineCount: 2; elide: Text.ElideRight }
                    Text { width: parent.width; visible: text !== ""; text: modelData.body; color: Theme.dim; font.family: Theme.font
                           font.pixelSize: 12; wrapMode: Text.Wrap; maximumLineCount: 4; elide: Text.ElideRight; textFormat: Text.PlainText }
                    Text { text: (modelData.app && modelData.app !== "FusionOS" ? modelData.app + " · " : "") + modelData.time
                           color: "#6e7681"; font.family: Theme.font; font.pixelSize: 10 }
                    Row {
                        visible: modelData.actions.length > 0; spacing: 6; topPadding: 4
                        Repeater { model: modelData.actions
                            FButton { text: modelData.label; implicitHeight: 26; onClicked: shell.invoke(toastItem.nid, modelData.key) } }
                    }
                }
                property int nid: modelData.id
                MouseArea { anchors.fill: parent; z: -1; onClicked: shell.invoke(modelData.id, "default") }
                FToolButton { id: closeBtn; icon: "close"; anchors.right: parent.right; anchors.top: parent.top; anchors.margins: 4
                              implicitWidth: 24; implicitHeight: 24; onClicked: shell.dismissToast(modelData.id) }
            }
        }
    }
}
