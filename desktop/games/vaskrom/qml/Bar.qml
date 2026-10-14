// Kocsma: a motorosok, kihívás tétre vagy forgalmira; jobb oldalt a ranglista
import QtQuick
import QtQuick.Controls

Item {
    id: bp
    property var st: win.st
    property int bet: 100
    property bool pink: false
    Canvas {
        anchors.fill: parent
        onWidthChanged: requestPaint(); onHeightChanged: requestPaint()
        onPaint: {
            var c = getContext("2d"), w = width, h = height
            var g = c.createLinearGradient(0, 0, 0, h)
            g.addColorStop(0, "#2a1a10"); g.addColorStop(1, "#140c07"); c.fillStyle = g; c.fillRect(0, 0, w, h)
            c.strokeStyle = "rgba(0,0,0,0.4)"; c.lineWidth = 2
            for (var x = 0; x < w; x += 46) { c.beginPath(); c.moveTo(x, 0); c.lineTo(x, h); c.stroke() }
            // neon felirat fénye
            var rg = c.createRadialGradient(w * 0.35, 40, 10, w * 0.35, 40, 300)
            rg.addColorStop(0, "rgba(255,60,40,0.25)"); rg.addColorStop(1, "rgba(255,60,40,0)"); c.fillStyle = rg; c.fillRect(0, 0, w, 300)
        }
    }
    Text { x: 24; y: 10; text: "KOCSMA · Olajos Kanna"; color: "#ff6a50"; font.pixelSize: 32; font.bold: true; font.family: "DejaVu Serif"
           style: Text.Outline; styleColor: "#5a0a00" }
    // tét
    Row {
        x: 24; y: 62; spacing: 8
        Text { text: "TÉT:"; color: "#e8e8e8"; font.pixelSize: 16; font.bold: true; anchors.verticalCenter: parent.verticalCenter }
        Repeater {
            model: [50, 100, 250, 500, 1000, 2500]
            Btn { text: win.money(modelData); active: !bp.pink && bp.bet === modelData; height: 34
                  enabled: (bp.st.money || 0) >= modelData; onClicked: { bp.bet = modelData; bp.pink = false } }
        }
        Btn { text: "FORGALMIRA"; kind: bp.pink ? "gold" : "dark"; height: 34; onClicked: bp.pink = !bp.pink }
        Text { leftPadding: 10; anchors.verticalCenter: parent.verticalCenter; color: "#9aa0a6"; font.pixelSize: 13
               text: bp.pink ? "a vesztes motorja a győztesé!" : bp.st.cur ? "a te motorod: " + bp.st.cur.name + " (~" + Number(bp.st.cur.est).toFixed(2) + " s)" : "nincs motorod" }
    }
    Flickable {
        anchors { left: parent.left; top: parent.top; bottom: parent.bottom; right: ladder.left; topMargin: 108; leftMargin: 24; rightMargin: 16; bottomMargin: 16 }
        contentHeight: grid.height; clip: true
        ScrollBar.vertical: ScrollBar {}
        Grid {
            id: grid; columns: Math.max(1, Math.floor(parent.width / 430)); spacing: 14
            Repeater {
                model: bp.st.bar || []
                Rectangle {
                    width: 420; height: 190; radius: 6
                    color: modelData.king ? "#2a2008" : "#1e1510"; border.color: modelData.king ? "#ffcf3a" : modelData.beaten ? "#3fb950" : "#6b4a2a"
                    border.width: 2
                    BikeView { art: modelData.bike.art; s: 0.32; x: 2; y: 30 }
                    Text { x: 12; y: 8; text: (modelData.king ? "♛ " : "") + modelData.name; color: modelData.king ? "#ffd54a" : "white"
                           font.pixelSize: 19; font.bold: true }
                    Text { visible: modelData.beaten; anchors.right: parent.right; anchors.rightMargin: 10; y: 10; text: "✔ LEGYŐZVE"
                           color: "#3fb950"; font.pixelSize: 12; font.bold: true }
                    Column {
                        x: 228; y: 40; spacing: 3
                        Text { text: modelData.bike.name; color: "#e0b880"; font.pixelSize: 14; font.bold: true; width: 180; elide: Text.ElideRight }
                        Text { text: modelData.bike.hp + " LE · " + modelData.bike.mass + " kg"; color: "#cfd3d8"; font.pixelSize: 13 }
                        Text { text: "~" + Number(modelData.bike.est).toFixed(2) + " s a 402 m"; color: "#cfd3d8"; font.pixelSize: 13 }
                        Text { text: "mérleg: " + modelData.wins + " / " + modelData.losses; color: "#9aa0a6"; font.pixelSize: 12 }
                        Text { text: "zsebében: " + win.money(modelData.cash); color: "#9aa0a6"; font.pixelSize: 12 }
                    }
                    Btn {
                        anchors.right: parent.right; anchors.bottom: parent.bottom; anchors.margins: 10; height: 34; kind: "red"
                        text: bp.pink ? "FORGALMIRA!" : "KIHÍVÁS " + win.money(bp.bet)
                        enabled: !!bp.st.cur && (!modelData.king || bp.st.kingAvailable)
                        onClicked: win.startRace(game.challenge(modelData.name, bp.pink ? 0 : bp.bet, bp.pink))
                    }
                    Text { visible: modelData.king && !bp.st.kingAvailable; x: 12; anchors.bottom: parent.bottom; anchors.bottomMargin: 8
                           text: "csak 8 győzelem után áll ki"; color: "#e5a050"; font.pixelSize: 12 }
                }
            }
        }
    }
    Panel {
        id: ladder; title: "RANGLISTA"
        anchors.right: parent.right; anchors.top: parent.top; anchors.bottom: parent.bottom; anchors.margins: 16; width: 250
        Column {
            spacing: 4; width: parent.width
            Repeater {
                model: (bp.st.ladder || []).slice().reverse()
                Rectangle {
                    width: parent.width; height: 34; radius: 3; color: modelData.beaten ? "#13301a" : "#202227"
                    border.color: index === 0 ? "#ffcf3a" : "transparent"
                    Text { x: 8; anchors.verticalCenter: parent.verticalCenter; text: (12 - index) + "."; color: "#9aa0a6"; font.pixelSize: 13 }
                    Text { x: 38; anchors.verticalCenter: parent.verticalCenter; text: modelData.name; color: index === 0 ? "#ffd54a" : "white"
                           font.pixelSize: 14; font.bold: index === 0; width: 150; elide: Text.ElideRight }
                    Text { anchors.right: parent.right; anchors.rightMargin: 8; anchors.verticalCenter: parent.verticalCenter
                           text: modelData.beaten ? "✔" : ""; color: "#3fb950"; font.pixelSize: 16 }
                }
            }
            Text { width: parent.width; topPadding: 8; wrapMode: Text.Wrap; color: "#9aa0a6"; font.pixelSize: 12
                   text: "A kocsmában naponta mások ülnek. Hírnév: " + (bp.st.rep || 0) }
        }
    }
}
