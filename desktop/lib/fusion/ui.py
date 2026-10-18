"""a Fúzió-felület közös beállításai, Qt nélkül (a Qt-s rész: fusion_ui) — M8b

    render_mode()     „gpu” (OpenGL, alapértelmezés) vagy „software” (processzoros rajzolás)
    render_forced()   a kernel parancssora (mérési boot-bejegyzés) dönt-e
    RENDER_FILE       ~/.config/fusion/render — Beállítások → Kijelző → Felület rajzolása
"""
import os

from . import CONFIG

RENDER_FILE = os.path.join(CONFIG, "render")


def _cmdline_render():
    try:
        with open("/proc/cmdline") as f:
            v = [w.split("=", 1)[1] for w in f.read().split() if w.startswith("fusion.ui.render=")]
    except OSError:
        v = []
    return v[-1] if v else ""


def render_mode(render_file=None):
    """Sorrend: FUSION_UI_RENDER (fejlesztés) → kernel parancssor (fusion.ui.render=…, mérési boot-bejegyzés)
    → Beállítások → Kijelző (~/.config/fusion/render)"""
    v = os.environ.get("FUSION_UI_RENDER", "") or _cmdline_render()
    if not v:
        try:
            with open(render_file or RENDER_FILE) as f:
                v = f.read().strip()
        except OSError:
            v = ""
    return "software" if v == "software" else "gpu"


def render_forced():
    return bool(_cmdline_render())
