"""Fúzió — Beállítások háttere: Távoli elérés (0.0.78)

Tailscale (privát hálózat a saját gépeid között, portnyitás nélkül), SSH-szerver (csak kulccsal, csak a
Tailscale-hálózat felől), a képernyő megosztása (x11vnc, a felhasználó saját szolgáltatása: fusion-vnc), a gép
ébren tartása. A rendszeroldali rész a fusion-admin `remote` parancsa (fusion-remote); a kulcsok
(~/.ssh/authorized_keys) és a VNC-jelszó (~/.config/fusion/vnc.pass) a felhasználó saját fájljai, root nélkül.

A Settings osztály (fusion_settings_backend) ezekből a részekből áll össze."""
import base64
import hashlib
import json
import os
import re
from PyQt6.QtCore import pyqtSlot
import fusion_ui as ui

# nyilvános SSH-kulcs egy sorban: típus, base64, megjegyzés (pl. „istvan@munkahely”)
KEY_TYPES = ("ssh-ed25519", "ssh-rsa", "ecdsa-sha2-nistp256", "ecdsa-sha2-nistp384", "ecdsa-sha2-nistp521",
             "sk-ssh-ed25519@openssh.com", "sk-ecdsa-sha2-nistp256@openssh.com")
KEY_RE = re.compile(r"^(?P<type>[a-z0-9@.-]+) (?P<blob>[A-Za-z0-9+/]+={0,3})(?: (?P<comment>[^\r\n]*))?$")
VNC_UNIT = "fusion-vnc.service"


def _home():
    return os.path.expanduser("~")


def keys_path():
    return os.path.join(_home(), ".ssh", "authorized_keys")


def vnc_pass_path():
    return os.path.join(_home(), ".config", "fusion", "vnc.pass")


def parse_key(line):
    """egy nyilvános kulcs ellenőrzése: (típus, base64, megjegyzés) vagy hibaszöveg (str)"""
    line = (line or "").strip()
    if not line:
        return "üres"
    if line.startswith("-----BEGIN") or "PRIVATE KEY" in line:
        return "ez titkos kulcs — a nyilvános kell (a .pub fájl tartalma)"
    m = KEY_RE.match(line)
    if not m or m.group("type") not in KEY_TYPES:
        return "nem nyilvános SSH-kulcs (ssh-ed25519 … vagy ssh-rsa … kezdetű egy sor kell)"
    try:
        blob = base64.b64decode(m.group("blob"), validate=True)
    except ValueError:
        return "hibás kulcs (a base64 rész sérült)"
    # a kulcs elején a saját típusa áll (hossz + név)
    n = int.from_bytes(blob[:4], "big") if len(blob) > 4 else 0
    if blob[4:4 + n].decode("ascii", "replace") != m.group("type"):
        return "hibás kulcs (a típus és a tartalom nem egyezik)"
    return m.group("type"), m.group("blob"), (m.group("comment") or "").strip()


def fingerprint(blob):
    d = hashlib.sha256(base64.b64decode(blob)).digest()
    return "SHA256:" + base64.b64encode(d).decode().rstrip("=")


def list_keys():
    """a belépésre jogosító kulcsok (az authorized_keys érvényes sorai)"""
    out = []
    try:
        with open(keys_path(), encoding="utf-8", errors="replace") as f:
            lines = f.read().splitlines()
    except OSError:
        return out
    for i, line in enumerate(lines):
        k = parse_key(line)
        if isinstance(k, tuple):
            out.append({"line": i, "type": k[0], "comment": k[2] or "(megjegyzés nélkül)", "fingerprint": fingerprint(k[1])})
    return out


def add_key(text):
    """kulcs hozzáadása (több sor is lehet); hibaszöveg vagy üres"""
    good = []
    for line in (text or "").replace("\r", "").split("\n"):
        if not line.strip():
            continue
        k = parse_key(line)
        if isinstance(k, str):
            return k
        good.append(" ".join(x for x in k if x))
    if not good:
        return "nincs kulcs a szövegben"
    have = {(k["type"], k["fingerprint"]) for k in list_keys()}
    new = [g for g in good if (g.split(" ")[0], fingerprint(g.split(" ")[1])) not in have]
    if not new:
        return "ez a kulcs már szerepel"
    d = os.path.dirname(keys_path())
    os.makedirs(d, mode=0o700, exist_ok=True)
    os.chmod(d, 0o700)
    try:
        with open(keys_path(), "rb") as f:
            old = f.read()
    except OSError:
        old = b""
    sep = b"" if not old or old.endswith(b"\n") else b"\n"
    with open(keys_path(), "ab") as f:
        f.write(sep + ("\n".join(new) + "\n").encode())
    os.chmod(keys_path(), 0o600)
    return ""


def remove_key(line_no, fp):
    """a kulcs törlése (a sor száma és az ujjlenyomata is egyezzen: közben ne változzon a fájl)"""
    try:
        with open(keys_path(), encoding="utf-8", errors="replace") as f:
            lines = f.read().splitlines()
    except OSError as e:
        return str(e)
    if not 0 <= line_no < len(lines):
        return "a kulcs már nincs meg"
    k = parse_key(lines[line_no])
    if not isinstance(k, tuple) or fingerprint(k[1]) != fp:
        return "a kulcsfájl közben megváltozott — frissítsen"
    del lines[line_no]
    tmp = keys_path() + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + ("\n" if lines else ""))
    os.chmod(tmp, 0o600)
    os.replace(tmp, keys_path())
    return ""


def vnc_state():
    _, act = ui.run(["systemctl", "--user", "is-active", VNC_UNIT])
    _, ena = ui.run(["systemctl", "--user", "is-enabled", VNC_UNIT])
    return {"active": act.strip() == "active",
            "enabled": ena.strip() == "enabled", "hasPassword": os.path.exists(vnc_pass_path()),
            "installed": os.path.exists("/usr/bin/x11vnc")}


def set_vnc_password(pw):
    """a VNC-jelszó (a VNC csak az első 8 karaktert nézi); hibaszöveg vagy üres"""
    if len(pw) < 6:
        return "legalább 6 karakter"
    if any(c in pw for c in "\r\n"):
        return "a jelszóban nem lehet sortörés"
    d = os.path.dirname(vnc_pass_path())
    os.makedirs(d, exist_ok=True)
    fd = os.open(vnc_pass_path() + ".tmp", os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write(pw[:8] + "\n")
    os.replace(vnc_pass_path() + ".tmp", vnc_pass_path())
    return ""


def remote_state():
    rc, out = ui.admin("remote", "status", "--json", timeout=40)
    try:
        d = json.loads(out[out.index("{"):])
        d["error"] = ""
    except ValueError:
        d = {"error": (out.strip().splitlines() or ["ismeretlen hiba"])[-1].replace("fusion-admin: ", ""),
             "tailscale": {"installed": False, "state": "", "peers": []}, "ssh": {}, "awake": {}, "hostname": ""}
    d["keys"] = list_keys()
    d["vnc"] = vnc_state()
    d["user"] = os.environ.get("USER") or os.path.basename(_home())
    return d


def _err(out):
    return (out.strip().splitlines() or ["ismeretlen hiba"])[-1].replace("fusion-admin: ", "").replace("fusion-remote: ", "")


class RemoteMixin:
    """Távoli elérés — a Settings része (a slotok a QML-nek)"""

    @pyqtSlot()
    def remoteRefresh(self):
        self._async("remote", remote_state)

    @pyqtSlot(bool)
    def remoteTailscale(self, on):
        def go():
            rc, out = ui.admin("remote", "tailscale", "on" if on else "off", timeout=90)
            d = remote_state()
            d["msg"] = "" if rc == 0 else "hiba: " + _err(out)
            return d
        self._async("remote-action", go)

    @pyqtSlot()
    def remoteLogout(self):
        def go():
            rc, out = ui.admin("remote", "tailscale", "logout", timeout=60)
            d = remote_state()
            d["msg"] = "Kijelentkezve: a gép kikerült a Tailscale-hálózatból." if rc == 0 else "hiba: " + _err(out)
            return d
        self._async("remote-action", go)

    @pyqtSlot(str)
    def remoteOpenUrl(self, url):
        if url.startswith("https://login.tailscale.com/"):
            ui.spawn(["xdg-open", url])

    @pyqtSlot(str)
    def remoteCopy(self, text):
        from PyQt6.QtGui import QGuiApplication
        QGuiApplication.clipboard().setText(text)

    @pyqtSlot(bool)
    def remoteSsh(self, on):
        def go():
            rc, out = ui.admin("remote", "ssh", "on" if on else "off", timeout=90)
            d = remote_state()
            d["msg"] = "" if rc == 0 else "hiba: " + _err(out)
            return d
        self._async("remote-action", go)

    @pyqtSlot(bool)
    def remoteAwake(self, on):
        def go():
            rc, out = ui.admin("remote", "awake", "on" if on else "off", timeout=40)
            d = remote_state()
            d["msg"] = "" if rc == 0 else "hiba: " + _err(out)
            return d
        self._async("remote-action", go)

    @pyqtSlot(str, result=str)
    def remoteKeyAdd(self, text):
        e = add_key(text)
        self.remoteRefresh()
        return e

    @pyqtSlot(int, str, result=str)
    def remoteKeyRemove(self, line_no, fp):
        e = remove_key(line_no, fp)
        self.remoteRefresh()
        return e

    @pyqtSlot(bool, str, result=str)
    def remoteVnc(self, on, password):
        if on:
            if password:
                e = set_vnc_password(password)
                if e:
                    return e
            elif not os.path.exists(vnc_pass_path()):
                return "előbb adjon meg jelszót"
            rc, out = ui.run(["systemctl", "--user", "enable", "--now", VNC_UNIT], timeout=30)
            if rc == 0:
                ui.run(["systemctl", "--user", "restart", VNC_UNIT], timeout=30)
        else:
            rc, out = ui.run(["systemctl", "--user", "disable", "--now", VNC_UNIT], timeout=30)
        self.remoteRefresh()
        return "" if rc == 0 else _err(out)
