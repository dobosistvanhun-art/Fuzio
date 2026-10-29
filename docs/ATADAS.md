# Átadási napló (ZBook ⇄ claude.ai)

Kétirányú napló: a helyben (FusionAI / Claude Code) és a webes Claude-dal (claude.ai) végzett munka összefoglalója,
hogy a másik oldal folytatni tudja. Mindkét oldal ide ír; a legfrissebb felül. A FusionAI a munkamenet elején a
legfelső bejegyzéseket olvassa el. Szabály: `CLAUDE.md` → „Átadás”.

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
