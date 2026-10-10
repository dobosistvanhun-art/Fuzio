"""a Fusion Hardware Layer állapota (csak olvas) — a fusion-hwprobe kimenete: /run/fusion/hardware/display.env"""
import os

from . import RUN, kv


def display(path=None):
    """{"profile", "profileName", "status", "driverState", "adapter", "adapterCount", "message", "raw": {...}}"""
    raw = kv.read(path or os.path.join(RUN, "hardware", "display.env"), shell=True)
    g = lambda k, d="": raw.get("FUSION_DISPLAY_" + k, d)  # noqa: E731
    try:
        count = int(g("ADAPTER_COUNT", "0") or 0)
    except ValueError:
        count = 0
    return {"profile": g("PROFILE"), "profileName": g("PROFILE_NAME"), "status": g("STATUS"),
            "driverState": g("DRIVER_STATE"), "adapter": g("ADAPTER"), "adapterId": g("ADAPTER_ID"),
            "adapterCount": count, "message": g("MESSAGE"), "raw": raw}


def summary(path=None):
    """egy sor emberi olvasásra: „nvidia-kepler-470 (ok, driver: loaded)”"""
    d = display(path)
    return f"{d['profile'] or '?'} ({d['status'] or '?'}, driver: {d['driverState'] or '?'})"
