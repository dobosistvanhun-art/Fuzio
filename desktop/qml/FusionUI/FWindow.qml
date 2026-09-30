// a Fusion-programok főablaka: FusionDark paletta a Qt Quick Controls elemeinek is
import QtQuick
import QtQuick.Controls.Basic

ApplicationWindow {
    color: Theme.bg
    font.family: Theme.font; font.pixelSize: Theme.fs
    palette.window: Theme.bg
    palette.windowText: Theme.text
    palette.base: Theme.base
    palette.alternateBase: Theme.alt
    palette.text: Theme.text
    palette.button: "#1b222c"
    palette.buttonText: Theme.text
    palette.brightText: "white"
    palette.highlight: Theme.accent
    palette.highlightedText: "white"
    palette.light: "#2d3846"
    palette.midlight: "#243040"
    palette.mid: "#3a4552"
    palette.dark: "#58677a"
    palette.shadow: "#000000"
    palette.placeholderText: Theme.dim
    palette.toolTipBase: Theme.panel
    palette.toolTipText: Theme.text
}
