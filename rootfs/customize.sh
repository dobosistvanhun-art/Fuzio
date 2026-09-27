#!/bin/bash
# =============================================================================
#  FusionOS rendszerkép — testreszabás (mmdebstrap customize-hook)
#  $1 = a rendszerkép gyökere. A gazdagépen fut; a chroot-os parancsok a képben.
#  Környezet: FUSION_ROOT, FUSION_VERSION, FUSION_MILESTONE (a fusion-build adja)
# =============================================================================
set -euo pipefail
R="$1"
: "${FUSION_ROOT:?}" "${FUSION_VERSION:?}" "${FUSION_MILESTONE:?}"
in_root() { chroot "$R" "$@"; }

echo "  [customize] FusionOS fájlok"
cp -a "$FUSION_ROOT/rootfs/overlay/." "$R/"
mkdir -p "$R/usr/lib/fusion/hardware"
install -m 0755 "$FUSION_ROOT/hardware/fusion-hwprobe" "$R/usr/lib/fusion/hardware/fusion-hwprobe"
rm -rf "$R/usr/lib/fusion/hardware/profiles"
cp -r "$FUSION_ROOT/hardware/profiles" "$R/usr/lib/fusion/hardware/profiles"
ln -sf /usr/lib/fusion/bin/fusion-hwinfo "$R/usr/bin/fusion-hwinfo"
mkdir -p "$R/data"

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
in_root useradd -m -s /bin/bash -c "FusionOS" -G sudo,dialout,plugdev,video,audio,input fusion
echo 'fusion:fusion' | in_root chpasswd
in_root passwd -l root >/dev/null
: > "$R/etc/machine-id"          # az első indításkor jön létre, a DATA-n marad meg
rm -f "$R/var/lib/dbus/machine-id"

echo "  [customize] szolgáltatások"
in_root systemctl enable systemd-networkd.service systemd-resolved.service \
    fusion-hardware.service fusion-selftest.service >/dev/null 2>&1
in_root systemctl mask apt-daily.timer apt-daily-upgrade.timer e2scrub_reap.service >/dev/null 2>&1 || true
ln -sf /run/systemd/resolve/stub-resolv.conf "$R/etc/resolv.conf"

echo "  [customize] csomagkezelő eltávolítása (a FusionOS-en nincs apt)"
in_root dpkg --purge --force-depends apt >/dev/null 2>&1 || true
rm -rf "$R/var/lib/apt" "$R/var/cache/apt" "$R/etc/apt"
rm -rf "$R/var/cache/debconf/"*-old "$R/var/log/"*.log "$R/var/log/apt" 2>/dev/null || true
find "$R/tmp" "$R/var/tmp" -mindepth 1 -delete 2>/dev/null || true

echo "  [customize] kész"
