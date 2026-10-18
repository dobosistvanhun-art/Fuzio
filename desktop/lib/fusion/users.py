"""felhasználók — a Beállítások → Felhasználók és a `fusion users` felülete (a root-részt a fusion-users végzi,
a fusion-admin kapun át; a jogosultságot a hívó felhasználó szerint az dönti el)

    state()                         {users: [{name, uid, fullname, admin, base, autologin, home}], caller, callerAdmin,
                                     autologin}
    add(név, teljes név, jelszó, admin)          (ok, üzenet)
    passwd(név, régi, új)                        (ok, üzenet) — a saját jelszóhoz a régi kell
    delete(név, remove_home=False) / set_admin(név, be) / autologin(név | "none")

A Fúzió alapfelhasználója (fusion / fusion) nem törölhető, a jelszava és a jogai nem módosíthatók.
"""
import json
import subprocess

from . import ADMIN, permissions


def _admin(*args, inp=None, timeout=60):
    try:
        r = subprocess.run(["sudo", "-n", ADMIN, "users"] + list(args), capture_output=True, text=True,
                           input=inp, timeout=timeout)
        msg = (r.stdout + r.stderr).strip()
        return r.returncode == 0, msg.replace("fusion-users: ", "").replace("fusion-admin: ", "")
    except (OSError, subprocess.TimeoutExpired) as e:
        return False, str(e)


def state():
    ok, out = _admin("list", "--json")
    if not ok:
        return {"users": [], "caller": "", "callerAdmin": False, "autologin": "", "error": out}
    try:
        return json.loads(out.splitlines()[-1])
    except (ValueError, IndexError):
        return {"users": [], "caller": "", "callerAdmin": False, "autologin": "", "error": out[-200:]}


def add(name, fullname, password, admin=False, program="fusion"):
    if not permissions.check(program, "system:users"):
        return False, "nincs engedély"
    return _admin("add", name, fullname, "1" if admin else "0", inp=password + "\n")


def passwd(name, old, new, program="fusion"):
    if not permissions.check(program, "system:users"):
        return False, "nincs engedély"
    return _admin("passwd", name, inp=f"{old}\n{new}\n")


def delete(name, remove_home=False, program="fusion"):
    if not permissions.check(program, "system:users"):
        return False, "nincs engedély"
    return _admin("delete", name, *(["--remove-home"] if remove_home else []))


def set_admin(name, on, program="fusion"):
    if not permissions.check(program, "system:users"):
        return False, "nincs engedély"
    return _admin("admin", name, "1" if on else "0")


def autologin(name, program="fusion"):
    if not permissions.check(program, "system:users"):
        return False, "nincs engedély"
    return _admin("autologin", name or "none")
