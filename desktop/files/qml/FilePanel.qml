// Fúzió — Fájlkezelő: egy panel (meghajtó, útvonal, oszlopfejléc, lista, állapotsor)
import QtQuick
import QtQuick.Controls
import FusionUI

Rectangle {
    id: panel
    property var model
    property string side: "left"
    property bool active: false
    property alias list: list
    property int cur: list.currentIndex
    property var vol: ({ name: "", icon: "drive" })
    property string typeAhead: ""
    signal activated()
    signal openRow(int row)
    signal request(string action)          // "view", "edit", "copy", "move", "mkdir", "delete", "rename", "drive", "menu"
    color: Theme.base
    border.color: active ? Theme.accentDim : Theme.border

    function focusList() { list.forceActiveFocus() }
    function selection() { return model.selection(list.currentIndex) }
    function current() { return model.item(list.currentIndex) }
    function go(path, select) {
        var i = model.load(path, select || "")
        if (i >= 0) { list.currentIndex = i; list.positionViewAtIndex(i, ListView.Contain) }
        vol = files.volumeOf(model.path)
    }
    function setCur(i) {
        if (i < 0 || i >= list.count) return
        list.currentIndex = i
        list.positionViewAtIndex(i, ListView.Contain)
    }
    onCurChanged: model.current = model.item(cur).name || ""
    Connections {
        target: panel.model
        function onReloaded(i) { list.currentIndex = Math.min(i, list.count - 1) }
        function onPathChanged() { panel.vol = files.volumeOf(panel.model.path) }
    }

    // --- fejléc: meghajtó + szabad hely + útvonal ---
    Rectangle {
        id: head
        width: parent.width; height: 34; color: panel.active ? "#16202c" : Theme.panel
        Row {
            x: 4; anchors.verticalCenter: parent.verticalCenter; spacing: 6
            FButton {
                id: driveBtn
                icon: panel.vol.icon || "drive"; text: panel.vol.name || ""
                implicitHeight: 26; flat: true; tip: "Meghajtó / hely (" + (panel.side === "left" ? "Alt+F1" : "Alt+F2") + ")"
                onClicked: { panel.activated(); panel.request("drive") }
            }
            Text { anchors.verticalCenter: parent.verticalCenter; text: panel.model.free; color: Theme.dim
                   font.family: Theme.font; font.pixelSize: 11 }
        }
    }
    Rectangle {
        id: pathBar
        anchors.top: head.bottom; width: parent.width; height: 28; color: panel.active ? Theme.selected : "#1b222c"
        Text {
            id: pathText
            visible: !pathEdit.visible
            anchors.fill: parent; anchors.leftMargin: 8; anchors.rightMargin: 8
            verticalAlignment: Text.AlignVCenter; elide: Text.ElideMiddle
            text: panel.model.path; color: panel.active ? Theme.text : Theme.dim
            font.family: Theme.mono; font.pixelSize: 12
            MouseArea { anchors.fill: parent; onClicked: { panel.activated(); pathEdit.text = panel.model.path; pathEdit.visible = true; pathEdit.forceActiveFocus(); pathEdit.selectAll() } }
        }
        FTextField {
            id: pathEdit
            visible: false; anchors.fill: parent; anchors.margins: 1
            font.family: Theme.mono; font.pixelSize: 12
            Keys.onReturnPressed: { visible = false; panel.go(text); panel.focusList() }
            Keys.onEnterPressed: { visible = false; panel.go(text); panel.focusList() }
            Keys.onEscapePressed: { visible = false; panel.focusList() }
            onActiveFocusChanged: if (!activeFocus) visible = false
        }
    }
    // --- lomtár sáv: a lomtár mappájában ---
    Rectangle {
        id: trashBar
        anchors.top: pathBar.bottom; width: parent.width; height: panel.model.isTrash ? 34 : 0; visible: panel.model.isTrash
        color: "#2a2216"
        property var info: panel.model.isTrash && panel.model.count > 0 ? files.trashInfo(panel.model.path + "/" + (panel.model.item(panel.cur).name || "")) : ({})
        FIcon { x: 8; anchors.verticalCenter: parent.verticalCenter; name: "trash"; size: 16 }
        Text { x: 30; anchors.verticalCenter: parent.verticalCenter; width: parent.width - 30 - tbRow.width - 16; elide: Text.ElideMiddle
               text: trashBar.info && trashBar.info.orig ? "Eredeti hely: " + trashBar.info.orig + "  ·  " + trashBar.info.date : "Lomtár — Del: végleges törlés"
               color: Theme.text; font.family: Theme.font; font.pixelSize: 11 }
        Row {
            id: tbRow; anchors.right: parent.right; anchors.rightMargin: 6; anchors.verticalCenter: parent.verticalCenter; spacing: 4
            FButton { implicitHeight: 24; text: "Visszaállítás"; onClicked: { panel.activated(); panel.request("restore") } }
            FButton { implicitHeight: 24; text: "Ürítés"; danger: true; onClicked: { panel.activated(); panel.request("emptytrash") } }
        }
    }
    // --- oszlopfejléc (kattintásra rendez) ---
    Rectangle {
        id: cols
        anchors.top: trashBar.bottom; width: parent.width; height: 24; color: Theme.panel
        property bool wide: panel.width > 620
        component ColHead: Rectangle {
            property string key; property string label; property int align: Text.AlignLeft
            height: parent.height; color: hma.containsMouse ? Theme.hover : "transparent"
            Text { anchors.fill: parent; anchors.leftMargin: 6; anchors.rightMargin: 6; verticalAlignment: Text.AlignVCenter
                   horizontalAlignment: parent.align
                   text: parent.label + (panel.model.sortKey === parent.key ? (panel.model.sortDesc ? "  ▼" : "  ▲") : "")
                   color: panel.model.sortKey === parent.key ? Theme.text : Theme.dim; font.family: Theme.font; font.pixelSize: 11 }
            MouseArea { id: hma; anchors.fill: parent; hoverEnabled: parent.key !== ""; onClicked: { if (parent.key) panel.model.setSort(parent.key); panel.activated() } }
        }
        Row {
            anchors.fill: parent
            ColHead { key: "name"; label: "Név"; width: cols.width - extW.width - sizeW.width - dateW.width - attrW.width }
            ColHead { id: extW; key: "ext"; label: "Kit."; width: 56 }
            ColHead { id: sizeW; key: "size"; label: "Méret"; width: 86; align: Text.AlignRight }
            ColHead { id: dateW; key: "date"; label: "Dátum"; width: 128 }
            ColHead { id: attrW; key: ""; label: "Jogok"; width: cols.wide ? 88 : 0; visible: cols.wide }
        }
    }

    // --- lista ---
    ListView {
        id: list
        anchors.top: cols.bottom; anchors.bottom: status.top; anchors.left: parent.left; anchors.right: parent.right
        anchors.margins: 1
        clip: true
        model: panel.model
        focus: true
        activeFocusOnTab: false
        keyNavigationEnabled: false
        boundsBehavior: Flickable.StopAtBounds
        highlightMoveDuration: 0
        currentIndex: 0
        ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }
        onActiveFocusChanged: if (activeFocus) panel.activated()
        property int pageRows: Math.max(1, Math.floor(height / Theme.row) - 1)

        delegate: Rectangle {
            id: rowItem
            width: list.width; height: Theme.row
            property bool isCur: index === list.currentIndex
            color: isCur && panel.active ? Theme.selected : (index % 2 ? Theme.alt : Theme.base)
            border.color: isCur ? (panel.active ? Theme.accent : "#3a4552") : "transparent"
            border.width: 1
            Rectangle { visible: model.marked; width: 3; height: parent.height; color: Theme.mark }
            Row {
                anchors.fill: parent; anchors.leftMargin: 6
                Item {
                    width: cols.width - extW.width - sizeW.width - dateW.width - attrW.width - 6; height: parent.height
                    FIcon { id: ic; name: model.icon; size: 16; anchors.verticalCenter: parent.verticalCenter }
                    Text { anchors.left: ic.right; anchors.leftMargin: 6; anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter
                           text: model.isParent ? ".." : (model.isDir ? "[" + model.name + "]" : model.name); elide: Text.ElideRight
                           color: model.marked ? Theme.mark : (model.hidden ? Theme.dim : Theme.text)
                           font.family: Theme.font; font.pixelSize: 13; font.bold: model.marked; font.italic: model.isLink }
                }
                Text { width: extW.width; height: parent.height; leftPadding: 6; verticalAlignment: Text.AlignVCenter; elide: Text.ElideRight
                       text: model.ext; color: model.marked ? Theme.mark : Theme.dim; font.family: Theme.font; font.pixelSize: 12 }
                Text { width: sizeW.width; height: parent.height; rightPadding: 6; verticalAlignment: Text.AlignVCenter; horizontalAlignment: Text.AlignRight
                       text: model.sizeText; color: model.marked ? Theme.mark : Theme.dim; font.family: Theme.mono; font.pixelSize: 12 }
                Text { width: dateW.width; height: parent.height; leftPadding: 8; verticalAlignment: Text.AlignVCenter
                       text: model.dateText; color: model.marked ? Theme.mark : Theme.dim; font.family: Theme.mono; font.pixelSize: 12 }
                Text { width: attrW.width; visible: cols.wide; height: parent.height; leftPadding: 6; verticalAlignment: Text.AlignVCenter
                       text: model.attr; color: "#6e7681"; font.family: Theme.mono; font.pixelSize: 12 }
            }
            MouseArea {
                id: rma
                anchors.fill: parent
                acceptedButtons: Qt.LeftButton | Qt.RightButton
                property point start
                property bool dragging: false
                onPressed: (m) => {
                    panel.activated(); list.forceActiveFocus()
                    start = Qt.point(m.x, m.y); dragging = false
                    if (m.button === Qt.RightButton) { list.currentIndex = index; panel.request("menu"); return }
                    if (m.modifiers & Qt.ControlModifier) { panel.model.toggleMark(index); list.currentIndex = index }
                    else if (m.modifiers & Qt.ShiftModifier) { panel.model.markRange(list.currentIndex, index, true); list.currentIndex = index }
                    else list.currentIndex = index
                }
                onPositionChanged: (m) => {
                    if (!pressed || m.buttons !== Qt.LeftButton) return
                    var p = mapToItem(dragProxy.parent, m.x, m.y)
                    if (!dragging && Math.abs(m.x - start.x) + Math.abs(m.y - start.y) > 10 && !model.isParent) {
                        dragging = true
                        dragProxy.paths = panel.selection(); dragProxy.source = panel.side
                        dragProxy.x = p.x + 8; dragProxy.y = p.y + 8
                        dragProxy.Drag.active = true
                    } else if (dragging) { dragProxy.x = p.x + 8; dragProxy.y = p.y + 8 }
                }
                onReleased: (m) => {
                    if (dragging) { dragProxy.shift = (m.modifiers & Qt.ShiftModifier) !== 0; dragProxy.Drag.drop(); dragProxy.Drag.active = false; dragging = false }
                }
                onDoubleClicked: (m) => { if (m.button === Qt.LeftButton) panel.openRow(index) }
            }
        }

        DropArea {
            anchors.fill: parent
            keys: ["fusion-files", "text/uri-list"]
            property int hoverRow: -1
            onPositionChanged: (d) => hoverRow = list.indexAt(d.x + list.contentX, d.y + list.contentY)
            onExited: hoverRow = -1
            onDropped: (d) => {
                var row = list.indexAt(d.x + list.contentX, d.y + list.contentY)
                var it = panel.model.item(row)
                var target = panel.model.path
                if (it && it.isDir) target = it.isParent ? it.full : it.full
                var paths = (d.source === dragProxy) ? dragProxy.paths : d.urls.map(u => decodeURIComponent(u.toString().replace(/^file:\/\//, "")))
                hoverRow = -1
                if (d.source === dragProxy && dragProxy.source === panel.side && target === panel.model.path) return
                d.accept(Qt.CopyAction)
                win.dropped(paths, target, d.source === dragProxy && dragProxy.shift)
            }
            Rectangle { anchors.fill: parent; color: "transparent"; border.color: Theme.accent; border.width: 2; visible: parent.containsDrag }
        }

        // --- billentyűk ---
        Keys.onPressed: (e) => {
            var ctrl = e.modifiers & Qt.ControlModifier, shift = e.modifiers & Qt.ShiftModifier, alt = e.modifiers & Qt.AltModifier
            var i = list.currentIndex, n = list.count
            var mv = function (t) { t = Math.max(0, Math.min(n - 1, t)); if (shift) panel.model.markRange(i, t, true); panel.setCur(t) }
            switch (e.key) {
            case Qt.Key_Up: mv(i - 1); break
            case Qt.Key_Down: mv(i + 1); break
            case Qt.Key_PageUp: if (ctrl) panel.go(panel.model.path + "/.."); else mv(i - list.pageRows); break
            case Qt.Key_PageDown: mv(i + list.pageRows); break
            case Qt.Key_Home: mv(0); break
            case Qt.Key_End: mv(n - 1); break
            case Qt.Key_Return: case Qt.Key_Enter: panel.openRow(i); break
            case Qt.Key_Backspace: panel.go(panel.model.path + "/.."); break
            case Qt.Key_Insert: panel.model.toggleMark(i); panel.setCur(i + 1); break
            case Qt.Key_Space:
                var it = panel.model.item(i)
                if (it.isDir && !it.isParent && !it.marked) files.dirSize(panel.model, it.full)
                panel.model.toggleMark(i); break
            case Qt.Key_Tab: case Qt.Key_Backtab: win.switchPanel(); break
            case Qt.Key_Delete: panel.request("delete"); break
            case Qt.Key_Asterisk: panel.model.invertMarks(); break
            case Qt.Key_Plus: if (e.modifiers & Qt.KeypadModifier || !e.text) { panel.request("markplus"); break } e.accepted = false; typeAheadKey(e); return
            case Qt.Key_Minus: if (e.modifiers & Qt.KeypadModifier) { panel.request("markminus"); break } e.accepted = false; typeAheadKey(e); return
            default:
                e.accepted = false
                typeAheadKey(e)
                return
            }
            e.accepted = true
        }
        function typeAheadKey(e) {
            var ctrl = e.modifiers & (Qt.ControlModifier | Qt.AltModifier | Qt.MetaModifier)
            if (ctrl || !e.text || e.text.charCodeAt(0) < 32) return
            panel.typeAhead += e.text
            typeTimer.restart()
            var r = panel.model.findPrefix(panel.typeAhead, Math.max(0, list.currentIndex))
            if (r < 0 && panel.typeAhead.length > 1) { panel.typeAhead = e.text; r = panel.model.findPrefix(e.text, list.currentIndex + 1) }
            if (r >= 0) panel.setCur(r)
            e.accepted = true
        }
    }
    Timer { id: typeTimer; interval: 1000; onTriggered: panel.typeAhead = "" }
    Rectangle {
        visible: panel.typeAhead !== ""
        anchors.right: parent.right; anchors.bottom: status.top; anchors.margins: 6
        width: taText.implicitWidth + 16; height: 24; color: Theme.selected; border.color: Theme.accent
        Text { id: taText; anchors.centerIn: parent; text: "→ " + panel.typeAhead; color: Theme.text; font.family: Theme.font; font.pixelSize: 12 }
    }
    Text {
        anchors.centerIn: list; visible: panel.model.error !== ""; width: list.width - 40; wrapMode: Text.Wrap
        horizontalAlignment: Text.AlignHCenter; text: panel.model.error; color: Theme.danger; font.family: Theme.font
    }

    // --- állapotsor ---
    Rectangle {
        id: status
        anchors.bottom: parent.bottom; width: parent.width; height: 24; color: Theme.panel
        Text { x: 8; anchors.verticalCenter: parent.verticalCenter; text: panel.model.status; color: Theme.dim
               font.family: Theme.font; font.pixelSize: 11; width: parent.width - 16; elide: Text.ElideRight }
    }
}
