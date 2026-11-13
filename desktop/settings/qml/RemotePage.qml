// Távoli elérés (0.0.78): Tailscale (privát hálózat a saját gépeid között, portnyitás nélkül), SSH-szerver (csak
// kulccsal, csak a Tailscale-hálózat felől), a képernyő megosztása (VNC), a gép ébren tartása. Alapból minden ki.
import QtQuick
import QtQuick.Controls
import FusionUI

SettingsPage {
    id: p
    title: "Távoli elérés"
    subtitle: "A gép elérése a saját gépeidről (munkahely, telefon): parancssor, fájlok, képernyő — a Tailscale-hálózaton át"
    property var s: ({ tailscale: { installed: true, state: "", peers: [], authUrl: "" }, ssh: {}, awake: {}, keys: [],
                       vnc: {}, hostname: "", user: "fusion", error: "" })
    property bool working: false
    property string msg: ""
    readonly property var ts: s.tailscale || {}
    readonly property bool tsOn: ts.active === true
    readonly property bool online: ts.state === "Running"
    // a többi gépről így érhető el: a MagicDNS-név, ennek hiányában a 100.x cím
    readonly property string addr: ts.dns ? ts.dns.split(".")[0] : (ts.ip || "")
    function stateText() {
        if (!ts.installed) return ts.error || "a Tailscale nincs a rendszerképben"
        if (!tsOn) return "kikapcsolva"
        if (ts.state === "Running") return "kapcsolódva — " + (ts.dns || ts.name) + "   ·   " + ts.ip
        if (ts.state === "NeedsLogin") return "be kell jelentkezni (lent a cím)"
        if (ts.state === "NeedsMachineAuth") return "a gépet jóvá kell hagyni a Tailscale admin oldalán"
        if (ts.state === "Stopped") return "leállítva"
        return ts.state ? ts.state + "…" : "indul…"
    }
    busy: working
    onRefresh: settings.remoteRefresh()
    Component.onCompleted: settings.remoteRefresh()
    // amíg a bejelentkezésre vár, gyakrabban néz rá
    Timer { interval: p.ts.state === "NeedsLogin" || p.ts.state === "Starting" ? 3000 : 15000
            running: p.visible && !p.working; repeat: true; onTriggered: settings.remoteRefresh() }
    Connections {
        target: settings
        function onResult(tag, r) {
            if (tag === "remote") { p.s = r }
            else if (tag === "remote-action") { p.s = r; p.working = false; p.msg = r.msg || "" }
        }
    }
    function act(f) { p.working = true; p.msg = ""; f() }

    Section {
        title: "TAILSCALE — PRIVÁT HÁLÓZAT"
        Item {
            width: parent.width; height: 44
            FCheck { x: 10; anchors.verticalCenter: parent.verticalCenter; enabled: !p.working && p.ts.installed === true
                     text: "Tailscale bekapcsolva"; checked: p.tsOn
                     onToggled: { var on = checked; p.act(function () { settings.remoteTailscale(on) }) } }
            FButton { anchors.right: parent.right; anchors.rightMargin: 12; anchors.verticalCenter: parent.verticalCenter
                      visible: p.online; enabled: !p.working; text: "Kijelentkezés"; icon: "logout"; flat: true
                      onClicked: p.act(function () { settings.remoteLogout() }) }
        }
        InfoRow { icon: "remote"; label: "Állapot"; value: p.stateText()
                  valueColor: p.online ? Theme.text : (p.tsOn ? Theme.warn : Theme.dim) }
        InfoRow {
            visible: p.tsOn && (p.ts.authUrl || "") !== ""
            label: "Bejelentkezés"; value: p.ts.authUrl || ""; mono: true
            FButton { text: "Megnyitás"; icon: "web"; onClicked: settings.remoteOpenUrl(p.ts.authUrl) }
            FButton { text: "Másolás"; icon: "copy"; flat: true; onClicked: settings.remoteCopy(p.ts.authUrl) }
        }
        InfoRow { visible: p.tsOn && p.ts.state === "NeedsLogin"; label: "Hogyan"
                  value: "Nyissa meg a címet (itt vagy a telefonján), és jelentkezzen be (pl. Google-fiókkal). Ugyanezzel a fiókkal lépjen be a Tailscale-be a munkahelyi gépen és a telefonon is: így látják egymást." }
        Repeater {
            model: p.online ? p.ts.peers : []
            InfoRow { icon: modelData.online ? "dot" : ""; label: modelData.name
                      value: (modelData.online ? "elérhető" : "nem elérhető") + "   ·   " + modelData.os + "   ·   " + modelData.ip
                      valueColor: modelData.online ? Theme.text : Theme.dim }
        }
        InfoRow { visible: p.online && p.ts.peers.length === 0; label: "Többi gép"
                  value: "még nincs más gép a hálózatban — telepítse a Tailscale-t a munkahelyi gépre vagy a telefonra, ugyanazzal a fiókkal" }
    }

    Section {
        title: "PARANCSSOR ÉS FÁJLOK (SSH)"
        Item {
            width: parent.width; height: 44
            FCheck { x: 10; anchors.verticalCenter: parent.verticalCenter; enabled: !p.working && p.s.ssh.installed === true
                     text: "SSH-szerver bekapcsolva (csak kulccsal, csak a Tailscale-hálózat felől)"; checked: p.s.ssh.active === true
                     onToggled: { var on = checked; p.act(function () { settings.remoteSsh(on) }) } }
        }
        InfoRow { visible: p.s.ssh.active === true; icon: "terminal"; label: "Belépés"; mono: true
                  value: "ssh " + p.s.user + "@" + (p.addr || "<a gép neve>")
                  FButton { text: "Másolás"; icon: "copy"; flat: true; enabled: p.addr !== ""
                            onClicked: settings.remoteCopy("ssh " + p.s.user + "@" + p.addr) } }
        InfoRow { visible: p.s.ssh.active === true; label: "Fájlok"
                  value: "WinSCP (SFTP) vagy a VS Code „Remote - SSH” bővítménye ugyanezzel a címmel és kulccsal; egy fájl: scp" }
        InfoRow { visible: p.s.ssh.active === true && (p.s.keys || []).length === 0; label: "Figyelem"; valueColor: Theme.warn
                  value: "még nincs kulcs — lent adja hozzá a munkahelyi gép nyilvános kulcsát, különben senki nem léphet be" }
    }

    Section {
        title: "BELÉPÉSRE JOGOSÍTÓ KULCSOK (" + p.s.user + ")"
        Repeater {
            model: p.s.keys || []
            InfoRow { icon: "lock"; label: modelData.comment; value: modelData.type + "   ·   " + modelData.fingerprint; mono: true
                      FButton { text: "Törlés"; icon: "trash"; flat: true
                                onClicked: { var e = settings.remoteKeyRemove(modelData.line, modelData.fingerprint); p.msg = e ? "hiba: " + e : "" } } }
        }
        InfoRow { visible: (p.s.keys || []).length === 0; label: "—"; value: "nincs kulcs" }
        Column {
            x: 14; width: parent.width - 28; spacing: 8; topPadding: 10; bottomPadding: 10
            Text { width: parent.width; wrapMode: Text.Wrap; color: Theme.dim; font.family: Theme.font; font.pixelSize: 12
                   text: "Új kulcs: a munkahelyi gépen (Windows PowerShell) „ssh-keygen -t ed25519”, utána a C:\\Users\\<név>\\.ssh\\id_ed25519.pub fájl egyetlen sorát (ssh-ed25519 … kezdetű) másolja ide. A titkos kulcs (pub nélküli fájl) soha ne kerüljön ide." }
            Row {
                width: parent.width; spacing: 8
                FTextField { id: keyIn; width: parent.width - addBtn.width - 8; placeholderText: "ssh-ed25519 AAAA… név@gép" }
                FButton { id: addBtn; text: "Hozzáadás"; icon: "plus"; enabled: keyIn.text.trim() !== ""
                          onClicked: { var e = settings.remoteKeyAdd(keyIn.text); p.msg = e ? "hiba: " + e : "A kulcs hozzáadva."; if (!e) keyIn.text = "" } }
            }
        }
    }

    Section {
        title: "KÉPERNYŐ (VNC)"
        Item {
            width: parent.width; height: 44
            FCheck { id: vncChk; x: 10; anchors.verticalCenter: parent.verticalCenter
                     enabled: p.s.vnc.installed === true && (p.s.vnc.hasPassword === true || vncPw.text.length >= 6)
                     text: "Képernyő megosztása (csak a Tailscale-hálózat felől, jelszóval)"; checked: p.s.vnc.active === true
                     onToggled: { var e = settings.remoteVnc(checked, vncPw.text); p.msg = e ? "hiba: " + e : ""; if (!e) vncPw.text = "" } }
        }
        Row {
            x: 14; spacing: 8; height: 44
            Text { anchors.verticalCenter: parent.verticalCenter; text: p.s.vnc.hasPassword ? "új jelszó:" : "jelszó:"
                   color: Theme.dim; font.family: Theme.font; font.pixelSize: 12 }
            FTextField { id: vncPw; anchors.verticalCenter: parent.verticalCenter; width: 220; echoMode: TextInput.Password
                         placeholderText: "6–8 karakter" }
            FButton { anchors.verticalCenter: parent.verticalCenter; text: "Jelszó mentése"; visible: p.s.vnc.hasPassword === true
                      enabled: vncPw.text.length >= 6
                      onClicked: { var e = settings.remoteVnc(p.s.vnc.active === true, vncPw.text); p.msg = e ? "hiba: " + e : "A jelszó elmentve."; if (!e) vncPw.text = "" } }
        }
        InfoRow { visible: p.s.vnc.active === true; icon: "desktop"; label: "Kapcsolódás"; mono: true
                  value: (p.addr || "<a gép neve>") + ":5900   (VNC-néző, pl. TigerVNC vagy RealVNC Viewer)" }
        InfoRow { label: "Tudnivaló"; value: "a VNC a jelszónak csak az első 8 karakterét nézi; a forgalmat a Tailscale titkosítja. Közben a képernyőn minden látszik, ami a gépen történik." }
    }

    Section {
        title: "ÉBREN TARTÁS"
        Item {
            width: parent.width; height: 44
            FCheck { x: 10; anchors.verticalCenter: parent.verticalCenter; enabled: !p.working
                     text: "A gép ne aludjon el (a fedél lecsukására sem), amíg ez be van kapcsolva"; checked: p.s.awake.active === true
                     onToggled: { var on = checked; p.act(function () { settings.remoteAwake(on) }) } }
        }
        InfoRow { label: "Miért"; value: "alvó gépet távolról nem lehet elérni. Töltőn hagyva ajánlott." }
    }

    Text { visible: p.msg !== "" || (p.s.error || "") !== ""; width: parent.width; wrapMode: Text.Wrap
           text: p.msg || p.s.error; color: /^hiba/.test(p.msg) || (!p.msg && p.s.error) ? Theme.danger : Theme.dim
           font.family: Theme.font; font.pixelSize: 12 }
}
