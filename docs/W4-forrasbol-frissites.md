# W4 — Új változat a forrásból, egy gombbal (0.0.69)

**Hol:** Beállítások → Rendszerfrissítés → „Új változat a forrásból…” (csak ha a gépen van Fúzió-forrás:
`~/Projektek/fusionos`). Parancssorban: `fusion-dev rebuild` (`--check [--json]`: csak az ellenőrzés).

**Lépések** (a Fúzió feladat-protokolljával — lépésszám, haladás; az ablak bezárható, a build fut tovább):

| # | Lépés | Ha baj van |
| --- | --- | --- |
| 1 | ellenőrzés: nem commitolt módosítás (követett fájlokban), a GitHubtól eltérő helyi ág, ≥ 10 GB szabad hely, Fejlesztődoboz; töltő (csak figyelmeztetés) | megáll, semmihez nem nyúl, kiírja az okot |
| 2 | `git pull --ff-only` (ha a GitHubon van új); ha nincs, a mostani állapotból épít | megáll |
| 3–5 | `build/fusion-build fetch`, `rootfs` (csak ha a forrás változott), `build` — a Fejlesztődobozban | megáll; „Elemzés a FusionAI-val” |
| 6 | takarítás: a régi VirtualBox-lemezkép (`*.vdi`) törlése, a `.fupd`-k közül a 3 legújabb marad | — |

A végén: „Elkészült … Telepítsem most?” — Telepítés most / Később. Az újraindítást a felhasználó indítja.
Hibánál az „Elemzés a FusionAI-val” a build naplóját a FusionAI-ba tölti (`fusion-ai <forrás> --kimenet <napló>`),
ott a „Kimenet → Claude” gombbal elemezhető.

**Megszűnt:** `build/fusion-build vdi | vm | vm-start` (VirtualBox-os fejlesztői környezet). Az `all` a teljes készletet
(lemezkép, telepítő-lemezkép) továbbra is elkészíti — mérföldkő-kiadáshoz; a gép frissítéséhez a .fupd elég.

**Ellenőrzés (fejlesztőgép):** a `fusion-dev rebuild` próba-repóval és próba-builddel (`FUSION_DEV_BUILD_RUNNER`):
mögötte lévő ág → pull, 6 lépés, .vdi törölve, 3 .fupd maradt, `FUPD:` / `KÉSZ:` sor; nem commitolt módosítás és
csak helyi commit → megáll. A feladat-protokoll (lépés, haladás, rc) a `fusion.jobs`-szal. A Rendszerfrissítés oldal
offscreen képernyőképeken (folyamatban, ellenőrző ablak, „Telepítsem most?”). **A ZBookon nincs kipróbálva.**
