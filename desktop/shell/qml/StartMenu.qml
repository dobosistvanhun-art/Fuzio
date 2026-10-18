// Fúzió — Start menü: keresés, programok, kikapcsolás. Egyszerű és gyors.
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
    property string group: ""        // kiválasztott csoport: "gyakori" | "osszes" | csoport-azonosító
    property var ctx: null           // jobb gombos menü: az alkalmazás

    function reset() {
        search.text = ""; cur = 0; powerOpen = false; confirm = ""; ctx = null
        group = frequent().length ? "gyakori" : (shell.groups.length ? shell.groups[0].id : "osszes")
        search.forceActiveFocus()
    }
    function norm(s) { return (s || "").toLowerCase() }
    function frequent() {
        return shell.apps.filter(a => !a.search_only && a.launches > 0)
                         .sort((x, y) => y.launches - x.launches).slice(0, 8)
    }
    function groupName(id) { var g = shell.allGroups.find(x => x.id === id); return g ? g.name : id }
    // a bal oldali lista: Gyakori (ha van), a nem üres csoportok, Összes
    property var groupList: {
        shell.apps
        var l = []
        if (frequent().length) l.push({ id: "gyakori", name: "Gyakran használt", icon: "clock" })
        l = l.concat(shell.groups)
        l.push({ id: "osszes", name: "Összes program", icon: "grid" })
        return l
    }
    function shown() {
        var f = norm(filter)
        if (f !== "")
            return shell.apps.filter(a => norm(a.name).indexOf(f) >= 0 || norm(a.desc).indexOf(f) >= 0 || norm(a.keywords).indexOf(f) >= 0)
        if (group === "gyakori") return frequent()
        if (group === "osszes") return shell.apps.filter(a => !a.search_only).slice().sort((x, y) => x.name.localeCompare(y.name, "hu"))
        return shell.apps.filter(a => !a.search_only && a.group === group).slice().sort((x, y) => x.name.localeCompare(y.name, "hu"))
    }
    property var items: { filter; group; shell.apps; return shown() }
    onItemsChanged: cur = 0
    function launch(i) { if (i >= 0 && i < items.length) shell.launch(items[i].id) }
    function stepGroup(d) {
        var i = groupList.findIndex(g => g.id === group)
        group = groupList[Math.max(0, Math.min(groupList.length - 1, i + d))].id
    }

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
            FTextMenu {}
            onTextChanged: { menu.filter = text; menu.ctx = null }
            Keys.onEscapePressed: menu.ctx ? menu.ctx = null : shell.hideMenu()
            Keys.onReturnPressed: menu.launch(menu.cur)
            Keys.onEnterPressed: menu.launch(menu.cur)
            Keys.onDownPressed: menu.cur = Math.min(menu.items.length - 1, menu.cur + 1)
            Keys.onUpPressed: menu.cur = Math.max(0, menu.cur - 1)
            Keys.onPressed: (e) => {
                if (menu.filter !== "") return
                if (e.key === Qt.Key_PageDown || e.key === Qt.Key_Right && search.text === "") { menu.stepGroup(1); e.accepted = true }
                else if (e.key === Qt.Key_PageUp || e.key === Qt.Key_Left && search.text === "") { menu.stepGroup(-1); e.accepted = true }
            }
            Text { anchors.verticalCenter: parent.verticalCenter; visible: !search.text; text: "Keresés a programok és beállítások között…"
                   color: Theme.dim; font.family: Theme.font; font.pixelSize: 14 }
        }
    }

    // bal oldal: csoportok (keresés közben rejtve)
    Column {
        id: side
        visible: menu.filter === ""
        x: 8; y: 64; width: 196
        spacing: 1
        Repeater {
            model: menu.groupList
            Rectangle {
                width: side.width; height: 34; radius: Theme.radius
                color: modelData.id === menu.group ? Theme.selected : (gma.containsMouse ? Theme.hover : "transparent")
                Rectangle { visible: modelData.id === menu.group; x: 0; y: 8; width: 3; height: 18; radius: 1.5; color: Theme.accent }
                FIcon { x: 12; anchors.verticalCenter: parent.verticalCenter; name: modelData.icon; size: 16 }
                Text { x: 38; anchors.verticalCenter: parent.verticalCenter; width: parent.width - 70; elide: Text.ElideRight
                       text: modelData.name; color: Theme.text; font.family: Theme.font; font.pixelSize: 13
                       font.bold: modelData.id === menu.group }
                Text { visible: modelData.count !== undefined; anchors.right: parent.right; anchors.rightMargin: 10
                       anchors.verticalCenter: parent.verticalCenter; text: modelData.count || ""; color: Theme.dim
                       font.family: Theme.font; font.pixelSize: 11 }
                MouseArea { id: gma; anchors.fill: parent; hoverEnabled: true
                    onClicked: { menu.group = modelData.id; menu.ctx = null; search.forceActiveFocus() } }
            }
        }
    }
    Rectangle { visible: side.visible; x: side.x + side.width + 6; y: 64; width: 1; height: list.height + 20; color: Theme.border }

    Text { id: head; x: list.x + 10; y: 64
           text: menu.filter ? "Találatok" : (menu.group === "gyakori" ? "Gyakran használt" : menu.group === "osszes" ? "Összes program" : menu.groupName(menu.group))
           color: Theme.dim; font.family: Theme.font; font.pixelSize: 11; font.bold: true }

    ListView {
        id: list
        x: menu.filter === "" ? side.x + side.width + 14 : 8; y: 84
        width: parent.width - x - 8; height: parent.height - y - foot.height - 6
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
                Text { width: parent.width; elide: Text.ElideRight
                       text: menu.filter && !modelData.search_only ? menu.groupName(modelData.group) + "  ·  " + modelData.desc : modelData.desc
                       color: Theme.dim; font.family: Theme.font; font.pixelSize: 11 }
            }
            MouseArea { id: ima; anchors.fill: parent; hoverEnabled: true; acceptedButtons: Qt.LeftButton | Qt.RightButton
                onEntered: if (!menu.ctx) menu.cur = index
                onClicked: (m) => {
                    if (m.button === Qt.RightButton && !modelData.search_only) { menu.cur = index; menu.ctx = modelData }
                    else menu.launch(index)
                } }
        }
        Text { anchors.centerIn: parent; visible: menu.items.length === 0; text: menu.filter ? "Nincs találat" : "Üres csoport"
               color: Theme.dim; font.family: Theme.font; font.pixelSize: 13 }
    }

    // jobb gombos menü: melyik csoportban legyen a program
    Rectangle {
        id: ctxBox
        visible: !!menu.ctx
        width: 250; height: cc.implicitHeight + 16; radius: Theme.radius
        x: list.x + list.width - width - 10; y: Math.min(list.y + 10, menu.height - height - foot.height - 10)
        color: Theme.panel; border.color: Theme.accent
        z: 10
        Column {
            id: cc; x: 8; y: 8; width: parent.width - 16; spacing: 1
            Text { width: parent.width; text: menu.ctx ? menu.ctx.name + " — csoport:" : ""; elide: Text.ElideRight
                   color: Theme.dim; font.family: Theme.font; font.pixelSize: 11; font.bold: true; bottomPadding: 4 }
            Repeater {
                model: shell.allGroups
                Rectangle {
                    width: cc.width; height: 26; radius: Theme.radius
                    color: cma.containsMouse ? Theme.hover : "transparent"
                    property bool on: !!menu.ctx && menu.ctx.group === modelData.id
                    FIcon { x: 6; anchors.verticalCenter: parent.verticalCenter; name: parent.on ? "check" : modelData.icon; size: 14 }
                    Text { x: 28; anchors.verticalCenter: parent.verticalCenter
                           text: modelData.name + (menu.ctx && menu.ctx.autoGroup === modelData.id ? "  (automatikus)" : "")
                           color: parent.on ? Theme.accent : Theme.text; font.family: Theme.font; font.pixelSize: 12 }
                    MouseArea { id: cma; anchors.fill: parent; hoverEnabled: true
                        onClicked: { var id = menu.ctx.id; var g = modelData.id === menu.ctx.autoGroup ? "" : modelData.id
                                     menu.ctx = null; shell.setAppGroup(id, g); menu.group = modelData.id; search.forceActiveFocus() } }
                }
            }
        }
    }
    MouseArea { visible: !!menu.ctx; anchors.fill: parent; z: 9; onClicked: menu.ctx = null }

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
                Text { text: shell.version; color: Theme.text; font.family: Theme.font; font.pixelSize: 13; font.bold: true }
                Text { text: "felhasználó: " + shell.user; color: Theme.dim; font.family: Theme.font; font.pixelSize: 10 }
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
