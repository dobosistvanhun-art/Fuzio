// FusionOS — Lézer állapot (M8d): a szerep állapota, a rögzítés, melyik program melyik COM-porton éri el,
// a program indítása — minden adat a Fusion API-ból (fusion.devices, fusion.programs)
import QtQuick
import QtQuick.Controls
import FusionUI

FWindow {
    id: win
    width: 560; height: 340
    minimumWidth: 460; minimumHeight: 320
    visible: true
    title: st.name || "Eszköz"
    readonly property var st: laser.state
    property string msg: ""
    property bool msgErr: false

    Component.onCompleted: { raise(); requestActivate() }
    Shortcut { sequence: "Esc"; onActivated: win.close() }
    Shortcut { sequence: "F5"; onActivated: laser.refresh() }
    Connections {
        target: laser
        function onMessage(text, isErr) {
            if (text === "__raise__") { win.show(); win.raise(); win.requestActivate(); return }
            win.msg = text; win.msgErr = isErr; msgTimer.restart()
        }
    }
    Timer { id: msgTimer; interval: 6000; onTriggered: win.msg = "" }

    Column {
        anchors.fill: parent; anchors.margins: 20
        spacing: 14

        // fejléc: a szerep és az állapota
        Row {
            spacing: 14
            FIcon { name: st.role === "printer" ? "printer" : "laser"; size: 40; anchors.verticalCenter: parent.verticalCenter }
            Column {
                anchors.verticalCenter: parent.verticalCenter; spacing: 4
                FLabel { text: st.name || ""; bold: true; font.pixelSize: 18 }
                Row {
                    spacing: 8
                    Rectangle { width: 11; height: 11; radius: 5.5; anchors.verticalCenter: parent.verticalCenter
                                color: !st.known ? Theme.danger : (st.present ? Theme.ok : "#4b5563") }
                    FLabel { text: !st.known ? "ismeretlen szerep: " + st.role
                                   : st.present ? "Csatlakoztatva — " + st.dev + "  (/dev/fusion/" + st.role + ")"
                                   : "Nincs csatlakoztatva"
                             color: st.present ? Theme.ok : Theme.dim }
                }
            }
        }

        Rectangle { width: parent.width; height: 1; color: "#243040" }

        Row {
            spacing: 8; visible: !!st.known
            FLabel { width: 110; text: "Azonosítás"; dim: true }
            FLabel { width: win.width - 170; text: st.keyText || ""; wrapMode: Text.Wrap; elide: Text.ElideNone }
        }

        FLabel { visible: !!st.known; text: "WINDOWS-PROGRAMOK EZEN A SZEREPEN"; dim: true; font.pixelSize: 11; font.bold: true }
        FLabel {
            visible: !!st.known && (st.programs || []).length === 0
            width: parent.width; wrapMode: Text.Wrap; elide: Text.ElideNone; dim: true
            text: "Egy program sem éri el ezt az eszközt. Programkezelő → a program → Eszközök"
                  + (st.comSuggested ? " (javasolt port: " + st.comSuggested + ")" : "") + "."
        }
        Repeater {
            model: st.programs || []
            Row {
                spacing: 10
                FLabel { width: 70; text: modelData.com; bold: true; anchors.verticalCenter: parent.verticalCenter }
                FLabel { width: 200; text: modelData.name || modelData.id; anchors.verticalCenter: parent.verticalCenter }
                FButton { text: "Indítás"; icon: "app"; primary: st.present; enabled: modelData.installed
                          tip: st.present ? "" : "Az eszköz nincs csatlakoztatva — a program elindul, de nem éri el"
                          onClicked: laser.launch(modelData.id) }
            }
        }

        Item { width: 1; height: 4 }
        Row {
            spacing: 10
            FButton { text: "Eszközök beállítása"; icon: "usb"; onClicked: laser.openSettings() }
            FButton { text: "Programkezelő"; icon: "package"; flat: true; onClicked: laser.openPrograms() }
        }
    }

    // üzenetsáv
    Rectangle {
        visible: win.msg !== ""
        anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: parent.bottom
        height: 34; color: win.msgErr ? "#3d1d20" : "#1d2d22"
        FLabel { anchors.fill: parent; anchors.leftMargin: 14; text: win.msg; color: win.msgErr ? Theme.danger : Theme.ok }
    }
}
