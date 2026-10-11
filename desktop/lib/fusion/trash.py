"""Lomtár (freedesktop.org Trash-szabvány) — a Fusion API felülete a fusion_trash modulhoz

    state()              {size, count, autoDays, autoChoices}
    set_auto_days(n)     automatikus ürítés: n napnál régebbi elemek (0 = kikapcsolva; 7, 30, 90)
    auto_purge()         a beállítás szerinti ürítés → törölt elemek száma
    empty()              a Lomtár teljes ürítése → törölt elemek száma
"""
from . import add_paths


def _t():
    add_paths()
    import fusion_trash
    return fusion_trash


def state():
    t = _t()
    size, count = t.size()
    return {"size": size, "count": count, "autoDays": t.auto_days(), "autoChoices": list(t.AUTO_CHOICES)}


def set_auto_days(days):
    t = _t()
    try:
        t.set_auto_days(int(days))
    except t.TrashError as e:
        raise ValueError(str(e)) from e


def auto_purge():
    return _t().auto_purge()


def empty():
    return _t().empty()
