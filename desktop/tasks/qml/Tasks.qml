// Fúzió — Feladatkezelő (Ctrl+Alt+Del): futó programok, „nem válaszol”, bezárás; folyamatok
import QtQuick
import QtQuick.Controls
import FusionUI

FWindow {
    id: win
    width: 820; height: 560
    minimumWidth: 640; minimumHeight: 420
    visible: true
    title: "Feladatkezelő"
    property int tab: 0                    // 0: Programok, 1: Folyamatok
    property string selKey: ""
    property int selPid: 0
    property string msg: ""
    property bool msgErr: false
    readonly property var progs: tasks.programs || []
    readonly property var procs: tasks.processes || []
    readonly property var sel: progs.find(g => g.key === selKey) || null
    readonly property int hungCount: progs.filter(g => g.status === "hung").length

    Component.onCompleted: { raise(); requestActivate() }
    Shortcut { sequence: "Esc"; onActivated: confirmDlg.visible ? confirmDlg.close() : win.close() }
    Shortcut { sequence: "Ctrl+Tab"; onActivated: win.tab = 1 - win.tab }
    Connections {
        target: tasks
        function onMessage(text, isErr) {
            if (text === "__raise__") { win.show(); win.raise(); win.requestActivate(); return }
            win.msg = text; win.msgErr = isErr; msgTimer.restart()
        }
    }
    Timer { id: msgTimer; interval: 6000; onTriggered: win.msg = "" }

    // a kijelölés maradjon érvényes; ha nincs, az első „nem válaszol” program
    onProgsChanged: if (!sel) selKey = (progs.find(g => g.status === "hung") || progs[0] || { key: "" }).key

    Column {
        anchors.fill: parent
        // --- összegzés ---
        Rectangle {
            width: parent.width; height: 54; color: Theme.panel
            Row {
                x: 16; anchors.verticalCenter: parent.verticalCenter; spacing: 28
                Repeater {
                    model: [["Processzor", (tasks.summary.cpu || 0) + " %"], ["Memória", tasks.summary.memText || ""],
                            ["Futó programok", win.progs.length + (win.hungCount ? "  (" + win.hungCount + " nem válaszol)" : "")]]
                    Column {
                        Text { text: modelData[0]; color: Theme.dim; font.family: Theme.font; font.pixelSize: 11 }
                        Text { text: modelData[1]; color: index === 2 && win.hungCount ? Theme.danger : Theme.text
                               font.family: Theme.font; font.pixelSize: 15; font.bold: true }
                    }
                }
                Text { anchors.verticalCenter: parent.verticalCenter; text: tasks.summary.memDetail || ""
                       color: Theme.dim; font.family: Theme.font; font.pixelSize: 11 }
            }
        }
        // --- fülek ---
        Row {
            x: 12; height: 40; spacing: 4
            Repeater {
                model: ["Programok", "Folyamatok"]
                Rectangle {
                    width: 130; height: 32; y: 6; radius: 3
                    color: win.tab === index ? Theme.selected : (tma.containsMouse ? Theme.panel : "transparent")
                    Text { anchors.centerIn: parent; text: modelData; color: Theme.text; font.family: Theme.font; font.pixelSize: 13
                           font.bold: win.tab === index }
                    MouseArea { id: tma; anchors.fill: parent; hoverEnabled: true; onClicked: win.tab = index }
                }
            }
        }
        // --- programok ---
        Rectangle {
            visible: win.tab === 0
            width: parent.width - 24; x: 12; height: win.height - 54 - 40 - 64
            color: Theme.base; border.color: Theme.border
            ListView {
                id: plist
                anchors.fill: parent; anchors.margins: 1; clip: true
                model: win.progs
                boundsBehavior: Flickable.StopAtBounds
                ScrollBar.vertical: ScrollBar {}
                header: Rectangle {
                    width: plist.width; height: 26; color: Theme.panel
                    Text { x: 46; anchors.verticalCenter: parent.verticalCenter; text: "Program"; color: Theme.dim; font.family: Theme.font; font.pixelSize: 11 }
                    Text { x: parent.width - 330; anchors.verticalCenter: parent.verticalCenter; text: "Állapot"; color: Theme.dim; font.family: Theme.font; font.pixelSize: 11 }
                    Text { x: parent.width - 170; anchors.verticalCenter: parent.verticalCenter; text: "CPU"; color: Theme.dim; font.family: Theme.font; font.pixelSize: 11 }
                    Text { x: parent.width - 95; anchors.verticalCenter: parent.verticalCenter; text: "Memória (PSS)"; color: Theme.dim; font.family: Theme.font; font.pixelSize: 11 }
                }
                delegate: Rectangle {
                    required property var modelData
                    width: plist.width; height: 48
                    color: modelData.key === win.selKey ? Theme.selected : (pma.containsMouse ? Theme.panel : "transparent")
                    FIcon { x: 12; anchors.verticalCenter: parent.verticalCenter; size: 24
                            name: modelData.kind === "windows" ? "app-laser" : modelData.kind === "flatpak" ? "app-package" : "app-app" }
                    Column {
                        x: 46; anchors.verticalCenter: parent.verticalCenter; width: parent.width - 46 - 340
                        Text { width: parent.width; text: modelData.name; elide: Text.ElideRight; color: Theme.text
                               font.family: Theme.font; font.pixelSize: 13; font.bold: true }
                        Text { width: parent.width; text: modelData.titles; elide: Text.ElideRight; color: Theme.dim
                               font.family: Theme.font; font.pixelSize: 11 }
                    }
                    Rectangle {
                        x: parent.width - 332; anchors.verticalCenter: parent.verticalCenter
                        width: stxt.implicitWidth + 16; height: 22; radius: 11
                        color: modelData.status === "hung" ? Theme.danger : "transparent"
                        border.color: modelData.status === "hung" ? Theme.danger : Theme.border
                        Text { id: stxt; anchors.centerIn: parent; color: modelData.status === "hung" ? "white" : Theme.dim
                               text: modelData.status === "hung" ? "Nem válaszol" : modelData.status === "ok" ? "Fut" : "Fut (nem ellenőrizhető)"
                               font.family: Theme.font; font.pixelSize: 11; font.bold: modelData.status === "hung" }
                    }
                    Text { x: parent.width - 170; anchors.verticalCenter: parent.verticalCenter; text: modelData.cpu + " %"
                           color: Theme.text; font.family: Theme.mono; font.pixelSize: 12 }
                    Text { x: parent.width - 95; anchors.verticalCenter: parent.verticalCenter; text: modelData.memText
                           color: Theme.text; font.family: Theme.mono; font.pixelSize: 12 }
                    MouseArea { id: pma; anchors.fill: parent; hoverEnabled: true
                                onClicked: win.selKey = modelData.key
                                onDoubleClicked: { win.selKey = modelData.key; tasks.act("activate", modelData.key) } }
                }
                Text { anchors.centerIn: parent; visible: win.progs.length === 0; text: "Nincs futó program (ablak)."
                       color: Theme.dim; font.family: Theme.font; font.pixelSize: 13 }
            }
        }
        // --- folyamatok ---
        Rectangle {
            visible: win.tab === 1
            width: parent.width - 24; x: 12; height: win.height - 54 - 40 - 64
            color: Theme.base; border.color: Theme.border
            ListView {
                id: flist
                anchors.fill: parent; anchors.margins: 1; clip: true
                model: win.procs
                boundsBehavior: Flickable.StopAtBounds
                ScrollBar.vertical: ScrollBar {}
                header: Rectangle {
                    width: flist.width; height: 26; color: Theme.panel
                    Repeater {
                        model: [[10, "Folyamat"], [flist.width - 300, "Azonosító"], [flist.width - 200, "CPU"], [flist.width - 110, "Memória (PSS)"]]
                        Text { x: modelData[0]; anchors.verticalCenter: parent.verticalCenter; text: modelData[1]; color: Theme.dim
                               font.family: Theme.font; font.pixelSize: 11 }
                    }
                }
                delegate: Rectangle {
                    required property var modelData
                    width: flist.width; height: 30
                    color: modelData.pid === win.selPid ? Theme.selected : (fma.containsMouse ? Theme.panel : "transparent")
                    Text { x: 10; width: parent.width - 320; anchors.verticalCenter: parent.verticalCenter; elide: Text.ElideRight
                           text: modelData.name + "   " + modelData.cmd; color: Theme.text; font.family: Theme.font; font.pixelSize: 12 }
                    Text { x: parent.width - 300; anchors.verticalCenter: parent.verticalCenter; text: modelData.pid
                           color: Theme.dim; font.family: Theme.mono; font.pixelSize: 12 }
                    Text { x: parent.width - 200; anchors.verticalCenter: parent.verticalCenter; text: modelData.cpu + " %"
                           color: Theme.text; font.family: Theme.mono; font.pixelSize: 12 }
                    Text { x: parent.width - 110; anchors.verticalCenter: parent.verticalCenter; text: modelData.memText
                           color: Theme.text; font.family: Theme.mono; font.pixelSize: 12 }
                    MouseArea { id: fma; anchors.fill: parent; hoverEnabled: true; onClicked: win.selPid = modelData.pid }
                }
            }
        }
        // --- gombok ---
        Item {
            width: parent.width; height: 64
            Text { x: 14; anchors.verticalCenter: parent.verticalCenter; width: parent.width - btns.width - 40
                   text: win.msg || (tasks.busy ? "folyamatban…" : (win.tab === 0
                         ? "Bezárás: mint az ablak X gombja. Kényszerített: azonnal leállítja (a nem mentett munka elvész)."
                         : "Csak a saját folyamatai állíthatók le; a rendszer folyamatai nem."))
                   color: win.msg ? (win.msgErr ? Theme.danger : Theme.mark) : Theme.dim; wrapMode: Text.Wrap
                   font.family: Theme.font; font.pixelSize: 11 }
            Row {
                id: btns
                anchors.right: parent.right; anchors.rightMargin: 12; anchors.verticalCenter: parent.verticalCenter
                spacing: 8
                FButton { visible: win.tab === 0; text: "Váltás"; enabled: !!win.sel
                          onClicked: tasks.act("activate", win.selKey) }
                FButton { visible: win.tab === 0; text: "Bezárás"; enabled: !!win.sel
                          onClicked: tasks.act("close", win.selKey) }
                FButton { visible: win.tab === 0; text: "Kényszerített bezárás"; danger: true; enabled: !!win.sel
                          onClicked: confirmDlg.ask("force", win.selKey, win.sel ? win.sel.name : "") }
                FButton { visible: win.tab === 1; text: "Folyamat leállítása"; danger: true; enabled: win.selPid > 0
                          onClicked: confirmDlg.ask("kill", String(win.selPid), (win.procs.find(p => p.pid === win.selPid) || {}).name || "") }
            }
        }
    }

    FDialog {
        id: confirmDlg
        property string action: ""
        property string arg: ""
        property string what: ""
        function ask(a, x, w) { action = a; arg = x; what = w; open() }
        title: action === "force" ? "Kényszerített bezárás" : "Folyamat leállítása"
        buttons: [["Mégse", ""], [action === "force" ? "Bezárás most" : "Leállítás", "danger"]]
        onButtonClicked: (i) => { close(); if (i === 1) tasks.act(action, arg) }
        Text {
            x: 20; y: 16; width: 440; wrapMode: Text.Wrap; color: Theme.text; font.family: Theme.font; font.pixelSize: 13
            text: "„" + confirmDlg.what + "” azonnal leáll" + (confirmDlg.action === "force" ? " (a program minden ablaka és folyamata)" : "") +
                  ".\nA nem mentett munka elvész."
        }
    }
}
