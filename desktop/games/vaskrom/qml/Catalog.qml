// Katalógus: új alkatrészek csoportonként; a megvett alkatrész a raktárba kerül
import QtQuick
import QtQuick.Controls

Item {
    id: cp
    property var st: win.st
    property string slot: "engine"
    property var slots: [["engine", "Motorblokk"], ["carb", "Karburátor"], ["cam", "Vezérműtengely"], ["exhaust", "Kipufogó"],
                         ["intake", "Levegőszűrő"], ["ignition", "Gyújtás"], ["blower", "Feltöltő"], ["trans", "Váltó"],
                         ["tire", "Hátsó gumi"], ["bars", "Kormány"]]
    function installed(s) {
        if (!st.cur) return null
        for (var i = 0; i < st.cur.parts.length; i++) if (st.cur.parts[i].slot === s) return st.cur.parts[i]
        return null
    }
    Rectangle { anchors.fill: parent; color: "#16181b" }
    Column {
        x: 16; y: 16; width: 220; spacing: 6
        Text { text: "KATALÓGUS"; color: "#ffcf3a"; font.pixelSize: 22; font.bold: true; bottomPadding: 6 }
        Repeater {
            model: cp.slots
            Btn { width: 220; height: 40; fs: 15; text: modelData[1]; active: cp.slot === modelData[0]; onClicked: cp.slot = modelData[0] }
        }
        Text { width: 220; topPadding: 12; wrapMode: Text.Wrap; color: "#7d848b"; font.pixelSize: 12
               text: "Új alkatrész, 100 % állapot. A raktárba kerül, a Garázsban szereled be. A régi alkatrész a raktárban marad — eladhatod." }
    }
    Panel {
        x: 252; y: 16; width: parent.width - 268; height: parent.height - 32
        title: (cp.slots.find(function (x) { return x[0] === cp.slot }) || ["", ""])[1].toUpperCase()
               + (cp.installed(cp.slot) ? "   —   most: " + cp.installed(cp.slot).name + " (" + cp.installed(cp.slot).cond + "%)" : "")
        ListView {
            anchors.fill: parent; clip: true; spacing: 4
            ScrollBar.vertical: ScrollBar {}
            model: (cp.st.catalog || []).filter(function (p) { return p.slot === cp.slot })
            delegate: Rectangle {
                width: ListView.view.width - 12; height: 58; radius: 4; color: index % 2 ? "#202227" : "#1b1d21"
                border.color: "#2c2f34"
                Text { x: 12; y: 8; text: modelData.name; color: modelData.fits ? "white" : "#7d848b"; font.pixelSize: 17; font.bold: true }
                Text { x: 12; y: 32; text: modelData.desc + (modelData.fits ? "" : (cp.st.cur ? "  ·  a mostani motorodba nem illik" : ""))
                       color: modelData.fits ? "#9aa0a6" : "#e5534b"; font.pixelSize: 13 }
                Text { anchors.right: buy.left; anchors.rightMargin: 16; anchors.verticalCenter: parent.verticalCenter
                       text: win.money(modelData.price); color: "#ffd54a"; font.pixelSize: 20; font.bold: true }
                Btn { id: buy; anchors.right: parent.right; anchors.rightMargin: 10; anchors.verticalCenter: parent.verticalCenter
                      text: "MEGVESZEM"; kind: "red"; enabled: (cp.st.money || 0) >= modelData.price; onClicked: game.buyPart(modelData.id) }
            }
        }
    }
}
