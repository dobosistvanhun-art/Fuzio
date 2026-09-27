# Kísérleti Wine-javítások (M4 proof-of-concept)

Ezek a javítások az M4 kísérleti futtatójához (Wine) tartoznak, **nem a FusionOS
követelményei**, és nem a végleges architektúra részei.

| Javítás | Mit csinál | Miért kell az M4-ben |
| --- | --- | --- |
| `0001-mountmgr-Ports-AutoDetect-switch.patch` | `HKLM\Software\Wine\Ports\AutoDetect=N` esetén a Wine nem képez le automatikusan minden `/dev/ttyS*`, `/dev/ttyUSB*` eszközt COM-portra | a LightBurn csak a COM3-at (= `/dev/fusion/laser`) lássa; ne lássa a Klipper MCU portját és a 32 ttyS-t |

A FusionOS-szintű követelmény ettől független: a Windows-program COM3-a a Fusion
eszközréteg (M3) `laser` szerepére mutat.
