// csúszka: FSlider { from: 0; to: 100; value: 50; onMoved: … }
import QtQuick
import QtQuick.Controls

Slider {
    id: s
    implicitHeight: 26
    implicitWidth: 200
    background: Rectangle {
        x: s.leftPadding; y: s.topPadding + s.availableHeight / 2 - height / 2
        width: s.availableWidth; height: 4; radius: 2; color: "#2d3643"
        Rectangle { width: s.visualPosition * parent.width; height: parent.height; radius: 2
                    color: s.enabled ? Theme.accent : Theme.dim }
    }
    handle: Rectangle {
        x: s.leftPadding + s.visualPosition * (s.availableWidth - width); y: s.topPadding + s.availableHeight / 2 - height / 2
        width: 16; height: 16; radius: 8
        color: s.pressed ? "#dbe7f7" : "#c9d1d9"; border.color: Theme.accent; border.width: s.activeFocus ? 2 : 0
    }
}
