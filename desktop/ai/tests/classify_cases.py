"""A FusionAI besorolási szabályainak esetei (fusion_ai_core.classify) — a fusion-ai --selftest futtatja.

Egy eset: (eszköz, bemenet, várt szint). A szintek: auto (kérdés nélkül), ask (jóváhagyás), danger (kiemelt
jóváhagyás), deny (tiltva). A relatív utak a próba-repóhoz (a projekthez) képest értendők.
"""
import os


def cases(home):
    B = lambda cmd, want: ("Bash", {"command": cmd}, want)     # noqa: E731
    return [
        # --- a korábbi esetek (0.0.60–0.0.75)
        B("git checkout -- .", "deny"), B("git restore src/a.rs", "deny"), B("git restore --staged a.rs", "ask"),
        B("sudo apt install x", "danger"), B("cargo test", "ask"), B("git push origin main", "danger"),
        B("git push -f origin x", "deny"), ("Read", {"file_path": "/etc/passwd"}, "ask"),
        ("Edit", {"file_path": "/etc/fstab"}, "danger"), ("Read", {"file_path": os.path.join(home, ".ssh", "id_ed25519")}, "deny"),
        ("Read", {"file_path": "calc.py"}, "auto"), ("Write", {"file_path": "uj.py"}, "ask"),
        B("cat ~/.ssh/id_rsa", "deny"), B("rm -rf build", "danger"), B("npm run deploy", "danger"),
        B("npx wrangler deploy", "danger"), B("npx wrangler d1 migrations apply motoros-tura-db --remote", "danger"),
        B("npx wrangler d1 migrations apply motoros-tura-db --local", "ask"), B("npm test", "ask"),

        # --- 0.0.76: csak olvasó parancsok kérdés nélkül
        B("git status", "auto"),
        B("git status --porcelain=v1 | head -5", "auto"),
        B("git log --oneline -n 10", "auto"),
        B("git diff HEAD --stat", "auto"),
        B("git show HEAD:calc.py | grep -n add | wc -l", "auto"),
        B("git for-each-ref refs/fusion-ai --format='%(refname) %(subject)'", "auto"),
        B("ls", "auto"), B("ls -la src", "auto"),
        B("wc -l src/*.py", "auto"), B("grep x src/*/*.qml", "auto"),
        B('grep -n "def " calc.py', "auto"),
        B("grep 'a|b' calc.py", "auto"),                    # idézett | nem cső
        B("cat calc.py | head -20", "auto"),
        B('cat "a b.txt"', "auto"),
        B("grep 'process.env.FOO' src/a.js", "auto"),       # a process.env nem .env fájl

        # (a) git: csak status/log/diff/show/for-each-ref, és a veszélyes kapcsolókkal jóváhagyás
        B("git -c core.pager=less log", "ask"), B("git -c diff.external=x diff", "ask"),
        B("git -C /tmp status", "ask"), B("git --no-pager log", "ask"),
        B("git diff --output=/tmp/x", "ask"), B("git diff --output /tmp/x", "ask"),
        B("git diff -o /tmp/x", "ask"), B("git log -c", "ask"), B("git log -pc", "ask"),
        B("git diff --ext-diff", "ask"), B("git diff --no-index /dev/null /etc/passwd", "ask"),
        B("git branch", "ask"), B("git config user.name", "ask"), B("git fetch", "ask"), B("git pull", "ask"),

        # (b) a projekten belüli titkos fájlok: Read, Grep és Bash is tiltva
        ("Read", {"file_path": ".dev.vars"}, "deny"), ("Read", {"file_path": "worker/.env.local"}, "deny"),
        ("Read", {"file_path": ".env"}, "deny"), ("Read", {"file_path": "certs/a.pem"}, "deny"),
        ("Read", {"file_path": "tls/server.key"}, "deny"), ("Read", {"file_path": "README.md"}, "auto"),
        ("Grep", {"pattern": "KEY", "path": "worker/.dev.vars"}, "deny"),
        ("Grep", {"pattern": "KEY", "glob": "**/.env*"}, "deny"),
        B("cat .dev.vars", "deny"), B("cat worker/.env.production", "deny"), B('cat ".env"', "deny"),
        B("git show HEAD:.env", "deny"), B("grep KEY .dev.vars", "deny"), B("cat certs/server.key", "deny"),
        B("wc -l *.pem", "deny"), B("head -3 tls/a.pem | wc -c", "deny"), B("cp .env /tmp/x", "deny"),
        B("cat calc.py .dev.vars", "deny"),

        # (c) cső: minden tag engedélyezett; minden más shell-szerkezet jóváhagyós
        B("cat calc.py | sh", "ask"), B("cat calc.py | sort", "ask"), B("git log | tee log.txt", "ask"),
        B("git status && rm x", "ask"), B("git status; rm x", "ask"), B("git status || true", "ask"),
        B("git status &", "ask"), B("git status |", "ask"), B("| cat calc.py", "ask"),
        B("git log > out.txt", "ask"), B("cat < calc.py", "ask"), B("git status 2>&1", "ask"),
        B("cat $(echo calc.py)", "ask"), B("cat `echo calc.py`", "ask"), B('cat "$HOME/x"', "ask"),
        B('cat "`id`"', "ask"), B("cat $X", "ask"), B("cat a\\ b", "ask"), B("git status\nrm x", "ask"),
        B("find . -name x -exec rm {} \\;", "ask"), B("find . -name '*.py'", "ask"),
        B("ls ~", "ask"), B("ls {a,b}", "ask"), B("cat /etc/passwd", "ask"), B("cat ../masik/x", "ask"),
        B("cat *", "ask"), B("ls .*", "ask"), B("cat src/[ab].py", "ask"), B("cat src/../../x", "ask"),
        B("grep -r SECRET .", "ask"), B("grep -rn x src", "ask"), B("grep --recursive x src", "ask"),
        B("grep -f /etc/passwd calc.py", "ask"), B("grep -e x /etc/passwd", "ask"),
        B("head --files0-from=/etc/passwd", "ask"), B("FOO=1 cat calc.py", "ask"), B("/bin/cat calc.py", "ask"),
        B("cat 'nincs vége", "ask"), B("echo hi", "ask"),
    ]


def run(core, project, check):
    for tool, inp, want in cases(core.HOME):
        got = core.classify(tool, inp, project)["level"]
        label = " ".join(str(v) for v in inp.values()).replace("\n", "\\n")
        check(f"CLASSIFY {tool} {label}", got == want, f"{got} (várt: {want})")


if __name__ == "__main__":         # önállóan: python3 classify_cases.py (a hibás esetek és a végeredmény)
    import sys
    import tempfile
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
    import fusion_ai_core
    res = []
    with tempfile.TemporaryDirectory() as d:
        run(fusion_ai_core, d, lambda name, cond, extra="": res.append(cond) or cond or print("HIBA", name, extra))
    print(f"CLASSIFY: {sum(res)}/{len(res)} ok")
    sys.exit(0 if all(res) else 1)
