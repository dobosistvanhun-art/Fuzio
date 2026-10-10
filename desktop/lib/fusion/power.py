"""energiaellátás — akkumulátor és hálózati táp (csak olvas), a Linux szabványos power_supply felületéből

    batteries()   [{name, percent, status, statusText, plugged, minutes, health, cycles, model, …}]
    summary()     egy sor emberi olvasásra, vagy "" ha nincs akkumulátor
    ac_online()   True / False / None (nincs hálózati táp-adat)

Általános: bármely gép /sys/class/power_supply/* bejegyzéseit olvassa (BAT0, BAT1, CMB0 …); akkumulátor nélküli
gépen üres lista — a felületek ilyenkor nem mutatják az akkumulátor-részt.
"""
import os

PS_DIR = os.environ.get("FUSION_POWER_SUPPLY", "/sys/class/power_supply")

STATUS_TEXT = {"Charging": "töltődik", "Discharging": "merül", "Full": "feltöltve", "Not charging": "nem tölt",
               "Unknown": "ismeretlen"}


def _r(d, name):
    try:
        with open(os.path.join(d, name)) as f:
            return f.read().strip()
    except OSError:
        return ""


def _int(d, name):
    v = _r(d, name)
    try:
        return int(v)
    except ValueError:
        return None


def _entries():
    try:
        return sorted(os.path.join(PS_DIR, e) for e in os.listdir(PS_DIR))
    except OSError:
        return []


def ac_online():
    found = None
    for d in _entries():
        if _r(d, "type") == "Mains":
            found = bool(found) or _r(d, "online") == "1"
    return found


def _battery(d, plugged):
    status = _r(d, "status") or "Unknown"
    # energia (µWh, µW) vagy töltés (µAh, µA) — a gyártótól függ
    now, full, design, rate = (_int(d, "energy_now"), _int(d, "energy_full"), _int(d, "energy_full_design"),
                               _int(d, "power_now"))
    if now is None:
        now, full, design, rate = (_int(d, "charge_now"), _int(d, "charge_full"), _int(d, "charge_full_design"),
                                   _int(d, "current_now"))
    pct = _int(d, "capacity")
    if pct is None and now is not None and full:
        pct = round(100.0 * now / full)
    minutes = None
    if rate and rate > 0 and now is not None:
        if status == "Discharging":
            minutes = int(60.0 * now / rate)
        elif status == "Charging" and full:
            minutes = int(60.0 * max(0, full - now) / rate)
        if minutes is not None and minutes > 48 * 60:
            minutes = None                     # a mérés elején értelmetlenül nagy becslés
    health = round(100.0 * full / design) if full and design else None
    return {"name": os.path.basename(d), "percent": max(0, min(100, pct)) if pct is not None else None,
            "status": status, "statusText": STATUS_TEXT.get(status, status.lower()), "plugged": plugged,
            "minutes": minutes, "health": health, "cycles": _int(d, "cycle_count"),
            "model": " ".join(x for x in (_r(d, "manufacturer"), _r(d, "model_name")) if x),
            "technology": _r(d, "technology")}


def batteries():
    plugged = ac_online()
    out = []
    for d in _entries():
        if _r(d, "type") == "Battery" and _r(d, "scope") != "Device" and _r(d, "present") != "0":
            out.append(_battery(d, plugged))
    return out


def hm(minutes):
    if minutes is None:
        return ""
    return f"{minutes // 60} ó {minutes % 60:02d} p" if minutes >= 60 else f"{minutes} p"


def summary():
    bs = batteries()
    if not bs:
        return ""
    parts = []
    for b in bs:
        s = f"{b['percent']} %" if b["percent"] is not None else "?"
        s += ", " + b["statusText"]
        if b["minutes"] is not None:
            s += (" — még " if b["status"] == "Discharging" else " — tele: ") + hm(b["minutes"])
        if b["health"] is not None:
            s += f", állapot: {b['health']} % a gyárihoz képest"
        parts.append(s)
    return "; ".join(parts)
