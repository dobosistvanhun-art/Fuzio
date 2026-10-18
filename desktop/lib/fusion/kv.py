"""kulcs = érték fájlok — a Fúzió leíróinak egyetlen olvasója / írója

Formátum: soronként `kulcs = érték`, `#` megjegyzés, üres sor. A Hardware Layer kimenete (display.env) shell-idézett:
`KULCS='érték'` (shell=True: az idézőjeleket a shell szabályai szerint oldja fel).
"""
import os
import shlex


def parse(text, shell=False):
    d = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k, v = k.strip(), v.strip()
        if shell and v:
            try:
                parts = shlex.split(v, posix=True)
                v = parts[0] if len(parts) == 1 else " ".join(parts)
            except ValueError:
                v = v.strip("'\"")
        d[k] = v
    return d


def read(path, shell=False):
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return parse(f.read(), shell)
    except OSError:
        return {}


def write(path, data, header=None, order=()):
    """atomikus írás (.tmp + csere); az `order` kulcsai elöl, a többi ábécérendben"""
    keys = [k for k in order if k in data] + sorted(k for k in data if k not in order)
    lines = [f"# {header}"] if header else []
    lines += [f"{k} = {data[k]}" for k in keys if data[k] is not None and str(data[k]) != ""]
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    os.replace(tmp, path)
