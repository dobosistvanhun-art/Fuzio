"""Fúzió — Fúzió API (Python-csomag `fusion`), 1-es változat

Az M8 szerint (claude/M8-Fusion-API-terv.md): a Fúzió saját képességeinek egyetlen, közös belépési pontja a
Fúzió-programoknak és a szkripteknek. A Linux-szabványos részeket (fájlok, hálózat-protokollok, systemd, Qt) nem
fedi el; csak ott ad saját felületet, ahol a Fúziónak saját tudása van.

    fusion.kv          kulcs = érték fájlok (program.fusion, *.role, *.profile, *.fwr, display.env)
    fusion.hardware    a Hardware Layer állapota (csak olvas)
    fusion.devices     eszközszerepek (lézer, nyomtató), COM-hozzárendelés
    fusion.notify      értesítések (org.freedesktop.Notifications)
    fusion.camera      kamerák (V4L2, csak olvas)
    fusion.bluetooth   Bluetooth-adapter és -eszközök (BlueZ)
    fusion.printers    papírnyomtatók (CUPS)
    fusion.users       felhasználók (a fusion-users rootrésszel)
    fusion.x11         ablakok (EWMH) — a Shell és a Feladatkezelő közös alapja
    fusion.permissions a jogosultság-ellenőrzés helye (most mindent engedélyez)

A rendszerképben a csomag a /usr/lib/fusion/desktop/lib/fusion alatt van, és a Python mindenhol látja
(/usr/lib/python3/dist-packages/fusion → ide mutat).
"""
import os
import sys

API_VERSION = 1

PREFIX = os.environ.get("FUSION_PREFIX", "/usr/lib/fusion")
RUN = os.environ.get("FUSION_RUN", "/run/fusion")
ADMIN = os.environ.get("FUSION_ADMIN", os.path.join(PREFIX, "bin", "fusion-admin"))
# a cserélhető kötetek (pendrive, SD-kártya) csatolási helye — a szabványos /run/media/<felhasználó>/<címke>: a GTK és Qt
# fájlválasztói (a Flatpak-programokban is, pl. PrusaSlicer) így mutatják őket eszközként
MEDIA_USER = os.environ.get("FUSION_MEDIA_USER", "fusion")
MEDIA = os.environ.get("FUSION_MEDIA_DIR", "/run/media/" + MEDIA_USER)
CONFIG = os.path.join(os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config"), "fusion")

DESKTOP_LIB = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))


def _programs_lib():
    env = os.environ.get("FUSION_PROGRAMS_LIB")
    if env:
        return env
    repo = os.path.join(os.path.dirname(os.path.dirname(DESKTOP_LIB)), "programs")   # fejlesztői fa: <repo>/programs
    for d in (os.path.join(PREFIX, "programs"), repo):
        if os.path.isfile(os.path.join(d, "fusion_programs.py")):
            return d
    return os.path.join(PREFIX, "programs")


PROGRAMS_LIB = _programs_lib()


def add_paths():
    """a régi, nem csomagba tartozó Fúzió-modulok (fusion_ui, fusion_programs …) elérése"""
    for p in (DESKTOP_LIB, PROGRAMS_LIB):
        if p not in sys.path:
            sys.path.insert(0, p)
