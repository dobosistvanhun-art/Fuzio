// Kijelző: felbontás kijelzőnként (xrandr); próba 15 mp-ig, megtartáskor a munkamenet indításakor is érvényes
import QtQuick
import QtQuick.Controls
import FusionUI

SettingsPage {
    id: p
    title: "Kijelző"
    property var outs: []
    property string summary: ""
    property var pending: null      // {output, mode, old}
    property int countdown: 0
    onRefresh: settings.displayRefresh()
    Component.onCompleted: settings.displayRefresh()
    Connections {
        target: settings
        function onResult(tag, r) { if (tag === "display") { p.outs = r.outputs || []; p.summary = r.summary || "" } }
    }
    Timer {
        id: revert; interval: 1000; repeat: true
        onTriggered: { p.countdown--; if (p.countdown <= 0) { stop(); p.undo() } }
    }
    function tryMode(o, mode) {
        var e = settings.displayApply(o.name, mode)
        if (e) { err.text = e; return }
        err.text = ""
        p.pending = { output: o.name, mode: mode, old: o.current }
        p.countdown = 15; revert.start(); keepDlg.open()
        settings.displayRefresh()
    }
    function undo() { if (p.pending) { settings.displayApply(p.pending.output, p.pending.old); p.pending = null; keepDlg.close(); settings.displayRefresh() } }

    Repeater {
        model: p.outs
        Section {
            id: sec
            property var out: modelData
            title: out.name + (out.primary ? "  (elsődleges)" : "")
            InfoRow { icon: "display"; label: "Jelenlegi felbontás"; value: sec.out.current + (sec.out.preferred && sec.out.preferred !== sec.out.current ? "   (ajánlott: " + sec.out.preferred + ")" : "") }
            Flow {
                width: parent.width; padding: 12; spacing: 6
                Repeater {
                    model: sec.out.modes
                    FButton {
                        text: modelData.mode + (Math.round(modelData.hz) > 0 ? "  " + Math.round(modelData.hz) + " Hz" : "")
                        checked: modelData.mode === sec.out.current
                        onClicked: if (!checked) p.tryMode(sec.out, modelData.mode)
                    }
                }
            }
        }
    }
    Text { id: err; visible: text !== ""; color: Theme.danger; font.family: Theme.font }
    property var render: settings.renderState()
    Section {
        title: "FELÜLET RAJZOLÁSA"
        InfoRow { icon: "chip"; label: "Most"; value: p.render.mode === "software" ? "szoftveres (processzor)" : "grafikus kártya (OpenGL)" }
        Row {
            x: 12; spacing: 8; topPadding: 6; bottomPadding: 6
            FButton { text: "Grafikus kártya"; checked: p.render.mode === "gpu"; enabled: !p.render.forced
                      onClicked: if (!checked) { rerr.text = settings.renderSet("gpu"); p.render = settings.renderState() } }
            FButton { text: "Szoftveres"; checked: p.render.mode === "software"; enabled: !p.render.forced
                      onClicked: if (!checked) { rerr.text = settings.renderSet("software"); p.render = settings.renderState() } }
        }
        InfoRow { label: "Mire jó"; value: "Szoftveres módban a Fusion Shell és a Fusion-programok OpenGL nélkül rajzolnak: kb. 90–100 MB-tal kevesebb memória, valamivel több processzorhasználat. A ZBookon (2026-10-08) nem volt érezhető lassulás. A LightBurnt, a Firefoxot és a többi programot nem érinti." }
        InfoRow { label: "Érvényes"; value: "A panel és az asztal azonnal újraindul az új móddal; a többi Fusion-program (pl. ez az ablak) a következő megnyitáskor." }
        InfoRow { visible: p.render.forced; label: "Most nem állítható"; value: "a boot menü mérési bejegyzése (fusion.ui.render) határozza meg"; valueColor: Theme.warn }
        Text { id: rerr; visible: text !== ""; x: 12; color: Theme.danger; font.family: Theme.font }
    }
    Section {
        title: "GRAFIKA (Fusion Hardware Layer)"
        InfoRow { icon: "chip"; label: "Meghajtó"; value: p.summary || "—"; mono: true }
    }
    FDialog {
        id: keepDlg
        title: "Megtartja ezt a felbontást?"
        buttons: [["Visszaállítás", ""], ["Megtartás", "primary"]]
        closePolicy: Popup.NoAutoClose
        onButtonClicked: (i) => {
            revert.stop(); close()
            if (i === 1 && p.pending) { settings.displaySave(p.pending.output, p.pending.mode); p.pending = null }
            else p.undo()
        }
        Text { x: 20; y: 16; text: "Visszaállítás " + p.countdown + " mp múlva, ha nem erősíti meg."; color: Theme.text; font.family: Theme.font; font.pixelSize: 13 }
    }
}
