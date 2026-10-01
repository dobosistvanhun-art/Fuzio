// Google Drive: bejelentkezés (böngészőben), csatolás a ~/GoogleDrive mappába, tárhely, leválasztás.
// A Drive a Fájlkezelőben kötetként látszik; minden program mappaként éri el.
import QtQuick
import QtQuick.Controls
import FusionUI

SettingsPage {
    id: p
    title: "Google Drive"
    subtitle: "A Drive a Fájlkezelőben kötetként látszik (~/GoogleDrive) — a fájlok a háttérben szinkronizálódnak"
    property var st: ({ configured: false, mounted: false })
    property string loginState: ""     // "" | "waiting" | "done" | "error"
    property string loginText: ""
    property string loginUrl: ""
    property string msg: ""
    property bool confirmOff: false
    busy: loginState === "waiting"
    onRefresh: settings.driveRefresh()
    Component.onCompleted: settings.driveRefresh()
    Timer { interval: 4000; running: p.visible; repeat: true; onTriggered: settings.driveRefresh() }
    Connections {
        target: settings
        function onResult(tag, r) {
            if (tag === "drive" && r.configured !== undefined) p.st = r
            else if (tag === "drive-login") {
                if (r.kind === "url") p.loginUrl = r.text
                else if (r.kind === "info") { p.loginText = r.text }
                else if (r.kind === "done") { p.loginState = "done"; p.loginText = r.text; settings.driveRefresh() }
                else if (r.kind === "error") { p.loginState = "error"; p.loginText = r.text; settings.driveRefresh() }
            } else if (tag === "drive-action") { p.msg = r.msg || ""; p.confirmOff = false; settings.driveRefresh() }
        }
    }

    // --- nincs bejelentkezve ---
    Section {
        visible: !p.st.configured
        title: "BEJELENTKEZÉS"
        InfoRow {
            icon: "cloud"; label: "Google-fiók"
            value: p.loginState === "waiting" ? "A böngészőben: jelentkezzen be, és engedélyezze a hozzáférést (rclone)…"
                   : (p.loginState === "error" ? p.loginText : "Nincs bejelentkezve")
            valueColor: p.loginState === "error" ? Theme.danger : Theme.text
            FButton { visible: p.loginState !== "waiting"; text: "Bejelentkezés"; primary: true; icon: "cloud"
                      onClicked: { p.loginState = "waiting"; p.loginText = ""; p.loginUrl = ""; p.msg = ""; settings.driveConnect() } }
            FButton { visible: p.loginState === "waiting"; text: "Mégse"; flat: true; onClicked: { settings.driveCancel(); p.loginState = "" } }
        }
        InfoRow {
            visible: p.loginState === "waiting" && p.loginUrl !== ""
            icon: "web"; label: "Ha nem nyílt meg"; value: p.loginUrl; mono: true
            FButton { text: "Böngésző"; icon: "web"; onClicked: settings.driveOpenUrl(p.loginUrl) }
        }
        Text { width: parent.width; padding: 14; wrapMode: Text.Wrap; color: Theme.dim; font.family: Theme.font; font.pixelSize: 12
               text: "A bejelentkezés a böngészőben (Firefox) történik, a Google saját oldalán — a jelszót a FusionOS nem látja. "
                     + "A hozzáférést az rclone kéri (a Google ezen a néven mutatja); a jegy csak ezen a gépen, a DATA-n tárolódik. "
                     + "Visszavonás: itt „Leválasztás”, vagy a Google-fiók biztonsági beállításaiban." }
    }

    // --- bejelentkezve ---
    Section {
        visible: p.st.configured
        title: "FIÓK"
        InfoRow { icon: "cloud"; label: "Google-fiók"
                  value: p.st.account && p.st.account.email ? (p.st.account.name ? p.st.account.name + "  ·  " : "") + p.st.account.email : "bejelentkezve"
                  valueColor: Theme.ok }
        InfoRow { visible: !!p.st.quotaText; icon: "drive"; label: "Tárhely"; value: p.st.quotaText || "" }
        InfoRow {
            icon: "folder"; label: "Mappa"
            value: p.st.mounted ? p.st.path + "  —  csatolva" : (p.st.service === "activating" ? "csatolás folyamatban…" : "nincs csatolva" + (p.st.error ? "\n" + p.st.error : ""))
            valueColor: p.st.mounted ? Theme.ok : Theme.warn
            FButton { visible: p.st.mounted; text: "Megnyitás"; icon: "files"; primary: true; onClicked: settings.spawn("fusion-files " + p.st.path) }
            FButton { visible: !p.st.mounted; text: "Csatolás"; primary: true; onClicked: { p.msg = "Csatolás…"; settings.driveMount(true) } }
            FButton { visible: p.st.mounted; text: "Leállítás"; flat: true; onClicked: settings.driveMount(false) }
        }
        InfoRow { icon: "restart"; label: "Bejelentkezéskor"; value: p.st.enabled ? "automatikusan csatolódik" : "nem csatolódik"
                  FButton { text: p.st.enabled ? "Kikapcsolás" : "Bekapcsolás"; onClicked: settings.driveAutostart(!p.st.enabled) } }
        InfoRow { icon: "archive-in"; label: "Helyi gyorsítótár"; value: (p.st.cacheText || "0 B") + "  (legfeljebb 2 GB; a megnyitott fájlok helyi másolata)" }
    }
    Text { visible: p.msg !== "" || p.loginState === "done"; text: p.msg || p.loginText; color: Theme.dim; font.family: Theme.font
           width: parent.width; wrapMode: Text.Wrap }
    Section {
        visible: p.st.configured
        title: "LEVÁLASZTÁS"
        InfoRow {
            icon: "logout"; label: "Google Drive leválasztása"
            value: p.confirmOff ? "Biztosan? A csatolás és a gyorsítótár törlődik; a felhőben lévő fájlok megmaradnak." : "kijelentkezés erről a gépről"
            FButton { visible: !p.confirmOff; text: "Leválasztás"; onClicked: p.confirmOff = true }
            FButton { visible: p.confirmOff; text: "Igen, leválasztás"; danger: true; onClicked: settings.driveDisconnect() }
            FButton { visible: p.confirmOff; text: "Mégse"; flat: true; onClicked: p.confirmOff = false }
        }
    }
    Text { width: parent.width; wrapMode: Text.Wrap; color: Theme.dim; font.family: Theme.font; font.pixelSize: 12
           text: "Tipp: a mentés a Drive mappába előbb helyben történik meg, a feltöltés a háttérben megy (internet nélkül később). "
                 + "Windows-program (pl. LightBurn) akkor látja, ha a Programkezelőben megkapja ezt a mappát." }
}
