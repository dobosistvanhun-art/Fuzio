# FusionOS 0.0.36 (m8b, j5 rész) — LightBurn: a DATA mappái a fájlválasztóban + Wi-Fi a hibajelentésben

## Mi volt a gond (0.0.34–0.0.35)

- **LightBurn → Projekt megnyitása**: a Windows-fájlválasztóban csak a C: (a program belső környezete), a P: és a
  Linux-fájlrendszer („/”, bin, etc, home…) látszott. Az Asztal és a Dokumentumok a Wine üres belső mappái voltak, ezért üres volt a lista.
  A DATA mappái nem látszottak.
- **Wi-Fi**: a kapcsolat időnként megszakad, majd helyreáll (pl. 04:50, 06:20). A hibajelentésben nem volt benne
  a Wi-Fi szolgáltatás (iwd) és a kártya (iwlwifi) naplója, ezért az ok nem látszott.

## Mi változott

| | |
| --- | --- |
| Asztal (a fájlválasztó fájának teteje) | **Adatok**, **Letöltések**, **Pendrive**, **Projektek**, **Saját mappa** |
| Sajátgép | **Program (C:)** — a program saját környezete, **Adatok (D:)**, **(E:)** — a pendrive-ok, **(P:)** — Projektek |
| Adatok (D:) | a DATA meghajtó felhasználói mappái (pl. import, printer, a saját mappáid). A rendszer mappái (overlay, fwr, programs, dev) nem látszanak. Új mappa a DATA-n: a program következő indításakor jelenik meg. |
| Dokumentumok | a **Projektek** mappára mutat — a program alapértelmezett mentési helye így látható helyre kerül. Ha a régi, belső Dokumentumok mappában volt fájl, az átkerül a Projektekbe (névütközésnél marad a helyén). |
| Letöltések | a valódi Letöltések mappa |
| Elrejtve | a Linux-fájlrendszer („/”), a Lomtár, a Vezérlőpult |
| Google Drive | **nem** része a Windows-programok helyeinek |
| Fájlkezelő → Megnyitás a LightBurnnel | DATA-n vagy pendrive-on lévő fájl is megnyitható (D:\…, E:\…) |
| Hibajelentés | új **WI-FI** szakasz: a kártya meghajtója, energiatakarékosság (be/ki), a kapcsolat adatai (jel, sebesség), a kártya modulparaméterei, a kapcsolódások és a megszakadásra utaló kernelüzenetek száma, a kernel Wi-Fi üzenetei és az iwd naplója. A gyors ellenőrzésben: „Wi-Fi ennél az indításnál: N× kapcsolódott, M megszakadásra utaló üzenet”. A hálózat neve és a MAC-címek maszkolva. |

Ez a Fusion Windows Runtime általános beállítása (`places = standard`, alapértelmezés minden Windows-programnál;
`places = none` kikapcsolja). Nem LightBurn-specifikus, és nem új Wine-architektúra: a kísérleti M4-megvalósításon belül marad.

## Frissítés (Minten, ~/Fusion)

```bash
cd ~/Fusion
rm -rf fusionos-regi && mv fusionos fusionos-regi
tar xzf fusionos-m8b.tar.gz
cp -r fusionos-regi/build/cache fusionos/build/
cd fusionos
build/fusion-build all
```
Utána a `.fupd` → pendrive → Beállítások → Rendszerfrissítés → Telepítés → Újraindítás most.

## Ellenőrzés a ZBookon

1. **LightBurn** → Fájl → Megnyitás: a bal oldali fában az Asztal alatt Adatok, Letöltések, Pendrive, Projektek, Saját mappa.
   Az első indítás néhány másodperccel tovább tart (a környezet frissül).
2. Adatok: a DATA mappái; Pendrive: a bedugott pendrive (a fájlkezelőben csatolva).
3. Mentés: az alapértelmezett hely a Projektek.
4. **Wi-Fi**: ha legközelebb megszakad, utána **rögtön** egy hibajelentés (Beállítások → Hibajelentés).
   A WI-FI szakaszból kiderül, ki bontotta a kapcsolatot (a router, a jel elvesztése vagy a kártya), és hogy be van-e kapcsolva
   az energiatakarékosság. Javítani ez után fogok, a mért adat alapján.
