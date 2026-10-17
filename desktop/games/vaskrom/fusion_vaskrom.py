#!/usr/bin/python3
"""Vas & Króm — motoros garázs- és gyorsulási verseny-játék (a régi Street Rod mechanikája, motorokkal)

    fusion-vaskrom              a játék (a mentés: ~/.local/share/vaskrom/mentes.json)
    fusion-vaskrom --selftest   önteszt: modell, rajz, felület (ablak nélkül)
"""
import os
import sys

HERE = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), "lib"))
import model as M  # noqa: E402
import art  # noqa: E402
import sound as snd  # noqa: E402
import json  # noqa: E402
from PyQt6.QtCore import QObject, QUrl, pyqtProperty, pyqtSignal, pyqtSlot  # noqa: E402

try:
    import fusion_ui as ui
except ImportError:                       # a FusionOS-en kívül (fejlesztés)
    ui = None


def part_desc(pid):
    p = M.PARTS[pid]
    s = p["slot"]
    if s == "engine":
        return f"{p['nm']} Nm @ {p['peak']}/perc, leszabályozás {p['red']}/perc"
    if s == "trans":
        return f"{len(p['ratios'])} fokozat, 1.: {p['ratios'][0]}, utolsó: {p['ratios'][-1]}"
    if s == "tire":
        return f"tapadás ×{p['grip']:.2f}"
    if s == "bars":
        return "légellenállás " + ("kisebb" if p.get("cda", 0) < 0 else "nagyobb" if p.get("cda", 0) > 0 else "változatlan")
    out = []
    if p.get("tq", 1) != 1:
        out.append(f"nyomaték +{(p['tq'] - 1) * 100:.0f}%")
    if p.get("rpm"):
        out.append(f"csúcs +{p['rpm']}/perc")
    if p.get("red"):
        out.append(f"leszabályozás +{p['red']}")
    if p.get("low"):
        out.append("gyengébb alul")
    if p.get("loud", 1) >= 3:
        out.append("hangos")
    return ", ".join(out) or "gyári"


class Game(QObject):
    changed = pyqtSignal()
    toast = pyqtSignal(str, bool)

    def __init__(self):
        super().__init__()
        self.g = M.Game()
        if not self.g.load():
            self.g.save()
        self._state = {}
        self._art = {}
        self.sfx = None                           # Sound (felületi hangok)
        self.refresh()

    # --- állapot a felületnek
    def bike_art(self, b):
        key = repr((b["model"], b["color"], b.get("flames"), sorted((s, p["id"]) for s, p in b["parts"].items())))
        if key not in self._art:
            self._art[key] = art.render(b)
        return self._art[key]

    def bike_view(self, b):
        d = M.bike_summary(b)
        d["art"] = self.bike_art(b)
        d["est"] = M.simulate(b, reaction=0.0)[0]
        return d

    def refresh(self):
        g = self.g
        cur = g.cur()
        st = {"day": g.day, "money": g.money, "rep": g.rep, "beaten": len(g.beaten), "won": g.won,
              "kingAvailable": g.king_available(), "garageSlots": M.GARAGE_SLOTS, "current": g.current,
              "log": list(reversed(g.log[-12:])), "messages": g.messages,
              "bikes": [dict(self.bike_view(b), selling=g.selling.get(b["uid"], 0)) for b in g.bikes]}
        if cur:
            parts = []
            for s in M.SLOTS:
                p = cur["parts"][s]
                parts.append({"slot": s, "slotName": M.SLOT_NAMES[s], "id": p["id"], "name": M.PARTS[p["id"]]["name"],
                              "cond": p["cond"], "repair": g.repair_cost(cur, s), "desc": part_desc(p["id"])})
            st["cur"] = dict(self.bike_view(cur), parts=parts, repairAll=g.repair_cost(cur))
        else:
            st["cur"] = None
        st["stock"] = [{"idx": i, "id": it["id"], "name": M.PARTS[it["id"]]["name"],
                        "slotName": M.SLOT_NAMES[M.PARTS[it["id"]]["slot"]], "cond": it["cond"],
                        "fits": bool(cur) and M.fits(it["id"], cur["model"]), "desc": part_desc(it["id"]),
                        "value": max(5, int(M.part_value(it["id"], it["cond"]) * 0.4))} for i, it in enumerate(g.stock)]
        st["catalog"] = [{"id": pid, "name": p["name"], "slot": p["slot"], "slotName": M.SLOT_NAMES[p["slot"]],
                          "price": p["price"], "desc": part_desc(pid),
                          "fits": bool(cur) and M.fits(pid, cur["model"])}
                         for pid, p in M.PARTS.items() if p["price"] > 0 and pid not in M.STOCK.values()]
        st["ads"] = [{"id": a["id"], "price": a["price"], "seller": a["seller"], "text": a["text"],
                      "bike": self.bike_view(a["bike"])} for a in g.ads]
        st["junk"] = [{"key": j["key"], "name": M.PARTS[j["id"]]["name"], "slotName": M.SLOT_NAMES[M.PARTS[j["id"]]["slot"]],
                       "cond": j["cond"], "price": j["price"], "desc": part_desc(j["id"]),
                       "fits": bool(cur) and M.fits(j["id"], cur["model"])} for j in g.junk]
        st["bar"] = [{"name": x["name"], "tier": x["tier"], "cash": x["cash"], "wins": x["wins"], "losses": x["losses"],
                      "beaten": x["name"] in g.beaten, "king": x["name"] == M.KING, "bike": self.bike_view(x["bike"])}
                     for x in g.bar]
        st["ladder"] = [{"name": x["name"], "beaten": x["name"] in g.beaten, "tier": x["tier"]} for x in g.rivals]
        st["colors"] = [{"hex": h, "name": n} for h, n in M.COLORS]
        st["paintPrice"], st["flamesPrice"] = M.PAINT_PRICE, M.FLAMES_PRICE
        self._state = st
        self.changed.emit()

    @pyqtProperty("QVariant", notify=changed)
    def state(self):
        return self._state

    def _done(self, res, fx="click"):
        ok, msg = res
        self.g.save()
        self.refresh()
        if self.sfx:
            self.sfx.play(fx if ok else "err")
        if msg:
            self.toast.emit(msg, not ok)
        return ok

    # --- műveletek
    @pyqtSlot(str, result=bool)
    def buyAd(self, ad_id):
        return self._done(self.g.buy_ad(ad_id), "cash")

    @pyqtSlot(str, int, result=bool)
    def listForSale(self, uid, price):
        return self._done(self.g.list_for_sale(uid, price))

    @pyqtSlot(str, result=bool)
    def cancelSale(self, uid):
        return self._done(self.g.cancel_sale(uid))

    @pyqtSlot(str, int, result=bool)
    def acceptOffer(self, uid, price):
        return self._done(self.g.accept_offer(uid, price), "cash")

    @pyqtSlot(int)
    def dismissMessage(self, i):
        if 0 <= i < len(self.g.messages):
            self.g.messages.pop(i)
            self.g.save()
            self.refresh()

    @pyqtSlot(str, result=bool)
    def buyPart(self, pid):
        return self._done(self.g.buy_part(pid), "cash")

    @pyqtSlot(str, result=bool)
    def buyJunk(self, key):
        return self._done(self.g.buy_junk(key), "cash")

    @pyqtSlot(int, result=bool)
    def sellPart(self, idx):
        return self._done(self.g.sell_part(idx), "cash")

    @pyqtSlot(int, result=bool)
    def install(self, idx):
        return self._done(self.g.install(idx), "shift")

    @pyqtSlot(str, result=bool)
    def repair(self, slot):
        return self._done(self.g.repair(slot or None), "shift")

    @pyqtSlot(str, bool, result=bool)
    def paint(self, color, flames):
        return self._done(self.g.paint(color, flames))

    @pyqtSlot(str)
    def select(self, uid):
        if self.g.bike(uid):
            self.g.current = uid
            self.g.save()
            self.refresh()

    @pyqtSlot()
    def endDay(self):
        self.g.end_day()
        self.g.save()
        self.refresh()
        self.toast.emit(f"{self.g.day}. nap — új hirdetések, új a kínálat a bontóban", False)

    @pyqtSlot()
    def work(self):
        pay, _ = self.g.work()
        if self.sfx:
            self.sfx.play("cash")
        self.g.save()
        self.refresh()
        self.toast.emit(f"Egy napot dolgoztál a műhelyben: +${pay}. {self.g.day}. nap", False)

    @pyqtSlot()
    def newGame(self):
        self.g = M.Game()
        self._art.clear()
        self.g.save()
        self.refresh()
        self.toast.emit(f"Új játék: ${M.START_MONEY}, üres garázs. Nézd meg a Moto Apró hirdetéseit!", False)

    # --- verseny
    @pyqtSlot(str, int, bool, result="QVariant")
    def challenge(self, name, bet, pink):
        ok, msg = self.g.rival_accepts(name, bet, pink)
        if not ok:
            self.toast.emit(msg, True)
            return {"ok": False, "msg": msg}
        cur = self.g.cur()
        x = self.g.rival(name)
        return {"ok": True, "msg": msg, "name": name, "bet": bet, "pink": pink,
                "me": dict(M.race_params(cur), art=self.bike_art(cur)),
                "opp": dict(self.g.opponent_params(name), art=self.bike_art(x["bike"]))}

    @pyqtSlot(result="QVariant")
    def practice(self):
        cur = self.g.cur()
        if not cur:
            return {"ok": False, "msg": "nincs motorod"}
        return {"ok": True, "name": "", "bet": 0, "pink": False, "me": dict(M.race_params(cur), art=self.bike_art(cur)),
                "opp": None}

    @pyqtSlot(str, int, bool, bool, float, float, float, bool, result="QVariant")
    def raceDone(self, name, bet, pink, won, my_time, their_time, over_rev, foul):
        if not name:                                    # próbafutam
            cur = self.g.cur()
            if over_rev > 0 and cur:
                cur["parts"]["engine"]["cond"] = max(0, cur["parts"]["engine"]["cond"] - min(20, int(over_rev * 12)))
            self.g.save()
            self.refresh()
            return {"won": True, "practice": True}
        res = self.g.finish_race(name, bet, pink, won, my_time, their_time, over_rev, foul)
        self.g.save()
        self.refresh()
        return res


def settings_path():
    return os.path.join(M.SAVE_DIR, "beallitas.json")


def load_settings():
    try:
        with open(settings_path()) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def save_settings(d):
    try:
        os.makedirs(M.SAVE_DIR, exist_ok=True)
        with open(settings_path(), "w") as f:
            json.dump(d, f)
    except OSError:
        pass


def make_sound(engine, enabled=True):
    s = snd.Sound(enabled)
    s.changed.connect(lambda: save_settings(dict(load_settings(), sound=s.enabled)))
    engine.rootContext().setContextProperty("sound", s)
    return s


def selftest():
    import tempfile
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    M.SAVE_DIR = tempfile.mkdtemp()
    art.CACHE = tempfile.mkdtemp()
    ok = True

    def check(name, cond, extra=""):
        nonlocal ok
        ok = ok and bool(cond)
        print(f"VASKROM: {name} {'ok' if cond else 'HIBA'} {extra}".rstrip(), flush=True)
    g = M.Game(seed=1)
    ad = min(g.ads, key=lambda a: a["price"])
    g.money = 100000
    check("BUY", g.buy_ad(ad["id"])[0] and g.cur())
    t, v = M.simulate(g.cur(), reaction=0)
    check("SIM", 6 < t < 20 and v > 80, f"{t} s, {v} km/h")
    check("PART", g.buy_part("carb_45")[0] and g.install(len(g.stock) - 1)[0])
    ra = art.render(g.cur())
    check("ART", all(os.path.exists(ra[k][7:]) for k in ("body", "over", "rear", "front") if ra.get(k)),
          "rajzolt" if ra.get("sprite") else "svg")
    from PyQt6.QtGui import QGuiApplication
    from PyQt6.QtQml import QQmlApplicationEngine
    app = QGuiApplication(sys.argv)
    eng = QQmlApplicationEngine()
    if ui:
        eng.addImportPath(ui.QML_DIR)
    rms, peak, cpu = snd.selftest()
    # a CPU-idő csak tájékoztató: QEMU-ban (emulált CPU, párhuzamos önteszt) sokszorosa a valós gépen mértnek
    check("SOUND", rms > 0.02 and peak < 0.99, f"rms={rms:.3f} csúcs={peak:.2f} cpu={cpu * 1000:.0f} ms/s")
    warns = []
    eng.warnings.connect(lambda ws: warns.extend(w.toString() for w in ws))
    game = Game()
    game.g.money = 100000
    game.buyAd(min(game.g.ads, key=lambda a: a["price"])["id"])
    game.sfx = make_sound(eng, True)
    eng.rootContext().setContextProperty("game", game)
    eng.rootContext().setContextProperty("selftestMode", True)
    eng.load(QUrl.fromLocalFile(os.path.join(HERE, "qml", "Main.qml")))
    root = eng.rootObjects()[0] if eng.rootObjects() else None
    if root:                                   # minden oldal és egy próbafutam (a kirajzolás nélkül)
        from PyQt6.QtCore import QTimer, QEventLoop
        for pg in ("news", "catalog", "junk", "bar", "garage"):
            root.setProperty("page", pg)
            app.processEvents()
        root.setProperty("race", game.practice())
        loop = QEventLoop()
        QTimer.singleShot(1500, loop.quit)
        loop.exec()
        root.setProperty("race", None)
        app.processEvents()
    for w in warns:
        print("  QML:", w)
    check("QML", bool(root) and not warns, f"{len(warns)} figyelmeztetés")
    sys.stdout.flush()
    os._exit(0 if ok else 1)                   # a QML-motor lebontása nélkül (a context-objektumok sorrendje miatt)


def sound_probe():
    """fusion-vaskrom --hangproba: a hangkimenet ellenőrzése a valódi gépen (mit lát a játék, szól-e)"""
    import subprocess
    import time
    from PyQt6.QtCore import QEventLoop, QTimer
    from PyQt6.QtGui import QGuiApplication
    os.environ["QT_QPA_PLATFORM"] = "offscreen"      # ablak nem kell
    app = QGuiApplication(sys.argv)

    def sh(cmd):
        try:
            return subprocess.run(cmd, capture_output=True, text=True, timeout=5).stdout.strip()
        except (OSError, subprocess.TimeoutExpired) as e:
            return f"({e})"
    print("HANGPRÓBA — Vas & Króm")
    print("  beállítás (a játék menüjében):", "BE" if load_settings().get("sound", True) else "KI (Menü → Hang bekapcsolása)")
    print("  hangkiszolgáló:", sh(["pactl", "info"]).replace("\n", " | ")[:300])
    print("  alapértelmezett kimenet:", sh(["pactl", "get-default-sink"]))
    print("  hangerő / némítás:", sh(["pactl", "get-sink-volume", "@DEFAULT_SINK@"]).splitlines()[0:1], sh(["pactl", "get-sink-mute", "@DEFAULT_SINK@"]))
    s = snd.Sound(True)
    print("  Qt-eszköz:", s.info.get("device", "-"), "| minden kimenet:", ", ".join(s.info.get("outputs", [])) or "-")
    print("  formátum:", s.info.get("format", "-"), "| próbák:", "; ".join(s.info.get("tried", [])) or "-")
    print("  hiba:", s.error or "nincs")
    if not s.sink:
        return 1
    print("  most szól: 3 sípszó, majd 2 mp motorhang (V2) és egy dallam …", flush=True)
    loop = QEventLoop()
    seq = [(300, lambda: s.play("beep")), (900, lambda: s.play("beep")), (1500, lambda: s.play("go")),
           (2200, lambda: s.engine("p", 2500, 1, 2, 3, 1340, 1.0)), (3200, lambda: s.engine("p", 5000, 1, 2, 3, 1340, 1.0)),
           (4300, lambda: (s.engineOff("p"), s.play("win")))]
    for ms, fn in seq:
        QTimer.singleShot(ms, fn)
    QTimer.singleShot(3000, lambda: print("  a folyam a kiszolgálón:", (sh(["pactl", "list", "short", "sink-inputs"]) or "NINCS").replace("\n", " | "),
                                           "| állapot:", s.sink.state().name, "| hiba:", s.sink.error().name, "| kiírva:", s.written, "bájt", flush=True))
    QTimer.singleShot(5600, loop.quit)
    loop.exec()
    print("  kész. Hallottad? (igen / nem)")
    sys.stdout.flush()
    os._exit(0)


def main():
    if sys.argv[1:2] == ["--selftest"]:
        return selftest()
    if sys.argv[1:2] == ["--hangproba"]:
        return sound_probe()
    if ui:
        app, engine = ui.create_app("fusion-vaskrom", "Vas & Króm", "game")
    else:
        from PyQt6.QtGui import QGuiApplication
        from PyQt6.QtQml import QQmlApplicationEngine
        app = QGuiApplication(sys.argv)
        engine = QQmlApplicationEngine()
    game = Game()
    sobj = make_sound(engine, load_settings().get("sound", True))
    game.sfx = sobj
    engine.rootContext().setContextProperty("game", game)
    engine.rootContext().setContextProperty("selftestMode", False)
    engine.load(QUrl.fromLocalFile(os.path.join(HERE, "qml", "Main.qml")))
    if not engine.rootObjects():
        return 1
    app._keep = [game, sobj]
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
