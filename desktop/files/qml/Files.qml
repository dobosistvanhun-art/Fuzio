// FusionOS — Fájlkezelő: főablak (menü, két panel, funkcióbillentyű-sor, párbeszédek)
import QtQuick
import QtQuick.Controls
import FusionUI

FWindow {
    id: win
    width: 1480; height: 860
    visible: true
    title: activeSide === "left" ? leftModel.path : rightModel.path
    property string activeSide: startActive
    property var act: activeSide === "left" ? lp : rp
    property var other: activeSide === "left" ? rp : lp
    property string message: ""
    property bool busy: files.jobState.active === true
    property bool modal: dlg.visible || conflictDlg.visible || errDlg.visible || progress.visible || driveMenu.visible || ctxMenu.visible

    function switchPanel() { activeSide = activeSide === "left" ? "right" : "left"; act.focusList() }
    function say(t) { message = t; msgTimer.restart() }
    Timer { id: msgTimer; interval: 6000; onTriggered: win.message = "" }

    Component.onCompleted: {
        lp.go(startPaths[0]); rp.go(startPaths[1])
        act.focusList()
        win.raise(); win.requestActivate()
    }

    // --- műveletek ---
    function openRow(p, row) {
        var it = p.model.item(row)
        if (!it.name) return
        if (it.isDir) { p.go(it.full); return }
        var k = files.kind(it.full)
        if (k === "exe") { files.installProgram(it.full); say("Telepítő: a telepítés a Programkezelőben folytatódik"); return }
        // Fusion-társítás (pl. .lbrn → LightBurn) mindig; a programok MIME-igénye csak akkor, ha a
        // beépített nézőke nem tudja megmutatni (kép, szöveg, archívum marad a nézőkében)
        var prog = files.openWithProgram(it.full, k === "image" || k === "text" || k === "archive")
        if (prog) { say("megnyitás: " + prog); return }
        if (k === "elf") { files.runFile(it.full); say("indítva: " + it.name); return }
        openViewer(it.full)
    }
    // a külön ablakokra hivatkozást tartunk, különben a JavaScript szemétgyűjtője bezárhatná őket
    property var kids: []
    function keep(o) {
        if (!o) return
        kids = kids.concat([o])
        o.closing.connect(function () { win.kids = win.kids.filter(k => k !== o) })
    }
    function openViewer(path) { keep(viewerComp.createObject(null, { path: path })) }
    function openEditor(path) { keep(editorComp.createObject(null, { path: path })) }

    function doAction(a) {
        var sel = act.selection(), it = act.current()
        switch (a) {
        case "view": if (it.name && !it.isDir) openViewer(it.full); break
        case "install": if (it.name && !it.isDir) { files.installProgram(it.full); say("a Programkezelő megnyílt: " + it.name) } break
        case "edit": if (it.name && !it.isDir) openEditor(it.full); break
        case "newfile": ask("Új fájl", "Az új fájl neve:", "", function (v) { var e = files.newFile(act.model.path, v); if (e) err("Nem hozható létre", e); else { act.model.reloadKeep(); act.setCur(act.model.indexOf(v)); openEditor(act.model.path + "/" + v) } }); break
        case "copy": case "move":
            if (!sel.length) return
            transfer(a, sel, other.model.path); break
        case "mkdir": ask("Új mappa", "Az új mappa neve:", "", function (v) { var e = files.mkdir(act.model.path, v); if (e) err("Nem hozható létre", e); else { act.go(act.model.path, v.split("/")[0]) } }); break
        case "rename":
            if (!it.name || it.isParent) return
            ask("Átnevezés", "Új név:", it.name, function (v) { var e = files.rename(it.full, v); if (e) err("Nem nevezhető át", e); else act.go(act.model.path, v) }); break
        case "delete":
            if (!sel.length) return
            confirm("Törlés", (sel.length === 1 ? "Törli ezt: „" + sel[0].split("/").pop() + "”?" : "Törli a kijelölt " + sel.length + " elemet?") + "\nA törlés végleges (nincs lomtár).",
                    "Törlés", "danger", function () { files.remove(sel) }); break
        case "pack":
            if (!sel.length) return
            var base = sel.length === 1 ? sel[0].split("/").pop().replace(/\.[^.]*$/, "") : act.model.path.split("/").pop() || "archivum"
            ask("Tömörítés (ZIP)", "Az archívum helye:", other.model.path + "/" + base + ".zip", function (v) {
                if (!v.toLowerCase().endsWith(".zip")) v += ".zip"
                files.pack(sel, v) }); break
        case "extract":
            var arcs = sel.filter(p => /\.(zip|tar|tgz|txz|tbz2|tar\.gz|tar\.xz|tar\.bz2)$/i.test(p))
            if (!arcs.length) { say("nincs kijelölt archívum (zip, tar, tar.gz, tar.xz, tar.bz2)"); return }
            ask("Kicsomagolás", arcs.length + " archívum kicsomagolása ide:", other.model.path, function (v) { files.extract(arcs, v, "all") }); break
        case "search": keep(searchComp.createObject(null, { root: act.model.path, panel: act })); break
        case "compare": say(files.compare()); break
        case "hidden": leftModel.showHidden = !leftModel.showHidden; rightModel.showHidden = leftModel.showHidden; break
        case "refresh": leftModel.reloadKeep(); rightModel.reloadKeep(); files.refreshVolumes(); break
        case "terminal": files.terminalHere(act.model.path); break
        case "markall": act.model.markAll(true); break
        case "marknone": act.model.markAll(false); break
        case "markinv": act.model.invertMarks(); break
        case "markplus": ask("Jelölés minta szerint", "Minta (pl. *.gcode *.nc):", "*", function (v) { act.model.markPattern(v, true) }); break
        case "markminus": ask("Jelölés törlése minta szerint", "Minta:", "*", function (v) { act.model.markPattern(v, false) }); break
        case "copyclip": if (sel.length) { files.setClip(sel, false); say(sel.length + " elem a vágólapon (másolás)") } break
        case "cutclip": if (sel.length) { files.setClip(sel, true); say(sel.length + " elem a vágólapon (kivágás)") } break
        case "paste":
            var c = files.takeClip()
            if (!c.paths || !c.paths.length) { say("a vágólap üres"); return }
            run(c.cut ? "move" : "copy", c.paths, act.model.path, function () { files.clipDone() }); break
        case "swap": var l = leftModel.path, r = rightModel.path; lp.go(r); rp.go(l); break
        case "same": other.go(act.model.path); break
        case "drive": driveMenu.openFor(act); break
        case "menu": ctxMenu.popup(); break
        }
    }
    // másolás / mozgatás: a cél szerkeszthető (mint a klasszikus kétpaneles kezelőkben)
    function transfer(kind, sel, target) {
        var label = kind === "copy" ? "Másolás" : "Mozgatás"
        ask(label, (sel.length === 1 ? "„" + sel[0].split("/").pop() + "”" : sel.length + " elem") + " " + (kind === "copy" ? "másolása" : "mozgatása") + " ide:",
            target, function (v) { run(kind, sel, v) }, label)
    }
    function run(kind, sel, target, after) {
        var e = files.checkTarget(sel, target)
        if (e) { err("Nem végezhető el", e); return }
        var c = files.conflicts(sel, target)
        var go = function (mode) { (kind === "copy" ? files.copy : files.move)(sel, target, mode); if (after) after() }
        if (c.length) { conflictDlg.names = c; conflictDlg.cb = go; conflictDlg.open() } else go("all")
    }
    function dropped(paths, target, move) { if (paths.length) transfer(move ? "move" : "copy", paths, target) }

    // --- párbeszéd-segédek ---
    function ask(title, label, value, cb, okText) {
        dlg.title = title; dlg.label = label; dlg.value = value; dlg.cb = cb; dlg.input = true
        dlg.buttons = [["Mégse", ""], [okText || "OK", "primary"]]; dlg.open()
    }
    function confirm(title, label, okText, style, cb) {
        dlg.title = title; dlg.label = label; dlg.cb = cb; dlg.input = false
        dlg.buttons = [["Mégse", ""], [okText, style]]; dlg.open()
    }
    function err(title, text, list) { errDlg.title = title; errDlg.text = text; errDlg.items = list || []; errDlg.open() }

    // --- billentyűparancsok (a párbeszédek alatt nem) ---
    component Key: Shortcut { enabled: !win.modal; context: Qt.WindowShortcut }
    Key { sequence: "F3"; onActivated: doAction("view") }
    Key { sequence: "F4"; onActivated: doAction("edit") }
    Key { sequence: "Shift+F4"; onActivated: doAction("newfile") }
    Key { sequence: "F5"; onActivated: doAction("copy") }
    Key { sequence: "F6"; onActivated: doAction("move") }
    Key { sequence: "Shift+F6"; onActivated: doAction("rename") }
    Key { sequence: "F2"; onActivated: doAction("rename") }
    Key { sequence: "F7"; onActivated: doAction("mkdir") }
    Key { sequence: "F8"; onActivated: doAction("delete") }
    Key { sequence: "Shift+Del"; onActivated: doAction("delete") }
    Key { sequence: "Alt+F7"; onActivated: doAction("search") }
    Key { sequence: "Alt+F5"; onActivated: doAction("pack") }
    Key { sequence: "Alt+F9"; onActivated: doAction("extract") }
    Key { sequence: "Shift+F2"; onActivated: doAction("compare") }
    Key { sequence: "Ctrl+H"; onActivated: doAction("hidden") }
    Key { sequence: "Ctrl+R"; onActivated: doAction("refresh") }
    Key { sequence: "Ctrl+A"; onActivated: doAction("markall") }
    Key { sequence: "Ctrl+C"; onActivated: doAction("copyclip") }
    Key { sequence: "Ctrl+X"; onActivated: doAction("cutclip") }
    Key { sequence: "Ctrl+V"; onActivated: doAction("paste") }
    Key { sequence: "Ctrl+U"; onActivated: doAction("swap") }
    Key { sequence: "Ctrl+T"; onActivated: doAction("terminal") }
    Key { sequence: "Alt+F1"; onActivated: { activeSide = "left"; driveMenu.openFor(lp) } }
    Key { sequence: "Alt+F2"; onActivated: { activeSide = "right"; driveMenu.openFor(rp) } }
    Key { sequence: "Ctrl+Q"; onActivated: Qt.quit() }
    Key { sequence: "F10"; onActivated: Qt.quit() }

    // --- menüsor ---
    menuBar: MenuBar {
        background: Rectangle { color: Theme.panel }
        delegate: MenuBarItem {
            id: mbi
            contentItem: Text { text: mbi.text.replace("&", ""); color: Theme.text; font.family: Theme.font; font.pixelSize: 13 }
            background: Rectangle { color: mbi.highlighted ? Theme.selected : "transparent" }
        }
        component MI: MenuItem {
            id: mi
            property string act: ""
            property string keys: ""
            onTriggered: if (act) win.doAction(act)
            contentItem: Row {
                spacing: 0
                Text { width: 200; text: mi.text; color: mi.enabled ? Theme.text : Theme.dim; font.family: Theme.font; font.pixelSize: 13 }
                Text { text: mi.keys; color: Theme.dim; font.family: Theme.font; font.pixelSize: 12 }
            }
            background: Rectangle { color: mi.highlighted ? Theme.selected : "transparent" }
        }
        Menu {
            title: "Fájl"
            MI { text: "Megtekintés"; keys: "F3"; act: "view" }
            MI { text: "Szerkesztés"; keys: "F4"; act: "edit" }
            MI { text: "Új fájl"; keys: "Shift+F4"; act: "newfile" }
            MenuSeparator {}
            MI { text: "Másolás"; keys: "F5"; act: "copy" }
            MI { text: "Mozgatás"; keys: "F6"; act: "move" }
            MI { text: "Átnevezés"; keys: "Shift+F6"; act: "rename" }
            MI { text: "Új mappa"; keys: "F7"; act: "mkdir" }
            MI { text: "Törlés"; keys: "F8"; act: "delete" }
            MenuSeparator {}
            MI { text: "Tömörítés (ZIP)"; keys: "Alt+F5"; act: "pack" }
            MI { text: "Kicsomagolás"; keys: "Alt+F9"; act: "extract" }
            MenuSeparator {}
            MI { text: "Kilépés"; keys: "Alt+F4"; onTriggered: Qt.quit() }
        }
        Menu {
            title: "Szerkesztés"
            MI { text: "Másolás a vágólapra"; keys: "Ctrl+C"; act: "copyclip" }
            MI { text: "Kivágás"; keys: "Ctrl+X"; act: "cutclip" }
            MI { text: "Beillesztés"; keys: "Ctrl+V"; act: "paste" }
            MenuSeparator {}
            MI { text: "Mind kijelölése"; keys: "Ctrl+A"; act: "markall" }
            MI { text: "Kijelölés megszüntetése"; act: "marknone" }
            MI { text: "Kijelölés megfordítása"; keys: "Num *"; act: "markinv" }
            MI { text: "Jelölés minta szerint…"; keys: "Num +"; act: "markplus" }
            MI { text: "Jelölés törlése minta szerint…"; keys: "Num −"; act: "markminus" }
        }
        Menu {
            title: "Nézet"
            MI { text: (leftModel.showHidden ? "✓ " : "") + "Rejtett fájlok"; keys: "Ctrl+H"; act: "hidden" }
            MI { text: "Frissítés"; keys: "Ctrl+R"; act: "refresh" }
            MenuSeparator {}
            MI { text: "Rendezés: név"; onTriggered: act.model.setSort("name") }
            MI { text: "Rendezés: kiterjesztés"; onTriggered: act.model.setSort("ext") }
            MI { text: "Rendezés: méret"; onTriggered: act.model.setSort("size") }
            MI { text: "Rendezés: dátum"; onTriggered: act.model.setSort("date") }
            MenuSeparator {}
            MI { text: "Panelek cseréje"; keys: "Ctrl+U"; act: "swap" }
            MI { text: "Másik panel ide"; act: "same" }
        }
        Menu {
            title: "Eszközök"
            MI { text: "Keresés…"; keys: "Alt+F7"; act: "search" }
            MI { text: "Könyvtárak összehasonlítása"; keys: "Shift+F2"; act: "compare" }
            MI { text: "Terminál itt"; keys: "Ctrl+T"; act: "terminal" }
            MenuSeparator {}
            MI { text: "Meghajtók (bal)"; keys: "Alt+F1"; onTriggered: driveMenu.openFor(lp) }
            MI { text: "Meghajtók (jobb)"; keys: "Alt+F2"; onTriggered: driveMenu.openFor(rp) }
        }
        Menu {
            title: "Súgó"
            MI { text: "Billentyűk"; onTriggered: helpDlg.open() }
        }
    }

    // --- a két panel ---
    Item {
        id: body
        anchors.top: parent.top; anchors.bottom: msgBar.top; anchors.left: parent.left; anchors.right: parent.right
        anchors.margins: 4
        FilePanel {
            id: lp; side: "left"; model: leftModel; active: win.activeSide === "left"
            x: 0; y: 0; width: (parent.width - 4) / 2; height: parent.height
            onActivated: win.activeSide = "left"
            onOpenRow: (r) => win.openRow(lp, r)
            onRequest: (a) => win.doAction(a)
        }
        FilePanel {
            id: rp; side: "right"; model: rightModel; active: win.activeSide === "right"
            x: lp.width + 4; y: 0; width: lp.width; height: parent.height
            onActivated: win.activeSide = "right"
            onOpenRow: (r) => win.openRow(rp, r)
            onRequest: (a) => win.doAction(a)
        }
    }
    Rectangle {
        id: msgBar
        anchors.bottom: fkeys.top; width: parent.width; height: win.message ? 24 : 0; visible: win.message !== ""
        color: "#1b222c"
        Text { x: 10; anchors.verticalCenter: parent.verticalCenter; text: win.message; color: Theme.text; font.family: Theme.font; font.pixelSize: 12 }
    }
    // --- funkcióbillentyű-sor ---
    Rectangle {
        id: fkeys
        anchors.bottom: parent.bottom; width: parent.width; height: 32; color: Theme.panel
        Row {
            anchors.fill: parent; anchors.margins: 3; spacing: 3
            Repeater {
                model: [["F3", "Nézet", "view"], ["F4", "Szerkesztés", "edit"], ["F5", "Másolás", "copy"], ["F6", "Mozgatás", "move"],
                        ["F7", "Új mappa", "mkdir"], ["F8", "Törlés", "delete"], ["Alt+F7", "Keresés", "search"], ["Alt+F4", "Kilépés", "quit"]]
                Rectangle {
                    width: (fkeys.width - 6 - 7 * 3) / 8; height: 26; radius: Theme.radius
                    color: fma.pressed ? Theme.selected : (fma.containsMouse ? Theme.hover : "#1b222c")
                    border.color: Theme.border
                    Row {
                        anchors.centerIn: parent; spacing: 6
                        Text { text: modelData[0]; color: Theme.accent; font.family: Theme.font; font.pixelSize: 12; font.bold: true }
                        Text { text: modelData[1]; color: Theme.text; font.family: Theme.font; font.pixelSize: 12 }
                    }
                    MouseArea { id: fma; anchors.fill: parent; hoverEnabled: true
                        onClicked: { if (modelData[2] === "quit") Qt.quit(); else win.doAction(modelData[2]); win.act.focusList() } }
                }
            }
        }
    }

    // húzott elemek „szellemképe”
    Rectangle {
        id: dragProxy
        property var paths: []
        property string source: ""
        property bool shift: false
        visible: Drag.active
        z: 1000
        width: dpt.implicitWidth + 20; height: 26; color: Theme.selected; border.color: Theme.accent; radius: Theme.radius
        Drag.keys: ["fusion-files"]
        Drag.dragType: Drag.Internal
        Drag.supportedActions: Qt.CopyAction | Qt.MoveAction
        Text { id: dpt; anchors.centerIn: parent; color: Theme.text; font.family: Theme.font; font.pixelSize: 12
               text: (dragProxy.paths.length === 1 ? dragProxy.paths[0].split("/").pop() : dragProxy.paths.length + " elem") + "  (Shift: mozgatás)" }
    }

    // --- meghajtó-választó ---
    Menu {
        id: driveMenu
        property var target: lp
        function openFor(p) { target = p; files.refreshVolumes(); x = p.x + 8; y = 40; open() }
        width: 380
        Repeater {
            model: files.volumes
            MenuItem {
                id: dmi
                contentItem: Row {
                    spacing: 10
                    FIcon { name: modelData.icon; size: 20; anchors.verticalCenter: parent.verticalCenter }
                    Column {
                        width: 320
                        Text { width: parent.width; elide: Text.ElideRight; text: modelData.name + (modelData.mounted ? "" : "  (nincs csatolva — kattintásra csatol)"); color: Theme.text; font.family: Theme.font; font.pixelSize: 13 }
                        Text { width: parent.width; elide: Text.ElideMiddle; text: modelData.info + (modelData.path && modelData.dev ? " → " + modelData.path : ""); color: Theme.dim; font.family: Theme.font; font.pixelSize: 11 }
                    }
                }
                background: Rectangle { color: dmi.highlighted ? Theme.selected : "transparent" }
                onTriggered: {
                    if (modelData.mounted) { driveMenu.target.go(modelData.path); driveMenu.target.focusList(); return }
                    var r = files.mountVolume(modelData.dev)
                    if (r.ok && r.path) { driveMenu.target.go(r.path); win.say(r.msg) } else win.err("Nem csatolható", r.msg)
                    driveMenu.target.focusList()
                }
            }
        }
        MenuSeparator {}
        MenuItem {
            id: ejectItem
            enabled: files.volumes.some(v => v.media && v.mounted)
            text: "Meghajtó kiadása (biztonságos eltávolítás)…"
            contentItem: Text { text: ejectItem.text; color: ejectItem.enabled ? Theme.text : Theme.dim; font.family: Theme.font; font.pixelSize: 13 }
            background: Rectangle { color: ejectItem.highlighted ? Theme.selected : "transparent" }
            onTriggered: ejectMenu.popup()
        }
    }
    Menu {
        id: ejectMenu
        Repeater {
            model: files.volumes.filter(v => v.media && v.mounted)
            MenuItem {
                id: emi
                contentItem: Text { text: modelData.name + "  (" + modelData.path + ")"; color: Theme.text; font.family: Theme.font; font.pixelSize: 13 }
                background: Rectangle { color: emi.highlighted ? Theme.selected : "transparent" }
                onTriggered: {
                    // a panelek ne álljanak a kiadandó kötet mappáiban
                    for (var p of [lp, rp]) if (p.model.path === modelData.path || p.model.path.startsWith(modelData.path + "/")) p.go(files.volumes[0].path)
                    var r = files.ejectVolume(modelData.dev || modelData.path)
                    if (r.ok) win.say(r.msg.split("\n").pop()); else win.err("Nem adható ki", r.msg)
                }
            }
        }
    }

    // --- helyi menü (jobb gomb) ---
    Menu {
        id: ctxMenu
        component CI: MenuItem {
            id: ci
            property string act: ""
            onTriggered: win.doAction(act)
            contentItem: Text { text: ci.text; color: Theme.text; font.family: Theme.font; font.pixelSize: 13 }
            background: Rectangle { color: ci.highlighted ? Theme.selected : "transparent" }
        }
        CI { text: "Megnyitás"; onTriggered: win.openRow(win.act, win.act.cur) }
        CI { text: "Megtekintés (F3)"; act: "view" }
        CI { text: "Szerkesztés (F4)"; act: "edit" }
        MenuSeparator {}
        CI { text: "Másolás a vágólapra (Ctrl+C)"; act: "copyclip" }
        CI { text: "Kivágás (Ctrl+X)"; act: "cutclip" }
        CI { text: "Beillesztés (Ctrl+V)"; act: "paste" }
        MenuSeparator {}
        CI { text: "Átnevezés (Shift+F6)"; act: "rename" }
        CI { text: "Tömörítés (Alt+F5)"; act: "pack" }
        CI { text: "Kicsomagolás (Alt+F9)"; act: "extract" }
        CI { text: "Telepítés a Programkezelővel"; act: "install" }
        CI { text: "Törlés (F8)"; act: "delete" }
        MenuSeparator {}
        CI { text: "Terminál itt"; act: "terminal" }
    }

    // --- általános párbeszéd: kérdés / szövegbevitel ---
    FDialog {
        id: dlg
        property string label: ""
        property string value: ""
        property bool input: false
        property var cb: null
        width: 560
        onOpened: if (input) { field.text = value; field.forceActiveFocus(); var dot = value.lastIndexOf("."); field.select(0, dot > 0 && value.indexOf("/") < 0 ? dot : value.length) } else forceActiveFocus()
        onClosed: win.act.focusList()
        onButtonClicked: (i) => { var f = cb; var v = field.text; close(); if (i === buttons.length - 1 && f) f(v) }
        Column {
            x: 20; y: 16; width: 520; spacing: 8
            Text { width: parent.width; text: dlg.label; color: Theme.text; font.family: Theme.font; font.pixelSize: 13; wrapMode: Text.Wrap }
            FTextField { id: field; visible: dlg.input; width: parent.width
                Keys.onReturnPressed: dlg.press(dlg.buttons.length - 1); Keys.onEnterPressed: dlg.press(dlg.buttons.length - 1) }
        }
    }
    FDialog {
        id: conflictDlg
        property var names: []
        property var cb: null
        title: "Már létezik"
        buttons: [["Mégse", ""], ["Kihagyás", ""], ["Felülírás mindet", "danger"]]
        defaultButton: 1
        onButtonClicked: (i) => { close(); if (i === 1) cb("skip"); else if (i === 2) cb("all"); win.act.focusList() }
        Column {
            x: 20; y: 16; width: 480; spacing: 6
            Text { text: conflictDlg.names.length + " elem már létezik a célban:"; color: Theme.text; font.family: Theme.font; font.pixelSize: 13 }
            Text { width: parent.width; text: conflictDlg.names.slice(0, 8).join("\n") + (conflictDlg.names.length > 8 ? "\n…" : "")
                   color: Theme.mark; font.family: Theme.font; font.pixelSize: 12; elide: Text.ElideMiddle }
        }
    }
    FDialog {
        id: errDlg
        property string text: ""
        property var items: []
        onButtonClicked: { close(); win.act.focusList() }
        Column {
            x: 20; y: 16; width: 560; spacing: 6
            Text { width: parent.width; text: errDlg.text; color: Theme.text; font.family: Theme.font; font.pixelSize: 13; wrapMode: Text.Wrap }
            Text { width: parent.width; visible: errDlg.items.length > 0; text: errDlg.items.slice(0, 12).join("\n")
                   color: Theme.danger; font.family: Theme.mono; font.pixelSize: 11; wrapMode: Text.Wrap }
        }
    }
    FDialog {
        id: helpDlg
        title: "Billentyűk"
        onButtonClicked: close()
        Text {
            x: 20; y: 16; color: Theme.text; font.family: Theme.mono; font.pixelSize: 12; lineHeight: 1.2
            text: "Tab            panelváltás           Enter        megnyitás\n" +
                  "Backspace      egy szinttel feljebb  Ctrl+PgUp    feljebb\n" +
                  "Insert         jelölés, és le        Szóköz       jelölés (+ mappaméret)\n" +
                  "Shift+nyilak   jelölés mozgatással   Ctrl+A       mind\n" +
                  "Num + / − / *  jelölés minta szerint / megfordítás\n" +
                  "F3 / F4        megtekintés / szerkesztés\n" +
                  "F5 / F6        másolás / mozgatás (a másik panelbe)\n" +
                  "Shift+F6, F2   átnevezés             F7  új mappa    F8, Del  törlés\n" +
                  "Alt+F5 / F9    tömörítés / kicsomagolás\n" +
                  "Alt+F7         keresés               Shift+F2  könyvtár-összehasonlítás\n" +
                  "Alt+F1 / F2    meghajtó (bal / jobb) Ctrl+H    rejtett fájlok\n" +
                  "Ctrl+C / X / V vágólap               Ctrl+U    panelek cseréje\n" +
                  "Ctrl+T         terminál itt          betűk     ugrás névre\n" +
                  "Egér: Ctrl+kattintás jelöl, Shift+kattintás tartományt jelöl,\n" +
                  "húzás a másik panelre: másolás (Shift: mozgatás), jobb gomb: helyi menü"
        }
    }

    // --- folyamatjelző (hosszú műveletekhez) ---
    Popup {
        id: progress
        visible: files.jobState.show === true
        modal: true; closePolicy: Popup.NoAutoClose
        anchors.centerIn: Overlay.overlay
        width: 520; padding: 0
        background: Rectangle { color: Theme.bg; border.color: Theme.border }
        contentItem: Column {
            Rectangle { width: parent.width; height: 34; color: Theme.panel
                Text { x: 14; anchors.verticalCenter: parent.verticalCenter; text: files.jobState.title || ""; color: Theme.text
                       font.family: Theme.font; font.pixelSize: 13; font.bold: true } }
            Column {
                x: 18; width: parent.width - 36; topPadding: 14; bottomPadding: 14; spacing: 8
                Text { width: parent.width; text: files.jobState.current || ""; elide: Text.ElideMiddle; color: Theme.dim; font.family: Theme.font; font.pixelSize: 12 }
                Rectangle { width: parent.width; height: 10; color: Theme.base; border.color: Theme.border
                    Rectangle { x: 1; y: 1; height: 8; width: (parent.width - 2) * (files.jobState.pct || 0) / 100; color: Theme.accent } }
                Text { text: (files.jobState.files ? files.jobState.files + " fájl" : "") + (files.jobState.bytes ? "   ·   " + files.jobState.bytes : "") +
                             (files.jobState.speed ? "   ·   " + files.jobState.speed : "")
                       color: Theme.text; font.family: Theme.font; font.pixelSize: 12 }
            }
            Rectangle { width: parent.width; height: 1; color: Theme.border }
            Item { width: parent.width; height: 48
                FButton { anchors.right: parent.right; anchors.rightMargin: 14; anchors.verticalCenter: parent.verticalCenter
                          text: "Megszakítás"; onClicked: files.cancelJob() } }
        }
    }
    Connections {
        target: files
        function onJobFinished(kind, summary, errors) {
            if (errors.length) win.err("Hibák a művelet közben", summary, errors); else win.say(summary)
            win.act.focusList()
        }
    }

    Component { id: viewerComp; Viewer {} }
    Component { id: editorComp; Editor {} }
    Component { id: searchComp; Search {} }
}
