// Mentés (T3): a DATA (programok, beállítások, Wi-Fi, saját fájlok) egy külső lemezre — visszaállítás a Fusion
// Telepítőben (új telepítés + „DATA visszaállítása mentésből”)
import QtQuick
import QtQuick.Controls
import FusionUI

SettingsPage {
    id: p
    title: "Mentés"
    subtitle: "A DATA (programok, beállítások, Wi-Fi, saját fájlok) mentése egy külső lemezre vagy pendrive-ra"
    property var s: ({ targets: [], backups: [], dataUsedText: "", error: "" })
    property var job: ({ running: false, lines: [], rc: null, title: "" })
    property string chosen: ""
    property string msg: ""
    property var auto: ({ enabled: false, keep: 4, target: "", targetError: "", last: null, lastText: "", days: 7, error: "" })
    function setKeep(n) { var e = settings.backupAutoSet(p.auto.enabled === true, n); p.msg = e ? "hiba: " + e : "" }
    busy: job.running
    onRefresh: settings.backupRefresh()
    Component.onCompleted: { settings.backupRefresh(); settings.backupJobWatch(); settings.backupAutoRefresh() }
    Timer { interval: 6000; running: p.visible && !p.job.running; repeat: true; onTriggered: settings.backupRefresh() }
    Connections {
        target: settings
        function onResult(tag, r) {
            if (tag === "backup" && r.targets !== undefined) {
                p.s = r
                if (r.job && !p.job.running) p.job = r.job
                if (p.chosen && !r.targets.find(t => t.mountpoint === p.chosen && t.ok)) p.chosen = ""
                if (!p.chosen) { var t = r.targets.find(x => x.ok); if (t) p.chosen = t.mountpoint }
            } else if (tag === "backup-auto") {
                p.auto = r
            } else if (tag === "backup-job") {
                var was = p.job.running
                p.job = r
                if (was && !r.running) { settings.backupRefresh(); settings.backupAutoRefresh() }
            }
        }
    }

    Section {
        title: "MI KERÜL A MENTÉSBE"
        InfoRow { icon: "archive-in"; label: "DATA"; value: (p.s.dataUsedText || "…") + " — a telepített programok (LightBurn, Flatpak), beállítások, Wi-Fi, Google Drive-bejelentkezés, saját fájlok, a nyomtató adatai" }
        InfoRow { label: "Visszaállítás"; value: "a Fúzió Telepítőben: Új telepítés → „DATA visszaállítása mentésből” (a mentést tartalmazó lemez legyen bedugva)" }
        InfoRow { label: "Figyelem"; value: "a mentés jelszavakat is tartalmaz (Wi-Fi, Google Drive) — tartsa biztonságban"; valueColor: Theme.warn }
    }
    Section {
        title: "AUTOMATIKUS MENTÉS A TÁRHELYRE"
        Item {
            width: parent.width; height: 44
            FCheck { id: autoChk; x: 10; anchors.verticalCenter: parent.verticalCenter
                     text: "Hetente automatikus mentés a Tárhelyre (Adatlemez)"
                     checked: p.auto.enabled === true
                     onToggled: { var e = settings.backupAutoSet(checked, p.auto.keep || 4); p.msg = e ? "hiba: " + e : "" } }
            Row {
                anchors.right: parent.right; anchors.rightMargin: 12; anchors.verticalCenter: parent.verticalCenter; spacing: 8
                Text { anchors.verticalCenter: parent.verticalCenter; text: "megtartott mentések:"; color: Theme.dim; font.family: Theme.font; font.pixelSize: 12 }
                FButton { text: "−"; enabled: (p.auto.keep || 4) > 1; onClicked: p.setKeep((p.auto.keep || 4) - 1) }
                Text { anchors.verticalCenter: parent.verticalCenter; width: 24; horizontalAlignment: Text.AlignHCenter
                       text: p.auto.keep || 4; color: Theme.text; font.family: Theme.font; font.pixelSize: 13 }
                FButton { text: "+"; enabled: (p.auto.keep || 4) < 20; onClicked: p.setKeep((p.auto.keep || 4) + 1) }
            }
        }
        InfoRow { icon: "drive"; label: "Cél"
                  value: p.auto.target ? p.auto.target.replace("/run/media/fusion/", "") + " (Tárhely)" : (p.auto.targetError || "…")
                  valueColor: p.auto.target ? Theme.text : Theme.warn }
        InfoRow { label: "Legutóbbi"; value: p.auto.lastText || "még nincs mentés a Tárhelyen" }
        InfoRow { label: "Hogyan"; value: "naponta egyszer megnézi (napközben, csak töltőn); ha a legutóbbi mentés " + (p.auto.days || 7) +
                  " napnál régebbi, ment. Közben a gép nem alszik el. A régi automatikus mentésekből a beállított számú marad, a kézi mentésekhez nem nyúl. Értesítést küld." }
        Item {
            width: parent.width; height: 44
            FButton { x: 10; anchors.verticalCenter: parent.verticalCenter; text: "Automatikus mentés most"; icon: "archive-in"
                      enabled: !p.job.running && (p.auto.target || "") !== ""
                      onClicked: { var e = settings.backupAutoNow(); p.msg = e ? "hiba: " + e : "" } }
        }
    }
    Section {
        title: "CÉL (CSATOLT KÜLSŐ KÖTET)"
        Repeater {
            model: p.s.targets
            Rectangle {
                width: parent.width; height: 46
                color: p.chosen === modelData.mountpoint ? Theme.selected : (tma.containsMouse && modelData.ok ? Theme.hover : "transparent")
                opacity: modelData.ok ? 1 : 0.5
                MouseArea { id: tma; anchors.fill: parent; hoverEnabled: true; enabled: modelData.ok; onClicked: p.chosen = modelData.mountpoint }
                FIcon { x: 14; anchors.verticalCenter: parent.verticalCenter; size: 22; name: "drive-usb" }
                Column {
                    x: 48; anchors.verticalCenter: parent.verticalCenter; width: parent.width - 60
                    Text { text: modelData.label + "   ·   " + modelData.fstype + "   ·   szabad: " + modelData.freeText
                           color: Theme.text; font.family: Theme.font; font.pixelSize: 13 }
                    Text { visible: !modelData.ok || modelData.split; color: modelData.ok ? Theme.dim : Theme.warn; font.family: Theme.font; font.pixelSize: 11
                           text: !modelData.ok ? modelData.reason : "FAT32: a mentés 3,9 GB-os darabokban" }
                }
            }
        }
        InfoRow { visible: p.s.targets.length === 0; label: "Nincs"; value: "Dugjon be egy külső lemezt vagy pendrive-ot (exFAT, NTFS vagy ext4 ajánlott), majd: Frissítés." }
    }
    Row {
        spacing: 10
        FButton { text: "Mentés most"; icon: "archive-in"; primary: true; enabled: p.chosen !== "" && !p.job.running
                  onClicked: { var e = settings.backupCreate(p.chosen); p.msg = e ? "hiba: " + e : "" } }
        Text { visible: p.msg !== ""; text: p.msg; color: Theme.danger; font.family: Theme.font; font.pixelSize: 12; anchors.verticalCenter: parent.verticalCenter }
    }
    Section {
        visible: p.job.title !== "" && p.job.recent === true && (p.job.running || p.job.rc !== null)
        title: p.job.running ? "MENTÉS FOLYAMATBAN…" : (p.job.rc === 0 ? "KÉSZ" : "SIKERTELEN")
        Column {
            x: 14; width: parent.width - 28; topPadding: 8; bottomPadding: 8; spacing: 6
            Rectangle {
                readonly property var pl: (p.job.lines || []).filter(l => /^PROGRESS /.test(l))
                visible: p.job.running; width: parent.width; height: 8; radius: 4; color: Theme.base
                Rectangle { height: parent.height; radius: 4; color: Theme.accent
                            width: parent.width * (parent.pl.length ? parseInt(parent.pl[parent.pl.length - 1].split(" ")[1]) : 0) / 100 }
            }
            Repeater {
                model: (p.job.lines || []).filter(l => !/^PROGRESS /.test(l))
                Text { width: parent.width; text: modelData; elide: Text.ElideMiddle; textFormat: Text.PlainText
                       color: /^fusion-|sikertelen|nem sikerült/i.test(modelData) ? Theme.danger : Theme.dim
                       font.family: Theme.mono; font.pixelSize: 11 }
            }
        }
    }
    Section {
        title: "MEGLÉVŐ MENTÉSEK"
        Repeater {
            model: p.s.backups
            InfoRow { icon: "archive-in"; label: modelData.when
                      value: "Fúzió " + modelData.version + "   ·   " + modelData.sizeText + "   ·   " + modelData.volume.replace("/run/media/fusion/", "") +
                             (modelData.parts.length > 1 ? "   ·   " + modelData.parts.length + " darab" : "") }
        }
        InfoRow { visible: p.s.backups.length === 0; label: "—"; value: "a csatolt köteteken nincs Fúzió-mentés" }
    }
}
