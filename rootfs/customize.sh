#!/bin/bash
# =============================================================================
#  Fúzió rendszerkép — testreszabás (mmdebstrap customize-hook)
#  $1 = a rendszerkép gyökere. A gazdagépen fut; a chroot-os parancsok a képben.
#  Környezet: FUSION_ROOT, FUSION_VERSION, FUSION_MILESTONE (a fusion-build adja)
# =============================================================================
set -Eeuo pipefail
# hiba esetén a sor és a parancs (az mmdebstrap csak annyit ír, hogy a hook leállt)
trap 'echo "  [customize] HIBA: a(z) $LINENO. sorban: $BASH_COMMAND (kilépési kód: $?)" >&2' ERR
R="$1"
: "${FUSION_ROOT:?}" "${FUSION_VERSION:?}" "${FUSION_MILESTONE:?}" "${KERNEL_ABI:?}" "${FUSION_NVIDIA_KO:?}" "${NVIDIA_MODULES:?}"
: "${FUSION_EXTRA_ROOT:?}" "${EXTRA_MODULES:?}" "${FIRMWARE_FILES:?}" "${FUSION_WINE_BUILD:?}" "${FUSION_WINE_ID:?}" "${FUSION_ICU_BUILD:?}"
in_root() { chroot "$R" "$@"; }

echo "  [customize] Fúzió fájlok"
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
ln -sf /usr/lib/fusion/bin/fusion-update "$R/usr/sbin/fusion-update"
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
    deps=$(modinfo -F depends "$f" 2>/dev/null | tr ',' ' ') \
        || { echo "  [customize] HIBA: a modinfo nem fut a build-gépen (kmod csomag: build/fusion-build deps --install)"; exit 1; }
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

echo "  [customize] grafikus szerver (a Fúzió Hardware Layer beállításaival)"
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

echo "  [customize] Fúzió Windows Runtime (Wine $FUSION_WINE_ID)"
mkdir -p "$R/usr/lib/fusion/wine" "$R/usr/lib/fusion/fwr/tools"
tar -C "$R/usr/lib/fusion/wine" -xf "$FUSION_WINE_BUILD/wine.tar"
echo "$FUSION_WINE_ID" > "$R/usr/lib/fusion/wine/.fusion-build-id"
cp "$FUSION_WINE_BUILD/BUILD-INFO" "$R/usr/lib/fusion/wine/BUILD-INFO"
install -m 0755 "$FUSION_ROOT/fwr/fwr" "$R/usr/lib/fusion/fwr/fwr"
rm -rf "$R/usr/lib/fusion/fwr/profiles"; cp -r "$FUSION_ROOT/fwr/profiles" "$R/usr/lib/fusion/fwr/profiles"
install -m 0644 "$FUSION_WINE_BUILD"/*.exe "$R/usr/lib/fusion/fwr/tools/"
# a Windows rendszer-ICU-ja: az fwr a programok környezetének System32 mappájába másolja
mkdir -p "$R/usr/lib/fusion/fwr/dlls/x86_64"
install -m 0644 "$FUSION_ICU_BUILD"/*.dll "$R/usr/lib/fusion/fwr/dlls/x86_64/"
[ -r "$R/usr/lib/fusion/fwr/dlls/x86_64/icuuc.dll" ] || { echo "  [customize] HIBA: nincs icuuc.dll a képben"; exit 1; }
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
echo "A Klipper dokumentációja: https://www.klipper3d.org/ (a Fúzió képében nincs benne)" > "$PR/klipper/docs/README.txt"
install -m 0755 "$FUSION_ROOT/printer/fusion-printer" "$PR/fusion-printer"
install -m 0644 "$FUSION_ROOT/printer/moonraker.conf" "$PR/moonraker.conf"
mkdir -p "$PR/defaults" "$PR/clients"
install -m 0644 "$FUSION_ROOT/printer/defaults/printer.cfg" "$PR/defaults/printer.cfg"
# kliens-makrók (mainsail-config, fluidd-config); a gcodes útvonala a Fúzióé
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
# nginx: csak a Fúzió nyomtató-oldalai
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
    --comment "Fúzió nyomtató (Klipper)" --user-group -G dialout klipper
# a Python-környezet próbája a képen belül (a venv a rendszer python3-át használja)
in_root /usr/lib/fusion/printer/klippy-env/bin/python -c 'import greenlet, cffi, serial, jinja2' \
    || { echo "  [customize] HIBA: a Klipper Python-környezete nem indul"; exit 1; }
in_root /usr/lib/fusion/printer/moonraker-env/bin/python -c 'import tornado, nacl, PIL' 2>/dev/null \
    || in_root /usr/lib/fusion/printer/moonraker-env/bin/python -c 'import tornado, libnacl, PIL' \
    || { echo "  [customize] HIBA: a Moonraker Python-környezete nem indul"; exit 1; }

echo "  [customize] Fúzió Desktop (M6): Fúzió Shell, Fájlkezelő, Beállítások"
DK="$R/usr/lib/fusion/desktop"
rm -rf "$DK" "$R/usr/lib/fusion/shell"; mkdir -p "$DK"
for d in lib qml icons shell files settings tasks disks installer laser camera games ai bin; do
    cp -r "$FUSION_ROOT/desktop/$d" "$DK/"
done
install -m 0644 "$FUSION_ROOT/desktop/apps.json" "$DK/apps.json"
find "$DK" -name '__pycache__' -prune -exec rm -rf {} +
rm -rf "$DK/games/vaskrom/art-src" "$DK/games/vaskrom/windows"   # a rajzolt motorképek forrása (fejlesztői eszköz, numpy) — a képbe csak az img/ kell
chmod 0755 "$DK/shell/fusion-shell" "$DK/shell/fusion_shell.py" "$DK/files/fusion_files.py" \
    "$DK/settings/fusion_settings.py" "$DK/bin/fusion" "$DK/bin/fusion-notify" "$DK/bin/fusion-sound" "$DK/bin/fusion-drive" \
    "$DK/tasks/fusion_tasks_app.py" "$DK/tasks/fusion-tasks-testwin" "$DK/disks/fusion_disks_app.py" "$DK/laser/fusion_laser_app.py" "$DK/camera/fusion_camera_app.py" "$DK/games/vaskrom/fusion_vaskrom.py" "$DK/installer/fusion_installer_app.py" \
    "$DK/ai/fusion_ai_app.py" "$DK/ai/tests/fake-claude"
chown -R root:root "$DK"
# Fúzió API (M8): a `fusion` Python-csomag minden Python-programnak (Fúzió-programok, szkriptek, root-segédek)
ln -sfn /usr/lib/fusion/desktop/lib/fusion "$R/usr/lib/python3/dist-packages/fusion"
in_root python3 -c "import fusion, fusion.kv, fusion.hardware, fusion.devices, fusion.notify, fusion.permissions, fusion.schema, fusion.jobs, fusion.cli, fusion.power, fusion.programs, fusion.bluetooth, fusion.printers, fusion.camera; assert fusion.API_VERSION == 1" \
    || { echo "  [customize] HIBA: a Fúzió API (python3 -c 'import fusion') nem tölthető be"; exit 1; }
ln -sf /usr/lib/fusion/desktop/shell/fusion-shell "$R/usr/bin/fusion-shell"
ln -sf /usr/lib/fusion/desktop/files/fusion_files.py "$R/usr/bin/fusion-files"
ln -sf /usr/lib/fusion/desktop/settings/fusion_settings.py "$R/usr/bin/fusion-settings"
ln -sf /usr/lib/fusion/desktop/bin/fusion "$R/usr/bin/fusion"
ln -sf /usr/lib/fusion/desktop/bin/fusion-notify "$R/usr/bin/fusion-notify"
ln -sf /usr/lib/fusion/desktop/bin/fusion-sound "$R/usr/bin/fusion-sound"
ln -sf /usr/lib/fusion/desktop/bin/fusion-drive "$R/usr/bin/fusion-drive"
ln -sf /usr/lib/fusion/desktop/bin/fusion-terminal "$R/usr/bin/fusion-terminal"
ln -sf /usr/lib/fusion/desktop/bin/fusion-devterm "$R/usr/bin/fusion-devterm"
ln -sf /usr/lib/fusion/desktop/bin/fusion-touchpad "$R/usr/bin/fusion-touchpad"
ln -sf /usr/lib/fusion/desktop/bin/fusion-screenshot "$R/usr/bin/fusion-screenshot"
ln -sf /usr/lib/fusion/desktop/tasks/fusion_tasks_app.py "$R/usr/bin/fusion-tasks"
ln -sf /usr/lib/fusion/desktop/disks/fusion_disks_app.py "$R/usr/bin/fusion-disks"
ln -sf /usr/lib/fusion/desktop/laser/fusion_laser_app.py "$R/usr/bin/fusion-laser"
ln -sf /usr/lib/fusion/desktop/camera/fusion_camera_app.py "$R/usr/bin/fusion-camera"
ln -sf /usr/lib/fusion/desktop/games/vaskrom/fusion_vaskrom.py "$R/usr/bin/fusion-vaskrom"
ln -sf /usr/lib/fusion/desktop/installer/fusion_installer_app.py "$R/usr/bin/fusion-installer"
ln -sf /usr/lib/fusion/desktop/ai/fusion_ai_app.py "$R/usr/bin/fusion-ai"
ln -sf /usr/lib/fusion/bin/fusion-report "$R/usr/bin/fusion-report"
ln -sf /usr/lib/fusion/bin/fusion-fonts "$R/usr/bin/fusion-fonts"
# hang: a PipeWire felhasználói szolgáltatásai (foglalat-indítás) minden felhasználónak
in_root systemctl --global enable pipewire.socket pipewire-pulse.socket wireplumber.service >/dev/null 2>&1 || true
for u in pipewire.socket pipewire-pulse.socket wireplumber.service; do
    # a képen belül nézzük (in_root): a symlinkek abszolútak, a build-gépen (pl. a Fejlesztődobozban, ahol nincs
    # PipeWire) a cél nem létezik — a gazdagépről vizsgálva tévesen „nincs engedélyezve”
    in_root test -e "/etc/systemd/user/sockets.target.wants/$u" || in_root test -e "/etc/systemd/user/pipewire.service.wants/$u" \
        || in_root test -e "/usr/lib/systemd/user/sockets.target.wants/$u" || in_root test -e "/usr/lib/systemd/user/pipewire.service.wants/$u" \
        || { echo "  [customize] HIBA: a(z) $u nincs engedélyezve"; exit 1; }
done
rm -f "$R/usr/bin/fusion-uimeasure"
echo "  [customize] Fúzió Programkezelő: fusion-programs, fusion-run (leírások: /data/programs/<id>/program.fusion)"
PG="$R/usr/lib/fusion/programs"
rm -rf "$PG"; mkdir -p "$PG/tests"
install -m 0644 "$FUSION_ROOT/programs/fusion_programs.py" "$PG/fusion_programs.py"
install -m 0644 "$FUSION_ROOT/programs/fusion_store.py" "$PG/fusion_store.py"
# Linux-programok receptjei (Flatpak-azonosító szerint, pl. a PrusaSlicer prusaslicer:// URL-sémája) — 0.0.39
install -d "$PG/recipes"
install -m 0644 "$FUSION_ROOT"/programs/recipes/*.recipe "$PG/recipes/"
for f in fusion-programs fusion-run fusion-appmeasure fusion-dev; do
    install -m 0755 "$FUSION_ROOT/programs/$f" "$PG/$f"
    ln -sf "/usr/lib/fusion/programs/$f" "$R/usr/bin/$f"
done
# a Programkezelő próbatelepítője (a QEMU-teszt és a ZBook-ellenőrzés használja)
install -m 0644 "$FUSION_ROOT/programs/tests/fusionteszt-setup.exe" "$PG/tests/fusionteszt-setup.exe"
# a Flatpak-letöltés próbája (a homokozóból a valódi Letöltések mappába)
install -m 0755 "$FUSION_ROOT/programs/tests/flatpak-download-test.sh" "$PG/tests/flatpak-download-test.sh"
# az M7 (A/B frissítés) előtti felmérés — csak olvas
install -D -m 0755 "$FUSION_ROOT/tools/m7-felmeres.sh" "$R/usr/lib/fusion/tools/m7-felmeres.sh"
# a modulok betölthetők, a QML-fájlok hibátlanul fordulnak (felület nélkül, offscreen)
in_root env HOME=/root QT_QPA_PLATFORM=offscreen python3 - <<'PY' || { echo "  [customize] HIBA: a Fúzió Desktop modulok nem tölthetők be"; exit 1; }
import sys, os, glob
sys.path.insert(0, "/usr/lib/fusion/desktop/lib")
sys.path.insert(0, "/usr/lib/fusion/desktop/files")
sys.path.insert(0, "/usr/lib/fusion/desktop/settings")
sys.path.insert(0, "/usr/lib/fusion/desktop/disks")
sys.path.insert(0, "/usr/lib/fusion/desktop/installer")
sys.path.insert(0, "/usr/lib/fusion/desktop/ai")
import fusion_disks_app, fusion_installer_app, fusion_ai_core
import fusion_ui, fusion.x11, fusion.devices, fusion.notify, fusion_net, fusion_apps, fusion_files_backend, fusion_settings_backend
import fusion_programs, fusion_store, fusion_sound, fusion_drive, fusion_tasks
assert fusion_apps.fp is fusion_programs, "a Programkezelő modulja nem töltődött be"
from PyQt6.QtDBus import QDBusConnection
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtQml import QQmlComponent, QQmlEngine
from PyQt6.QtCore import QUrl
app = QGuiApplication(sys.argv)
eng = QQmlEngine()
eng.addImportPath("/usr/lib/fusion/desktop/qml")
bad = 0
# 0.0.71: a Beállítások QML-je csak létező háttér-slotot hívhat (a fusion_settings_parts részekre bontás őre)
import re
mo = fusion_settings_backend.Settings().metaObject()
have = {bytes(mo.method(i).name()).decode() for i in range(mo.methodCount())}
used = set()
for f in glob.glob("/usr/lib/fusion/desktop/settings/qml/*.qml"):
    used |= set(re.findall(r"\bsettings\.([A-Za-z_]\w*)", open(f, encoding="utf-8").read()))
if used - have:
    bad += 1
    print("  Beállítások: a QML nem létező slotot hív:", ", ".join(sorted(used - have)))
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
install -m 0440 "$FUSION_ROOT/rootfs/overlay/etc/sudoers.d/fusion-admin" "$R/etc/sudoers.d/fusion-admin"
in_root visudo -c -q -f /etc/sudoers.d/fusion-admin || { echo "  [customize] HIBA: sudoers.d/fusion-admin"; exit 1; }

echo "  [customize] eszközréteg: a soros portot semmi ne foglalja le"
for pkg in modemmanager brltty; do
    if in_root dpkg -s "$pkg" >/dev/null 2>&1; then echo "  [customize] HIBA: $pkg a rendszerképben"; exit 1; fi
done

echo "  [customize] os-release"
# az alaprendszer neve (a hibajelentéshez) — az Ubuntu os-release-éből, mielőtt felülírjuk
FUSION_BASE=$(sed -n "s/^FUSION_BASE='\(.*\)'$/\1/p" "$R/usr/lib/fusion/fusion-release" 2>/dev/null || true)
if grep -q '^NAME="Ubuntu"' "$R/usr/lib/os-release" 2>/dev/null; then
    FUSION_BASE=$(. "$R/usr/lib/os-release"; echo "$PRETTY_NAME ($VERSION_CODENAME)")
fi
cat > "$R/usr/lib/os-release" <<EOF
NAME="Fúzió"
ID=fusionos
ID_LIKE="ubuntu debian"
PRETTY_NAME="Fúzió $FUSION_VERSION ($FUSION_MILESTONE)"
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
FUSION_BASE='${FUSION_BASE:-Ubuntu 24.04 LTS (noble)}'
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
# M9: az `input` csoport nincs (a nyers billentyűzet- és egéreseményekhez minden program hozzáférne); az Xorg a
# bemeneti eszközöket a logind-on át kapja (root nélküli Xorg), vagy rootként nyitja meg
# fusion-desktop: minden asztali felhasználó (a fusion-admin sudo-szabálya, a pendrive-ok helye) — fusion-users
in_root groupadd --system fusion-desktop
# a build közben (a build-gép környezetéből, pl. a Fejlesztődobozban, ahol a fejlesztő is „fusion”) keletkezhetett
# egy root tulajdonú /home/fusion — a képbe nem való; az useradd hozza létre tisztán
# (az mmdebstrap a helyi .deb-eket — build/cache/nvidia — a build-gépen lévő útvonalukon csatolja be, ezért a képben
# üres /home/<build-felhasználó>/… mappák maradnak; a Minten /home/dobos, a dobozban /home/fusion)
for d in "$R"/home/*; do
    [ -d "$d" ] || continue
    find "$d" -depth -type d -empty -delete 2>/dev/null || true
done
if [ -e "$R/home/fusion" ]; then
    echo "  [customize] a build közben keletkezett /home/fusion törölve: $(cd "$R/home/fusion" && find . -mindepth 1 -maxdepth 2 | head -n 5 | tr '\n' ' ')"
    rm -rf --one-file-system "${R:?}/home/fusion"
fi
in_root useradd -m -s /bin/bash -c "Fúzió" -G sudo,fusion-desktop,dialout,plugdev,video,audio,systemd-journal,adm,klipper,bluetooth,lpadmin fusion
echo 'fusion:fusion' | in_root chpasswd
in_root passwd -l root >/dev/null
# az Ubuntu „To run a command as administrator…” üdvözlő sora nem kell (fájl + tulajdonos; runuser/PAM nélkül)
: > "$R/home/fusion/.sudo_as_admin_successful"
in_root chown fusion:fusion /home/fusion /home/fusion/.sudo_as_admin_successful
: > "$R/etc/machine-id"          # az első indításkor jön létre, a DATA-n marad meg
rm -f "$R/var/lib/dbus/machine-id"

echo "  [customize] szolgáltatások"
in_root systemctl enable systemd-networkd.service systemd-resolved.service iwd.service \
    fusion-hardware.service fusion-selftest.service fusion-boot-check.service \
    fusion-klipper.service fusion-moonraker.service nginx.service fusion-users.service fusion-storage.service >/dev/null 2>&1
# Bluetooth (az adapter megjelenésekor indul), nyomtatás (CUPS, hálózati felderítés: Avahi / mDNS)
in_root systemctl enable bluetooth.service cups.service cups.socket avahi-daemon.service >/dev/null 2>&1 \
    || echo "  [customize] FIGYELEM: a bluetooth / cups / avahi szolgáltatás engedélyezése nem sikerült"
in_root systemctl mask apt-daily.timer apt-daily-upgrade.timer e2scrub_reap.service >/dev/null 2>&1 || true
# TPM 2.0: a ZBook 15 G2-ben TPM 1.2 van, a Fúzió most nem használ TPM-et
# (a biztonsági modellben LATER). E nélkül a boot "Failed to start systemd-tpm2-setup" hibát ír.
in_root systemctl mask systemd-tpm2-setup.service systemd-tpm2-setup-early.service >/dev/null 2>&1
# NVIDIA: a persistenced (CUDA-szerverekhez) nem kell; az udev-szabály enélkül hiányzó egységet kérne
in_root systemctl mask nvidia-persistenced.service >/dev/null 2>&1
# altatás NVIDIA-val (0.0.56): az NVIDIA altató-szolgáltatásai (nvidia-sleep.sh, /proc/driver/nvidia/suspend) a 470-es
# driverrel a ZBookon beragadtak (a gép nem aludt el, sötét kijelzővel ébren maradt) — maszkolva; a driver a kernel
# saját altatási útját használja. A system-sleep hookjuk is kikerül (ébredéskor „resume”-ot írna altatás nélkül).
in_root systemctl disable nvidia-suspend.service nvidia-resume.service nvidia-hibernate.service >/dev/null 2>&1 || true
in_root systemctl mask nvidia-suspend.service nvidia-resume.service nvidia-hibernate.service >/dev/null 2>&1 \
    || echo "  [customize] FIGYELEM: az nvidia-suspend szolgáltatások nem maszkolhatók"
rm -f "$R/usr/lib/systemd/system-sleep/nvidia" "$R/lib/systemd/system-sleep/nvidia"
# altatás-napló + a kijelző visszakapcsolása ébredés után (system-sleep hook); a fedél viselkedése (Beállítások)
chmod 0755 "$R/usr/lib/systemd/system-sleep/fusion"
in_root systemctl enable fusion-lid.service >/dev/null 2>&1 \
    || echo "  [customize] FIGYELEM: a fusion-lid szolgáltatás nem engedélyezhető"
# automatikus heti mentés a Tárhelyre (0.0.70): a napi időzítő csak akkor ment, ha a Beállításokban be van kapcsolva
in_root systemctl enable fusion-backup-auto.timer >/dev/null 2>&1 \
    || { echo "  [customize] HIBA: a fusion-backup-auto.timer nem engedélyezhető"; exit 1; }
# a noble login-PAM-ja a pam_lastlog-ot kéri, de a modul nincs a csomagban → minden belépéskor hibaüzenet a naplóban
sed -i '/pam_lastlog\.so/d' "$R/etc/pam.d/login"
# Terminál: több soros parancs beillesztése (pl. egy leírásból) soronként fusson, ne kerüljenek a sorba
# „^[[200~” vezérlőjelek (a bash „bracketed paste” módja xtermben) — 0.0.39
grep -q 'enable-bracketed-paste' "$R/etc/inputrc" 2>/dev/null \
    || printf '\n# Fúzió: beillesztés soronként (xterm)\nset enable-bracketed-paste off\n' >> "$R/etc/inputrc"
# NVIDIA-csomag: „alias nouveau off” — ez a Nouveau kifejezett betöltését is tiltaná (mérési bejegyzés, 0.0.30).
# Az automatikus betöltést a Fúzió Hardware Layer saját tiltólistája (fusion-display.conf) amúgy is tiltja.
rm -f "$R/usr/lib/modprobe.d/nvidia-graphics-drivers.conf" "$R/lib/modprobe.d/nvidia-graphics-drivers.conf"
in_root grep -rqs '^alias nouveau off' /etc/modprobe.d /usr/lib/modprobe.d && { echo "  [customize] HIBA: a nouveau tiltása (alias off) maradt"; exit 1; }
grep -qx 'blacklist nouveau' "$R/etc/modprobe.d/fusion-display.conf" || { echo "  [customize] HIBA: fusion-display.conf: nincs blacklist nouveau"; exit 1; }
# Ctrl+Alt+Del: a Fúzió Desktopban a Feladatkezelő; a szöveges konzolon se indítsa újra a gépet
in_root systemctl mask ctrl-alt-del.target >/dev/null 2>&1
# Lemezkezelő: a SMART-állapotot kérésre olvassa (smartctl); a háttérfigyelő (smartd, levélküldés) nem kell
in_root systemctl disable smartd.service smartmontools.service >/dev/null 2>&1 || true
in_root systemctl mask smartd.service >/dev/null 2>&1 || true
for t in zstd efibootmgr dumpe2fs fsck.vfat e2fsck parted sgdisk mkfs.vfat fatlabel mkfs.exfat exfatlabel mkntfs ntfslabel mkfs.ext4 e2label smartctl wipefs sfdisk partx; do
    in_root env PATH=/usr/sbin:/usr/bin:/sbin:/bin sh -c "command -v $t" >/dev/null || { echo "  [customize] HIBA: a Lemezkezelőhöz hiányzik: $t"; exit 1; }
done
ln -sf /run/systemd/resolve/stub-resolv.conf "$R/etc/resolv.conf"

echo "  [customize] csomagkezelő eltávolítása (a Fúzión nincs apt)"
in_root dpkg --purge --force-depends apt >/dev/null 2>&1 || true
rm -rf "$R/var/lib/apt" "$R/var/cache/apt" "$R/etc/apt"
rm -rf "$R/var/cache/debconf/"*-old "$R/var/log/"*.log "$R/var/log/apt" 2>/dev/null || true
find "$R/tmp" "$R/var/tmp" -mindepth 1 -delete 2>/dev/null || true

echo "  [customize] kész"
