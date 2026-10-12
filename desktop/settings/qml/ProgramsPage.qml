// Programkezelő: telepített programok (Windows és Linux), telepítés fájlból és a Flathubról,
// eltávolítás, frissítés, eszköz-hozzáférés. A felület csak kér — a műveletet a háttér
// (fusion-programs) végzi, külön folyamatban; a végén értesítés jön.
import QtQuick
import QtQuick.Controls
import FusionUI

SettingsPage {
    id: p
    title: "Programkezelő"
    subtitle: "Windows- és Linux-programok — minden program a DATA-n, saját mappában (/data/programs)"
    property var progs: []
    property var roles: []
    property var recipes: []
    property var inst: []
    property var sizes: ({})
    property var job: ({ running: false, lines: [], rc: null, title: "" })
    property var found: []
    property bool searching: false
    property string openId: ""          // kinyitott program
    property string confirm: ""       // eltávolítás megerősítése
    property string msg: ""
    property string chosen: ""
    busy: job.running || searching
    onRefresh: settings.programsRefresh()
    Component.onCompleted: { if (win.param) chooseFile(win.param); settings.programsRefresh(); settings.programJobWatch(); settings.devRefresh() }
    property var dev: ({ node: "", npm: "", wrangler: "" })
    property bool devLoaded: false
    // a terminálban futó telepítés után az állapot frissül, amikor az ablak újra előtérbe kerül
    Connections { target: win; function onActiveChanged() { if (win.active && p.visible) settings.devRefresh() } }
    Connections {
        target: win
        function onParamChanged() { if (win.param) p.chooseFile(win.param) }
    }
    function chooseFile(path) { p.chosen = path; srcField.text = path }
    function typeColor(t) { return t === "win64" ? "#1d4ed8" : t === "flatpak" ? "#15803d" : "#b45309" }
    Connections {
        target: settings
        function onResult(tag, r) {
            if (tag === "dev") { p.dev = r; p.devLoaded = true; return }
            if (tag === "programs" && r.programs) {
                p.progs = r.programs; p.roles = r.roles; p.recipes = r.recipes; p.job = r.job
                if (r.installers !== undefined) { p.inst = r.installers; settings.programSizes() }
            } else if (tag === "program-sizes" && !r.error) p.sizes = r
            else if (tag === "program-job") {
                var was = p.job.running || p.pending
                p.job = r
                if (was && !r.running) { p.pending = false; p.confirm = ""; settings.programsRefresh() }
            } else if (tag === "flathub") { p.searching = false; p.found = r.results || []; p.msg = r.error ? "hiba: " + r.error : (p.found.length ? "" : "Nincs találat: " + r.term) }
        }
    }
    function act(err) { p.msg = err ? "hiba: " + err : "" }
    function startJob(err) { p.act(err); if (!err) p.pending = true }
    property bool pending: false

    // --- folyamatban lévő / utolsó művelet ---
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
                    Text { width: logCol.width; text: modelData; color: /hiba|nem sikerült|sikertelen|error/i.test(modelData) ? Theme.danger : Theme.dim
                           font.family: Theme.mono; font.pixelSize: 11; elide: Text.ElideRight; textFormat: Text.PlainText }
                }
            }
        }
    }
    Text { visible: p.msg !== ""; text: p.msg; color: p.msg.indexOf("hiba") === 0 ? Theme.danger : Theme.ok
           font.family: Theme.font; width: parent.width; wrapMode: Text.Wrap }

    // --- telepített programok ---
    Section {
        title: "TELEPÍTETT PROGRAMOK"
        Repeater {
            model: p.progs
            Column {
                id: row
                width: parent.width
                property var m: modelData
                property bool isOpen: p.openId === m.id
                Rectangle {
                    width: parent.width; height: 56
                    color: row.isOpen ? Theme.selected : (rma.containsMouse ? Theme.hover : "transparent")
                    MouseArea { id: rma; anchors.fill: parent; hoverEnabled: true; onClicked: p.openId = row.isOpen ? "" : row.m.id }
                    FIcon { x: 14; anchors.verticalCenter: parent.verticalCenter; size: 32
                            name: row.m.iconFile || ("app-" + row.m.icon) }
                    Column {
                        x: 58; anchors.verticalCenter: parent.verticalCenter; width: parent.width - 58 - btns.width - 20; spacing: 3
                        Text { text: row.m.name; color: Theme.text; font.family: Theme.font; font.pixelSize: 14; font.bold: true; elide: Text.ElideRight; width: parent.width }
                        Row {
                            spacing: 8
                            Rectangle { width: tb.implicitWidth + 10; height: 16; radius: 3; color: p.typeColor(row.m.type)
                                Text { id: tb; anchors.centerIn: parent; text: row.m.typeName; color: "white"; font.family: Theme.font; font.pixelSize: 10 } }
                            Text { text: [row.m.version, p.sizes[row.m.id] || "", row.m.open ? "megnyitja: " + row.m.open : ""].filter(x => x).join("  ·  ")
                                   color: Theme.dim; font.family: Theme.font; font.pixelSize: 11 }
                        }
                    }
                    Row {
                        id: btns; anchors.right: parent.right; anchors.rightMargin: 10; anchors.verticalCenter: parent.verticalCenter; spacing: 6
                        FButton { text: "Indítás"; primary: true; onClicked: settings.programLaunch(row.m.id) }
                        FButton { visible: row.m.canUpdate; text: "Frissítés"; enabled: !p.job.running; onClicked: p.startJob(settings.programUpdate(row.m.id)) }
                        FButton { text: "Eltávolítás"; enabled: !p.job.running; onClicked: { p.confirm = row.m.id; p.openId = row.m.id } }
                    }
                    Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: "#232c38" }
                }
                // részletek
                Column {
                    visible: row.isOpen; width: parent.width
                    // eltávolítás megerősítése
                    Rectangle {
                        visible: p.confirm === row.m.id; width: parent.width; height: 48; color: "#2a1a1d"
                        Text { x: 58; anchors.verticalCenter: parent.verticalCenter; text: "Biztosan eltávolítja: " + row.m.name + "?"
                               color: Theme.text; font.family: Theme.font; font.pixelSize: 13 }
                        Row {
                            anchors.right: parent.right; anchors.rightMargin: 10; anchors.verticalCenter: parent.verticalCenter; spacing: 10
                            FCheck { id: withData; text: "a program adatai és beállításai is"; checked: false }
                            FButton { text: "Eltávolítás"; danger: true; onClicked: p.startJob(settings.programRemove(row.m.id, withData.checked)) }
                            FButton { text: "Mégse"; flat: true; onClicked: p.confirm = "" }
                        }
                    }
                    InfoRow { label: "Típus"; value: row.m.typeName + (row.m.type === "win64" ? " — futtató: Fusion Windows Runtime (fwr)" : row.m.type === "flatpak" ? " — homokozóban fut" : "") }
                    InfoRow { visible: row.m.appid !== ""; label: "Flatpak-azonosító"; value: row.m.appid; mono: true }
                    InfoRow { visible: row.m.exe !== ""; label: "Program"; value: row.m.exe; mono: true }
                    InfoRow { label: "Helye"; value: row.m.dir + (row.m.prefix && row.m.prefix.indexOf(row.m.dir + "/") !== 0 ? "\nWindows-környezet: " + row.m.prefix : ""); mono: true }
                    InfoRow { visible: Object.keys(row.m.folders).length > 0; label: "Látott mappák"
                              value: Object.keys(row.m.folders).map(k => k + ":  ~/" + row.m.folders[k]).join("\n"); mono: true }
                    InfoRow { label: "Telepítve"; value: [row.m.installed, row.m.source].filter(x => x).join("  ·  ") }
                    InfoRow { icon: "lock"; label: "Védelem"; value: (row.m.protection || "")
                                  + (row.m.allowFiles ? "\nMappák: " + row.m.allowFiles : "")
                                  + (row.m.net === false ? "\nHálózat: tiltva" : "")
                              valueColor: row.m.sandbox || row.m.type === "flatpak" ? Theme.ok : Theme.dim }
                    // eszköz-hozzáférés (Windows-programok soros portjai)
                    Repeater {
                        model: row.m.type === "win64" ? p.roles : []
                        InfoRow {
                            property string com: {
                                var d = row.m.devices
                                for (var k in d) if (d[k] === modelData.role) return k
                                if (modelData.com && !d[modelData.com]) return modelData.com
                                for (var i = 3; i < 10; i++) if (!d["COM" + i]) return "COM" + i
                                return ""
                            }
                            property bool on: Object.keys(row.m.devices).some(k => row.m.devices[k] === modelData.role)
                            icon: modelData.role === "laser" ? "laser" : modelData.role === "printer" ? "printer" : "usb"
                            label: "Eszköz: " + modelData.name
                            value: on ? "hozzáfér — a programban: " + com : "nem fér hozzá"
                            valueColor: on ? Theme.ok : Theme.dim
                            FButton { text: parent.parent.on ? "Tiltás" : "Engedélyezés (" + parent.parent.com + ")"
                                      onClicked: { var e = settings.programDevice(row.m.id, parent.parent.com, parent.parent.on ? "" : modelData.role); p.act(e); settings.programsRefresh() } }
                        }
                    }
                }
            }
        }
        Text { visible: p.progs.length === 0; padding: 14; text: "Nincs telepített program."; color: Theme.dim; font.family: Theme.font }
        Repeater {
            model: p.recipes
            InfoRow { icon: "app"; label: modelData.name; value: "Ismert program, nincs telepítve — telepítő: " + (modelData.match || "?") + " (lent: Telepítés fájlból)"; valueColor: Theme.dim }
        }
    }

    // --- telepítés fájlból ---
    Section {
        title: "TELEPÍTÉS FÁJLBÓL (Windows: .exe, .msi · Linux: Flatpak, AppImage, archívum)"
        Rectangle {
            width: parent.width; height: srcCol.implicitHeight + 20; color: "transparent"
            Column {
                id: srcCol; x: 14; y: 10; width: parent.width - 28; spacing: 8
                Row {
                    spacing: 8; width: parent.width
                    FTextField { id: srcField; width: parent.width - instBtn.width - filesBtn.width - 16; placeholderText: "a telepítő vagy program teljes útja"
                                 onTextChanged: p.chosen = text }
                    FButton { id: filesBtn; text: "Fájlkezelő"; icon: "files"; onClicked: settings.spawn("fusion-files /data/import") }
                    FButton { id: instBtn; text: "Telepítés"; primary: true; enabled: p.chosen !== "" && !p.job.running
                              onClicked: p.startJob(settings.programInstall(p.chosen, nameField.text, portable.checked)) }
                }
                Row {
                    spacing: 14
                    Text { anchors.verticalCenter: parent.verticalCenter; text: p.chosen ? settings.programDetect(p.chosen) : ""; color: Theme.dim; font.family: Theme.font; font.pixelSize: 12 }
                    FTextField { id: nameField; width: 220; placeholderText: "név (nem kötelező)" }
                    FCheck { id: portable; text: "hordozható .exe (nincs telepítője)"; visible: /\.exe$/i.test(p.chosen) }
                }
            }
        }
        Repeater {
            model: p.inst
            Rectangle {
                width: parent.width; height: 34; color: modelData.path === p.chosen ? Theme.selected : (ima.containsMouse ? Theme.hover : "transparent")
                FIcon { x: 14; anchors.verticalCenter: parent.verticalCenter; name: /\.(exe|msi)$/i.test(modelData.name) ? "file-exe" : "package"; size: 16 }
                Text { x: 40; anchors.verticalCenter: parent.verticalCenter; width: parent.width - 220; elide: Text.ElideMiddle
                       text: modelData.path; color: Theme.text; font.family: Theme.font; font.pixelSize: 12 }
                Text { anchors.right: parent.right; anchors.rightMargin: 14; anchors.verticalCenter: parent.verticalCenter
                       text: modelData.size + "   " + modelData.date; color: Theme.dim; font.family: Theme.font; font.pixelSize: 11 }
                MouseArea { id: ima; anchors.fill: parent; hoverEnabled: true; onClicked: p.chooseFile(modelData.path) }
            }
        }
        Text { visible: p.inst.length === 0; padding: 14; width: parent.width; wrapMode: Text.Wrap
               text: "Nem található telepítő a szokásos helyeken (saját mappa, Letöltések, /data/import, USB-meghajtók). Írja be az útját, vagy nyissa meg a Fájlkezelőben (Enter a fájlon)."
               color: Theme.dim; font.family: Theme.font }
    }

    // --- Flathub: a Programboltban ---
    Section {
        title: "LINUX-PROGRAMOK A FLATHUBRÓL"
        InfoRow { icon: "store"; label: "Programbolt"; value: "Népszerű programok, kategóriák, keresés, képernyőképek — telepítés egy kattintással"
                  FButton { text: "Programbolt"; icon: "store"; primary: true; onClicked: win.cur = win.pages.findIndex(x => x.id === "store") } }
    }
    // --- fejlesztői eszközök ---
    Section {
        title: "FEJLESZTŐI ESZKÖZÖK (a DATA-n; a Terminálban: node, npm, wrangler)"
        InfoRow {
            icon: "file-code"; label: "Node.js (LTS)"
            value: !p.devLoaded ? "…" : (p.dev.node ? p.dev.node + "  ·  npm " + p.dev.npm : "nincs telepítve — a nodejs.org-ról, ellenőrzőösszeggel")
            valueColor: p.dev.node ? Theme.ok : Theme.dim
            FButton { visible: !p.dev.node; text: "Telepítés"; primary: true; onClicked: settings.openTerminal("dev-install-node") }
            FButton { visible: !!p.dev.node; text: "Frissítés"; onClicked: settings.openTerminal("dev-update-node") }
            FButton { visible: !!p.dev.node; text: "Eltávolítás"; flat: true; onClicked: settings.openTerminal("dev-remove-node") }
        }
        InfoRow {
            icon: "cloud"; label: "Cloudflare Wrangler"
            value: !p.devLoaded ? "…" : (p.dev.wrangler ? p.dev.wrangler : (p.dev.node ? "nincs telepítve" : "előbb a Node.js kell"))
            valueColor: p.dev.wrangler ? Theme.ok : Theme.dim
            FButton { visible: !p.dev.wrangler; enabled: !!p.dev.node; text: "Telepítés"; primary: true; onClicked: settings.openTerminal("dev-install-wrangler") }
            FButton { visible: !!p.dev.wrangler; text: "Bejelentkezés"; icon: "web"; onClicked: settings.openTerminal("wrangler-login") }
            FButton { visible: !!p.dev.wrangler; text: "Frissítés"; onClicked: settings.openTerminal("dev-update-wrangler") }
            FButton { visible: !!p.dev.wrangler; text: "Eltávolítás"; flat: true; onClicked: settings.openTerminal("dev-remove-wrangler") }
        }
    }
    FButton { text: "A Windows-futtatókörnyezet ellenőrzése (fwr check)"; icon: "check"; onClicked: settings.openTerminal("fwrcheck") }
}
