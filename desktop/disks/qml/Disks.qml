// FusionOS — Lemezkezelő: lemezek, partíciók, állapot; formázás, címke, új partíció, törlés
// (a lemezíró műveletekhez a lemez nevét be kell gépelni; a FusionOS saját lemeze csak megtekinthető)
import QtQuick
import QtQuick.Controls
import FusionUI

FWindow {
    id: win
    width: 1000; height: 660
    minimumWidth: 760; minimumHeight: 480
    visible: true
    title: "Lemezkezelő"
    property string selDisk: ""
    property string selSeg: ""
    property string msg: ""
    property bool msgErr: false
    readonly property var list: disks.disks || []
    readonly property var disk: list.find(d => d.name === selDisk) || null
    readonly property var seg: disk ? (disk.segments.find(s => s.name === selSeg) || null) : null

    Component.onCompleted: { raise(); requestActivate() }
    Shortcut { sequence: "Esc"; onActivated: opDlg.visible ? opDlg.close() : win.close() }
    Shortcut { sequence: "F5"; onActivated: disks.reload(true) }
    Connections {
        target: disks
        function onMessage(text, isErr) {
            if (text === "__raise__") { win.show(); win.raise(); win.requestActivate(); return }
            win.msg = text; win.msgErr = isErr; msgTimer.restart()
        }
    }
    Timer { id: msgTimer; interval: 8000; onTriggered: win.msg = "" }
    onListChanged: {
        if (!disk) selDisk = (list.find(d => !d.system) || list[0] || { name: "" }).name
        if (disk && !seg) selSeg = (disk.segments[0] || { name: "" }).name
    }
    onSelDiskChanged: {
        var d = list.find(x => x.name === selDisk)
        selSeg = d ? (d.segments[0] || { name: "" }).name : ""
    }

    function kindIcon(d) { return d.kind === "usb" || d.kind === "sd" ? "drive-usb" : "drive" }
    function fsColor(s) {
        if (s.seg === "free") return "transparent"
        return ({ vfat: "#1f6feb", exfat: "#8957e5", ntfs: "#0e7490", ext4: "#238636", ext2: "#238636", ext3: "#238636",
                  erofs: "#6e7681", swap: "#9a6700" })[s.fstype] || "#4b5563"
    }

    Row {
        anchors.fill: parent
        // --- lemezlista ---
        Rectangle {
            width: 280; height: parent.height; color: Theme.panel
            Column {
                anchors.fill: parent
                Item {
                    width: parent.width; height: 44
                    Text { x: 14; anchors.verticalCenter: parent.verticalCenter; text: "LEMEZEK"; color: Theme.dim
                           font.family: Theme.font; font.pixelSize: 11; font.bold: true }
                    FToolButton { anchors.right: parent.right; anchors.rightMargin: 8; anchors.verticalCenter: parent.verticalCenter
                                  icon: "refresh"; tip: "Frissítés (F5)"; onClicked: disks.reload(true) }
                }
                ListView {
                    id: dlist
                    width: parent.width; height: parent.height - 44
                    clip: true; model: win.list
                    boundsBehavior: Flickable.StopAtBounds
                    delegate: Rectangle {
                        required property var modelData
                        width: dlist.width; height: 58
                        color: modelData.name === win.selDisk ? Theme.selected : (dma.containsMouse ? Theme.hover : "transparent")
                        FIcon { x: 14; anchors.verticalCenter: parent.verticalCenter; size: 26; name: win.kindIcon(modelData) }
                        Column {
                            x: 50; anchors.verticalCenter: parent.verticalCenter; width: parent.width - 50 - 34
                            Text { width: parent.width; text: modelData.model; elide: Text.ElideRight; color: Theme.text
                                   font.family: Theme.font; font.pixelSize: 13; font.bold: true }
                            Text { width: parent.width; elide: Text.ElideRight; color: Theme.dim; font.family: Theme.font; font.pixelSize: 11
                                   text: modelData.name + " · " + modelData.sizeText + " · " + modelData.kindText +
                                         (modelData.system ? " · FusionOS" : "") }
                        }
                        FIcon { visible: modelData.system; anchors.right: parent.right; anchors.rightMargin: 12
                                anchors.verticalCenter: parent.verticalCenter; size: 16; name: "lock" }
                        MouseArea { id: dma; anchors.fill: parent; hoverEnabled: true; onClicked: win.selDisk = modelData.name }
                    }
                    Text { anchors.centerIn: parent; width: parent.width - 40; wrapMode: Text.Wrap; horizontalAlignment: Text.AlignHCenter
                           visible: win.list.length === 0; color: disks.error ? Theme.danger : Theme.dim
                           text: disks.error || "lemezek beolvasása…"; font.family: Theme.font; font.pixelSize: 12 }
                }
            }
        }

        // --- a kijelölt lemez ---
        Flickable {
            width: parent.width - 280; height: parent.height
            contentHeight: main.implicitHeight + 24; clip: true
            boundsBehavior: Flickable.StopAtBounds
            ScrollBar.vertical: ScrollBar {}
            Column {
                id: main
                x: 20; y: 16; width: parent.width - 40; spacing: 14
                visible: !!win.disk

                // fejléc
                Item {
                    width: parent.width; height: 52
                    Column {
                        width: parent.width - dbtns.width - 12
                        Text { width: parent.width; elide: Text.ElideRight; text: win.disk ? win.disk.model : ""; color: Theme.text
                               font.family: Theme.font; font.pixelSize: 18; font.bold: true }
                        Text { width: parent.width; elide: Text.ElideRight; color: Theme.dim; font.family: Theme.font; font.pixelSize: 12
                               text: win.disk ? win.disk.path + "  ·  " + win.disk.sizeText + "  ·  " + win.disk.kindText +
                                                "  ·  " + win.disk.tableText + (win.disk.removable ? "  ·  cserélhető" : "") : "" }
                    }
                    Row {
                        id: dbtns
                        anchors.right: parent.right; spacing: 8
                        FButton { text: "Kiadás"; icon: "eject"; visible: !!win.disk && win.disk.removable && !win.disk.system
                                  enabled: !disks.busy; onClicked: disks.eject(win.disk.name) }
                        FButton { text: "Lemez formázása…"; icon: "trash"; danger: true
                                  visible: !!win.disk && !win.disk.system && !win.disk.ro
                                  enabled: !disks.busy && !win.disk.inuse
                                  tip: win.disk && win.disk.inuse ? "Nem törölhető: " + win.disk.inuse : "A teljes lemez törlése és újraformázása"
                                  onClicked: opDlg.ask("format-disk") }
                    }
                }

                // figyelmeztetések
                Rectangle {
                    visible: !!win.disk && (win.disk.system || win.disk.otheros || !!win.disk.inuse || win.disk.fusion)
                    width: parent.width; height: warnTxt.implicitHeight + 18; radius: Theme.radius
                    color: win.disk && win.disk.system ? "#1c2a3a" : "#3a2a10"
                    FIcon { x: 12; y: 9; size: 18; name: win.disk && win.disk.system ? "lock" : "info" }
                    Text {
                        id: warnTxt; x: 40; y: 9; width: parent.width - 52; wrapMode: Text.Wrap; color: Theme.text
                        font.family: Theme.font; font.pixelSize: 12
                        text: !win.disk ? "" : win.disk.system
                              ? "A FusionOS saját lemeze: csak megtekinthető. A rendszer frissítése a Beállítások → Rendszerfrissítés oldalon történik."
                              : win.disk.fusion
                              ? "Ezen a lemezen egy másik FusionOS-telepítés van (pl. régi telepítő pendrive). A FusionOS-partíciók külön nem módosíthatók; a teljes lemez törölhető."
                              : win.disk.otheros
                              ? "Ezen a lemezen EFI-partíció van — valószínűleg egy másik operációs rendszer (pl. Linux Mint, Windows) is rajta van. Csak akkor módosítsa, ha biztos benne."
                              : "Egy partícióját a rendszer használja (" + win.disk.inuse + "), ezért a lemez egésze nem törölhető."
                    }
                }

                // állapot (SMART)
                Row {
                    spacing: 10
                    visible: !!win.disk
                    Text { text: "Állapot:"; color: Theme.dim; font.family: Theme.font; font.pixelSize: 13 }
                    Text {
                        readonly property var sm: win.disk ? win.disk.smart : null
                        text: !sm ? "ellenőrzés…" : !sm.available ? "nem elérhető" + (sm.text && sm.text !== "nem elérhető" ? " — " + sm.text.replace("nem elérhető ", "") : "")
                              : sm.text + (sm.temp ? "   ·   " + sm.temp + " °C" : "") + (sm.hours ? "   ·   " + sm.hours + " üzemóra" : "") +
                                (sm.wear !== undefined ? "   ·   kopás: " + sm.wear + " %" : "")
                        color: !sm || !sm.available ? Theme.dim : sm.level === "bad" ? Theme.danger : sm.level === "warn" ? Theme.warn : Theme.ok
                        font.family: Theme.font; font.pixelSize: 13; font.bold: !!sm && sm.available
                    }
                }

                // partíciósáv
                Rectangle {
                    id: bar
                    width: parent.width; height: 70; color: Theme.base; border.color: Theme.border
                    visible: !!win.disk
                    readonly property var segs: win.disk ? win.disk.segments : []
                    readonly property real total: Math.max(1, segs.reduce((a, s) => a + s.size, 0))
                    readonly property real minW: 46
                    // arányos szélesség, de minden szakasz legalább minW (a kicsik is kattinthatók)
                    readonly property var widths: {
                        var w = bar.width - 4 - Math.max(0, segs.length - 1) * 2, n = segs.length, small = 0, rest = 0
                        if (!n) return []
                        for (var i = 0; i < n; i++) { var pw = segs[i].size / total * w; if (pw < minW) small++; else rest += segs[i].size }
                        var avail = w - small * minW
                        return segs.map(s => Math.max(minW, s.size / total * w < minW ? minW : s.size / rest * avail))
                    }
                    Row {
                        x: 2; y: 2; spacing: 2
                        Repeater {
                            model: bar.segs
                            Rectangle {
                                required property var modelData
                                required property int index
                                width: bar.widths[index] || 0; height: 66
                                color: modelData.seg === "free" ? Theme.bg : win.fsColor(modelData)
                                border.width: modelData.name === win.selSeg ? 2 : (modelData.seg === "free" ? 1 : 0)
                                border.color: modelData.name === win.selSeg ? "white" : Theme.border
                                opacity: modelData.seg === "free" || modelData.mountpoint || win.disk.system ? 1 : 0.8
                                Column {
                                    anchors.fill: parent; anchors.margins: 6; spacing: 2; clip: true
                                    Text { width: parent.width; elide: Text.ElideRight; text: modelData.title
                                           color: modelData.seg === "free" ? Theme.dim : "white"; font.family: Theme.font; font.pixelSize: 12; font.bold: true }
                                    Text { width: parent.width; elide: Text.ElideRight; text: modelData.sizeText
                                           color: modelData.seg === "free" ? Theme.dim : "#e0e0e0"; font.family: Theme.font; font.pixelSize: 11 }
                                    Text { width: parent.width; elide: Text.ElideRight; visible: modelData.seg !== "free"
                                           text: (modelData.fsText || "") ; color: "#d0d0d0"; font.family: Theme.font; font.pixelSize: 10 }
                                }
                                MouseArea { anchors.fill: parent; onClicked: win.selSeg = modelData.name }
                            }
                        }
                    }
                    Text { anchors.centerIn: parent; visible: bar.segs.length === 0; color: Theme.dim; font.family: Theme.font; font.pixelSize: 12
                           text: win.disk && win.disk.fstype ? "partíciós tábla nélküli kötet: " + win.disk.fstype + (win.disk.label ? " (" + win.disk.label + ")" : "")
                                                             : "üres lemez — nincs partíciós tábla" }
                }

                // a kijelölt partíció / szabad terület
                Rectangle {
                    width: parent.width; height: det.implicitHeight + 24; color: Theme.panel; radius: Theme.radius
                    visible: !!win.seg
                    Column {
                        id: det
                        x: 16; y: 12; width: parent.width - 32; spacing: 6
                        Text { text: win.seg ? win.seg.title : ""; color: Theme.text; font.family: Theme.font; font.pixelSize: 15; font.bold: true }
                        Repeater {
                            model: !win.seg ? [] : win.seg.seg === "free"
                                   ? [["Méret", win.seg.sizeText], ["Hely", "a lemez " + Math.round(win.seg.start / 1048576) + " MiB-tól"]]
                                   : [["Eszköz", win.seg.path + (win.seg.partlabel && win.seg.partlabel !== win.seg.title ? "   (partíciónév: " + win.seg.partlabel + ")" : "")],
                                      ["Fájlrendszer", win.seg.fsText + (win.seg.label ? "   ·   címke: " + win.seg.label : "")],
                                      ["Méret", win.seg.sizeText],
                                      ["Foglaltság", win.seg.usedText || (win.seg.mountpoint || !win.seg.mountable ? "—" : "csatolás után látszik")],
                                      ["Csatolva", win.seg.mountpoint || "nincs csatolva"]].concat(
                                      win.seg.locked ? [["Védett", win.seg.locked]] : [])
                            Row {
                                spacing: 10
                                Text { width: 110; text: modelData[0]; color: Theme.dim; font.family: Theme.font; font.pixelSize: 12 }
                                Text { width: det.width - 120; text: modelData[1]; color: modelData[0] === "Védett" ? Theme.warn : Theme.text
                                       wrapMode: Text.Wrap; font.family: Theme.font; font.pixelSize: 12 }
                            }
                        }
                        Rectangle {
                            visible: !!win.seg && win.seg.usedPct >= 0
                            width: Math.min(det.width, 420); height: 8; radius: 4; color: Theme.base
                            Rectangle { width: parent.width * Math.max(0, (win.seg && win.seg.usedPct) || 0); height: parent.height; radius: 4
                                        color: win.seg && win.seg.usedPct > 0.9 ? Theme.danger : Theme.accent }
                        }
                        Item { width: 1; height: 4 }
                        Flow {
                            width: det.width; spacing: 8
                            visible: !!win.seg && !win.disk.system
                            FButton { text: "Megnyitás"; icon: "files"; visible: !!win.seg && !!win.seg.mountpoint
                                      onClicked: disks.openFiles(win.seg.mountpoint) }
                            FButton { text: "Csatolás"; icon: "drive"; visible: !!win.seg && win.seg.seg === "part" && win.seg.mountable && !win.seg.mountpoint
                                      enabled: !disks.busy; onClicked: disks.mount(win.seg.name) }
                            FButton { text: "Leválasztás"; icon: "eject"; visible: !!win.seg && win.seg.seg === "part" && !!win.seg.media
                                      enabled: !disks.busy; onClicked: disks.unmount(win.seg.name) }
                            FButton { text: "Átnevezés…"; icon: "edit"
                                      visible: !!win.seg && win.seg.seg === "part" && win.seg.editable && ["vfat", "exfat", "ntfs", "ext2", "ext3", "ext4"].indexOf(win.seg.fstype) >= 0
                                      enabled: !disks.busy; onClicked: opDlg.ask("label") }
                            FButton { text: "Formázás…"; icon: "trash"; danger: true; visible: !!win.seg && win.seg.seg === "part" && win.seg.editable
                                      enabled: !disks.busy; onClicked: opDlg.ask("format") }
                            FButton { text: "Partíció törlése…"; icon: "minus"; danger: true; visible: !!win.seg && win.seg.seg === "part" && win.seg.editable
                                      enabled: !disks.busy; onClicked: opDlg.ask("delete") }
                            FButton { text: "Új partíció…"; icon: "plus"; primary: true; visible: !!win.seg && win.seg.seg === "free" && win.seg.editable
                                      enabled: !disks.busy && !(win.disk.table === "dos" && (win.disk.primaryFull || win.disk.hasExtended))
                                      tip: win.disk && win.disk.table === "dos" && (win.disk.primaryFull || win.disk.hasExtended) ? "MBR-lemez: legfeljebb 4 elsődleges partíció" : ""
                                      onClicked: opDlg.ask("create") }
                        }
                    }
                }

                // folyamatban lévő / utolsó művelet
                Rectangle {
                    visible: disks.busy !== "" || disks.log.length > 0
                    width: parent.width; height: logCol.implicitHeight + 16; color: Theme.base; border.color: Theme.border
                    Column {
                        id: logCol; x: 12; y: 8; width: parent.width - 24
                        Text { visible: disks.busy !== ""; text: "Folyamatban: " + disks.busy + " …"; color: Theme.mark
                               font.family: Theme.font; font.pixelSize: 12; font.bold: true }
                        Repeater {
                            model: disks.log
                            Text { width: logCol.width; text: modelData; elide: Text.ElideRight; textFormat: Text.PlainText
                                   color: /hiba|nem |sikertelen|egyezik|foglalt/i.test(modelData) ? Theme.danger : Theme.dim
                                   font.family: Theme.mono; font.pixelSize: 11 }
                        }
                    }
                }
                Text { visible: win.msg !== ""; text: win.msg; color: win.msgErr ? Theme.danger : Theme.ok
                       width: parent.width; wrapMode: Text.Wrap; font.family: Theme.font; font.pixelSize: 12 }
            }
        }
    }

    // --- műveleti párbeszédablak ---------------------------------------------------------------
    FDialog {
        id: opDlg
        property string op: ""
        property string fs: "exfat"
        property string table: "gpt"
        property string label: ""
        property int sizeMiB: 0
        property int maxMiB: 0
        property int startMiB: 0
        readonly property bool destructive: op !== "label"
        readonly property bool fsOp: op === "format-disk" || op === "format" || op === "create"
        readonly property string target: win.disk ? win.disk.name : ""
        readonly property bool confirmOk: !destructive || confirmField.text.trim() === target
        function ask(o) {
            op = o
            var removable = win.disk && win.disk.removable
            fs = o === "format" && win.seg && ["vfat", "exfat", "ntfs", "ext4"].indexOf(win.seg.fstype) >= 0 ? win.seg.fstype
               : removable ? "exfat" : "ext4"
            table = removable && win.disk.size <= 2199023255552 ? "dos" : "gpt"
            label = o === "label" || o === "format" ? (win.seg.label || "") : ""
            if (o === "create") {
                startMiB = Math.round(win.seg.start / 1048576)
                maxMiB = Math.floor(win.seg.size / 1048576)
                sizeMiB = maxMiB
                sizeField.text = String(maxMiB)
            }
            labelField.text = label
            confirmField.text = ""
            open()
            if (o === "label") labelField.forceActiveFocus(); else confirmField.forceActiveFocus()
        }
        title: ({ "format-disk": "Lemez formázása", "format": "Partíció formázása", "label": "Átnevezés",
                  "create": "Új partíció", "delete": "Partíció törlése" })[op] || ""
        buttons: [["Mégse", ""], [({ "format-disk": "Lemez törlése és formázása", "format": "Formázás", "label": "Mentés",
                                     "create": "Létrehozás", "delete": "Törlés" })[op] || "OK", op === "label" || op === "create" ? "primary" : "danger"]]
        onButtonClicked: (i) => {
            if (i === 0) { close(); return }
            if (!confirmOk) { confirmField.forceActiveFocus(); return }
            var c = confirmField.text.trim(), l = labelField.text
            if (op === "format-disk") disks.formatDisk(target, table, fs, l, c)
            else if (op === "format") disks.formatPart(win.seg.name, fs, l, c)
            else if (op === "label") disks.setLabel(win.seg.name, l)
            else if (op === "create") {
                var n = parseInt(sizeField.text)
                if (!(n > 0 && n <= maxMiB)) { sizeField.forceActiveFocus(); return }
                disks.create(target, startMiB, n, fs, l, c)
            }
            else if (op === "delete") disks.delete(win.seg.name, c)
            close()
        }
        Column {
            x: 20; y: 16; width: 520; spacing: 12
            Text {
                width: parent.width; wrapMode: Text.Wrap; color: opDlg.destructive && opDlg.op !== "create" ? Theme.danger : Theme.text
                font.family: Theme.font; font.pixelSize: 13; font.bold: opDlg.destructive && opDlg.op !== "create"
                text: !win.disk ? "" : opDlg.op === "format-disk"
                      ? "A(z) " + win.disk.model + " (" + win.disk.name + ", " + win.disk.sizeText + ") ÖSSZES adata és partíciója törlődik."
                      : opDlg.op === "format" ? "A(z) " + (win.seg ? win.seg.title + " (" + win.seg.name + ")" : "") + " partíció összes adata törlődik."
                      : opDlg.op === "delete" ? "A(z) " + (win.seg ? win.seg.title + " (" + win.seg.name + ", " + win.seg.sizeText + ")" : "") + " partíció és a rajta lévő adatok törlődnek."
                      : opDlg.op === "create" ? "Új partíció a szabad területen (" + (win.seg ? win.seg.sizeText : "") + "). A többi partíció nem változik."
                      : "A kötet új neve (a Fájlkezelőben és más gépeken is ez látszik)."
            }
            // partíciós tábla
            Column {
                visible: opDlg.op === "format-disk"; spacing: 6
                Text { text: "Partíciós tábla"; color: Theme.dim; font.family: Theme.font; font.pixelSize: 12 }
                Row {
                    spacing: 6
                    FButton { text: "MBR"; checked: opDlg.table === "dos"; onClicked: opDlg.table = "dos"
                              tip: "régebbi eszközök is olvassák (autórádió, nyomtató, 3D-nyomtató); legfeljebb 2 TB" }
                    FButton { text: "GPT"; checked: opDlg.table === "gpt"; onClicked: opDlg.table = "gpt"
                              tip: "korszerű; nagy lemezekhez és belső lemezhez" }
                }
            }
            // fájlrendszer
            Column {
                visible: opDlg.fsOp; spacing: 6; width: parent.width
                Text { text: "Fájlrendszer"; color: Theme.dim; font.family: Theme.font; font.pixelSize: 12 }
                Flow {
                    width: parent.width; spacing: 6
                    Repeater {
                        model: [["vfat", "FAT32"], ["exfat", "exFAT"], ["ntfs", "NTFS"], ["ext4", "ext4"]].concat(
                               opDlg.op === "format-disk" ? [["none", "Üres (partíció nélkül)"]] : [])
                        FButton { text: modelData[1]; checked: opDlg.fs === modelData[0]; onClicked: opDlg.fs = modelData[0] }
                    }
                }
                Text {
                    width: parent.width; wrapMode: Text.Wrap; color: Theme.dim; font.family: Theme.font; font.pixelSize: 11
                    text: ({ vfat: "Minden eszköz olvassa (Windows, Mac, régi készülékek, 3D-nyomtató, lézer). Egy fájl legfeljebb 4 GB; a címke legfeljebb 11 karakter, ékezet nélkül.",
                             exfat: "Pendrive-ra ajánlott: nagy fájlok, Windows és Mac is olvassa.",
                             ntfs: "Windows-lemez; a FusionOS is írja-olvassa.",
                             ext4: "Linux / FusionOS adatlemez; Windows alatt nem olvasható.",
                             none: "Csak üres partíciós tábla; a partíciókat utána hozhatja létre." })[opDlg.fs] || ""
                }
            }
            // méret
            Column {
                visible: opDlg.op === "create"; spacing: 6
                Text { text: "Méret (MiB, legfeljebb " + opDlg.maxMiB + ")"; color: Theme.dim; font.family: Theme.font; font.pixelSize: 12 }
                FTextField { id: sizeField; width: 160; validator: IntValidator { bottom: 1; top: opDlg.maxMiB } }
            }
            // címke
            Column {
                visible: opDlg.fsOp && opDlg.fs !== "none" || opDlg.op === "label"; spacing: 6
                Text { text: "Címke (kötetnév)"; color: Theme.dim; font.family: Theme.font; font.pixelSize: 12 }
                FTextField { id: labelField; width: 260; maximumLength: 32 }
            }
            // megerősítés
            Column {
                visible: opDlg.destructive; spacing: 6; width: parent.width
                Text { width: parent.width; wrapMode: Text.Wrap; color: Theme.text; font.family: Theme.font; font.pixelSize: 12
                       text: "Megerősítéshez írja be a lemez nevét: <b>" + opDlg.target + "</b>"; textFormat: Text.StyledText }
                FTextField { id: confirmField; width: 160
                             color: opDlg.confirmOk ? Theme.ok : Theme.text }
            }
        }
    }
}
