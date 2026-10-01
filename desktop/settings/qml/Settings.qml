// FusionOS — Beállítások: főablak (bal oldalt az oldalak, jobbra a tartalom)
import QtQuick
import QtQuick.Controls
import FusionUI

FWindow {
    id: win
    width: 1100; height: 740
    visible: true
    title: pages[cur].title
    property int cur: Math.max(0, pages.findIndex(p => p.id === startPage))
    property string param: startParam
    readonly property var pages: [
        { id: "wifi", title: "Wi-Fi és hálózat", icon: "wifi", qml: "WifiPage.qml" },
        { id: "display", title: "Kijelző", icon: "display", qml: "DisplayPage.qml" },
        { id: "devices", title: "Eszközök", icon: "usb", qml: "DevicesPage.qml" },
        { id: "printer", title: "Nyomtató (Klipper)", icon: "printer", qml: "PrinterPage.qml" },
        { id: "sound", title: "Hang", icon: "volume", qml: "SoundPage.qml" },
        { id: "programs", title: "Programkezelő", icon: "package", qml: "ProgramsPage.qml" },
        { id: "store", title: "Programbolt", icon: "store", qml: "StorePage.qml" },
        { id: "desktop", title: "Asztal", icon: "desktop", qml: "DesktopPage.qml" },
        { id: "system", title: "Rendszer", icon: "chip", qml: "SystemPage.qml" }
    ]
    Connections {
        target: settings
        function onPageRequested(page, param) {
            var i = win.pages.findIndex(p => p.id === page)
            if (param) win.param = param
            if (i >= 0) win.cur = i
            win.raise(); win.requestActivate()
        }
    }
    Component.onCompleted: { win.raise(); win.requestActivate() }
    Shortcut { sequence: "Esc"; onActivated: win.close() }
    Shortcut { sequence: "Ctrl+Q"; onActivated: win.close() }

    Rectangle {
        id: side
        width: 230; height: parent.height; color: Theme.panel
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
    Rectangle { x: side.width; width: 1; height: parent.height; color: Theme.border }
    Loader {
        id: pageLoader
        x: side.width + 1; width: parent.width - x; height: parent.height
        source: win.pages[win.cur].qml
    }
}
