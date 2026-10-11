// FusionOS — Beállítások: főablak (bal oldalt az oldalak, jobbra a tartalom)
import QtQuick
import QtQuick.Controls
import FusionUI

FWindow {
    id: win
    width: 1100; height: 740
    visible: true
    title: appMode === "programs" ? "Programkezelő" : pages[cur].title
    property int cur: Math.max(0, pages.findIndex(p => p.id === startPage))
    property string param: startParam
    // külön ablak (fusion-settings --app programs): csak a Programkezelő és a Programbolt, oldalsáv nélkül, fülekkel
    readonly property bool single: appMode !== ""
    readonly property var pages: single ? allPages.filter(p => p.id === "programs" || p.id === "store") : allPages
    readonly property var allPages: [
        { id: "wifi", title: "Wi-Fi és hálózat", icon: "wifi", qml: "WifiPage.qml" },
        { id: "display", title: "Kijelző", icon: "display", qml: "DisplayPage.qml" },
        { id: "devices", title: "Eszközök", icon: "usb", qml: "DevicesPage.qml" },
        { id: "printer", title: "Nyomtató (Klipper)", icon: "printer", qml: "PrinterPage.qml" },
        { id: "drive", title: "Google Drive", icon: "cloud", qml: "DrivePage.qml" },
        { id: "sound", title: "Hang", icon: "volume", qml: "SoundPage.qml" },
        { id: "programs", title: "Programkezelő", icon: "package", qml: "ProgramsPage.qml" },
        { id: "store", title: "Programbolt", icon: "store", qml: "StorePage.qml" },
        { id: "desktop", title: "Asztal", icon: "desktop", qml: "DesktopPage.qml" },
        { id: "update", title: "Rendszerfrissítés", icon: "update", qml: "UpdatePage.qml" },
        { id: "backup", title: "Mentés", icon: "archive-in", qml: "BackupPage.qml" },
        { id: "report", title: "Hibajelentés", icon: "report", qml: "ReportPage.qml" },
        { id: "system", title: "Rendszer", icon: "chip", qml: "SystemPage.qml" }
    ]
    Connections {
        target: settings
        function onPageRequested(page, param) {
            var i = win.pages.findIndex(p => p.id === page)
            if (i < 0 && win.single) { settings.spawn("fusion-settings " + page); return }
            if (param) win.param = param
            if (i >= 0) win.cur = i
            win.raise(); win.requestActivate()
        }
    }
    Component.onCompleted: { win.raise(); win.requestActivate() }
    Shortcut { sequence: "Esc"; onActivated: win.close() }
    Shortcut { sequence: "Ctrl+Q"; onActivated: win.close() }

    // fülek a külön ablakban
    Rectangle {
        id: tabs
        visible: win.single
        width: parent.width; height: win.single ? 48 : 0; color: Theme.panel
        Row {
            x: 14; anchors.verticalCenter: parent.verticalCenter; spacing: 6
            Repeater {
                model: win.single ? win.pages : []
                FButton { text: modelData.title; icon: modelData.icon; flat: index !== win.cur; checked: index === win.cur
                          onClicked: win.cur = index }
            }
        }
        FButton { anchors.right: parent.right; anchors.rightMargin: 14; anchors.verticalCenter: parent.verticalCenter
                  text: "Beállítások"; icon: "settings"; flat: true; onClicked: settings.spawn("fusion-settings") }
        Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.border }
    }
    Rectangle {
        id: side
        visible: !win.single
        width: win.single ? 0 : 230; height: parent.height; color: Theme.panel
        Column {
            anchors.fill: parent; anchors.topMargin: 12; spacing: 2
            Text { x: 18; text: "Beállítások"; color: Theme.text; font.family: Theme.font; font.pixelSize: 17; font.bold: true; bottomPadding: 10 }
            Repeater {
                model: win.pages
                Rectangle {
                    x: 8; width: side.width - 16; height: 38; radius: Theme.radius
                    color: index === win.cur ? Theme.selected : (sma.containsMouse ? Theme.hover : "transparent")
                    Rectangle { visible: index === win.cur; width: 3; height: 20; anchors.verticalCenter: parent.verticalCenter; color: Theme.accent }
                    FIcon { x: 14; anchors.verticalCenter: parent.verticalCenter; name: modelData.icon; size: 18 }
                    Text { x: 44; anchors.verticalCenter: parent.verticalCenter; text: modelData.title; color: Theme.text
                           font.family: Theme.font; font.pixelSize: 13 }
                    MouseArea { id: sma; anchors.fill: parent; hoverEnabled: true; onClicked: win.cur = index }
                }
            }
        }
        Text { anchors.bottom: parent.bottom; anchors.bottomMargin: 12; x: 18; text: fusionSys.version(); color: Theme.dim
               font.family: Theme.font; font.pixelSize: 11 }
    }
    Rectangle { visible: !win.single; x: side.width; width: 1; height: parent.height; color: Theme.border }
    Loader {
        id: pageLoader
        x: win.single ? 0 : side.width + 1; y: tabs.height; width: parent.width - x; height: parent.height - y
        source: win.pages[win.cur].qml
    }
}
