// Vas & Króm — főablak: felső sáv (oldalak, pénz, nap), oldalak, telefon (üzenetek), verseny
import QtQuick
import QtQuick.Window
import QtQuick.Controls

ApplicationWindow {
    id: win
    width: 1280; height: 780
    minimumWidth: 1100; minimumHeight: 700
    visible: !selftestMode
    title: "Vas & Króm"
    color: "#121316"
    property var st: game.state
    property string page: st.bikes && st.bikes.length ? "garage" : "news"
    property var race: null              // a futó verseny adatai (challenge eredménye)
    property string toastText: ""
    property bool toastErr: false
    function money(n) { return "$" + Number(n).toLocaleString(Qt.locale("hu_HU"), "f", 0) }
    function startRace(r) { if (r && r.ok) { race = r } }

    Connections {
        target: game
        function onToast(t, err) { win.toastText = t; win.toastErr = err; toastTimer.restart() }
    }

    // felső sáv
    Rectangle {
        id: top
        width: parent.width; height: 64; z: 5
        gradient: Gradient { GradientStop { position: 0; color: "#2a2d33" } GradientStop { position: 1; color: "#15171a" } }
        Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 3; color: "#7a4b1c" }
        // logó
        Rectangle {
            id: logoBox
            x: 14; anchors.verticalCenter: parent.verticalCenter; width: logo.implicitWidth + 30; height: 46; radius: 6
            gradient: Gradient { GradientStop { position: 0; color: "#c4271b" } GradientStop { position: 1; color: "#6e0d08" } }
            border.color: "#ffcf3a"; border.width: 2
            Text { id: logo; anchors.centerIn: parent; text: "VAS & KRÓM"; color: "#ffd54a"; style: Text.Outline; styleColor: "#3a0602"
                   font.family: "DejaVu Sans"; font.bold: true; font.pixelSize: 24; font.letterSpacing: 2 }
        }
        Row {
            x: logoBox.x + logoBox.width + 16; anchors.verticalCenter: parent.verticalCenter; spacing: 8
            Repeater {
                model: [{ id: "garage", t: "GARÁZS" }, { id: "news", t: "MOTO APRÓ" }, { id: "catalog", t: "KATALÓGUS" },
                        { id: "junk", t: "BONTÓ" }, { id: "bar", t: "KOCSMA" }]
                Btn { text: modelData.t; active: win.page === modelData.id; fs: 15; height: 40; onClicked: win.page = modelData.id }
            }
        }
        Row {
            anchors.right: parent.right; anchors.rightMargin: 14; anchors.verticalCenter: parent.verticalCenter; spacing: 16
            Column {
                anchors.verticalCenter: parent.verticalCenter
                Text { text: "PÉNZ"; color: "#9aa0a6"; font.pixelSize: 11; font.bold: true; font.family: "DejaVu Sans" }
                Text { text: win.money(win.st.money || 0); color: "#ffd54a"; font.pixelSize: 22; font.bold: true; font.family: "DejaVu Sans" }
            }
            Column {
                anchors.verticalCenter: parent.verticalCenter
                Text { text: "NAP"; color: "#9aa0a6"; font.pixelSize: 11; font.bold: true; font.family: "DejaVu Sans" }
                Text { text: win.st.day || 1; color: "#e8e8e8"; font.pixelSize: 22; font.bold: true; font.family: "DejaVu Sans" }
            }
            Column {
                anchors.verticalCenter: parent.verticalCenter
                Text { text: "LEGYŐZÖTT"; color: "#9aa0a6"; font.pixelSize: 11; font.bold: true; font.family: "DejaVu Sans" }
                Text { text: (win.st.beaten || 0) + " / 12"; color: "#e8e8e8"; font.pixelSize: 22; font.bold: true; font.family: "DejaVu Sans" }
            }
            Btn { text: "NAP VÉGE ▸"; kind: "red"; fs: 15; height: 40; anchors.verticalCenter: parent.verticalCenter
                  onClicked: game.endDay() }
            Btn { text: "☰"; height: 40; width: 40; anchors.verticalCenter: parent.verticalCenter; onClicked: menu.open() }
        }
    }
    Menu {
        id: menu; x: win.width - 220; y: 60
        MenuItem { text: "Új játék"; onTriggered: confirmNew.open() }
        MenuItem { text: sound.enabled ? "Hang kikapcsolása" : "Hang bekapcsolása"; enabled: sound.available
                   onTriggered: sound.enabled = !sound.enabled }
        MenuItem { text: "Súgó"; onTriggered: help.visible = true }
        MenuItem { text: "Kilépés"; onTriggered: Qt.quit() }
    }
    Dialog {
        id: confirmNew; anchors.centerIn: parent; modal: true; title: "Új játék?"
        standardButtons: Dialog.Yes | Dialog.No
        Label { text: "A mostani állás elvész." }
        onAccepted: game.newGame()
    }

    // oldalak
    Item {
        id: pages
        anchors { left: parent.left; right: parent.right; top: top.bottom; bottom: parent.bottom }
        Garage { anchors.fill: parent; visible: win.page === "garage" }
        News { anchors.fill: parent; visible: win.page === "news" }
        Catalog { anchors.fill: parent; visible: win.page === "catalog" }
        Junk { anchors.fill: parent; visible: win.page === "junk" }
        Bar { anchors.fill: parent; visible: win.page === "bar" }
    }

    // telefon: kihívások, ajánlatok
    Phone { id: phone; z: 8; anchors.right: parent.right; anchors.bottom: parent.bottom; anchors.margins: 16
            visible: (win.st.messages || []).length > 0 && !win.race }

    // értesítés
    Rectangle {
        z: 9; visible: win.toastText !== ""; anchors.horizontalCenter: parent.horizontalCenter; y: 78
        width: Math.min(tt.implicitWidth + 40, parent.width - 60); height: 42; radius: 6
        color: win.toastErr ? "#5a1414" : "#1d3a24"; border.color: win.toastErr ? "#e5534b" : "#3fb950"; border.width: 2
        Text { id: tt; anchors.centerIn: parent; text: win.toastText; color: "white"; font.pixelSize: 15; font.family: "DejaVu Sans"
               width: parent.width - 30; elide: Text.ElideRight; horizontalAlignment: Text.AlignHCenter }
    }
    Timer { id: toastTimer; interval: 4500; onTriggered: win.toastText = "" }

    // győzelem
    Rectangle {
        z: 20; anchors.fill: parent; visible: !!win.st.won && !win.race && !wonSeen; color: "#d0000000"
        property bool wonSeen: false
        Column {
            anchors.centerIn: parent; spacing: 18
            Text { anchors.horizontalCenter: parent.horizontalCenter; text: "LEGYŐZTED A KIRÁLYT!"; color: "#ffd54a"
                   font.pixelSize: 54; font.bold: true; style: Text.Outline; styleColor: "#6e0d08" }
            Text { anchors.horizontalCenter: parent.horizontalCenter; text: "A város leggyorsabb motorosa vagy. " + (win.st.day || 0) + " nap alatt."
                   color: "white"; font.pixelSize: 20 }
            Btn { anchors.horizontalCenter: parent.horizontalCenter; text: "TOVÁBB"; kind: "red"; onClicked: parent.parent.wonSeen = true }
        }
    }

    // súgó
    Rectangle {
        id: help; z: 15; anchors.fill: parent; color: "#e0000000"; visible: false
        Panel {
            anchors.centerIn: parent; width: 760; height: 520; title: "HOGYAN JÁTSSZ"
            Text {
                anchors.fill: parent; wrapMode: Text.Wrap; color: "#e8e8e8"; font.pixelSize: 15; textFormat: Text.StyledText
                text: "<b>Cél:</b> legyőzni mindenkit a Kocsmában, végül <b>a Királyt</b>.<br><br>" +
                      "<b>Moto Apró</b>: használt motorok. Vegyél egyet — a garázsban " + (win.st.garageSlots || 3) + " hely van.<br>" +
                      "<b>Katalógus</b>: új alkatrész (drága, 100 %). <b>Bontó</b>: használt, olcsó, naponta más.<br>" +
                      "<b>Garázs</b>: szerelés, javítás, fényezés, eladás, próbafutam.<br>" +
                      "<b>Kocsma</b>: kihívás pénzre vagy <b>forgalmira</b> (a vesztes motorja a győztesé).<br><br>" +
                      "<b>Verseny (402 m):</b> a lámpánál <b>SZÓKÖZ</b> = gáz (tartsd), zöldnél <b>JOBB NYÍL / ENTER</b> = kuplung, " +
                      "utána ugyanezzel váltasz. Túl magas fordulat az indulásnál: kipörgés. A piros mező fölött a motor károsodik. " +
                      "Zöld előtt indulsz: kiesel.<br><br><b>Nap vége</b>: új hirdetések, új bontókínálat, vevők jelentkeznek. Ha fogy a pénz: <b>Szerelőmunka</b> (Garázs; egy nap, kis biztos pénz).<br>" +
                      "Tipp: az újságban mindig van egy olcsó, <b>felújítandó</b> motor — javítsd meg, és kezdd a kocsma leggyengébbjeivel, kis tétre."
            }
        }
        MouseArea { anchors.fill: parent; z: -1; onClicked: help.visible = false }
    }

    // verseny
    Loader {
        id: raceLoader; z: 30; anchors.fill: parent; active: !!win.race
        sourceComponent: Race { info: win.race; onClosed: win.race = null }
    }
    Component.onCompleted: { if (!selftestMode && (!win.st.bikes || !win.st.bikes.length) && win.st.day === 1) help.visible = true }
}
