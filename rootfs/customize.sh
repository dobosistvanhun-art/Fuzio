#!/bin/bash
# =============================================================================
#  FusionOS rendszerkép — testreszabás (mmdebstrap customize-hook)
#  $1 = a rendszerkép gyökere. A gazdagépen fut; a chroot-os parancsok a képben.
#  Környezet: FUSION_ROOT, FUSION_VERSION, FUSION_MILESTONE (a fusion-build adja)
# =============================================================================
set -euo pipefail
R="$1"
: "${FUSION_ROOT:?}" "${FUSION_VERSION:?}" "${FUSION_MILESTONE:?}" "${KERNEL_ABI:?}" "${FUSION_NVIDIA_KO:?}" "${NVIDIA_MODULES:?}"
: "${FUSION_EXTRA_ROOT:?}" "${EXTRA_MODULES:?}"
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
in_root useradd -m -s /bin/bash -c "FusionOS" -G sudo,dialout,plugdev,video,audio,input,systemd-journal,adm fusion
echo 'fusion:fusion' | in_root chpasswd
in_root passwd -l root >/dev/null
# az Ubuntu „To run a command as administrator…” üdvözlő sora nem kell
in_root runuser -u fusion -- touch /home/fusion/.sudo_as_admin_successful
: > "$R/etc/machine-id"          # az első indításkor jön létre, a DATA-n marad meg
rm -f "$R/var/lib/dbus/machine-id"

echo "  [customize] szolgáltatások"
in_root systemctl enable systemd-networkd.service systemd-resolved.service \
    fusion-hardware.service fusion-selftest.service >/dev/null 2>&1
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
