// párbeszédablak (az ablakon belül, modális): FDialog { title: "…"; buttons: [["Mégse",""],["OK","primary"]] }
import QtQuick
import QtQuick.Controls

Popup {
    id: d
    property string title: ""
    property var buttons: [["OK", "primary"]]      // [felirat, "primary"|"danger"|""]
    property int defaultButton: buttons.length - 1  // Enter
    default property alias content: body.data
    signal buttonClicked(int index)
    modal: true; focus: true
    anchors.centerIn: Overlay.overlay
    padding: 0
    closePolicy: Popup.CloseOnEscape
    width: Math.max(380, body.childrenRect.width + 40)
    Overlay.modal: Rectangle { color: "#80000000" }
    background: Rectangle { color: Theme.bg; border.color: Theme.border }
    function press(i) { d.buttonClicked(i) }
    contentItem: FocusScope {
        implicitHeight: col.implicitHeight
        Keys.onReturnPressed: d.press(d.defaultButton)
        Keys.onEnterPressed: d.press(d.defaultButton)
        Column {
            id: col
            width: parent.width
            Rectangle {
                width: parent.width; height: 34; color: Theme.panel
                Text { anchors.fill: parent; anchors.leftMargin: 14; verticalAlignment: Text.AlignVCenter
                    text: d.title; color: Theme.text; font.family: Theme.font; font.pixelSize: Theme.fs; font.bold: true }
            }
            Item {
                id: body
                width: parent.width
                height: childrenRect.height + 32
                // a tartalom elemei: x: 20; y: 16 (a hívó helyezi el)
            }
            Rectangle { width: parent.width; height: 1; color: Theme.border }
            Item {
                width: parent.width; height: 50
                Row {
                    anchors.right: parent.right; anchors.rightMargin: 14; anchors.verticalCenter: parent.verticalCenter
                    spacing: 8
                    Repeater {
                        model: d.buttons
                        FButton { text: modelData[0]; primary: modelData[1] === "primary"; danger: modelData[1] === "danger"
                                  width: Math.max(90, implicitWidth); onClicked: d.press(index) }
                    }
                }
            }
        }
    }
}
