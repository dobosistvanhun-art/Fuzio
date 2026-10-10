# FusionOS 0.0.37 — M8d: Lézer állapot (próba-program) + akkumulátor az Asztalon

## Lézer állapot (Start → Műhely → Lézer állapot, vagy `fusion-laser`)

Az első Fusion-natív program, amely **csak a Fusion API-t** használja (`fusion.devices`, `fusion.programs`, a felülethez
`fusion_ui` + FusionUI). Ezzel bizonyítja, hogy az API elég egy valódi programhoz (M8, 7. fejezet).

- A szerep állapota: csatlakoztatva-e, melyik eszközön (`ttyUSB0`, `/dev/fusion/laser`). Be- és kihúzáskor 2 mp-en belül frissül, és üzenetet ír.
- Azonosítás: mi alapján ismeri fel a FusionOS a lézert (a fizikai USB-port vagy a sorozatszám).
- Melyik Windows-program melyik COM-porton éri el (pl. COM3 → LightBurn), **Indítás** gombbal.
- Gombok: Eszközök beállítása, Programkezelő.
- Általános: bármely szerepre működik (`fusion-laser printer`).

Az API-ból hiányzott, ezért most került bele:
- `fusion.programs`: a Programkezelő felülete — lista, indítás, ki melyik eszközt éri el;
- `fusion.power`: az akkumulátor adatai.

## Akkumulátor (István kérése, 2026-10-10)

- **Asztal → Rendszer kártya**, a processzor és a memória alatt:
  - töltöttség (sáv: 30 % alatt sárga, 15 % alatt piros);
  - töltődik / merül / feltöltve, a becsült idő;
  - az akkumulátor állapota: kapacitás a gyárihoz képest, töltési ciklusok, ha a gép közli.
- **Hibajelentés** fejléce: „Akkumulátor:” sor.
- **Parancssor**: `fusion power` (`--json`).
- Általános megoldás: a Linux szabványos `/sys/class/power_supply` felületét olvassa. Akkumulátor nélküli gépen a rész nem látszik. Az egér és a billentyűzet akkuját nem számolja.

## Ellenőrzés

- Egységtesztek: 48, köztük az akkumulátor hamis rendszerfájlokkal (merülés, töltés, akkumulátor nélkül).
- QEMU: a `fusion power --json` és a Lézer állapot önteszt a valódi eszközréteggel.
- A ZBookon:
  - **Asztal**: az akkumulátor sora a Rendszer kártyán;
  - **Start → Lézer állapot**: a lézert be- és kihúzva frissül-e; az Indítás elindítja-e a LightBurnt.
