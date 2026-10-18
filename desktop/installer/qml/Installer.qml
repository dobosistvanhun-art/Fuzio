// Fúzió — Fúzió Telepítő: céllemez, mód (új telepítés / a DATA megőrzésével), megerősítés, telepítés
import QtQuick
import QtQuick.Controls
import FusionUI

FWindow {
    id: win
    width: 1100; height: 720
    minimumWidth: 860; minimumHeight: 560
    visible: true
    visibility: Window.Maximized
    title: "Fúzió telepítő"
    property int page: 0                  // 0 üdvözlés, 1 céllemez, 2 mód, 3 megerősítés, 4 telepítés
    property string target: ""
    property string mode: "new"
    property string msg: ""
    property string restore: ""           // mentés (új telepítéskor): a fájl útvonala
    property bool wifi: true
    readonly property var d: inst.data || ({ disks: [], payload: {}, machine: {} })
    readonly property var pay: d.payload || ({})
    readonly property var mach: d.machine || ({})
    readonly property var disk: (d.disks || []).find(x => x.name === target) || null
    readonly property var backup: (d.backups || []).find(b => b.path === restore) || null
    readonly property bool wifiAvail: (d.wifi || []).length > 0
    readonly property bool payOk: !!pay.version && !pay.error
    readonly property var pages: ["Üdvözlés", "Céllemez", "Telepítés módja", "Megerősítés", "Telepítés"]

    onPageChanged: if (page === 3) confirmField.text = ""

    Row {
        anchors.fill: parent
        // --- lépések ---
        Rectangle {
            width: 250; height: parent.height; color: Theme.panel
            Column {
                x: 20; y: 24; width: parent.width - 40; spacing: 6
                Row {
                    spacing: 10
                    FIcon { name: "app-disks"; size: 30 }
                    Column {
                        anchors.verticalCenter: parent.verticalCenter
                        Text { text: "Fúzió"; color: Theme.text; font.family: Theme.font; font.pixelSize: 17; font.bold: true }
                        Text { text: "telepítő"; color: Theme.dim; font.family: Theme.font; font.pixelSize: 12 }
                    }
                }
                Item { width: 1; height: 20 }
                Repeater {
                    model: win.pages
                    Row {
                        spacing: 10; height: 30
                        Rectangle { width: 22; height: 22; radius: 11; anchors.verticalCenter: parent.verticalCenter
                                    color: index < win.page ? Theme.ok : index === win.page ? Theme.accent : "transparent"
                                    border.color: index <= win.page ? "transparent" : Theme.border
                                    Text { anchors.centerIn: parent; text: index < win.page ? "✓" : index + 1; color: index <= win.page ? "white" : Theme.dim
                                           font.family: Theme.font; font.pixelSize: 11; font.bold: true } }
                        Text { anchors.verticalCenter: parent.verticalCenter; text: modelData
                               color: index === win.page ? Theme.text : Theme.dim; font.family: Theme.font; font.pixelSize: 13
                               font.bold: index === win.page }
                    }
                }
            }
            Column {
                anchors.bottom: parent.bottom; anchors.bottomMargin: 20; x: 20; width: parent.width - 40; spacing: 6
                Text { text: "ESZKÖZÖK"; color: Theme.dim; font.family: Theme.font; font.pixelSize: 11; font.bold: true }
                FButton { width: parent.width; text: "Lemezkezelő"; icon: "disks"; onClicked: inst.tool("disks") }
                FButton { width: parent.width; text: "Wi-Fi"; icon: "wifi"; onClicked: inst.tool("wifi") }
                FButton { width: parent.width; text: "Terminál"; icon: "terminal"; onClicked: inst.tool("terminal") }
                FButton { width: parent.width; text: "Újraindítás"; icon: "restart"; enabled: inst.state !== "running"; onClicked: inst.power("reboot") }
                FButton { width: parent.width; text: "Kikapcsolás"; icon: "power"; enabled: inst.state !== "running"; onClicked: inst.power("poweroff") }
            }
        }

        // --- tartalom ---
        Item {
            width: parent.width - 250; height: parent.height
            Flickable {
                anchors.fill: parent; anchors.bottomMargin: 70
                contentHeight: body.implicitHeight + 40; clip: true
                boundsBehavior: Flickable.StopAtBounds
                ScrollBar.vertical: ScrollBar {}
                Column {
                    id: body
                    x: 36; y: 30; width: parent.width - 72; spacing: 16

                    Text { text: win.pages[win.page]; color: Theme.text; font.family: Theme.font; font.pixelSize: 22; font.bold: true }

                    // 0 — üdvözlés
                    Column {
                        visible: win.page === 0; width: parent.width; spacing: 14
                        Text { width: parent.width; wrapMode: Text.Wrap; color: Theme.text; font.family: Theme.font; font.pixelSize: 14
                               text: "A Fúzió telepítése egy lemezre — új telepítés, vagy egy meglévő Fúzió újratelepítése a programok és beállítások megtartásával." }
                        Rectangle {
                            width: parent.width; height: infoCol.implicitHeight + 24; color: Theme.panel; radius: Theme.radius
                            Column {
                                id: infoCol; x: 16; y: 12; width: parent.width - 32; spacing: 6
                                Repeater {
                                    model: [["Telepítendő rendszer", win.payOk ? "Fúzió " + win.pay.version + (win.pay.milestone ? " (" + win.pay.milestone + ")" : "") + "   ·   " + win.pay.name
                                                                               : (inst.loading ? "beolvasás…" : "HIBA: " + (win.pay.error || "nincs csomag"))],
                                            ["Gép", win.mach.model || "…"],
                                            ["Memória", win.mach.memoryText || "…"],
                                            ["Kijelző", win.mach.display || "…"],
                                            ["Áramellátás", win.mach.ac === true ? "töltő csatlakoztatva" : win.mach.ac === false ? "AKKUMULÁTORRÓL (" + win.mach.batteryPct + " %) — csatlakoztassa a töltőt!" : "asztali gép / ismeretlen"]]
                                    Row {
                                        spacing: 12
                                        Text { width: 170; text: modelData[0]; color: Theme.dim; font.family: Theme.font; font.pixelSize: 13 }
                                        Text { width: infoCol.width - 182; text: modelData[1]; wrapMode: Text.Wrap; font.family: Theme.font; font.pixelSize: 13
                                               color: /HIBA|AKKU/.test(modelData[1]) ? Theme.danger : Theme.text }
                                    }
                                }
                            }
                        }
                        Text { width: parent.width; wrapMode: Text.Wrap; color: Theme.dim; font.family: Theme.font; font.pixelSize: 12
                               text: "A telepítő a pendrive-ra nem ír (a változások csak a memóriában vannak). Internet nem kell. " +
                                     "A telepítés kb. 5–10 perc." }
                    }

                    // 1 — céllemez
                    Column {
                        visible: win.page === 1; width: parent.width; spacing: 8
                        Text { width: parent.width; wrapMode: Text.Wrap; color: Theme.dim; font.family: Theme.font; font.pixelSize: 13
                               text: "Melyik lemezre kerüljön a Fúzió? (legalább 10 GiB)" }
                        Repeater {
                            model: win.d.disks
                            Rectangle {
                                width: body.width; height: 66; radius: Theme.radius
                                color: modelData.name === win.target ? Theme.selected : (dma.containsMouse && modelData.eligible ? Theme.hover : Theme.panel)
                                border.color: modelData.name === win.target ? Theme.accent : "transparent"
                                opacity: modelData.eligible ? 1 : 0.5
                                FIcon { x: 16; anchors.verticalCenter: parent.verticalCenter; size: 28
                                        name: modelData.kind === "usb" || modelData.kind === "sd" ? "drive-usb" : "drive" }
                                Column {
                                    x: 58; anchors.verticalCenter: parent.verticalCenter; width: parent.width - 70
                                    Text { width: parent.width; elide: Text.ElideRight; color: Theme.text; font.family: Theme.font; font.pixelSize: 14; font.bold: true
                                           text: modelData.model + "   ·   " + modelData.name + "   ·   " + modelData.sizeText + "   ·   " + modelData.kindText }
                                    Text { width: parent.width; elide: Text.ElideRight; font.family: Theme.font; font.pixelSize: 12
                                           color: !modelData.eligible ? Theme.dim : modelData.otheros ? Theme.warn : Theme.dim
                                           text: modelData.eligible ? modelData.content : "nem választható: " + modelData.reason }
                                }
                                MouseArea { id: dma; anchors.fill: parent; hoverEnabled: true; enabled: modelData.eligible
                                            onClicked: { win.target = modelData.name; win.mode = modelData.keepData ? "keep-data" : "new" } }
                            }
                        }
                        Text { visible: (win.d.disks || []).length === 0; text: inst.loading ? "lemezek beolvasása…" : (win.d.error || "nincs lemez")
                               color: Theme.dim; font.family: Theme.font; font.pixelSize: 13 }
                        FButton { text: "Lista frissítése"; icon: "refresh"; onClicked: inst.refresh() }
                    }

                    // 2 — mód
                    Column {
                        visible: win.page === 2; width: parent.width; spacing: 10
                        Repeater {
                            model: [["keep-data", "Újratelepítés, a DATA megőrzésével",
                                     "A rendszer újraíródik, a programok (pl. LightBurn), a Wi-Fi, a beállítások és a saját fájlok MEGMARADNAK. Ha a Fúzió elromlott, ez a helyreállítás."],
                                    ["new", "Új telepítés",
                                     "A lemez TELJES tartalma törlődik; tiszta Fúzió kerül rá — üres DATA-val, vagy a DATA egy mentésből (lent)."]]
                            Rectangle {
                                readonly property bool avail: modelData[0] === "new" || (!!win.disk && win.disk.keepData)
                                width: body.width; height: mcol.implicitHeight + 24; radius: Theme.radius
                                color: win.mode === modelData[0] ? Theme.selected : Theme.panel
                                border.color: win.mode === modelData[0] ? Theme.accent : "transparent"
                                opacity: avail ? 1 : 0.5
                                Column {
                                    id: mcol; x: 16; y: 12; width: parent.width - 32; spacing: 4
                                    Text { text: modelData[1]; color: Theme.text; font.family: Theme.font; font.pixelSize: 15; font.bold: true }
                                    Text { width: parent.width; wrapMode: Text.Wrap; color: Theme.dim; font.family: Theme.font; font.pixelSize: 12
                                           text: parent.parent.avail ? modelData[2]
                                                 : "Csak meglévő Fúzió-lemezen" + (win.disk && win.disk.fusion && win.disk.fusion.reason ? " (" + win.disk.fusion.reason + ")" : "") + "." }
                                }
                                MouseArea { anchors.fill: parent; enabled: parent.avail; onClicked: win.mode = modelData[0] }
                            }
                        }
                        // új telepítés: a DATA egy mentésből (T3), Wi-Fi átvétele
                        Column {
                            visible: win.mode === "new"; width: parent.width; spacing: 8; topPadding: 8
                            Text { text: "DATA AZ ÚJ TELEPÍTÉSHEZ"; color: Theme.dim; font.family: Theme.font; font.pixelSize: 11; font.bold: true }
                            Repeater {
                                model: [{ path: "", title: "Üres DATA (tiszta rendszer)", sub: "a programokat és a beállításokat újra kell telepíteni / megadni" }].concat(
                                       (win.d.backups || []).map(b => ({ path: b.path, title: "Visszaállítás mentésből: " + b.when + " (Fúzió " + b.version + ")",
                                                                         sub: b.where + "   ·   " + b.sizeText + " tömörítve, " + b.dataText + " adat" })))
                                Rectangle {
                                    width: body.width; height: 50; radius: Theme.radius
                                    color: win.restore === modelData.path ? Theme.selected : (rma.containsMouse ? Theme.hover : Theme.panel)
                                    border.color: win.restore === modelData.path ? Theme.accent : "transparent"
                                    MouseArea { id: rma; anchors.fill: parent; hoverEnabled: true; onClicked: win.restore = modelData.path }
                                    Column {
                                        x: 16; anchors.verticalCenter: parent.verticalCenter; width: parent.width - 32
                                        Text { text: modelData.title; color: Theme.text; font.family: Theme.font; font.pixelSize: 13; font.bold: true }
                                        Text { text: modelData.sub; color: Theme.dim; font.family: Theme.font; font.pixelSize: 11; elide: Text.ElideRight; width: parent.width }
                                    }
                                }
                            }
                            Text { width: parent.width; wrapMode: Text.Wrap; color: Theme.dim; font.family: Theme.font; font.pixelSize: 11
                                   text: "Mentés: Fúzió → Beállítások → Mentés. A mentést tartalmazó lemezt dugja be, majd: Céllemez → Lista frissítése." }
                            FCheck { visible: win.wifiAvail; checked: win.wifi; onToggled: win.wifi = checked
                                     text: "A telepítőben beállított Wi-Fi átvétele (" + (win.d.wifi || []).join(", ") + ")" }
                        }
                    }

                    // 3 — megerősítés
                    Column {
                        visible: win.page === 3; width: parent.width; spacing: 12
                        Rectangle {
                            width: parent.width; height: sumCol.implicitHeight + 24; color: Theme.panel; radius: Theme.radius
                            Column {
                                id: sumCol; x: 16; y: 12; width: parent.width - 32; spacing: 6
                                Repeater {
                                    model: !win.disk ? [] : [["Rendszer", "Fúzió " + (win.pay.version || "?") + (win.pay.milestone ? " (" + win.pay.milestone + ")" : "")],
                                                             ["Céllemez", win.disk.model + " — " + win.disk.name + ", " + win.disk.sizeText],
                                                             ["Most rajta", win.disk.content],
                                                             ["Mód", win.mode === "new" ? "új telepítés — a lemez TELJES tartalma törlődik" : "újratelepítés — a DATA megmarad"]].concat(
                                                             win.mode === "new" ? [["DATA", win.backup ? "visszaállítás mentésből: " + win.backup.when + " (" + win.backup.where + ")" : "üres"]] : []).concat(
                                                             win.mode === "new" && win.wifiAvail && win.wifi ? [["Wi-Fi", "átvétel: " + (win.d.wifi || []).join(", ")]] : [])
                                    Row {
                                        spacing: 12
                                        Text { width: 120; text: modelData[0]; color: Theme.dim; font.family: Theme.font; font.pixelSize: 13 }
                                        Text { width: sumCol.width - 132; text: modelData[1]; wrapMode: Text.Wrap; font.family: Theme.font; font.pixelSize: 13
                                               color: /TELJES/.test(modelData[1]) ? Theme.danger : Theme.text }
                                    }
                                }
                            }
                        }
                        Rectangle {
                            visible: !!win.disk && win.mode === "new" && (win.disk.otheros || !!win.disk.fusion)
                            width: parent.width; height: wt.implicitHeight + 20; color: "#3a1515"; radius: Theme.radius
                            Text { id: wt; x: 14; y: 10; width: parent.width - 28; wrapMode: Text.Wrap; color: Theme.text; font.family: Theme.font; font.pixelSize: 13
                                   text: win.disk && win.disk.fusion ? "Ezen a lemezen most Fúzió van — az új telepítés a programokat és a beállításokat is TÖRLI. Ha meg akarja tartani őket: Vissza → „Újratelepítés, a DATA megőrzésével”."
                                                                     : "Ezen a lemezen egy másik operációs rendszer van (pl. Linux Mint vagy Windows) — az is TÖRLŐDIK." }
                        }
                        Text { width: parent.width; wrapMode: Text.Wrap; color: Theme.text; font.family: Theme.font; font.pixelSize: 13; textFormat: Text.StyledText
                               text: "Megerősítéshez írja be a lemez nevét: <b>" + win.target + "</b>" }
                        FTextField { id: confirmField; width: 200; color: text.trim() === win.target ? Theme.ok : Theme.text }
                    }

                    // 4 — telepítés
                    Column {
                        visible: win.page === 4; width: parent.width; spacing: 12
                        Text { width: parent.width; wrapMode: Text.Wrap; font.family: Theme.font; font.pixelSize: 15; font.bold: true
                               color: inst.state === "failed" ? Theme.danger : inst.state === "done" ? Theme.ok : Theme.text
                               text: inst.state === "done" ? "A telepítés sikerült." : inst.state === "failed" ? "A telepítés nem sikerült." : (inst.stepText || "…") }
                        Rectangle {
                            width: parent.width; height: 12; radius: 6; color: Theme.base
                            Rectangle { width: parent.width * inst.percent / 100; height: parent.height; radius: 6
                                        color: inst.state === "failed" ? Theme.danger : inst.state === "done" ? Theme.ok : Theme.accent }
                        }
                        Text { visible: inst.state === "done"; width: parent.width; wrapMode: Text.Wrap; color: Theme.text; font.family: Theme.font; font.pixelSize: 14
                               text: "Vegye ki a telepítő pendrive-ot, majd indítsa újra a gépet. A Fúzió a boot menüből (ZBook: F9) is választható." }
                        Row {
                            spacing: 8; visible: inst.state === "done" || inst.state === "failed"
                            FButton { visible: inst.state === "done"; text: "Újraindítás"; icon: "restart"; primary: true; onClicked: inst.power("reboot") }
                            FButton { visible: inst.state === "failed"; text: "Hibajelentés a pendrive-ra"; icon: "report"; onClicked: win.msg = inst.report() }
                            FButton { visible: inst.state === "failed"; text: "Vissza"; onClicked: { win.page = 1; inst.refresh() } }
                        }
                        Text { visible: win.msg !== ""; width: parent.width; wrapMode: Text.Wrap; text: win.msg; color: Theme.dim
                               font.family: Theme.font; font.pixelSize: 12 }
                        Rectangle {
                            width: parent.width; height: 300; color: Theme.base; border.color: Theme.border
                            ListView {
                                id: logView; anchors.fill: parent; anchors.margins: 8; clip: true
                                model: inst.log
                                onCountChanged: positionViewAtEnd()
                                delegate: Text { width: logView.width; text: modelData; wrapMode: Text.Wrap; textFormat: Text.PlainText
                                                 color: /^HIBA|FIGYELEM/.test(modelData) ? Theme.danger : /^LÉPÉS|^KÉSZ/.test(modelData) ? Theme.text : Theme.dim
                                                 font.family: Theme.mono; font.pixelSize: 12 }
                            }
                        }
                    }
                }
            }

            // --- navigáció ---
            Rectangle {
                anchors.bottom: parent.bottom; width: parent.width; height: 70; color: Theme.bg
                Rectangle { width: parent.width; height: 1; color: Theme.border }
                Row {
                    anchors.right: parent.right; anchors.rightMargin: 36; anchors.verticalCenter: parent.verticalCenter; spacing: 10
                    FButton { text: "Vissza"; visible: win.page > 0 && win.page < 4; onClicked: win.page-- }
                    FButton {
                        visible: win.page < 3
                        text: "Tovább"; primary: true
                        enabled: win.page === 0 ? win.payOk : win.page === 1 ? !!win.disk : true
                        onClicked: win.page++
                    }
                    FButton {
                        visible: win.page === 3
                        text: win.mode === "new" ? "Telepítés (a lemez törlődik)" : "Újratelepítés"; danger: true
                        enabled: !!win.disk && confirmField.text.trim() === win.target
                        onClicked: { win.page = 4; win.msg = ""
                                     inst.install(win.target, win.mode, confirmField.text.trim(), win.mode === "new" ? win.restore : "",
                                                  win.mode === "new" && win.wifiAvail && win.wifi) }
                    }
                }
            }
        }
    }
}
