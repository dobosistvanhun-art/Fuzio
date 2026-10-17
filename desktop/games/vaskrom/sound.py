"""Vas & Króm — hangok, valós időben kiszámolva (nincs hangfájl): motorhang a fordulathoz és a hengerszámhoz,
kipörgés, lámpa, váltás, felületi hangok. Tiszta Python (numpy nélkül), QAudioSink-re írva.

Motorhang: minden gyújtás egy rövid, lecsengő kipufogó-impulzus (alacsony rezonancia + zaj); a gyújtások
ritmusa adja a hangot: V2 (45°) — 0° és 315° a 720°-os ciklusban („krumpli-krumpli”), V8 (kereszt-főtengely) — 90°-onként,
soronként eltérő erővel (dübörgés). A hangosabb kipufogó: erősebb, zajosabb impulzus, gázelvételnél durrogás.
"""
import array
import math
import random

SR = 22050


def _kernel(sr, f1, f2, tau, noise, length=0.03, seed=1):
    r = random.Random(seed)
    n = int(sr * length)
    out = []
    lp = 0.0
    for i in range(n):
        t = i / sr
        env = (1 - math.exp(-t / 0.0007)) * math.exp(-t / tau)
        lp += 0.35 * (r.uniform(-1, 1) - lp)
        out.append(env * (math.sin(2 * math.pi * f1 * t) + 0.55 * math.sin(2 * math.pi * f2 * t + 0.7) + noise * lp))
    return out


class Engine:
    """egy motor hangja; rpm, gáz (0–1), hangerő menet közben állítható"""

    def __init__(self, sr, cyl=2, loud=1, cc=1000, seed=1):
        self.sr = sr
        self.rng = random.Random(seed)
        self.cyl = cyl
        self.loud = loud
        if cyl >= 8:
            self.offsets = [k / 8 for k in range(8)]
            self.amps = [1.0, 0.78, 1.12, 0.7, 1.0, 0.86, 1.2, 0.74]
            f1 = 52
        else:
            self.offsets = [0.0, 315 / 720]
            self.amps = [1.0, 0.86]
            f1 = max(55, 95 - cc / 50)                       # nagyobb köbcenti: mélyebb
        nz = 0.35 + 0.25 * (loud - 1)
        tau = 0.006 + 0.002 * (loud - 1)
        self.kernel = _kernel(sr, f1, f1 * 2.7, tau, nz, seed=seed)
        self.pop = _kernel(sr, f1 * 1.6, f1 * 4.1, 0.004, 1.6, length=0.025, seed=seed + 7)
        self.gain = 0.22 + 0.06 * (loud - 1)
        self.phase = 0.0
        self.rpm = 900.0
        self.thr = 0.0
        self.vol = 1.0
        self.target = (900.0, 0.0, 1.0)
        self.pulses = []                                     # [kernel, pozíció, erő]
        self.mech = 0.0

    def set(self, rpm, thr, vol):
        self.target = (max(300.0, float(rpm)), max(0.0, min(1.0, float(thr))), max(0.0, float(vol)))

    def render(self, out, n):
        rpm0, thr0, vol0 = self.rpm, self.thr, self.vol
        rpm1, thr1, vol1 = self.target
        inc0 = rpm0 / 120.0 / self.sr                        # 4 ütem: 2 fordulat egy ciklus
        inc1 = rpm1 / 120.0 / self.sr
        inc = (inc0 + inc1) / 2
        p0 = self.phase
        p1 = p0 + inc * n
        r = self.rng
        # gyújtások ebben a darabban
        for k, off in enumerate(self.offsets):
            c = math.floor(p0 - off) + 1
            while c + off < p1:
                idx = int((c + off - p0) / inc)
                if 0 <= idx < n:
                    thr = thr0 + (thr1 - thr0) * idx / n
                    a = (0.3 + 0.7 * thr) * self.amps[k] * (0.9 + 0.2 * r.random())
                    if thr < 0.1 and rpm1 > 2500 and self.loud >= 2 and r.random() < 0.05 * self.loud:
                        self.pulses.append([self.pop, -idx, 1.4])           # durrogás gázelvételnél
                    else:
                        self.pulses.append([self.kernel, -idx, a])
                c += 1
        self.phase = p1 % 1000.0
        g = self.gain
        keep = []
        for pl in self.pulses:
            ker, pos, a = pl
            a *= g
            if pos < 0:
                o0, k0 = -pos, 0
            else:
                o0, k0 = 0, pos
            m = min(n - o0, len(ker) - k0)
            if m > 0:
                seg = out[o0:o0 + m]
                out[o0:o0 + m] = [x + a * kk for x, kk in zip(seg, ker[k0:k0 + m])]
            pl[1] = pos + n
            if pl[1] < len(ker):
                keep.append(pl)
        self.pulses = keep
        # mechanikus zaj, szívás: halk, a fordulattal nő
        lvl = (0.004 + 0.02 * min(1.0, rpm1 / 7000.0) * (0.4 + 0.6 * thr1)) * self.gain * 4
        mech = self.mech
        for i in range(n):
            mech += 0.25 * (r.uniform(-1, 1) - mech)
            out[i] += lvl * mech
        self.mech = mech
        # hangerő: a darab végén érvényes (a durva ugrás elkerülésére a következő darab már ezzel indul)
        if vol1 != 1.0 or vol0 != 1.0:
            for i in range(n):
                out[i] *= vol0 + (vol1 - vol0) * i / n
        self.rpm, self.thr, self.vol = rpm1, thr1, vol1


class Squeal:
    """kipörgő gumi: rezonátoron átszűrt zaj"""

    def __init__(self, sr):
        self.sr = sr
        self.level = 0.0
        self.target = 0.0
        self.y1 = self.y2 = 0.0
        self.t = 0
        self.rng = random.Random(3)

    def render(self, out, n):
        if self.level < 0.001 and self.target < 0.001:
            self.level = 0.0
            return
        r = self.rng
        y1, y2 = self.y1, self.y2
        for i in range(n):
            self.level += (self.target - self.level) * 0.002
            f = 1650 + 120 * math.sin(self.t / self.sr * 2 * math.pi * 7)
            w = 2 * math.pi * f / self.sr
            rr = 0.985
            y = r.uniform(-1, 1) * 0.08 + 2 * rr * math.cos(w) * y1 - rr * rr * y2
            y2, y1 = y1, y
            out[i] += y * self.level * 0.18
            self.t += 1
        self.y1, self.y2 = y1, y2


def _tone(sr, parts, length):
    """egyszerű hangjel: [(frekvencia, kezdet s, hossz s, erő)]"""
    n = int(sr * length)
    out = [0.0] * n
    for f, st, ln, a in parts:
        i0, i1 = int(st * sr), min(n, int((st + ln) * sr))
        for i in range(i0, i1):
            t = (i - i0) / sr
            env = min(1.0, t / 0.005) * min(1.0, (ln - t) / 0.03)
            out[i] += a * env * (math.sin(2 * math.pi * f * t) + 0.25 * math.sin(4 * math.pi * f * t))
    return out


def _clunk(sr):
    r = random.Random(5)
    n = int(sr * 0.09)
    return [math.exp(-i / sr / 0.018) * (0.7 * math.sin(2 * math.pi * 48 * i / sr) + 0.25 * r.uniform(-1, 1)) * 0.6
            for i in range(n)]


class Mixer:
    """minden hang összekeverve; render(n) → int16 minták (array)"""

    def __init__(self, sr=SR):
        self.sr = sr
        self.engines = {}
        self.squeal = Squeal(sr)
        self.shots = []                     # [minták, pozíció]
        self.master = 1.25
        self.fx = {
            "beep": _tone(sr, [(620, 0, 0.16, 0.35)], 0.2),
            "go": _tone(sr, [(1240, 0, 0.35, 0.35)], 0.4),
            "shift": _clunk(sr),
            "click": _tone(sr, [(1800, 0, 0.025, 0.2)], 0.04),
            "cash": _tone(sr, [(1320, 0, 0.08, 0.25), (1760, 0.07, 0.25, 0.3)], 0.35),
            "err": _tone(sr, [(180, 0, 0.12, 0.3), (150, 0.13, 0.18, 0.3)], 0.33),
            "win": _tone(sr, [(523, 0, 0.14, 0.3), (659, 0.13, 0.14, 0.3), (784, 0.26, 0.14, 0.3), (1047, 0.39, 0.4, 0.35)], 0.85),
            "lose": _tone(sr, [(392, 0, 0.2, 0.3), (330, 0.2, 0.2, 0.3), (262, 0.4, 0.5, 0.3)], 0.95),
        }

    def busy(self):
        return bool(self.engines or self.shots or self.squeal.level > 0.001 or self.squeal.target > 0)

    def engine(self, key, rpm, thr, cyl, loud, cc, vol):
        e = self.engines.get(key)
        if not e or e.cyl != cyl or e.loud != loud:
            e = self.engines[key] = Engine(self.sr, cyl, loud, cc, seed=hash(key) & 0xffff)
            e.rpm = float(rpm)
        e.set(rpm, thr, vol)

    def engine_off(self, key):
        self.engines.pop(key, None)

    def stop(self):
        self.engines.clear()
        self.squeal.target = 0.0

    def play(self, name):
        if name in self.fx:
            self.shots.append([self.fx[name], 0])

    def render(self, n):
        out = [0.0] * n
        for e in list(self.engines.values()):
            e.render(out, n)
        self.squeal.render(out, n)
        keep = []
        for s in self.shots:
            buf, pos = s
            m = min(n, len(buf) - pos)
            out[:m] = [x + y for x, y in zip(out[:m], buf[pos:pos + m])]
            s[1] = pos + m
            if s[1] < len(buf):
                keep.append(s)
        self.shots = keep
        g = self.master * 32767
        return array.array("h", [int(g * (x / (1 + abs(x)))) for x in out])      # lágy vágás


# --- Qt: QAudioSink-re írás, QML-ből hívható ---------------------------------------------------------------------
try:
    from PyQt6.QtCore import QObject, QTimer, pyqtProperty, pyqtSignal, pyqtSlot
except ImportError:                                   # a modell-teszt Qt nélkül is fut
    QObject = object


if QObject is not object:
    class Sound(QObject):
        changed = pyqtSignal()

        def __init__(self, enabled=True, parent=None):
            super().__init__(parent)
            self._enabled = enabled
            self.sink = self.io = None
            self.mix = Mixer(SR)
            self.ch = 1
            self.error = ""
            self.info = {}
            self.written = 0
            self._open()
            self.timer = QTimer(self)
            self.timer.setInterval(12)
            self.timer.timeout.connect(self._feed)
            if self.sink:
                self.timer.start()

        def _open(self):
            """a hangkimenet megnyitása. 0.0.49: több formátum próbája (a gép kimenete nem minden formátumot fogad),
            a megnyitás hibája kiderül (sink.error), és a folyam végig fut (nincs felfüggesztés / folytatás:
            csendben csak nullák mennek) — a ZBookon a játék néma volt"""
            try:
                from PyQt6.QtMultimedia import QAudio, QAudioFormat, QAudioSink, QMediaDevices
            except Exception as e:                    # hang nélkül is menjen a játék
                self.error = f"QtMultimedia: {e}"
                return
            dev = QMediaDevices.defaultAudioOutput()
            self.info["device"] = dev.description() if not dev.isNull() else ""
            self.info["outputs"] = [d.description() for d in QMediaDevices.audioOutputs()]
            if dev.isNull():
                self.error = "nincs hangkimenet (QMediaDevices: üres alapértelmezett eszköz)"
                return
            tries = [(1, SR), (2, 48000), (2, 44100), (1, 48000), (1, 44100)]
            pf = dev.preferredFormat()
            if pf.sampleRate() > 0 and pf.channelCount() in (1, 2):
                tries.append((pf.channelCount(), pf.sampleRate()))
            errs = []
            for ch, sr in tries:
                fmt = QAudioFormat()
                fmt.setChannelCount(ch)
                fmt.setSampleFormat(QAudioFormat.SampleFormat.Int16)
                fmt.setSampleRate(sr)
                if not dev.isFormatSupported(fmt):
                    errs.append(f"{ch}ch/{sr}: nem támogatott")
                    continue
                sink = QAudioSink(dev, fmt, self)
                sink.setBufferSize(int(sr * 0.2) * 2 * ch)
                io = sink.start()
                if sink.error() != QAudio.Error.NoError or io is None:
                    errs.append(f"{ch}ch/{sr}: {sink.error().name}")
                    sink.stop()
                    continue
                self.sink, self.io, self.ch = sink, io, ch
                self.mix = Mixer(sr)
                self.info.update(format=f"{ch} csatorna, {sr} Hz, 16 bit", tried=errs)
                return
            self.error = "a hangkimenet nem nyitható meg: " + "; ".join(errs)
            self.info["tried"] = errs

        def _wake(self):
            pass

        def _feed(self):
            if not self.sink:
                return
            sr = self.mix.sr
            frame = 2 * self.ch
            free = self.sink.bytesFree()
            queued = self.sink.bufferSize() - free
            want = (int(sr * 0.07) * frame - queued) // frame              # ~70 ms előre (képkocka)
            if want <= 0:
                return
            want = min(want, free // frame)
            if want <= 0:
                return
            if self.mix.busy():
                data = self.mix.render(want)
                if self.ch == 2:
                    st = array.array("h", bytes(4 * len(data)))
                    st[0::2] = data
                    st[1::2] = data
                    data = st
                raw = data.tobytes()
            else:
                raw = bytes(want * frame)                                  # csend: a folyam fut tovább
            if self.io:
                self.written += self.io.write(raw) or 0

        @pyqtProperty(bool, notify=changed)
        def enabled(self):
            return self._enabled

        @enabled.setter
        def enabled(self, v):
            self._enabled = bool(v)
            if not v:
                self.mix.stop()
                self.mix.shots.clear()
            self.changed.emit()

        @pyqtProperty(bool, constant=True)
        def available(self):
            return self.sink is not None

        @pyqtSlot(str, float, float, int, int, int, float)
        def engine(self, key, rpm, thr, cyl, loud, cc, vol):
            if self._enabled and self.sink:
                self.mix.engine(key, rpm, thr, cyl, loud, cc, vol)
                self._wake()

        @pyqtSlot(str)
        def engineOff(self, key):
            self.mix.engine_off(key)

        @pyqtSlot(float)
        def squeal(self, level):
            if self._enabled and self.sink:
                self.mix.squeal.target = max(0.0, min(1.0, level))
                if level > 0:
                    self._wake()

        @pyqtSlot(str)
        def play(self, name):
            if self._enabled and self.sink:
                self.mix.play(name)
                self._wake()

        @pyqtSlot()
        def stop(self):
            self.mix.stop()


def selftest():
    """1 s motorhang (V2 és V8) ablak és hangeszköz nélkül: nem néma, nem vág, és elég gyors-e"""
    import time
    m = Mixer(SR)
    m.engine("a", 4500, 1.0, 2, 3, 1340, 1.0)
    m.engine("b", 3000, 0.6, 8, 2, 6200, 0.5)
    m.squeal.target = 1.0
    m.play("go")
    t = time.time()
    data = array.array("h")
    for _ in range(50):
        data.extend(m.render(SR // 50))
    cpu = time.time() - t
    rms = math.sqrt(sum(x * x for x in data) / len(data)) / 32767
    peak = max(abs(x) for x in data) / 32767
    return rms, peak, cpu
