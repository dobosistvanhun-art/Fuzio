// FusionOS — hang felugró (a panel hangszóró-jelére): hangerő, némítás, kimenet, mikrofon
import QtQuick
import QtQuick.Controls
import FusionUI

Rectangle {
    id: sp
    color: Theme.bg
    border.color: Theme.border
    focus: true
    Keys.onEscapePressed: shell.togglePopup("sound")
    readonly property var st: shell ? shell.sound : ({})
    // a csúszka húzása közben ne ugráljon vissza a kiszolgáló régebbi értékére
    property bool dragging: vol.pressed || mic.pressed
    Timer { id: volT; interval: 60; onTriggered: shell.soundSet(Math.round(vol.value)) }
    Timer { id: micT; interval: 60; onTriggered: shell.micSet(Math.round(mic.value)) }

    implicitHeight: col.implicitHeight + 28
    Column {
        id: col
        x: 16; y: 14; width: parent.width - 32; spacing: 10
        Row {
            width: parent.width
            Text { text: "Hang"; color: Theme.text; font.family: Theme.font; font.pixelSize: 15; font.bold: true; width: parent.width - tb.width }
            FToolButton { id: tb; icon: "settings"; tip: "Hangbeállítások"; onClicked: { shell.togglePopup("sound"); shell.run("fusion-settings sound") } }
        }
        Text { visible: !sp.st.ok; text: "A hangkiszolgáló nem fut" + (sp.st.error ? " (" + sp.st.error + ")" : ""); color: Theme.warn
               font.family: Theme.font; font.pixelSize: 12; width: parent.width; wrapMode: Text.Wrap }
        Text { visible: sp.st.ok && !sp.st.hasOutput; text: "Nincs hangkimenet (hangkártya?)"; color: Theme.warn
               font.family: Theme.font; font.pixelSize: 12 }
        // kimenet hangereje
        Row {
            spacing: 8; width: parent.width; enabled: sp.st.ok
            FToolButton { icon: sp.st.mute ? "volume-mute" : "volume"; tip: sp.st.mute ? "Némítás feloldása" : "Némítás"
                          anchors.verticalCenter: parent.verticalCenter; onClicked: shell.soundToggleMute() }
            FSlider { id: vol; from: 0; to: 100; width: parent.width - 90; anchors.verticalCenter: parent.verticalCenter
                      value: sp.dragging ? value : Math.min(100, sp.st.volume || 0); onMoved: volT.restart() }
            Text { text: Math.round(vol.pressed ? vol.value : (sp.st.volume || 0)) + "%"; color: sp.st.mute ? Theme.dim : Theme.text
                   font.family: Theme.font; font.pixelSize: 13; anchors.verticalCenter: parent.verticalCenter; width: 40; horizontalAlignment: Text.AlignRight }
        }
        // kimenetek
        Text { visible: (sp.st.sinks || []).length > 1; text: "KIMENET"; color: Theme.dim; font.family: Theme.font; font.pixelSize: 11; font.bold: true }
        Repeater {
            model: (sp.st.sinks || []).length > 1 ? sp.st.sinks : []
            Rectangle {
                width: parent.width; height: 30; radius: Theme.radius
                color: modelData.name === sp.st.sink ? Theme.selected : (oma.containsMouse ? Theme.hover : "transparent")
                FIcon { x: 8; anchors.verticalCenter: parent.verticalCenter; name: modelData.bus === "usb" ? "usb" : (/hdmi/i.test(modelData.name) ? "display" : "speaker"); size: 16 }
                Text { x: 32; anchors.verticalCenter: parent.verticalCenter; width: parent.width - 40; elide: Text.ElideRight
                       text: modelData.desc; color: Theme.text; font.family: Theme.font; font.pixelSize: 12 }
                MouseArea { id: oma; anchors.fill: parent; hoverEnabled: true; onClicked: shell.soundSetSink(modelData.name) }
            }
        }
        // mikrofon
        Text { visible: (sp.st.sources || []).length > 0; text: "MIKROFON"; color: Theme.dim; font.family: Theme.font; font.pixelSize: 11; font.bold: true }
        Row {
            visible: (sp.st.sources || []).length > 0
            spacing: 8; width: parent.width
            FToolButton { icon: sp.st.micMute ? "volume-mute" : "mic"; tip: sp.st.micMute ? "Mikrofon bekapcsolása" : "Mikrofon némítása"
                          anchors.verticalCenter: parent.verticalCenter; onClicked: shell.micToggleMute() }
            FSlider { id: mic; from: 0; to: 100; width: parent.width - 90; anchors.verticalCenter: parent.verticalCenter
                      value: sp.dragging ? value : Math.min(100, sp.st.micVolume || 0); onMoved: micT.restart() }
            Text { text: Math.round(mic.pressed ? mic.value : (sp.st.micVolume || 0)) + "%"; color: Theme.text
                   font.family: Theme.font; font.pixelSize: 13; anchors.verticalCenter: parent.verticalCenter; width: 40; horizontalAlignment: Text.AlignRight }
        }
        FButton { text: "Próbahang"; icon: "volume"; flat: true; enabled: sp.st.ok && sp.st.hasOutput; onClicked: shell.soundTest() }
    }
}
