// ikon a Fusion ikonkészletből: FIcon { name: "folder"; size: 16 }
import QtQuick

Image {
    property string name: "file"
    property int size: 16
    width: size; height: size
    sourceSize.width: size * 2; sourceSize.height: size * 2
    source: name ? fusionIconDir + name + ".svg" : ""
    fillMode: Image.PreserveAspectFit
    smooth: true
    asynchronous: false
}
