# G1 — Vas & Króm (beépített motoros játék)

A régi „Street Rod” mechanikája motorokra: használt motor a hirdetésből, alkatrészek, szerelés, kihívás a kocsmában
pénzre vagy forgalmira, gyorsulási verseny 402 m-en, a végén a Király. A név saját: a „Street Rod” és a „Boss Hoss”
mások márkanevei, ezért a V8-as óriásmotor a játékban „V8-as óriás”, a gyártók kitaláltak.

Indítás: Start menü → Játékok → **Vas & Króm**, vagy `fusion-vaskrom`. Mentés: `~/.local/share/vaskrom/mentes.json`
(minden művelet után), rajzok: `~/.cache/vaskrom/`.

## Oldalak

| Oldal | Mi van rajta |
| --- | --- |
| **Garázs** | a kiválasztott motor nagyban (az alkatrészekből rajzolva — a csere látszik), adatok (LE, Nm, kg, becsült 402 m-es idő, érték); alkatrészek állapottal és javítással; raktár (beszerelés, eladás); fényezés (10 szín, lángnyelvek); eladás hirdetéssel; próbafutam |
| **Moto Apró** | használt motorok hirdetései (bobber, café, cruiser, chopper, V8-as óriás), állapottal; naponta új szám |
| **Katalógus** | új alkatrész csoportonként: motorblokk, karburátor, vezérműtengely, kipufogó, levegőszűrő, gyújtás, feltöltő, váltó, hátsó gumi, kormány |
| **Bontó** | használt alkatrész olcsón, változó állapotban, naponta más |
| **Kocsma** | a ma ott ülő motorosok; tét ($100–$2500) vagy **forgalmira** (a vesztes motorja a győztesé); ranglista (12 ellenfél, a csúcson a Király — 8 győzelem után áll ki) |
| **Telefon** | nap végén: vevők ajánlatai az eladásra kínált motorra, kihívások |

**Nap vége**: új hirdetések és bontókínálat, a vevők jelentkeznek, az ellenfelek fejlesztenek.

**Pénz (0.0.45):** kezdőpénz $3000; az újságban mindig van egy olcsó **felújítandó** motor (~$900–1300), így a
vétel után marad pénz javításra és tétre (a legkisebb tét $50). Ha mégis elfogy: **Szerelőmunka** a Garázsban —
egy nap telik el, $120–220 (+ a hírnévvel nő).

## Hang (0.0.45)

Nincs hangfájl: minden hang a játékban számolódik ki (`sound.py`), a FusionOS hangrendszerén (PipeWire) szól.
- **Motorhang:** minden gyújtás egy rövid kipufogó-impulzus; a ritmus a hengerszámtól függ — V2 (45°): a jellegzetes
  egyenetlen „krumpli-krumpli”, V8: dübörgés. A nagyobb köbcenti mélyebb; a hangosabb kipufogó (drag, 2-1) erősebb,
  zajosabb, gázelvételnél durrog. Az ellenfél motorja a távolsággal halkul.
- Kipörgő gumi, lámpa (sárga: rövid, zöld: magas), váltás, győzelem / vereség, vásárlás, hiba.
- **Garázs → BERÚGÁS:** a motor alapjáraton jár, a GÁZ gombbal felpörgethető — a kipufogócsere itt hallatszik.
- Menü (☰) → Hang ki/be (megjegyzi). CPU-igény: ~5 % egy magon verseny közben (két motor + gumi).

## Verseny

- Lámpa: 3 sárga, majd zöld. **SZÓKÖZ** (vagy a GÁZ gomb, nyomva tartva) = gáz, **JOBB NYÍL / ENTER** (KUPLUNG) = indulás,
  utána ugyanez a váltás. Zöld előtt indulsz: piros lámpa, vesztettél.
- Indulás: a kuplung csúszik, amíg a kerék utol nem éri a motor fordulatát — magas fordulat: erős indulás, de
  kipörgés (füst); alacsony: lefullad.
- A fordulatszámmérő piros mezőjében (leszabályozás) tartott gáz: motorkár (versenyenként legfeljebb 35 %, próbafutamon 20 %).
- Ágaskodás nagy nyomatéknál; légellenállás (kormány), tapadás (gumi, állapot), tömeg.
- Az ellenfél ugyanezzel a fizikával megy, saját reakcióidővel, indulási fordulattal és váltással (a tudása a szintjétől függ).

## Felépítés

| Fájl | |
| --- | --- |
| `desktop/games/vaskrom/model.py` | a játék állapota, alkatrészek, motorok, ellenfelek, a gyorsulási modell (`simulate`) — Qt nélkül |
| `desktop/games/vaskrom/art.py` | a motor oldalnézeti rajza SVG-ben, az alkatrészekből (váz, blokk, tank, kipufogó, kormány, kerekek külön rétegen) |
| `desktop/games/vaskrom/fusion_vaskrom.py` | a felület háttere (QObject), önteszt |
| `desktop/games/vaskrom/qml/` | Main, Garage, News, Catalog, Junk, Bar, Phone, Race (a versenyfizika a `simulate` JS-párja) |

Önteszt: `fusion-vaskrom --selftest` → `VASKROM: BUY / SIM / PART / ART / QML` (minden oldal és egy próbafutam, ablak
nélkül). A rendszer-önteszt sora: `FUSION-G1:`.

## Tovább

G2: városi motorozás felülnézetből, utcai verseny, rendőrség. G3: motorhang a fordulathoz, finomhangolás.
