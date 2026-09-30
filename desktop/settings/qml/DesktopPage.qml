// Asztal: háttérszín, billentyűk
import QtQuick
import QtQuick.Controls
import FusionUI

SettingsPage {
    id: p
    title: "Asztal"
    property string bg: settings.background()
    Section {
        title: "IRÁNYÍTÓPULT"
        Item { width: parent.width; height: 48
            FCheck { x: 14; anchors.verticalCenter: parent.verticalCenter; checked: settings.dashboard()
                     text: "Irányítópult az asztalon (lézer, nyomtató, hálózat, rendszer, meghajtók, programok)"
                     onToggled: settings.setDashboard(checked) } }
    }
    Section {
        title: "HÁTTÉRSZÍN"
        Flow {
            width: parent.width; padding: 14; spacing: 10
            Repeater {
                model: ["#16202b", "#0d1117", "#1b2a1f", "#2a1f2d", "#1f2a36", "#2b2b2b", "#10263a", "#303846"]
                Rectangle {
                    width: 72; height: 48; radius: Theme.radius; color: modelData
                    border.color: p.bg.toLowerCase() === modelData ? Theme.accent : Theme.border; border.width: p.bg.toLowerCase() === modelData ? 2 : 1
                    MouseArea { anchors.fill: parent; onClicked: { settings.setBackground(modelData); p.bg = modelData } }
                }
            }
        }
    }
    Section {
        title: "BILLENTYŰK"
        InfoRow { label: "Start menü"; value: "Super (Windows-gomb), Alt+F1" }
        InfoRow { label: "Ablakváltás"; value: "Alt+Tab" }
        InfoRow { label: "Ablak bezárása"; value: "Alt+F4" }
        InfoRow { label: "Teljes méret"; value: "Alt+F10" }
        InfoRow { label: "Fájlkezelő"; value: "Ctrl+Alt+E" }
        InfoRow { label: "Beállítások"; value: "Ctrl+Alt+S" }
        InfoRow { label: "Terminál"; value: "Ctrl+Alt+T" }
        InfoRow { label: "Billentyűzetkiosztás"; value: "magyar (hu)" }
    }
}
