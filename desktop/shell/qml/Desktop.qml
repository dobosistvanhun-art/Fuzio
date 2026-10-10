// FusionOS — irányítópult az asztalon: egy pillantásra minden fontos állapot
// (lézer, 3D nyomtató, hálózat, rendszer, meghajtók) és gyorsindítás. Nem csicsás: kártyák, szöveg, sávok.
import QtQuick
import FusionUI

Rectangle {
    id: desk
    color: dash.bg

    component Card: Rectangle {
        id: card
        property string title: ""
        property string icon: ""
        property color accent: Theme.accent
        default property alias content: body.data
        width: 360; height: body.implicitHeight + 54
        color: Qt.rgba(0.07, 0.09, 0.11, 0.92); border.color: Theme.border; radius: Theme.radius
        Row {
            x: 14; y: 12; spacing: 8
            FIcon { name: card.icon; size: 18; anchors.verticalCenter: parent.verticalCenter }
            Text { text: card.title; color: Theme.text; font.family: Theme.font; font.pixelSize: 14; font.bold: true; anchors.verticalCenter: parent.verticalCenter }
        }
        Column { id: body; x: 14; y: 42; width: parent.width - 28; spacing: 6 }
    }
    component KV: Row {
        property string k: ""
        property string v: ""
        property color vc: Theme.text
        spacing: 8
        Text { width: 110; text: parent.k; color: Theme.dim; font.family: Theme.font; font.pixelSize: 12; elide: Text.ElideRight }
        Text { width: 220; text: parent.v; color: parent.vc; font.family: Theme.font; font.pixelSize: 12; elide: Text.ElideRight }
    }
    component Bar: Rectangle {
        property real pct: 0
        property color fill: pct > 90 ? Theme.danger : (pct > 75 ? Theme.warn : Theme.accent)
        width: parent ? parent.width : 300; height: 6; radius: 3; color: "#243040"
        Rectangle { width: parent.width * Math.max(0, Math.min(100, parent.pct)) / 100; height: parent.height; radius: 3; color: parent.fill }
    }
    component Dot: Rectangle { property bool on: false; width: 9; height: 9; radius: 4.5; color: on ? Theme.ok : "#4b5563" }

    // fejléc: óra, dátum, verzió
    Column {
        x: 40; y: 32; spacing: 2
        Text { text: shell.clock.time || ""; color: Theme.text; font.family: Theme.font; font.pixelSize: 46; font.weight: Font.Light }
        Text { text: shell.clock.long || ""; color: Theme.dim; font.family: Theme.font; font.pixelSize: 15 }
    }
    Text { anchors.right: parent.right; anchors.rightMargin: 40; y: 40; text: dash.system.version || ""; color: "#4b5563"
           font.family: Theme.font; font.pixelSize: 13 }

    Flow {
        id: dflow
        x: 40; y: 130; width: parent.width - 80; spacing: 16

        // --- lézer ---
        Card {
            title: "Lézer"; icon: "laser"
            property var d: shell.devices.find(x => x.role === "laser") || ({})
            property var lb: shell.apps.find(a => a.fwr === "lightburn")
            Row { spacing: 8
                Dot { on: parent.parent.parent.d.present === true; anchors.verticalCenter: parent.verticalCenter }
                Text { text: parent.parent.parent.d.present ? ("csatlakoztatva — " + parent.parent.parent.d.dev + " → COM3") : "nincs csatlakoztatva"
                       color: parent.parent.parent.d.present ? Theme.text : Theme.dim; font.family: Theme.font; font.pixelSize: 13 } }
            Row { spacing: 6; topPadding: 4
                FButton { visible: !!parent.parent.parent.lb && parent.parent.parent.lb.installed; text: "LightBurn"; icon: "laser"; primary: true
                          onClicked: shell.launch(parent.parent.parent.lb.id) }
                FButton { text: "Eszközök"; flat: true; onClicked: shell.run("fusion-settings devices") } }
        }

        // --- 3D nyomtató (Klipper) ---
        Card {
            id: pc
            title: "3D nyomtató"; icon: "printer"
            property var p: dash.printer
            property var d: shell.devices.find(x => x.role === "printer") || ({})
            function stateText(s) {
                return ({ "printing": "nyomtat", "paused": "szüneteltetve", "complete": "kész", "standby": "készenlét",
                          "error": "hiba", "cancelled": "megszakítva" })[s] || s
            }
            Row { spacing: 8
                Dot { on: pc.p.online && pc.p.klippy === "ready"; anchors.verticalCenter: parent.verticalCenter }
                Text { text: !pc.p.online ? "a Klipper nem érhető el" : (pc.p.klippy !== "ready" ? ("Klipper: " + pc.p.klippy) : pc.stateText(pc.p.state))
                       color: Theme.text; font.family: Theme.font; font.pixelSize: 13 } }
            Text { visible: pc.p.online && pc.p.klippy !== "ready" && pc.p.message !== ""; width: parent.width; text: pc.p.message || ""
                   color: Theme.warn; font.family: Theme.font; font.pixelSize: 11; wrapMode: Text.Wrap; maximumLineCount: 2; elide: Text.ElideRight }
            KV { visible: pc.p.printing === true; k: "Fájl"; v: pc.p.file || "" }
            Bar { visible: pc.p.printing === true; pct: pc.p.progress || 0; fill: Theme.ok }
            KV { visible: pc.p.printing === true; k: "Állás"; v: (pc.p.progress || 0) + " %" }
            KV { visible: pc.p.printing === true; k: "Idő"; v: "eltelt " + (pc.p.elapsed || "") + (pc.p.left ? "  ·  hátra ~" + pc.p.left : "") }
            KV { visible: pc.p.online === true && pc.p.klippy === "ready"; k: "Fej / tálca"; v: pc.p.ext + " / " + pc.p.extT + " °C   ·   " + pc.p.bed + " / " + pc.p.bedT + " °C" }
            KV { k: "USB"; v: pc.d.present ? ("csatlakoztatva — " + pc.d.dev) : "nincs csatlakoztatva"; vc: pc.d.present ? Theme.text : Theme.dim }
            Row { spacing: 6; topPadding: 4
                FButton { text: "Fluidd"; icon: "web"; primary: true; onClicked: shell.run("fusion-printer ui") }
                FButton { text: "Mainsail"; flat: true; onClicked: shell.run("fusion-printer ui mainsail") }
                FButton { text: "G-kódok"; flat: true; onClicked: shell.run("fusion-files /data/printer/gcodes") } }
        }

        // --- hálózat ---
        Card {
            title: "Hálózat"; icon: "wifi"
            Row { spacing: 8
                FSignal { level: shell.wifi.state === "connected" ? shell.wifi.level : 0; anchors.verticalCenter: parent.verticalCenter }
                Text { text: shell.wifi.state === "connected" ? shell.wifi.ssid : "Wi-Fi: nincs kapcsolat"
                       color: shell.wifi.state === "connected" ? Theme.text : Theme.dim; font.family: Theme.font; font.pixelSize: 13 } }
            KV { visible: !!shell.wifi.ip; k: "Wi-Fi cím"; v: shell.wifi.ip || "" }
            Repeater { model: dash.wired
                KV { k: "Vezetékes " + modelData.name; v: modelData.ip || modelData.state; vc: modelData.ip ? Theme.text : Theme.dim } }
            Row { topPadding: 4; FButton { text: "Wi-Fi beállítás"; flat: true; onClicked: shell.run("fusion-settings wifi") } }
        }

        // --- rendszer ---
        Card {
            id: sc
            title: "Rendszer"; icon: "chip"
            property var s: dash.system
            KV { k: "Processzor"; v: (sc.s.cpuPct || 0) + " %  (terhelés " + (sc.s.load || "0") + ")" + (sc.s.temp ? "   ·   " + sc.s.temp : "") }
            Bar { pct: sc.s.cpuPct || 0 }
            KV { k: "Memória"; v: (sc.s.mem || "") + "  (" + (sc.s.memPct || 0) + " %)" }
            Bar { pct: sc.s.memPct || 0 }
            KV { k: "DATA"; v: (sc.s.data && sc.s.data.free) ? (sc.s.data.free + " szabad / " + sc.s.data.total) : "—" }
            Bar { pct: (sc.s.data && sc.s.data.pct) || 0 }
            KV { k: "Bekapcsolva"; v: sc.s.uptime || "" }
        }

        // --- meghajtók ---
        Card {
            title: "Meghajtók"; icon: "drive-usb"
            Text { visible: shell.media.length === 0; text: "Nincs csatlakoztatott meghajtó"; color: Theme.dim; font.family: Theme.font; font.pixelSize: 12 }
            Repeater { model: shell.media
                Row { spacing: 8
                    Text { width: 220; text: modelData.name; color: Theme.text; font.family: Theme.font; font.pixelSize: 13; elide: Text.ElideRight; anchors.verticalCenter: parent.verticalCenter }
                    FButton { text: "Megnyitás"; implicitHeight: 26; flat: true; onClicked: shell.run("fusion-files " + modelData.path) } } }
        }

        // --- programok: nagyobb csempék, csoportok (a Start menü csoportjai), görgethető ---
        Card {
            id: pg
            title: "Programok"; icon: "app"
            width: Math.min(desk.width - 80, 780)
            property string group: ""          // "" = összes, csoportosítva
            readonly property var apps: shell.apps.filter(a => !a.search_only && a.installed)
            readonly property var groupsUsed: shell.allGroups.filter(g => pg.apps.some(a => a.group === g.id))
            readonly property var sections: pg.group === "" ? pg.groupsUsed : pg.groupsUsed.filter(g => g.id === pg.group)
            Flow {
                width: parent.width; spacing: 6
                visible: pg.groupsUsed.length > 1
                Repeater {
                    model: [{ id: "", name: "Összes" }].concat(pg.groupsUsed)
                    Rectangle {
                        height: 26; width: ct.implicitWidth + 22; radius: 13
                        color: pg.group === modelData.id ? Theme.accent : (cma.containsMouse ? Theme.hover : "#1c2530")
                        Text { id: ct; anchors.centerIn: parent; text: modelData.name; font.family: Theme.font; font.pixelSize: 12
                               color: pg.group === modelData.id ? "#0b0f14" : Theme.text }
                        MouseArea { id: cma; anchors.fill: parent; hoverEnabled: true; onClicked: pg.group = modelData.id }
                    }
                }
            }
            Flickable {
                id: pfl
                width: parent.width
                // a kártya alja a képernyő (a tálca feletti rész) aljáig érhet: a kártya helye a Flow-ban + fejléc + csoportfülek
                height: Math.min(pcol.implicitHeight, Math.max(150, desk.height - (dflow.y + pg.y) - 42 - pfl.y - 12 - 16))
                contentHeight: pcol.implicitHeight; clip: true
                boundsBehavior: Flickable.StopAtBounds
                interactive: contentHeight > height
                Column {
                    id: pcol; width: pfl.width - (pfl.interactive ? 12 : 0); spacing: 8
                    Repeater {
                        model: pg.sections
                        Column {
                            width: pcol.width; spacing: 4
                            readonly property var items: pg.apps.filter(a => a.group === modelData.id)
                            Text { visible: pg.group === "" && pg.sections.length > 1; text: modelData.name.toUpperCase() + "  ·  " + parent.items.length
                                   color: Theme.dim; font.family: Theme.font; font.pixelSize: 11; font.bold: true; topPadding: 2 }
                            Flow {
                                width: parent.width; spacing: 6
                                Repeater {
                                    model: parent.parent.items
                                    Rectangle {
                                        width: 128; height: 96; radius: Theme.radius
                                        color: gma.containsMouse ? Theme.hover : "transparent"
                                        Column { anchors.horizontalCenter: parent.horizontalCenter; y: 12; spacing: 6
                                            FIcon { anchors.horizontalCenter: parent.horizontalCenter; name: modelData.iconFile || ("app-" + modelData.icon); size: 42 }
                                            Text { width: 120; horizontalAlignment: Text.AlignHCenter; text: modelData.name; color: Theme.text
                                                   wrapMode: Text.Wrap; maximumLineCount: 2; elide: Text.ElideRight
                                                   font.family: Theme.font; font.pixelSize: 12 } }
                                        MouseArea { id: gma; anchors.fill: parent; hoverEnabled: true; onClicked: shell.launch(modelData.id) }
                                    }
                                }
                            }
                        }
                    }
                }
                Rectangle {   // görgetősáv
                    visible: pfl.interactive
                    x: pfl.width - 6; y: pfl.contentY + pfl.visibleArea.yPosition * pfl.height
                    width: 6; radius: 3; color: "#3a4756"
                    height: pfl.visibleArea.heightRatio * pfl.height
                }
            }
        }
    }
}
