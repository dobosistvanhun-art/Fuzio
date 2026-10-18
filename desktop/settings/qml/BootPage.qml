// Indítás: a gép UEFI-bejegyzései (F9 menü) — mire mutatnak, melyik az alapértelmezett, melyik árvult el
import QtQuick
import QtQuick.Controls
import FusionUI

SettingsPage {
    id: p
    title: "Indítás"
    subtitle: "A gép indítási bejegyzései (UEFI, F9 menü): alapértelmezett rendszer, egyszeri indítás, elárvult bejegyzések törlése"
    property var s: ({ entries: [], error: "" })
    property string open: ""          // a kinyitott bejegyzés száma (törlés megerősítése)
    property string msg: ""
    property bool msgErr: false
    onRefresh: settings.bootRefresh()
    Component.onCompleted: settings.bootRefresh()
    Connections {
        target: settings
        function onResult(tag, r) {
            if (tag === "boot" && r.entries !== undefined) p.s = r
            else if (tag === "boot-action") { p.msg = r.msg || ""; p.msgErr = !r.ok; p.open = ""; settings.bootRefresh() }
        }
    }
    function kindText(e) {
        if (e.managed) return "Fúzió — mérési / tartalék bejegyzés (a Fúzió tartja karban)"
        if (e.kind === "fusion") return "Fúzió (ez a lemez)"
        if (e.kind === "installer") return "Fúzió telepítő pendrive"
        if (e.kind === "usb") return "USB-eszköz"
        if (e.kind === "firmware") return "a gép saját bejegyzése (hálózat, beépített eszköz)"
        if (/ubuntu|mint/i.test(e.label)) return "Linux Mint / Ubuntu (GRUB)"
        if (/windows/i.test(e.label)) return "Windows"
        return "másik rendszer"
    }
    Section {
        title: "BEJEGYZÉSEK — A SORRENDBEN AZ ELSŐ INDUL"
        InfoRow { visible: p.s.error !== ""; icon: "info"; label: "Hiba"; value: p.s.error; valueColor: Theme.danger }
        Repeater {
            model: p.s.entries
            Rectangle {
                width: parent.width; height: col.height + 16; color: modelData.current ? Theme.selected : "transparent"
                FIcon { x: 14; y: 12; size: 22
                        name: modelData.kind === "fusion" || modelData.kind === "installer" ? "chip" : modelData.kind === "usb" ? "drive-usb"
                              : modelData.kind === "firmware" ? "settings" : "drive" }
                Column {
                    id: col; x: 48; y: 8; width: parent.width - 60; spacing: 4
                    Row {
                        spacing: 8
                        Text { text: modelData.label || ("Boot" + modelData.num); color: Theme.text; font.family: Theme.font; font.pixelSize: 14; font.bold: true }
                        Repeater {
                            model: [modelData.pos === 0 ? ["ALAPÉRTELMEZETT", Theme.accent] : null,
                                    modelData.current ? ["MOST FUT", Theme.ok] : null,
                                    modelData.next ? ["KÖVETKEZŐ INDÍTÁS", Theme.warn] : null,
                                    modelData.orphan ? ["ELÁRVULT", Theme.danger] : null].filter(x => x)
                            Rectangle { height: 18; width: bt.implicitWidth + 12; radius: 9; color: "transparent"; border.color: modelData[1]
                                        anchors.verticalCenter: parent.verticalCenter
                                        Text { id: bt; anchors.centerIn: parent; text: modelData[0]; color: modelData[1]; font.family: Theme.font
                                               font.pixelSize: 10; font.bold: true } }
                        }
                    }
                    Text { width: parent.width; wrapMode: Text.Wrap; color: Theme.dim; font.family: Theme.font; font.pixelSize: 12
                           text: p.kindText(modelData) + "   ·   Boot" + modelData.num
                                 + (modelData.disk ? "   ·   " + modelData.disk + (modelData.model ? " (" + modelData.model + ")" : "") : "")
                                 + (modelData.orphan ? "   ·   a lemez vagy a fájl már nincs meg" : "") }
                    Text { visible: modelData.path !== ""; width: parent.width; elide: Text.ElideMiddle; text: modelData.path
                           color: Theme.dim; font.family: Theme.mono; font.pixelSize: 11 }
                    Flow {
                        width: parent.width; spacing: 8; topPadding: 2
                        visible: !modelData.managed
                        FButton { visible: modelData.pos !== 0 && !modelData.orphan; text: "Legyen ez az alapértelmezett"; icon: "check"
                                  onClicked: settings.bootAction("first", modelData.num, "") }
                        FButton { visible: !modelData.current && !modelData.orphan; text: "Csak a következő indításkor"; flat: true
                                  onClicked: settings.bootAction("next", modelData.num, "") }
                        FButton { visible: modelData.deletable && p.open !== modelData.num; text: "Törlés…"; icon: "trash"; flat: true
                                  onClicked: { p.open = modelData.num; confirmField.text = "" } }
                    }
                    Row {
                        visible: p.open === modelData.num; spacing: 8
                        FLabel { height: 32; text: "A törléshez írja be a nevét: " + modelData.label; dim: true }
                        FTextField { id: confirmField; width: 200; placeholderText: modelData.label }
                        FButton { text: "Törlés"; danger: true; enabled: confirmField.text === modelData.label
                                  onClicked: settings.bootAction("delete", modelData.num, confirmField.text) }
                        FButton { text: "Mégse"; flat: true; onClicked: p.open = "" }
                    }
                }
                Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.border }
            }
        }
    }
    Text { visible: p.msg !== ""; text: p.msg; color: p.msgErr ? Theme.danger : Theme.ok; font.family: Theme.font; font.pixelSize: 13 }
    Section {
        title: "TUDNIVALÓK"
        InfoRow { label: "Alapértelmezett"; value: "a sorrendben az első bejegyzés indul magától; a többi az F9 menüből (bekapcsoláskor) választható" }
        InfoRow { label: "Elárvult"; value: "a bejegyzés egy már nem létező lemezre vagy fájlra mutat (pl. egy régi pendrive) — nyugodtan törölhető" }
        InfoRow { label: "Védett"; value: "a most futó rendszer bejegyzése és a gép saját bejegyzései nem törölhetők; a mérési bejegyzéseket a Fúzió kezeli" }
        InfoRow { label: "A Mint"; value: "a Mint törlése előtt ne törölje az ubuntu-bejegyzést — utána igen (a Mint lemezén az EFI-mappa is törölhető)" }
    }
}
