// telefon: SMS-ek — vételi ajánlatok és kihívások
import QtQuick
import QtQuick.Controls

Rectangle {
    id: ph
    property var msgs: win.st.messages || []
    property bool mini: false
    width: 300; height: mini ? 64 : Math.min(520, 110 + list.contentHeight)
    radius: 28; color: "#0d0e10"; border.color: "#5a5f66"; border.width: 3
    Rectangle { anchors.horizontalCenter: parent.horizontalCenter; y: 12; width: 60; height: 6; radius: 3; color: "#2c2f34" }
    Rectangle {
        anchors.fill: parent; anchors.margins: 12; anchors.topMargin: ph.mini ? 22 : 26; anchors.bottomMargin: ph.mini ? 14 : 26; radius: 10
        gradient: Gradient { GradientStop { position: 0; color: "#1d3a4a" } GradientStop { position: 1; color: "#0f1e28" } }
        Text { x: 12; y: ph.mini ? 2 : 8; text: "ÜZENETEK (" + ph.msgs.length + ")"; color: "#9ad0ff"; font.pixelSize: 13; font.bold: true }
        Text { anchors.right: parent.right; anchors.rightMargin: 12; y: ph.mini ? 0 : 6; text: ph.mini ? "▲" : "▼"; color: "#9ad0ff"; font.pixelSize: 14 }
        MouseArea { width: parent.width; height: 28; y: ph.mini ? -8 : 0; onClicked: ph.mini = !ph.mini; cursorShape: Qt.PointingHandCursor }
        ListView {
            id: list; visible: !ph.mini; anchors.fill: parent; anchors.margins: 8; anchors.topMargin: 32; clip: true; spacing: 8
            model: ph.msgs
            delegate: Rectangle {
                width: ListView.view.width; height: col.height + 16; radius: 10; color: "#e8f2ff"
                Column {
                    id: col; x: 10; y: 8; width: parent.width - 20; spacing: 8
                    Text { width: parent.width; text: modelData.text; wrapMode: Text.Wrap; color: "#111"; font.pixelSize: 13 }
                    Row {
                        spacing: 6
                        Btn { height: 26; fs: 12; kind: "red"; text: modelData.kind === "offer" ? "ELADOM" : "ELFOGADOM"
                              onClicked: {
                                  var m = modelData, i = index
                                  if (m.kind === "offer") { game.acceptOffer(m.uid, m.price) }
                                  else { var r = game.challenge(m.rival, m.bet, false); game.dismissMessage(i); win.startRace(r) }
                              } }
                        Btn { height: 26; fs: 12; text: "NEM"; onClicked: game.dismissMessage(index) }
                    }
                }
            }
        }
    }
}
