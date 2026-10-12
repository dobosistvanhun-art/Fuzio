// Nyomtatók (papír): felvett nyomtatók, keresés (USB és hálózat), felvétel, alapértelmezett, próbaoldal, feladatok (CUPS)
import QtQuick
import QtQuick.Controls
import FusionUI

SettingsPage {
    id: p
    title: "Nyomtatók"
    subtitle: "Papírnyomtatók — CUPS (a 3D nyomtató: „3D nyomtató (Klipper)”)"
    property var st: ({ printers: [], jobs: [], service: "" })
    property var found: []
    property bool searched: false
    property bool searching: false
    property bool adding: false
    property var drv: ({ model: "", drivers: [] })   // kézi meghajtóválasztás
    property var pick: null                           // a felvenni kívánt eszköz (ha nincs automatikus meghajtó)
    property string msg: ""
    property bool msgErr: false
    busy: searching || adding
    onRefresh: settings.prnRefresh()
    Component.onCompleted: settings.prnRefresh()
    Timer { interval: 3000; running: true; repeat: true; onTriggered: settings.prnRefresh() }
    function say(t, err) { msg = t; msgErr = err }
    Connections {
        target: settings
        function onResult(tag, r) {
            if (tag === "prn") {
                if (r.printers) p.st = r
            } else if (tag === "prn-discover") {
                p.searching = false; p.searched = true
                if (r.error) p.say("A keresés nem sikerült: " + r.error, true)
                p.found = r.devices || []
            } else if (tag === "prn-drivers") {
                p.drv = r
            } else if (tag === "prn-add") {
                p.adding = false
                if (r.ok) {
                    p.say("Felvéve: " + r.name + " — próbaoldal: a nyomtató sorában.", false)
                    p.pick = null; p.found = p.found.map(d => d.uri === r.uri ? Object.assign({}, d, { added: true }) : d)
                } else if (r.uri && !p.pick) {
                    // nincs automatikus meghajtó: választás a listából
                    p.pick = { uri: r.uri, model: r.model }
                    p.say("Nem sikerült automatikusan: " + r.msg + " — válasszon meghajtót lent.", true)
                    settings.prnDrivers(r.model || "")
                } else p.say("Nem sikerült: " + (r.msg || r.error), true)
                settings.prnRefresh()
            } else if (tag === "prn-action") {
                if (!r.ok) p.say(r.msg || r.error, true); else if (r.msg) p.say(r.msg, false); else p.msg = ""
                settings.prnRefresh()
            } else if (tag === "service-restart") {
                p.say(r.rc === 0 ? "A nyomtatási szolgáltatás újraindult." : "Hiba: " + r.msg, r.rc !== 0)
                settings.prnRefresh()
            }
        }
    }

    Text { visible: p.msg !== ""; width: parent.width; wrapMode: Text.Wrap; text: p.msg
           color: p.msgErr ? Theme.danger : Theme.ok; font.family: Theme.font; font.pixelSize: 13 }

    Section {
        title: "NYOMTATÓK"
        Repeater {
            model: p.st.printers
            Rectangle {
                width: parent.width; height: Math.max(58, pcol.implicitHeight + 18); color: "transparent"
                Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: "#232c38" }
                FIcon { name: "print"; size: 22; x: 14; anchors.verticalCenter: parent.verticalCenter }
                Column {
                    id: pcol; x: 50; anchors.verticalCenter: parent.verticalCenter; width: parent.width - 50 - pbtn.width - 20; spacing: 2
                    Text { width: parent.width; elide: Text.ElideRight; color: Theme.text; font.family: Theme.font; font.pixelSize: 14; font.bold: true
                           text: modelData.info + (modelData.default ? "   (alapértelmezett)" : "") }
                    Text { width: parent.width; elide: Text.ElideRight; color: Theme.dim; font.family: Theme.font; font.pixelSize: 12
                           text: modelData.connection + (modelData.model ? "  ·  " + modelData.model : "") }
                    Text { width: parent.width; wrapMode: Text.Wrap; font.family: Theme.font; font.pixelSize: 12
                           color: modelData.state === 5 || modelData.reasonsText.length ? Theme.warn : (modelData.state === 4 ? Theme.accent : Theme.ok)
                           text: modelData.stateText + (modelData.reasonsText.length ? " — " + modelData.reasonsText.join(", ") : "") }
                }
                Row {
                    id: pbtn; anchors.right: parent.right; anchors.rightMargin: 10; anchors.verticalCenter: parent.verticalCenter; spacing: 6
                    FButton { visible: modelData.state === 5 || !modelData.accepting; text: "Folytatás"; icon: "restart"
                              tip: "A leállított nyomtató újraindítása"; onClicked: settings.prnEnable(modelData.name) }
                    FButton { text: "Próbaoldal"; onClicked: { p.msg = ""; settings.prnTest(modelData.name) } }
                    FToolButton { visible: !modelData.default; icon: "star"; tip: "Legyen az alapértelmezett"; onClicked: settings.prnDefault(modelData.name) }
                    FToolButton { icon: "trash"; tip: "Eltávolítás"; onClicked: { p.msg = ""; settings.prnRemove(modelData.name) } }
                }
            }
        }
        Text { visible: p.st.printers.length === 0; padding: 14; width: parent.width; wrapMode: Text.Wrap
               color: Theme.dim; font.family: Theme.font
               text: "Még nincs felvett nyomtató. Kapcsolja be a nyomtatót (USB-n csatlakoztatva, vagy ugyanazon a hálózaton), majd: Keresés." }
    }

    Section {
        title: "NYOMTATÁSI FELADATOK"
        visible: p.st.jobs.length > 0
        Repeater {
            model: p.st.jobs
            InfoRow { icon: "file"; label: modelData.id; value: modelData.user + "  ·  " + Math.round(modelData.size / 1024) + " kB  ·  " + modelData.time
                      FButton { text: "Törlés"; flat: true; onClicked: settings.prnCancel(modelData.id) } }
        }
    }

    Section {
        title: "NYOMTATÓ HOZZÁADÁSA" + (p.searching ? "  —  keresés (10–20 mp)…" : "")
        InfoRow {
            icon: "search"; label: "Keresés"
            value: "USB-n csatlakoztatott és hálózati nyomtatók. A korszerű nyomtatók meghajtó nélkül működnek (IPP Everywhere / AirPrint)."
            FButton { text: p.searching ? "Keresés…" : "Keresés"; primary: true; enabled: !p.searching && !p.adding
                      onClicked: { p.msg = ""; p.pick = null; p.searching = true; settings.prnDiscover() } }
        }
        Repeater {
            model: p.found
            InfoRow {
                icon: modelData.connection === "USB" ? "usb" : "web"
                label: modelData.info
                value: modelData.connection + (modelData.driverless ? "  ·  meghajtó nélkül" : "") + "\n" + modelData.uri
                valueColor: Theme.dim; mono: false
                FButton { text: modelData.added ? "Felvéve" : "Felvétel"; enabled: !modelData.added && !p.adding
                          onClicked: { p.msg = ""; p.pick = null; p.adding = true
                                       settings.prnAdd(modelData.uri, modelData.model, modelData.info, "") } }
            }
        }
        Text { visible: p.searched && !p.searching && p.found.length === 0; padding: 14; width: parent.width; wrapMode: Text.Wrap
               color: Theme.dim; font.family: Theme.font
               text: "Nem található nyomtató. Be van kapcsolva? USB: próbáljon másik kábelt / portot. Hálózat: ugyanazon a Wi-Fin van?" }
        InfoRow {
            icon: "file"; label: "PDF-nyomtató"; value: "„nyomtatás” PDF-fájlba (a ~/PDF mappába) — minden programból"
            visible: !p.st.printers.some(x => x.uri.indexOf("cups-pdf") === 0)
            FButton { text: "Felvétel"; enabled: !p.adding; onClicked: { p.msg = ""; p.adding = true; settings.prnAddPdf() } }
        }
    }

    // kézi meghajtóválasztás (ha a nyomtató nem driverless, és nincs automatikus találat)
    Section {
        title: "MEGHAJTÓ VÁLASZTÁSA"
        visible: p.pick !== null
        InfoRow { icon: "print"; label: "Nyomtató"; value: (p.pick ? (p.pick.model || p.pick.uri) : "") }
        Row {
            x: 14; spacing: 8; height: 46
            FTextField { id: mf; width: 300; anchors.verticalCenter: parent.verticalCenter; placeholderText: "gyártó és típus, pl. HP LaserJet 1020"
                         text: p.pick ? p.pick.model : ""; onAccepted: settings.prnDrivers(text) }
            FButton { text: "Keresés"; anchors.verticalCenter: parent.verticalCenter; onClicked: settings.prnDrivers(mf.text) }
        }
        Repeater {
            model: (p.drv.drivers || []).slice(0, 12)
            InfoRow { icon: "dot"; label: ""; value: modelData.name
                      FButton { text: "Ezzel"; enabled: !p.adding
                                onClicked: { p.adding = true; settings.prnAdd(p.pick.uri, p.pick.model, p.pick.model, modelData.ppd) } } }
        }
        Text { visible: (p.drv.drivers || []).length === 0; padding: 14; color: Theme.dim; font.family: Theme.font
               text: "Nincs találat — próbáljon rövidebb nevet (pl. csak a sorozatot)." }
    }

    Section {
        title: "SZOLGÁLTATÁS"
        InfoRow { icon: "info"; label: "CUPS"; value: p.st.service || "—"; mono: true
                  FButton { text: "Webes felület"; flat: true; tip: "http://localhost:631 — haladó beállítások"; onClicked: settings.prnWeb() }
                  FButton { text: "Újraindítás"; icon: "restart"; onClicked: { p.msg = ""; settings.serviceRestart("cups") } } }
    }
}
