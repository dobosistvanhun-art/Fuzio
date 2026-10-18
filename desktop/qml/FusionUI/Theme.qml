// Fúzió — FusionDark téma (a Fúzió Desktop minden programja ezt használja)
// GUI-elv: gyors, egyszerű, informatív; nincs áttetszőség, felesleges animáció, erőltetett kerekítés.
pragma Singleton
import QtQuick

QtObject {
    readonly property color panel: "#11161c"      // panel, fejlécek
    readonly property color bg: "#161b22"         // ablakok háttere
    readonly property color base: "#0d1117"       // listák, beviteli mezők
    readonly property color alt: "#12171e"        // listák váltakozó sora
    readonly property color border: "#2a3441"
    readonly property color hover: "#1f2933"
    readonly property color selected: "#243447"   // aktív sor / gomb
    readonly property color mark: "#e3b341"       // kijelölt (megjelölt) fájl
    readonly property color text: "#e6edf3"
    readonly property color dim: "#8b949e"
    readonly property color accent: "#2f81f7"
    readonly property color accentDim: "#1f4f8f"
    readonly property color ok: "#3fb950"
    readonly property color warn: "#d29922"
    readonly property color danger: "#f85149"
    readonly property string font: "DejaVu Sans"
    readonly property string mono: "DejaVu Sans Mono"
    readonly property int fs: 13          // alap betűméret (px)
    readonly property int fsSmall: 11
    readonly property int fsBig: 16
    readonly property int radius: 3
    readonly property int row: 24         // listasor magassága
}
