"""Vas & Króm — a játék modellje: motorok, alkatrészek, hirdetések, bontó, ellenfelek, napok, mentés (Qt nélkül)

A régi „Street Rod” mechanikája motorokra: újsághirdetésből veszel motort, alkatrészt a katalógusból (új) vagy a
bontóból (használt), a garázsban szereled, a kocsmában kihívod a többieket pénzre vagy forgalmira, a végén a Király.
A versenyt (drag, 402 m) a felület számolja a `race_params()` adataiból; az eredményt a `finish_race()` könyveli.
"""
import json
import math
import os
import random
import time

SAVE_DIR = os.environ.get("VASKROM_SAVE_DIR", os.path.join(os.path.expanduser("~"), ".local", "share", "vaskrom"))
START_MONEY = 3000
PROJECT_PRICE = (0.55, 0.75)          # a „felújítandó” hirdetés ára az érték arányában (mindig van egy olcsó)
WORK_PAY = (120, 220)                  # alkalmi szerelőmunka egy napra
GARAGE_SLOTS = 3
RIDER_KG = 85
QUARTER = 402.3          # m

# --- motorok (vázak) ----------------------------------------------------------------------------------------------
# type: chopper | cruiser | bobber | cafe | v8 ; a márkák kitaláltak
MODELS = {
    "bobber883":  {"name": "Rozsdás Bobber 883", "type": "bobber", "make": "Kentaur", "mass": 235, "value": 2600,
                   "cda": 0.62, "wheelbase": 1.52, "cg": 0.62, "engine": "v2_883", "trans": "t4", "tire": "r130",
                   "bars": "drag", "wheel": "spoke"},
    "cafe1000":   {"name": "Kentaur Café 1000", "type": "cafe", "make": "Kentaur", "mass": 225, "value": 4200,
                   "cda": 0.55, "wheelbase": 1.45, "cg": 0.6, "engine": "v2_1000", "trans": "t5", "tire": "r150",
                   "bars": "clip", "wheel": "cast"},
    "cruiser1200": {"name": "Pannon Cruiser 1200", "type": "cruiser", "make": "Pannon", "mass": 290, "value": 4800,
                    "cda": 0.72, "wheelbase": 1.62, "cg": 0.6, "engine": "v2_1200", "trans": "t5", "tire": "r150",
                    "bars": "beach", "wheel": "cast"},
    "chopper1340": {"name": "Hosszúvillás Chopper 1340", "type": "chopper", "make": "Vasló", "mass": 270, "value": 5600,
                    "cda": 0.75, "wheelbase": 1.85, "cg": 0.66, "engine": "v2_1340", "trans": "t4", "tire": "r180",
                    "bars": "ape", "wheel": "spoke"},
    "cruiser1800": {"name": "Pannon Road Cruiser 1800", "type": "cruiser", "make": "Pannon", "mass": 330, "value": 9500,
                    "cda": 0.78, "wheelbase": 1.65, "cg": 0.6, "engine": "v2_1800", "trans": "t6", "tire": "r180",
                    "bars": "beach", "wheel": "cast"},
    "v8giant":    {"name": "V8-as óriás", "type": "v8", "make": "Vasló", "mass": 470, "value": 16500,
                   "cda": 0.85, "wheelbase": 1.88, "cg": 0.58, "engine": "v8_57", "trans": "t2", "tire": "r240",
                   "bars": "beach", "wheel": "cast"},
}
TYPE_NAMES = {"chopper": "chopper", "cruiser": "cruiser", "bobber": "bobber", "cafe": "café racer", "v8": "V8-as óriás"}

# --- alkatrészek ----------------------------------------------------------------------------------------------------
SLOTS = ["engine", "carb", "cam", "exhaust", "intake", "ignition", "blower", "trans", "tire", "bars"]
SLOT_NAMES = {"engine": "Motorblokk", "carb": "Karburátor", "cam": "Vezérműtengely", "exhaust": "Kipufogó",
              "intake": "Levegőszűrő", "ignition": "Gyújtás", "blower": "Feltöltő", "trans": "Váltó",
              "tire": "Hátsó gumi", "bars": "Kormány"}
# fits: mely vázakba (type) való; tq: nyomatékszorzó; rpm: a csúcsnyomaték fordulatának eltolása; red: leszabályozás
PARTS = {
    # motorblokkok (V2: nem V8-as vázba; V8: csak V8-as vázba)
    "v2_883":  {"slot": "engine", "name": "V2 883 cm³", "price": 900, "cc": 883, "cyl": 2, "nm": 70, "peak": 3800, "red": 6200, "kg": 0},
    "v2_1000": {"slot": "engine", "name": "V2 1000 cm³", "price": 1300, "cc": 1000, "cyl": 2, "nm": 84, "peak": 4800, "red": 7500, "kg": 0},
    "v2_1200": {"slot": "engine", "name": "V2 1200 cm³", "price": 1700, "cc": 1200, "cyl": 2, "nm": 100, "peak": 3600, "red": 6200, "kg": 5},
    "v2_1340": {"slot": "engine", "name": "V2 1340 cm³", "price": 2100, "cc": 1340, "cyl": 2, "nm": 108, "peak": 3800, "red": 6000, "kg": 8},
    "v2_1584": {"slot": "engine", "name": "V2 1584 cm³", "price": 2900, "cc": 1584, "cyl": 2, "nm": 128, "peak": 3300, "red": 5800, "kg": 12},
    "v2_1800": {"slot": "engine", "name": "V2 1800 cm³", "price": 3800, "cc": 1800, "cyl": 2, "nm": 150, "peak": 3400, "red": 5800, "kg": 15},
    "v2_2000": {"slot": "engine", "name": "V2 2000 cm³ verseny", "price": 6200, "cc": 2000, "cyl": 2, "nm": 182, "peak": 3800, "red": 6200, "kg": 18},
    "v8_57":   {"slot": "engine", "name": "V8 5,7 l", "price": 5800, "cc": 5700, "cyl": 8, "nm": 450, "peak": 3800, "red": 5600, "kg": 0},
    "v8_62":   {"slot": "engine", "name": "V8 6,2 l", "price": 8900, "cc": 6200, "cyl": 8, "nm": 540, "peak": 4200, "red": 6000, "kg": 10},
    # karburátor
    "carb_std":   {"slot": "carb", "name": "Gyári karburátor", "price": 120, "tq": 1.00, "rpm": 0, "red": 0},
    "carb_42":    {"slot": "carb", "name": "42 mm-es karburátor", "price": 380, "tq": 1.06, "rpm": 150, "red": 0},
    "carb_45":    {"slot": "carb", "name": "45 mm-es nagy torkú", "price": 620, "tq": 1.10, "rpm": 250, "red": 100},
    "carb_dual":  {"slot": "carb", "name": "Dupla karburátor", "price": 1150, "tq": 1.16, "rpm": 350, "red": 150},
    # vezérműtengely
    "cam_std":    {"slot": "cam", "name": "Gyári vezérmű", "price": 150, "tq": 1.00, "rpm": 0, "red": 0},
    "cam_street": {"slot": "cam", "name": "Utcai sport vezérmű", "price": 450, "tq": 1.05, "rpm": 250, "red": 200},
    "cam_race":   {"slot": "cam", "name": "Verseny vezérmű", "price": 980, "tq": 1.11, "rpm": 650, "red": 500, "low": 0.85},
    # kipufogó
    "ex_std":     {"slot": "exhaust", "name": "Gyári kipufogó", "price": 150, "tq": 1.00, "loud": 1, "style": "std"},
    "ex_slash":   {"slot": "exhaust", "name": "Ferde végű dobok", "price": 320, "tq": 1.03, "loud": 2, "style": "slash"},
    "ex_21":      {"slot": "exhaust", "name": "2-1 sportkipufogó", "price": 640, "tq": 1.06, "loud": 2, "style": "21"},
    "ex_drag":    {"slot": "exhaust", "name": "Egyenes csövek (drag)", "price": 520, "tq": 1.07, "loud": 3, "style": "drag"},
    # levegőszűrő
    "in_std":     {"slot": "intake", "name": "Gyári levegőszűrő", "price": 60, "tq": 1.00},
    "in_open":    {"slot": "intake", "name": "Nyitott kúpszűrő", "price": 160, "tq": 1.03},
    "in_big":     {"slot": "intake", "name": "Nagy beömlő", "price": 340, "tq": 1.05},
    # gyújtás
    "ig_std":     {"slot": "ignition", "name": "Gyári gyújtás", "price": 90, "tq": 1.00, "red": 0},
    "ig_sport":   {"slot": "ignition", "name": "Sport gyújtás", "price": 290, "tq": 1.02, "red": 300},
    "ig_race":    {"slot": "ignition", "name": "Verseny gyújtás", "price": 620, "tq": 1.03, "red": 600},
    # feltöltő
    "bl_none":    {"slot": "blower", "name": "Nincs feltöltő", "price": 0, "tq": 1.00, "kg": 0},
    "bl_turbo":   {"slot": "blower", "name": "Turbó", "price": 3200, "tq": 1.22, "kg": 9, "low": 0.80},
    "bl_comp":    {"slot": "blower", "name": "Kompresszor (feltöltő)", "price": 4200, "tq": 1.25, "kg": 14},
    # váltó (teljes áttételek: primer × váltó × szekunder)
    "t2":  {"slot": "trans", "name": "2 fokozatú automata", "price": 900, "ratios": [4.4, 2.8]},
    "t3":  {"slot": "trans", "name": "3 fokozatú verseny", "price": 2400, "ratios": [5.0, 3.5, 2.6]},
    "t4":  {"slot": "trans", "name": "4 fokozatú", "price": 500, "ratios": [10.4, 7.0, 5.0, 3.9]},
    "t5":  {"slot": "trans", "name": "5 fokozatú", "price": 900, "ratios": [9.3, 6.4, 4.7, 3.8, 3.15]},
    "t6":  {"slot": "trans", "name": "6 fokozatú", "price": 1400, "ratios": [9.3, 6.6, 5.0, 4.0, 3.4, 2.85]},
    "t5c": {"slot": "trans", "name": "5 fokozatú sűrű áttételű", "price": 1900, "ratios": [8.2, 6.2, 4.9, 4.0, 3.4]},
    # hátsó gumi
    "r130": {"slot": "tire", "name": "130-as gumi", "price": 110, "grip": 0.95, "w": 130},
    "r150": {"slot": "tire", "name": "150-es gumi", "price": 150, "grip": 1.02, "w": 150},
    "r180": {"slot": "tire", "name": "180-as gumi", "price": 210, "grip": 1.10, "w": 180},
    "r240": {"slot": "tire", "name": "240-es széles gumi", "price": 420, "grip": 1.22, "w": 240},
    "r300": {"slot": "tire", "name": "300-as óriásgumi", "price": 690, "grip": 1.32, "w": 300},
    "rslick": {"slot": "tire", "name": "Drag slick", "price": 950, "grip": 1.48, "w": 260},
    # kormány (látvány + légellenállás)
    "drag":  {"slot": "bars", "name": "Drag kormány", "price": 120, "cda": -0.03},
    "clip":  {"slot": "bars", "name": "Csonkkormány", "price": 160, "cda": -0.05},
    "beach": {"slot": "bars", "name": "Széles túrakormány", "price": 110, "cda": 0.0},
    "ape":   {"slot": "bars", "name": "Majomkormány", "price": 180, "cda": 0.04},
}
STOCK = {"carb": "carb_std", "cam": "cam_std", "exhaust": "ex_std", "intake": "in_std", "ignition": "ig_std",
         "blower": "bl_none"}
COLORS = [("#b01818", "piros"), ("#1d3fa8", "kék"), ("#111111", "fekete"), ("#d8d8d8", "ezüst"), ("#d48a12", "narancs"),
          ("#1f6b2a", "zöld"), ("#5a1d6e", "lila"), ("#c9b037", "arany"), ("#e8e8e8", "fehér"), ("#6b4423", "rozsdabarna")]
PAINT_PRICE = 450
FLAMES_PRICE = 300

FIRST = ["Pista", "Karcsi", "Józsi", "Laci", "Feri", "Gyuri", "Tibi", "Zoli", "Bandi", "Sanyi", "Béla", "Imi", "Ottó"]
RIVALS = [
    ("Rozsda", "bobber883", 0), ("Csavar", "bobber883", 1), ("Füstös", "cafe1000", 1), ("Szikra", "cruiser1200", 1),
    ("Kalapács", "cruiser1200", 2), ("Vidra", "cafe1000", 2), ("Hosszúvillás", "chopper1340", 2),
    ("Bivaly", "chopper1340", 3), ("Zsírkirály", "cruiser1800", 3), ("Krómos Karcsi", "cruiser1800", 4),
    ("Vasmacska", "v8giant", 4), ("A Király", "v8giant", 6),
]
KING = "A Király"
TIERS = [  # ellenfél-fejlettség → alkatrészek
    {},
    {"carb": "carb_42", "intake": "in_open"},
    {"carb": "carb_42", "intake": "in_open", "exhaust": "ex_slash", "cam": "cam_street"},
    {"carb": "carb_45", "intake": "in_big", "exhaust": "ex_21", "cam": "cam_street", "ignition": "ig_sport"},
    {"carb": "carb_45", "intake": "in_big", "exhaust": "ex_drag", "cam": "cam_race", "ignition": "ig_sport", "tire": "r240"},
    {"carb": "carb_dual", "intake": "in_big", "exhaust": "ex_drag", "cam": "cam_race", "ignition": "ig_race",
     "tire": "r300", "trans": "t5c"},
    {"engine": "v8_62", "carb": "carb_dual", "intake": "in_big", "exhaust": "ex_drag", "cam": "cam_race",
     "ignition": "ig_race", "blower": "bl_turbo", "tire": "rslick", "trans": "t3"},
]


def fits(part_id, model_id):
    p, t = PARTS[part_id], MODELS[model_id]["type"]
    if p["slot"] == "engine":
        return (p["cyl"] == 8) == (t == "v8")
    if p["slot"] == "trans":
        return part_id in (("t2", "t3") if t == "v8" else ("t4", "t5", "t6", "t5c"))
    if p["slot"] == "tire" and t != "v8" and p["w"] > 240 and part_id != "rslick":
        return t == "chopper"
    return True


def new_bike(model_id, rng, cond=None, parts=None, color=None, flames=False):
    m = MODELS[model_id]
    c = cond if cond is not None else rng.randint(35, 95)
    ps = {}
    for s in SLOTS:
        pid = (parts or {}).get(s) or STOCK.get(s) or m.get(s)
        ps[s] = {"id": pid, "cond": max(10, min(100, c + rng.randint(-15, 10)))}
    col = color or rng.choice(COLORS)[0]
    return {"uid": f"b{int(time.time() * 1000) % 10**9}{rng.randint(100, 999)}", "model": model_id, "color": col,
            "flames": flames, "cond": c, "parts": ps}


# --- teljesítmény ---------------------------------------------------------------------------------------------------
def spec(b):
    """a motor számított adatai: nyomaték, teljesítmény, tömeg, tapadás, áttételek"""
    m = MODELS[b["model"]]
    p = {s: PARTS[b["parts"][s]["id"]] for s in SLOTS if b["parts"].get(s)}
    e = p["engine"]
    tq, rpm_shift, red_add, low = 1.0, 0, 0, 1.0
    for s in ("carb", "cam", "exhaust", "intake", "ignition", "blower"):
        x = p.get(s, {})
        tq *= x.get("tq", 1.0)
        rpm_shift += x.get("rpm", 0)
        red_add += x.get("red", 0)
        low = min(low, x.get("low", 1.0))
    econd = b["parts"]["engine"]["cond"]
    wear = 0.7 + 0.3 * min(1.0, econd / 70.0)            # elhasznált motor: kevesebb erő
    nm = e["nm"] * tq * wear
    peak = e["peak"] + rpm_shift
    red = e["red"] + red_add
    mass = m["mass"] + e.get("kg", 0) + p.get("blower", {}).get("kg", 0)
    tire = p["tire"]
    grip = tire["grip"] * (0.8 + 0.2 * b["parts"]["tire"]["cond"] / 100.0)
    curve = torque_curve(nm, peak, red, low)
    hp = max(t * r for r, t in curve) / 7023.5        # LE (Nm × 1/perc)
    return {"nm": round(nm), "peak": peak, "red": red, "mass": mass, "hp": round(hp), "grip": round(grip, 3),
            "ratios": p["trans"]["ratios"], "cda": max(0.4, m["cda"] + p["bars"].get("cda", 0)),
            "wheelbase": m["wheelbase"], "cg": m["cg"], "curve": curve, "cc": e["cc"], "cyl": e["cyl"],
            "loud": p["exhaust"].get("loud", 1)}


def torque_curve(nm, peak, red, low=1.0, idle=900, step=250):
    """(fordulat, Nm) pontok: emelkedés a csúcsig, utána lassú esés; low < 1: gyenge alsó tartomány (versenyvezérmű)"""
    pts = []
    r = idle
    while r <= red + step:
        x = r / peak
        if x <= 1:
            f = 0.55 + 0.45 * math.sin(x * math.pi / 2) ** 1.4
            f *= low + (1 - low) * x ** 2
        else:
            f = 1 - 0.55 * (x - 1) ** 1.6
        pts.append((r, round(max(0.15, f) * nm, 1)))
        r += step
    return pts


def race_params(b):
    s = spec(b)
    return {"curve": [[r, t] for r, t in s["curve"]], "red": s["red"], "idle": 900, "ratios": s["ratios"],
            "mass": s["mass"] + RIDER_KG, "grip": s["grip"], "cda": s["cda"], "wheelbase": s["wheelbase"],
            "cg": s["cg"], "radius": 0.33, "eff": 0.88, "hp": s["hp"], "nm": s["nm"], "cyl": s["cyl"],
            "loud": s["loud"], "cc": s["cc"]}


def simulate(b, rng=None, reaction=0.25, launch_frac=0.55, shift_frac=None, dt=1 / 120):
    """a felület versenymodelljének Python-párja: becsült 402 m-es idő (az ellenfelek döntéseihez és a teszthez)"""
    p = race_params(b)
    curve = p["curve"]

    def T(rpm):
        if rpm <= curve[0][0]:
            return curve[0][1]
        for i in range(1, len(curve)):
            if rpm <= curve[i][0]:
                r0, t0 = curve[i - 1]
                r1, t1 = curve[i]
                return t0 + (t1 - t0) * (rpm - r0) / (r1 - r0)
        return curve[-1][1]
    shift_rpm = (shift_frac or 0.97) * p["red"]
    m, g = p["mass"], 9.81
    x = v = t = 0.0
    gear = 0
    rpm = launch_frac * p["red"]
    slip_t = 0.0
    while x < QUARTER and t < 40:
        ratio = p["ratios"][gear]
        wheel_rpm = v / (2 * math.pi * p["radius"]) * 60 * ratio
        if slip_t >= 0 and wheel_rpm < rpm and slip_t < 2.5:     # kuplungcsúszás, amíg a kerék utol nem éri a motort
            rpm = max(rpm - 1500 * dt, 2000)
            slip_t += dt
        elif slip_t >= 0:
            slip_t = -1
            rpm = max(wheel_rpm, p["idle"])
        else:
            rpm = max(wheel_rpm, p["idle"])
        torque = T(rpm) if rpm < p["red"] else 0.0
        f = torque * ratio * p["eff"] / p["radius"]
        rear = m * g * (1 - p["cg"] * 0.55) + f * 0.25    # súlyáthelyeződés
        fmax = p["grip"] * rear
        f = min(f, fmax)
        wheelie = m * g * p["wheelbase"] * 0.62 / 0.6
        f = min(f, wheelie)
        drag = 0.5 * 1.2 * p["cda"] * v * v + 0.015 * m * g
        v = max(0.0, v + (f - drag) / m * dt)
        x += v * dt
        t += dt
        if rpm >= shift_rpm and gear < len(p["ratios"]) - 1:
            gear += 1
            t += 0.12                          # váltási idő
    return round(t + reaction, 3), round(v * 3.6)


# --- érték ----------------------------------------------------------------------------------------------------------
def part_value(pid, cond):
    return PARTS[pid]["price"] * (0.25 + 0.75 * cond / 100.0)


def bike_value(b):
    m = MODELS[b["model"]]
    v = m["value"] * (0.45 + 0.55 * b["cond"] / 100.0) * 0.6
    for s, p in b["parts"].items():
        v += part_value(p["id"], p["cond"]) * 0.55
    if b.get("flames"):
        v += 150
    return int(round(v / 10) * 10)


def bike_summary(b):
    s = spec(b)
    p = b["parts"]
    mods = [PARTS[p[sl]["id"]]["name"] for sl in ("carb", "cam", "exhaust", "intake", "ignition", "blower")
            if p[sl]["id"] != STOCK[sl]]
    return {"uid": b["uid"], "model": b["model"], "name": MODELS[b["model"]]["name"], "type": MODELS[b["model"]]["type"],
            "typeName": TYPE_NAMES[MODELS[b["model"]]["type"]], "cc": s["cc"], "hp": s["hp"], "nm": s["nm"],
            "mass": s["mass"], "gears": len(s["ratios"]), "tire": PARTS[p["tire"]["id"]]["w"], "mods": mods,
            "cond": b["cond"], "engineCond": p["engine"]["cond"], "value": bike_value(b), "color": b["color"],
            "flames": b.get("flames", False), "red": s["red"],
            "cyl": s["cyl"], "loud": s["loud"], "peak": s["peak"]}


# --- a játék állása -------------------------------------------------------------------------------------------------
class Game:
    def __init__(self, seed=None):
        self.rng = random.Random(seed)
        self.reset()

    def reset(self):
        r = self.rng
        self.day = 1
        self.money = START_MONEY
        self.bikes = []                       # a garázs (legfeljebb GARAGE_SLOTS)
        self.current = ""                     # a kiválasztott motor uid-je
        self.stock = []                       # raktár: [{"id", "cond"}]
        self.rep = 0
        self.beaten = []
        self.won = False
        self.log = []
        self.messages = []
        self.selling = {}                     # uid → kért ár
        self.rivals = []
        for name, model, tier in RIVALS:
            b = new_bike(model, r, cond=r.randint(60, 90), parts=TIERS[tier], flames=tier >= 3 and r.random() < 0.6)
            self.rivals.append({"name": name, "tier": tier, "cash": 800 + tier * 900 + r.randint(0, 600), "bike": b,
                                "wins": 0, "losses": 0})
        self.new_day_market()

    # -- napi kínálat
    def new_day_market(self):
        r = self.rng
        self.ads = []
        pool = ["bobber883"] * 4 + ["cafe1000"] * 3 + ["cruiser1200"] * 3 + ["chopper1340"] * 2 + ["cruiser1800"] * 2 + ["v8giant"]
        for _ in range(r.randint(4, 6)):
            mid = r.choice(pool)
            tier = r.choice([0, 0, 0, 1, 1, 2])
            b = new_bike(mid, r, parts=TIERS[tier] if tier else None, flames=r.random() < 0.2)
            price = int(bike_value(b) * r.uniform(0.75, 1.15) / 10) * 10
            seller = r.choice(FIRST)
            self.ads.append({"id": f"ad{r.randint(10**5, 10**6)}", "bike": b, "price": price, "seller": seller,
                             "text": ad_text(b, r)})
        # mindig van legalább egy olcsó, felújítandó motor — a kezdőpénzből utána is marad szerelésre, tétre
        mid = r.choice(["bobber883", "bobber883", "cafe1000"])
        b = new_bike(mid, r, cond=r.randint(18, 35))
        price = int(bike_value(b) * r.uniform(*PROJECT_PRICE) / 10) * 10
        self.ads.insert(0, {"id": f"ad{r.randint(10**5, 10**6)}", "bike": b, "price": price, "seller": r.choice(FIRST),
                            "text": f"FELÚJÍTANDÓ: {MODELS[mid]['name']}, {PARTS[b['parts']['engine']['id']]['cc']} cm³, "
                                    f"régóta áll, olcsón vihető. Indul, de hangos."})
        self.junk = []
        ids = [k for k, p in PARTS.items() if p["price"] > 0 and not k.startswith(("carb_std", "cam_std", "ex_std",
                                                                                    "in_std", "ig_std"))]
        for _ in range(r.randint(6, 9)):
            pid = r.choice(ids)
            cond = r.randint(15, 75)
            self.junk.append({"id": pid, "cond": cond, "price": max(20, int(part_value(pid, cond) * 0.45 / 5) * 5),
                              "key": f"j{r.randint(10**5, 10**6)}"})
        self.bar = r.sample([x for x in self.rivals if x["name"] != KING or self.king_available()],
                            k=min(5, len(self.rivals)))

    def work(self):
        """alkalmi szerelőmunka: egy nap telik el, kis biztos pénz (ha elfogyott, ne akadjon el a játék)"""
        pay = int(self.rng.randint(*WORK_PAY) + min(200, self.rep * 5))
        self.money += pay
        self.note(f"szerelőmunka: ${pay}")
        msgs = self.end_day()
        return pay, msgs

    def king_available(self):
        return len(self.beaten) >= 8

    def end_day(self):
        r = self.rng
        self.day += 1
        msgs = []
        # eladásra kínált motorok: vevő jelentkezik
        for uid, price in list(self.selling.items()):
            b = self.bike(uid)
            if not b:
                self.selling.pop(uid, None)
                continue
            val = bike_value(b)
            chance = max(0.15, min(0.9, 1.4 - price / max(1, val)))
            if r.random() < chance:
                offer = int(min(price, val * r.uniform(0.9, 1.2)) / 10) * 10
                msgs.append({"kind": "offer", "uid": uid, "price": offer,
                             "text": f"{r.choice(FIRST)}: megvenném a {MODELS[b['model']]['name']}-t ${offer}-ért."})
        # az ellenfelek fejlődnek
        for x in self.rivals:
            x["cash"] += 60 + x["tier"] * 40
            if r.random() < 0.08 and x["tier"] < 5 and x["name"] != KING:
                x["tier"] += 1
                for s, pid in TIERS[x["tier"]].items():
                    if fits(pid, x["bike"]["model"]):
                        x["bike"]["parts"][s] = {"id": pid, "cond": r.randint(70, 95)}
        # kihívás telefonon
        if self.current and r.random() < 0.45:
            x = r.choice([y for y in self.rivals if y["name"] != KING])
            bet = int(min(x["cash"], max(100, self.money * r.uniform(0.1, 0.4))) / 10) * 10
            msgs.append({"kind": "challenge", "rival": x["name"], "bet": bet,
                         "text": f"{x['name']}: Na, kiállsz ellenem a pályán? ${bet} a tét."})
        self.messages = msgs
        self.new_day_market()
        self.note(f"{self.day}. nap")
        return msgs

    # -- segédek
    def note(self, t):
        self.log = (self.log + [t])[-60:]

    def bike(self, uid):
        return next((b for b in self.bikes if b["uid"] == uid), None)

    def cur(self):
        return self.bike(self.current)

    def rival(self, name):
        return next((x for x in self.rivals if x["name"] == name), None)

    # -- vásárlás, eladás
    def buy_ad(self, ad_id):
        ad = next((a for a in self.ads if a["id"] == ad_id), None)
        if not ad:
            return False, "a hirdetés már nem él"
        if len(self.bikes) >= GARAGE_SLOTS:
            return False, f"a garázsban {GARAGE_SLOTS} hely van — előbb adj el egy motort"
        if self.money < ad["price"]:
            return False, "nincs elég pénzed"
        self.money -= ad["price"]
        self.bikes.append(ad["bike"])
        self.ads.remove(ad)
        if not self.current:
            self.current = ad["bike"]["uid"]
        self.note(f"megvetted: {MODELS[ad['bike']['model']]['name']} (${ad['price']})")
        return True, "a motor a garázsodban"

    def list_for_sale(self, uid, price):
        if not self.bike(uid):
            return False, "nincs ilyen motor"
        self.selling[uid] = max(50, int(price))
        return True, "a hirdetés holnap megjelenik a Moto Apróban"

    def cancel_sale(self, uid):
        self.selling.pop(uid, None)
        return True, ""

    def accept_offer(self, uid, price):
        b = self.bike(uid)
        if not b:
            return False, "nincs ilyen motor"
        self.bikes.remove(b)
        self.selling.pop(uid, None)
        self.money += price
        if self.current == uid:
            self.current = self.bikes[0]["uid"] if self.bikes else ""
        self.messages = [m for m in self.messages if m.get("uid") != uid]
        self.note(f"eladtad: {MODELS[b['model']]['name']} (${price})")
        return True, f"eladva ${price}-ért"

    def buy_part(self, pid):
        p = PARTS[pid]
        if self.money < p["price"]:
            return False, "nincs elég pénzed"
        self.money -= p["price"]
        self.stock.append({"id": pid, "cond": 100})
        self.note(f"vettél: {p['name']} (${p['price']})")
        return True, "a raktárba került"

    def buy_junk(self, key):
        j = next((x for x in self.junk if x["key"] == key), None)
        if not j:
            return False, "már elvitték"
        if self.money < j["price"]:
            return False, "nincs elég pénzed"
        self.money -= j["price"]
        self.junk.remove(j)
        self.stock.append({"id": j["id"], "cond": j["cond"]})
        return True, "a raktárba került"

    def sell_part(self, idx):
        if not 0 <= idx < len(self.stock):
            return False, "nincs ilyen alkatrész"
        it = self.stock.pop(idx)
        price = max(5, int(part_value(it["id"], it["cond"]) * 0.4))
        self.money += price
        return True, f"eladva ${price}-ért"

    # -- szerelés
    def install(self, idx):
        b = self.cur()
        if not b:
            return False, "nincs kiválasztott motor"
        if not 0 <= idx < len(self.stock):
            return False, "nincs ilyen alkatrész"
        it = self.stock[idx]
        if not fits(it["id"], b["model"]):
            return False, "ebbe a motorba nem illik"
        slot = PARTS[it["id"]]["slot"]
        old = b["parts"][slot]
        self.stock[idx] = old
        b["parts"][slot] = it
        if old["id"] == "bl_none":
            self.stock.pop(idx)
        return True, f"beszerelve: {PARTS[it['id']]['name']}"

    def repair_cost(self, b, slot=None):
        if slot:
            p = b["parts"][slot]
            return int(PARTS[p["id"]]["price"] * (100 - p["cond"]) / 100 * 0.5)
        frame = int(MODELS[b["model"]]["value"] * (100 - b["cond"]) / 100 * 0.25)
        return frame + sum(self.repair_cost(b, s) for s in SLOTS)          # váz + minden alkatrész

    def repair(self, slot=None):
        b = self.cur()
        if not b:
            return False, "nincs kiválasztott motor"
        cost = self.repair_cost(b, slot)
        if cost <= 0:
            return False, "nincs mit javítani"
        if self.money < cost:
            return False, f"a javítás ${cost} — nincs elég pénzed"
        self.money -= cost
        if slot:
            b["parts"][slot]["cond"] = 100
        else:
            b["cond"] = 100
            for p in b["parts"].values():
                p["cond"] = 100
        return True, f"megjavítva (${cost})"

    def paint(self, color, flames):
        b = self.cur()
        if not b:
            return False, "nincs kiválasztott motor"
        cost = PAINT_PRICE + (FLAMES_PRICE if flames and not b.get("flames") else 0)
        if self.money < cost:
            return False, "nincs elég pénzed"
        self.money -= cost
        b["color"], b["flames"] = color, bool(flames)
        return True, f"új fényezés (${cost})"

    # -- verseny
    def rival_accepts(self, name, bet, pink):
        x = self.rival(name)
        b = self.cur()
        if not x or not b:
            return False, "nincs ellenfél vagy motor"
        if name == KING and not self.king_available():
            return False, "A Király csak azzal áll ki, aki legalább 8 embert legyőzött"
        if b["parts"]["engine"]["cond"] <= 0:
            return False, "a motorod blokkja tönkrement — javítsd vagy cseréld"
        if not pink and (bet > self.money):
            return False, "nincs ennyi pénzed"
        if not pink and bet > x["cash"]:
            return False, f"{name}: Nincs nálam ennyi."
        mine, _ = simulate(b, reaction=0.3)
        theirs, _ = simulate(x["bike"], reaction=0.3)
        margin = mine - theirs               # pozitív: ő a gyorsabb
        if pink:
            ok = margin > 0.15 or (name != KING and self.rng.random() < 0.15)
            return (True, "Áll az alku: a vesztes motorja a győztesé!") if ok else (False, f"{name}: Forgalmira? Veled? Majd ha gyorsabb leszel… vagy lassabb.")
        ok = margin > -0.6 or self.rng.random() < 0.25
        return (True, f"{name}: Rendben, ${bet}. Pályára!") if ok else (False, f"{name}: Hagyjuk, ma nem.")

    def opponent_params(self, name):
        x = self.rival(name)
        p = race_params(x["bike"])
        r = self.rng
        skill = min(0.95, 0.55 + x["tier"] * 0.07)
        p["reaction"] = round(r.uniform(0.18, 0.5) - skill * 0.12, 3)
        p["launch"] = round(r.uniform(0.35, 0.7), 2)
        p["shift"] = round(0.88 + skill * 0.1 + r.uniform(-0.04, 0.02), 3)
        return p

    def finish_race(self, name, bet, pink, won, my_time, their_time, over_rev, foul):
        x = self.rival(name)
        b = self.cur()
        res = {"won": won}
        if over_rev > 0 and b:                    # túlpörgetés: motorkár
            e = b["parts"]["engine"]
            e["cond"] = max(0, e["cond"] - min(35, int(over_rev * 25)))
            res["engine"] = e["cond"]
        if b:
            b["parts"]["tire"]["cond"] = max(5, b["parts"]["tire"]["cond"] - self.rng.randint(1, 4))
        if won:
            x["losses"] += 1
            if name not in self.beaten:
                self.beaten.append(name)
            self.rep += 1 + x["tier"]
            if pink:
                if len(self.bikes) < GARAGE_SLOTS:
                    nb = x["bike"]
                    nb["uid"] = f"b{self.rng.randint(10**8, 10**9)}"
                    self.bikes.append(nb)
                    res["got"] = MODELS[nb["model"]]["name"]
                    x["bike"] = new_bike(x["bike"]["model"], self.rng, cond=60, parts=TIERS[max(0, x["tier"] - 1)])
                else:
                    val = bike_value(x["bike"])
                    self.money += val
                    res["got"] = f"${val} (a garázsod tele, a motorját pénzért adta)"
            else:
                self.money += bet
                x["cash"] -= bet
            if name == KING:
                self.won = True
            self.note(f"legyőzted: {name} ({my_time:.2f} s vs {their_time:.2f} s)")
        else:
            x["wins"] += 1
            if pink and b:
                self.bikes.remove(b)
                res["lost"] = MODELS[b["model"]]["name"]
                self.current = self.bikes[0]["uid"] if self.bikes else ""
            else:
                self.money -= bet
                x["cash"] += bet
            self.note(f"vesztettél: {name}" + (" (korai indulás)" if foul else ""))
        return res

    # -- mentés
    def to_json(self):
        return {"v": 1, "day": self.day, "money": self.money, "bikes": self.bikes, "current": self.current,
                "stock": self.stock, "rep": self.rep, "beaten": self.beaten, "won": self.won, "log": self.log,
                "messages": self.messages, "selling": self.selling, "rivals": self.rivals, "ads": self.ads,
                "junk": self.junk, "bar": [x["name"] for x in self.bar], "seed": self.rng.random()}

    def from_json(self, d):
        for k in ("day", "money", "bikes", "current", "stock", "rep", "beaten", "won", "log", "messages", "selling",
                  "rivals", "ads", "junk"):
            setattr(self, k, d[k])
        self.bar = [x for x in self.rivals if x["name"] in d.get("bar", [])]
        self.rng = random.Random(d.get("seed"))

    def save(self, slot="mentes"):
        os.makedirs(SAVE_DIR, exist_ok=True)
        p = os.path.join(SAVE_DIR, slot + ".json")
        with open(p + ".tmp", "w", encoding="utf-8") as f:
            json.dump(self.to_json(), f, ensure_ascii=False)
        os.replace(p + ".tmp", p)
        return p

    def load(self, slot="mentes"):
        try:
            with open(os.path.join(SAVE_DIR, slot + ".json"), encoding="utf-8") as f:
                self.from_json(json.load(f))
            return True
        except (OSError, ValueError, KeyError):
            return False


def ad_text(b, r):
    s = bike_summary(b)
    cond = "kiváló" if b["cond"] > 85 else "jó" if b["cond"] > 65 else "használt" if b["cond"] > 45 else "felújítandó"
    extra = (", " + ", ".join(s["mods"][:2]).lower()) if s["mods"] else ""
    flames = ", lángfényezés" if b.get("flames") else ""
    return (f"ELADÓ: {s['name']}, {s['cc']} cm³, {cond} állapotban{extra}{flames}. "
            + r.choice(["Csere nem érdekel.", "Komoly érdeklődők!", "Garázsban tartott.", "Papírok rendben.",
                        "Hétvégén megtekinthető.", "Sürgősen!"]))
