// Fúzió — Fúzió Shell: panel (a képernyő alján)
// Start | tálca (nyitott ablakok) | eszközök, meghajtók, Wi-Fi, értesítések, óra
import QtQuick
import FusionUI

Rectangle {
    id: panel
    color: Theme.panel
    readonly property var deskWindows: shell.windows.filter(w => w.desktop === undefined || w.desktop < 0 || w.desktop === shell.desktop)
    Rectangle { anchors.top: parent.top; width: parent.width; height: 1; color: Theme.border }

    component TrayButton: Rectangle {
        id: tb
        property string tip: ""
        property bool on: false
        signal clicked()
        signal middle()
        signal wheel(int delta)
        default property alias content: inner.data
        height: 32; width: inner.childrenRect.width + 16; radius: Theme.radius
        anchors.verticalCenter: parent ? parent.verticalCenter : undefined
        color: on ? Theme.selected : (tma.containsMouse ? Theme.hover : "transparent")
        Item { id: inner; x: 8; width: childrenRect.width; height: parent.height }
        MouseArea { id: tma; anchors.fill: parent; hoverEnabled: true; acceptedButtons: Qt.LeftButton | Qt.MiddleButton
                    onClicked: (m) => m.button === Qt.MiddleButton ? tb.middle() : tb.clicked()
                    onWheel: (w) => tb.wheel(w.angleDelta.y) }
        ToolTipLite { text: tb.tip; show: tma.containsMouse }
    }

    Row {
        id: taskRow
        anchors.left: parent.left; anchors.leftMargin: 4
        anchors.verticalCenter: parent.verticalCenter
        spacing: 3

        // Start gomb
        Rectangle {
            width: 44; height: 34; radius: Theme.radius
            color: shell.menuOpen ? Theme.selected : (startMa.containsMouse ? Theme.hover : "transparent")
            Rectangle {
                anchors.centerIn: parent; width: 24; height: 24; radius: 4; color: Theme.accent
                Text { anchors.centerIn: parent; text: "F"; color: "white"; font.family: Theme.font; font.bold: true; font.pixelSize: 15 }
            }
            MouseArea { id: startMa; anchors.fill: parent; hoverEnabled: true; onClicked: shell.toggleMenu() }
            ToolTipLite { text: "Start (Super)"; show: startMa.containsMouse }
        }
        Rectangle { width: 1; height: 24; color: Theme.border; anchors.verticalCenter: parent.verticalCenter }

        // asztalok (0.0.54): 1 | 2 — kattintás / görgő: váltás; Ctrl+Alt+← / → (a Tab nem kell hozzá)
        Row {
            id: deskRow
            visible: shell.desktopCount > 1
            anchors.verticalCenter: parent.verticalCenter
            spacing: 2
            Repeater {
                model: shell.desktopCount
                delegate: Rectangle {
                    width: 26; height: 26; radius: Theme.radius
                    color: index === shell.desktop ? Theme.selected : (dma.containsMouse ? Theme.hover : "transparent")
                    border.color: index === shell.desktop ? Theme.accent : Theme.border; border.width: 1
                    Text { anchors.centerIn: parent; text: index + 1; color: index === shell.desktop ? Theme.text : Theme.dim
                           font.family: Theme.font; font.pixelSize: 12; font.bold: index === shell.desktop }
                    // pötty: van-e ablak ezen az asztalon
                    Rectangle { anchors.bottom: parent.bottom; anchors.bottomMargin: 3; anchors.horizontalCenter: parent.horizontalCenter
                                width: 4; height: 4; radius: 2; color: Theme.dim
                                visible: shell.windows.some(w => w.desktop === index) }
                    MouseArea { id: dma; anchors.fill: parent; hoverEnabled: true; onClicked: shell.setDesktop(index)
                                onWheel: (w) => shell.setDesktop(w.angleDelta.y > 0 ? Math.max(0, shell.desktop - 1)
                                                                                    : Math.min(shell.desktopCount - 1, shell.desktop + 1)) }
                    ToolTipLite { text: (index + 1) + ". asztal  (Ctrl+Alt+" + (index + 1) + ";  Ctrl+Alt+← / →)"; show: dma.containsMouse }
                }
            }
        }
        Rectangle { visible: deskRow.visible; width: 1; height: 24; color: Theme.border; anchors.verticalCenter: parent.verticalCenter }

        // tálca: az aktuális asztal ablakai (és a minden asztalon látszók)
        Repeater {
            model: panel.deskWindows
            delegate: Rectangle {
                width: Math.min(230, Math.max(110, (panel.width - trayRow.width - 140) / Math.max(1, panel.deskWindows.length) - 3))
                height: 34; radius: Theme.radius
                color: modelData.active && !modelData.hidden ? Theme.selected : (winMa.containsMouse ? Theme.hover : "transparent")
                Rectangle {
                    anchors.bottom: parent.bottom; anchors.horizontalCenter: parent.horizontalCenter
                    width: parent.width - 12; height: 2
                    color: modelData.active && !modelData.hidden ? Theme.accent : (modelData.hidden ? "transparent" : "#4b5563")
                }
                FIcon { id: wic; x: 8; anchors.verticalCenter: parent.verticalCenter; size: 18
                        name: modelData.iconFile ? modelData.iconFile : "app-" + modelData.icon
                        opacity: modelData.hidden ? 0.6 : 1 }
                Text {
                    anchors.left: wic.right; anchors.leftMargin: 7; anchors.right: parent.right; anchors.rightMargin: 8
                    anchors.verticalCenter: parent.verticalCenter
                    text: modelData.title; elide: Text.ElideRight
                    color: modelData.hidden ? Theme.dim : Theme.text
                    font.family: Theme.font; font.pixelSize: 13
                }
                MouseArea { id: winMa; anchors.fill: parent; hoverEnabled: true
                    acceptedButtons: Qt.LeftButton | Qt.MiddleButton | Qt.RightButton
                    onClicked: (m) => m.button === Qt.MiddleButton ? shell.closeWindow(modelData.id)
                                    : m.button === Qt.RightButton ? (shell.desktopCount > 1 && modelData.desktop >= 0
                                          ? shell.moveWindowToDesktop(modelData.id, (shell.desktop + 1) % shell.desktopCount) : null)
                                    : shell.toggleWindow(modelData.id) }
                ToolTipLite { text: modelData.title + "\n(középső gomb: bezárás" + (shell.desktopCount > 1 ? ";  jobb gomb: át a másik asztalra)" : ")")
                              show: winMa.containsMouse }
            }
        }
    }

    // jobb oldal
    Row {
        id: trayRow
        anchors.right: parent.right; anchors.rightMargin: 4
        anchors.verticalCenter: parent.verticalCenter
        spacing: 2

        // soros eszközök (lézer, 3D nyomtató): csatlakoztatva színesen, különben halványan
        Repeater {
            model: shell.devices
            TrayButton {
                tip: modelData.name + (modelData.present ? ": csatlakoztatva (" + modelData.dev + ")" : ": nincs csatlakoztatva")
                onClicked: shell.run("fusion-settings devices")
                FIcon { name: modelData.role; size: 18; y: 7; opacity: modelData.present ? 1 : 0.35 }
                Rectangle { x: 13; y: 20; width: 7; height: 7; radius: 3.5; visible: modelData.present; color: Theme.ok
                            border.color: Theme.panel; border.width: 1 }
            }
        }
        // cserélhető meghajtók
        TrayButton {
            visible: shell.media.length > 0
            tip: "Meghajtók: " + shell.media.map(m => m.name).join(", ")
            onClicked: shell.run("fusion-files " + (shell.media.length ? shell.media[0].path : ""))
            FIcon { name: "drive-usb"; size: 18; y: 7 }
        }
        Rectangle { width: 1; height: 24; color: Theme.border; anchors.verticalCenter: parent.verticalCenter }
        // Wi-Fi
        TrayButton {
            tip: shell.wifi.state === "connected" ? ("Wi-Fi: " + shell.wifi.ssid + (shell.wifi.ip ? "\n" + shell.wifi.ip : ""))
                                                  : ("Wi-Fi: " + (shell.wifi.state || "nincs"))
            onClicked: shell.run("fusion-settings wifi")
            Row {
                spacing: 7; anchors.verticalCenter: parent.verticalCenter
                FSignal { level: shell.wifi.state === "connected" ? shell.wifi.level : 0; anchors.verticalCenter: parent.verticalCenter
                          on: Theme.text }
                Text {
                    text: shell.wifi.state === "connected" ? shell.wifi.ssid : "nincs kapcsolat"
                    width: Math.min(implicitWidth, 150); elide: Text.ElideRight
                    color: shell.wifi.state === "connected" ? Theme.text : Theme.dim
                    font.family: Theme.font; font.pixelSize: 12; anchors.verticalCenter: parent.verticalCenter
                }
            }
        }
        // hang: kattintás → felugró, görgetés → hangerő
        TrayButton {
            on: shell.popup === "sound"
            tip: !shell.sound.ok ? "Hang: a hangkiszolgáló nem fut" : (!shell.sound.hasOutput ? "Hang: nincs kimenet"
                 : ("Hangerő: " + shell.sound.volume + "%" + (shell.sound.mute ? " (némítva)" : "") + (shell.sound.sinkDesc ? "\n" + shell.sound.sinkDesc : "")
                    + "\n(görgetés: hangerő, középső gomb: némítás)"))
            onClicked: shell.togglePopup("sound")
            onMiddle: shell.soundToggleMute()
            onWheel: (d) => shell.soundStep(d > 0 ? 5 : -5)
            FIcon { name: shell.sound.icon || "volume-mute"; size: 18; y: 7; opacity: shell.sound.ok && !shell.sound.mute ? 1 : 0.5 }
        }
        // értesítések
        TrayButton {
            on: shell.popup === "center"
            tip: shell.unread ? (shell.unread + " új értesítés") : "Értesítések"
            onClicked: shell.togglePopup("center")
            FIcon { name: "bell"; size: 18; y: 7; opacity: shell.notifications.length ? 1 : 0.6 }
            Rectangle {
                visible: shell.unread > 0
                x: 10; y: 3; height: 15; width: Math.max(15, cnt.implicitWidth + 8); radius: 7; color: Theme.accent
                Text { id: cnt; anchors.centerIn: parent; text: shell.unread > 9 ? "9+" : shell.unread; color: "white"
                       font.family: Theme.font; font.pixelSize: 10; font.bold: true }
            }
        }
        // óra
        TrayButton {
            on: shell.popup === "calendar"
            tip: shell.clock.long || ""
            onClicked: shell.togglePopup("calendar")
            Column {
                anchors.verticalCenter: parent.verticalCenter
                Text { anchors.right: parent.right; text: shell.clock.time || ""; color: Theme.text; font.family: Theme.font; font.pixelSize: 14; font.bold: true }
                Text { anchors.right: parent.right; text: shell.clock.date || ""; color: Theme.dim; font.family: Theme.font; font.pixelSize: 10 }
            }
        }
    }
}
