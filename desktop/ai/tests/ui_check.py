#!/usr/bin/python3
"""A FusionAI felületének próbája (offscreen) — a fusion-ai --selftest külön folyamatban futtatja:
    python3 ui_check.py [<AI.qml>]

A jóváhagyó ablak nagyon hosszú paranccsal (kiemelt jóváhagyás) is kifér az ablakba, a gombjaival együtt:
a normál (1180×760) és a legkisebb (860×520) ablakméretnél. Kimenet: „FUSION-AI: <név> ok|HIBA …” sorok.
Ideiglenes HOME-mal és próba-repóval fut (a valódi beállításokhoz nem nyúl), a próba-Claude-dal.
"""
import os
import shutil
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.realpath(__file__))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ.setdefault("FUSION_AI_SDK_DIR", os.path.expanduser("~/.local/share/fusion-ai/python"))
os.environ["FUSION_AI_CLI"] = os.path.join(HERE, "fake-claude")
TMP = tempfile.mkdtemp(prefix="fusion-ai-ui-")
os.environ["HOME"] = TMP
os.environ.pop("XDG_CONFIG_HOME", None)
sys.path.insert(0, os.path.dirname(HERE))
import fusion_ai_app as appmod  # noqa: E402
from fusion_ai_app import Backend, core, ui  # noqa: E402
from PyQt6.QtCore import QObject  # noqa: E402

ok = True


def check(name, cond, extra=""):
    global ok
    print(f"FUSION-AI: {name} {'ok' if cond else 'HIBA'}{(' ' + extra) if extra else ''}", flush=True)
    ok = ok and bool(cond)


def settle(app, sec=0.5):
    t0 = time.monotonic()
    while time.monotonic() - t0 < sec:
        app.processEvents()
        time.sleep(0.01)


def main():
    repo = os.path.join(TMP, "Projektek", "proba")
    subprocess.run(["git", "init", "-q", repo], check=True)
    qml = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(HERE), "qml", "AI.qml")
    app, engine = ui.create_app("fusion-ai", "FusionAI", "ai")
    be = Backend(repo)
    appmod.wire(be)
    engine.rootContext().setContextProperty("ai", be)
    win = ui.load(engine, qml)
    dlg = win.findChild(QObject, "permDlg")
    summary = win.findChild(QObject, "permSummary")
    box = win.findChild(QObject, "permDetail")
    check("UI-LOAD", dlg is not None and summary is not None)
    if dlg is None or summary is None:
        return 1
    cmd = "printf '%s\\n' " + " ".join(f"sor-{i:04d}-nagyon-hosszu-argumentum" for i in range(400)) + " > /tmp/x && git commit -m x"
    for w, h in ((1180, 760), (860, 520)):
        win.setWidth(w)
        win.setHeight(h)
        settle(app, 0.2)
        be.permission.emit({"id": "p-ui", "tool": "Bash", "level": "danger", "why": "Git commit", "summary": cmd,
                            "detail": core.describe("Bash", {"command": cmd, "description": "hosszú próba"})
                                      + "".join(f"\n{i}. sor" for i in range(300)),
                            "reason": "kiemelt jóváhagyás: " + "nagyon hosszú indoklás " * 40})
        settle(app)
        y, dh = dlg.property("y"), dlg.property("height")
        bh = box.property("height") if box is not None else -1
        check(f"UI-PERM-FITS {w}x{h}", dlg.property("opened") and y >= 0 and y + dh <= h and bh <= max(60, h - 320),
              f"ablak y={y:.0f}, magasság={dh:.0f}, részletek doboza={bh:.0f}, a FusionAI ablaka {h}")
        check(f"UI-PERM-SUMMARY {w}x{h}", summary.property("lineCount") <= 3 and summary.property("truncated"),
              f"{summary.property('lineCount')} sor")
        win.setProperty("perm", None)
        win.setProperty("permQueue", [])
        dlg.close()
        settle(app, 0.2)
    be.shutdown()
    print(f"FUSION-AI: UI-RESULT {'ok' if ok else 'HIBA'}", flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    try:
        rc = main()
    finally:
        shutil.rmtree(TMP, ignore_errors=True)
    sys.exit(rc)
