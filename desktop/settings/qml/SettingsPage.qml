// egy beállítás-oldal kerete: cím, frissítés gomb, görgethető tartalom
import QtQuick
import QtQuick.Controls
import FusionUI

Item {
    id: page
    property string title: ""
    property string subtitle: ""
    property bool busy: false
    default property alias content: col.data
    signal refresh()
    Rectangle {
        id: head; width: parent.width; height: 60; color: Theme.bg
        Column {
            x: 24; anchors.verticalCenter: parent.verticalCenter
            Text { text: page.title; color: Theme.text; font.family: Theme.font; font.pixelSize: 18; font.bold: true }
            Text { visible: text !== ""; text: page.subtitle; color: Theme.dim; font.family: Theme.font; font.pixelSize: 12 }
        }
        Row {
            anchors.right: parent.right; anchors.rightMargin: 16; anchors.verticalCenter: parent.verticalCenter; spacing: 10
            BusyIndicator { running: page.busy; visible: page.busy; width: 26; height: 26 }
            FToolButton { icon: "refresh"; tip: "Frissítés"; onClicked: page.refresh() }
        }
        Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.border }
    }
    ScrollView {
        anchors.top: head.bottom; anchors.bottom: parent.bottom; width: parent.width
        contentWidth: availableWidth
        clip: true
        Column {
            id: col
            x: 24; width: page.width - 48; spacing: 18
            topPadding: 18; bottomPadding: 24
        }
    }
}
