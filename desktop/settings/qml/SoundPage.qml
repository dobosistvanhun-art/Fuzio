// Hang: kimenetek (hangszóró, fejhallgató, HDMI, USB), hangerő, bemenet (mikrofon), próbahang
import QtQuick
import QtQuick.Controls
import FusionUI

SettingsPage {
    id: p
    title: "Hang"
    subtitle: "Hangkiszolgáló: PipeWire (PulseAudio-felülettel — a Flatpak-programok is ezen szólnak)"
    property var st: ({ ok: false, sinks: [], sources: [] })
    property string msg: ""
    property bool dragging: false
    onRefresh: settings.soundRefresh()
    Component.onCompleted: settings.soundRefresh()
    Timer { interval: 2000; running: true; repeat: true; onTriggered: if (!p.dragging) settings.soundRefresh() }
    Connections {
        target: settings
        function onResult(tag, r) {
            if (tag === "sound" && r.sinks !== undefined && !p.dragging) p.st = r
            else if (tag === "sound-test") p.msg = r.rc === 0 ? "Próbahang lejátszva." : "A próbahang nem szólt (hiba: " + r.rc + ")."
            else if (tag === "sound-restart") { p.msg = r.rc === 0 ? "A hangkiszolgáló újraindult." : "Hiba: " + r.msg; settings.soundRefresh() }
        }
    }
    component VolRow: InfoRow {
        id: vr
        property var dev
        property bool source: false
        property bool isDefault: false
        icon: source ? "mic" : (dev.bus === "usb" ? "usb" : (/hdmi/i.test(dev.name) ? "display" : "speaker"))
        label: dev.desc
        valueColor: isDefault ? Theme.ok : Theme.dim
        value: isDefault ? "alapértelmezett" : ""
        Timer { id: vt; interval: 80; onTriggered: settings.soundSetVolume(Math.round(sl.value), vr.source) }
        FToolButton { icon: vr.dev.mute ? "volume-mute" : (vr.source ? "mic" : "volume"); tip: vr.dev.mute ? "Némítás feloldása" : "Némítás"
                      visible: vr.isDefault; onClicked: settings.soundToggleMute(vr.source) }
        FSlider { id: sl; visible: vr.isDefault; width: 220; from: 0; to: 150; value: vr.dev.volume
                  onPressedChanged: p.dragging = pressed; onMoved: vt.restart() }
        Text { visible: vr.isDefault; width: 44; text: Math.round(sl.value) + "%"; color: sl.value > 100 ? Theme.warn : Theme.text
               font.family: Theme.font; font.pixelSize: 13; anchors.verticalCenter: parent.verticalCenter }
        FButton { visible: !vr.isDefault; text: "Ez legyen"; onClicked: settings.soundSetDefault(vr.dev.name, vr.source) }
        FButton { visible: !vr.source; text: "Próba"; icon: "volume"; flat: true; onClicked: { p.msg = ""; settings.soundTest(vr.dev.name) } }
    }

    Text { visible: !p.st.ok; width: parent.width; wrapMode: Text.Wrap; color: Theme.warn; font.family: Theme.font
           text: "A hangkiszolgáló nem érhető el" + (p.st.error ? ": " + p.st.error : "") + " — próbálja: Újraindítás lent." }
    Section {
        title: "KIMENET (hangszóró, fejhallgató, HDMI, USB) — 100% fölött erősítés"
        Repeater { model: p.st.sinks; VolRow { dev: modelData; isDefault: modelData.name === p.st.sink } }
        // a kiválasztott kimenet csatlakozói (pl. hangszóró / fejhallgató)
        Repeater {
            model: { var d = (p.st.sinks || []).find(x => x.name === p.st.sink); return d && d.ports.length > 1 ? d.ports : [] }
            InfoRow {
                icon: "dot"; label: "  " + modelData.desc; value: modelData.available ? "" : "nincs bedugva"; valueColor: Theme.dim
                property bool cur: { var d = p.st.sinks.find(x => x.name === p.st.sink); return d && d.port === modelData.name }
                FButton { text: parent.parent.cur ? "Aktív" : "Ide"; checked: parent.parent.cur; enabled: !parent.parent.cur
                          onClicked: settings.soundSetPort(p.st.sink, modelData.name) }
            }
        }
        Text { visible: p.st.ok && (p.st.sinks || []).length === 0; padding: 14; color: Theme.dim; font.family: Theme.font
               text: "Nincs hangkimenet — a hangkártya nem látszik (lásd: Rendszer → Hardverjelentés)." }
    }
    Section {
        title: "BEMENET (mikrofon)"
        Repeater { model: p.st.sources; VolRow { dev: modelData; source: true; isDefault: modelData.name === p.st.source } }
        Text { visible: (p.st.sources || []).length === 0; padding: 14; color: Theme.dim; font.family: Theme.font; text: "Nincs mikrofon." }
    }
    Text { visible: p.msg !== ""; text: p.msg; color: Theme.dim; font.family: Theme.font }
    Section {
        title: "HANGKISZOLGÁLÓ"
        InfoRow { icon: "volume"; label: "Kiszolgáló"; value: p.st.server || "—"; mono: true
                  FButton { text: "Újraindítás"; icon: "restart"; onClicked: { p.msg = ""; settings.soundRestart() } } }
        InfoRow { icon: "info"; label: "Billentyűk"; value: "hangerő fel / le / némítás: a gép hangerőgombjai; panel: görgetés a hangszórón, középső gomb = némítás" }
    }
}
