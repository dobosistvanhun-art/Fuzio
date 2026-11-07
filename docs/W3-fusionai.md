# W3 — FusionAI: Claude Code helyben, a FusionOS-ből (0.0.60)

## 1. Felmérés (2026-10-27)

| Kérdés | Eredmény |
| --- | --- |
| Felület | Python + PyQt6 + QML, a közös `FusionUI` modullal (`desktop/lib/fusion_ui.py`: `create_app`, `load`, `spawn`); egy program = `desktop/<név>/fusion_<név>_app.py` + `qml/` |
| Indítás | `desktop/apps.json` (Start menü, kereső) → `/usr/bin/fusion-<név>` hivatkozás (`rootfs/customize.sh`) |
| D-Bus | a Fúzió API-ban (M8, D1-döntés) egyelőre nincs saját D-Bus-szolgáltatás: Python + parancssor. A FusionAI-nak sem kell |
| Fejlesztői eszközök | `fusion-dev` (root nélkül, a felhasználó mappájába / a DATA-ra: Node.js, Wrangler), a Fejlesztődoboz (Ubuntu 24.04, `fusion-dev box run …`) a fordításhoz |
| Python | a rendszerkép python3-ja (Ubuntu 24.04: 3.12), **pip és venv nélkül**; a rendszerkép csak olvasható |
| Claude Code | hivatalos natív telepítő: `curl -fsSL https://claude.ai/install.sh \| bash` → `~/.local/bin/claude`, `~/.local/share/claude`, root nélkül, magától frissül. Ubuntu 20.04+ / x64 / 4 GB RAM — a ZBook megfelel |
| Bejelentkezés | `claude auth login` (Claude-előfizetés az alapértelmezés), az Anthropic oldalán; a hitelesítő: `~/.claude/.credentials.json` (0600) |
| Programozott elérés | a hivatalos **Claude Agent SDK** (Python, `claude-agent-sdk`, MIT): a telepített `claude`-ot indítja, `ClaudeSDKClient` (folyamatos válasz, `can_use_tool` jóváhagyás, `resume`, `interrupt`, `rewind_files`, `list_sessions`) |

### Előfizetés (Pro/Max) — mit mond az Anthropic

A Claude Code dokumentációja (Legal and compliance, Authentication) szerint:
- a Pro/Max bejelentkezés (OAuth) a Claude Code „szokásos használatára” szolgál; a Pro/Max korlátok **egyéni**
  használatot feltételeznek;
- harmadik fél **nem kínálhat** saját claude.ai-bejelentkezést a saját programjában, és nem gyűjtheti / közvetítheti a
  hitelesítőt; a bejelentkezésnek az Anthropic saját folyamatán kell lezajlania;
- ugyanakkor „nem tiltja, hogy a felhasználó a **módosítatlan Claude Code-ba** a saját előfizetésével jelentkezzen be”.

A FusionAI ehhez igazodik: a módosítatlan, hivatalosan telepített Claude Code-ot indítja; bejelentkezni a Terminálban
kell (`claude auth login`, az Anthropic oldalán); a FusionAI a tokent nem olvassa, nem tárolja, nem továbbítja.
Külön API-kulcs nem kell. Ha a FusionOS-t egyszer más is használná, mindenki a saját fiókjával jelentkezik be — a
FusionAI nem ad tovább előfizetést. (Ez a dokumentáció olvasata, nem jogi vélemény; a feltételek változhatnak.)

## 2. Felépítés

```
FusionAI (QML: desktop/ai/qml/AI.qml)
   │  Backend (Python, fusion_ai_app.py) — külön szál, asyncio
   │  ├─ Claude Agent SDK (~/.local/share/fusion-ai/python)  ──stdin/stdout──▶  claude (~/.local/bin, hivatalos)
   │  │     cwd = a kijelölt repó, permission_mode = default (vagy acceptEdits, ha bekapcsolod)
   │  │     can_use_tool ─▶ fusion_ai_core.classify ─▶ automatikus / jóváhagyó ablak / kiemelt (piros) / tiltva
   │  └─ fusion_ai_core: Git-állapot, diff, pillanatkép (refs/fusion-ai/*), visszaállítás
   └─ Terminál (fusion-terminal): bejelentkezés, telepítés, kézi parancsok
```

Nincs új háttérszolgáltatás, nincs új keretrendszer: a FusionAI egy közönséges Fúzió-program, csak futás közben
indítja a `claude`-ot. Ha a Claude Code nincs telepítve, nincs bejelentkezve vagy nincs internet, a FusionAI ezt
kiírja; a Fúzió többi része nem függ tőle.

## 3. Jogosultságok

Sorrend: előbb a Claude Code saját engedélykezelése (amit magától nem enged, azt kérdezi), majd a FusionAI szabályai
(`fusion_ai_core.classify`), végül a felhasználó.

| Eset | FusionAI |
| --- | --- |
| olvasás a projektben (Read, Grep, Glob) | magától |
| olvasás a projekten kívül | jóváhagyás |
| fájlmódosítás a projektben | jóváhagyás (a régi → új szöveggel); „Fájlmódosítás kérdés nélkül” = a Claude Code hivatalos `acceptEdits` módja, csak az adott munkamenetre |
| fájlmódosítás a projekten kívül / rendszerfájl | **kiemelt** jóváhagyás |
| csak olvasó parancs a projektben (0.0.76): `git status/log/diff/show/for-each-ref`, `ls`, `cat`, `head`, `wc`, `grep`, csővel (`\|`) összefűzve is | magától (részletek: 6b.) |
| parancs (Bash) | jóváhagyás, a teljes parancssorral |
| titkos fájl a projektben (0.0.76): `.dev.vars`, `.env*`, `*.pem`, `*.key` — Read, Grep, Bash | **tiltva** |
| `sudo`, `fusion-admin`, telepítés (apt, pip, npm -g, `fusion-dev install`), `git commit`, `git push`, merge/rebase, `rm -r`, `systemctl`, `kill` … | **kiemelt** jóváhagyás (piros; Enter = Elutasítás) |
| `git reset --hard`, `checkout -- …`, `restore` (munkafa), `clean`, `stash drop/clear`, `push --force`, `branch -D` | **tiltva**, kérdés nélkül (a nem commitolt munka védelme) — ha tényleg kell, kézzel |
| `~/.ssh`, `~/.gnupg`, `~/.claude/.credentials.json`, `~/.git-credentials`, rclone | **tiltva** |
| `bypassPermissions` / `--dangerously-skip-permissions` | soha |

A Claude Code a projekt `.claude/settings.json`-ját és `CLAUDE.md`-jét betölti (`setting_sources=["project"]`); a
felhasználói `~/.claude/settings.json` engedélyei a FusionAI-ban nem érvényesek.

## 4. Visszaállíthatóság

- **Pillanatkép** minden munkamenet elején: a munkafa teljes állapota (követett + új, nem ignorált fájlok) egy
  commit-objektumban, `refs/fusion-ai/<idő>` alatt. Külön indexfájllal készül: a munkafát, az indexet, a stash-t és az
  ágakat nem érinti. Kézzel is: „Pillanatkép most”.
- **Visszaállítás** (Pillanatképek fül): előbb a mostani állapotról is pillanatkép készül, így ez is visszavonható; a
  pillanatkép óta keletkezett új fájlok megmaradnak (a felület felsorolja őket).
- **Visszavonás** gomb (0.0.64-től): minden kérés előtt pillanatkép készül (ha az állapot nem változott, nem új); a
  gomb a munkafát erre állítja vissza — a Claude parancsokkal (Bash) végzett módosításait is, amelyeket a Claude Code
  saját `rewind_files`-a nem követ. A kérés óta keletkezett új fájlok megmaradnak (a FusionAI kiírja őket).
- Parancssorból: `git for-each-ref refs/fusion-ai` · `git diff <sha>` · `git restore --source=<sha> --worktree -- .`
  (előtte érdemes a mostani állapotot commitolni vagy pillanatképezni) · törlés: `git update-ref -d refs/fusion-ai/<név>`.

## 5. Telepítés és első indítás (ZBook)

```sh
fusion-dev install claude          # Claude Code (hivatalos telepítő) + Claude Agent SDK; root nélkül
claude auth login                  # egyszer: a Claude Pro/Max fiókoddal, a böngészőben
fusion-ai                          # 0.0.60-tól a Start menüben: Rendszer → FusionAI
```

A 0.0.60-as frissítés előtt a forrásfából is fut (a rendszer nem változik):
`python3 ~/Projektek/fusionos/desktop/ai/fusion_ai_app.py ~/Projektek/fusionos`

Eltávolítás: `fusion-dev remove claude` (a `~/.claude` — bejelentkezés, munkamenetek — megmarad; előtte
`claude auth logout`, ha kell). A FusionAI beállításai: `~/.config/fusion/ai.json`.

## 6. Ellenőrzés

| Mit | Hol | Eredmény |
| --- | --- | --- |
| `fusion-ai --selftest`: indítás, folyamatos válasz, munkamenet-azonosító, pillanatkép, Edit-jóváhagyás és a módosítás, diff, `git reset --hard` magától elutasítva (a munka megmaradt), commit kiemelt jóváhagyással elutasítva (nincs commit), visszaállítás és annak visszavonhatósága, folytatás `--resume`-mal, a CLI-argumentumok (default mód, a repó a munkamappa, nincs bypass), 14 besorolási eset | fejlesztőgép, **próba-Claude-dal** (`desktop/ai/tests/fake-claude` — a Claude Code SDK-felületét utánozza, nem AI) | ok |
| `fusion-dev install claude` → `status` → `remove claude` | fejlesztőgép, a telepítő helyett próba-szkripttel; a pip (a kerékből) és az SDK a valódi PyPI-ról, Python 3.13 | ok |
| a felület (QML) | fejlesztőgép, offscreen képernyőképek: beszélgetés, jóváhagyás, kiemelt jóváhagyás, diff | ok |
| **valódi Claude Code + Pro/Max bejelentkezés**, jóváhagyás, tiltás, kiemelt jóváhagyás, Commit/Push, Visszavonás, munkamenet-folytatás | ZBook | **ok (István, 2026-10-29)** |
| Python 3.12 (Ubuntu 24.04) alatt a pip-es SDK-telepítés | ZBook | **nincs ellenőrizve** |
| a Claude Code hivatalos telepítője a Fúzión | ZBook | **nincs ellenőrizve** |

## 6a. 0.0.61 — a teljes munkafolyamat (4. fázis)

A középső sáv gombjai (ezeket te indítod, nem a Claude — ezért nem kérnek jóváhagyó ablakot; a Claude ugyanezeket csak
jóváhagyással futtathatja):

| Gomb | Mit csinál |
| --- | --- |
| Teszt | a projekt tesztparancsa a projekt mappájában; a kimenet a Napló fülön, az eredmény (és az utolsó sorok) a beszélgetésben |
| Naplók | `journalctl --user` (300 sor), a rendszernapló figyelmeztetései és hibái (ebben az indításban), a Fúzió-programok naplói |
| Kimenet → Claude | az utolsó teszt- / naplókimenet (legfeljebb 150 sor) elküldése Claude-nak: „mi a hiba oka, javasolj javítást” |
| Újraindítás… | a projekt saját újraindító parancsa, megerősítés után, a FusionAI-tól függetlenül indítva |
| Commit… | a változott fájlok listája, a szerző, a te üzeneted; `git add -A` + `git commit`, előtte pillanatkép; Git-szerző nélkül érthető hiba |
| Push… | a feltöltendő commitok listája és a cél; `git push` (upstream nélkül `-u origin <ág>`), **soha nem --force** |
| Beállítások | projektenként a teszt- és az újraindító parancs (`~/.config/fusion/ai.json`); javaslat: Cargo → `fusion-dev box run cargo test`, npm → `npm test`, a Fúzió repó → a FusionAI öntesztje |

Biztonság (0.0.61): a FusionAI szabályai a Claude Code **PreToolUse-horgaként** is futnak, így a tiltott parancs
akkor is tilos, a kiemelt (commit, push, sudo, élesítés) akkor is kérdez, ha egy Claude Code-szabály (pl. a projekt
`.claude/settings.json`-ja) magától engedné. ZBookon igazolva (2026-10-29): commit-kérésre piros ablak, Elutasításra
nincs commit.

## 6b. 0.0.76 — git pull, csak olvasó parancsok, titkos fájlok, kiférő jóváhagyó ablak

**Pull gomb** (`fusion_ai_core.pull`): `git fetch`, majd `git pull --ff-only`, de csak ha
- nincs nem commitolt munka (új, nem követett fájl sem);
- van kijelölt ág, van távoli párja, és ez a távoli tároló fő ága (`origin/HEAD`, ha nincs: `main` / `master`);
- a helyi ág nem tért el (csak a távolin van új commit).

Különben nem húz, és kiírja, miért. Sikeres pull után a beszélgetésben: az új commitok, a fájlok száma, és ha a
`CLAUDE.md` / `docs/ATADAS.md` változott, az külön; a Claude a következő kéréssel megjegyzést kap („olvasd újra: …”).
Projekt-beállítások → „Projekt megnyitásakor és új munkamenetnél magától git pull” (alapból ki; `~/.config/fusion/ai.json`,
`settings.<repo>.autoPull`). Pull közben a Küldés vár.

**Csak olvasó parancsok kérdés nélkül** (`_safe_readonly`). Egy parancs akkor fut magától, ha:
- egyszerű szavakból áll, legfeljebb `|`-vel összefűzve, és minden tagja engedélyezett. Más shell-szerkezetnél
  (`&&`, `||`, `;`, `&`, `<`, `>`, `$( )`, `$VÁLTOZÓ`, fordított aposztróf, `{ }`, `~`, `#`, `\`, új sor) jóváhagyás kell;
- a git-tagok közvetlenül `status`, `log`, `diff`, `show` vagy `for-each-ref` alparanccsal kezdődnek: a git saját
  kapcsolói (`-c`, `-C`, `--no-pager`) is jóváhagyósak. Jóváhagyás kell `--output`, `-o`, `--ext-diff`, `--no-index`,
  valamint `c`, `o` vagy `O` betűt tartalmazó rövid kapcsoló esetén is (pl. `-c`, `-pc`);
- a többi tag csak `ls`, `cat`, `head`, `wc` vagy `grep`: minden fájl-argumentum (a `--kapcsoló=érték` értéke is) a
  projekten belül van. A `grep` bejárós (`-r`, `-R`, `--recursive`), mintafájlos (`-f`) és eszközös (`-d`, `-D`) kapcsolója
  jóváhagyós. A nem idézett `*` / `?` csak egyszerű kiterjesztés-mintában mehet (pl. `src/*/*.py`), a `.`-tal kezdődő
  minta, a `[ ]` és a `..` jóváhagyós (pl. `cat *`, `ls .*`). A `find` (`-exec`), `sort`, `tee`, `sh`, `echo` stb.
  továbbra is kérdez.

**Titkos fájlok a projektben**: a `.dev.vars`, `.env*`, `*.pem`, `*.key` olvasása tiltva: a Read (út), a Grep (`path`
vagy `glob`) és minden Bash-parancs, amely ilyen nevet tartalmaz (pl. `cat .dev.vars`, `git show HEAD:.env`,
`cp .env /tmp`). Szerkesztésük (Edit/Write) a régi módon jóváhagyással megy.
**Korlát:** egy út nélküli, a teljes projektre futó Grep-keresés ezek tartalmát nem zárja ki. A rejtett fájlokat
(`.env`, `.dev.vars`) a ripgrep alapból kihagyja, ezt a Claude Code Grep-jére nem ellenőriztem. A `*.pem` / `*.key`
nem rejtett, ezért az ilyen keresés tartalmukat elérheti.
**Téves találat** (tiltás ott, ahol nem kellene): egy `grep 'obj.key'` mintában a `.key` végződés is tiltást vált ki.

**Jóváhagyó ablak**: az összefoglaló legfeljebb 3, az ok legfeljebb 2 sor (a végén …). A részletek doboza legfeljebb
`win.height - 320` (és legfeljebb 320) magas, görgethető, és ott a teljes parancs olvasható. Mérés (offscreen, 400 szavas
parancs + 300 soros részletek, kiemelt jóváhagyás): 1180×760-nál az ablak y=76, magassága 609; 860×520-nál y=16,
magassága 489. A gombok mindkét méretnél az ablakon belül vannak.

**Induló utasítás**: „Fúzió” (nem FusionOS), a Tab-szabály, a csak olvasó parancsok és a titkos fájlok minden projektben.
A gépre (ZBook, NVIDIA 470) és a Fúzió-forrásra vonatkozó sor csak a Fúzió repójában szerepel; más projektben az a
sor, hogy a Fúzió saját szabályai ott nem érvényesek.

| Mit | Hol | Eredmény |
| --- | --- | --- |
| `fusion-ai --selftest` (167 ellenőrzés): a korábbiak + PULL (siker, CLAUDE.md-jelzés, Claude-megjegyzés), naprakész, nem commitolt munka, magától (új munkamenet), más ág, eltérés; PROMPT; 106 besorolási eset (`tests/classify_cases.py`); UI (`tests/ui_check.py`, a jóváhagyó ablak két ablakméretnél) | ZBook, forrásból, próba-Claude-dal (2026-11-05) | ok |
| a Pull gomb a valódi GitHub-repón, a kiférő ablak és a kérdés nélküli olvasó parancsok a valódi Claude Code-dal | ZBook, telepített 0.0.76 | **nincs ellenőrizve** |

## 6c. 0.0.77 — Pull a saját távoli ágról, Fordítás és telepítés

**Pull**: a fő ágon kívül az az ág is húzható, amely a saját, azonos nevű távoli párját követi (pl. a SolidCraft
`fuzio` → `origin/fuzio`). Más nevű távoli ágat követő ágon (`masnevu` → `origin/mellek`) nem húz, csak szól. A többi
feltétel (nem commitolt munka, eltérés) változatlan.

**Fordítás és telepítés** gomb (csak ha van fordító parancs): a Projekt-beállítások két új mezője, „Fordító parancs” és
„Telepítő parancs” (`settings.<repo>.build` / `.install`). Ha a projektben van `scripts/fuzio-build.sh`, a javaslat:
`bash scripts/fuzio-build.sh --no-install` és `bash scripts/fuzio-build.sh --install` (a SolidCraftnál: fordítás a
Fejlesztődobozban, majd `fusion-programs install … --name SolidCraft`; ugyanazzal a névvel a meglévő program frissül,
a Start menü bejegyzése az új változatot indítja). A gomb a fordítást a Napló fülre írja (legfeljebb 4 óra), sikeres
fordítás után megkérdezi: „Telepítsem?”; hibás fordítás után nem kérdez. A Claude futása közben nem indul.

| Mit | Hol | Eredmény |
| --- | --- | --- |
| `fusion-ai --selftest`: PULL-OWN-BRANCH, PULL-BRANCH (más nevű távoli ág), PULL-DIVERGED; DETECT-BUILD, BUILD-SAVED, BUILD-KEPT, BUILD (kérdez), INSTALL, BUILD-FAIL (nem kérdez); UI | felhőben, forrásból, próba-Claude-dal (2026-11-07) | ok |
| a SolidCraft `--no-install` / `--install` módja helyettesítő `fusion-dev` / `fusion-programs` paranccsal | felhőben | ok |
| a valódi SolidCraft-fordítás a Fejlesztődobozban a gombról, a telepítés és a Start menü | ZBook, telepített 0.0.77 | **nincs ellenőrizve** |

## 7. Következő lépések

1. ZBook: telepítés, bejelentkezés, egy valódi hibakeresési feladat egy repón; a munkamenet folytatása; egy elutasított
   és egy engedélyezett parancs.
2. Tapasztalat alapján: a besorolási szabályok finomítása (mit kérdezzen kevésbé / jobban).
3. ~~4. lépés~~ — kész a 0.0.61-ben (6a. fejezet); ZBook-próba hátra.
