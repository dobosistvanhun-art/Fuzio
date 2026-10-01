// ikon a Fusion ikonkészletből: FIcon { name: "folder"; size: 16 } — vagy fájlból: name: "/data/programs/x/icon.png"
import QtQuick

Image {
    property string name: "file"
    property int size: 16
    width: size; height: size
    sourceSize.width: size * 2; sourceSize.height: size * 2
    source: !name ? "" : name.charAt(0) === "/" ? "file://" + name : fusionIconDir + name + ".svg"
    fillMode: Image.PreserveAspectFit
    smooth: true
    asynchronous: false
}
