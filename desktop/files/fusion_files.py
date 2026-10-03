#!/usr/bin/python3
"""FusionOS — Fájlkezelő (fusion-files): kétpaneles, billentyűzettel gyors fájlkezelés

    fusion-files [bal mappa] [jobb mappa]
    fusion-files --selftest <üres munkakönyvtár>     a műveletek ellenőrzése felület nélkül

Billentyűk: F3 megtekintés, F4 szerkesztés, F5 másolás, F6 mozgatás, F7 új mappa, F8 / Del törlés,
Shift+F6 átnevezés, Tab panelváltás, Insert / Szóköz jelölés, Ctrl+A mind, Ctrl+C / X / V,
Ctrl+H rejtett fájlok, Alt+F7 keresés, Alt+F5 tömörítés, Alt+F9 kicsomagolás, Alt+F1 / F2 meghajtó.
"""
import os
import time
import shutil
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), "lib"))

import fusion_ui as ui  # noqa: E402

HERE = os.path.dirname(os.path.realpath(__file__))
STATE = os.path.join(ui.CONFIG, "files.json")


def selftest(work):
    """a fájlműveletek önellenőrzése (a QEMU-tesztben és kézzel): FUSION-FILES sorok"""
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    from PyQt6.QtCore import QCoreApplication
    import fusion_files_backend as fb
    _app = QCoreApplication(sys.argv)  # noqa: F841
    ok = True

    def check(name, cond, extra=""):
        nonlocal ok
        print(f"FUSION-FILES: {name} {'ok' if cond else 'HIBA'}{(' ' + extra) if extra else ''}", flush=True)
        ok = ok and bool(cond)

    work = os.path.abspath(work)
    shutil.rmtree(work, ignore_errors=True)      # egy korábbi futás maradéka ne zavarjon
    a, b = os.path.join(work, "bal"), os.path.join(work, "jobb")
    for d in (a, b):
        os.makedirs(d, exist_ok=True)
    os.makedirs(os.path.join(a, "mappa", "al"), exist_ok=True)
    with open(os.path.join(a, "szöveg ékezettel.txt"), "w", encoding="utf-8") as f:
        f.write("árvíztűrő tükörfúrógép\nFUSION-KERESES\n")
    with open(os.path.join(a, "mappa", "al", "nagy.bin"), "wb") as f:
        f.write(os.urandom(3 * 1024 * 1024 + 17))
    with open(os.path.join(a, "vágás.gcode"), "w") as f:
        f.write("G28\nG1 X10 Y10\n")
    open(os.path.join(a, ".rejtett"), "w").close()

    m = fb.DirModel()
    m.load(a)
    names = [i["name"] for i in m.entries()]
    check("LIST", names == ["mappa", "szöveg ékezettel.txt", "vágás.gcode"], ",".join(names))
    m.showHidden = True
    check("HIDDEN", ".rejtett" in [i["name"] for i in m.entries()])
    m.showHidden = False

    def run(fn):
        j = fb.Job("t", "t")
        fn(j)
        return j

    srcs = [os.path.join(a, "mappa"), os.path.join(a, "szöveg ékezettel.txt")]
    j = run(lambda j: fb.FileOps(j).copy(srcs, b))
    same = open(os.path.join(a, "mappa/al/nagy.bin"), "rb").read() == open(os.path.join(b, "mappa/al/nagy.bin"), "rb").read()
    check("COPY", same and not j.errors and j.files_done == j.files_total == 2, f"{j.files_done}/{j.files_total} {j.done}B")
    check("CONFLICT", fb.conflicts(srcs, b) == ["mappa", "szöveg ékezettel.txt"])
    check("SELFCOPY", fb.check_target([os.path.join(a, "mappa")], os.path.join(a, "mappa", "al")) != "")
    j = run(lambda j: fb.FileOps(j, "skip").copy(srcs, b))
    check("SKIP", not j.errors)
    j = run(lambda j: fb.FileOps(j).move([os.path.join(b, "szöveg ékezettel.txt")], os.path.join(b, "mappa")))
    check("MOVE", os.path.exists(os.path.join(b, "mappa", "szöveg ékezettel.txt")) and not os.path.exists(os.path.join(b, "szöveg ékezettel.txt")))
    files = fb.Files(m, fb.DirModel())
    check("MKDIR", files.mkdir(b, "Új mappa") == "" and os.path.isdir(os.path.join(b, "Új mappa")))
    check("RENAME", files.rename(os.path.join(b, "Új mappa"), "Projektek") == "" and os.path.isdir(os.path.join(b, "Projektek")))
    zp = os.path.join(b, "csomag.zip")
    j = run(lambda j: fb.FileOps(j).pack([os.path.join(a, "mappa"), os.path.join(a, "vágás.gcode")], zp))
    check("PACK", os.path.exists(zp) and not j.errors, f"{os.path.getsize(zp)}B")
    ex = os.path.join(b, "ki")
    os.makedirs(ex)
    j = run(lambda j: fb.FileOps(j).extract([zp], ex))
    check("EXTRACT", open(os.path.join(ex, "mappa/al/nagy.bin"), "rb").read() == open(os.path.join(a, "mappa/al/nagy.bin"), "rb").read() and not j.errors)
    import tarfile
    tp = os.path.join(b, "csomag.tar.gz")
    with tarfile.open(tp, "w:gz") as t:
        t.add(os.path.join(a, "vágás.gcode"), "vágás.gcode")
    ex2 = os.path.join(b, "ki2")
    os.makedirs(ex2)
    j = run(lambda j: fb.FileOps(j).extract([tp], ex2))
    check("TAR", os.path.exists(os.path.join(ex2, "vágás.gcode")) and not j.errors)
    lst = fb.archive_list(zp)
    check("ARCLIST", "nagy.bin" in lst)
    res = []
    run(lambda j: fb.search(work, "*.gcode", "", j, res))
    check("SEARCH", len(res) == 3 and all(r.endswith("vágás.gcode") for r in res), str(len(res)))
    res = []
    run(lambda j: fb.search(work, "", "FUSION-KERESES", j, res))
    check("GREP", len(res) >= 2, str(len(res)))
    ma, mb = fb.DirModel(), fb.DirModel()
    ma.load(a); mb.load(b)
    lm, rm = fb.compare_dirs(ma.entries(), mb.entries())
    check("COMPARE", "vágás.gcode" in lm and "csomag.zip" in rm, f"bal={sorted(lm)} jobb={sorted(rm)}")
    info = files.readFile(os.path.join(a, "szöveg ékezettel.txt"))
    check("VIEW", "tükörfúrógép" in info["text"] and not info["binary"])
    check("SAVE", files.writeFile(os.path.join(b, "új.txt"), "ő ű\n") == "" and open(os.path.join(b, "új.txt"), encoding="utf-8").read() == "ő ű\n")
    j = run(lambda j: fb.FileOps(j).delete([os.path.join(b, "mappa"), zp]))
    check("DELETE", not os.path.exists(os.path.join(b, "mappa")) and not os.path.exists(zp) and not j.errors)
    # lomtár: áthelyezés (azonnali), eredeti hely, visszaállítás, visszavonás, végleges törlés
    import fusion_trash as tr
    tf = os.path.join(b, "lomtarba.txt")
    with open(tf, "w") as f:
        f.write("x")
    t0 = time.monotonic()
    j = run(lambda j: setattr(files, "_last_trash", fb.FileOps(j).trash([tf])))
    dt = time.monotonic() - t0
    ent = [e for e in tr.entries() if e["orig"] == tf]
    check("TRASH", not os.path.exists(tf) and len(ent) == 1 and not j.errors, f"{dt * 1000:.0f}ms")
    check("TRASHDIR", tr.is_trash_files_dir(os.path.join(tr.HOME_TRASH, "files")))
    check("UNDO", files.undoTrash() == 1 and os.path.exists(tf))
    run(lambda j: fb.FileOps(j).trash([tf]))
    tp2 = os.path.join(tr.HOME_TRASH, "files", [e for e in tr.entries() if e["orig"] == tf][0]["name"])
    r = files.restoreFromTrash([tp2])
    check("RESTORE", r["ok"] == 1 and os.path.exists(tf))
    run(lambda j: fb.FileOps(j).trash([tf]))
    nm = [e for e in tr.entries() if e["orig"] == tf][0]["name"]
    tr.purge(tr.HOME_TRASH, nm)
    check("PURGE", not any(e["orig"] == tf for e in tr.entries()) and not os.path.exists(os.path.join(tr.HOME_TRASH, "files", nm)))
    # Megnyitás ezzel…: „mindig ezzel” (itt: a beépített nézőke) elmentődik, és visszaállítható
    if fb.fp is not None:
        sv = os.path.join(b, "rajz.svg")
        with open(sv, "w") as f:
            f.write("<svg/>")
        ch = files.openWithChoices(sv)
        r1 = files.openWith(sv, "", True)
        saved = fb.fp._assoc_user().get(".svg")
        files.resetAssociation(sv)
        check("OPENWITH", ch["key"] == ".svg" and r1 == "" and saved == fb.fp.BUILTIN and ".svg" not in fb.fp._assoc_user(),
              f"key={ch['key']} saved={saved} items={len(ch['items'])}")
    vols = fb.volumes()
    check("VOLUMES", any(v["path"] == os.path.expanduser("~") for v in vols), ", ".join(f"{v['name']}={v['path'] or v['dev']}" for v in vols))
    print(f"FUSION-FILES: RESULT {'ok' if ok else 'HIBA'}", flush=True)
    return 0 if ok else 1


def main():
    args = sys.argv[1:]
    if args[:1] == ["--selftest"]:
        return selftest(args[1] if len(args) > 1 else os.path.join(ui.RUNTIME, "fusion-files-selftest"))

    app, engine = ui.create_app("fusion-files", "Fájlkezelő", "files")
    import fusion_files_backend as fb
    left, right = fb.DirModel(), fb.DirModel()
    files = fb.Files(left, right)
    st = ui.load_json(STATE, {})
    home = os.path.expanduser("~")
    lp = args[0] if len(args) > 0 else st.get("left", home)
    rp = args[1] if len(args) > 1 else st.get("right", "/data" if os.path.isdir("/data") else home)
    for mdl, key in ((left, "leftSort"), (right, "rightSort")):
        s = st.get(key)
        if isinstance(s, list) and len(s) == 2 and s[0] in ("name", "ext", "size", "date"):
            mdl._sort, mdl._desc = s[0], bool(s[1])
        mdl._hidden = bool(st.get("hidden", False))
    files.refreshVolumes()
    ctx = engine.rootContext()
    ctx.setContextProperty("leftModel", left)
    ctx.setContextProperty("rightModel", right)
    ctx.setContextProperty("files", files)
    ctx.setContextProperty("startPaths", [lp if os.path.isdir(lp) else home, rp if os.path.isdir(rp) else home])
    ctx.setContextProperty("startActive", "left" if args else st.get("active", "left"))
    root = ui.load(engine, os.path.join(HERE, "qml", "Files.qml"))

    def save():
        ui.save_json(STATE, {"left": left.path, "right": right.path, "active": root.property("activeSide"),
                             "hidden": left.showHidden, "leftSort": [left.sortKey, left.sortDesc],
                             "rightSort": [right.sortKey, right.sortDesc]})
    app.aboutToQuit.connect(save)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
