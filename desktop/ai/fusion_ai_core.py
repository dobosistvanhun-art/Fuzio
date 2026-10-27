"""Fúzió — FusionAI: a Qt nélküli rész (Claude Code elérése, jogosultsági szabályok, Git-biztonság)

A FusionAI a hivatalos Claude Code-ot használja (a felhasználó saját bejelentkezésével, a Claude Agent SDK-n
át); saját AI-protokoll nincs. Ez a modul:
  - megkeresi a Claude Code-ot és az SDK-t (fusion-dev install claude telepíti őket a felhasználó mappájába);
  - eldönti egy eszközhívásról, hogy magától mehet, kérdezni kell, kiemelten kell kérdezni, vagy tilos
    (a Claude Code saját engedélykezelése ezután, a can_use_tool visszahívásban fut);
  - pillanatképet készít a projekt nem commitolt állapotáról, és vissza tudja állítani — a munkafa és az
    index érintése nélkül (külön indexfájllal), így semmi sem vész el.
"""
import json
import os
import re
import shlex
import subprocess
import sys
import time

HOME = os.path.expanduser("~")
SDK_DIR = os.environ.get("FUSION_AI_SDK_DIR") or os.path.join(HOME, ".local", "share", "fusion-ai", "python")
CLI = os.environ.get("FUSION_AI_CLI") or os.path.join(HOME, ".local", "bin", "claude")
CONFIG = os.path.join(os.environ.get("XDG_CONFIG_HOME") or os.path.join(HOME, ".config"), "fusion", "ai.json")
PROJECT_ROOTS = [os.path.join(HOME, "Projektek")]
SNAP_REF = "refs/fusion-ai/"
DIFF_CAP = 400_000          # a diff legfeljebb ennyi karakter a felületen


# ---------------------------------------------------------------- Claude Code és SDK

def load_sdk():
    """(modul, hiba): a Claude Agent SDK a felhasználó mappájából; ha nincs, (None, ok)"""
    if os.path.isdir(SDK_DIR) and SDK_DIR not in sys.path:
        sys.path.insert(0, SDK_DIR)
    try:
        import claude_agent_sdk
        return claude_agent_sdk, ""
    except Exception as e:          # hiányzik vagy sérült: a FusionAI ettől még elindul
        return None, f"{type(e).__name__}: {e}"


def run(cmd, cwd=None, timeout=30, env=None, input=None):
    """(kód, stdout, stderr) — a hibák nem dobnak kivételt"""
    try:
        r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout, env=env,
                           input=input, errors="replace")
        return r.returncode, r.stdout or "", r.stderr or ""
    except (OSError, subprocess.TimeoutExpired) as e:
        return 127, "", str(e)


def cli_status():
    """a Claude Code állapota: telepítve-e, változat, be van-e jelentkezve (a jelszót/tokent nem olvassuk)"""
    st = {"installed": os.access(CLI, os.X_OK), "path": CLI, "version": "", "loggedIn": False, "authMethod": "",
          "error": ""}
    if not st["installed"]:
        st["error"] = "a Claude Code nincs telepítve (fusion-dev install claude)"
        return st
    rc, out, err = run([CLI, "--version"], timeout=30)
    st["version"] = out.strip().split(" ")[0] if rc == 0 else ""
    rc, out, err = run([CLI, "auth", "status", "--json"], timeout=30)
    try:
        d = json.loads(out)
        st["loggedIn"] = bool(d.get("loggedIn"))
        st["authMethod"] = str(d.get("authMethod") or "")
    except ValueError:
        st["error"] = (err or out).strip()[:300]
    return st


# ---------------------------------------------------------------- projektek

def load_config():
    try:
        with open(CONFIG, encoding="utf-8") as f:
            d = json.load(f)
            return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def save_config(d):
    try:
        os.makedirs(os.path.dirname(CONFIG), exist_ok=True)
        tmp = CONFIG + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=1)
        os.replace(tmp, CONFIG)
    except OSError:
        pass


def is_repo(path):
    return os.path.isdir(os.path.join(path, ".git")) or os.path.isfile(os.path.join(path, ".git"))


def projects():
    """a helyi Git-repók: a ~/Projektek mappái (két szint mélyen) és a kézzel felvettek"""
    seen, out = set(), []
    extra = [p for p in load_config().get("projects", []) if isinstance(p, str)]
    cands = []
    for root in PROJECT_ROOTS:
        try:
            for n in sorted(os.listdir(root)):
                p = os.path.join(root, n)
                if is_repo(p):
                    cands.append(p)
                elif os.path.isdir(p):
                    try:
                        cands += [os.path.join(p, m) for m in sorted(os.listdir(p)) if is_repo(os.path.join(p, m))]
                    except OSError:
                        pass
        except OSError:
            pass
    for p in cands + extra:
        rp = os.path.realpath(p)
        if rp not in seen and is_repo(rp):
            seen.add(rp)
            out.append({"path": rp, "name": os.path.basename(rp)})
    return out


def add_project(path):
    path = os.path.realpath(os.path.expanduser(path))
    if not is_repo(path):
        return False
    d = load_config()
    lst = [p for p in d.get("projects", []) if isinstance(p, str)]
    if path not in lst:
        lst.append(path)
    d["projects"] = lst
    save_config(d)
    return True


# ---------------------------------------------------------------- jogosultsági szabályok

READ_TOOLS = {"Read", "Glob", "Grep", "LS", "NotebookRead", "TodoWrite", "TaskCreate", "TaskUpdate", "TaskList",
              "TaskGet", "ToolSearch"}
EDIT_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}
SECRET_PATHS = [os.path.join(HOME, p) for p in (".ssh", ".gnupg", ".claude/.credentials.json", ".config/rclone",
                                                  ".local/share/keyrings", ".netrc", ".git-credentials")]
SYSTEM_PREFIXES = ("/etc", "/usr", "/boot", "/bin", "/sbin", "/lib", "/opt", "/var", "/root", "/sys", "/proc", "/dev")

# a nem commitolt munkát eldobó Git-parancsok: ezeket a FusionAI meg sem kérdezi, elutasítja
DESTRUCTIVE_GIT = [
    (r"\bgit\s+reset\b.*--hard", "git reset --hard"),
    (r"\bgit\s+checkout\b.*\s--\s", "git checkout -- (fájlok visszaállítása)"),
    (r"\bgit\s+checkout\s+\.(\s|$)", "git checkout ."),
    (r"\bgit\s+clean\b", "git clean"),
    (r"\bgit\s+stash\s+(drop|clear)\b", "git stash drop/clear"),
    (r"\bgit\s+push\b.*(\s-f\b|--force)", "git push --force"),
    (r"\bgit\s+branch\s+-D\b", "git branch -D"),
    (r"\bgit\s+update-ref\s+-d\s+refs/fusion-ai", "a FusionAI pillanatképeinek törlése"),
]
# kiemelt jóváhagyás (piros): rendszer, rendszergazda, telepítés, commit/push, törlés
DANGER_CMD = [
    (r"(^|[;&|]\s*|\s)(sudo|su|pkexec|doas)\s", "rendszergazdai jog"),
    (r"\bfusion-admin\b", "Fúzió rendszersegéd (root)"),
    (r"\b(apt|apt-get|dpkg|snap|flatpak)\s+(install|remove|purge|upgrade|dist-upgrade|-i)\b", "telepítés / eltávolítás"),
    (r"\b(pip|pip3)\s+install\b|\bnpm\s+(install|i)\s+(-g|--global)\b|\bcargo\s+install\b", "telepítés"),
    (r"\b(curl|wget)\b[^|]*\|\s*(ba|z)?sh\b", "letöltött szkript futtatása"),
    (r"\bfusion-dev\s+(install|update|remove)\b", "fejlesztői eszköz telepítése / eltávolítása"),
    (r"\bgit\s+commit\b", "Git commit"),
    (r"\bgit\s+push\b", "Git push"),
    (r"\bgit\s+(merge|rebase|cherry-pick|revert|am|tag)\b", "Git-történet módosítása"),
    (r"\bgh\s+(pr|release|repo|issue)\s+(create|merge|close|delete|edit)\b", "GitHub-művelet"),
    (r"\b(systemctl|reboot|shutdown|poweroff|mount|umount|mkfs\S*|dd|fdisk|parted|wipefs)\b", "rendszerművelet"),
    (r"\brm\s+(-\w*[rR]\w*|--recursive)\b", "mappa törlése"),
    (r"\b(chmod|chown)\b.*\s/", "jogosultság módosítása"),
    (r"\b(kill|pkill|killall)\b", "folyamat leállítása"),
]


def _inside(path, root):
    try:
        rp = os.path.realpath(os.path.join(root, os.path.expanduser(path)))
        rr = os.path.realpath(root)
        return rp == rr or rp.startswith(rr + os.sep), rp
    except (TypeError, ValueError):
        return False, str(path)


def _secret(rp):
    return any(rp == s or rp.startswith(s + os.sep) for s in SECRET_PATHS)


def classify(tool, inp, project):
    """egy eszközhívás besorolása: {"level": auto|ask|danger|deny, "why": ok, "summary": rövid leírás}

    A Claude Code a saját szabályai szerint csak azt kérdezi meg tőlünk, amit nem enged meg magától; amit ide
    küld, azt itt soroljuk be. A „deny” nem jut el a felhasználóig (a nem commitolt munka és a titkos fájlok
    védelme); az „ask” és a „danger” jóváhagyó ablakot nyit."""
    inp = inp if isinstance(inp, dict) else {}
    path = inp.get("file_path") or inp.get("notebook_path") or inp.get("path") or ""
    if tool in READ_TOOLS or tool in EDIT_TOOLS:
        summary = tool
        if path:
            inside, rp = _inside(path, project)
            summary = f"{tool}: {os.path.relpath(rp, os.path.realpath(project)) if inside else rp}"
            if _secret(rp):
                return {"level": "deny", "why": "titkos / személyes hitelesítő fájl", "summary": summary}
            if not inside:
                sysf = rp.startswith(SYSTEM_PREFIXES)
                if tool in EDIT_TOOLS:
                    return {"level": "danger", "why": "rendszerfájl módosítása" if sysf else "a projekten kívüli fájl módosítása",
                            "summary": summary}
                return {"level": "ask", "why": "a projekten kívüli olvasás", "summary": summary}
        if tool in READ_TOOLS:
            return {"level": "auto", "why": "olvasás a projektben", "summary": summary}
        return {"level": "ask", "why": "fájlmódosítás a projektben", "summary": summary}
    if tool == "Bash":
        cmd = str(inp.get("command") or "")
        one = " ".join(cmd.split())
        restore_wt = re.search(r"\bgit\s+restore\b", one) and not ("--staged" in one and not re.search(r"\s(--worktree|-W)\b", one))
        if restore_wt:
            return {"level": "deny", "why": "git restore: eldobná a nem commitolt munkát — ha tényleg kell, kézzel futtasd",
                    "summary": cmd}
        for pat, name in DESTRUCTIVE_GIT:
            if re.search(pat, one):
                return {"level": "deny", "why": f"{name}: eldobná a nem commitolt munkát — ha tényleg kell, kézzel futtasd",
                        "summary": cmd}
        if any(s in one for s in (".ssh/", ".gnupg", ".credentials.json", ".git-credentials")):
            return {"level": "deny", "why": "titkos / személyes hitelesítő fájl", "summary": cmd}
        for pat, name in DANGER_CMD:
            if re.search(pat, one):
                return {"level": "danger", "why": name, "summary": cmd}
        return {"level": "ask", "why": "parancs futtatása", "summary": cmd}
    if tool in ("WebFetch", "WebSearch"):
        return {"level": "ask", "why": "internet", "summary": f"{tool}: {inp.get('url') or inp.get('query') or ''}"}
    return {"level": "ask", "why": "eszköz használata", "summary": f"{tool}: {json.dumps(inp, ensure_ascii=False)[:300]}"}


def describe(tool, inp):
    """a jóváhagyó ablak részletei (szerkesztésnél a régi → új szöveg)"""
    inp = inp if isinstance(inp, dict) else {}
    if tool == "Edit":
        return f"--- régi\n{inp.get('old_string', '')}\n+++ új\n{inp.get('new_string', '')}"
    if tool == "MultiEdit":
        return "\n\n".join(f"--- régi\n{e.get('old_string', '')}\n+++ új\n{e.get('new_string', '')}"
                           for e in inp.get("edits", []) if isinstance(e, dict))
    if tool == "Write":
        c = str(inp.get("content", ""))
        return c[:20000] + ("\n…" if len(c) > 20000 else "")
    if tool == "Bash":
        d = inp.get("description")
        return (f"# {d}\n" if d else "") + str(inp.get("command", ""))
    return json.dumps(inp, ensure_ascii=False, indent=1)[:20000]


# ---------------------------------------------------------------- Git: állapot, diff, pillanatkép

def git(repo, *args, timeout=60, env=None):
    e = dict(os.environ, **(env or {}), GIT_TERMINAL_PROMPT="0", LC_ALL="C")
    return run(["git", "-C", repo, *args], timeout=timeout, env=e)


def git_state(repo):
    rc, out, err = git(repo, "status", "--porcelain=v1", "--branch", "--untracked-files=all")
    if rc != 0:
        return {"ok": False, "error": err.strip(), "branch": "", "files": []}
    lines = out.splitlines()
    branch = lines[0][3:] if lines and lines[0].startswith("## ") else ""
    files = [{"status": ln[:2], "path": ln[3:]} for ln in lines[1:] if len(ln) > 3]
    return {"ok": True, "error": "", "branch": branch, "files": files}


def git_diff(repo):
    """a nem commitolt változások: a követett fájlok diffje (HEAD-hez képest) + az új fájlok listája"""
    rc, out, err = git(repo, "diff", "HEAD", "--stat", "--patch", "--no-color", "--no-ext-diff")
    if rc != 0:     # még nincs commit
        rc, out, err = git(repo, "diff", "--patch", "--no-color", "--no-ext-diff")
    rc2, new, _ = git(repo, "ls-files", "--others", "--exclude-standard")
    text = out
    if new.strip():
        text += "\nÚj (nem követett) fájlok:\n" + "".join(f"  + {n}\n" for n in new.splitlines())
    if len(text) > DIFF_CAP:
        text = text[:DIFF_CAP] + "\n… (a diff hosszabb; a teljes: git diff HEAD)"
    return text or "Nincs nem commitolt változás."


def snapshot(repo, label=""):
    """a munkafa teljes állapota (a követett és az új, nem ignorált fájlok) egy commit-objektumban, a
    refs/fusion-ai/<idő> alatt. A munkafát, az indexet és a stash-t nem érinti. Visszaad: {"ref", "sha"}"""
    idx = os.path.join(repo, ".git", f"fusion-ai-index-{os.getpid()}")
    gitdir_rc, gitdir, _ = git(repo, "rev-parse", "--absolute-git-dir")
    if gitdir_rc == 0:
        idx = os.path.join(gitdir.strip(), f"fusion-ai-index-{os.getpid()}")
    env = {"GIT_INDEX_FILE": idx}
    try:
        rc, head, _ = git(repo, "rev-parse", "--verify", "-q", "HEAD")
        head = head.strip() if rc == 0 else ""
        if head:
            git(repo, "read-tree", head, env=env)
        rc, _, err = git(repo, "add", "-A", ".", env=env, timeout=300)
        if rc != 0:
            return {"ref": "", "sha": "", "error": err.strip()}
        rc, tree, err = git(repo, "write-tree", env=env)
        if rc != 0:
            return {"ref": "", "sha": "", "error": err.strip()}
        msg = f"FusionAI pillanatkép {time.strftime('%Y-%m-%d %H:%M:%S')} {label}".strip()
        args = ["commit-tree", tree.strip(), "-m", msg] + (["-p", head] if head else [])
        cenv = {"GIT_AUTHOR_NAME": "FusionAI", "GIT_AUTHOR_EMAIL": "fusion-ai@localhost",
                "GIT_COMMITTER_NAME": "FusionAI", "GIT_COMMITTER_EMAIL": "fusion-ai@localhost"}
        rc, sha, err = git(repo, *args, env=cenv)
        if rc != 0:
            return {"ref": "", "sha": "", "error": err.strip()}
        sha = sha.strip()
        ref = SNAP_REF + time.strftime("%Y%m%d-%H%M%S") + f"-{sha[:7]}"
        git(repo, "update-ref", ref, sha)
        return {"ref": ref, "sha": sha, "error": ""}
    finally:
        try:
            os.unlink(idx)
        except OSError:
            pass


def snapshots(repo):
    rc, out, _ = git(repo, "for-each-ref", "--sort=-refname", "--format=%(refname)%09%(objectname)%09%(subject)",
                     SNAP_REF.rstrip("/"))
    res = []
    for ln in out.splitlines():
        p = ln.split("\t", 2)
        if len(p) == 3:
            res.append({"ref": p[0], "sha": p[1], "subject": p[2]})
    return res


def restore(repo, sha):
    """a munkafa visszaállítása egy pillanatképre. Előtte a mostani állapotról is pillanatkép készül, így a
    visszaállítás is visszavonható. A pillanatkép óta keletkezett új fájlok megmaradnak (listázva)."""
    before = snapshot(repo, "(visszaállítás előtt)")
    if before.get("error"):
        return {"ok": False, "error": "nem sikerült a mostani állapotot menteni: " + before["error"]}
    rc, files, err = git(repo, "ls-tree", "-r", "--name-only", sha)
    if rc != 0:
        return {"ok": False, "error": err.strip()}
    rc, _, err = git(repo, "restore", f"--source={sha}", "--worktree", "--", ".")
    if rc != 0:
        return {"ok": False, "error": err.strip()}
    want = set(files.splitlines())
    _, now, _ = git(repo, "ls-files", "--others", "--exclude-standard")
    _, tracked, _ = git(repo, "ls-files")
    extra = sorted(f for f in set(now.splitlines()) | set(tracked.splitlines()) if f not in want and os.path.exists(os.path.join(repo, f)))
    return {"ok": True, "error": "", "before": before["ref"], "extra": extra}


def system_prompt(project):
    """a FusionAI kiegészítése a Claude Code saját rendszerpromptjához"""
    return (
        "A FusionAI-ban futsz: a felhasználó FusionOS-t (saját Linux-rendszer, QML-felület) használ egy HP ZBook 15 G2 "
        f"laptopon. A kijelölt projekt: {project}. Válaszolj magyarul.\n"
        "- Fordításhoz és buildhez a Fejlesztődoboz eszközeit használd: `fusion-dev box run <parancs>` (Ubuntu 24.04, "
        "a saját mappa közös); a rendszerkép csak olvasható.\n"
        "- Ne commitolj és ne pusholj, csak ha a felhasználó kifejezetten kéri; ezeket a FusionAI külön jóváhagyatja.\n"
        "- Soha ne dobd el a nem commitolt változtatásokat (git reset --hard, checkout --, clean, stash drop: tiltva).\n"
        "- A munkamenet elején a FusionAI pillanatképet készít (refs/fusion-ai/*); a változtatásaid visszaállíthatók.\n"
        "- A projekten kívüli fájlokhoz és a rendszerhez csak indokkal, jóváhagyással nyúlj.\n"
        "- A végén röviden: mit változtattál (fájlonként), milyen teszt futott, mi maradt ellenőrizetlen."
    )


def shell_quote(args):
    return " ".join(shlex.quote(a) for a in args)
