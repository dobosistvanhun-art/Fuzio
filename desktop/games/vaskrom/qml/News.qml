// Moto Apró: újság a használt motorok hirdetéseivel
import QtQuick
import QtQuick.Controls

Item {
    id: np
    property var st: win.st
    Rectangle { anchors.fill: parent; color: "#3b3127" }
    Rectangle {
        id: paper
        anchors.fill: parent; anchors.margins: 18; color: "#efe9dc"
        border.color: "#b9ad94"; border.width: 1
        // fejléc
        Column {
            id: head; x: 24; y: 14; width: parent.width - 48; spacing: 2
            Row {
                width: parent.width
                Text { width: parent.width / 3; text: "Ára: 2 Ft · " + (np.st.day || 1) + ". nap"; color: "#3a3226"; font.family: "DejaVu Serif"; font.pixelSize: 13 }
                Text { width: parent.width / 3; horizontalAlignment: Text.AlignHCenter; text: "★ HASZNÁLT MOTOROK ★"; color: "#3a3226"
                       font.family: "DejaVu Serif"; font.pixelSize: 13; font.bold: true }
                Text { width: parent.width / 3; horizontalAlignment: Text.AlignRight; text: "Pénzed: " + win.money(np.st.money || 0)
                       color: "#7a1a10"; font.family: "DejaVu Serif"; font.pixelSize: 15; font.bold: true }
            }
            Text { anchors.horizontalCenter: parent.horizontalCenter; text: "MOTO APRÓ"; color: "#1c1813"
                   font.family: "DejaVu Serif"; font.pixelSize: 58; font.bold: true; font.letterSpacing: 6 }
            Rectangle { width: parent.width; height: 3; color: "#1c1813" }
            Rectangle { width: parent.width; height: 1; color: "#1c1813" }
        }
        Text {
            visible: !(np.st.ads || []).length; anchors.centerIn: parent; color: "#5a5040"; font.family: "DejaVu Serif"; font.pixelSize: 20
            text: "Ma nincs több hirdetés. Holnap új szám jelenik meg (Nap vége)."
        }
        Flickable {
            anchors { left: parent.left; right: parent.right; top: head.bottom; bottom: parent.bottom; margins: 20 }
            contentHeight: grid.height; clip: true
            ScrollBar.vertical: ScrollBar {}
            Grid {
                id: grid; columns: Math.max(1, Math.floor((parent.width + 18) / 398)); spacing: 18
                Repeater {
                    model: np.st.ads || []
                    Rectangle {
                        width: (grid.parent.width - (grid.columns - 1) * 18) / grid.columns; height: 330; color: "transparent"; border.color: "#7a6e58"; border.width: 1
                        Rectangle { x: 10; y: 10; width: parent.width - 20; height: 176; color: "#ddd5c2"; border.color: "#b9ad94"
                            BikeView { art: modelData.bike.art; s: 0.5; anchors.centerIn: parent; anchors.verticalCenterOffset: -6 } }
                        Text { x: 12; y: 192; width: parent.width - 24; text: modelData.bike.name.toUpperCase(); color: "#1c1813"
                               font.family: "DejaVu Serif"; font.bold: true; font.pixelSize: 18; elide: Text.ElideRight }
                        Text { x: 12; y: 216; width: parent.width - 24; height: 58; text: modelData.text; color: "#3a3226"
                               font.family: "DejaVu Serif"; font.pixelSize: 13; wrapMode: Text.Wrap; elide: Text.ElideRight; maximumLineCount: 3 }
                        Text { x: 12; y: 274; text: modelData.bike.hp + " LE · " + modelData.bike.mass + " kg · állapot " + modelData.bike.cond + "% · ~"
                                                   + Number(modelData.bike.est).toFixed(1) + " s"
                               color: "#5a5040"; font.family: "DejaVu Serif"; font.pixelSize: 12 }
                        Text { x: 12; y: 296; text: win.money(modelData.price); color: "#7a1a10"; font.family: "DejaVu Serif"; font.bold: true; font.pixelSize: 24 }
                        Btn { anchors.right: parent.right; anchors.rightMargin: 10; y: 292; text: "MEGVESZEM"; kind: "red"
                              enabled: (np.st.money || 0) >= modelData.price; onClicked: { if (game.buyAd(modelData.id)) win.page = "garage" } }
                    }
                }
            }
        }
    }
}
