# shellcheck shell=bash
# FusionOS build — közös segédfüggvények. A fusion-build forrásolja be.

FUSION_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
BUILD_DIR="$FUSION_ROOT/build"
# shellcheck disable=SC2034  # a lépésfájlok használják
CACHE_DIR="$BUILD_DIR/cache"
OUT_DIR="$BUILD_DIR/out"

# shellcheck source=/dev/null
. "$FUSION_ROOT/VERSION"
# shellcheck source=build/config/build.conf
. "$BUILD_DIR/config/build.conf"
# shellcheck source=build/config/layout.conf
. "$BUILD_DIR/config/layout.conf"

if [ -t 1 ]; then
    C_OK=$'\e[32m'; C_ERR=$'\e[31m'; C_WARN=$'\e[33m'; C_H=$'\e[1m'; C_0=$'\e[0m'
else
    C_OK=""; C_ERR=""; C_WARN=""; C_H=""; C_0=""
fi

step() { printf '\n%s==> %s%s\n' "$C_H" "$*" "$C_0"; }
info() { printf '    %s\n' "$*"; }
ok()   { printf '    %s%s%s\n' "$C_OK" "$*" "$C_0"; }
warn() { printf '    %sFIGYELEM:%s %s\n' "$C_WARN" "$C_0" "$*" >&2; }
die()  { printf '\n%sHIBA:%s %s\n' "$C_ERR" "$C_0" "$*" >&2; exit 1; }

have() { command -v "$1" >/dev/null 2>&1; }

need() {
    local missing=()
    for c in "$@"; do have "$c" || missing+=("$c"); done
    [ ${#missing[@]} -eq 0 ] || die "hiányzó parancs(ok): ${missing[*]} — futtasd: build/fusion-build deps"
}

not_root() {
    [ "$(id -u)" -ne 0 ] || die "ezt a lépést ne rootként futtasd (root csak a 'usb' lépéshez kell)."
}

# Build-változat: release (VirtualBox / ZBook) vagy test (QEMU automatikus teszt)
variant_dir() { printf '%s/%s' "$OUT_DIR" "${FUSION_VARIANT:-release}"; }

uki_name() { printf 'fusionos-%s-%s-%s.efi' "$FUSION_VERSION" "$FUSION_MILESTONE" "${1:-A}"; }

# partíció eszközneve: /dev/sdc + 1 -> /dev/sdc1 ; /dev/nvme0n1 + 1 -> /dev/nvme0n1p1
part_dev() {
    case "$1" in
        *[0-9]) printf '%sp%s' "$1" "$2" ;;
        *)      printf '%s%s' "$1" "$2" ;;
    esac
}

# sfdisk parancsfájl a lemezelrendezéshez. $1 = DATA méret MiB-ban, vagy "rest"
sfdisk_script() {
    local data="$1" mib=2048   # 1 MiB = 2048 szektor (512 B)
    local esp_start=$((1 * mib))
    local a_start=$((esp_start + ESP_MIB * mib))
    local b_start=$((a_start + SLOT_MIB * mib))
    local d_start=$((b_start + SLOT_MIB * mib))
    echo "label: gpt"
    echo "start=$esp_start, size=$((ESP_MIB * mib)), type=$TYPE_ESP, name=\"$PART_ESP\""
    echo "start=$a_start, size=$((SLOT_MIB * mib)), type=$TYPE_ROOT, name=\"$PART_A\""
    echo "start=$b_start, size=$((SLOT_MIB * mib)), type=$TYPE_ROOT, name=\"$PART_B\""
    if [ "$data" = "rest" ]; then
        echo "start=$d_start, type=$TYPE_DATA, name=\"$PART_DATA\""
    else
        echo "start=$d_start, size=$((data * mib)), type=$TYPE_DATA, name=\"$PART_DATA\""
    fi
}

# a lemezkép teljes mérete MiB-ban (1 MiB eleje + partíciók + 1 MiB a GPT-másolatnak)
image_total_mib() { echo $((1 + ESP_MIB + 2 * SLOT_MIB + IMAGE_DATA_MIB + 1)); }

# rm_work <könyvtár> — munkakönyvtár biztonságos törlése. Ha egy korábbi, megszakadt
# build csatolásokat hagyott benne (proc, sys, dev/pts, dev/shm), előbb leválasztja őket,
# és a törlés soha nem lép át másik fájlrendszerre (a gazdagép /dev-je, /proc-ja érintetlen marad).
rm_work() {
    local dir="$1" m
    [ -n "$dir" ] && [ "$dir" != "/" ] || die "rm_work: érvénytelen könyvtár: '$dir'"
    [ -e "$dir" ] || return 0
    dir=$(readlink -f "$dir")
    if [ -r /proc/self/mounts ]; then
        # a legmélyebb csatolással kezdve
        for m in $(awk -v d="$dir/" 'index($2, d) == 1 {print $2}' /proc/self/mounts | sort -r); do
            umount "$m" 2>/dev/null || umount -l "$m" 2>/dev/null || die "nem választható le: $m"
        done
    fi
    rm -rf --one-file-system "$dir"
}
