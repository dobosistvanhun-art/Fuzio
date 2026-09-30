#!/bin/bash
# =============================================================================
#  FusionOS rendszerkép — testreszabás (mmdebstrap customize-hook)
#  $1 = a rendszerkép gyökere. A gazdagépen fut; a chroot-os parancsok a képben.
#  Környezet: FUSION_ROOT, FUSION_VERSION, FUSION_MILESTONE (a fusion-build adja)
# =============================================================================
set -euo pipefail
R="$1"
: "${FUSION_ROOT:?}" "${FUSION_VERSION:?}" "${FUSION_MILESTONE:?}" "${KERNEL_ABI:?}" "${FUSION_NVIDIA_KO:?}" "${NVIDIA_MODULES:?}"
: "${FUSION_EXTRA_ROOT:?}" "${EXTRA_MODULES:?}" "${FIRMWARE_FILES:?}" "${FUSION_WINE_BUILD:?}" "${FUSION_WINE_ID:?}"
in_root() { chroot "$R" "$@"; }

echo "  [customize] FusionOS fájlok"
# a tulajdonos mindig root (a build felhasználójáé NE kerüljön a képbe)
cp -a --no-preserve=ownership "$FUSION_ROOT/rootfs/overlay/." "$R/"
mkdir -p "$R/usr/lib/fusion/hardware"
install -m 0755 "$FUSION_ROOT/hardware/fusion-hwprobe" "$R/usr/lib/fusion/hardware/fusion-hwprobe"
rm -rf "$R/usr/lib/fusion/hardware/profiles"
cp -r "$FUSION_ROOT/hardware/profiles" "$R/usr/lib/fusion/hardware/profiles"
rm -rf "$R/usr/lib/fusion/devices"; mkdir -p "$R/usr/lib/fusion/devices"
install -m 0755 "$FUSION_ROOT/devices/fusion-devd" "$R/usr/lib/fusion/devices/fusion-devd"
cp -r "$FUSION_ROOT/devices/roles" "$R/usr/lib/fusion/devices/roles"
mkdir -p "$R/etc/fusion"
chown -R root:root "$R/usr/lib/fusion"
ln -sf /usr/lib/fusion/bin/fusion-hwinfo "$R/usr/bin/fusion-hwinfo"
ln -sf /usr/lib/fusion/bin/fusion-session "$R/usr/bin/fusion-session"
ln -sf /usr/lib/fusion/devices/fusion-devd "$R/usr/bin/fusion-devices"
ln -sf /usr/lib/fusion/bin/fusion-wifi "$R/usr/bin/fusion-wifi"
mkdir -p "$R/data"

echo "  [customize] NVIDIA kernelmodulok ($KERNEL_ABI)"
kdir="$R/usr/lib/modules/$KERNEL_ABI"
[ -d "$kdir" ] || { echo "  [customize] HIBA: nincs $kdir"; exit 1; }
mkdir -p "$kdir/updates/nvidia"
for m in $NVIDIA_MODULES; do
    install -m 0644 "$FUSION_NVIDIA_KO/$m.ko" "$kdir/updates/nvidia/$m.ko"
done

echo "  [customize] kiegészítő kernelmodulok (linux-modules-extra): $EXTRA_MODULES"
# a kiválasztott modulok és a függőségeik; ami már a képben van, nem másoljuk újra
xsrc="$FUSION_EXTRA_ROOT/lib/modules/$KERNEL_ABI"
modkey() { basename "$1" | sed 's/\.ko.*$//' | tr '-' '_'; }
idx_img=$(mktemp); idx_src=$(mktemp)
find "$kdir" -name '*.ko*' | while read -r f; do echo "$(modkey "$f") $f"; done > "$idx_img"
find "$xsrc" -name '*.ko*' | while read -r f; do echo "$(modkey "$f") $f"; done > "$idx_src"
queue=$EXTRA_MODULES; copied=""
while :; do
    # shellcheck disable=SC2086  # a sor szóközzel elválasztott modullista
    set -- $queue; [ $# -gt 0 ] || break
    m=$(echo "$1" | tr '-' '_'); shift; queue="$*"
    case " $copied " in *" $m "*) continue ;; esac
    copied="$copied $m"
    grep -q "^$m " "$idx_img" && continue
    f=$(awk -v m="$m" '$1==m {print $2; exit}' "$idx_src")
    [ -n "$f" ] || { echo "  [customize] HIBA: nincs ilyen kernelmodul: $m"; exit 1; }
    rel=${f#"$xsrc"/}
    mkdir -p "$kdir/$(dirname "$rel")"
    install -m 0644 "$f" "$kdir/$rel"
    echo "$m $kdir/$rel" >> "$idx_img"
    deps=$(modinfo -F depends "$f" 2>/dev/null | tr ',' ' ')
    queue="$queue $deps"
done
rm -f "$idx_img" "$idx_src"
in_root depmod -a "$KERNEL_ABI"
for m in $EXTRA_MODULES; do
    in_root modinfo -k "$KERNEL_ABI" -n "$m" >/dev/null 2>&1 \
        || { echo "  [customize] HIBA: a(z) $m modul nem látható a depmod után"; exit 1; }
done
in_root modinfo -k "$KERNEL_ABI" -F version nvidia >/dev/null \
    || { echo "  [customize] HIBA: az nvidia modul nem látható a depmod után"; exit 1; }

echo "  [customize] grafikus szerver (a Fusion Hardware Layer beállításaival)"
# az Xorg eszköz- és jogosultság-beállítása a bootkor a hardverprofilból készül
ln -sf /run/fusion/hardware/xorg-display.conf "$R/etc/X11/xorg.conf.d/10-fusion-display.conf"
ln -sf /run/fusion/hardware/Xwrapper.config "$R/etc/X11/Xwrapper.config"
chmod 0755 "$R/usr/lib/fusion/bin/"* "$R/usr/lib/fusion/session/xinitrc"

echo "  [customize] firmware: $FIRMWARE_FILES"
fwsrc="$FUSION_EXTRA_ROOT/lib/firmware"
nfw=0
for pat in $FIRMWARE_FILES; do
    for f in $fwsrc/$pat; do
        [ -e "$f" ] || continue
        rel=${f#"$fwsrc"/}
        mkdir -p "$R/usr/lib/firmware/$(dirname "$rel")"
        cp -L "$f" "$R/usr/lib/firmware/$rel"      # a hivatkozások helyett a fájl
        nfw=$((nfw + 1))
    done
done
[ "$nfw" -gt 0 ] || { echo "  [customize] HIBA: egy firmware-fájl sem illeszkedik: $FIRMWARE_FILES"; exit 1; }
echo "  [customize] firmware: $nfw fájl"

echo "  [customize] Fusion Windows Runtime (Wine $FUSION_WINE_ID)"
mkdir -p "$R/usr/lib/fusion/wine" "$R/usr/lib/fusion/fwr/tools"
tar -C "$R/usr/lib/fusion/wine" -xf "$FUSION_WINE_BUILD/wine.tar"
echo "$FUSION_WINE_ID" > "$R/usr/lib/fusion/wine/.fusion-build-id"
cp "$FUSION_WINE_BUILD/BUILD-INFO" "$R/usr/lib/fusion/wine/BUILD-INFO"
install -m 0755 "$FUSION_ROOT/fwr/fwr" "$R/usr/lib/fusion/fwr/fwr"
rm -rf "$R/usr/lib/fusion/fwr/profiles"; cp -r "$FUSION_ROOT/fwr/profiles" "$R/usr/lib/fusion/fwr/profiles"
install -m 0644 "$FUSION_WINE_BUILD"/*.exe "$R/usr/lib/fusion/fwr/tools/"
chown -R root:root "$R/usr/lib/fusion/wine" "$R/usr/lib/fusion/fwr"
ln -sf /usr/lib/fusion/fwr/fwr "$R/usr/bin/fwr"
[ -x "$R/usr/lib/fusion/wine/bin/wine" ] || { echo "  [customize] HIBA: nincs wine a képben"; exit 1; }
# a futtatókörnyezetek helye a DATA-n (az első indításkor jön létre)
mkdir -p "$R/usr/lib/tmpfiles.d"
echo "d /data/fwr 0755 fusion fusion -" > "$R/usr/lib/tmpfiles.d/fusion-fwr.conf"

echo "  [customize] nyomtató (M5): Klipper + Moonraker ($FUSION_PRINTER_ID)"
PR="$R/usr/lib/fusion/printer"
mkdir -p "$PR"
tar -C "$PR" -xf "$FUSION_PRINTER_BUILD/printer.tar"
cp "$FUSION_PRINTER_BUILD/BUILD-INFO" "$PR/BUILD-INFO"
cp "$FUSION_PRINTER_BUILD/pip-freeze.txt" "$PR/pip-freeze.txt"
echo "$FUSION_PRINTER_ID" > "$PR/.fusion-build-id"
[ -f "$PR/klipper/klippy/chelper/c_helper.so" ] || { echo "  [customize] HIBA: hiányzik a c_helper.so"; exit 1; }
# a Moonraker a Klipper docs/ mappáját is kiszolgálná; a képből kimarad, egy üres mappa elég
mkdir -p "$PR/klipper/docs"
echo "A Klipper dokumentációja: https://www.klipper3d.org/ (a FusionOS képében nincs benne)" > "$PR/klipper/docs/README.txt"
install -m 0755 "$FUSION_ROOT/printer/fusion-printer" "$PR/fusion-printer"
install -m 0644 "$FUSION_ROOT/printer/moonraker.conf" "$PR/moonraker.conf"
mkdir -p "$PR/defaults" "$PR/clients"
install -m 0644 "$FUSION_ROOT/printer/defaults/printer.cfg" "$PR/defaults/printer.cfg"
# kliens-makrók (mainsail-config, fluidd-config); a gcodes útvonala a FusionOS-é
sed 's|^path: ~/printer_data/gcodes|path: /data/printer/gcodes|' "$FUSION_MAINSAIL_CONFIG/mainsail.cfg" > "$PR/clients/mainsail.cfg"
sed 's|^path: ~/printer_data/gcodes|path: /data/printer/gcodes|' "$FUSION_FLUIDD_CONFIG/fluidd.cfg" > "$PR/clients/fluidd.cfg"
chown -R root:root "$PR"
ln -sf /usr/lib/fusion/printer/fusion-printer "$R/usr/bin/fusion-printer"
# webes felületek (Fluidd, Mainsail)
for line in $WEBUI_ZIPS; do
    IFS='|' read -r name ver _ _ <<<"$line"
    rm -rf "$R/usr/share/fusion/web/$name"; mkdir -p "$R/usr/share/fusion/web/$name"
    unzip -q "$FUSION_WEBUI_DIR/$name-$ver.zip" -d "$R/usr/share/fusion/web/$name"
    [ -f "$R/usr/share/fusion/web/$name/index.html" ] || { echo "  [customize] HIBA: $name index.html hiányzik"; exit 1; }
done
chown -R root:root "$R/usr/share/fusion/web"
# nginx: csak a FusionOS nyomtató-oldalai
rm -f "$R/etc/nginx/sites-enabled/default"
install -m 0644 "$FUSION_ROOT/printer/nginx/fusion-printer.conf" "$R/etc/nginx/sites-available/fusion-printer"
ln -sf ../sites-available/fusion-printer "$R/etc/nginx/sites-enabled/fusion-printer"
install -m 0644 "$FUSION_ROOT/printer/nginx/fusion-moonraker.conf" "$R/etc/nginx/snippets/fusion-moonraker.conf"
in_root nginx -t >/dev/null 2>&1 || { echo "  [customize] HIBA: nginx -t"; in_root nginx -t; exit 1; }
# szolgáltatások, udev
install -m 0644 "$FUSION_ROOT"/printer/systemd/*.service "$R/usr/lib/systemd/system/"
install -m 0644 "$FUSION_ROOT/printer/udev/71-fusion-printer.rules" "$R/usr/lib/udev/rules.d/"
# a szolgáltatás-felhasználó (a soros porthoz: dialout); adatai a DATA-n
in_root useradd --system --home-dir /data/printer --no-create-home --shell /usr/sbin/nologin \
    --comment "FusionOS nyomtató (Klipper)" --user-group -G dialout klipper
# a Python-környezet próbája a képen belül (a venv a rendszer python3-át használja)
in_root /usr/lib/fusion/printer/klippy-env/bin/python -c 'import greenlet, cffi, serial, jinja2' \
    || { echo "  [customize] HIBA: a Klipper Python-környezete nem indul"; exit 1; }
in_root /usr/lib/fusion/printer/moonraker-env/bin/python -c 'import tornado, nacl, PIL' 2>/dev/null \
    || in_root /usr/lib/fusion/printer/moonraker-env/bin/python -c 'import tornado, libnacl, PIL' \
    || { echo "  [customize] HIBA: a Moonraker Python-környezete nem indul"; exit 1; }

echo "  [customize] Fusion Desktop (M6): Fusion Shell, Fájlkezelő, Beállítások"
DK="$R/usr/lib/fusion/desktop"
rm -rf "$DK" "$R/usr/lib/fusion/shell"; mkdir -p "$DK"
for d in lib qml icons shell files settings bin; do
    cp -r "$FUSION_ROOT/desktop/$d" "$DK/"
done
install -m 0644 "$FUSION_ROOT/desktop/apps.json" "$DK/apps.json"
find "$DK" -name '__pycache__' -prune -exec rm -rf {} +
chmod 0755 "$DK/shell/fusion-shell" "$DK/shell/fusion_shell.py" "$DK/files/fusion_files.py" \
    "$DK/settings/fusion_settings.py" "$DK/bin/fusion-notify"
chown -R root:root "$DK"
ln -sf /usr/lib/fusion/desktop/shell/fusion-shell "$R/usr/bin/fusion-shell"
ln -sf /usr/lib/fusion/desktop/files/fusion_files.py "$R/usr/bin/fusion-files"
ln -sf /usr/lib/fusion/desktop/settings/fusion_settings.py "$R/usr/bin/fusion-settings"
ln -sf /usr/lib/fusion/desktop/bin/fusion-notify "$R/usr/bin/fusion-notify"
rm -f "$R/usr/bin/fusion-uimeasure"
# a modulok betölthetők, a QML-fájlok hibátlanul fordulnak (felület nélkül, offscreen)
in_root env HOME=/root QT_QPA_PLATFORM=offscreen python3 - <<'PY' || { echo "  [customize] HIBA: a Fusion Desktop modulok nem tölthetők be"; exit 1; }
import sys, os, glob
sys.path.insert(0, "/usr/lib/fusion/desktop/lib")
sys.path.insert(0, "/usr/lib/fusion/desktop/files")
sys.path.insert(0, "/usr/lib/fusion/desktop/settings")
import fusion_ui, fusion_x11, fusion_net, fusion_apps, fusion_files_backend, fusion_settings_backend
from PyQt6.QtDBus import QDBusConnection
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtQml import QQmlComponent, QQmlEngine
from PyQt6.QtCore import QUrl
app = QGuiApplication(sys.argv)
eng = QQmlEngine()
eng.addImportPath("/usr/lib/fusion/desktop/qml")
bad = 0
for f in sorted(glob.glob("/usr/lib/fusion/desktop/*/qml/*.qml")):
    c = QQmlComponent(eng, QUrl.fromLocalFile(f))
    # a kontextus-objektumok (shell, files, settings) hiánya itt nem hiba: csak a fordítást nézzük
    if c.isError():
        bad += 1
        for e in c.errors():
            print("  QML:", e.toString())
print(f"  [customize] QML: {len(glob.glob('/usr/lib/fusion/desktop/*/qml/*.qml'))} fájl, {bad} hibás")
sys.exit(1 if bad else 0)
PY
mkdir -p "$R/usr/lib/fusion/programs"
install -m 0755 "$FUSION_ROOT/programs/fusion-appmeasure" "$R/usr/lib/fusion/programs/fusion-appmeasure"
ln -sf /usr/lib/fusion/programs/fusion-appmeasure "$R/usr/bin/fusion-appmeasure"
install -m 0440 "$FUSION_ROOT/rootfs/overlay/etc/sudoers.d/fusion-admin" "$R/etc/sudoers.d/fusion-admin"
in_root visudo -c -q -f /etc/sudoers.d/fusion-admin || { echo "  [customize] HIBA: sudoers.d/fusion-admin"; exit 1; }

echo "  [customize] eszközréteg: a soros portot semmi ne foglalja le"
for pkg in modemmanager brltty; do
    if in_root dpkg -s "$pkg" >/dev/null 2>&1; then echo "  [customize] HIBA: $pkg a rendszerképben"; exit 1; fi
done

echo "  [customize] os-release"
cat > "$R/usr/lib/os-release" <<EOF
NAME="FusionOS"
ID=fusionos
ID_LIKE="ubuntu debian"
PRETTY_NAME="FusionOS $FUSION_VERSION ($FUSION_MILESTONE)"
VERSION="$FUSION_VERSION ($FUSION_MILESTONE)"
VERSION_ID="$FUSION_VERSION"
IMAGE_ID=fusionos
IMAGE_VERSION="$FUSION_VERSION-$FUSION_MILESTONE"
HOME_URL="https://github.com/"
EOF
ln -sf ../usr/lib/os-release "$R/etc/os-release"
rm -f "$R/etc/lsb-release"
cat > "$R/usr/lib/fusion/fusion-release" <<EOF
FUSION_VERSION='$FUSION_VERSION'
FUSION_MILESTONE='$FUSION_MILESTONE'
FUSION_IMAGE_ID='$(date -u +%Y%m%d%H%M%S)'
EOF

echo "  [customize] nyelv, időzóna, konzol"
sed -i 's/^# *hu_HU.UTF-8 UTF-8/hu_HU.UTF-8 UTF-8/; s/^# *en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/' "$R/etc/locale.gen"
grep -q '^hu_HU.UTF-8' "$R/etc/locale.gen" || echo 'hu_HU.UTF-8 UTF-8' >> "$R/etc/locale.gen"
in_root locale-gen >/dev/null
ln -sf /usr/share/zoneinfo/Europe/Budapest "$R/etc/localtime"
echo "Europe/Budapest" > "$R/etc/timezone"
# a konzol billentyűzetkiosztás előre elkészítve (a képben az /etc csak olvasható alapréteg)
in_root setupcon --save-only --force >/dev/null 2>&1 || echo "  [customize] FIGYELEM: setupcon --save-only nem sikerült"

echo "  [customize] felhasználó (fejlesztői: fusion / fusion)"
in_root useradd -m -s /bin/bash -c "FusionOS" -G sudo,dialout,plugdev,video,audio,input,systemd-journal,adm,klipper fusion
echo 'fusion:fusion' | in_root chpasswd
in_root passwd -l root >/dev/null
# az Ubuntu „To run a command as administrator…” üdvözlő sora nem kell
in_root runuser -u fusion -- touch /home/fusion/.sudo_as_admin_successful
: > "$R/etc/machine-id"          # az első indításkor jön létre, a DATA-n marad meg
rm -f "$R/var/lib/dbus/machine-id"

echo "  [customize] szolgáltatások"
in_root systemctl enable systemd-networkd.service systemd-resolved.service iwd.service \
    fusion-hardware.service fusion-selftest.service \
    fusion-klipper.service fusion-moonraker.service nginx.service >/dev/null 2>&1
in_root systemctl mask apt-daily.timer apt-daily-upgrade.timer e2scrub_reap.service >/dev/null 2>&1 || true
# TPM 2.0: a ZBook 15 G2-ben TPM 1.2 van, a FusionOS most nem használ TPM-et
# (a biztonsági modellben LATER). E nélkül a boot "Failed to start systemd-tpm2-setup" hibát ír.
in_root systemctl mask systemd-tpm2-setup.service systemd-tpm2-setup-early.service >/dev/null 2>&1
# NVIDIA: a persistenced (CUDA-szerverekhez) nem kell; az udev-szabály enélkül hiányzó egységet kérne
in_root systemctl mask nvidia-persistenced.service >/dev/null 2>&1
ln -sf /run/systemd/resolve/stub-resolv.conf "$R/etc/resolv.conf"

echo "  [customize] csomagkezelő eltávolítása (a FusionOS-en nincs apt)"
in_root dpkg --purge --force-depends apt >/dev/null 2>&1 || true
rm -rf "$R/var/lib/apt" "$R/var/cache/apt" "$R/etc/apt"
rm -rf "$R/var/cache/debconf/"*-old "$R/var/log/"*.log "$R/var/log/apt" 2>/dev/null || true
find "$R/tmp" "$R/var/tmp" -mindepth 1 -delete 2>/dev/null || true

echo "  [customize] kész"
