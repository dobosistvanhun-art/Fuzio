// Felhasználók: lista, új felhasználó, jelszócsere, rendszergazda-jog, törlés, automatikus belépés (fusion-users)
import QtQuick
import QtQuick.Controls
import FusionUI

SettingsPage {
    id: p
    title: "Felhasználók"
    subtitle: st.caller ? ("Bejelentkezve: " + st.caller + (st.callerAdmin ? " (rendszergazda)" : "")) : ""
    property var st: ({ users: [], caller: "", callerAdmin: false, autologin: "" })
    property string msg: ""
    property bool msgErr: false
    property string pwFor: ""            // melyik felhasználó jelszavát cseréljük
    property string delFor: ""           // törlés megerősítése
    property bool adding: false
    busy: false
    onRefresh: settings.usersRefresh()
    Component.onCompleted: settings.usersRefresh()
    function say(t, err) { msg = t; msgErr = err }
    Connections {
        target: settings
        function onResult(tag, r) {
            if (tag === "users") {
                if (r.users) p.st = r
                if (r.error) p.say(r.error, true)
            } else if (tag === "users-action") {
                p.say(r.ok ? (r.msg || "Rendben.") : r.msg, !r.ok)
                if (r.ok) { p.pwFor = ""; p.delFor = ""; p.adding = false; pw1.text = ""; pw2.text = ""; pwOld.text = "" }
                settings.usersRefresh()
            }
        }
    }

    Text { visible: p.msg !== ""; width: parent.width; wrapMode: Text.Wrap; text: p.msg
           color: p.msgErr ? Theme.danger : Theme.ok; font.family: Theme.font; font.pixelSize: 13 }

    Section {
        title: "FELHASZNÁLÓK"
        Repeater {
            model: p.st.users
            Column {
                width: parent.width
                InfoRow {
                    icon: "user"
                    label: modelData.name + (modelData.name === p.st.caller ? "  (Ön)" : "")
                    value: (modelData.fullname ? modelData.fullname + "  ·  " : "")
                           + (modelData.admin ? "rendszergazda" : "felhasználó")
                           + (modelData.autologin ? "  ·  automatikus belépés" : "")
                           + (modelData.base ? "  ·  a Fúzió alapfelhasználója (jelszó: fusion — rögzített)" : "")
                    valueColor: modelData.admin ? Theme.text : Theme.dim
                    FButton { visible: !modelData.base && (modelData.name === p.st.caller || p.st.callerAdmin)
                              text: "Jelszó"; flat: true; onClicked: { p.msg = ""; p.pwFor = modelData.name; p.delFor = "" } }
                    FButton { visible: !modelData.base && p.st.callerAdmin && modelData.name !== p.st.caller
                              text: modelData.admin ? "Jog elvétele" : "Rendszergazda"; flat: true
                              onClicked: settings.userAdmin(modelData.name, !modelData.admin) }
                    FButton { visible: p.st.callerAdmin && !modelData.autologin; text: "Automatikus belépés"; flat: true
                              tip: "A gép indításakor ez a felhasználó lép be jelszó nélkül"
                              onClicked: settings.userAutologin(modelData.name) }
                    FToolButton { visible: !modelData.base && p.st.callerAdmin && modelData.name !== p.st.caller
                                  icon: "trash"; tip: "Törlés"; onClicked: { p.msg = ""; p.delFor = modelData.name; p.pwFor = "" } }
                }
                // törlés megerősítése
                Rectangle {
                    visible: p.delFor === modelData.name; width: parent.width; height: 48; color: "#2a1a1d"
                    Text { x: 44; anchors.verticalCenter: parent.verticalCenter; text: "Biztosan törli: " + modelData.name + "?"
                           color: Theme.text; font.family: Theme.font; font.pixelSize: 13 }
                    Row {
                        anchors.right: parent.right; anchors.rightMargin: 10; anchors.verticalCenter: parent.verticalCenter; spacing: 10
                        FCheck { id: rmHome; text: "a saját mappája (" + modelData.home + ") is"; checked: false }
                        FButton { text: "Törlés"; danger: true; onClicked: settings.userDelete(modelData.name, rmHome.checked) }
                        FButton { text: "Mégse"; flat: true; onClicked: p.delFor = "" }
                    }
                }
            }
        }
    }

    // jelszócsere
    Section {
        title: "JELSZÓCSERE — " + p.pwFor
        visible: p.pwFor !== ""
        Column {
            x: 14; width: parent.width - 28; spacing: 8; topPadding: 10; bottomPadding: 10
            FTextField { id: pwOld; width: 320; echoMode: TextInput.Password; visible: p.pwFor === p.st.caller
                         placeholderText: "jelenlegi jelszó" }
            FTextField { id: pw1; width: 320; echoMode: TextInput.Password; placeholderText: "új jelszó (legalább 4 karakter)" }
            FTextField { id: pw2; width: 320; echoMode: TextInput.Password; placeholderText: "új jelszó még egyszer" }
            Row {
                spacing: 8
                FButton { text: "Mentés"; primary: true
                          onClicked: { if (pw1.text !== pw2.text) { p.say("A két új jelszó nem egyezik.", true); return }
                                       settings.userPasswd(p.pwFor, pwOld.text, pw1.text) } }
                FButton { text: "Mégse"; flat: true; onClicked: { p.pwFor = ""; pw1.text = ""; pw2.text = ""; pwOld.text = "" } }
            }
        }
    }

    // új felhasználó (csak rendszergazda)
    Section {
        title: "ÚJ FELHASZNÁLÓ"
        visible: p.st.callerAdmin
        InfoRow {
            visible: !p.adding; icon: "plus"; label: "Hozzáadás"
            value: "Saját mappát, saját beállításokat és saját programokat kap. A LightBurn és a többi program a telepítő felhasználóé."
            FButton { text: "Új felhasználó"; primary: true; onClicked: { p.msg = ""; p.adding = true } }
        }
        Column {
            visible: p.adding; x: 14; width: parent.width - 28; spacing: 8; topPadding: 10; bottomPadding: 10
            FTextField { id: nName; width: 320; placeholderText: "felhasználónév (kisbetű, pl. bela)" }
            FTextField { id: nFull; width: 320; placeholderText: "teljes név (pl. Kiss Béla)" }
            FTextField { id: nPw1; width: 320; echoMode: TextInput.Password; placeholderText: "jelszó (legalább 4 karakter)" }
            FTextField { id: nPw2; width: 320; echoMode: TextInput.Password; placeholderText: "jelszó még egyszer" }
            FCheck { id: nAdmin; text: "rendszergazda (programtelepítés, rendszerfrissítés, lemezek, felhasználók)" }
            Row {
                spacing: 8
                FButton { text: "Felvétel"; primary: true
                          onClicked: { if (nPw1.text !== nPw2.text) { p.say("A két jelszó nem egyezik.", true); return }
                                       settings.userAdd(nName.text.trim(), nFull.text.trim(), nPw1.text, nAdmin.checked)
                                       nPw1.text = ""; nPw2.text = "" } }
                FButton { text: "Mégse"; flat: true; onClicked: p.adding = false }
            }
        }
    }

    Section {
        title: "BELÉPÉS"
        InfoRow {
            icon: "lock"; label: "Indításkor"
            value: p.st.autologin && p.st.autologin !== "none" ? ("automatikusan belép: " + p.st.autologin)
                   : "jelszóval (felhasználónév + jelszó a képernyőn)"
            FButton { visible: p.st.callerAdmin && p.st.autologin !== "none"; text: "Jelszóval lépjen be"; flat: true
                      onClicked: settings.userAutologin("none") }
        }
        InfoRow { icon: "info"; label: "Megjegyzés"; value: "A belépés módja a következő indítástól érvényes. A felhasználók a rendszerfrissítés után is megmaradnak." }
    }
}
