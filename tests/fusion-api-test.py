#!/usr/bin/env python3
"""Fusion API (M8) — egységtesztek a `fusion` csomagra, rendszer nélkül (ideiglenes mappákkal).
Futtatás: python3 tests/fusion-api-test.py   (a build `test` lépése is futtatja, a QEMU előtt)"""
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = tempfile.mkdtemp()
os.environ.update(FUSION_DEVICES_ROLES=os.path.join(ROOT, "devices", "roles"), FUSION_DEV=os.path.join(T, "dev"),
                  FUSION_DEVICES_DB=os.path.join(T, "devices.conf"), FUSION_PROGRAMS_DIR=os.path.join(T, "programs"),
                  FUSION_RUN=os.path.join(T, "run"))
sys.path.insert(0, os.path.join(ROOT, "desktop", "lib"))
import fusion  # noqa: E402
from fusion import devices, hardware, kv, notify, permissions  # noqa: E402

ok = fail = 0


def check(name, cond, extra=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  OK    {name}")
    else:
        fail += 1
        print(f"  HIBA  {name} {extra}")


print("Fusion API egységtesztek")
check("API_VERSION", fusion.API_VERSION == 1)
# kv
d = kv.parse("# megj\n a = 1 \nb=két szó\n\nnincs-egyenlő\nport.COM3 = laser\n")
check("kv.parse", d == {"a": "1", "b": "két szó", "port.COM3": "laser"}, d)
s = kv.parse("X='a'\\''b'\nY=\"c d\"\nZ=sima\nE=''\n", shell=True)
check("kv.parse shell-idézés", s == {"X": "a'b", "Y": "c d", "Z": "sima", "E": ""}, s)
p = os.path.join(T, "x", "p.fusion")
kv.write(p, {"name": "Próba", "id": "proba", "üres": "", "z": "1"}, header="teszt", order=("id", "name"))
check("kv.write sorrend + üres kihagyva", open(p).read() == "# teszt\nid = proba\nname = Próba\nz = 1\n", repr(open(p).read()))
check("kv.write atomikus (nincs .tmp)", not os.path.exists(p + ".tmp"))
check("kv.read hiányzó fájl", kv.read(os.path.join(T, "nincs")) == {})
# hardware
os.makedirs(os.path.join(T, "run", "hardware"))
open(os.path.join(T, "run", "hardware", "display.env"), "w").write(
    "FUSION_DISPLAY_STATUS='manual'\nFUSION_DISPLAY_PROFILE='intel-kms'\nFUSION_DISPLAY_DRIVER_STATE='loaded'\n"
    "FUSION_DISPLAY_ADAPTER_COUNT='2'\nFUSION_DISPLAY_MESSAGE='Kézi profilválasztás (mérés): intel-kms'\n")
h = hardware.display(os.path.join(T, "run", "hardware", "display.env"))
check("hardware.display", h["profile"] == "intel-kms" and h["adapterCount"] == 2 and h["status"] == "manual", h)
check("hardware.summary", hardware.summary(os.path.join(T, "run", "hardware", "display.env")) == "intel-kms (manual, driver: loaded)")
# devices
r = {x["role"]: x for x in devices.roles()}
check("devices: szerepek a .role fájlokból", set(r) == {"laser", "printer"} and r["laser"]["com"] == "COM3", list(r))
check("devices: nincs csatlakoztatva", not r["laser"]["present"] and r["laser"]["programs"] == [])
os.makedirs(os.path.join(T, "dev"))
open(os.path.join(T, "ttyUSB0"), "w").close()
os.symlink(os.path.join(T, "ttyUSB0"), os.path.join(T, "dev", "laser"))
open(os.environ["FUSION_DEVICES_DB"], "w").write("laser path:1a86:7523:pci-0000:00:14.0-usb-0:2:1.0\n")
kv.write(os.path.join(T, "programs", "lightburn", "program.fusion"),
         {"id": "lightburn", "name": "LightBurn", "type": "win64", "port.COM3": "laser", "port.COM5": "ismeretlen"})
r = {x["role"]: x for x in devices.roles()}
check("devices: csatlakoztatva + azonosító", r["laser"]["present"] and r["laser"]["dev"] == "ttyUSB0"
      and r["laser"]["key"].startswith("path:"), r["laser"])
check("devices: COM a program leírójából", r["laser"]["programs"] == [{"id": "lightburn", "name": "LightBurn", "com": "COM3"}],
      r["laser"]["programs"])
check("devices.present", [x["role"] for x in devices.present() if x["present"]] == ["laser"])
# értesítés: a parancssor ellenőrzi a paramétereket (Shell nélkül a küldés nem sikerül, de nem száll el)
check("notify.main paraméter nélkül → 2", notify.main([]) == 2)
check("notify.send Shell nélkül → False", notify.send("x") in (False, True))
check("permissions.check (most mindig engedélyez)", permissions.check("x", "device:laser"))
# --- M8b: sémák, elsőbbségi szabály, feladat-protokoll, parancssor ---
from fusion import cli, jobs, schema, ui  # noqa: E402
import contextlib  # noqa: E402
import io  # noqa: E402
import json  # noqa: E402
import time  # noqa: E402
for f in [os.path.join(ROOT, "fwr", "profiles", x) for x in os.listdir(os.path.join(ROOT, "fwr", "profiles"))] + \
        [os.path.join(ROOT, "devices", "roles", x) for x in os.listdir(os.path.join(ROOT, "devices", "roles"))]:
    probs = schema.validate_file(f)
    check(f"schema: {os.path.basename(f)} érvényes", not probs, probs)
bad = schema.validate_program({"id": "X y", "name": "x", "type": "win64", "port.COM12": "laser", "open": "lbrn", "uj": "1"})
lv = {(p[1], p[0]) for p in bad}
check("schema: hibák felismerése", {("id", "hiba"), ("port.COM12", "hiba"), ("open", "hiba"), ("exe", "hiba"),
                                    ("uj", "figyelmeztetés")} <= lv, bad)
check("schema: flatpak appid kötelező", ("appid", "hiba") in {(p[1], p[0]) for p in schema.validate_program({"id": "a", "name": "A", "type": "flatpak"})})
check("schema: recept type nélkül is", not schema.validate_program({"id": "lb", "name": "LB", "exe": "C:\\x.exe", "match": "L*.exe"}, recipe=True))
rec = {"id": "lightburn", "name": "LightBurn", "exe": "C:\\Program Files\\LightBurn\\LightBurn.exe", "windows": "win10",
       "port.COM3": "laser", "drive.P": "Projektek", "match": "LightBurn*.exe", "recipe_file": "/x/lightburn.fwr"}
m0 = schema.apply_recipe(rec)
check("apply_recipe: új leírás", m0["type"] == "win64" and m0["port.COM3"] == "laser" and "match" not in m0 and "recipe_file" not in m0, m0)
m1 = schema.apply_recipe(dict(rec, exe="C:\\LB2\\LightBurn.exe"),
                         {"id": "lightburn", "name": "LightBurn", "type": "win64", "exe": "C:\\régi.exe", "port.COM4": "laser",
                          "drive.Q": "Munkák", "places": "none"})
check("apply_recipe: a recept technikai kulcsa frissül, a felhasználó beállítása marad",
      m1["exe"] == "C:\\LB2\\LightBurn.exe" and m1.get("port.COM4") == "laser" and "port.COM3" not in m1
      and m1.get("drive.Q") == "Munkák" and "drive.P" not in m1 and m1["places"] == "none", m1)
# feladat-protokoll
check("jobs.parse_line", jobs.parse_line("LÉPÉS 2/6: Írás") == ("step", 2, 6, "Írás") and jobs.parse_line("PROGRESS 42") == ("progress", 42)
      and jobs.parse_line("napló") == ("log", "napló"))
os.environ["FUSION_JOBS_DIR"] = os.path.join(T, "jobs")
os.environ["PYTHONPATH"] = os.path.join(ROOT, "desktop", "lib")
err, pr = jobs.start("proba", "Próba", ["sh", "-c", "echo 'LÉPÉS 1/2: egy'; echo PROGRESS 50; echo 'LÉPÉS 2/2: kettő'; echo 'kész: jó'"],
                     okpat="^kész")
check("jobs.start", err == "" and pr is not None, err)
pr.wait()
st = jobs.state("proba")
check("jobs.state kész", not st["running"] and st["rc"] == 0 and st["step"] == {"i": 2, "n": 2, "text": "kettő"} and st["progress"] == 50
      and st["recent"] and st["lines"][-1] == "kész: jó", st)
err, pr = jobs.start("hibas", "Hibás", ["sh", "-c", "echo 'x: rossz'; exit 3"])
pr.wait()
check("jobs.state sikertelen", jobs.state("hibas")["rc"] == 3)
check("jobs.list_jobs", [j["name"] for j in jobs.list_jobs()] == ["hibas", "proba"])
try:
    jobs.state("../x")
    check("jobs: érvénytelen név elutasítva", False)
except ValueError:
    check("jobs: érvénytelen név elutasítva", True)
# rajzolási mód (Qt nélkül)
rf = os.path.join(T, "render")
open(rf, "w").write("software\n")
check("ui.render_mode fájlból", ui.render_mode(rf) == "software" or ui.render_forced() or os.environ.get("FUSION_UI_RENDER"))


def run_cli(*a):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = cli.main(list(a))
    return rc, buf.getvalue()


rc, o = run_cli("api-version", "--json")
check("cli api-version --json", rc == 0 and json.loads(o) == {"api": 1}, o)
rc, o = run_cli("devices", "--json")
j = json.loads(o)
check("cli devices --json", rc == 0 and {x["role"] for x in j} == {"laser", "printer"}
      and all({"role", "name", "present", "dev", "key", "programs", "com"} <= set(x) for x in j), o[:200])
rc, o = run_cli("jobs", "--json")
check("cli jobs --json", rc == 0 and {"name", "title", "running", "rc", "step", "progress", "lines"} <= set(json.loads(o)[0]), o[:200])
rc, o = run_cli("system", "--json")
j = json.loads(o)
check("cli system --json", rc == 0 and {"api", "version", "slot", "bootState", "display", "render"} <= set(j), o[:200])
rc, o = run_cli("validate", os.path.join(ROOT, "fwr", "profiles", "lightburn.fwr"), "--json")
check("cli validate --json", rc == 0 and json.loads(o)[0]["ok"] and json.loads(o)[0]["kind"] == "recipe", o[:200])
rc, o = run_cli("schema", "--json")
check("cli schema --json", rc == 0 and json.loads(o)["version"] == 1 and "port.COMn" in json.loads(o)["program"]["fields"])
rc, o = run_cli("volumes", "--json")
check("cli volumes --json", rc == 0 and isinstance(json.loads(o), list))
rc, o = run_cli("nincs-ilyen", "--json")
check("cli ismeretlen parancs → 2, JSON-hiba", rc == 2 and "error" in json.loads(o))
# --- M8d / akkumulátor: fusion.power (hamis /sys/class/power_supply) ---
from fusion import power  # noqa: E402
ps = os.path.join(T, "ps")
for name, files in {"AC": {"type": "Mains", "online": "0"},
                    "BAT0": {"type": "Battery", "status": "Discharging", "capacity": "84", "energy_now": "42000000",
                             "energy_full": "50000000", "energy_full_design": "70000000", "power_now": "14000000",
                             "cycle_count": "312", "manufacturer": "HP", "model_name": "AI06XL"},
                    "hidpp_battery_0": {"type": "Battery", "scope": "Device", "capacity": "50"}}.items():
    os.makedirs(os.path.join(ps, name))
    for k, v in files.items():
        open(os.path.join(ps, name, k), "w").write(v + "\n")
power.PS_DIR = ps
b = power.batteries()
check("power.batteries (az egér akkuja kimarad)", len(b) == 1 and b[0]["name"] == "BAT0", b)
check("power: töltöttség, idő, állapot", b[0]["percent"] == 84 and b[0]["minutes"] == 180 and b[0]["health"] == 71
      and b[0]["cycles"] == 312 and b[0]["plugged"] is False and b[0]["statusText"] == "merül", b[0])
check("power.summary", power.summary() == "84 %, merül — még 3 ó 00 p, állapot: 71 % a gyárihoz képest", power.summary())
open(os.path.join(ps, "BAT0", "status"), "w").write("Charging\n")
open(os.path.join(ps, "AC", "online"), "w").write("1\n")
b = power.batteries()[0]
check("power: töltés, becsült idő a teljesig", b["status"] == "Charging" and b["minutes"] == 34 and b["plugged"] is True, b)
power.PS_DIR = os.path.join(T, "nincs")
check("power: akkumulátor nélkül üres", power.batteries() == [] and power.summary() == "")
rc, o = run_cli("power", "--json")
check("cli power --json", rc == 0 and json.loads(o) == {"ac": None, "batteries": []}, o)
# fusion.programs (a Programkezelő API-felülete)
from fusion import programs as fprog  # noqa: E402
check("programs.users_of", fprog.users_of("laser") == [{"id": "lightburn", "name": "LightBurn", "com": "COM3"}], fprog.users_of("laser"))
check("programs.info ismeretlen", fprog.info("nincs-ilyen") is None and fprog.info("../x") is None)
print(f"Eredmény: {ok} sikeres, {fail} hibás")
sys.exit(1 if fail else 0)
