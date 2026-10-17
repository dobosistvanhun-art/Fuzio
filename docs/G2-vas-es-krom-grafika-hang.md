# 0.0.49 (g2): Vas & Króm — új grafika, megbízhatóbb hang

## Grafika
- **Motorok** (`art.py`, újraírva): minden típusnak saját formája van.
  - Bobber: fekete blokk, szóló nyereg rugókon, csonkított sárvédő.
  - Café racer: térdmélyedéses tank, púpos ülés, csonkkormány.
  - Cruiser: szoknyás sárvédők, primer-fedél, padló, tükör, kiegészítő lámpák.
  - Chopper: merev váz, magas háttámla, kis tank, majomkormány.
  - V8: turbinaküllős kerekek.
- **Részletek:**
  - bordázott hengerek és hengerfejek, krómozott szelepfedél, tolórudak, vezérműfedél, szűrők;
  - árnyalt fényezés csillanással, csíkozás és embléma, lángnyelvek;
  - keresztbe fűzött küllők, féktárcsa, szíjtárcsa;
  - hőfuttatott drag-csövek, megafon (2-1);
  - árnyék a talajon.
- **Jelenetek** (`scenes.py` → `img/*.svg`):
  - garázs: szerszámfal, polc, munkapad, lámpafény, plakát, gumihalom; a motor a padlón áll;
  - kocsma: lambéria, italpolc, csapok, fotók, darts;
  - bontó: roncshalmok, drótkerítés, daru;
  - versenypálya: naplemente, város és lelátó (nézők, zászlók, reklámtáblák), parallaxisos csempékkel.
- Minden rajz saját, a nevek kitaláltak. A rajzok a Qt SVG-rajzolójához készültek: szűrő nincs, csak színátmenet és réteg.

## Hang
- A ZBookon a játék néma volt. Ugyanez a kód a fejlesztői gépen PipeWire-rel szólt (felvétellel mérve), tehát az ok gépfüggő.
- **A hangkimenet most:**
  - több formátumot próbál (mono 22 050 Hz, sztereó 48/44,1 kHz, az eszköz saját formátuma);
  - megnyitás után ellenőrzi a hibát;
  - a folyam végig fut, csendben nullákat ír; nincs felfüggesztés és folytatás.
- **Hangpróba:** `fusion-vaskrom --hangproba`. Kiírja:
  - a játék hangbeállítását;
  - a hangkiszolgálót és az alapértelmezett kimenetet, annak hangerejét és némítását;
  - mit lát a Qt (eszköz, formátum, hiba);
  - a folyam állapotát a kiszolgálón.

  Közben lejátszik sípszókat, motorhangot és egy dallamot.
