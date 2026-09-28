# Kísérleti Wine-javítások (M4 proof-of-concept)

Ezek a javítások az M4 kísérleti futtatójához (Wine) tartoznak, **nem a FusionOS
követelményei**, és nem a végleges architektúra részei.

| Javítás | Mit csinál | Miért kell az M4-ben |
| --- | --- | --- |
| `0001-mountmgr-Ports-AutoDetect-switch.patch` | `HKLM\Software\Wine\Ports\AutoDetect=N` esetén a Wine nem képez le automatikusan minden `/dev/ttyS*`, `/dev/ttyUSB*` eszközt COM-portra; a portlista olvasása átlépi a hosszú (nem port) értékneveket ahelyett, hogy megállna | a LightBurn csak a COM3-at (= `/dev/fusion/laser`) lássa; ne lássa a Klipper MCU portját és a 32 ttyS-t |
| `0002-windows.devices.enumeration-camera-enumeration.patch` | (1) a `Windows.Media.Capture.Frames.MediaFrameSourceGroup` WinRT-osztály statikus metódusai (a Wine 11.0-ból hiányzik): `FindAllAsync` üres kamera-listát ad, `FromIdAsync` null-t, `GetDeviceSelector` a kamera-szelektort; (2) a `DeviceWatcher` `Updated`/`Removed` feliratkozása működik (eddig csonk, `E_NOTIMPL`). Mindkettő a `windows.devices.enumeration.dll`-ben | a LightBurn 2.x induláskor kamerát keres és kamerafigyelőt indít; az (1) nélkül `0x80040154`, a (2) nélkül `0x80004001` → kezeletlen C++/WinRT-kivétel → összeomlás. A kiegészítéssel „nincs kamera”, a LightBurn 2.1.04 elindul (felhőben ellenőrizve). Ellenőrzés: `fwr check` → `CAM:` sorok (`fwr-camtest.exe`) |

A FusionOS-szintű követelmény ettől független: a Windows-program COM3-a a Fusion
eszközréteg (M3) `laser` szerepére mutat.
