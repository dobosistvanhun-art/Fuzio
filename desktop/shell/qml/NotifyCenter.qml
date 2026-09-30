// FusionOS — értesítésközpont (a panel harang-gombjára)
import QtQuick
import FusionUI

Rectangle {
    id: root
    color: Theme.bg
    border.color: Theme.border
    focus: true
    Keys.onEscapePressed: shell.togglePopup("center")

    Rectangle {
        id: head; width: parent.width; height: 44; color: Theme.panel
        Text { x: 14; anchors.verticalCenter: parent.verticalCenter; text: "Értesítések"; color: Theme.text
               font.family: Theme.font; font.pixelSize: 14; font.bold: true }
        FButton { anchors.right: parent.right; anchors.rightMargin: 8; anchors.verticalCenter: parent.verticalCenter
                  flat: true; text: "Összes törlése"; visible: shell.notifications.length > 0; onClicked: shell.clearAll() }
    }
    ListView {
        id: list
        anchors.top: head.bottom; anchors.bottom: parent.bottom; anchors.left: parent.left; anchors.right: parent.right
        anchors.margins: 6
        clip: true; spacing: 4
        model: shell.notifications
        delegate: Rectangle {
            width: list.width; height: Math.max(56, col.implicitHeight + 18)
            color: nma.containsMouse ? Theme.hover : "#1b222c"; radius: Theme.radius
            Column {
                id: col
                x: 12; y: 9; width: parent.width - 50; spacing: 2
                Text { width: parent.width; text: modelData.summary; color: Theme.text; font.family: Theme.font; font.pixelSize: 13
                       font.bold: true; elide: Text.ElideRight }
                Text { width: parent.width; visible: text !== ""; text: modelData.body; color: Theme.dim; font.family: Theme.font
                       font.pixelSize: 12; wrapMode: Text.Wrap; maximumLineCount: 3; elide: Text.ElideRight; textFormat: Text.PlainText }
                Text { text: (modelData.app ? modelData.app + " · " : "") + modelData.time; color: "#6e7681"; font.family: Theme.font; font.pixelSize: 10 }
            }
            MouseArea { id: nma; anchors.fill: parent; hoverEnabled: true
                onClicked: (modelData.hasDefault || modelData.local) ? shell.invoke(modelData.id, "default") : null }
            FToolButton { anchors.right: parent.right; anchors.top: parent.top; anchors.margins: 4; icon: "close"
                          implicitWidth: 24; implicitHeight: 24; tip: "Törlés"; onClicked: shell.dismiss(modelData.id) }
        }
        Column {
            anchors.centerIn: parent; visible: shell.notifications.length === 0; spacing: 8
            FIcon { anchors.horizontalCenter: parent.horizontalCenter; name: "bell"; size: 32; opacity: 0.4 }
            Text { text: "Nincs értesítés"; color: Theme.dim; font.family: Theme.font; font.pixelSize: 13 }
        }
    }
}
