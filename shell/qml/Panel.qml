// FusionOS — Fusion Shell panel (QML változat, M6 mérőprototípus)
import QtQuick

Rectangle {
    id: panel
    color: "#11161c"
    property var st: ({ windows: [], clock: "", date: "", wifi: { state: "", ssid: "" } })
    property bool menuOpen: false
    property string stateJson: ""
    onStateJsonChanged: if (stateJson) st = JSON.parse(stateJson)
    function send(msg) { bridge.send(msg) }

    Rectangle { anchors.top: parent.top; width: parent.width; height: 1; color: "#2a3441" }

    Row {
        id: left
        anchors.left: parent.left; anchors.leftMargin: 6
        anchors.verticalCenter: parent.verticalCenter
        spacing: 4

        // Start gomb
        Rectangle {
            id: startBtn
            width: 44; height: 32; radius: 4
            color: panel.menuOpen ? "#243447" : (startMa.containsMouse ? "#1f2933" : "transparent")
            Rectangle {
                anchors.centerIn: parent; width: 22; height: 22; radius: 4; color: "#2f81f7"
                Text { anchors.centerIn: parent; text: "F"; color: "white"; font.family: "DejaVu Sans"; font.bold: true; font.pixelSize: 14 }
            }
            MouseArea { id: startMa; anchors.fill: parent; hoverEnabled: true; onClicked: panel.send(JSON.stringify({ cmd: "menu" })) }
        }

        Rectangle { width: 1; height: 24; color: "#2a3441"; anchors.verticalCenter: parent.verticalCenter }

        // ablaklista
        Repeater {
            model: panel.st.windows
            delegate: Rectangle {
                width: Math.min(220, Math.max(120, (panel.width - 420) / Math.max(1, panel.st.windows.length)))
                height: 32; radius: 4
                color: modelData.active ? "#243447" : (winMa.containsMouse ? "#1f2933" : "transparent")
                Rectangle {
                    anchors.bottom: parent.bottom; anchors.horizontalCenter: parent.horizontalCenter
                    width: parent.width - 16; height: 2; radius: 1
                    color: modelData.active ? "#2f81f7" : (modelData.hidden ? "transparent" : "#4b5563")
                }
                Text {
                    anchors.fill: parent; anchors.leftMargin: 10; anchors.rightMargin: 10
                    verticalAlignment: Text.AlignVCenter
                    text: modelData.title; elide: Text.ElideRight
                    color: modelData.hidden ? "#8b949e" : "#e6edf3"
                    font.family: "DejaVu Sans"; font.pixelSize: 13
                }
                MouseArea { id: winMa; anchors.fill: parent; hoverEnabled: true
                    onClicked: panel.send(JSON.stringify({ cmd: "toggle", id: modelData.id })) }
            }
        }
    }

    // jobb oldal: Wi-Fi, óra
    Row {
        anchors.right: parent.right; anchors.rightMargin: 10
        anchors.verticalCenter: parent.verticalCenter
        spacing: 14
        Text {
            anchors.verticalCenter: parent.verticalCenter
            text: panel.st.wifi.state === "connected" ? ("Wi-Fi  " + panel.st.wifi.ssid) : "Wi-Fi: nincs kapcsolat"
            color: panel.st.wifi.state === "connected" ? "#e6edf3" : "#8b949e"
            font.family: "DejaVu Sans"; font.pixelSize: 12
        }
        Column {
            anchors.verticalCenter: parent.verticalCenter
            Text { anchors.right: parent.right; text: panel.st.clock; color: "#e6edf3"; font.family: "DejaVu Sans"; font.pixelSize: 14; font.bold: true }
            Text { anchors.right: parent.right; text: panel.st.date; color: "#8b949e"; font.family: "DejaVu Sans"; font.pixelSize: 10 }
        }
    }
}
