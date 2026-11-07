# Átadási napló (ZBook ⇄ claude.ai)

Kétirányú napló: a helyben (FusionAI / Claude Code) és a webes Claude-dal (claude.ai) végzett munka összefoglalója,
hogy a másik oldal folytatni tudja. Mindkét oldal ide ír; a legfrissebb felül. A FusionAI a munkamenet elején a
legfelső bejegyzéseket olvassa el. Szabály: `CLAUDE.md` → „Átadás”.






## 2026-11-07 — 0.0.77: 7z kicsomagolás; FusionAI: Pull a saját távoli ágról, Fordítás és telepítés
- István kérése: a .7z kicsomagolása a Fájlkezelőben, plusz a megbeszélt teendő (2026-11-06): a FusionAI Pull a
  SolidCraft `fuzio` ágán is húzzon, és egy gomb fordítsa le és telepítse a SolidCraftot.
- Fájlok: `rootfs/packages.list` (`7zip`); `desktop/files/fusion_files_backend.py` (`sevenzip`, `is_7z`,
  `sevenzip_entries`, `FileOps._extract_7z`, `_place`), `desktop/files/fusion_files.py` (önteszt), `desktop/files/qml/Files.qml`
  (a .7z a kicsomagolható listán); `desktop/ai/fusion_ai_core.py` (`pull`: azonos nevű távoli ág; `build` / `install`
  beállítás, `scripts/fuzio-build.sh` felismerése), `desktop/ai/fusion_ai_app.py` (`buildProject`, `installBuilt`,
  `buildReady`, önteszt), `desktop/ai/qml/AI.qml` (gomb, két beállítás-mező, „Telepítsem?” ablak); `docs/W2-7z-kicsomagolas.md`,
  `docs/W3-fusionai.md` 6c; `VERSION`, `README.md`; a `CLAUDE.md`-ből törölve a teendő. A SolidCraft repóban
  (`fuzio` ág): `scripts/fuzio-build.sh` `--no-install` és `--install` módja.
- Próba (felhőben, forrásból): `fusion-files --selftest` → RESULT ok (7Z, 7ZLIST, 7ZSKIP); jelszavas 7z → hibaüzenet;
  `fusion-ai --selftest` → RESULT ok (PULL-OWN-BRANCH, PULL-BRANCH, BUILD, INSTALL, BUILD-FAIL, UI); a SolidCraft
  szkript módjai helyettesítő parancsokkal.
  **Nem próbált:** a build és a telepített 0.0.77 a ZBookon; a valódi SolidCraft-fordítás a gombról (30–60 perc) és
  a telepítés; ha a Fejlesztődoboz épp nyitva van egy terminálban, a `fusion-dev box run` (egyszerre egy példány).
- Döntés (Claude): a RAR nem került be (a `7zip-rar` multiverse, nem szabad licenc); jelszót a Fájlkezelő nem kér.

## 2026-11-05 — 0.0.76: FusionAI — Pull gomb, csak olvasó parancsok kérdés nélkül, kiférő jóváhagyó ablak
- István kérése (FusionAI-ban, helyben): az 1–3. pont a „mit módosítanál magadon” listából, kiegészítésekkel.
  (a) A gitből csak a status/log/diff/show/for-each-ref menjen kérdés nélkül, `-c`, `--output`, `-o`, `--ext-diff`
  kapcsolóval ezek is kérdezzenek. (b) A projekten belüli `.dev.vars`, `.env*`, `*.pem`, `*.key`: a Read és a Bash
  is deny. (c) Csőnél minden tag engedélyezett legyen; `&&`, `;`, `>`, `$( )`, fordított aposztróf, `find -exec`
  jóváhagyós marad. (d) Az önteszt próbálja végig a trükköket.
  Menet közben: a jóváhagyó ablak kétszer kilógott a képernyőből (hosszú próbaparancs, a gombok nem látszottak) →
  javítás ugyanebben a változatban. István utasítása: a próbák a `desktop/ai/tests/` alá, fájlba kerüljenek, és rövid
  paranccsal fussanak, ne hosszú, beágyazott Bash-sal.
- Fájlok: `desktop/ai/fusion_ai_core.py` (`pull`, `_safe_readonly`, `_pipeline`, `_safe_glob`, titkos nevek,
  `is_fusion_repo`, új `system_prompt`, `autoPull` beállítás); `desktop/ai/fusion_ai_app.py` (`pullProject`,
  magától projektnyitáskor / új munkamenetnél, megjegyzés Claude-nak, `saveSettings(…, autoPull)`, önteszt);
  `desktop/ai/qml/AI.qml` (Pull gomb, beállítás-kapcsoló, a jóváhagyó ablak korlátai); új: `desktop/ai/tests/classify_cases.py`
  (106 eset, önállóan is fut), `desktop/ai/tests/ui_check.py` (offscreen ablakmérés); `docs/W3-fusionai.md` 6b.;
  `VERSION`, `README.md`; a `CLAUDE.md`-ből törölve a „git pull gombnyomásra” teendő.
- Próba (ZBook, forrásból, próba-Claude-dal): `python3 desktop/ai/fusion_ai_app.py --selftest` → 167 ellenőrzés, mind
  ok (RESULT ok). Ebből PULL ×7 (bare remote + második klón), PROMPT, 106 CLASSIFY, UI: 1180×760 és 860×520 ablaknál
  a jóváhagyó ablak kifér, az összefoglaló 3 sor.
  **Nem próbált:** a build és a telepített 0.0.76; a Pull gomb a valódi GitHub-repón; a valódi Claude Code-dal a
  kérdés nélküli olvasó parancsok és az ablak. Ismert korlát: a teljes projektre futó Grep a titkos fájlok tartalmát
  nem zárja ki (részletek: `docs/W3-fusionai.md` 6b.).
- Visszavonás: a fenti fájlok visszaállítása a 0.0.75-ös commitra (`779842e`); a beállításban az `autoPull` kulcs
  magától figyelmen kívül marad.
## 2026-11-05 — 0.0.75: kijelző ki gombbal és tétlenség után, videó alatt nem
- István: nem találta, hol a fedél-beállítás → Beállítások → Rendszer → ENERGIA (most a Start menü keresője is
  megtalálja: „fedél”, „kijelző”, „energia”). Kérés: kijelző ki gombbal, időzítő x perc tétlenség után, videó alatt ne.
- Új: `desktop/lib/fusion/screen.py` (Fúzió API), `desktop/shell/screensaver.py` (`org.freedesktop.ScreenSaver`
  Inhibit/UnInhibit a Shellben; a kérő kilépésekor magától megszűnik); `fusion_shell.py`: `tick_screen` (5 mp),
  `screenOff`, a fedél felnyitásakor a beállítás áll vissza (eddig `-dpms`); Start menü → kikapcsolás → „Kijelző ki”;
  jwmrc: Ctrl+Alt+K és XF86ScreenSaver → `fusion-shell screen-off`; Beállítások → Rendszer → Energia: „Kijelző ki
  tétlenség után” (Soha/5/10/15/30/60 perc, a `~/.config/fusion/screen-off` fájlban, root nélkül), „Kijelző ki”,
  „Most ébren tartja: …”. Alapérték: Soha. Leírás: `docs/W2-kijelzo-ki.md`.
- Próba (fejlesztőgépen): utánzott `xset` + valódi D-Bus-munkamenet — Inhibit → `-dpms`, UnInhibit / a kérő kilépése →
  vissza az időzítő, kikapcsolt kijelzőhöz nem nyúl, „Soha” → `-dpms`, a `/ScreenSaver` út gdbus-szal (uint) is jó;
  `fusion-settings --selftest`: SCREEN logic=ok, QML ok, SLOTS ok; a StartMenu.qml betölt; jwmrc XML jó.
  ZBookon: István, 2026-11-05 17:31 — „Jó lett” (telepítve és kipróbálva).
- Teendő a FusionAI-nak: a GitHub-repó új címe `https://github.com/dobosistvanhun-art/Fuzio.git` (a régi átirányít);
  ha a ZBookon még a régi az `origin`: `git remote set-url origin https://github.com/dobosistvanhun-art/Fuzio.git`.
## 2026-11-04 — 0.0.74: a Firefox „Megnyitás mappában” a Fájlkezelőt nyitja
- István (képernyőkép): a Firefox Letöltések ablakában a mappa ikonra „Open With… / No Apps available” jön. Ok: a
  képben nem volt `.desktop`-bejegyzés `inode/directory`-ra, így a portál (xdg-desktop-portal-gtk) nem talált mappakezelőt.
- Javítás: `desktop/files/fusion-files.desktop` (`Exec=fusion-files %U`, `MimeType=inode/directory`, `NoDisplay`), a
  `rootfs/customize.sh` a `/usr/share/applications/`-ba teszi, és `mimeapps.list`-ben alapértelmezettnek jelöli;
  `fusion_files.py`: `start_path()` — `file://` cím, fájl → a mappája, idegen cím / nem létező → saját mappa.
- Próba: a `start_path` 8 esete (ékezetes, szóközös, `localhost`, idegen gép, https, nem létező) jó, a
  `customize.sh` szintaxisa jó. **Nem próbált:** a teljes `fusion-files --selftest` (itt nincs PyQt6), a build és a
  Firefox-gomb a ZBookon — a 0.0.74 telepítése után kell megnézni (Firefox → Letöltések → mappa ikon).
- Visszavonás: a két új sor a `customize.sh`-ban és a `.desktop` fájl törlése.
## 2026-11-01 — ötlet későbbre (István: „ne most, majd ha lesz vele dolgunk”)
- FusionAI: munkamenet indításakor (vagy egy gombbal) magától `git pull --ff-only` a kiválasztott projekten, hogy a
  webes Claude-dal készült változások (`CLAUDE.md`, `docs/ATADAS.md`) kézi parancs nélkül meglegyenek. Nem
  commitolt munka / eltérő ág esetén ne húzzon, csak szóljon.
## 2026-11-01 — webes Claude: 0.0.73, lassú Google Drive a Fájlkezelőben
- István: „a Google a fájlkezelőben iszonyat lassú”. Ok (a forrásból): a `fusion-drive.service` `--dir-cache-time 30s`-e
  miatt 30 mp után minden mappa megnyitása újra a Google API-hoz fordult, és a Fájlkezelő `load()`-ja ezt a felület
  szálán várta ki (megakadt). Mérés a ZBookon nem volt; a `~/.local/share/fusion/files.log` „lassú (… mp)” sorai mutatják.
- Javítás: `--dir-cache-time 1000h` (a `--poll-interval 30s` a Drive változásfolyamával érvényteleníti — rclone ajánlás);
  `desktop/files/fusion_files_backend.py`: felhő-/hálózati kötetnél 0,25 mp után háttérben fejeződik be a listázás.
- Próba (fejlesztőgépen, lassított próba-kötettel): gyors mappa szinkron; lassú mappa 0,25 mp-en belül vált, a lista
  megérkezik, a kijelölés a korábbi mappán; továbblépéskor a késő lista eldobva; hiba a háttérben kijelezve;
  `fusion-files --selftest` ok. ZBookon (valódi Drive): István, 2026-11-01 — „jobb lett”.
## 2026-10-31 — webes Claude: 0.0.72, helytakarítás a DATA-n
- István kérdése: mi foglalja a DATA-t (38 GB / 109 GB). Mérés: 34 GB a saját mappa; ebből `fusionos-regi/build`
  8,4 GB (a 0.0.55 buildje — törölve), `solidcraft/target` 4,3 GB (törölhető, `rm -rf`; a dobozban a `cargo` nincs a
  PATH-on), `build/out/release` régi `fusionos.img` + `fusionos-telepito.img` (0.0.69-es `all`, kb. 3,3 GB valódi
  foglalás — törlendő), Flatpak 4,7 GB (nincs nem használt futtatókörnyezet).
- 0.0.72: a `fusion-dev rebuild` takarítása a régi `.img`-ket is törli (próba: ritka 12 GB-os és valódi kép törölve,
  a .fupd marad). ZBookon ellenőrizetlen.
- István döntése: a mentésből **nem** hagyjuk ki a build-mappákat (a javasolt kizárás elvetve).
## 2026-10-31 — webes Claude: 0.0.71, rendrakás: a Beállítások háttere részekre bontva
- `desktop/settings/fusion_settings_parts/`: base (közös segédek, SettingsBase, feladat-protokoll), net, display,
  devices, programs, update, backup, system; a `fusion_settings_backend.py` csak összerakja (mixinek) és a régi
  neveken továbbadja a függvényeket. Kód nem változott, csak áthelyeződött (gépi szétválasztás, sorról sorra ellenőrizve).
- Ellenőrizve (fejlesztőgépen, PyQt 6.11 és a noble-é, a **6.6.1** alatt is): a 114 slot neve és típusa egyezik a
  szétszedés előttivel; pyflakes tiszta; `fusion-settings --selftest`: QML ok, SLOTS ok; a Mentés oldal képernyőképe;
  a .fupd-keresés próbája; a `customize.sh` modul- és QML-ellenőrzése (egy szándékosan hibás QML-lel is: elkapja).
- Új őr: a Beállítások QML-je csak létező slotot hívhat (selftest `SLOTS`, build: `customize.sh`).
- Döntés (webes Claude javaslata): a „közös függvények a Fúzió API-ba” lépés most elmarad — a keresés szerint alig van
  valódi ismétlődés (a /proc/meminfo olvasása 3 helyen, néhány sor); a frissítés/mentés lekérdezései akkor kerülnek
  a `fusion` csomagba, ha egy második program (pl. a Shell) is használná őket.
- ZBookon ellenőrizetlen: a 0.0.71 build és a Beállítások minden oldalának kattintgatása.
## 2026-10-31 — webes Claude: 0.0.70, automatikus heti DATA-mentés a Tárhelyre
- Kész: `fusion-backup auto | auto-get | auto-set`, `fusion-backup-auto.service/.timer` (naponta 12:30 körül +
  indításkor 20 perc múlva; csak töltőn; altatás-tiltással), `fusion-admin backup auto-get|auto-set|auto-now`,
  Beállítások → Mentés: „AUTOMATIKUS MENTÉS A TÁRHELYRE” szakasz. Leírás: `docs/W5-automatikus-mentes.md`.
- Kipróbálva (fejlesztőgépen): a mentés-logika tmpfs-en (7 napon belül kihagy, `--most` ment, a régiekből `keep` marad,
  hiányzó Tárhely → érthető hiba); a Beállítások oldal képernyőképpel (bekapcsolva / Tárhely nélkül); `--selftest` QML ok.
- **ZBookon ellenőrizetlen:** a timer valódi futása, az értesítés, a valódi Tárhely-csatolás, az altatás-tiltás.
- Ugyanekkor a motoros projektben: 1.30.0 (éjszakai D1 → R2 mentés) — commitolva, **nincs élesítve** (ott: `docs/MENTES.md`).
## 2026-10-31 — állapot (István)
- 0.0.67–0.0.69 a ZBookon működik (a .fupd-keresés gyors, az „Új változat a forrásból” gomb végigment).
- Az altatás / ébredés hibája (2026-10-20) **megoldva, működik** — nem nyitott.
- Javasolt sorrend a folytatáshoz (webes Claude): 1. motoros: tesztkészlet + staging; 2. automatikus mentés (Fúzió
  DATA → Tárhely, motoros D1 → R2); 3. rendrakás (Beállítások háttere szétszedve, közös függvények a Fúzió API-ba).
## 2026-10-30 — webes Claude: 0.0.69, új változat a forrásból egy gombbal; VirtualBox ki
- István döntései: a gomb a Rendszerfrissítés oldalon legyen; a build végén kérdezze meg a telepítést; a VirtualBox-os
  rész (vdi, vm) végleg törölve; a teljes lemezkép-készlet csak mérföldkő-kiadáshoz.
- Kész: `fusion-dev rebuild`, a Beállítások gombja és ablakai, a FusionAI `--kimenet` (build-napló elemzése),
  `build/steps/vm.sh` törölve, `all` VDI nélkül — leírás: `docs/W4-forrasbol-frissites.md`.
- Nyitott: ZBook-próba (a Beállítások a forrásból: `python3 ~/Projektek/fusionos/desktop/settings/fusion_settings.py update`).
## 2026-10-30 — webes Claude: 0.0.68, modell a FusionAI-ban
- István döntése: a FusionAI Opus 5.5-tel, medium erőfeszítéssel dolgozzon. Alapból így indul (`--model claude-opus-5-5
  --effort medium`); a fejlécben választható (a `~/.config/fusion/ai.json` őrzi). Önteszt: MODEL-ARGS ok.
## 2026-10-30 — webes Claude: 0.0.67, a lassú .fupd-keresés oka és javítása
- Mérés a ZBookon (`fupd-gyorsmeres.sh`, hidegen indítva): `glob ~/*/build/out/release` **60 mp fölött** (időtúllépés),
  `~/*/*/build…` 7 mp, ugyanez Google Drive nélkül 0,08 mp, a teljes keresés melegen 0,5 mp. Ok: a build-kimenet keresése
  (`update_roots`, 0.0.48 óta) időkorlát nélkül belépett a `~/GoogleDrive` rclone-csatolásba; hideg gyorsítótárnál ez
  percekig várt. A 0.0.54-es javítás csak a bejárást korlátozta, ezt nem.
- Javítás: a saját mappa almappáit `scandir`-ral nézi (d_type, stat és symlink-követés nélkül), kihagyja a
  GoogleDrive / Tárhely / rejtett mappákat és minden csatolási pontot (`/proc/self/mounts`); a bejárás is a mount-listát
  használja `ismount` (stat) helyett. Próba (fejlesztőgép): a régi kód belép a „Drive”-ba, az új nem; a talált .fupd-k
  ugyanazok.
- Nyitott: ZBook-próba (a Beállítások a forrásból vagy a 0.0.67 buildje után); a FusionAI 16:43-kor indított mérése
  elakadt (valószínűleg ugyanezen) — leállítva.
## 2026-10-29 19:10 — holnapi feladat (István)
- **Hiba:** a Beállítások → Rendszerfrissítés még mindig percekig keresi a frissítőfájlt (`.fupd`). Meg kell nézni,
  mit vizsgál végig (mappák, pendrive-ok, Google Drive, build-kimenet), és miért lassú; mérés előtt nem javítunk.
- A nap eredménye: a FusionAI a ZBookon minden próbán átment (0.0.65); a motoros projekt privát GitHub-repóban,
  1.29.1 (szuperadmin-rate-limit) a FusionAI-val elkészítve és élesítve.
## 2026-10-29 18:20 — a FusionAI minden tervezett próbán átment (ZBook) + 0.0.65
- ZBookon igazolva (István): jóváhagyás, tiltás, kiemelt jóváhagyás (commit), Commit/Push gomb, Visszavonás (Bash-sel
  írt sor is, 0.0.64), munkamenet folytatása újraindítás után, átadás új munkamenetbe a naplóból.
- Észrevétel: a folytatott munkamenetben a Claude nem tudta, hogy a módosítását közben visszavontad („nincs
  commitolva, a változás helyben van meg”). 0.0.65: Visszavonás után a következő kéréshez megjegyzés kerül Claude-nak.
- Nyitott: a 0.0.62–0.0.65 buildje (a Start menüs FusionAI és a Drive-javítás miatt) és a fusion-drive ellenőrzés.

## 2026-10-29 18:10 — webes Claude: 0.0.64 (Visszavonás)
- ZBook-próba (István, 17:54): a Claude a `docs/ATADAS.md` végére Bash-sel (`printf >>`) írt, a Visszavonás azt írta
  „visszavonva”, de a sor megmaradt — a Claude Code `rewind_files`-a csak az Edit/Write-ot követi.
- Javítás: minden kérés előtt pillanatkép (dedupe), a Visszavonás arra állítja vissza a munkafát, és ellenőrzi:
  „Visszavonva” csak akkor, ha a munkafa tényleg azonos; különben kiírja, mi maradt. Önteszt: TURN-BASH, UNDO ok.

## 2026-10-29 18:00 — webes Claude: 0.0.63
- A Commit ablak üres üzenetmezővel nyílt, ezért lett a 0.0.62 üzenete „p”. Most javaslattal nyílik: a README új
  változatsorából („0.0.N (mérföldkő): …”), különben a módosított fájlok neveiből; átírható. Önteszt: COMMIT-SUGGEST ok.

## 2026-10-29 17:45 — a teljes kör a ZBookon (István + FusionAI)
- A FusionAI a „Kimenet → Claude” gombbal elemezte a munkamenet naplóját (nincs valódi hiba, csak zaj), és jóváhagyással
  megcsinálta a 0.0.62-t: `fusion-drive.service` — a `fusermount3 -uz` csak akkor fut, ha a `~/GoogleDrive` csatolva van.
- Commit a FusionAI Commit gombjával, push a Push gombbal (a8e25a9; az üzenet véletlenül csak „p” — a történetet nem
  írjuk át). A ZBookon a Git-szerző és a GitHub-token (fine-grained, Fuzio + solidcraft, Contents írás,
  `credential.helper store`) beállítva.
- Nyitott: a 0.0.62 buildje és a ZBook-próba (`journalctl --user -b -u fusion-drive | grep fusermount` üres);
  a Visszavonás és a munkamenet-folytatás próbája. A `proba-mentes` ág a ZBookon törölhető.

## 2026-10-29 este — webes Claude → ZBook: 0.0.61, a FusionAI 4. fázisa
- Gombok: Teszt, Naplók, Kimenet → Claude, Újraindítás…, Commit…, Push…, Beállítások (projektenkénti teszt- és
  újraindító parancs) — `docs/W3-fusionai.md` 6a. Önteszt (próba-Claude, helyi bare remote-tal): teszt ok / hiba,
  napló, commit szerző nélkül → érthető hiba, commit, push, a remote-on megjelenik — mind ok.
- István: a besorolás nem kérdez se túl sokat, se túl keveset (változatlan).
- Nyitott a ZBookon: a Visszavonás és a munkamenet-folytatás próbája; a 0.0.61 gombjainak próbája; Git-szerző beállítása.

## 2026-10-29 este — webes Claude → ZBook: a kiemelt jóváhagyás nem lehet megkerülhető
- ZBook-próba (István): a „commitold” kérésre a `git add proba.py && git commit …` lefutott (a commit csak a hiányzó
  Git-szerző miatt állt le). Nem biztos, hogy megjelent a piros ablak — ha nem, egy Claude Code-szabály magától
  engedte, és a FusionAI `can_use_tool`-ja meg sem kapta.
- Javítás: a FusionAI szabályai most **PreToolUse-horogként** is futnak (`fusion_ai_app.py: _pre_tool_use`): a tiltott
  tilos, a kiemelt mindig kérdez, bármit engedne a Claude Code magától. A próba-Claude ezt utánozza („megengedő
  szabály”); horog nélkül a DENY-AUTO és a COMMIT-DANGER próba elbukik, vele átmegy.
- **ZBookon igazolva (István, 17:20):** a javítás után a commit kérésére a piros ablak megjelenik, Elutasításra nincs commit.
- Tudnivaló: a Visszaállítás a pillanatkép óta keletkezett új fájlokat (pl. `proba.py`) szándékosan megtartja és
  felsorolja; a stagingből `git restore --staged proba.py` veszi ki.

## 2026-10-29 — webes Claude → ZBook: a FusionAI-beszélgetés összefoglalója (2026-10-26 … 29)
**Kérés (István):** natív QML „FusionAI” alkalmazás a Fúzióban, amelyből a hivatalos Claude Code a ZBookon, a helyi
Git-repókon dolgozik (hibakeresés, javítás, teszt, újraindítás; commit/push csak jóváhagyással), a saját Pro/Max
előfizetéssel, API-kulcs nélkül. Sorrend: felmérés → minimális prototípus → QML-felület → teljes munkafolyamat.

**Kész:**
- 0.0.60 (45e2b92): `desktop/ai/` — `fusion_ai_app.py` (háttér: Claude Agent SDK, külön asyncio-szál), `fusion_ai_core.py`
  (Claude Code / SDK keresése, jogosultsági besorolás, Git-állapot, diff, pillanatkép, visszaállítás), `qml/AI.qml`,
  `tests/fake-claude` (próba-Claude az önteszthez); `fusion-dev install|update|remove claude`; Start menü: Rendszer → FusionAI;
  leírás: `docs/W3-fusionai.md`.
- 2302ef4: `CLAUDE.md` (ezt a Claude Code minden munkamenet elején beolvassa).
- 9ea559f: az élesítés (`npm run deploy`, `wrangler deploy`, D1 `--remote`, KV/R2 írás) kiemelt jóváhagyással.
- A motoros projekthez (`~/Projektek/motoros-projekt`) István kapott egy `CLAUDE.md`-t (több klub, szuperadmin:
  `/superadmin/`, élesítés csak kérésre); annak a repónak nincs GitHub-távolija — javasolt: privát repó, hogy a
  webes Claude is lássa.

**Döntések / tények:**
- Előfizetés: a módosítatlan Claude Code-ba a saját fiókkal bejelentkezni megengedett (Anthropic dokumentáció); a
  FusionAI a tokent nem látja, bejelentkezés: `claude auth login` a Terminálban.
- Nincs D-Bus, nincs háttérszolgáltatás; a FusionAI Claude Code nélkül is elindul (kiírja, mi hiányzik).
- Jogosultság: olvasás a projektben magától; fájlmódosítás és parancs jóváhagyással; commit, push, sudo, telepítés,
  rendszer, élesítés kiemelten (piros, Enter = Elutasítás); a nem commitolt munkát eldobó Git-parancsok és a titkos
  fájlok tiltva. A felhasználói `~/.claude/settings.json` engedélyei a FusionAI-ban nem érvényesek.
- Visszaállítás: pillanatkép a munkamenet elején (`refs/fusion-ai/*`), Visszaállítás gomb, Visszavonás (utolsó kérés).
- A webes Claude a GitHubról látja a repókat, a helyi munkameneteket és a FusionAI memóriáját nem — ezért ez a napló.

**Ellenőrizve:** önteszt (próba-Claude) a fejlesztőgépen; a ZBookon a valódi Claude Code 2.1.311 bejelentkezve,
egy kérdés-válasz a `fusionos` repón (István képernyőképe, 2026-10-27).

**Nyitott (ZBook-próbák, sorban):** fájlmódosítás jóváhagyással (`proba.py`), parancs jóváhagyással, `git reset --hard`
magától elutasítva, commit kiemelt jóváhagyással (Elutasítás), Visszavonás és Visszaállítás, munkamenet folytatása
újraindítás után. Utána a 4. fázis: tesztfuttatás gomb, naplók, jóváhagyott újraindítás, commit/push gomb.

**Nem ide tartozik:** a SolidCraft (külön projekt, pihen; az utolsó javítások a fork `fuzio` ágán: 5175ce9 — K-tényező
hajlításonként, d503430 — NVIDIA 470: hálózás a CPU-n).

## 2026-10-29 — a napló indul (webes Claude)
- FusionAI 0.0.60 a ZBookon fut a valódi Claude Code-dal (2.1.311, claude.ai-bejelentkezés) — István képernyőképe, 2026-10-27.
- Az élesítő parancsok (`npm run deploy`, `wrangler deploy`, `wrangler d1 … --remote`, KV/R2 írás) a FusionAI-ban
  kiemelt (piros) jóváhagyást kérnek.
- Nyitott: a jóváhagyás / tiltás / visszavonás / munkamenet-folytatás próbái a ZBookon (`docs/W3-fusionai.md` 7. pont).
