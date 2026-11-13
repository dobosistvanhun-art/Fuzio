"""Fúzió — Beállítások: háttérrész

Oldalak: Wi-Fi, Bluetooth, Kijelző, Eszközök (kamera is), Nyomtatók (CUPS), 3D nyomtató (Klipper), Programkezelő,
Asztal, Rendszerfrissítés, Mentés, Indítás, Hibajelentés, Rendszer.
A lassú lekérdezések és műveletek (Wi-Fi-keresés, kapcsolódás, szolgáltatás-újraindítás) külön
szálon futnak; az eredmény a „result” jelzéssel jön vissza (címke + adat), a felület nem akad meg.
Rendszerjogot igénylő művelet csak a szűk jogú fusion-admin segéden át történik.

0.0.71 óta a kód oldalcsoportonként a `fusion_settings_parts/` alatt van; ez a fájl rakja össze belőlük a
QML `settings` objektumát (Settings), és a régi neveken továbbadja a lekérdező függvényeket (selftest,
fusion-selftest, customize.sh). Új oldal / slot: a megfelelő részbe (vagy új rész + ide a listába).

| rész | tartalom |
| --- | --- |
| base | közös segédek (_read, _timing, SAFE), SettingsBase: jelzések, _async, a feladat-protokoll (_job…) |
| net | Wi-Fi, Bluetooth, Google Drive |
| display | Kijelző, a felület rajzolása, Asztal |
| devices | Eszközök, touchpad, hang, nyomtatók (CUPS), 3D nyomtató (Klipper) |
| programs | Programkezelő, Programbolt, fejlesztői eszközök, Fejlesztődoboz |
| update | Rendszerfrissítés, új változat a forrásból, telepítő pendrive |
| backup | Mentés (kézi és automatikus) |
| system | Rendszer, Indítás, Felhasználók, Hibajelentés |
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))

from fusion_settings_parts.base import *        # noqa: E402,F401,F403
from fusion_settings_parts.base import SettingsBase, _read, _timing  # noqa: E402,F401
from fusion_settings_parts.net import *         # noqa: E402,F401,F403
from fusion_settings_parts.net import NetMixin  # noqa: E402
from fusion_settings_parts.display import *     # noqa: E402,F401,F403
from fusion_settings_parts.display import DisplayMixin  # noqa: E402
from fusion_settings_parts.devices import *     # noqa: E402,F401,F403
from fusion_settings_parts.devices import DevicesMixin  # noqa: E402
from fusion_settings_parts.programs import *    # noqa: E402,F401,F403
from fusion_settings_parts.programs import ProgramsMixin  # noqa: E402
from fusion_settings_parts.update import *      # noqa: E402,F401,F403
from fusion_settings_parts.update import UpdateMixin, _mount_points, _plain_subdirs, _from_src  # noqa: E402,F401
from fusion_settings_parts.backup import *      # noqa: E402,F401,F403
from fusion_settings_parts.backup import BackupMixin  # noqa: E402
from fusion_settings_parts.system import *      # noqa: E402,F401,F403
from fusion_settings_parts.system import SystemMixin  # noqa: E402


class Settings(NetMixin, DisplayMixin, DevicesMixin, ProgramsMixin, UpdateMixin, BackupMixin, SystemMixin,
               SettingsBase):
    """a QML `settings` objektuma: minden oldal slotja egy objektumon (a részek a fusion_settings_parts alatt)"""
