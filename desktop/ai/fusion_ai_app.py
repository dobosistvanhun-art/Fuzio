#!/usr/bin/python3
"""Fúzió — FusionAI: fejlesztőasszisztens a helyi Git-repókon (a hivatalos Claude Code-dal)

    fusion-ai                 az ablak (ha már fut: előre hozza)
    fusion-ai <mappa>         az ablak, a megadott projekttel
    fusion-ai --selftest      önteszt a próba-Claude-dal (tests/fake-claude): indítás, folyamatos válasz,
                              jóváhagyás, tiltott parancs, pillanatkép és visszaállítás, munkamenet folytatása

A Claude Code a felhasználó saját bejelentkezésével fut (Pro/Max előfizetés: `claude auth login` a Terminálban,
az Anthropic saját bejelentkezésével); a FusionAI a jelszót vagy a tokent nem látja és nem tárolja.
Telepítés: fusion-dev install claude. Ha a Claude Code nincs telepítve vagy nincs internet, a FusionAI ezt
kiírja, a Fúzió többi része ettől független.
"""
import asyncio
import os
import sys
import threading
import time
import traceback

HERE = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))
sys.path.insert(0, HERE)
import fusion_ai_core as core  # noqa: E402

if "--selftest" not in sys.argv:
    import fusion_ui as ui  # noqa: E402
from PyQt6.QtCore import QObject, QTimer, pyqtProperty, pyqtSignal, pyqtSlot  # noqa: E402

LOG_CAP = 2000          # naplósorok száma a felületen


class Backend(QObject):
    """a QML ezt látja: projekt, munkamenet, üzenetek, jóváhagyások, diff, pillanatképek"""
    changed = pyqtSignal()
    item = pyqtSignal("QVariant")                 # új üzenet a beszélgetésben
    delta = pyqtSignal(str)                       # folyamatos válasz: szövegdarab az utolsó üzenethez
    permission = pyqtSignal("QVariant")           # jóváhagyás kell: {id, tool, level, why, summary, detail}
    message = pyqtSignal(str, bool)               # állapotsor: szöveg, hiba-e
    logLine = pyqtSignal(str)

    def __init__(self, project=""):
        super().__init__()
        self._sdk, self._sdk_err = core.load_sdk()
        self._status = {}
        self._project = ""
        self._projects = []
        self._sessions = []
        self._session = ""
        self._busy = False
        self._connected = False
        self._accept_edits = False
        self._diff = ""
        self._git = {}
        self._snaps = []
        self._last_user_uuid = ""
        self._pending = {}                        # jóváhagyás azonosító → asyncio.Future
        self._client = None
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._loop.run_forever, daemon=True)
        self._thread.start()
        self.refresh()
        if project:
            self.openProject(project)
        else:
            last = core.load_config().get("last_project", "")
            if last and core.is_repo(last):
                self.openProject(last)

    # ------------------------------------------------------------ tulajdonságok

    @pyqtProperty("QVariant", notify=changed)
    def status(self):
        s = dict(self._status)
        s["sdk"] = self._sdk is not None
        s["sdkError"] = self._sdk_err
        return s

    @pyqtProperty("QVariant", notify=changed)
    def projects(self):
        return self._projects

    @pyqtProperty(str, notify=changed)
    def project(self):
        return self._project

    @pyqtProperty("QVariant", notify=changed)
    def sessions(self):
        return self._sessions

    @pyqtProperty(str, notify=changed)
    def session(self):
        return self._session

    @pyqtProperty(bool, notify=changed)
    def busy(self):
        return self._busy

    @pyqtProperty(bool, notify=changed)
    def acceptEdits(self):
        return self._accept_edits

    @pyqtProperty(str, notify=changed)
    def diff(self):
        return self._diff

    @pyqtProperty("QVariant", notify=changed)
    def git(self):
        return self._git

    @pyqtProperty("QVariant", notify=changed)
    def snaps(self):
        return self._snaps

    @pyqtProperty(bool, notify=changed)
    def canUndoTurn(self):
        return bool(self._last_user_uuid) and self._connected and not self._busy

    # ------------------------------------------------------------ műveletek (QML)

    @pyqtSlot()
    def refresh(self):
        self._status = core.cli_status()
        self._projects = core.projects()
        self.changed.emit()

    @pyqtSlot(str)
    def openProject(self, path):
        path = os.path.realpath(os.path.expanduser(path))
        if not core.is_repo(path):
            self.message.emit(f"nem Git-repó: {path}", True)
            return
        if path not in [p["path"] for p in self._projects]:
            core.add_project(path)
            self._projects = core.projects()
        self._close_client()
        self._project, self._session, self._last_user_uuid = path, "", ""
        cfg = core.load_config()
        cfg["last_project"] = path
        core.save_config(cfg)
        self.refreshSessions()
        self.refreshGit()
        self.item.emit({"kind": "info", "text": f"Projekt: {path}"})

    @pyqtSlot()
    def refreshSessions(self):
        self._sessions = []
        if self._sdk is not None and self._project:
            try:
                for s in self._sdk.list_sessions(directory=self._project, limit=30):
                    self._sessions.append({"id": s.session_id, "title": (s.summary or "")[:90],
                                           "when": time.strftime("%m.%d. %H:%M", time.localtime(s.last_modified / 1000))})
            except Exception as e:
                self._log(f"a munkamenetek listája nem olvasható: {e}")
        self.changed.emit()

    @pyqtSlot()
    def refreshGit(self):
        if self._project:
            self._git = core.git_state(self._project)
            self._diff = core.git_diff(self._project)
            self._snaps = core.snapshots(self._project)[:30]
        self.changed.emit()

    @pyqtSlot()
    def newSession(self):
        self._close_client()
        self._session, self._last_user_uuid = "", ""
        self.item.emit({"kind": "info", "text": "Új munkamenet"})
        self.changed.emit()

    @pyqtSlot(str)
    def resumeSession(self, sid):
        self._close_client()
        self._session, self._last_user_uuid = sid, ""
        self.item.emit({"kind": "info", "text": f"Munkamenet folytatása: {sid[:8]}…"})
        self.changed.emit()

    @pyqtSlot(str)
    def send(self, text):
        text = text.strip()
        if not text:
            return
        if self._busy:
            self.message.emit("Claude még dolgozik — várj, vagy állítsd le", True)
            return
        if not self._project:
            self.message.emit("előbb válassz projektet", True)
            return
        if self._sdk is None:
            self.message.emit("hiányzik a Claude Agent SDK: fusion-dev install claude", True)
            return
        if not self._status.get("installed"):
            self.message.emit("a Claude Code nincs telepítve: fusion-dev install claude", True)
            return
        self._busy = True
        self.changed.emit()
        self.item.emit({"kind": "user", "text": text})
        asyncio.run_coroutine_threadsafe(self._turn(text), self._loop)

    @pyqtSlot()
    def stop(self):
        if self._client is not None:
            asyncio.run_coroutine_threadsafe(self._interrupt(), self._loop)
        for fut in list(self._pending.values()):
            self._loop.call_soon_threadsafe(self._resolve, fut, False, "a felhasználó leállította")

    @pyqtSlot(str, bool, str)
    def answer(self, pid, allow, note):
        fut = self._pending.pop(pid, None)
        if fut is not None:
            self._loop.call_soon_threadsafe(self._resolve, fut, allow, note)

    @pyqtSlot(bool)
    def setAcceptEdits(self, on):
        """a Claude Code hivatalos „acceptEdits” módja: a projekten belüli fájlmódosítások kérdés nélkül
        (a parancsok továbbra is jóváhagyással). Csak erre a munkamenetre szól."""
        self._accept_edits = bool(on)
        self.changed.emit()
        if self._client is not None:
            asyncio.run_coroutine_threadsafe(self._set_mode(), self._loop)

    @pyqtSlot()
    def takeSnapshot(self):
        if self._project:
            r = core.snapshot(self._project, "(kézi)")
            self.message.emit("pillanatkép: " + (r["ref"] or r["error"]), bool(r["error"]))
            self.refreshGit()

    @pyqtSlot(str)
    def restoreSnapshot(self, sha):
        if not self._project or self._busy:
            return
        r = core.restore(self._project, sha)
        if r["ok"]:
            extra = (" — a pillanatkép óta keletkezett fájlok megmaradtak: " + ", ".join(r["extra"][:8])) if r["extra"] else ""
            self.message.emit(f"visszaállítva; az előző állapot: {r['before']}{extra}", False)
            self.item.emit({"kind": "info", "text": f"Visszaállítás a pillanatképre {sha[:8]} (az előző állapot mentve: {r['before']})"})
        else:
            self.message.emit("a visszaállítás nem sikerült: " + r["error"], True)
        self.refreshGit()

    @pyqtSlot()
    def undoTurn(self):
        """az utolsó kérés óta a Claude által végzett fájlmódosítások visszavonása (Claude Code: rewind_files)"""
        if self._client is not None and self._last_user_uuid and not self._busy:
            asyncio.run_coroutine_threadsafe(self._rewind(self._last_user_uuid), self._loop)

    @pyqtSlot()
    def login(self):
        """bejelentkezés: a Claude Code saját folyamata a Terminálban (a FusionAI nem látja a hitelesítőt)"""
        if not self._status.get("installed"):
            ui.spawn(["fusion-terminal", "-t", "Claude Code telepítése", "-e", "sh", "-c",
                      "fusion-dev install claude; echo; echo 'Enter: tovább a bejelentkezéshez'; read _; "
                      f"{core.CLI} auth login; echo; echo 'Kész. (Enter: bezárás)'; read _"])
        else:
            ui.spawn(["fusion-terminal", "-t", "Claude Code bejelentkezés", "-e", "sh", "-c",
                      f"{core.CLI} auth login; echo; echo 'Kész. (Enter: bezárás)'; read _"])

    @pyqtSlot()
    def openTerminal(self):
        if self._project:
            ui.spawn(["fusion-terminal", "-t", "FusionAI — " + os.path.basename(self._project),
                      f"--working-directory={self._project}"])

    # ------------------------------------------------------------ a Claude Code-szál (asyncio)

    def _log(self, text):
        self.logLine.emit(time.strftime("%H:%M:%S ") + text.rstrip())

    def _resolve(self, fut, allow, note):
        if not fut.done():
            fut.set_result((allow, note))

    def _options(self):
        sdk = self._sdk
        return sdk.ClaudeAgentOptions(
            cwd=self._project,
            cli_path=core.CLI,
            permission_mode="acceptEdits" if self._accept_edits else "default",
            can_use_tool=self._can_use_tool,
            resume=self._session or None,
            include_partial_messages=True,
            enable_file_checkpointing=True,
            extra_args={"replay-user-messages": None},
            setting_sources=["project"],
            system_prompt={"type": "preset", "preset": "claude_code", "append": core.system_prompt(self._project)},
            stderr=lambda ln: self._log("claude: " + ln),
            # a FusionAI szabályai minden eszközhívás előtt (PreToolUse-horog): a tiltott tilos, a kiemelt mindig
            # kérdez — akkor is, ha a Claude Code egy szabálya (pl. a projekt .claude/settings.json-ja) magától engedné
            hooks={"PreToolUse": [sdk.HookMatcher(matcher=None, hooks=[self._pre_tool_use])]},
        )

    async def _ensure_client(self):
        if self._client is None:
            snap = core.snapshot(self._project, "(munkamenet eleje)")
            if snap["ref"]:
                self.item.emit({"kind": "info", "text": f"Pillanatkép a munkamenet elején: {snap['ref']}"})
            client = self._sdk.ClaudeSDKClient(self._options())
            await client.connect()
            self._client, self._connected = client, True

    async def _turn(self, text):
        sdk = self._sdk
        try:
            await self._ensure_client()
            await self._client.query(text)
            streaming = False
            async for msg in self._client.receive_response():
                if isinstance(msg, sdk.StreamEvent):
                    ev = msg.event or {}
                    if ev.get("type") == "content_block_delta" and (ev.get("delta") or {}).get("type") == "text_delta":
                        if not streaming:
                            self.item.emit({"kind": "assistant", "text": ""})
                            streaming = True
                        self.delta.emit(ev["delta"].get("text", ""))
                elif isinstance(msg, sdk.SystemMessage):
                    if msg.subtype == "init":
                        sid = (msg.data or {}).get("session_id", "")
                        if sid and sid != self._session:
                            self._session = sid
                            self.changed.emit()
                elif isinstance(msg, sdk.AssistantMessage):
                    for b in msg.content:
                        if isinstance(b, sdk.TextBlock):
                            if not streaming:
                                self.item.emit({"kind": "assistant", "text": b.text})
                        elif isinstance(b, sdk.ToolUseBlock):
                            c = core.classify(b.name, b.input, self._project)
                            self.item.emit({"kind": "tool", "text": c["summary"][:400], "tool": b.name})
                    streaming = False
                elif isinstance(msg, sdk.UserMessage):
                    if isinstance(msg.content, str) and msg.uuid:
                        self._last_user_uuid = msg.uuid
                    elif isinstance(msg.content, list):
                        for b in msg.content:
                            if isinstance(b, sdk.ToolResultBlock) and b.is_error:
                                t = b.content if isinstance(b.content, str) else str(b.content)
                                self.item.emit({"kind": "error", "text": t[:1000]})
                elif isinstance(msg, sdk.ResultMessage):
                    if msg.session_id:
                        self._session = msg.session_id
                    if msg.is_error:
                        self.item.emit({"kind": "error", "text": f"Claude Code: {msg.result or msg.subtype}"})
                    secs = (msg.duration_ms or 0) / 1000
                    self.item.emit({"kind": "result", "text": f"kész — {msg.num_turns} lépés, {secs:.0f} mp"})
        except Exception as e:
            self._log(traceback.format_exc())
            self.item.emit({"kind": "error", "text": self._explain(e)})
            await self._drop_client()
        finally:
            self._busy = False
            self.changed.emit()
            self.refreshSessionsLater.emit()
            self.refreshGitLater.emit()

    refreshSessionsLater = pyqtSignal()
    refreshGitLater = pyqtSignal()

    def _explain(self, e):
        s = f"{type(e).__name__}: {e}"
        low = s.lower()
        if "not logged in" in low or "login" in low or "authenticat" in low or "401" in low:
            return "A Claude Code nincs bejelentkezve — Bejelentkezés gomb (claude auth login). " + s[:300]
        if "getaddrinfo" in low or "network" in low or "connection" in low or "enotfound" in low:
            return "Nincs kapcsolat a Claude szolgáltatással (internet?). " + s[:300]
        if "cli not found" in low or "no such file" in low:
            return "A Claude Code nem található: fusion-dev install claude. " + s[:300]
        return s[:1500]

    async def _pre_tool_use(self, data, tool_use_id, ctx):
        data = data if isinstance(data, dict) else {}
        c = core.classify(str(data.get("tool_name") or ""), data.get("tool_input") or {}, self._project)
        if c["level"] == "deny":
            self.item.emit({"kind": "denied", "text": f"{c['summary'][:300]} — {c['why']}"})
            return {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                           "permissionDecisionReason": f"A FusionAI ezt nem engedi: {c['why']}"}}
        if c["level"] == "danger":
            return {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "ask",
                                           "permissionDecisionReason": f"kiemelt jóváhagyás: {c['why']}"}}
        return {}

    async def _can_use_tool(self, tool, inp, ctx):
        sdk = self._sdk
        c = core.classify(tool, inp, self._project)
        if c["level"] == "auto":
            return sdk.PermissionResultAllow()
        if c["level"] == "deny":
            self.item.emit({"kind": "denied", "text": f"{c['summary'][:300]} — {c['why']}"})
            return sdk.PermissionResultDeny(message=f"A FusionAI ezt nem engedi: {c['why']}")
        pid = f"p{time.monotonic_ns()}"
        fut = self._loop.create_future()
        self._pending[pid] = fut
        self.permission.emit({"id": pid, "tool": tool, "level": c["level"], "why": c["why"], "summary": c["summary"],
                              "detail": core.describe(tool, inp),
                              "reason": str(getattr(ctx, "decision_reason", "") or getattr(ctx, "description", "") or "")})
        allow, note = await fut
        self._pending.pop(pid, None)
        if allow:
            self.item.emit({"kind": "allowed", "text": c["summary"][:300]})
            return sdk.PermissionResultAllow()
        self.item.emit({"kind": "denied", "text": c["summary"][:300] + (f" — {note}" if note else "")})
        return sdk.PermissionResultDeny(message="A felhasználó nem engedélyezte." + (f" Megjegyzés: {note}" if note else ""))

    async def _interrupt(self):
        try:
            if self._client is not None:
                await self._client.interrupt()
        except Exception as e:
            self._log(f"megszakítás: {e}")

    async def _set_mode(self):
        try:
            await self._client.set_permission_mode("acceptEdits" if self._accept_edits else "default")
        except Exception as e:
            self._log(f"jogosultsági mód: {e}")

    async def _rewind(self, uuid):
        try:
            await self._client.rewind_files(uuid)
            self.item.emit({"kind": "info", "text": "Az utolsó kérés fájlmódosításai visszavonva."})
            self._last_user_uuid = ""
        except Exception as e:
            self.item.emit({"kind": "error", "text": f"a visszavonás nem sikerült: {e}"})
        self.refreshGitLater.emit()
        self.changed.emit()

    async def _drop_client(self):
        c, self._client, self._connected = self._client, None, False
        if c is not None:
            try:
                await c.disconnect()
            except Exception as e:
                self._log(f"lezárás: {e}")

    def _close_client(self):
        for fut in list(self._pending.values()):
            self._loop.call_soon_threadsafe(self._resolve, fut, False, "a munkamenet lezárult")
        self._pending.clear()
        if self._client is not None:
            f = asyncio.run_coroutine_threadsafe(self._drop_client(), self._loop)
            try:
                f.result(timeout=10)
            except Exception:
                pass

    def shutdown(self):
        self._close_client()
        self._loop.call_soon_threadsafe(self._loop.stop)


def wire(be):
    be.refreshSessionsLater.connect(be.refreshSessions)
    be.refreshGitLater.connect(be.refreshGit)


# ---------------------------------------------------------------- önteszt

def selftest():
    """a próba-Claude-dal (nem a valódi Claude Code-dal!) — a FusionAI csővezetékét ellenőrzi"""
    import shutil
    import subprocess
    import tempfile
    from PyQt6.QtCore import QCoreApplication
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QCoreApplication(sys.argv)
    tmp = tempfile.mkdtemp(prefix="fusion-ai-test-")
    os.environ["HOME"] = tmp
    repo = os.path.join(tmp, "Projektek", "proba")
    os.makedirs(repo)
    core.CLI = os.environ.get("FUSION_AI_CLI") or os.path.join(HERE, "tests", "fake-claude")
    core.CONFIG = os.path.join(tmp, "ai.json")
    core.PROJECT_ROOTS = [os.path.join(tmp, "Projektek")]
    ok = True

    def check(name, cond, extra=""):
        nonlocal ok
        print(f"FUSION-AI: {name} {'ok' if cond else 'HIBA'}{(' ' + extra) if extra else ''}", flush=True)
        ok = ok and bool(cond)

    g = ["git", "-C", repo, "-c", "user.name=t", "-c", "user.email=t@t"]
    subprocess.run(["git", "init", "-q", repo], check=True)
    open(os.path.join(repo, "calc.py"), "w").write("def add(a, b):\n    return a - b\n")
    subprocess.run(g + ["add", "."], check=True)
    subprocess.run(g + ["commit", "-qm", "kezdet"], check=True)
    open(os.path.join(repo, "jegyzet.txt"), "w").write("nem commitolt munka\n")       # nem követett fájl

    be = Backend(repo)
    wire(be)
    items, perms = [], []
    be.item.connect(lambda d: items.append(dict(d)))
    be.delta.connect(lambda t: items.append({"kind": "delta", "text": t}))

    def on_perm(p):
        perms.append(dict(p))
        be.answer(p["id"], perms_allow[0], "")
    perms_allow = [True]
    be.permission.connect(on_perm)

    def wait_idle(sec=30):
        t0 = time.monotonic()
        while time.monotonic() - t0 < sec:
            app.processEvents()
            if not be.busy:
                app.processEvents()
                return True
            time.sleep(0.02)
        return False

    check("CLI", be.status.get("installed") and be.status.get("loggedIn"), str(be.status.get("version")))
    check("SDK", be.status.get("sdk"), be.status.get("sdkError", ""))
    check("PROJECTS", any(p["path"] == os.path.realpath(repo) for p in be.projects))

    be.send("Mi van a projektben?")
    check("TURN1", wait_idle())
    streamed = "".join(i["text"] for i in items if i["kind"] == "delta")
    check("STREAM", "calc.py" in streamed and "jegyzet.txt" in streamed, repr(streamed[:80]))
    sid = be.session
    check("SESSION", len(sid) > 10, sid[:8])
    check("SNAPSHOT", len(core.snapshots(repo)) >= 1)
    snap0 = core.snapshots(repo)[-1]["sha"]

    be.send("Javítsd ki az add függvényt")
    check("TURN2", wait_idle())
    check("PERM-ASKED", any(p["tool"] == "Edit" and p["level"] == "ask" for p in perms))
    check("EDITED", "return a + b" in open(os.path.join(repo, "calc.py")).read())
    be.refreshGit()
    check("DIFF", "+    return a + b" in be.diff and "jegyzet.txt" in be.diff)

    perms.clear()
    be.send("Töröld az összes változást")
    check("TURN3", wait_idle())
    check("DENY-AUTO", not perms and any(i["kind"] == "denied" and "reset --hard" in i["text"] for i in items))
    check("WORK-KEPT", os.path.exists(os.path.join(repo, "jegyzet.txt")) and "a + b" in open(os.path.join(repo, "calc.py")).read())

    perms_allow[0] = False
    be.send("commit")
    check("TURN4", wait_idle())
    check("COMMIT-DANGER", any(p["level"] == "danger" and "commit" in p["summary"] for p in perms))
    _, log, _ = core.git(repo, "log", "--oneline")
    check("NO-COMMIT", len(log.splitlines()) == 1)

    # visszaállítás a munkamenet eleji pillanatképre: a javítás eltűnik, a jegyzet marad, a mostani állapot mentve
    r = core.restore(repo, snap0)
    check("RESTORE", r["ok"] and "return a - b" in open(os.path.join(repo, "calc.py")).read()
          and os.path.exists(os.path.join(repo, "jegyzet.txt")), r.get("error", ""))
    before = core.git(repo, "show", f"{r.get('before', '')}:calc.py")[1]
    check("RESTORE-UNDOABLE", "return a + b" in before)

    # munkamenet folytatása (új kapcsolat, --resume)
    be.newSession()
    be.resumeSession(sid)
    items.clear()
    be.send("Mi van a projektben?")
    check("TURN5", wait_idle())
    streamed = "".join(i["text"] for i in items if i["kind"] == "delta")
    check("RESUME", "korábbi kérés" in streamed and be.session == sid, repr(streamed[:60]))
    import json as _j
    last = _j.load(open(os.path.join(tmp, ".cache", "fake-claude", "last-args.json")))
    a = last["args"]
    check("ARGS", "--permission-mode" in a and a[a.index("--permission-mode") + 1] == "default"
          and os.path.realpath(last["cwd"]) == os.path.realpath(repo)
          and not any(x in a for x in ("bypassPermissions", "--dangerously-skip-permissions")), " ".join(a)[:200])

    # osztályozás: néhány kézi eset
    cases = [("Bash", {"command": "git checkout -- ."}, "deny"), ("Bash", {"command": "git restore src/a.rs"}, "deny"),
             ("Bash", {"command": "git restore --staged a.rs"}, "ask"), ("Bash", {"command": "sudo apt install x"}, "danger"),
             ("Bash", {"command": "cargo test"}, "ask"), ("Bash", {"command": "git push origin main"}, "danger"),
             ("Bash", {"command": "git push -f origin x"}, "deny"), ("Read", {"file_path": "/etc/passwd"}, "ask"),
             ("Edit", {"file_path": "/etc/fstab"}, "danger"), ("Read", {"file_path": os.path.join(core.HOME, ".ssh", "id_ed25519")}, "deny"),
             ("Read", {"file_path": "calc.py"}, "auto"), ("Write", {"file_path": "uj.py"}, "ask"),
             ("Bash", {"command": "cat ~/.ssh/id_rsa"}, "deny"), ("Bash", {"command": "rm -rf build"}, "danger"),
             ("Bash", {"command": "npm run deploy"}, "danger"), ("Bash", {"command": "npx wrangler deploy"}, "danger"),
             ("Bash", {"command": "npx wrangler d1 migrations apply motoros-tura-db --remote"}, "danger"),
             ("Bash", {"command": "npx wrangler d1 migrations apply motoros-tura-db --local"}, "ask"),
             ("Bash", {"command": "npm test"}, "ask")]
    for tool, inp, want in cases:
        got = core.classify(tool, inp, repo)["level"]
        check(f"CLASSIFY {tool} {list(inp.values())[0]}", got == want, f"{got} (várt: {want})")

    be.shutdown()
    shutil.rmtree(tmp, ignore_errors=True)
    print(f"FUSION-AI: RESULT {'ok' if ok else 'HIBA'}", flush=True)
    return 0 if ok else 1


# ---------------------------------------------------------------- indítás

def main():
    if sys.argv[1:2] == ["--selftest"]:
        return selftest()
    if sys.argv[1:2] in (["-h"], ["--help"]):
        print(__doc__.strip())
        return 0
    from PyQt6.QtNetwork import QLocalServer, QLocalSocket
    project = next((a for a in sys.argv[1:] if not a.startswith("-")), "")
    name = f"fusion-ai-{os.getuid()}"
    sock = QLocalSocket()
    sock.connectToServer(name)
    if sock.waitForConnected(300):          # már fut: előre hozzuk (és átadjuk a projektet)
        import json
        sock.write((json.dumps({"raise": True, "project": project}) + "\n").encode())
        sock.waitForBytesWritten(500)
        return 0
    app, engine = ui.create_app("fusion-ai", "FusionAI", "ai")
    be = Backend(project)
    wire(be)
    server = QLocalServer()
    QLocalServer.removeServer(name)
    server.listen(name)

    def on_conn():
        c = server.nextPendingConnection()
        if c is None:
            return

        def rd():
            import json
            try:
                d = json.loads(bytes(c.readAll()).decode() or "{}")
            except ValueError:
                d = {}
            if d.get("project"):
                be.openProject(d["project"])
            be.message.emit("__raise__", False)
        c.readyRead.connect(rd)
    server.newConnection.connect(on_conn)
    engine.rootContext().setContextProperty("ai", be)
    ui.load(engine, os.path.join(HERE, "qml", "AI.qml"))
    app.aboutToQuit.connect(be.shutdown)
    t = QTimer()
    t.timeout.connect(lambda: None)         # a Python-jelzések (Ctrl+C) feldolgozása
    t.start(500)
    app._keep = [server, be, t]
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
