// Garázs: a kiválasztott motor nagyban, alkatrészek (állapot, javítás), raktár (beszerelés), fényezés, eladás, próbafutam
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: gp
    property var st: win.st
    property var cur: st.cur

    property bool running: false
    property real grpm: 900
    onRunningChanged: if (!running && typeof sound !== "undefined") sound.engineOff("garage")
    onVisibleChanged: if (!visible) running = false
    onCurChanged: running = false
    Timer {
        interval: 30; repeat: true; running: gp.running && !!gp.cur && !win.race
        onRunningChanged: if (!running && typeof sound !== "undefined") sound.engineOff("garage")
        onTriggered: {
            var red = gp.cur.red, g = gasG.pressed
            gp.grpm += g ? 7500 * 0.03 : -5000 * 0.03
            gp.grpm = Math.max(900, gp.grpm)
            if (gp.grpm >= red) gp.grpm = red - 400
            sound.engine("garage", gp.grpm, g ? 1 : 0, gp.cur.cyl, gp.cur.loud, gp.cur.cc, 1.0)
        }
    }

    // háttér: tégla fal, szerszámfal, beton padló
    // a padló vonala a háttérképen (scenes.py: 900-ból 630) — a motor ezen áll
    readonly property real floorY: height - 270 * Math.max(width / 1600, height / 900)
    Image {
        anchors.fill: parent; source: "../img/garage.svg"; fillMode: Image.PreserveAspectCrop; verticalAlignment: Image.AlignBottom
        sourceSize.width: Math.max(width, height * 16 / 9); smooth: true; asynchronous: true
    }

    // üres garázs
    Column {
        visible: !gp.cur; anchors.centerIn: parent; spacing: 18
        Text { anchors.horizontalCenter: parent.horizontalCenter; text: "Üres a garázs"; color: "#ffd54a"; font.pixelSize: 40; font.bold: true
               style: Text.Outline; styleColor: "#000" }
        Text { anchors.horizontalCenter: parent.horizontalCenter; text: "Vegyél egy használt motort a Moto Apróból — " + win.money(gp.st.money || 0) + " van nálad."
               color: "white"; font.pixelSize: 18 }
        Btn { anchors.horizontalCenter: parent.horizontalCenter; text: "MOTO APRÓ ▸"; kind: "red"; fs: 18; height: 46; onClicked: win.page = "news" }
        Btn { anchors.horizontalCenter: parent.horizontalCenter; text: "SZERELŐMUNKA (egy nap, kis pénz)"; fs: 15; height: 40; onClicked: game.work() }
    }

    // bal: motorválasztó, a motor, adatok, műveletek
    Item {
        visible: !!gp.cur
        x: 16; y: 12; width: parent.width - 520 - 48; height: parent.height - 24
        Row {
            id: picker; spacing: 10
            Repeater {
                model: gp.st.bikes || []
                Rectangle {
                    width: 150; height: 80; radius: 5
                    color: modelData.uid === gp.st.current ? "#3a1a10" : "#1b1d21"
                    border.color: modelData.uid === gp.st.current ? "#ffcf3a" : "#5b4632"; border.width: 2
                    BikeView { art: modelData.art; s: 0.19; x: 10; y: -4 }
                    Text { x: 6; anchors.bottom: parent.bottom; anchors.bottomMargin: 3; width: parent.width - 12; elide: Text.ElideRight
                           text: modelData.name; color: "#e8e8e8"; font.pixelSize: 11; font.bold: true }
                    Text { visible: modelData.selling > 0; anchors.right: parent.right; anchors.rightMargin: 5; y: 4; text: "ELADÓ"
                           color: "#ffd54a"; font.pixelSize: 10; font.bold: true }
                    MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: game.select(modelData.uid) }
                }
            }
            Repeater {
                model: Math.max(0, (gp.st.garageSlots || 3) - (gp.st.bikes || []).length)
                Rectangle { width: 150; height: 80; radius: 5; color: "#14151880"; border.color: "#3a3d42"; border.width: 2
                            Text { anchors.centerIn: parent; text: "üres hely"; color: "#6e757c"; font.pixelSize: 13 } }
            }
        }
        // berúgás: a motor hangja a garázsban (a kipufogócsere itt hallatszik), GÁZ nyomva tartva
        Row {
            anchors.right: parent.right; y: picker.height + 12; spacing: 8; z: 2
            visible: typeof sound !== "undefined" && sound.available && sound.enabled
            Btn { text: gp.running ? "■ LEÁLLÍT" : "🔑 BERÚGÁS"; kind: gp.running ? "dark" : "gold"; fs: 13; height: 34
                  onClicked: gp.running = !gp.running }
            Rectangle {
                visible: gp.running; width: 90; height: 34; radius: 4; color: gasG.pressed ? "#3fb950" : "#1d3a24"; border.color: "#3fb950"; border.width: 2
                Text { anchors.centerIn: parent; text: "GÁZ"; color: "white"; font.bold: true; font.pixelSize: 14 }
                MouseArea { id: gasG; anchors.fill: parent }
            }
        }
        // a motor
        BikeView {
            id: big; art: gp.cur ? gp.cur.art : null
            s: Math.min(1.05, parent.width / 680)
            anchors.horizontalCenter: parent.horizontalCenter
            y: Math.max(picker.height + 4, gp.floorY - 12 - (art ? art.ground : 330) * s + 2)
        }
        Column {
            anchors.left: parent.left; anchors.top: big.bottom; anchors.topMargin: -6; spacing: 4
            Text { text: gp.cur ? gp.cur.name : ""; color: "#ffd54a"; font.pixelSize: 26; font.bold: true; style: Text.Outline; styleColor: "#000" }
            Text { text: gp.cur ? gp.cur.typeName + " · " + gp.cur.cc + " cm³ · " + gp.cur.gears + " fokozat · " + gp.cur.tire + " mm hátsó gumi" : ""
                   color: "#cfd3d8"; font.pixelSize: 14 }
            Row {
                spacing: 22; topPadding: 6
                Repeater {
                    model: gp.cur ? [["TELJESÍTMÉNY", gp.cur.hp + " LE"], ["NYOMATÉK", gp.cur.nm + " Nm"], ["TÖMEG", gp.cur.mass + " kg"],
                                     ["402 M (BECSLÉS)", Number(gp.cur.est).toFixed(2) + " s"], ["ÉRTÉK", win.money(gp.cur.value)]] : []
                    Column {
                        Text { text: modelData[0]; color: "#9aa0a6"; font.pixelSize: 11; font.bold: true }
                        Text { text: modelData[1]; color: "white"; font.pixelSize: 21; font.bold: true }
                    }
                }
            }
            Text { visible: !!gp.cur && gp.cur.mods.length > 0; text: gp.cur ? "Tuning: " + gp.cur.mods.join(", ") : ""; color: "#ffb347"; font.pixelSize: 13
                   width: big.width; wrapMode: Text.Wrap }
        }
        Row {
            anchors.bottom: parent.bottom; spacing: 10
            Btn { text: "PRÓBAFUTAM"; kind: "red"; fs: 13; height: 40; onClicked: win.startRace(game.practice()) }
            Btn { text: "FÉNYEZÉS"; fs: 13; height: 40; onClicked: paintPop.open() }
            Btn { text: gp.cur && gp.st.bikes.find(function (b) { return b.uid === gp.cur.uid }).selling > 0 ? "ELADÁS VISSZAVONÁSA" : "ELADÁS"
                  fs: 13; height: 40
                  onClicked: {
                      var b = gp.st.bikes.find(function (x) { return x.uid === gp.cur.uid })
                      if (b.selling > 0) game.cancelSale(b.uid); else { priceField.text = String(gp.cur.value); sellPop.open() }
                  } }
            Btn { text: "TELJES JAVÍTÁS  " + (gp.cur ? win.money(gp.cur.repairAll) : ""); fs: 13; height: 40
                  enabled: !!gp.cur && gp.cur.repairAll > 0; onClicked: game.repair("") }
            Btn { text: "SZERELŐMUNKA"; fs: 13; height: 40; onClicked: game.work() }
        }
    }

    // jobb: alkatrészek és raktár
    Column {
        visible: !!gp.cur
        anchors.right: parent.right; anchors.rightMargin: 16; y: 12; width: 520; spacing: 10
        Panel {
            title: "ALKATRÉSZEK"; width: parent.width; height: 36 + 14 + 10 * 34 + 6
            Column {
                anchors.fill: parent; spacing: 2
                Repeater {
                    model: gp.cur ? gp.cur.parts : []
                    Item {
                        width: parent.width; height: 32
                        Rectangle { anchors.fill: parent; color: index % 2 ? "#202227" : "transparent"; radius: 3 }
                        Text { x: 6; y: 2; width: 92; text: modelData.slotName; color: "#9aa0a6"; font.pixelSize: 12; font.bold: true; elide: Text.ElideRight }
                        Text { x: 100; y: 1; width: 196; text: modelData.name; color: "#e8e8e8"; font.pixelSize: 13; elide: Text.ElideRight }
                        Text { x: 100; y: 17; width: 196; text: modelData.desc; color: "#7d848b"; font.pixelSize: 10; elide: Text.ElideRight }
                        CondBar { x: 302; anchors.verticalCenter: parent.verticalCenter; width: 60; value: modelData.cond }
                        Text { x: 366; anchors.verticalCenter: parent.verticalCenter; text: modelData.cond + "%"; color: "#cfd3d8"; font.pixelSize: 11 }
                        Btn { anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; height: 24; fs: 11
                              visible: modelData.repair > 0; text: "JAVÍT " + win.money(modelData.repair)
                              onClicked: game.repair(modelData.slot) }
                    }
                }
            }
        }
        Panel {
            title: "RAKTÁR  (" + (gp.st.stock || []).length + ")"; width: parent.width; height: gp.height - 24 - 10 - (36 + 14 + 10 * 34 + 6)
            Text { visible: !(gp.st.stock || []).length; text: "Üres. Alkatrész a Katalógusból (új) vagy a Bontóból (használt)."
                   color: "#7d848b"; font.pixelSize: 13; width: parent.width; wrapMode: Text.Wrap }
            ListView {
                anchors.fill: parent; clip: true; spacing: 2; model: gp.st.stock || []
                ScrollBar.vertical: ScrollBar {}
                delegate: Item {
                    width: ListView.view.width - 10; height: 36
                    Rectangle { anchors.fill: parent; color: index % 2 ? "#202227" : "transparent"; radius: 3 }
                    Text { x: 6; y: 2; width: 250; text: modelData.name; color: modelData.fits ? "#e8e8e8" : "#7d848b"; font.pixelSize: 13; elide: Text.ElideRight }
                    Text { x: 6; y: 19; width: 250; text: modelData.slotName + (modelData.fits ? "" : " · nem illik ebbe"); color: "#7d848b"; font.pixelSize: 10 }
                    CondBar { x: 262; anchors.verticalCenter: parent.verticalCenter; width: 50; value: modelData.cond }
                    Row {
                        anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; spacing: 6
                        Btn { height: 26; fs: 11; text: "BESZEREL"; kind: "red"; enabled: modelData.fits; onClicked: game.install(modelData.idx) }
                        Btn { height: 26; fs: 11; text: "ELAD " + win.money(modelData.value); onClicked: game.sellPart(modelData.idx) }
                    }
                }
            }
        }
    }

    // fényezés
    Popup {
        id: paintPop; anchors.centerIn: parent; width: 520; height: 300; modal: true
        property string col: gp.cur ? gp.cur.color : ""
        property bool fl: gp.cur ? gp.cur.flames : false
        onOpened: { col = gp.cur.color; fl = gp.cur.flames }
        background: Panel { title: "FÉNYEZÉS — " + win.money(gp.st.paintPrice || 0) + (paintPop.fl && !(gp.cur && gp.cur.flames) ? " + lángok " + win.money(gp.st.flamesPrice || 0) : "") }
        contentItem: Item {
            Grid {
                x: 18; y: 48; columns: 5; spacing: 12
                Repeater {
                    model: gp.st.colors || []
                    Rectangle {
                        width: 80; height: 48; radius: 6; color: modelData.hex
                        border.color: paintPop.col === modelData.hex ? "#ffcf3a" : "#000"; border.width: paintPop.col === modelData.hex ? 4 : 1
                        Text { anchors.bottom: parent.bottom; anchors.horizontalCenter: parent.horizontalCenter; text: modelData.name
                               color: "white"; style: Text.Outline; styleColor: "black"; font.pixelSize: 10 }
                        MouseArea { anchors.fill: parent; onClicked: paintPop.col = modelData.hex }
                    }
                }
            }
            Btn { x: 18; y: 186; height: 36; active: paintPop.fl; onClicked: paintPop.fl = !paintPop.fl
                  text: (paintPop.fl ? "✔ " : "") + "LÁNGNYELVEK" + (gp.cur && gp.cur.flames ? "" : "  +" + win.money(gp.st.flamesPrice || 0)) }
            Row {
                anchors.right: parent.right; anchors.rightMargin: 18; y: 236; spacing: 10
                Btn { text: "MÉGSE"; onClicked: paintPop.close() }
                Btn { text: "FÉNYEZD"; kind: "red"; onClicked: { if (game.paint(paintPop.col, paintPop.fl)) paintPop.close() } }
            }
        }
    }

    // eladás
    Popup {
        id: sellPop; anchors.centerIn: parent; width: 440; height: 220; modal: true
        background: Panel { title: "ELADÁS — HIRDETÉS A MOTO APRÓBAN" }
        contentItem: Item {
            Text { x: 18; y: 50; width: 400; wrapMode: Text.Wrap; color: "#cfd3d8"; font.pixelSize: 14
                   text: "Becsült érték: " + (gp.cur ? win.money(gp.cur.value) : "") + ". Minél drágábban kínálod, annál ritkábban jön vevő. A vevők a nap végén jelentkeznek telefonon." }
            Text { x: 18; y: 120; text: "Ár: $"; color: "white"; font.pixelSize: 18 }
            TextField { id: priceField; x: 80; y: 112; width: 140; font.pixelSize: 18; validator: IntValidator { bottom: 50; top: 999999 } }
            Row {
                anchors.right: parent.right; anchors.rightMargin: 18; y: 160; spacing: 10
                Btn { text: "MÉGSE"; onClicked: sellPop.close() }
                Btn { text: "MEGHIRDETEM"; kind: "red"; onClicked: { if (game.listForSale(gp.cur.uid, parseInt(priceField.text) || 0)) sellPop.close() } }
            }
        }
    }
}
