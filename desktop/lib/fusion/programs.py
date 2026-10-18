"""programok (a Fúzió Programkezelő) — a Fúzió API felülete a fusion_programs modulhoz (M8d)

    list_programs()          a telepített programok összefoglalója: [{id, name, type, typeName, devices, folders, …}]
    info(id)                 egy program összefoglalója, vagy None
    run(id, files=())        indítás (fájlokkal); visszaadja a parancsot — hiba: ProgramError
    opener(path)             melyik program nyitja meg a fájlt: (id, név) vagy None
    users_of(role)           mely programok érik el az eszközszerepet (COMn): [{id, name, com}]

A telepítés / eltávolítás hosszú művelet: a feladat-protokollal (fusion.jobs) a `fusion-programs` parancson át.
"""
from . import add_paths, devices


class ProgramError(Exception):
    pass


def _fp():
    """a Programkezelő modulja — csak használatkor töltődik be (a rendszerkép építésekor még nincs a helyén)"""
    add_paths()
    import fusion_programs
    return fusion_programs


def list_programs():
    fp = _fp()
    return [fp.info(m) for m in fp.programs()]


def info(pid):
    fp = _fp()
    m = fp.manifest(pid) if fp.ID_RE.match(pid or "") else None
    return fp.info(m) if m else None


def run(pid, files=()):
    fp = _fp()
    try:
        return fp.launch(pid, list(files))
    except fp.ProgramError as e:
        raise ProgramError(str(e)) from e


def opener(path):
    res = _fp().assoc(path)
    return tuple(res[0]) if res else None


def users_of(role):
    return devices.com_usage().get(role, [])
