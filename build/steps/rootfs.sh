# shellcheck shell=bash
# rootfs — a FusionOS rendszerkép (Ubuntu 24.04 minbase + Fusion) építése,
# tömörített, csak olvasható EROFS-képfájlba. Root kell hozzá (mmdebstrap, chroot).

ROOTFS_IMG_NAME="rootfs.erofs"
ROOTFS_MIRROR="${FUSION_MIRROR:-http://archive.ubuntu.com/ubuntu}"
ROOTFS_SECURITY="${FUSION_SECURITY_MIRROR:-http://security.ubuntu.com/ubuntu}"

rootfs_img() { printf '%s/%s' "$OUT_DIR" "$ROOTFS_IMG_NAME"; }

# igaz, ha a rendszerképet újra kell építeni (hiányzik, vagy frissebb a forrása)
rootfs_stale() {
    local img; img=$(rootfs_img)
    [ -r "$img" ] || return 0
    [ -n "$(find "$FUSION_ROOT/rootfs" "$FUSION_ROOT/hardware" "$BUILD_DIR/config" "$FUSION_ROOT/VERSION" \
              -newer "$img" -type f -print -quit 2>/dev/null)" ]
}

# a nem-root build lépésekből hívva: sudo-val újraindítja magát a rootfs lépésre
ensure_rootfs() {
    if [ "${1:-}" != "--force" ] && ! rootfs_stale; then
        info "rendszerkép naprakész: $(rootfs_img)"
        return 0
    fi
    if [ "$(id -u)" -ne 0 ]; then
        step "Rendszerkép építése — root jog kell (mmdebstrap, chroot)"
        sudo "$BUILD_DIR/fusion-build" rootfs
    else
        step_rootfs
    fi
}

# shellcheck disable=SC2016  # a $1-et az mmdebstrap helyettesíti be a hookokban
step_rootfs() {
    [ "$(id -u)" -eq 0 ] || die "a 'rootfs' lépéshez root kell:  sudo build/fusion-build rootfs  (vagy: build/fusion-build all)"
    need mmdebstrap mkfs.erofs chroot
    local owner="${SUDO_USER:-root}"
    local work="$OUT_DIR/rootfs-work" tree img pkgs
    tree="$work/tree"; img=$(rootfs_img)
    mkdir -p "$OUT_DIR"
    rm -rf "$work"; mkdir -p "$work"

    pkgs=$(sed -e 's/#.*//' -e "s/@KERNEL_ABI@/$KERNEL_ABI/" "$FUSION_ROOT/rootfs/packages.list" | tr -s ' \n' ',' | sed 's/^,//; s/,$//')

    step "Rendszerkép: Ubuntu 24.04 (noble) minbase + FusionOS csomagok"
    info "tükör: $ROOTFS_MIRROR"
    export FUSION_ROOT FUSION_VERSION FUSION_MILESTONE
    mmdebstrap --mode=root --variant=minbase --arch=amd64 \
        --components=main,universe \
        --include="$pkgs" \
        --dpkgopt='path-exclude=/usr/share/doc/*' \
        --dpkgopt='path-include=/usr/share/doc/*/copyright' \
        --dpkgopt='path-exclude=/usr/share/man/*' \
        --dpkgopt='path-exclude=/usr/share/info/*' \
        --dpkgopt='path-exclude=/usr/share/lintian/*' \
        --dpkgopt='path-exclude=/usr/share/locale/*' \
        --dpkgopt='path-include=/usr/share/locale/hu/*' \
        --dpkgopt='path-include=/usr/share/locale/locale.alias' \
        --essential-hook='echo "keyboard-configuration keyboard-configuration/layoutcode string hu" | chroot "$1" debconf-set-selections' \
        --essential-hook='echo "keyboard-configuration keyboard-configuration/modelcode string pc105" | chroot "$1" debconf-set-selections' \
        --essential-hook='echo "console-setup console-setup/charmap47 select UTF-8" | chroot "$1" debconf-set-selections' \
        --customize-hook="bash \"$FUSION_ROOT/rootfs/customize.sh\" \"\$1\"" \
        noble "$tree" \
        "deb $ROOTFS_MIRROR noble main universe" \
        "deb $ROOTFS_MIRROR noble-updates main universe" \
        "deb $ROOTFS_SECURITY noble-security main universe"

    # a telepített csomagok listája (a rendszerkép "anyagjegyzéke")
    chroot "$tree" dpkg-query -W -f='${Package} ${Version}\n' | sort > "$OUT_DIR/rootfs.packages"
    local raw; raw=$(du -sm "$tree" | cut -f1)

    step "EROFS rendszerkép (lz4hc, csak olvasható)"
    rm -f "$img"
    mkfs.erofs -zlz4hc,12 -Eztailpacking -T0 -L FUSION_ROOT "$img" "$tree" >/dev/null
    local sz; sz=$(( $(stat -c %s "$img") / 1024 / 1024 ))
    [ "$sz" -lt "$SLOT_MIB" ] || die "a rendszerkép ($sz MiB) nem fér a slotba ($SLOT_MIB MiB)"
    chown "$owner": "$img" "$OUT_DIR/rootfs.packages" 2>/dev/null || true
    [ "$owner" != root ] && chown "$owner": "$OUT_DIR" 2>/dev/null || true
    printf 'kicsomagolva=%s MiB\nerofs=%s MiB\nslot=%s MiB\ncsomagok=%s\n' \
        "$raw" "$sz" "$SLOT_MIB" "$(wc -l < "$OUT_DIR/rootfs.packages")" > "$OUT_DIR/rootfs.size"
    chown "$owner": "$OUT_DIR/rootfs.size" 2>/dev/null || true
    rm -rf "$work"
    ok "kész: $img — ${sz} MiB tömörítve (kicsomagolva ${raw} MiB, $(wc -l < "$OUT_DIR/rootfs.packages") csomag), slot: ${SLOT_MIB} MiB"
}
