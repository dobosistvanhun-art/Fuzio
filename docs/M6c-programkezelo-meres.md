# M6c — irányítópult, LightBurn-indítás, Fusion Programkezelő: a Firefox-mérés

## Frissítés (Mint) — a DATA és a LightBurn megmarad

```bash
cd ~/Fusion && \
rm -rf fusionos-regi && mv fusionos fusionos-regi && \
tar xzf fusionos-m6c.tar.gz && \
cp -r fusionos-regi/build/cache fusionos/build/ && \
cd fusionos && \
build/fusion-build deps --install && \
build/fusion-build all && \
sudo build/fusion-build update /dev/sdb
```

## A) Ami változott

- [ ] **Irányítópult** az asztalon (minden ablak alatt): óra; Lézer (állapot, LightBurn gomb); 3D nyomtató
      (Klipper állapota, nyomtatás közben fájl, százalék, idő, fej- és tálcahőmérséklet); Hálózat; Rendszer
      (CPU, hőmérséklet, memória, DATA); Meghajtók; Programok. Ki-/bekapcsolás: Beállítások → Asztal.
- [ ] Nyomtatás végén / hibánál értesítés jön.
- [ ] **LightBurn indítása**: a Wine külön tálcaikon-ablaka már nem ugrik fel. Az első indításkor (frissítés
      után) a futtatókörnyezet egyszer frissül — erről értesítés jelzi, hogy ne tűnjön lefagyásnak.

## B) Fusion Programkezelő — a Linux-programok formátumának mérése (Firefox)

A döntés előtt két formát mérünk (terv: projekt → `claude/Programkezelo-architektura.md`):
**Flatpak** (Flathub) és a **Mozilla saját csomagja** (tarball a DATA-n). Internet kell (Wi-Fi), kb. 1–2 GB
letöltés, 10–20 perc. A Fusion Desktop termináljában (Ctrl+Alt+T):

```bash
fusion-appmeasure --check
fusion-appmeasure firefox
```

Közben Firefox-ablakok nyílnak és zárulnak — ne nyúlj a géphez. A végén egy táblázat: telepítési idő,
méret, indulás, memória, és hogy a grafika **NVIDIA** (hardveres) vagy **szoftveres** — ez a legfontosabb
sor. Mentés: `/data/fusion/appmeasure-….txt`.

**Kézi rész** (a táblázat alatt is kiírja):
1. `flatpak run org.mozilla.firefox` → **Ctrl+O**: megjelenik a fájlválasztó?
2. Mindkét Firefoxban `about:support` → Grafika → *Összeállítás / Compositing*: WebRender vagy WebRender (Software)?
   A tarballos indítása: `/data/programs/_meres/firefox-tarball/firefox/firefox`
3. Egy videó (hang még nincs a rendszerben) — akad-e?

**Visszajelzés:** fotó a táblázatról + a három kézi pont. Utána döntünk a formátumról, és a mérés
telepítései törölhetők: `fusion-appmeasure --clean`.
