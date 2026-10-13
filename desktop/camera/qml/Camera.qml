// FusionOS — Kamera: élőkép, kameraváltás, fénykép, videófelvétel (Qt Multimedia + ffmpeg)
import QtQuick
import QtQuick.Controls
import QtMultimedia
import FusionUI

FWindow {
    id: win
    width: 820; height: 600
    minimumWidth: 480; minimumHeight: 380
    visible: true
    title: "Kamera"
    property string msg: ""
    property bool msgErr: false
    property string lastPhoto: ""
    property int camIndex: 0
    readonly property var inputs: md.videoInputs
    readonly property bool hasCam: inputs.length > 0

    Component.onCompleted: { if (!selftestMode) { raise(); requestActivate() } }
    Shortcut { sequence: "Esc"; onActivated: win.close() }
    Shortcut { sequence: "Space"; onActivated: win.shoot() }
    Shortcut { sequence: "R"; onActivated: win.toggleRecord() }
    property string recTime: ""
    property bool withSound: true
    // bezáráskor a futó felvétel lezárul (különben a fájl befejezetlen maradna)
    onClosing: if (cam.recording) cam.stopRecording()
    function toggleRecord() {
        if (!hasCam) return
        if (cam.recording) {
            var r = cam.stopRecording()
            if (r.ok) { lastPhoto = r.path; say("Videó mentve: " + r.path, false) }
            else say("A videó nem készült el: " + r.message, true)
        } else {
            var e = cam.startRecording(vo.videoSink, withSound)
            if (e) say("A felvétel nem indult: " + e, true)
        }
    }
    Timer { interval: 500; repeat: true; running: cam.recording; onTriggered: win.recTime = cam.recordingTime() }
    Connections {
        target: cam
        function onMessage(text, isErr) {
            if (text === "__raise__") { win.show(); win.raise(); win.requestActivate(); return }
            win.say(text, isErr)
        }
    }
    // a legjobb képformátum: a legnagyobb felbontás 1280×720-ig, legalább 15 kép/mp; egyenlőnél a gyorsabb —
    // a Qt magától gyakran a legkisebbet választja (ZBook, 0.0.41: gyenge minőségű kép)
    function bestFormat(dev) {
        var best = null, bestScore = -1
        var fs = dev ? dev.videoFormats : []
        for (var i = 0; i < fs.length; i++) {
            var f = fs[i], w = f.resolution.width, h = f.resolution.height
            if (w > 1280 || h > 720 || f.maxFrameRate < 15) continue
            var score = w * h * 1000 + Math.min(f.maxFrameRate, 60)
            if (score > bestScore) { best = f; bestScore = score }
        }
        return best
    }
    function say(t, err) { msg = t; msgErr = err; msgTimer.restart() }
    // fénykép: az élőkép aktuális képkockája (a Qt Multimedia háttértől független)
    function shoot() {
        if (!hasCam) return
        var path = cam.saveFrame(vo.videoSink)
        if (path) { lastPhoto = path; flashAnim.restart(); say("Mentve: " + path, false) }
        else say("A kép nem készült el — még nincs élőkép.", true)
    }
    Timer { id: msgTimer; interval: 6000; onTriggered: win.msg = "" }
    // önteszt: néhány másodperc élőkép után egy kép az élőképből, majd kilépés
    Timer { interval: 8000; running: selftestMode && win.hasCam
            onTriggered: { cam.selftestShot(vo.videoSink, camera.cameraFormat.resolution.width + "x"
                                           + camera.cameraFormat.resolution.height) } }

    MediaDevices { id: md }
    CaptureSession {
        camera: Camera {
            id: camera
            cameraDevice: win.hasCam ? win.inputs[Math.min(win.camIndex, win.inputs.length - 1)] : md.defaultVideoInput
            function pickFormat() { var f = win.bestFormat(cameraDevice); if (f) cameraFormat = f }
            onCameraDeviceChanged: pickFormat()
            Component.onCompleted: pickFormat()
            active: win.hasCam && win.visible
            onErrorOccurred: (error, errorString) => win.say("Kamerahiba: " + errorString, true)
        }
        videoOutput: vo
    }

    Rectangle {
        id: view
        anchors { left: parent.left; right: parent.right; top: parent.top; bottom: bar.top; margins: 10 }
        color: "black"; radius: Theme.radius
        VideoOutput { id: vo; anchors.fill: parent; fillMode: VideoOutput.PreserveAspectFit }
        Column {
            anchors.centerIn: parent; spacing: 10; visible: !win.hasCam
            FIcon { name: "camera"; size: 56; anchors.horizontalCenter: parent.horizontalCenter; opacity: 0.6 }
            FLabel { text: "Nem található kamera"; bold: true; anchors.horizontalCenter: parent.horizontalCenter }
            FLabel { dim: true; width: 380; wrapMode: Text.Wrap; horizontalAlignment: Text.AlignHCenter
                     text: "A beépített webkamerát egyes gépeken a BIOS-ban vagy egy billentyűvel lehet ki- és bekapcsolni. "
                           + "USB-kamera: dugja be, és a lista magától frissül." }
        }
        Rectangle {
            visible: cam.recording; x: 12; y: 12; height: 28; width: rl.implicitWidth + 30; radius: 14; color: "#b62324"
            Rectangle { x: 10; anchors.verticalCenter: parent.verticalCenter; width: 10; height: 10; radius: 5; color: "white" }
            FLabel { id: rl; x: 26; anchors.verticalCenter: parent.verticalCenter; text: "FELVÉTEL  " + win.recTime; bold: true; color: "white" }
        }
        // villanás a kép készítésekor
        Rectangle { id: flash; anchors.fill: parent; color: "white"; opacity: 0; radius: Theme.radius
                    NumberAnimation on opacity { id: flashAnim; from: 0.7; to: 0; duration: 250; running: false } }
    }

    Rectangle {
        id: bar
        anchors { left: parent.left; right: parent.right; bottom: parent.bottom }
        height: 56; color: Theme.panel
        Row {
            anchors.left: parent.left; anchors.leftMargin: 12; anchors.verticalCenter: parent.verticalCenter; spacing: 8
            ComboBox {
                id: sel; width: 260; visible: win.inputs.length > 1
                model: win.inputs.map(d => d.description)
                currentIndex: win.camIndex
                onActivated: (i) => win.camIndex = i
            }
            FLabel { visible: win.inputs.length === 1; text: win.hasCam ? win.inputs[0].description : ""; dim: true
                     anchors.verticalCenter: parent.verticalCenter; width: 260 }
        }
        Row {
            anchors.centerIn: parent; spacing: 10
            FButton {
                text: "Fénykép"; icon: "camera"; primary: true
                enabled: win.hasCam && camera.active; tip: "Szóköz"
                onClicked: win.shoot()
            }
            FButton {
                text: cam.recording ? "Leállítás  " + win.recTime : "Videó"; icon: cam.recording ? "close" : "dot"
                danger: cam.recording; enabled: win.hasCam && camera.active; tip: "R"
                onClicked: win.toggleRecord()
            }
            FCheck { text: "hanggal"; checked: win.withSound; enabled: !cam.recording
                     onToggled: win.withSound = checked; anchors.verticalCenter: parent.verticalCenter }
        }
        Row {
            anchors.right: parent.right; anchors.rightMargin: 12; anchors.verticalCenter: parent.verticalCenter; spacing: 8
            FButton { visible: win.lastPhoto !== ""; text: "Mappa"; icon: "folder-open"; flat: true
                      onClicked: cam.showFile(win.lastPhoto) }
            FToolButton { icon: "settings"; tip: "Eszközök (Beállítások)"; onClicked: cam.openSettings() }
        }
    }
    Rectangle {
        visible: win.msg !== ""
        anchors.horizontalCenter: parent.horizontalCenter; anchors.bottom: bar.top; anchors.bottomMargin: 18
        width: Math.min(mt.implicitWidth + 28, win.width - 40); height: 34; radius: 17
        color: win.msgErr ? "#5a1d1d" : "#1d2a3a"; border.color: win.msgErr ? Theme.danger : Theme.border
        FLabel { id: mt; anchors.centerIn: parent; width: parent.width - 28; text: win.msg; horizontalAlignment: Text.AlignHCenter }
    }
}
