// Drag-verseny (402 m): lámpa, gáz (SZÓKÖZ), kuplung és váltás (JOBB NYÍL / ENTER); a fizika a model.simulate párja
import QtQuick
import QtQuick.Controls

Rectangle {
    id: rc
    property var info: null
    signal closed()
    color: "#0b0c0e"
    focus: true

    readonly property real quarter: 402.3
    readonly property real ppm: 32                       // képpont / méter a pályán
    readonly property real meS: 0.42
    readonly property real oppS: 0.34
    readonly property real camX: width * 0.30
    readonly property real startOff: info && info.me ? (info.me.art.fx - info.me.art.rx) * meS / ppm : 4
    property bool practice: !info || !info.opp
    property real clock: 0                               // mp a megnyitás óta
    readonly property real greenAt: 2.9
    property string phase: "lights"                      // lights | race | done
    property bool gas: false
    property bool foul: false
    property var me: null
    property var opp: null
    property var result: null
    property real tick: 0                                // kirajzolás frissítése
    property var smoke: []

    function curveT(p, rpm) {
        var c = p.curve
        if (rpm <= c[0][0]) return c[0][1]
        for (var i = 1; i < c.length; i++)
            if (rpm <= c[i][0]) return c[i - 1][1] + (c[i][1] - c[i - 1][1]) * (rpm - c[i - 1][0]) / (c[i][0] - c[i - 1][0])
        return c[c.length - 1][1]
    }
    function newCar(p) {
        return { p: p, x: 0, v: 0, gear: 0, rpm: p.idle, launched: false, launchT: 0, slipT: 0, shiftT: 0, throttle: false,
                 spin: false, wh: 0, overRev: 0, limT: 0, finished: false, et: 0, react: 0, top: 0, angle: 0 }
    }
    function step(c, dt) {
        var p = c.p, g = 9.81, m = p.mass
        if (c.finished) { c.v = Math.max(0, c.v - 6 * dt); c.x += c.v * dt; c.rpm = Math.max(p.idle, c.rpm - 3000 * dt); c.wh *= 0.9; return }
        if (!c.launched) {                                   // álló motor: felpörgetés
            if (c.throttle) c.rpm += (c.target ? Math.sign(c.target - c.rpm) * Math.min(Math.abs(c.target - c.rpm), 9000 * dt) : 8000 * dt)
            else c.rpm -= 5000 * dt
            if (c.rpm >= p.red) c.rpm = p.red - 350 * Math.random() - 150    // leszabályozó
            c.rpm = Math.max(p.idle, c.rpm)
            return
        }
        var ratio = p.ratios[c.gear]
        var wheelRpm = c.v / (2 * Math.PI * p.radius) * 60 * ratio
        if (c.shiftT > 0) { c.shiftT -= dt; c.rpm = Math.max(wheelRpm, c.rpm - 3000 * dt) }
        else if (c.slipT >= 0 && wheelRpm < c.rpm && c.slipT < 2.5) { c.rpm = Math.max(c.rpm - 1500 * dt, 2000); c.slipT += dt }
        else { c.slipT = -1; c.rpm = Math.max(wheelRpm, p.idle) }
        var torque = (c.throttle && c.shiftT <= 0 && c.rpm < p.red) ? curveT(p, c.rpm) : 0
        if (c.throttle && c.rpm >= p.red * 0.995) { c.limT += dt; if (c.limT > 0.25) c.overRev += dt } else c.limT = 0
        if (c.rpm > p.red) c.rpm = p.red + 60 * Math.random()
        var f = torque * ratio * p.eff / p.radius
        var rear = m * g * (1 - p.cg * 0.55) + f * 0.25
        var fmax = p.grip * rear
        c.spin = f > fmax
        if (c.spin) f = fmax * 0.85
        var wl = m * g * p.wheelbase * 0.62 / 0.6
        var wt = f > wl * 0.8 ? Math.min(13, (f - wl * 0.8) / (wl * 0.2) * 13) : 0
        c.wh += (wt - c.wh) * Math.min(1, dt * 5)
        f = Math.min(f, wl)
        var drag = 0.5 * 1.2 * p.cda * c.v * c.v + 0.015 * m * g
        c.v = Math.max(0, c.v + (f - drag) / m * dt)
        c.x += c.v * dt
        c.top = Math.max(c.top, c.v)
        c.angle += (c.v * dt + (c.spin ? 0.25 : 0)) / (2 * Math.PI * p.radius) * 360
        if (c.x >= quarter) { c.finished = true; c.et = clock - greenAt }
    }
    function launch(c) { c.launched = true; c.react = clock - greenAt; c.slipT = 0 }
    function shift(c) { if (c.gear < c.p.ratios.length - 1) { c.gear += 1; c.shiftT = 0.12 } }
    function clutch() {
        if (phase === "done" || !me) return
        if (!me.launched) {
            if (clock < greenAt) foul = true
            launch(me)
        } else shift(me)
    }
    function ai(dt) {
        var c = opp, p = c.p
        if (!c.launched) {
            c.throttle = clock > 1.0
            c.target = p.launch * p.red
            if (clock >= greenAt + Math.max(0.05, p.reaction)) launch(c)
        } else {
            c.throttle = true
            if (c.shiftT <= 0 && c.rpm >= p.shift * p.red && c.slipT < 0) shift(c)
        }
    }
    function advance(dt) {
        clock += dt
        me.throttle = gas
        if (opp) ai(dt)
        step(me, dt)
        if (opp) step(opp, dt)
        if (me.spin && me.v < 40 && Math.random() < 0.5)
            smoke.push({ x: me.x, y: 0, r: 8, a: 0.55, vx: -1 - Math.random() * 2, vy: 0.4 + Math.random() * 0.8 })
        if (opp && opp.spin && opp.v < 40 && Math.random() < 0.4)
            smoke.push({ x: opp.x, y: 0, r: 6, a: 0.45, vx: -1 - Math.random() * 2, vy: 0.4 + Math.random() * 0.6, far: true })
        for (var i = smoke.length - 1; i >= 0; i--) {
            var s = smoke[i]; s.x += s.vx * dt; s.y += s.vy * dt; s.r += 30 * dt; s.a -= 0.5 * dt
            if (s.a <= 0) smoke.splice(i, 1)
        }
        if (phase === "race" && (me.finished || clock - greenAt > 40)) finish()
    }
    function finish() {
        phase = "done"
        var myT = me.finished ? me.et : 99
        var theirT = 0
        if (opp) {
            var guard = 0
            while (!opp.finished && guard++ < 20000) { clock += 1 / 120; ai(1 / 120); step(opp, 1 / 120) }
            theirT = opp.finished ? opp.et : 99
        }
        var won = practice ? true : (!foul && myT < theirT)
        var res = game.raceDone(info.name, info.bet, info.pink, won, myT, theirT, me.overRev, foul)
        result = { won: won, my: myT, their: theirT, react: me.react, top: Math.round(me.top * 3.6),
                   otop: opp ? Math.round(opp.top * 3.6) : 0, res: res || {}, over: me.overRev }
    }

    Component.onCompleted: {
        me = newCar(info.me)
        if (info.opp) opp = newCar(info.opp)
        forceActiveFocus()
        last = Date.now()
    }
    property double last: 0
    Timer {
        interval: 16; repeat: true; running: rc.phase !== "done" || rc.smoke.length > 0
        onTriggered: {
            var now = Date.now(), el = Math.min(0.1, (now - rc.last) / 1000)
            rc.last = now
            if (rc.phase === "lights" && rc.clock >= rc.greenAt) rc.phase = "race"
            var n = Math.max(1, Math.round(el * 120))
            for (var i = 0; i < n; i++) rc.advance(el / n)
            rc.sync()
            rc.tick += 1
        }
    }
    Keys.onPressed: function (e) {
        if (e.isAutoRepeat) { e.accepted = true; return }
        if (e.key === Qt.Key_Space) { gas = true; e.accepted = true }
        else if (e.key === Qt.Key_Right || e.key === Qt.Key_Return || e.key === Qt.Key_Enter) { clutch(); e.accepted = true }
        else if (e.key === Qt.Key_Escape && phase === "done") closed()
    }
    Keys.onReleased: function (e) { if (e.key === Qt.Key_Space && !e.isAutoRepeat) { gas = false; e.accepted = true } }

    // ---- kép
    // a rajzhoz: a JS-objektumok másolata képkockánként (a QML a belső mezők változását nem követi)
    property real myX: 0
    property var hm: ({ x: 0, v: 0, rpm: 0, gear: 0, launched: false, spin: false, lim: 0, react: 0, wh: 0, angle: 0 })
    property var ho: ({ x: 0, wh: 0, angle: 0 })
    function sync() {
        myX = me.x
        hm = { x: me.x, v: me.v, rpm: me.rpm, gear: me.gear, launched: me.launched, spin: me.spin, lim: me.limT, react: me.react, wh: me.wh, angle: me.angle }
        if (opp) ho = { x: opp.x, wh: opp.wh, angle: opp.angle }
    }
    function sx(worldX) { return camX + (worldX - myX) * ppm }
    readonly property real horizon: height * 0.36
    readonly property real farLane: height * 0.60
    readonly property real nearLane: height * 0.80

    Rectangle {
        width: parent.width; height: rc.horizon
        gradient: Gradient { GradientStop { position: 0; color: "#1a2a4a" } GradientStop { position: 0.7; color: "#d9773a" } GradientStop { position: 1; color: "#f2b25a" } }
    }
    // távoli város (lassú parallaxis)
    Canvas {
        id: city; y: rc.horizon - 140; width: rc.width * 2; height: 140
        x: -((rc.myX * rc.ppm * 0.06) % rc.width)
        onPaint: {
            var c = getContext("2d"), w = width / 2
            c.fillStyle = "#2a1e2e"
            var seed = 3
            function r() { seed = (seed * 9301 + 49297) % 233280; return seed / 233280 }
            var xs = [], x = 0
            while (x < w) { var bw = 30 + r() * 60, bh = 30 + r() * 100; xs.push([x, bw, bh]); x += bw + 4 }
            for (var k = 0; k < 2; k++) for (var i = 0; i < xs.length; i++) c.fillRect(xs[i][0] + k * w, 140 - xs[i][2], xs[i][1], xs[i][2])
            c.fillStyle = "rgba(255,210,120,0.6)"
            for (k = 0; k < 2; k++) for (i = 0; i < xs.length; i++)
                for (var yy = 140 - xs[i][2] + 8; yy < 130; yy += 14) for (var xx = xs[i][0] + 6; xx < xs[i][0] + xs[i][1] - 6; xx += 12)
                    if ((xx * 7 + yy * 3) % 5 < 2) c.fillRect(xx + k * w, yy, 4, 6)
        }
    }
    // lelátó és kerítés (közepes parallaxis)
    Canvas {
        y: rc.horizon - 70; width: rc.width + 400; height: rc.farLane - rc.horizon + 30
        x: -((rc.myX * rc.ppm * 0.5) % 400)
        onPaint: {
            var c = getContext("2d"), h = height
            c.fillStyle = "#3d4a3a"; c.fillRect(0, 70, width, h - 70)
            for (var x = 0; x < width; x += 400) {
                c.fillStyle = "#5a5f66"; c.fillRect(x + 20, 10, 300, 60)
                c.fillStyle = "#3a3d42"; for (var r = 0; r < 4; r++) c.fillRect(x + 20, 18 + r * 14, 300, 3)
                c.fillStyle = "#8a2a1a"; c.fillRect(x + 10, 0, 320, 10)
                for (var p = 0; p < 28; p++) { c.fillStyle = ["#d9773a", "#3a6ea5", "#e8e8e8", "#c4271b"][p % 4]
                                               c.fillRect(x + 28 + p * 10.5, 22 + (p * 7 % 4) * 12, 6, 8) }
            }
            c.strokeStyle = "#9aa0a6"; c.lineWidth = 2
            c.beginPath(); c.moveTo(0, 74); c.lineTo(width, 74); c.stroke()
            for (x = 0; x < width; x += 25) { c.beginPath(); c.moveTo(x, 74); c.lineTo(x, 100); c.stroke() }
            c.beginPath(); c.moveTo(0, 100); c.lineTo(width, 100); c.stroke()
        }
    }
    // aszfalt
    Rectangle {
        y: rc.farLane - 50; width: parent.width; height: parent.height - y
        gradient: Gradient { GradientStop { position: 0; color: "#3a3b3e" } GradientStop { position: 1; color: "#1c1d1f" } }
    }
    // sávelválasztó, szaggatott (a pályával együtt mozog)
    Canvas {
        y: (rc.farLane + rc.nearLane) / 2 - 18; width: rc.width + 200; height: 6
        x: -((rc.myX * rc.ppm) % 200)
        onPaint: { var c = getContext("2d"); c.fillStyle = "#e8e8e8"; for (var x = 0; x < width; x += 200) c.fillRect(x, 0, 110, 6) }
    }
    Rectangle { y: rc.nearLane + 18; width: parent.width; height: 5; color: "#d9c27a" }
    Rectangle { y: rc.farLane - 46; width: parent.width; height: 4; color: "#d9c27a" }
    // rajt, táblák, cél
    Repeater {
        model: [[0, "RAJT"], [100, "100 m"], [201, "201 m"], [300, "300 m"], [402.3, "CÉL"]]
        Item {
            property real wx: modelData[0] + rc.startOff
            x: rc.sx(wx); y: rc.farLane - 50; width: 1; height: rc.nearLane - rc.farLane + 70
            visible: x > -200 && x < rc.width + 200
            Grid {
                visible: modelData[1] === "CÉL" || modelData[1] === "RAJT"; x: -8; columns: 2; rows: Math.ceil(parent.height / 8)
                Repeater { model: parent.columns * parent.rows
                    Rectangle { width: 8; height: 8; color: modelData[1] === "RAJT" ? "white" : ((index + Math.floor(index / 2)) % 2 ? "white" : "black") } }
            }
            Rectangle { visible: modelData[1] !== "CÉL" && modelData[1] !== "RAJT"; x: -2; width: 4; height: parent.height; color: "#ffffff55" }
            Rectangle {
                x: -40; y: -120; width: 80; height: 44; color: modelData[1] === "CÉL" ? "#c4271b" : "#1b1d21"; border.color: "#ffcf3a"; border.width: 2
                Text { anchors.centerIn: parent; text: modelData[1]; color: "white"; font.bold: true; font.pixelSize: 16 }
                Rectangle { x: 38; y: 44; width: 4; height: 76; color: "#5a5f66" }
            }
        }
    }
    // füst (hátsó kerék mögött)
    Canvas {
        id: smokeCv; anchors.fill: parent; z: 3
        property real t: rc.tick
        onTChanged: requestPaint()
        onPaint: {
            var c = getContext("2d"); c.clearRect(0, 0, width, height)
            for (var i = 0; i < rc.smoke.length; i++) {
                var s = rc.smoke[i]
                c.fillStyle = "rgba(220,220,220," + Math.max(0, s.a) + ")"
                c.beginPath(); c.arc(rc.sx(s.x) - (s.far ? 20 : 30), (s.far ? rc.farLane : rc.nearLane) - 10 - s.y * 30, s.r * (s.far ? 0.8 : 1), 0, 6.3); c.fill()
            }
        }
    }
    // ellenfél (távoli sáv)
    BikeView {
        visible: !!rc.opp; z: 2
        art: rc.info && rc.info.opp ? rc.info.opp.art : null; s: rc.oppS
        x: rc.opp && art ? rc.sx(rc.ho.x) - art.rx * s : 0; y: rc.farLane - (art ? art.ground * s : 0)
        wheelAngle: rc.ho.angle; wheelie: rc.ho.wh
    }
    // én (közeli sáv)
    BikeView {
        z: 4; art: rc.info ? rc.info.me.art : null; s: rc.meS
        x: rc.camX - (art ? art.rx * s : 0); y: rc.nearLane - (art ? art.ground * s : 0)
        wheelAngle: rc.hm.angle; wheelie: rc.hm.wh
    }

    // ---- HUD
    // lámpa (karácsonyfa)
    Rectangle {
        z: 6; anchors.horizontalCenter: parent.horizontalCenter; y: 14; width: 70; height: 200; radius: 8; color: "#111"; border.color: "#444"
        visible: rc.phase === "lights" || rc.clock < rc.greenAt + 1.5
        Column {
            anchors.centerIn: parent; spacing: 8
            Repeater {
                model: 3
                Rectangle { width: 36; height: 36; radius: 18; border.color: "#000"
                            color: rc.clock >= 1.4 + index * 0.5 && rc.clock < rc.greenAt ? "#ffb000" : "#3a2a00" }
            }
            Rectangle { width: 36; height: 36; radius: 18; color: rc.clock >= rc.greenAt ? (rc.foul ? "#3a0000" : "#20ff40") : "#003a10"; border.color: "#000" }
            Rectangle { width: 36; height: 14; radius: 4; color: rc.foul ? "#ff2020" : "#3a0000"; border.color: "#000" }
        }
    }
    Text {
        z: 6; anchors.horizontalCenter: parent.horizontalCenter; y: 222
        visible: rc.phase === "lights" || rc.foul && rc.phase !== "done"
        text: rc.foul ? "KORAI INDULÁS!" : rc.clock < 1.4 ? "Készülj… SZÓKÖZ = gáz" : "zöldnél: JOBB NYÍL / ENTER"
        color: rc.foul ? "#ff4040" : "white"; font.pixelSize: 20; font.bold: true; style: Text.Outline; styleColor: "black"
    }
    // haladás
    Rectangle {
        z: 6; x: 20; y: 16; width: 360; height: rc.opp ? 52 : 30; radius: 6; color: "#c0000000"; border.color: "#444"
        Rectangle { x: 10; y: 14; width: 340; height: 2; color: "#666" }
        Rectangle { x: 10 + 340 * Math.min(1, rc.myX / rc.quarter) - 6; y: 9; width: 12; height: 12; radius: 6; color: "#ffcf3a" }
        Rectangle { visible: !!rc.opp; x: 10; y: 36; width: 340; height: 2; color: "#666" }
        Rectangle { visible: !!rc.opp; x: 10 + 340 * Math.min(1, rc.ho.x / rc.quarter) - 6; y: 31
                    width: 12; height: 12; radius: 6; color: "#e5534b" }
    }
    Text { z: 6; x: 20; y: rc.opp ? 74 : 52; text: rc.info ? (rc.practice ? "PRÓBAFUTAM" : "vs " + rc.info.name + (rc.info.pink ? " — FORGALMIRA" : " — " + win.money(rc.info.bet))) : ""
           color: "white"; font.pixelSize: 16; font.bold: true; style: Text.Outline; styleColor: "black" }
    // fordulatszámmérő, fokozat, sebesség
    Item {
        z: 6; anchors.right: parent.right; anchors.top: parent.top; anchors.margins: 14; width: 250; height: 250
        Canvas {
            id: tach; anchors.fill: parent
            property real t: rc.tick
            onTChanged: requestPaint()
            onPaint: {
                if (!rc.me) return
                var c = getContext("2d"), cx = width / 2, cy = height / 2, R = width / 2 - 6
                var red = rc.me.p.red, max = Math.ceil(red * 1.12 / 1000) * 1000
                function ang(r) { return (135 + 270 * r / max) * Math.PI / 180 }
                c.clearRect(0, 0, width, height)
                c.fillStyle = "#101113"; c.beginPath(); c.arc(cx, cy, R, 0, 6.3); c.fill()
                c.strokeStyle = "#5a5f66"; c.lineWidth = 3; c.stroke()
                c.strokeStyle = "#c4271b"; c.lineWidth = 12; c.beginPath(); c.arc(cx, cy, R - 14, ang(red), ang(max)); c.stroke()
                c.fillStyle = "white"; c.strokeStyle = "white"; c.font = "bold 15px 'DejaVu Sans'"; c.textAlign = "center"; c.textBaseline = "middle"
                for (var r = 0; r <= max; r += 1000) {
                    var a = ang(r)
                    c.lineWidth = 3; c.beginPath(); c.moveTo(cx + Math.cos(a) * (R - 22), cy + Math.sin(a) * (R - 22))
                    c.lineTo(cx + Math.cos(a) * (R - 6), cy + Math.sin(a) * (R - 6)); c.stroke()
                    c.fillText(String(r / 1000), cx + Math.cos(a) * (R - 40), cy + Math.sin(a) * (R - 40))
                }
                var na = ang(Math.min(max, rc.me.rpm))
                c.strokeStyle = "#ff3b2b"; c.lineWidth = 4
                c.beginPath(); c.moveTo(cx, cy); c.lineTo(cx + Math.cos(na) * (R - 18), cy + Math.sin(na) * (R - 18)); c.stroke()
                c.fillStyle = "#5a5f66"; c.beginPath(); c.arc(cx, cy, 10, 0, 6.3); c.fill()
                c.fillStyle = "#9aa0a6"; c.font = "11px 'DejaVu Sans'"; c.fillText("×1000/perc", cx, cy + 34)
            }
        }
        Text { anchors.horizontalCenter: parent.horizontalCenter; y: parent.height * 0.62
               text: rc.hm.launched ? String(rc.hm.gear + 1) : "N"
               color: rc.hm.lim > 0.05 ? "#ff3b2b" : "#ffd54a"; font.pixelSize: 40; font.bold: true }
    }
    Column {
        z: 6; anchors.right: parent.right; anchors.rightMargin: 280; y: 24; spacing: 2
        Text { text: Math.round(rc.hm.v * 3.6) + " km/h"; color: "white"; font.pixelSize: 34; font.bold: true
               style: Text.Outline; styleColor: "black"; anchors.right: parent.right }
        Text { text: (rc.clock >= rc.greenAt ? (rc.clock - rc.greenAt).toFixed(2) : "0.00") + " s"; color: "#cfd3d8"; font.pixelSize: 22
               style: Text.Outline; styleColor: "black"; anchors.right: parent.right }
        Text { visible: rc.hm.launched; text: "reakció " + rc.hm.react.toFixed(3) + " s"; color: "#9aa0a6"; font.pixelSize: 14
               anchors.right: parent.right }
        Text { visible: rc.hm.spin; text: "KIPÖRÖG!"; color: "#ffb000"; font.pixelSize: 18; font.bold: true; anchors.right: parent.right }
        Text { visible: rc.hm.lim > 0.25; text: "VÁLTS! (motorkár)"; color: "#ff3b2b"; font.pixelSize: 18; font.bold: true; anchors.right: parent.right }
    }
    // érintős / egeres vezérlés
    Row {
        z: 6; anchors.bottom: parent.bottom; anchors.right: parent.right; anchors.margins: 18; spacing: 14
        visible: rc.phase !== "done"
        Rectangle {
            width: 150; height: 70; radius: 10; color: gasMa.pressed ? "#3fb950" : "#1d3a24"; border.color: "#3fb950"; border.width: 2
            Text { anchors.centerIn: parent; text: "GÁZ\n(szóköz)"; horizontalAlignment: Text.AlignHCenter; color: "white"; font.bold: true; font.pixelSize: 16 }
            MouseArea { id: gasMa; anchors.fill: parent; onPressed: rc.gas = true; onReleased: rc.gas = false; onCanceled: rc.gas = false }
        }
        Rectangle {
            width: 170; height: 70; radius: 10; color: clMa.pressed ? "#d42a1c" : "#3a1010"; border.color: "#ffcf3a"; border.width: 2
            Text { anchors.centerIn: parent; text: (rc.hm.launched ? "VÁLTÁS" : "KUPLUNG") + "\n(→ / Enter)"; horizontalAlignment: Text.AlignHCenter
                   color: "white"; font.bold: true; font.pixelSize: 16 }
            MouseArea { id: clMa; anchors.fill: parent; onPressed: { rc.clutch(); rc.forceActiveFocus() } }
        }
    }
    Btn { z: 6; anchors.left: parent.left; anchors.bottom: parent.bottom; anchors.margins: 18; text: "FELADOM"; visible: rc.phase !== "done"
          onClicked: { rc.clock = rc.greenAt + 41; rc.phase = "race"; rc.finish() } }

    // eredmény
    Rectangle {
        z: 10; anchors.fill: parent; color: "#b0000000"; visible: !!rc.result
        Panel {
            anchors.centerIn: parent; width: 560; height: 330
            title: rc.result ? (rc.practice ? "PRÓBAFUTAM" : rc.result.won ? "NYERTÉL!" : "VESZTETTÉL") : ""
            Column {
                width: parent.width; spacing: 10
                Text { text: rc.result ? (rc.practice ? "Idő" : rc.result.won ? "Szép volt!" : rc.foul ? "Piros lámpa — korán indultál." : "Ezúttal ő volt a gyorsabb.") : ""
                       color: rc.result && rc.result.won ? "#7ee787" : "#ff7b72"; font.pixelSize: 22; font.bold: true }
                Grid {
                    columns: rc.practice ? 2 : 3; columnSpacing: 30; rowSpacing: 6
                    Text { text: " "; width: 120; color: "white" }
                    Text { text: "TE"; color: "#ffd54a"; font.bold: true; font.pixelSize: 15 }
                    Text { visible: !rc.practice; text: rc.info ? rc.info.name : ""; color: "#ff7b72"; font.bold: true; font.pixelSize: 15 }
                    Text { text: "402 m"; color: "#9aa0a6"; font.pixelSize: 15 }
                    Text { text: rc.result ? (rc.result.my >= 99 ? "—" : rc.result.my.toFixed(3) + " s") : ""; color: "white"; font.pixelSize: 18; font.bold: true }
                    Text { visible: !rc.practice; text: rc.result ? (rc.result.their >= 99 ? "—" : rc.result.their.toFixed(3) + " s") : ""; color: "white"; font.pixelSize: 18; font.bold: true }
                    Text { text: "végsebesség"; color: "#9aa0a6"; font.pixelSize: 15 }
                    Text { text: rc.result ? rc.result.top + " km/h" : ""; color: "white"; font.pixelSize: 16 }
                    Text { visible: !rc.practice; text: rc.result ? rc.result.otop + " km/h" : ""; color: "white"; font.pixelSize: 16 }
                    Text { text: "reakció"; color: "#9aa0a6"; font.pixelSize: 15 }
                    Text { text: rc.result ? rc.result.react.toFixed(3) + " s" : ""; color: "white"; font.pixelSize: 16 }
                    Text { visible: !rc.practice; text: rc.opp ? Math.max(0.05, rc.opp.p.reaction).toFixed(3) + " s" : ""; color: "white"; font.pixelSize: 16 }
                }
                Text {
                    width: parent.width; wrapMode: Text.Wrap; color: "#e8e8e8"; font.pixelSize: 16
                    text: !rc.result ? "" : [
                        rc.practice || rc.info.pink ? "" : (rc.result.won ? "Nyereményed: " + win.money(rc.info.bet) : "Vesztettél: " + win.money(rc.info.bet)),
                        rc.result.res.got ? "Megkaptad: " + rc.result.res.got : "",
                        rc.result.res.lost ? "Elvitték a motorodat: " + rc.result.res.lost : "",
                        rc.result.over > 0 ? "Túlpörgetted (" + rc.result.over.toFixed(1) + " s) — a motorblokk megsínylette." : ""
                    ].filter(function (s) { return s !== "" }).join("\n")
                }
            }
            Btn { anchors.right: parent.right; anchors.bottom: parent.bottom; text: "VISSZA"; kind: "red"; fs: 16; height: 40; onClicked: rc.closed() }
        }
    }
}
