"""értesítések — a szabványos org.freedesktop.Notifications szolgáltatáson át (a Fúzió Shell valósítja meg)

    fusion.notify.send(cím, szöveg="", ikon="", app="Fúzió", urgency="normal", timeout_ms=-1)

Parancssor (fusion-notify): [-i ikon] [-u low|normal|critical] [-a program] [-t ms] <cím> [szöveg]
"""
import getopt
import os
import subprocess
import sys

URGENCY = {"low": 0, "normal": 1, "critical": 2}


def _env():
    env = dict(os.environ)
    if not env.get("DBUS_SESSION_BUS_ADDRESS"):
        rt = env.get("XDG_RUNTIME_DIR") or f"/run/user/{os.getuid()}"
        if os.path.exists(os.path.join(rt, "bus")):
            env["DBUS_SESSION_BUS_ADDRESS"] = f"unix:path={rt}/bus"
    return env


def send(summary, body="", icon="", app="Fúzió", urgency="normal", timeout_ms=-1):
    """True, ha a Shell átvette"""
    u = URGENCY.get(urgency, 1) if isinstance(urgency, str) else int(urgency)
    try:
        r = subprocess.run(["busctl", "--user", "--", "call", "org.freedesktop.Notifications",
                            "/org/freedesktop/Notifications", "org.freedesktop.Notifications", "Notify",
                            "susssasa{sv}i", app, "0", icon, summary, body, "0", "1", "urgency", "y", str(u),
                            str(timeout_ms)], capture_output=True, text=True, timeout=5, env=_env())
        return r.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def main(argv=None):
    usage = "használat: fusion-notify [-i ikon] [-u low|normal|critical] [-a program] [-t ms] <cím> [szöveg]"
    try:
        opts, args = getopt.getopt(sys.argv[1:] if argv is None else argv, "i:u:a:t:")
    except getopt.GetoptError:
        print(usage, file=sys.stderr)
        return 2
    o = dict(opts)
    if not args:
        print(usage, file=sys.stderr)
        return 2
    try:
        tmo = int(o.get("-t", "-1"))
    except ValueError:
        tmo = -1
    ok = send(args[0], args[1] if len(args) > 1 else "", o.get("-i", ""), o.get("-a", "Fúzió"),
              o.get("-u", "normal"), tmo)
    return 0 if ok else 1
