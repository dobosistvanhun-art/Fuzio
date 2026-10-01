// Programbolt: a Flathub katalógusa — népszerű programok, kategóriák, keresés, részletek.
// A telepítést a Programkezelő háttere végzi (fusion-programs install flathub:<azonosító>), értesítéssel.
import QtQuick
import QtQuick.Controls
import FusionUI

SettingsPage {
    id: p
    title: "Programbolt"
    subtitle: "Linux-programok a Flathubról — telepítés egy kattintással, root nélkül, a DATA-ra"
    property string kind: "popular"
    property string arg: ""
    property int page: 1
    property int pages: 1
    property var apps: []
    property var icons: ({})
    property var installed: ({})        // appid → Programkezelő-azonosító
    property bool loading: false
    property string error: ""
    property var detail: null           // a kinyitott program részletei
    property bool detailLoading: false
    property var shots: []
    property var job: ({ running: false, lines: [], rc: null, title: "" })
    property string pendingId: ""
    property string msg: ""
    readonly property var cats: settings.storeCategories()
    busy: loading || detailLoading || job.running
    onRefresh: load(kind, arg, 1)
    Component.onCompleted: { if (win.param && win.param.indexOf("search:") === 0) { q.text = win.param.substring(7); load("search", q.text, 1) } else load("popular", "", 1); settings.programJobWatch() }

    function load(k, a, pg) {
        p.kind = k; p.arg = a; p.page = pg; p.error = ""; p.loading = true; p.detail = null
        if (pg === 1) p.apps = []
        settings.storeList(k, a, pg)
    }
    function openApp(appid) { p.detail = { appid: appid, name: "", summary: "" }; p.shots = []; p.detailLoading = true; settings.storeDetails(appid) }
    function install(appid, name) {
        var e = settings.programInstall("flathub:" + appid, "", false)
        if (e) p.msg = "hiba: " + e; else { p.msg = ""; p.pendingId = appid }
    }
    function title_of() {
        if (p.kind === "search") return "Találatok: „" + p.arg + "”"
        if (p.kind === "category") { var c = p.cats.find(x => x.id === p.arg); return c ? c.name : p.arg }
        return "Népszerű programok"
    }
    Connections {
        target: settings
        function onResult(tag, r) {
            if (tag === "store-list") {
                if (r.kind !== p.kind || r.arg !== p.arg || r.page !== p.page) return
                p.loading = false
                if (r.error) { p.error = r.error; return }
                p.apps = p.page === 1 ? r.apps : p.apps.concat(r.apps)
                p.pages = r.pages; p.installed = r.installed
                var ic = Object.assign({}, p.icons, r.icons); p.icons = ic
            } else if (tag === "store-icons") {
                var ic2 = Object.assign({}, p.icons, r); p.icons = ic2
            } else if (tag === "store-details") {
                if (!p.detail || r.appid !== p.detail.appid) return
                p.detailLoading = false
                p.detail = r
            } else if (tag === "store-shots") {
                if (p.detail && r.appid === p.detail.appid) p.shots = r.files
            } else if (tag === "program-job") {
                var was = p.job.running
                p.job = r
                if ((was || p.pendingId) && !r.running) {
                    p.pendingId = ""
                    p.installed = settings.storeInstalled()
                    if (p.detail && p.detail.appid) { var d = Object.assign({}, p.detail); d.pid = p.installed[d.appid] || ""; p.detail = d }
                }
            }
        }
    }

    // --- keresés + kategóriák ---
    Row {
        spacing: 8; width: parent.width
        FTextField { id: q; width: Math.min(420, parent.width - 120); placeholderText: "Keresés a Flathubon, pl. inkscape, freecad, gimp, kicad"
                     onAccepted: if (text.trim()) p.load("search", text.trim(), 1) }
        FButton { text: "Keresés"; icon: "search"; primary: true; enabled: q.text.trim() !== ""; onClicked: p.load("search", q.text.trim(), 1) }
    }
    Flow {
        width: parent.width; spacing: 6
        FButton { text: "Népszerű"; icon: "star"; checked: p.kind === "popular" && !p.detail; onClicked: p.load("popular", "", 1) }
        Repeater {
            model: p.cats
            FButton { text: modelData.name; icon: modelData.icon; checked: p.kind === "category" && p.arg === modelData.id && !p.detail
                      onClicked: p.load("category", modelData.id, 1) }
        }
    }

    // --- folyamatban lévő telepítés ---
    Rectangle {
        visible: p.job.running
        width: parent.width; height: 44; radius: Theme.radius; color: "#1b222c"; border.color: Theme.border
        BusyIndicator { x: 8; anchors.verticalCenter: parent.verticalCenter; width: 24; height: 24; running: p.job.running }
        Column {
            x: 42; anchors.verticalCenter: parent.verticalCenter; width: parent.width - 54
            Text { text: p.job.title; color: Theme.text; font.family: Theme.font; font.pixelSize: 13; font.bold: true; elide: Text.ElideRight; width: parent.width }
            Text { text: p.job.lines.length ? p.job.lines[p.job.lines.length - 1] : ""; color: Theme.dim; font.family: Theme.mono; font.pixelSize: 11
                   elide: Text.ElideRight; width: parent.width; textFormat: Text.PlainText }
        }
    }
    Text { visible: p.msg !== ""; text: p.msg; color: Theme.danger; font.family: Theme.font; width: parent.width; wrapMode: Text.Wrap }

    // --- lista ---
    Column {
        visible: !p.detail; width: parent.width; spacing: 12
        Text { text: p.title_of() + (p.loading && p.apps.length === 0 ? " — betöltés…" : ""); color: Theme.dim; font.family: Theme.font; font.pixelSize: 12; font.bold: true }
        Text { visible: p.error !== ""; text: p.error; color: Theme.danger; font.family: Theme.font; width: parent.width; wrapMode: Text.Wrap }
        Text { visible: !p.loading && !p.error && p.apps.length === 0; text: "Nincs találat."; color: Theme.dim; font.family: Theme.font }
        Flow {
            id: grid; width: parent.width; spacing: 10
            readonly property int cols: Math.max(1, Math.floor((width + spacing) / 300))
            readonly property real cw: (width - (cols - 1) * spacing) / cols
            Repeater {
                model: p.apps
                Rectangle {
                    width: grid.cw; height: 92; radius: Theme.radius
                    color: cma.containsMouse ? Theme.hover : "#1b222c"; border.color: Theme.border
                    property bool have: !!p.installed[modelData.appid]
                    MouseArea { id: cma; anchors.fill: parent; hoverEnabled: true; onClicked: p.openApp(modelData.appid) }
                    Image { x: 12; anchors.verticalCenter: parent.verticalCenter; width: 56; height: 56; sourceSize.width: 112; sourceSize.height: 112
                            fillMode: Image.PreserveAspectFit; asynchronous: true
                            source: p.icons[modelData.appid] ? "file://" + p.icons[modelData.appid] : "" }
                    FIcon { x: 24; anchors.verticalCenter: parent.verticalCenter; visible: !p.icons[modelData.appid]; name: "app-app"; size: 32 }
                    Column {
                        x: 80; y: 12; width: parent.width - 92; spacing: 3
                        Row { spacing: 6; width: parent.width
                            Text { text: modelData.name; color: Theme.text; font.family: Theme.font; font.pixelSize: 14; font.bold: true
                                   elide: Text.ElideRight; width: Math.min(implicitWidth, parent.width - (vb.visible ? vb.width + 6 : 0)) }
                            FIcon { id: vb; visible: modelData.verified; name: "check"; size: 14; anchors.verticalCenter: parent.verticalCenter } }
                        Text { text: modelData.summary; color: Theme.dim; font.family: Theme.font; font.pixelSize: 12; wrapMode: Text.Wrap
                               maximumLineCount: 2; elide: Text.ElideRight; width: parent.width }
                        Text { text: parent.parent.have ? "Telepítve" : (p.pendingId === modelData.appid ? "Telepítés folyamatban…" : "")
                               visible: text !== ""; color: Theme.ok; font.family: Theme.font; font.pixelSize: 11 }
                    }
                }
            }
        }
        FButton { visible: !p.loading && p.page < p.pages && p.apps.length > 0; text: "Továbbiak"; icon: "plus"
                  onClicked: { p.page = p.page + 1; p.loading = true; settings.storeList(p.kind, p.arg, p.page) } }
        Text { visible: p.loading && p.apps.length > 0; text: "betöltés…"; color: Theme.dim; font.family: Theme.font }
        Text { text: "Forrás: flathub.org — a programokat a fejlesztőik és a Flathub közössége teszi közzé; a pipa = ellenőrzött kiadó."
               color: Theme.dim; font.family: Theme.font; font.pixelSize: 11; width: parent.width; wrapMode: Text.Wrap }
    }

    // --- részletek ---
    Column {
        visible: !!p.detail; width: parent.width; spacing: 14
        FButton { text: "Vissza"; icon: "folder-up"; flat: true; onClicked: p.detail = null }
        Text { visible: p.detailLoading; text: "betöltés…"; color: Theme.dim; font.family: Theme.font }
        Text { visible: !!p.detail && !!p.detail.error; text: p.detail && p.detail.error ? p.detail.error : ""; color: Theme.danger; font.family: Theme.font }
        Row {
            visible: !!p.detail && !!p.detail.name; spacing: 18; width: parent.width
            Image { width: 96; height: 96; sourceSize.width: 192; sourceSize.height: 192; fillMode: Image.PreserveAspectFit
                    source: p.detail && p.detail.iconFile ? "file://" + p.detail.iconFile : "" }
            Column {
                width: parent.width - 96 - 18 - acts.width - 18; spacing: 4
                Text { text: p.detail ? p.detail.name : ""; color: Theme.text; font.family: Theme.font; font.pixelSize: 22; font.bold: true; width: parent.width; elide: Text.ElideRight }
                Text { text: p.detail ? p.detail.summary : ""; color: Theme.text; font.family: Theme.font; font.pixelSize: 14; width: parent.width; wrapMode: Text.Wrap }
                Text { text: p.detail ? [p.detail.developer, p.detail.verified ? "ellenőrzött kiadó" : "", p.detail.version ? "változat " + p.detail.version : "",
                                         p.detail.date].filter(x => x).join("  ·  ") : ""
                       color: Theme.dim; font.family: Theme.font; font.pixelSize: 12; width: parent.width; wrapMode: Text.Wrap }
                Text { text: p.detail ? [p.detail.downloadText ? "letöltés: " + p.detail.downloadText : "", p.detail.installedText ? "telepítve: " + p.detail.installedText : "",
                                         p.detail.license ? "licenc: " + p.detail.license + (p.detail.free ? "" : " (nem szabad)") : ""].filter(x => x).join("  ·  ") : ""
                       color: Theme.dim; font.family: Theme.font; font.pixelSize: 12; width: parent.width; wrapMode: Text.Wrap }
            }
            Column {
                id: acts; spacing: 6
                property bool have: !!p.detail && !!p.installed[p.detail.appid]
                FButton { visible: !acts.have; text: p.pendingId === (p.detail ? p.detail.appid : "") ? "Telepítés…" : "Telepítés"; primary: true; icon: "download"
                          enabled: !p.job.running; onClicked: p.install(p.detail.appid, p.detail.name) }
                FButton { visible: acts.have; text: "Indítás"; primary: true; onClicked: settings.programLaunch(p.installed[p.detail.appid]) }
                FButton { visible: acts.have; text: "Programkezelő"; icon: "package"; flat: true; onClicked: win.cur = win.pages.findIndex(x => x.id === "programs") }
            }
        }
        Text { text: p.detail && p.detail.description ? p.detail.description : ""; color: Theme.text; font.family: Theme.font; font.pixelSize: 13
               width: parent.width; wrapMode: Text.Wrap; textFormat: Text.PlainText; lineHeight: 1.15 }
        // képernyőképek
        Flow {
            width: parent.width; spacing: 10
            visible: p.shots.length > 0
            Repeater {
                model: p.shots
                Image { width: (parent.width - 10) / 2; height: width * 0.62; fillMode: Image.PreserveAspectFit; asynchronous: true
                        sourceSize.width: 900; source: "file://" + modelData }
            }
        }
        Text { visible: !!p.detail && p.shots.length === 0 && p.detail.screenshots && p.detail.screenshots.length > 0
               text: "képernyőképek betöltése…"; color: Theme.dim; font.family: Theme.font; font.pixelSize: 12 }
        Text { visible: !!p.detail && !!p.detail.homepage; text: p.detail ? "Honlap: " + p.detail.homepage : ""; color: Theme.dim
               font.family: Theme.font; font.pixelSize: 12; width: parent.width; elide: Text.ElideRight }
    }
}
