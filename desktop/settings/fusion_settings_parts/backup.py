"""Fúzió — Beállítások háttere: Mentés (kézi és automatikus)

A Settings osztály (fusion_settings_backend) ezekből a részekből áll össze; a QML ugyanazt a `settings`
objektumot látja, mint a szétszedés előtt."""
import json
from PyQt6.QtCore import pyqtSlot
import fusion_ui as ui


# --- Mentés (T3) és telepítő pendrive ---
def backup_state():
    rc, out = ui.admin("backup", "list", timeout=60)
    try:
        d = json.loads(out[out.index("{"):])
    except ValueError:
        return {"error": (out.strip().splitlines() or ["ismeretlen hiba"])[-1].replace("fusion-admin: ", ""),
                "targets": [], "backups": [], "dataUsed": 0}
    d["error"] = ""
    d["dataUsedText"] = ui.human_size(d.get("dataUsed", 0))
    for t in d["targets"]:
        t["freeText"] = ui.human_size(t["free"])
    for b in d["backups"]:
        b["sizeText"] = ui.human_size(b.get("bytes", 0))
        b["when"] = b.get("date", "")[:16].replace("T", " ")
    return d


class BackupMixin:
    """Mentés (kézi és automatikus) — a Settings része (a slotok a QML-nek)"""

    # --- Mentés (T3) ---
    @pyqtSlot()
    def backupRefresh(self):
        self._async("backup", lambda: dict(backup_state(), job=self._job_state("backup")))

    @pyqtSlot()
    def backupAutoRefresh(self):
        def go():
            rc, out = ui.admin("backup", "auto-get", timeout=60)
            try:
                d = json.loads(out[out.index("{"):])
            except ValueError:
                return {"error": (out.strip().splitlines() or ["ismeretlen hiba"])[-1].replace("fusion-admin: ", "")}
            d["error"] = ""
            last = d.get("last") or d.get("lastAny")
            if last:
                d["lastText"] = (last.get("date", "")[:16].replace("T", " ") + "   ·   " + ui.human_size(last.get("bytes", 0))
                                 + ("" if last.get("auto") else "   ·   kézi mentés"))
            return d
        self._async("backup-auto", go)

    @pyqtSlot(bool, int, result=str)
    def backupAutoSet(self, on, keep):
        rc, out = ui.admin("backup", "auto-set", "on" if on else "off", str(max(1, min(20, keep))), timeout=30)
        self.backupAutoRefresh()
        return "" if rc == 0 else out.strip().replace("fusion-admin: ", "").replace("fusion-backup: ", "")

    @pyqtSlot(result=str)
    def backupAutoNow(self):
        return self._job("Automatikus mentés most (Tárhely)", [], kind="backup", cmd=("sudo", "-n", ui.ADMIN, "backup", "auto-now"),
                         app="Mentés", icon="archive-in", okpat="^kész")

    @pyqtSlot(str, result=str)
    def backupCreate(self, mountpoint):
        return self._job("DATA mentése", [mountpoint], kind="backup", cmd=("sudo", "-n", ui.ADMIN, "backup", "create"),
                         app="Mentés", icon="archive-in", okpat="^kész")

    @pyqtSlot()
    def backupJobWatch(self):
        if self._job_state("backup")["running"]:
            self._job_watch("backup")
