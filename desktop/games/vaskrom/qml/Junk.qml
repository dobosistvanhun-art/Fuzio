// Bontó: használt alkatrészek olcsón, változó állapotban, naponta más kínálat
import QtQuick
import QtQuick.Controls

Item {
    id: jp
    property var st: win.st
    Image {
        anchors.fill: parent; source: "../img/junk.svg"; fillMode: Image.PreserveAspectCrop
        sourceSize.width: Math.max(width, height * 16 / 9); smooth: true; asynchronous: true
    }
    Rectangle {
        x: 24; y: 16; width: sign.implicitWidth + 40; height: 52; color: "#d9c27a"; border.color: "#3a2a10"; border.width: 3; rotation: -2
        Text { id: sign; anchors.centerIn: parent; text: "BONTÓ · Rozsdás Józsi"; color: "#3a2a10"; font.pixelSize: 26; font.bold: true; font.family: "DejaVu Serif" }
    }
    Text { anchors.right: parent.right; anchors.rightMargin: 24; y: 28; text: "Pénzed: " + win.money(jp.st.money || 0); color: "#ffd54a"
           font.pixelSize: 20; font.bold: true; style: Text.Outline; styleColor: "black" }
    Text { visible: !(jp.st.junk || []).length; anchors.centerIn: parent; text: "Mára elfogyott minden. Holnap jön új szállítmány."
           color: "white"; font.pixelSize: 20; style: Text.Outline; styleColor: "black" }
    Flickable {
        anchors { fill: parent; topMargin: 90; leftMargin: 24; rightMargin: 24; bottomMargin: 16 }
        contentHeight: grid.height; clip: true
        ScrollBar.vertical: ScrollBar {}
        Grid {
            id: grid; columns: Math.max(1, Math.floor(parent.width / 300)); spacing: 14
            Repeater {
                model: jp.st.junk || []
                Rectangle {
                    width: 290; height: 150; radius: 4
                    gradient: Gradient { GradientStop { position: 0; color: "#5a3a22" } GradientStop { position: 1; color: "#3a2414" } }
                    border.color: "#8b5a2b"; border.width: 2
                    Rectangle { x: 10; y: 10; width: 46; height: 18; radius: 3; color: "#d9c27a"; rotation: -4
                                Text { anchors.centerIn: parent; text: modelData.cond + "%"; color: "#3a2a10"; font.pixelSize: 12; font.bold: true } }
                    Text { x: 66; y: 10; width: parent.width - 76; text: modelData.slotName; color: "#e0b880"; font.pixelSize: 12; font.bold: true }
                    Text { x: 12; y: 36; width: parent.width - 24; text: modelData.name; color: "white"; font.pixelSize: 16; font.bold: true; elide: Text.ElideRight }
                    Text { x: 12; y: 60; width: parent.width - 24; text: modelData.desc; color: "#d8c8b0"; font.pixelSize: 12; elide: Text.ElideRight }
                    CondBar { x: 12; y: 82; width: parent.width - 24; value: modelData.cond }
                    Text { x: 12; y: 102; text: modelData.fits ? "beleillik a motorodba" : (jp.st.cur ? "a mostani motorodba nem illik" : "")
                           color: modelData.fits ? "#7ee787" : "#e5a050"; font.pixelSize: 11 }
                    Text { x: 12; y: 118; text: win.money(modelData.price); color: "#ffd54a"; font.pixelSize: 20; font.bold: true }
                    Btn { anchors.right: parent.right; anchors.rightMargin: 10; y: 112; height: 30; text: "VISZEM"; kind: "red"
                          enabled: (jp.st.money || 0) >= modelData.price; onClicked: game.buyJunk(modelData.key) }
                }
            }
        }
    }
}
