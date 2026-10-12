"""kamerák — a Linux szabványos V4L2 felületéből (csak olvas)

    cameras()    [{dev, name, bus, usb, driver, index}] — csak a képrögzítésre alkalmas eszközök (egy USB-kamera
                 a /dev/video0 mellett metaadat-eszközt is ad: /dev/video1 — az nem kamera)
    summary()    egy sor emberi olvasásra

A beépített webkamera (UVC) a uvcvideo modullal jelenik meg; a hozzáférés a video csoporté (a felhasználó tagja).
A Flatpak-programok (böngésző, videohívás) a /dev/video* eszközt közvetlenül vagy a kamera-portálon át érik el.
"""
import os
import re
import subprocess

V4L_DIR = os.environ.get("FUSION_V4L_SYS", "/sys/class/video4linux")
DEV_DIR = os.environ.get("FUSION_DEV_DIR", "/dev")

# V4L2 képességjelzők (videodev2.h)
CAP_VIDEO_CAPTURE = 0x00000001
CAP_VIDEO_CAPTURE_MPLANE = 0x00001000
CAP_META_CAPTURE = 0x00800000


def _r(path):
    try:
        with open(path) as f:
            return f.read().strip()
    except OSError:
        return ""


def _device_caps(dev):
    """a v4l2-ctl --info „Device Caps” értéke; None, ha nem olvasható"""
    try:
        r = subprocess.run(["v4l2-ctl", "-d", dev, "--info"], capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.TimeoutExpired):
        return None
    m = re.search(r"Device Caps\s*:\s*0x([0-9a-fA-F]+)", r.stdout)
    if not m:
        m = re.search(r"Capabilities\s*:\s*0x([0-9a-fA-F]+)", r.stdout)
    return int(m.group(1), 16) if m else None


def _usb_id(sysdir):
    """a sysfs-ben fölfelé haladva az USB-eszköz azonosítója (vendor:product)"""
    d = os.path.realpath(os.path.join(sysdir, "device"))
    for _ in range(4):
        v, p = _r(os.path.join(d, "idVendor")), _r(os.path.join(d, "idProduct"))
        if v and p:
            return f"{v}:{p}"
        d = os.path.dirname(d)
    return ""


def cameras():
    try:
        names = sorted(n for n in os.listdir(V4L_DIR) if n.startswith("video"))
    except OSError:
        return []
    names.sort(key=lambda n: int(re.sub(r"\D", "", n) or 0))
    res = []
    for n in names:
        sd = os.path.join(V4L_DIR, n)
        dev = os.path.join(DEV_DIR, n)
        caps = _device_caps(dev)
        if caps is not None:
            if not caps & (CAP_VIDEO_CAPTURE | CAP_VIDEO_CAPTURE_MPLANE):
                continue
        elif _r(os.path.join(sd, "index")) not in ("", "0"):
            continue            # v4l2-ctl nélkül: az eszköz második csomópontja általában metaadat
        drv = os.path.basename(os.path.realpath(os.path.join(sd, "device", "driver")))
        usb = _usb_id(sd)
        res.append({"dev": dev, "name": _r(os.path.join(sd, "name")) or n, "usb": usb,
                    "bus": "USB" if usb else ("virtuális" if drv in ("vivid", "v4l2loopback") else "egyéb"),
                    "driver": drv if drv not in ("", "device") else "", "index": n})
    return res


def summary():
    c = cameras()
    return ", ".join(f"{x['name']} ({x['dev']})" for x in c) if c else "nincs kamera"
