"""Fúzió — hálózat (Wi-Fi) a Fúzió Desktop programjainak

A Wi-Fi-t az iwd kezeli; ez a modul a rendszerbuszon (D-Bus, net.connman.iwd) kérdezi,
a busctl JSON-kimenetével — nincs képernyőszöveg-értelmezés. Jelszavas új hálózathoz
az iwctl --passphrase kapcsolódik (ugyanúgy, mint a fusion-wifi); a megjegyzett
hálózatokat az iwd a DATA-n tárolja, legközelebb magától kapcsolódik.
Jogosultság: az iwd D-Bus-szabálya a sudo és a netdev csoportnak engedi.
"""
import json
import os
import subprocess

IWD = "net.connman.iwd"


def _busctl(*args, timeout=4):
    try:
        r = subprocess.run(["busctl", "--system", "--json=short"] + list(args),
                           capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as e:
        return None, str(e)
    if r.returncode != 0:
        return None, (r.stderr or r.stdout).strip()
    try:
        return json.loads(r.stdout) if r.stdout.strip() else {}, ""
    except ValueError:
        return None, r.stdout


def _v(props, key, default=None):
    x = props.get(key)
    return x.get("data", default) if isinstance(x, dict) else default


def level(signal100):
    """jelerősség (100*dBm) → 0..4 oszlop"""
    dbm = signal100 / 100.0
    for lv, th in ((4, -60), (3, -67), (2, -74), (1, -82)):
        if dbm >= th:
            return lv
    return 0


def objects():
    j, err = _busctl("call", IWD, "/", "org.freedesktop.DBus.ObjectManager", "GetManagedObjects")
    if j is None:
        return None, err
    data = j.get("data") or [{}]
    return data[0], ""


def state():
    """{"ok", "error", "device", "path", "state", "ssid", "ip", "scanning", "known": [...]}"""
    objs, err = objects()
    if objs is None:
        return {"ok": False, "error": "a Wi-Fi szolgáltatás (iwd) nem érhető el" + (f": {err}" if err else ""),
                "state": "nincs", "ssid": "", "device": ""}
    st = {"ok": True, "error": "", "device": "", "path": "", "state": "nincs eszköz", "ssid": "", "ip": "",
          "scanning": False, "powered": False, "known": []}
    for path, ifaces in sorted(objs.items()):
        if "net.connman.iwd.Station" in ifaces and not st["path"]:
            s = ifaces["net.connman.iwd.Station"]
            dev = ifaces.get("net.connman.iwd.Device", {})
            st.update(path=path, device=_v(dev, "Name", ""), powered=_v(dev, "Powered", False),
                      state=_v(s, "State", "?"), scanning=_v(s, "Scanning", False))
            cn = _v(s, "ConnectedNetwork", "")
            if cn and cn in objs:
                st["ssid"] = _v(objs[cn].get("net.connman.iwd.Network", {}), "Name", "")
        if "net.connman.iwd.KnownNetwork" in ifaces:
            k = ifaces["net.connman.iwd.KnownNetwork"]
            st["known"].append({"path": path, "name": _v(k, "Name", ""), "type": _v(k, "Type", ""),
                                "auto": _v(k, "AutoConnect", True)})
    if not st["path"]:
        # van-e eszköz egyáltalán (pl. kikapcsolt rádió)
        for path, ifaces in objs.items():
            if "net.connman.iwd.Device" in ifaces:
                d = ifaces["net.connman.iwd.Device"]
                st.update(device=_v(d, "Name", ""), powered=_v(d, "Powered", False), state="kikapcsolva")
    if st["device"]:
        try:
            r = subprocess.run(["ip", "-4", "-o", "addr", "show", "dev", st["device"]],
                               capture_output=True, text=True, timeout=3)
            parts = r.stdout.split()
            if "inet" in parts:
                st["ip"] = parts[parts.index("inet") + 1]
        except (OSError, subprocess.TimeoutExpired):
            pass
    return st


def networks(st=None):
    """látható hálózatok, erősség szerint: [{"path","name","type","signal","level","connected","known"}]"""
    st = st or state()
    if not st.get("path"):
        return []
    j, _err = _busctl("call", IWD, st["path"], "net.connman.iwd.Station", "GetOrderedNetworks")
    if not j:
        return []
    objs, _ = objects()
    objs = objs or {}
    out = []
    for path, sig in (j.get("data") or [[]])[0]:
        n = objs.get(path, {}).get("net.connman.iwd.Network", {})
        out.append({"path": path, "name": _v(n, "Name", "?"), "type": _v(n, "Type", ""),
                    "signal": sig, "level": level(sig), "connected": bool(_v(n, "Connected", False)),
                    "known": bool(_v(n, "KnownNetwork", ""))})
    return out


def scan(st=None):
    st = st or state()
    if not st.get("path"):
        return False, "nincs Wi-Fi eszköz"
    j, err = _busctl("call", IWD, st["path"], "net.connman.iwd.Station", "Scan")
    # "már folyamatban" nem hiba
    return (j is not None or "InProgress" in err or "Busy" in err), err


def connect(name, passphrase="", st=None):
    """kapcsolódás: megjegyzett / nyílt hálózat a D-Buson, új jelszavas az iwctl-lel"""
    st = st or state()
    if not st.get("device"):
        return False, "nincs Wi-Fi eszköz"
    if passphrase:
        cmd = ["iwctl", "--passphrase", passphrase, "station", st["device"], "connect", name]
    else:
        for n in networks(st):
            if n["name"] == name:
                j, err = _busctl("call", IWD, n["path"], "net.connman.iwd.Network", "Connect", timeout=40)
                return (j is not None), err
        cmd = ["iwctl", "station", st["device"], "connect", name]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=40)
        out = (r.stdout + r.stderr).strip()
        return r.returncode == 0 and "fail" not in out.lower(), out
    except (OSError, subprocess.TimeoutExpired) as e:
        return False, str(e)


def disconnect(st=None):
    st = st or state()
    if not st.get("path"):
        return False, "nincs Wi-Fi eszköz"
    j, err = _busctl("call", IWD, st["path"], "net.connman.iwd.Station", "Disconnect")
    return j is not None, err


def forget(name, st=None):
    st = st or state()
    for k in st.get("known", []):
        if k["name"] == name:
            j, err = _busctl("call", IWD, k["path"], "net.connman.iwd.KnownNetwork", "Forget")
            return j is not None, err
    return False, "nem megjegyzett hálózat"


def wired():
    """vezetékes (és egyéb) csatolók IPv4-címmel: [{"name","state","ip"}]"""
    try:
        r = subprocess.run(["ip", "-j", "addr"], capture_output=True, text=True, timeout=3)
        data = json.loads(r.stdout or "[]")
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return []
    out = []
    for i in data:
        name = i.get("ifname", "")
        # csak valódi (eszközhöz tartozó) vezetékes csatolók; a Wi-Fi-t a fenti rész mutatja
        if name == "lo" or not os.path.exists(f"/sys/class/net/{name}/device") or os.path.exists(f"/sys/class/net/{name}/wireless"):
            continue
        ip = next((a["local"] + "/" + str(a["prefixlen"]) for a in i.get("addr_info", []) if a.get("family") == "inet"), "")
        out.append({"name": name, "state": i.get("operstate", "").lower(), "ip": ip})
    return out
