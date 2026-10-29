// Fúzió — FusionAI: beszélgetés a Claude Code-dal a kijelölt helyi Git-repón; jóváhagyások, változások, pillanatképek
import QtQuick
import QtQuick.Controls
import FusionUI

FWindow {
    id: win
    width: 1180; height: 760
    minimumWidth: 860; minimumHeight: 520
    visible: true
    title: "FusionAI" + (ai.project ? " — " + ai.project.split("/").pop() : "")
    property int tab: 0                     // jobb oldal: 0 Változások, 1 Pillanatképek, 2 Napló
    property string msg: ""
    property bool msgErr: false
    property var perm: null                 // a nyitott jóváhagyás
    property var permQueue: []
    readonly property var st: ai.status || ({})

    Component.onCompleted: { raise(); requestActivate(); input.forceActiveFocus() }
    Shortcut { sequence: "Esc"; onActivated: if (ai.busy) ai.stop() }
    Shortcut { sequence: "Ctrl+N"; onActivated: ai.newSession() }
    Shortcut { sequence: "F5"; onActivated: { ai.refresh(); ai.refreshGit(); ai.refreshSessions() } }

    ListModel { id: chat }
    ListModel { id: logModel }

    Connections {
        target: ai
        function onItem(d) {
            chat.append({ kind: d.kind, text: d.text || "", tool: d.tool || "" })
            view.positionViewAtEnd()
        }
        function onDelta(t) {
            if (chat.count === 0) return
            const i = chat.count - 1
            chat.setProperty(i, "text", chat.get(i).text + t)
            if (view.atYEnd || ai.busy) view.positionViewAtEnd()
        }
        function onPermission(p) { win.permQueue = win.permQueue.concat([p]); win.nextPerm() }
        function onMessage(text, isErr) {
            if (text === "__raise__") { win.show(); win.raise(); win.requestActivate(); return }
            win.msg = text; win.msgErr = isErr; msgTimer.restart()
        }
        function onChanged() {
            if (!ai.busy && (win.perm || win.permQueue.length)) { win.perm = null; win.permQueue = []; permDlg.close() }
        }
        function onLogLine(t) { logModel.append({ t: t }); if (logModel.count > 2000) logModel.remove(0, 200) }
    }
    Timer { id: msgTimer; interval: 8000; onTriggered: win.msg = "" }

    function nextPerm() {
        if (win.perm || win.permQueue.length === 0) return
        win.perm = win.permQueue[0]
        win.permQueue = win.permQueue.slice(1)
        noteField.text = ""
        permDlg.open()
    }
    function decide(allow) {
        if (!win.perm) return
        ai.answer(win.perm.id, allow, noteField.text)
        win.perm = null
        permDlg.close()
        Qt.callLater(win.nextPerm)
    }
    function kindColor(k) {
        return k === "user" ? Theme.accent : k === "error" || k === "denied" ? Theme.danger
             : k === "allowed" || k === "result" ? Theme.ok : k === "tool" ? Theme.warn : Theme.dim
    }
    function kindLabel(k) {
        return ({ user: "Te", assistant: "Claude", tool: "Eszköz", error: "Hiba", denied: "Elutasítva",
                  allowed: "Engedélyezve", result: "Kész", info: "FusionAI" })[k] || k
    }

    // ------------------------------------------------------------ állapotsor (Claude Code)
    Rectangle {
        id: top
        width: parent.width; height: 40; color: Theme.panel
        Row {
            x: 12; anchors.verticalCenter: parent.verticalCenter; spacing: 10
            Rectangle { width: 10; height: 10; radius: 5; anchors.verticalCenter: parent.verticalCenter
                color: !st.installed || !st.sdk ? Theme.danger : st.loggedIn ? Theme.ok : Theme.warn }
            FLabel {
                anchors.verticalCenter: parent.verticalCenter
                text: !st.installed ? "A Claude Code nincs telepítve"
                    : !st.sdk ? "Hiányzik a Claude Agent SDK (fusion-dev install claude)"
                    : st.loggedIn ? "Claude Code " + st.version + " — bejelentkezve (" + (st.authMethod || "?") + ")"
                    : "Claude Code " + st.version + " — nincs bejelentkezve"
            }
            FButton { text: !st.installed || !st.sdk ? "Telepítés…" : "Bejelentkezés…"; visible: !st.installed || !st.sdk || !st.loggedIn
                      primary: true; onClicked: ai.login() }
            FButton { text: "Frissítés"; icon: "refresh"; flat: true; onClicked: { ai.refresh(); ai.refreshGit(); ai.refreshSessions() } }
        }
        Row {
            anchors.right: parent.right; anchors.rightMargin: 12; anchors.verticalCenter: parent.verticalCenter; spacing: 8
            FLabel { anchors.verticalCenter: parent.verticalCenter; dim: true
                     text: ai.session ? "munkamenet: " + ai.session.substring(0, 8) : "új munkamenet" }
            FButton { text: "Terminál"; icon: "terminal"; enabled: ai.project !== ""; onClicked: ai.openTerminal() }
        }
    }

    // ------------------------------------------------------------ bal: projekt és munkamenetek
    Rectangle {
        id: left
        anchors { top: top.bottom; bottom: bottomBar.top; left: parent.left }
        width: 250; color: Theme.bg
        Rectangle { anchors.right: parent.right; width: 1; height: parent.height; color: Theme.border }
        Column {
            x: 10; y: 10; width: parent.width - 20; spacing: 6
            FLabel { text: "Projekt"; bold: true }
            ComboBox {
                id: projBox
                width: parent.width
                model: (ai.projects || []).map(p => p.name)
                currentIndex: (ai.projects || []).findIndex(p => p.path === ai.project)
                onActivated: i => ai.openProject(ai.projects[i].path)
            }
            Row {
                spacing: 6
                FTextField { id: pathField; width: left.width - 20 - 76; placeholderText: "másik mappa…" }
                FButton { text: "Nyit"; width: 70; onClicked: { ai.openProject(pathField.text); pathField.text = "" } }
            }
            FLabel { width: parent.width; dim: true; font.pixelSize: Theme.fsSmall; text: ai.project; elide: Text.ElideMiddle }
            Item { width: 1; height: 6 }
            Row {
                spacing: 6
                FLabel { text: "Munkamenetek"; bold: true; anchors.verticalCenter: parent.verticalCenter }
                FButton { text: "Új"; icon: "plus"; onClicked: ai.newSession() }
            }
        }
        ListView {
            id: sessList
            anchors { left: parent.left; right: parent.right; bottom: parent.bottom; top: parent.top; topMargin: 196; rightMargin: 1 }
            clip: true
            model: ai.sessions || []
            ScrollBar.vertical: ScrollBar {}
            delegate: Rectangle {
                width: sessList.width; height: 44
                color: modelData.id === ai.session ? Theme.selected : (ma.containsMouse ? Theme.hover : "transparent")
                Column {
                    x: 10; anchors.verticalCenter: parent.verticalCenter; width: parent.width - 20
                    FLabel { width: parent.width; text: modelData.title || "(cím nélkül)" }
                    FLabel { width: parent.width; dim: true; font.pixelSize: Theme.fsSmall; text: modelData.when }
                }
                MouseArea { id: ma; anchors.fill: parent; hoverEnabled: true; onClicked: ai.resumeSession(modelData.id) }
            }
            FLabel { anchors.centerIn: parent; visible: sessList.count === 0; dim: true; text: "Még nincs mentett munkamenet" }
        }
    }

    // ------------------------------------------------------------ jobb: változások, pillanatképek, napló
    Rectangle {
        id: right
        anchors { top: top.bottom; bottom: bottomBar.top; right: parent.right }
        width: Math.max(340, win.width * 0.36); color: Theme.bg
        Rectangle { width: 1; height: parent.height; color: Theme.border }
        Row {
            id: tabs
            x: 10; y: 8; spacing: 4
            Repeater {
                model: ["Változások" + ((ai.git.files || []).length ? " (" + ai.git.files.length + ")" : ""), "Pillanatképek", "Napló"]
                FButton { text: modelData; checked: win.tab === index; onClicked: win.tab = index }
            }
        }
        // Változások
        Item {
            anchors { top: tabs.bottom; topMargin: 8; left: parent.left; leftMargin: 1; right: parent.right; bottom: parent.bottom }
            visible: win.tab === 0
            FLabel { id: branch; x: 10; text: "Ág: " + (ai.git.branch || "?"); dim: true }
            FButton { anchors.right: parent.right; anchors.rightMargin: 10; text: "Pillanatkép most"; icon: "archive-in"
                      enabled: ai.project !== ""; onClicked: ai.takeSnapshot() }
            ScrollView {
                anchors { top: branch.bottom; topMargin: 14; left: parent.left; right: parent.right; bottom: parent.bottom }
                clip: true
                ListView {
                    id: diffList
                    model: (ai.diff || "").split("\n")
                    delegate: Text {
                        width: diffList.width
                        text: modelData; textFormat: Text.PlainText
                        font.family: Theme.mono; font.pixelSize: Theme.fsSmall
                        leftPadding: 8
                        color: modelData.startsWith("+++") || modelData.startsWith("---") ? Theme.dim
                             : modelData.startsWith("+") ? Theme.ok : modelData.startsWith("-") ? Theme.danger
                             : modelData.startsWith("@@") ? Theme.accent : modelData.startsWith("diff ") ? Theme.warn : Theme.text
                    }
                }
            }
        }
        // Pillanatképek
        Item {
            anchors { top: tabs.bottom; topMargin: 8; left: parent.left; leftMargin: 1; right: parent.right; bottom: parent.bottom }
            visible: win.tab === 1
            FLabel { id: snapHelp; x: 10; width: parent.width - 20; wrapMode: Text.Wrap; dim: true; font.pixelSize: Theme.fsSmall
                     text: "Minden munkamenet elején a FusionAI elmenti a projekt teljes állapotát (a nem commitolt munkát is). Visszaállításkor előbb a mostani állapot is mentődik, így a visszaállítás is visszavonható." }
            ListView {
                id: snapList
                anchors { top: snapHelp.bottom; topMargin: 8; left: parent.left; right: parent.right; bottom: parent.bottom }
                clip: true
                model: ai.snaps || []
                ScrollBar.vertical: ScrollBar {}
                delegate: Rectangle {
                    width: snapList.width; height: 46; color: index % 2 ? Theme.alt : "transparent"
                    Column {
                        x: 10; anchors.verticalCenter: parent.verticalCenter; width: parent.width - 130
                        FLabel { width: parent.width; text: modelData.subject.replace("FusionAI pillanatkép ", "") }
                        FLabel { width: parent.width; dim: true; font.pixelSize: Theme.fsSmall; text: modelData.sha.substring(0, 10) }
                    }
                    FButton { anchors.right: parent.right; anchors.rightMargin: 10; anchors.verticalCenter: parent.verticalCenter
                              text: "Visszaállítás…"; enabled: !ai.busy
                              onClicked: { restoreDlg.sha = modelData.sha; restoreDlg.label = modelData.subject; restoreDlg.open() } }
                }
            }
        }
        // Napló
        ListView {
            id: logList
            anchors { top: tabs.bottom; topMargin: 8; left: parent.left; leftMargin: 1; right: parent.right; bottom: parent.bottom }
            visible: win.tab === 2
            clip: true
            model: logModel
            ScrollBar.vertical: ScrollBar {}
            onCountChanged: positionViewAtEnd()
            delegate: Text { width: logList.width; leftPadding: 8; text: t; wrapMode: Text.WrapAnywhere; color: Theme.dim
                             font.family: Theme.mono; font.pixelSize: Theme.fsSmall; textFormat: Text.PlainText }
        }
    }

    // ------------------------------------------------------------ közép: beszélgetés
    Item {
        anchors { top: top.bottom; bottom: bottomBar.top; left: left.right; right: right.left }
        // a helyi munkafolyamat gombjai (ezeket te indítod, nem a Claude)
        Flow {
            id: tools
            anchors { top: parent.top; left: parent.left; right: parent.right; margins: 8 }
            spacing: 6
            enabled: ai.project !== ""
            FButton { text: ai.task === "teszt" ? "Teszt fut…" : "Teszt"; icon: "flask"; enabled: !ai.task && ai.settings.test !== ""
                      tip: ai.settings.test || "nincs tesztparancs — Beállítások"; onClicked: { win.tab = 2; ai.runTest() } }
            FButton { text: "Naplók"; icon: "report"; enabled: !ai.task; onClicked: logMenu.open()
                Menu {
                    id: logMenu; y: parent.height
                    MenuItem { text: "A munkamenet naplója"; onTriggered: { win.tab = 2; ai.showLog("user") } }
                    MenuItem { text: "Rendszernapló (figyelmeztetések, hibák)"; onTriggered: { win.tab = 2; ai.showLog("system") } }
                    MenuItem { text: "Fúzió-programok naplói"; onTriggered: { win.tab = 2; ai.showLog("fusion") } }
                }
            }
            FButton { text: "Kimenet → Claude"; icon: "copy"; visible: ai.hasOutput; enabled: !ai.busy
                      tip: "Az utolsó teszt / napló kimenetét elküldi Claude-nak elemzésre"; onClicked: ai.sendOutputToClaude() }
            FButton { text: "Újraindítás…"; icon: "restart"; enabled: ai.settings.restart !== ""
                      tip: ai.settings.restart || "nincs újraindító parancs — Beállítások"; onClicked: restartDlg.open() }
            FButton { text: "Commit…"; icon: "check"; enabled: !ai.task && !ai.busy && (ai.git.files || []).length > 0
                      onClicked: { commitDlg.info = ai.commitInfo(); commitMsg.text = commitDlg.info.message || ""; commitDlg.open(); commitMsg.forceActiveFocus() } }
            FButton { text: "Push…"; icon: "up"; enabled: !ai.task && !ai.busy
                      onClicked: { pushDlg.info = ai.pushInfo(); pushDlg.open() } }
            FButton { text: "Beállítások"; icon: "settings"; flat: true
                      onClicked: { testCmd.text = ai.settings.test || ""; restartCmd.text = ai.settings.restart || ""; setDlg.open() } }
        }
        ListView {
            id: view
            anchors { top: tools.bottom; left: parent.left; right: parent.right; bottom: inputBox.top; margins: 8 }
            clip: true
            spacing: 8
            model: chat
            ScrollBar.vertical: ScrollBar {}
            delegate: Rectangle {
                width: view.width - 12
                height: body.implicitHeight + 30
                color: kind === "user" ? "#17263a" : kind === "assistant" ? Theme.base : "transparent"
                border.color: kind === "user" || kind === "assistant" ? Theme.border : "transparent"
                radius: Theme.radius
                Text { x: 10; y: 5; text: win.kindLabel(kind) + (tool ? " · " + tool : ""); color: win.kindColor(kind)
                       font.family: Theme.font; font.pixelSize: Theme.fsSmall; font.bold: true }
                TextEdit {
                    id: body
                    x: 10; y: 22; width: parent.width - 20
                    text: model.text; readOnly: true; selectByMouse: true; wrapMode: Text.Wrap
                    textFormat: kind === "assistant" ? TextEdit.MarkdownText : TextEdit.PlainText
                    color: kind === "tool" || kind === "info" ? Theme.dim : Theme.text
                    font.family: kind === "tool" ? Theme.mono : Theme.font
                    font.pixelSize: kind === "tool" || kind === "info" ? Theme.fsSmall : Theme.fs
                    selectionColor: Theme.accent
                }
            }
            Column {
                anchors.centerIn: parent; width: Math.min(parent.width - 40, 520); spacing: 8
                visible: chat.count === 0
                FLabel { width: parent.width; horizontalAlignment: Text.AlignHCenter; font.pixelSize: Theme.fsBig; bold: true
                         text: "Mit nézzen meg a Claude?" }
                FLabel { width: parent.width; wrapMode: Text.Wrap; dim: true; horizontalAlignment: Text.AlignHCenter; elide: Text.ElideNone
                         text: "Például: „Nem működik a Programkezelő egyik gombja. Keresd meg a hibát a forrásban és a naplókban, javítsd ki, futtasd a teszteket, és mutasd meg, mi változott.”\n\nA Claude a kijelölt repó helyi fájljain dolgozik. Fájlmódosítás és parancs csak a jóváhagyásoddal; commit és push külön, kiemelt jóváhagyással; a nem commitolt munkát eldobó parancsokat a FusionAI elutasítja." }
            }
        }
        Rectangle {
            id: inputBox
            anchors { left: parent.left; right: parent.right; bottom: parent.bottom; margins: 8 }
            height: Math.min(180, Math.max(64, input.implicitHeight + 46))
            color: Theme.base; border.color: input.activeFocus ? Theme.accent : Theme.border; radius: Theme.radius
            ScrollView {
                anchors { left: parent.left; right: sendCol.left; top: parent.top; bottom: opts.top; margins: 6 }
                TextArea {
                    id: input
                    wrapMode: TextArea.Wrap
                    placeholderText: ai.project ? "Írd le a feladatot… (Enter: küldés, Shift+Enter: új sor)" : "Előbb válassz projektet"
                    color: Theme.text; placeholderTextColor: Theme.dim
                    font.family: Theme.font; font.pixelSize: Theme.fs
                    background: null
                    Keys.onReturnPressed: ev => {
                        if (ev.modifiers & Qt.ShiftModifier) { ev.accepted = false; return }
                        if (!ai.busy && text.trim().length) { ai.send(text); text = "" }
                    }
                }
            }
            Row {
                id: opts
                anchors { left: parent.left; bottom: parent.bottom; leftMargin: 8; bottomMargin: 4 }
                spacing: 12
                FCheck { text: "Fájlmódosítás kérdés nélkül (ebben a munkamenetben)"; checked: ai.acceptEdits
                         onToggled: ai.setAcceptEdits(checked); font.pixelSize: Theme.fsSmall }
            }
            Column {
                id: sendCol
                anchors { right: parent.right; top: parent.top; margins: 6 }
                spacing: 6
                FButton { width: 104; text: ai.busy ? "Leállítás" : "Küldés"; danger: ai.busy; primary: !ai.busy
                          enabled: ai.busy || (input.text.trim().length > 0 && ai.project !== "")
                          onClicked: { if (ai.busy) ai.stop(); else { ai.send(input.text); input.text = "" } } }
                FButton { width: 104; text: "Visszavonás"; tip: "Az utolsó kérés óta végzett fájlmódosítások visszavonása"
                          enabled: ai.canUndoTurn; onClicked: ai.undoTurn() }
            }
        }
    }

    // ------------------------------------------------------------ alsó sor
    Rectangle {
        id: bottomBar
        anchors.bottom: parent.bottom
        width: parent.width; height: 26; color: Theme.panel
        FLabel { x: 12; anchors.verticalCenter: parent.verticalCenter; width: parent.width - 24
                 text: win.msg || (ai.busy ? "Claude dolgozik… (Esc: leállítás)" : "Készen áll")
                 color: win.msgErr ? Theme.danger : Theme.dim; font.pixelSize: Theme.fsSmall }
    }

    // ------------------------------------------------------------ jóváhagyás
    FDialog {
        id: permDlg
        title: !win.perm ? "" : win.perm.level === "danger" ? "Kiemelt jóváhagyás: " + win.perm.why : "Jóváhagyás: " + win.perm.why
        buttons: [["Elutasítás", ""], ["Engedélyezés", win.perm && win.perm.level === "danger" ? "danger" : "primary"]]
        defaultButton: (!!win.perm && win.perm.level === "danger") ? 0 : 1
        closePolicy: Popup.NoAutoClose
        width: Math.min(win.width - 80, 760)
        onButtonClicked: i => win.decide(i === 1)
        Column {
            x: 20; y: 16; width: permDlg.width - 40; spacing: 8
            Rectangle {
                width: parent.width; height: 30; radius: Theme.radius
                visible: !!win.perm && win.perm.level === "danger"
                color: "#3d1416"; border.color: Theme.danger
                FLabel { anchors.fill: parent; anchors.leftMargin: 10
                         text: "Ez a projekten kívülre, a rendszerre vagy a Git-történetre hat. Csak akkor engedélyezd, ha érted." }
            }
            FLabel { width: parent.width; wrapMode: Text.Wrap; elide: Text.ElideNone; bold: true
                     text: win.perm ? win.perm.summary : "" }
            FLabel { width: parent.width; wrapMode: Text.Wrap; elide: Text.ElideNone; dim: true
                     visible: text !== ""; text: win.perm ? win.perm.reason : "" }
            Rectangle {
                width: parent.width; height: Math.min(320, detail.implicitHeight + 16)
                color: Theme.base; border.color: Theme.border
                ScrollView {
                    anchors.fill: parent; anchors.margins: 6; clip: true
                    TextEdit { id: detail; readOnly: true; selectByMouse: true; text: win.perm ? win.perm.detail : ""
                               color: Theme.text; font.family: Theme.mono; font.pixelSize: Theme.fsSmall; textFormat: TextEdit.PlainText }
                }
            }
            FTextField { id: noteField; width: parent.width; placeholderText: "Megjegyzés Claude-nak (elutasításnál: mit csináljon helyette)" }
        }
    }

    FDialog {
        id: restoreDlg
        property string sha: ""
        property string label: ""
        title: "Visszaállítás pillanatképre"
        buttons: [["Mégse", ""], ["Visszaállítás", "danger"]]
        defaultButton: 0
        onButtonClicked: i => { if (i === 1) ai.restoreSnapshot(sha); close() }
        FLabel { x: 20; y: 16; width: 440; wrapMode: Text.Wrap; elide: Text.ElideNone
                 text: "A projekt fájljai erre az állapotra állnak vissza:\n" + restoreDlg.label + "\n\nA mostani állapotról előbb új pillanatkép készül; a pillanatkép óta keletkezett új fájlok megmaradnak." }
    }

    // ------------------------------------------------------------ a helyi munkafolyamat ablakai
    FDialog {
        id: setDlg
        title: "Projekt-beállítások — " + ai.project.split("/").pop()
        buttons: [["Mégse", ""], ["Mentés", "primary"]]
        width: Math.min(win.width - 80, 640)
        onButtonClicked: i => { if (i === 1) ai.saveSettings(testCmd.text, restartCmd.text); close() }
        Column {
            x: 20; y: 16; width: setDlg.width - 40; spacing: 6
            FLabel { text: "Tesztparancs (a projekt mappájában fut)"; bold: true }
            FTextField { id: testCmd; width: parent.width; font.family: Theme.mono
                         placeholderText: "pl. fusion-dev box run cargo test · npm test · python3 -m pytest -q" }
            Item { width: 1; height: 6 }
            FLabel { text: "Újraindító parancs (a te programod újraindítása)"; bold: true }
            FTextField { id: restartCmd; width: parent.width; font.family: Theme.mono
                         placeholderText: "pl. pkill -f fusion-tasks; fusion-tasks" }
            FLabel { width: parent.width; wrapMode: Text.Wrap; elide: Text.ElideNone; dim: true; font.pixelSize: Theme.fsSmall
                     text: "Ezeket te indítod a gombokkal, ezért nem kérnek külön jóváhagyást (az újraindítás megerősítést kér). Ha a Claude akarja futtatni őket, az továbbra is jóváhagyással megy." }
        }
    }

    FDialog {
        id: restartDlg
        title: "Újraindítás"
        buttons: [["Mégse", ""], ["Újraindítás", "primary"]]
        onButtonClicked: i => { if (i === 1) ai.restartApp(); close() }
        FLabel { x: 20; y: 16; width: 460; wrapMode: Text.Wrap; elide: Text.ElideNone
                 text: "Lefut:\n" + (ai.settings.restart || "") }
    }

    FDialog {
        id: commitDlg
        property var info: ({})
        title: "Commit — " + ((info && info.branch) || "")
        buttons: [["Mégse", ""], ["Commit", "primary"]]
        defaultButton: 0
        width: Math.min(win.width - 80, 700)
        onButtonClicked: i => { if (i === 1 && commitMsg.text.trim().length) { ai.commitChanges(commitMsg.text, true); close() } else if (i === 0) close() }
        Column {
            x: 20; y: 16; width: commitDlg.width - 40; spacing: 6
            FLabel { width: parent.width; text: "Szerző: " + ((commitDlg.info && commitDlg.info.author) || "NINCS BEÁLLÍTVA — Terminál: git config --global user.name / user.email")
                     color: commitDlg.info && commitDlg.info.author ? Theme.dim : Theme.danger }
            FLabel { text: "Minden változás bekerül (" + ((commitDlg.info && commitDlg.info.files) || []).length + " fájl); előtte pillanatkép készül:" }
            Rectangle {
                width: parent.width; height: Math.min(140, fileCol.implicitHeight + 10); color: Theme.base; border.color: Theme.border
                ScrollView { anchors.fill: parent; anchors.margins: 5; clip: true
                    Column { id: fileCol
                        Repeater { model: (commitDlg.info && commitDlg.info.files) || []
                            Text { text: modelData.status + "  " + modelData.path; color: Theme.text; font.family: Theme.mono; font.pixelSize: Theme.fsSmall } } } }
            }
            FLabel { text: "Commit-üzenet (javaslat a változásokból — írd át, ha kell)"; bold: true }
            Rectangle {
                width: parent.width; height: 90; color: Theme.base; border.color: commitMsg.activeFocus ? Theme.accent : Theme.border
                ScrollView { anchors.fill: parent; anchors.margins: 4
                    TextArea { id: commitMsg; wrapMode: TextArea.Wrap; color: Theme.text; font.family: Theme.font; font.pixelSize: Theme.fs
                               background: null; placeholderText: "0.0.N (mérföldkő): rövid összefoglaló"; placeholderTextColor: Theme.dim } }
            }
        }
    }

    FDialog {
        id: pushDlg
        property var info: ({})
        title: "Push — " + ((info && info.branch) || "")
        buttons: [["Mégse", ""], ["Push", "danger"]]
        defaultButton: 0
        width: Math.min(win.width - 80, 640)
        onButtonClicked: i => { if (i === 1 && ((pushDlg.info && pushDlg.info.commits) || []).length) ai.doPush(); close() }
        Column {
            x: 20; y: 16; width: pushDlg.width - 40; spacing: 6
            FLabel { width: parent.width; text: "Cél: " + ((pushDlg.info && pushDlg.info.upstream) || "") + " (soha nem --force)" }
            FLabel { text: ((pushDlg.info && pushDlg.info.commits) || []).length ? "Feltöltendő commitok:" : "Nincs feltöltendő commit."; bold: true }
            Rectangle {
                width: parent.width; height: Math.min(180, pushCol.implicitHeight + 10); color: Theme.base; border.color: Theme.border
                visible: ((pushDlg.info && pushDlg.info.commits) || []).length > 0
                ScrollView { anchors.fill: parent; anchors.margins: 5; clip: true
                    Column { id: pushCol
                        Repeater { model: (pushDlg.info && pushDlg.info.commits) || []
                            Text { text: modelData; color: Theme.text; font.family: Theme.mono; font.pixelSize: Theme.fsSmall } } } }
            }
        }
    }
}
