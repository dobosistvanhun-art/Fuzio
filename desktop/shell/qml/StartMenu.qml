// FusionOS — Start menü: keresés, programok, kikapcsolás. Egyszerű és gyors.
import QtQuick
import FusionUI

Rectangle {
    id: menu
    color: Theme.bg
    border.color: Theme.border; border.width: 1
    focus: true
    property string filter: ""
    property int cur: 0
    property bool powerOpen: false
    property string confirm: ""      // "reboot" | "poweroff" | "logout"

    function reset() { search.text = ""; cur = 0; powerOpen = false; confirm = ""; search.forceActiveFocus() }
    function norm(s) { return (s || "").toLowerCase() }
    function shown() {
        var f = norm(filter)
        return shell.apps.filter(function (a) {
            if (f === "") return !a.search_only
            return norm(a.name).indexOf(f) >= 0 || norm(a.desc).indexOf(f) >= 0 || norm(a.keywords).indexOf(f) >= 0
        })
    }
    property var items: { filter; shell.apps; return shown() }
    onItemsChanged: cur = 0
    function launch(i) { if (i >= 0 && i < items.length) shell.launch(items[i].id) }

    // keresőmező
    Rectangle {
        id: box
        x: 14; y: 14; width: parent.width - 28; height: 38; radius: Theme.radius
        color: Theme.base; border.color: search.activeFocus ? Theme.accent : Theme.border
        FIcon { id: sic; name: "search"; size: 16; x: 11; anchors.verticalCenter: parent.verticalCenter; opacity: 0.8 }
        TextInput {
            id: search
            anchors.left: sic.right; anchors.leftMargin: 10; anchors.right: parent.right; anchors.rightMargin: 10
            anchors.verticalCenter: parent.verticalCenter
            color: Theme.text; font.family: Theme.font; font.pixelSize: 15
            selectByMouse: true
            onTextChanged: menu.filter = text
            Keys.onEscapePressed: shell.hideMenu()
            Keys.onReturnPressed: menu.launch(menu.cur)
            Keys.onEnterPressed: menu.launch(menu.cur)
            Keys.onDownPressed: menu.cur = Math.min(menu.items.length - 1, menu.cur + 1)
            Keys.onUpPressed: menu.cur = Math.max(0, menu.cur - 1)
            Text { anchors.verticalCenter: parent.verticalCenter; visible: !search.text; text: "Keresés a programok és beállítások között…"
                   color: Theme.dim; font.family: Theme.font; font.pixelSize: 14 }
        }
    }

    Text { x: 18; y: 64; text: menu.filter ? "Találatok" : "Programok"; color: Theme.dim
           font.family: Theme.font; font.pixelSize: 11; font.bold: true }

    ListView {
        id: list
        x: 8; y: 84; width: parent.width - 16; height: parent.height - y - foot.height - 6
        clip: true; spacing: 1
        model: menu.items
        currentIndex: menu.cur
        boundsBehavior: Flickable.StopAtBounds
        delegate: Rectangle {
            width: list.width; height: 48; radius: Theme.radius
            color: index === menu.cur ? Theme.selected : (ima.containsMouse ? Theme.hover : "transparent")
            FIcon { id: ico; x: 10; anchors.verticalCenter: parent.verticalCenter; name: modelData.iconFile || ("app-" + modelData.icon); size: 30
                    opacity: modelData.installed ? 1 : 0.5 }
            Column {
                anchors.left: ico.right; anchors.leftMargin: 12; anchors.right: parent.right; anchors.rightMargin: 10
                anchors.verticalCenter: parent.verticalCenter
                Text { width: parent.width; text: modelData.name; elide: Text.ElideRight
                       color: modelData.installed ? Theme.text : Theme.dim; font.family: Theme.font; font.pixelSize: 14 }
                Text { width: parent.width; text: modelData.desc; elide: Text.ElideRight
                       color: Theme.dim; font.family: Theme.font; font.pixelSize: 11 }
            }
            MouseArea { id: ima; anchors.fill: parent; hoverEnabled: true
                onEntered: menu.cur = index; onClicked: menu.launch(index) }
        }
        Text { anchors.centerIn: parent; visible: menu.items.length === 0; text: "Nincs találat"
               color: Theme.dim; font.family: Theme.font; font.pixelSize: 13 }
    }

    // lábléc: felhasználó, verzió, beállítások, kikapcsolás
    Rectangle {
        id: foot
        anchors.bottom: parent.bottom; anchors.left: parent.left; anchors.right: parent.right
        anchors.margins: 1
        height: menu.powerOpen ? 48 + pcol.height : 48
        color: Theme.panel
        Rectangle { width: parent.width; height: 1; color: Theme.border }

        Column {
            id: pcol
            visible: menu.powerOpen
            x: parent.width - width - 8; y: 8; width: 230
            spacing: 2
            Repeater {
                model: [["logout", "Kijelentkezés", "logout"], ["reboot", "Újraindítás", "restart"], ["poweroff", "Leállítás", "power"]]
                Rectangle {
                    width: pcol.width; height: 34; radius: Theme.radius
                    color: menu.confirm === modelData[0] ? "#3b1d1f" : (pma.containsMouse ? Theme.hover : "transparent")
                    FIcon { x: 10; anchors.verticalCenter: parent.verticalCenter; name: modelData[2]; size: 16 }
                    Text { x: 36; anchors.verticalCenter: parent.verticalCenter
                           text: menu.confirm === modelData[0] ? (modelData[1] + "? Kattintson újra") : modelData[1]
                           color: menu.confirm === modelData[0] ? Theme.danger : Theme.text; font.family: Theme.font; font.pixelSize: 13 }
                    MouseArea { id: pma; anchors.fill: parent; hoverEnabled: true
                        onClicked: menu.confirm === modelData[0] ? shell.power(modelData[0]) : menu.confirm = modelData[0] }
                }
            }
        }
        Item {
            anchors.bottom: parent.bottom; width: parent.width; height: 48
            Rectangle { x: 12; anchors.verticalCenter: parent.verticalCenter; width: 28; height: 28; radius: 14; color: Theme.selected
                Text { anchors.centerIn: parent; text: shell.user.substring(0, 1).toUpperCase(); color: Theme.text
                       font.family: Theme.font; font.bold: true; font.pixelSize: 13 } }
            Column {
                x: 48; anchors.verticalCenter: parent.verticalCenter
                Text { text: shell.user; color: Theme.text; font.family: Theme.font; font.pixelSize: 13 }
                Text { text: shell.version; color: Theme.dim; font.family: Theme.font; font.pixelSize: 10 }
            }
            Row {
                anchors.right: parent.right; anchors.rightMargin: 8; anchors.verticalCenter: parent.verticalCenter
                spacing: 2
                FToolButton { icon: "settings"; tip: "Beállítások"; onClicked: shell.run("fusion-settings") }
                FToolButton { icon: "power"; tip: "Kikapcsolás"; checked: menu.powerOpen
                              onClicked: { menu.powerOpen = !menu.powerOpen; menu.confirm = "" } }
            }
        }
    }
}
