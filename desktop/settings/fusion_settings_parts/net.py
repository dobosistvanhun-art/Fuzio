"""Fúzió — Beállítások háttere: Wi-Fi, Bluetooth, Google Drive

A Settings osztály (fusion_settings_backend) ezekből a részekből áll össze; a QML ugyanazt a `settings`
objektumot látja, mint a szétszedés előtt."""
import time
from PyQt6.QtCore import pyqtSlot
import fusion_net
import fusion_drive
import fusion_ui as ui
from fusion import bluetooth as fbt


class NetMixin:
    """Wi-Fi, Bluetooth, Google Drive — a Settings része (a slotok a QML-nek)"""

    # --- Wi-Fi ---
    @pyqtSlot()
    def wifiRefresh(self):
        def f():
            st = fusion_net.state()
            return {"state": st, "networks": fusion_net.networks(st), "wired": fusion_net.wired()}
        self._async("wifi", f)

    @pyqtSlot()
    def wifiScan(self):
        def f():
            ok, err = fusion_net.scan()
            time.sleep(4)
            st = fusion_net.state()
            return {"state": st, "networks": fusion_net.networks(st), "wired": fusion_net.wired(), "scanned": ok, "error": "" if ok else err}
        self._async("wifi-scan", f)

    @pyqtSlot(str, str)
    def wifiConnect(self, name, passphrase):
        def f():
            ok, out = fusion_net.connect(name, passphrase)
            for _ in range(20):
                st = fusion_net.state()
                if st.get("state") == "connected" and st.get("ssid") == name:
                    break
                time.sleep(1)
            for _ in range(10):               # a DHCP-cím
                if st.get("ip"):
                    break
                time.sleep(1)
                st = fusion_net.state()
            good = st.get("state") == "connected" and st.get("ssid") == name
            return {"ok": good, "name": name, "msg": "" if good else (out or "nem sikerült (rossz jelszó vagy gyenge jel?)")}
        self._async("wifi-connect", f)

    @pyqtSlot()
    def wifiDisconnect(self):
        self._async("wifi-action", lambda: dict(zip(("ok", "msg"), fusion_net.disconnect())))

    @pyqtSlot(str)
    def wifiForget(self, name):
        self._async("wifi-action", lambda: dict(zip(("ok", "msg"), fusion_net.forget(name))))

    # --- Bluetooth ---
    @pyqtSlot()
    def btRefresh(self):
        def f():
            a = fbt.adapter()
            return {"adapter": a, "devices": fbt.devices() if a["present"] else []}
        self._async("bt", f)

    def _bt(self, tag, fn, *a):
        def f():
            ok, msg = fn(*a)
            return {"ok": ok, "msg": msg}
        self._async(tag, f)

    @pyqtSlot(bool)
    def btPower(self, on):
        self._bt("bt-action", fbt.power, on)

    @pyqtSlot()
    def btScan(self):
        self._bt("bt-scan", fbt.scan, 12)

    @pyqtSlot(str)
    def btPair(self, addr):
        def ev(kind, code):
            self.result.emit("bt-code", {"kind": kind, "code": code, "address": addr})
        self._bt("bt-pair", fbt.pair, addr, ev)

    @pyqtSlot(str)
    def btConnect(self, addr):
        self._bt("bt-action", fbt.connect, addr)

    @pyqtSlot(str)
    def btDisconnect(self, addr):
        self._bt("bt-action", fbt.disconnect, addr)

    @pyqtSlot(str)
    def btRemove(self, addr):
        self._bt("bt-action", fbt.remove, addr)

    # --- Google Drive ---
    @pyqtSlot()
    def driveRefresh(self):
        def f():
            st = fusion_drive.status(with_account=True)
            st["cacheText"] = ui.human_size(fusion_drive.cache_size())
            acc = st.get("account") or {}
            st["quotaText"] = (ui.human_size(acc["used"]) + " / " + ui.human_size(acc["total"])) if acc.get("total") else \
                (ui.human_size(acc["used"]) + " használatban" if acc.get("used") else "")
            return st
        self._async("drive", f)

    @pyqtSlot()
    def driveConnect(self):
        if getattr(self, "_login", None) and self._login.proc and self._login.proc.poll() is None:
            return
        self._login = fusion_drive.Login(lambda kind, text: self.result.emit("drive-login", {"kind": kind, "text": text}))
        self._login.start()

    @pyqtSlot()
    def driveCancel(self):
        if getattr(self, "_login", None):
            self._login.cancel()

    @pyqtSlot(str)
    def driveOpenUrl(self, url):
        if url.startswith("http://127.0.0.1:"):
            fusion_drive.open_browser(url)

    @pyqtSlot()
    def driveDisconnect(self):
        self._async("drive-action", lambda: {"ok": fusion_drive.disconnect(), "msg": "A Google Drive leválasztva (a felhőben lévő fájlok érintetlenek)."})

    @pyqtSlot(bool)
    def driveMount(self, on):
        def f():
            if on:
                ok, msg = fusion_drive.start()
                return {"ok": ok, "msg": "Csatolva: " + msg if ok else "Hiba: " + msg}
            return {"ok": fusion_drive.stop(), "msg": "A csatolás megszüntetve."}
        self._async("drive-action", f)

    @pyqtSlot(bool)
    def driveAutostart(self, on):
        self._async("drive-action", lambda: {"ok": fusion_drive.set_autostart(on),
                                              "msg": "Bejelentkezéskor " + ("csatolódik." if on else "nem csatolódik.")})
