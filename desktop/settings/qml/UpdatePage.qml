// Rendszerfrissítés (M7): a futó rendszer és a két slot állapota, frissítés .fupd fájlból
// (Letöltések, pendrive, /data/import). A frissítés a NEM futó slotba kerül, próbaként indul;
// ha rendben elindul, véglegesül — ha háromszor nem, magától a mostani rendszer indul.
import QtQuick
import QtQuick.Controls
import FusionUI

SettingsPage {
    id: p
    title: "Rendszerfrissítés"
    subtitle: "A Fúzió frissítése fájlból (.fupd) — a frissítés a másik rendszer-slotba kerül, a mostani tartalék marad"
    property var s: ({ entries: [], files: [], version: "", slot: "", state: "" })
    property var job: ({ running: false, lines: [], rc: null, title: "" })
    property string msg: ""
    property string chosen: ""
    property bool pending: false
    property bool searching: false          // a csatolt kötetek (pendrive, Tárhely) keresése még tart
    property var mjob: ({ running: false, lines: [], rc: null, title: "" })
    property var mdisks: []
    // 0.0.69: új változat a forrásból (fusion-dev rebuild)
    property var rjob: ({ running: false, lines: [], rc: null, title: "", step: {}, progress: null })
    property var rcheck: null               // az ellenőrzés eredménye (a párbeszédablakban)
    property bool rasked: false             // a „Telepítsem most?” kérdés egy buildnél egyszer jön
    busy: job.running
    onRefresh: settings.updateRefresh()
    Component.onCompleted: { settings.updateRefresh(); settings.updateJobWatch(); settings.mediaJobWatch(); settings.rebuildJobWatch() }
    Timer { interval: 8000; running: p.visible && !p.job.running; repeat: true; onTriggered: settings.updateRefresh() }
    Connections {
        target: settings
        function onResult(tag, r) {
            if (tag === "update" && r.version !== undefined) {
                r.files = p.s.files || []
                p.s = r
                if (r.job && !p.job.running) p.job = r.job
            } else if (tag === "update-files" && r.files !== undefined) {
                var n = Object.assign({}, p.s); n.files = r.files; p.s = n
                p.searching = r.partial === true
                if (p.chosen && !r.files.find(f => f.path === p.chosen)) p.chosen = ""
                if (!p.chosen && r.files.length && r.files[0].newer) p.chosen = r.files[0].path
            } else if (tag === "media-job") {
                p.mjob = r
            } else if (tag === "media-disks") {
                p.mdisks = r.disks
            } else if (tag === "rebuild-check") {
                p.rcheck = r
            } else if (tag === "rebuild-job") {
                var wasR = p.rjob.running
                p.rjob = r
                if (wasR && !r.running) {
                    settings.updateRefresh()
                    if (r.rc === 0 && !p.rasked) {
                        p.rasked = true
                        installAsk.fupd = settings.rebuildFupd()
                        if (installAsk.fupd) installAsk.open()
                    }
                }
            } else if (tag === "update-job") {
                var was = p.job.running || p.pending
                p.job = r
                if (was && !r.running) { p.pending = false; settings.updateRefresh() }
            }
        }
    }
    function stateText(e) {
        return e.state === "bad" ? "nem indult el (hibás)" : e.state === "trial" ? "próba — még " + e.left + " indítási lehetőség" : "véglegesített"
    }
    readonly property bool done: !job.running && job.rc === 0 && job.recent === true

    Section {
        title: "FUTÓ RENDSZER"
        InfoRow { icon: "chip"; label: "Verzió"; value: "Fúzió " + p.s.version + (p.s.milestone ? " (" + p.s.milestone + ")" : "") + "   ·   slot: " + p.s.slot }
        InfoRow { label: "Indulás"; value: p.s.state || "—"; mono: true
                  valueColor: /^HIBA/.test(p.s.state) ? Theme.danger : /^VÉGLEGESÍTVE/.test(p.s.state) ? Theme.ok : Theme.text }
        InfoRow { visible: p.s.error !== undefined && p.s.error !== ""; label: "Hiba"; value: p.s.error || ""; valueColor: Theme.danger }
    }
    Section {
        title: "RENDSZER-SLOTOK (BOOT MENÜ)"
        Repeater {
            model: p.s.entries
            InfoRow {
                icon: modelData.running ? "check" : ""
                label: "Slot " + modelData.slot + (modelData.running ? " — fut" : "")
                value: "Fúzió " + modelData.version + "   ·   " + p.stateText(modelData) + "\n" + modelData.name
                valueColor: modelData.state === "bad" ? Theme.danger : Theme.text
            }
        }
        InfoRow { visible: p.s.entries.length === 0; label: "—"; value: "nincs adat (a lista root-jogot igényel: fusion-admin update-status)" }
    }

    // --- folyamatban / kész ---
    Section {
        visible: p.job.title !== "" && p.job.recent === true && (p.job.running || p.job.rc !== null)
        title: p.job.running ? "FOLYAMATBAN: " + p.job.title.toUpperCase()
                             : (p.job.rc === 0 ? "KÉSZ: " : "SIKERTELEN: ") + p.job.title.toUpperCase()
        Rectangle {
            width: parent.width; height: logCol.implicitHeight + 16; color: "transparent"
            Column {
                id: logCol; x: 12; y: 8; width: parent.width - 24
                Repeater {
                    model: p.job.lines
                    Text { width: logCol.width; text: modelData; color: /hiba|nem sikerült|sikertelen|eltér|nem egyezik|fusion-(update|admin):/i.test(modelData) ? Theme.danger : Theme.dim
                           font.family: Theme.mono; font.pixelSize: 11; elide: Text.ElideRight; textFormat: Text.PlainText }
                }
            }
        }
        Rectangle {
            visible: p.done; width: parent.width; height: 56; color: "#14301f"
            Text { x: 14; anchors.verticalCenter: parent.verticalCenter; width: parent.width - rb.width - 40; wrapMode: Text.Wrap
                   text: "Az új rendszer a következő indításkor próbaként indul. Ha a felület rendben megjelenik, véglegessé válik."
                   color: Theme.text; font.family: Theme.font; font.pixelSize: 13 }
            FButton { id: rb; anchors.right: parent.right; anchors.rightMargin: 10; anchors.verticalCenter: parent.verticalCenter
                      text: "Újraindítás most"; primary: true; icon: "restart"; onClicked: settings.updateReboot() }
        }
    }


    // --- 0.0.69: új változat a forrásból ---
    Section {
        visible: (p.s.src || "") !== ""
        title: "ÚJ VÁLTOZAT A FORRÁSBÓL"
        InfoRow { icon: "update"; label: "Forrás"; value: (p.s.src || "") + "\nGit-frissítés → letöltések → rendszerkép → build a Fejlesztődobozban; a végén rákérdez a telepítésre" }
        Item {
            width: parent.width; height: 46
            FButton { x: 12; anchors.verticalCenter: parent.verticalCenter
                      text: p.rjob.running ? "Épül…" : "Új változat a forrásból…"; icon: "update"; primary: !p.rjob.running
                      enabled: !p.rjob.running && !p.job.running
                      onClicked: { p.rcheck = null; settings.rebuildCheck(); rebuildDlg.open() } }
            FButton { anchors.right: parent.right; anchors.rightMargin: 12; anchors.verticalCenter: parent.verticalCenter
                      visible: !p.rjob.running && p.rjob.rc !== null && p.rjob.rc !== undefined && p.rjob.rc !== 0 && p.rjob.recent === true
                      text: "Elemzés a FusionAI-val"; icon: "app-ai"; onClicked: settings.rebuildToAI() }
        }
        Column {
            visible: p.rjob.title !== "" && p.rjob.recent === true && (p.rjob.running || (p.rjob.rc !== null && p.rjob.rc !== undefined))
            x: 12; width: parent.width - 24; spacing: 4; bottomPadding: 8
            Text { text: p.rjob.running ? ("Folyamatban — " + ((p.rjob.step || {}).text ? (p.rjob.step.i + "/" + p.rjob.step.n + ": " + p.rjob.step.text) : "indul…"))
                                        : (p.rjob.rc === 0 ? "Kész." : "Sikertelen (kód: " + p.rjob.rc + ") — az ok az utolsó sorokban")
                   color: p.rjob.running ? Theme.text : (p.rjob.rc === 0 ? Theme.ok : Theme.danger); font.family: Theme.font; font.pixelSize: 13; font.bold: true }
            Rectangle {
                visible: p.rjob.running; width: parent.width; height: 6; radius: 3; color: Theme.base
                Rectangle { width: parent.width * Math.max(0.02, (p.rjob.progress || 0) / 100); height: parent.height; radius: 3; color: Theme.accent }
            }
            Repeater {
                model: (p.rjob.lines || []).filter(l => !/^(PROGRESS |LÉPÉS )/.test(l)).slice(-10)
                Text { width: parent.width; text: modelData; elide: Text.ElideMiddle; textFormat: Text.PlainText
                       color: /hiba|nem sikerült|sikertelen|fusion-dev:|error|AKADÁLY/i.test(modelData) ? Theme.danger : Theme.dim
                       font.family: Theme.mono; font.pixelSize: 11 }
            }
        }
    }

    Section {
        title: "FRISSÍTŐFÁJL (.fupd)"
        Repeater {
            model: p.s.files
            Rectangle {
                width: parent.width; height: 52
                color: p.chosen === modelData.path ? Theme.selected : (fma.containsMouse ? Theme.hover : "transparent")
                MouseArea { id: fma; anchors.fill: parent; hoverEnabled: true; onClicked: p.chosen = modelData.path }
                FIcon { x: 14; anchors.verticalCenter: parent.verticalCenter; size: 26; name: "app-chip" }
                Column {
                    x: 52; anchors.verticalCenter: parent.verticalCenter; width: parent.width - 52 - 140
                    Text { text: "Fúzió " + modelData.version + (modelData.milestone ? " (" + modelData.milestone + ")" : "") +
                                 (modelData.newer ? "" : "   — nem újabb a futó rendszernél")
                           color: modelData.newer ? Theme.text : Theme.dim; font.family: Theme.font; font.pixelSize: 14; font.bold: modelData.newer }
                    Text { width: parent.width; elide: Text.ElideMiddle; text: modelData.place + "/" + modelData.name + "   ·   " + modelData.size
                           color: Theme.dim; font.family: Theme.font; font.pixelSize: 11 }
                }
            }
        }
        InfoRow { visible: p.searching; icon: "search"; label: "Keresés…"; value: "a pendrive-ok és a Tárhely átnézése még tart — a már megtalált fájlok fent láthatók"; valueColor: Theme.dim }
        InfoRow { visible: p.s.files.length === 0 && !p.searching; label: "Nincs frissítőfájl"
                  value: "Másolja a .fupd fájlt a Letöltések mappába vagy egy pendrive-ra, majd: Frissítés (jobb felső gomb). A saját build (…/fusionos/build/out/release) magától megjelenik." }
    }
    Flow {
        width: parent.width; spacing: 8
        FButton { text: "Telepítés"; primary: true; icon: "update"; visible: p.s.files.length > 0
                  enabled: p.chosen !== "" && !p.job.running && (p.s.files.find(f => f.path === p.chosen) || {}).newer === true
                  onClicked: { var e = settings.updateInstall(p.chosen); p.msg = e ? "hiba: " + e : ""; if (!e) p.pending = true } }
        FButton { text: "Telepítő pendrive készítése…"; icon: "drive-usb"; visible: p.s.files.length > 0
                  enabled: p.chosen !== "" && !p.mjob.running && (p.s.files.find(f => f.path === p.chosen) || {}).media === true
                  tip: (p.s.files.find(f => f.path === p.chosen) || {}).media === false ? "ebből a .fupd-ből nem készíthető telepítő (0.0.29 előtti)" : "a kijelölt .fupd-ből egy telepítő pendrive (Fúzió Telepítő)"
                  onClicked: { p.mdisks = []; settings.mediaDisks(); mediaDlg.open() } }
        Text { visible: p.msg !== ""; text: p.msg; color: Theme.danger; font.family: Theme.font; font.pixelSize: 12; anchors.verticalCenter: parent.verticalCenter }
    }
    Section {
        visible: p.mjob.title !== "" && p.mjob.recent === true && (p.mjob.running || p.mjob.rc !== null)
        title: p.mjob.running ? "FOLYAMATBAN: " + p.mjob.title.toUpperCase() : (p.mjob.rc === 0 ? "KÉSZ: " : "SIKERTELEN: ") + p.mjob.title.toUpperCase()
        Column {
            x: 12; width: parent.width - 24; topPadding: 8; bottomPadding: 8
            Repeater {
                model: (p.mjob.lines || []).filter(l => !/^PROGRESS /.test(l))
                Text { width: parent.width; text: modelData; elide: Text.ElideMiddle; textFormat: Text.PlainText
                       color: /^fusion-|sikertelen|nem sikerült/i.test(modelData) ? Theme.danger : Theme.dim
                       font.family: Theme.mono; font.pixelSize: 11 }
            }
        }
    }
    FDialog {
        id: rebuildDlg
        objectName: "rebuildDlg"
        title: "Új változat a forrásból"
        buttons: [["Mégse", ""], ["Indítás", "primary"]]
        defaultButton: 0
        onButtonClicked: (i) => {
            if (i === 1 && p.rcheck && p.rcheck.ok) {
                var e = settings.rebuildStart()
                p.msg = e ? "hiba: " + e : ""
                if (!e) { p.rasked = false; settings.rebuildJobWatch() }
            }
            close()
        }
        Column {
            x: 20; y: 16; width: 560; spacing: 8
            Text { visible: p.rcheck === null; text: "Ellenőrzés… (nem commitolt munka, GitHub, szabad hely, töltő, Fejlesztődoboz)"
                   color: Theme.dim; font.family: Theme.font; font.pixelSize: 13 }
            Text { visible: p.rcheck !== null; width: parent.width; wrapMode: Text.Wrap; color: Theme.text; font.family: Theme.font; font.pixelSize: 13
                   text: !p.rcheck ? "" : "Mostani állapot: " + (p.rcheck.head || "?") + "\n" +
                         (p.rcheck.behind > 0 ? "A GitHubon " + p.rcheck.behind + " új commit van — letöltöm, és abból építek."
                                              : "Nincs új commit a GitHubon — a mostani állapotból építek újra.") +
                         ((p.rcheck.last || {}).secs ? "\nA legutóbbi build " + Math.round(p.rcheck.last.secs / 60) + " percig tartott." : "") +
                         "\nA végén megkérdezem, telepítsem-e. Közben dolgozhatsz, az ablak be is zárható." }
            Repeater {
                model: p.rcheck ? (p.rcheck.warnings || []) : []
                Text { width: 560; wrapMode: Text.Wrap; text: "⚠ " + modelData; color: Theme.warn; font.family: Theme.font; font.pixelSize: 12 }
            }
            Repeater {
                model: p.rcheck ? (p.rcheck.problems || []) : []
                Text { width: 560; wrapMode: Text.Wrap; text: "✖ " + modelData; color: Theme.danger; font.family: Theme.font; font.pixelSize: 12 }
            }
        }
    }
    FDialog {
        id: installAsk
        objectName: "installAsk"
        property string fupd: ""
        title: "Elkészült az új változat"
        buttons: [["Később", ""], ["Telepítés most", "primary"]]
        onButtonClicked: (i) => {
            if (i === 1 && fupd) {
                var e = settings.updateInstall(fupd)
                p.msg = e ? "hiba: " + e : ""
                if (!e) p.pending = true
            }
            close()
        }
        Text { x: 20; y: 16; width: 520; wrapMode: Text.Wrap; color: Theme.text; font.family: Theme.font; font.pixelSize: 13
               text: "Elkészült: " + installAsk.fupd.replace(/^.*\//, "") + "\n\nTelepítsem most? A frissítés a másik rendszer-slotba kerül; " +
                     "az újraindítást utána te indítod. „Később”: a fájl a frissítőfájlok között marad." }
    }
    FDialog {
        id: mediaDlg
        property string disk: ""
        title: "Telepítő pendrive készítése"
        buttons: [["Mégse", ""], ["Készítés (a pendrive törlődik)", "danger"]]
        onOpened: { disk = ""; mconfirm.text = "" }
        onButtonClicked: (i) => {
            if (i === 0) { close(); return }
            if (!disk || mconfirm.text.trim() !== disk) return
            var e = settings.mediaCreate(p.chosen, disk, mconfirm.text.trim())
            p.msg = e ? "hiba: " + e : ""
            close()
        }
        Column {
            x: 20; y: 16; width: 520; spacing: 10
            Text { width: parent.width; wrapMode: Text.Wrap; color: Theme.text; font.family: Theme.font; font.pixelSize: 13
                   text: "A kijelölt frissítőfájlból (" + p.chosen.replace(/^.*\//, "") + ") egy telepítő pendrive készül: új telepítés, " +
                         "újratelepítés a DATA megőrzésével, vagy visszaállítás mentésből — Mint nélkül. Legalább 4 GB-os pendrive kell." }
            Text { text: "Pendrive"; color: Theme.dim; font.family: Theme.font; font.pixelSize: 12 }
            Repeater {
                model: p.mdisks
                Rectangle {
                    width: 520; height: 40; radius: Theme.radius
                    color: mediaDlg.disk === modelData.name ? Theme.selected : (dma.containsMouse ? Theme.hover : Theme.panel)
                    MouseArea { id: dma; anchors.fill: parent; hoverEnabled: true; onClicked: mediaDlg.disk = modelData.name }
                    Text { x: 12; anchors.verticalCenter: parent.verticalCenter; width: parent.width - 24; elide: Text.ElideRight
                           text: modelData.model + "   ·   " + modelData.name + "   ·   " + modelData.sizeText + "   ·   " + modelData.content
                           color: Theme.text; font.family: Theme.font; font.pixelSize: 12 }
                }
            }
            Text { visible: p.mdisks.length === 0; text: "nincs bedugott pendrive (vagy még tölt)…"; color: Theme.dim; font.family: Theme.font; font.pixelSize: 12 }
            Text { visible: mediaDlg.disk !== ""; width: parent.width; wrapMode: Text.Wrap; color: Theme.danger; font.family: Theme.font; font.pixelSize: 12; textFormat: Text.StyledText
                   text: "A(z) <b>" + mediaDlg.disk + "</b> TELJES tartalma törlődik. Megerősítéshez írja be a nevét:" }
            FTextField { id: mconfirm; visible: mediaDlg.disk !== ""; width: 160 }
        }
    }
    Text {
        width: parent.width; wrapMode: Text.Wrap; color: Theme.dim; font.family: Theme.font; font.pixelSize: 11
        text: "A telepítés a DATA-hoz (programok, beállítások, Wi-Fi) nem nyúl. A boot menüben (indításkor 5 mp) mindkét rendszer " +
              "választható. Ha az új rendszer háromszor sem indul el, a gép magától a mostanit indítja, és értesítést kap."
    }
}
