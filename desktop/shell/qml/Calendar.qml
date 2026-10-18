// Fúzió — naptár (az órára kattintva); a hét hétfővel kezdődik
import QtQuick
import FusionUI

Rectangle {
    id: cal
    color: Theme.bg
    border.color: Theme.border
    focus: true
    Keys.onEscapePressed: shell.togglePopup("calendar")
    property int year: 2026
    property int month: 1   // 1..12
    readonly property var names: ["január","február","március","április","május","június","július","augusztus","szeptember","október","november","december"]
    // a Shell leállásakor (újraindítás, kikapcsolás) a „shell” már null lehet — egyszer olvassuk ki, ellenőrizve
    function clk() { var sh = shell; return sh ? (sh.clock || null) : null }
    function reset() { var c = clk(); if (c) { year = c.year; month = c.month } }
    function shift(d) { var m = month + d; if (m < 1) { m = 12; year-- } else if (m > 12) { m = 1; year++ } month = m }
    function cells() {
        var first = new Date(year, month - 1, 1)
        var off = (first.getDay() + 6) % 7          // hétfő = 0
        var days = new Date(year, month, 0).getDate()
        var out = []
        for (var i = 0; i < 42; i++) {
            var d = i - off + 1
            out.push(d >= 1 && d <= days ? d : 0)
        }
        return out
    }

    Text { x: 16; y: 14; text: (cal.clk() || {}).time || ""; color: Theme.text; font.family: Theme.font; font.pixelSize: 26 }
    Text { x: 16; y: 50; text: (cal.clk() || {}).long || ""; color: Theme.dim; font.family: Theme.font; font.pixelSize: 12 }
    Rectangle { x: 0; y: 74; width: parent.width; height: 1; color: Theme.border }
    Item {
        x: 10; y: 80; width: parent.width - 20; height: 32
        FToolButton { icon: "up"; rotation: -90; anchors.left: parent.left; onClicked: cal.shift(-1) }
        Text { anchors.centerIn: parent; text: cal.year + ". " + cal.names[cal.month - 1]; color: Theme.text
               font.family: Theme.font; font.pixelSize: 13; font.bold: true }
        FToolButton { icon: "up"; rotation: 90; anchors.right: parent.right; onClicked: cal.shift(1) }
    }
    Grid {
        x: 14; y: 116; columns: 7; spacing: 2
        Repeater { model: ["H", "K", "Sze", "Cs", "P", "Szo", "V"]
            Text { width: 36; height: 20; horizontalAlignment: Text.AlignHCenter; text: modelData; color: Theme.dim
                   font.family: Theme.font; font.pixelSize: 11 } }
        Repeater {
            model: cal.cells()
            Rectangle {
                width: 36; height: 24; radius: Theme.radius
                property var c: cal.clk()
                property bool today: !!c && modelData === c.day && cal.month === c.month && cal.year === c.year
                color: today ? Theme.accent : "transparent"
                Text { anchors.centerIn: parent; text: modelData || ""; color: parent.today ? "white" : (index % 7 >= 5 ? "#c9a0a0" : Theme.text)
                       font.family: Theme.font; font.pixelSize: 12 }
            }
        }
    }
}
