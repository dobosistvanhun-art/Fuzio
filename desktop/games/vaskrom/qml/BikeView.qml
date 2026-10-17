// a motor rajza: test + kerekek (forgathatók) + kipufogó-réteg; scale: méretarány
import QtQuick
Item {
    id: v
    property var art: null
    property real s: 0.5
    property real wheelAngle: 0          // fok
    property real wheelie: 0             // fok (ágaskodás)
    width: (art ? art.w : 680) * s; height: (art ? art.h : 380) * s
    Item {
        id: rig
        width: parent.width; height: parent.height
        transform: Rotation { origin.x: v.art ? (v.art.rx + v.art.rr * 0.3) * v.s : 0; origin.y: v.art ? v.art.ground * v.s : 0; angle: -v.wheelie }
        Image { visible: !!v.art && !!v.art.shadow; source: v.art && v.art.shadow ? v.art.shadow : ""; smooth: true
                width: parent.width; height: v.art ? (v.art.h + 14) * v.s : 0; sourceSize.width: width; sourceSize.height: height }
        Image { anchors.fill: parent; source: v.art ? v.art.body : ""; smooth: true; asynchronous: false
                sourceSize.width: width; sourceSize.height: height }
        Image { visible: !!v.art && !!v.art.rear; source: v.art ? v.art.rear : ""; smooth: true
                width: v.art ? (2 * v.art.rr + 8) * v.s : 0; height: width; sourceSize.width: width; sourceSize.height: height
                x: v.art ? v.art.rx * v.s - width / 2 : 0; y: v.art ? v.art.ry * v.s - height / 2 : 0; rotation: v.wheelAngle }
        Image { visible: !!v.art && !!v.art.front; source: v.art ? v.art.front : ""; smooth: true
                width: v.art ? (2 * v.art.fr + 8) * v.s : 0; height: width; sourceSize.width: width; sourceSize.height: height
                x: v.art ? v.art.fx * v.s - width / 2 : 0; y: v.art ? v.art.fy * v.s - height / 2 : 0
                rotation: v.art ? v.wheelAngle * v.art.rr / v.art.fr : 0 }
        Image { anchors.fill: parent; visible: !!v.art && !!v.art.over; source: v.art ? v.art.over : ""; smooth: true; sourceSize.width: width; sourceSize.height: height }
    }
}
