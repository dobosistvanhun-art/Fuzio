# FusionOS 0.0.35 (m8a1) — a pendrive a Flatpak-programok fájlválasztójában

**Hiba (0.0.34, ZBook, 2026-10-10):** a PrusaSlicer megnyitás-ablakában a pendrive nem látszott sem a bal oldali
listában, sem az „Egyéb helyek” között (Ctrl+L-lel, a `/run/media/…` útvonal beírásával elérhető volt).

**Ok:** a pendrive-ok eddig a `/run/media/<címke>` alá csatolódtak. A GLib (a GTK fájlválasztóinak alapja — a
Flatpak-programokban is) normál felhasználónak csak a `/media/…` és a **`/run/media/<felhasználó>/…`** alatti köteteket
mutatja eszközként (ez a Linux-asztalok szabványos helye). Mérve: ugyanaz a csatolás rootként látszik, a
felhasználóként nem.

**Javítás:** a cserélhető kötetek helye mostantól **`/run/media/fusion/<címke>`** (a Fusion API-ban: `fusion.MEDIA`).
A Fájlkezelő, a Mentés, a Telepítő, a Lemezkezelő, a frissítés és a hibajelentés ezt használja. A QEMU-teszt a GLib
saját döntését ellenőrzi a fusion felhasználó nevében (`FUSION-M6: GIO-SHOWN … FUSIONUSB`).

Közben: a Fusion Shell leállításakor (kikapcsolás) a naptár / hang / értesítés felület nem ír több „… of null” sort.

## Ellenőrzés a ZBookon

Frissítés után: pendrive be → PrusaSlicer → Megnyitás: a pendrive a bal oldali listában (vagy az „Egyéb helyek”
alatt) a címkéjével látszik. Ugyanígy a Firefox, Inkscape, GIMP, LibreOffice fájlválasztójában.
