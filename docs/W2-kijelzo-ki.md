# 0.0.75 — Kijelző ki gombbal és tétlenség után (ellenőrzés a ZBookon)

István kérése (2026-11-05): a fedél lecsukása nélkül egy gombbal kikapcsolni a kijelzőt; időzítő, hogy x perc
tétlenség után kikapcsoljon; videó alatt ne kapcsoljon ki.

## Hol van
- **Fedél lecsukásakor**: Beállítások → **Rendszer** → **ENERGIA** (a Hardver és a Lomtár között): Altatás / Töltőn
  csak kijelző ki / Csak kijelző ki. A Start menü keresőjében: „fedél”, „energia”, „kijelző”.
- **Kijelző ki tétlenség után**: ugyanott — Soha / 5 / 10 / 15 / 30 / 60 perc. Alapérték: Soha (mint eddig).
- **Kijelző ki most**: Start → kikapcsolás gomb (jobb alul) → „Kijelző ki”; **Ctrl+Alt+K**; Beállítások → Rendszer →
  Energia → „Kijelző ki”; parancssorban `fusion-shell screen-off`. Egérmozdításra / billentyűre visszajön.

## Hogyan működik
- A tétlenségi időt az X-kiszolgáló DPMS-e méri (`xset dpms 0 0 <mp>`); a Fúzió Shell 5 mp-enként egyezteti a
  beállítással (`fusion.screen.apply`), így felnyitás / ébredés után is helyreáll. Kikapcsolt kijelzőhöz nem nyúl.
- Ébren tartás: a Shell az `org.freedesktop.ScreenSaver` szolgáltatás (`/org/freedesktop/ScreenSaver`,
  `/ScreenSaver`): `Inhibit` → amíg tart, `xset -dpms`; `UnInhibit` vagy a kérő kilépése → újra az időzítő.
  Az XScreenSaverSuspend-et (mpv) az X maga tartja be. Napló: `~/.local/share/fusion/shell.log`
  („kijelző ébren tartva — …”, „ébren tartás vége — …”).

## Próba
1. Beállítások → Rendszer → Energia → „5 perc”. Terminálban: `xset q | tail -4` → `Standby: 0  Suspend: 0  Off: 300`,
   `DPMS is Enabled`.
2. 5 perc érintés nélkül → a kijelző kikapcsol; egérmozdításra visszajön.
3. Firefoxban YouTube-videó lejátszása → a Beállítások Energia részén: „Most ébren tartja: …”; `xset q` → `DPMS is
   Disabled`; 5 perc után sem kapcsol ki. Szünet / fül bezárása → a sor eltűnik, az időzítő újra él.
4. Start → kikapcsolás gomb → „Kijelző ki” (és Ctrl+Alt+K) → a kijelző kb. 1 mp múlva kikapcsol, egérre visszajön.
5. Fedél le / fel („Csak kijelző ki” módban) → felnyitás után `xset q` újra a beállított időt mutatja.

## Mit nem próbáltunk (a fejlesztőgépen nincs DPMS)
A logika és a D-Bus-szolgáltatás egy utánzott `xset`-tel és valódi munkamenet-busszal kipróbálva (Inhibit / UnInhibit /
a kérő kilépése / kikapcsolt kijelző / „Soha”); a `fusion-settings --selftest` (SCREEN, QML, SLOTS) ok. **A ZBookon nincs
kipróbálva:** a valódi DPMS az NVIDIA 470-nel, és hogy a Flatpak Firefox valóban kér-e ébren tartást (a portálon át
vagy közvetlenül). Ha a 3. pont nem jön („Most ébren tartja” nem jelenik meg), a Firefox nem kér — akkor jelezd.

## Visszavonás
A Beállításokban „Soha” = a régi viselkedés. Kódban: a `screensaver.py` és a `fusion/screen.py` törlése, a
`fusion_shell.py` `tick_screen` / `screenOff` részei, a Start menü „Kijelző ki” sora, a jwmrc két `screen-off` sora.
