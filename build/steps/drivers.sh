# shellcheck shell=bash
# drivers — gyári (nem kernelbe épített) kernelmodulok fordítása a rögzített kernelhez.
#
# NVIDIA 470: a modul a nvidia-kernel-source csomagból fordul, pontosan a UKI
# kernelének (KERNEL_ABI) fejléceivel, egy eldobható mmdebstrap build-chrootban.
# A FusionOS rendszerképbe csak a kész .ko fájlok kerülnek (fordító, fejlécek nem).
# Root kell (mmdebstrap, chroot); a rootfs lépés hívja, ha a modulok hiányoznak.

nvidia_ko_dir() { printf '%s/drivers/nvidia-%s-%s' "$CACHE_DIR" "$NVIDIA_VERSION" "$KERNEL_ABI"; }

# igaz, ha minden NVIDIA modul megvan a rögzített kernelhez
nvidia_ko_ready() {
    local d m; d=$(nvidia_ko_dir)
    for m in $NVIDIA_MODULES; do [ -r "$d/$m.ko" ] || return 1; done
}

step_drivers() {
    [ "$(id -u)" -eq 0 ] || die "a 'drivers' lépéshez root kell:  sudo build/fusion-build drivers  (vagy: build/fusion-build all)"
    need mmdebstrap chroot modinfo strip
    local owner="${SUDO_USER:-root}" out work src_deb line n path
    out=$(nvidia_ko_dir); work="$OUT_DIR/drivers-work"

    src_deb=""
    for line in $NVIDIA_DEBS; do
        IFS='|' read -r n path _ <<<"$line"
        [ "$n" = "$NVIDIA_SOURCE_PKG" ] && src_deb="$(nvidia_debs_dir)/${path##*/}"
    done
    [ -r "$src_deb" ] || die "hiányzik a(z) $NVIDIA_SOURCE_PKG csomag — előbb: build/fusion-build fetch"

    step "NVIDIA $NVIDIA_VERSION kernelmodul fordítása a $KERNEL_ABI kernelhez (build-chroot, ~3–6 perc)"
    rm -rf "$work"; mkdir -p "$work/ko" "$OUT_DIR"
    local mods_excl="nvidia-peermem nvidia-vgpu-vfio"
    # a build-chroot mindent a saját tükréből telepít, a gazdagép apt-jától független
    mmdebstrap --mode=root --variant=minbase --arch=amd64 \
        --components=main \
        --hook-dir=/usr/share/mmdebstrap/hooks/file-mirror-automount \
        --include="make,gcc,libc6-dev,kmod,linux-headers-$KERNEL_ABI" \
        --include="$src_deb" \
        --dpkgopt='path-exclude=/usr/share/doc/*' \
        --dpkgopt='path-exclude=/usr/share/man/*' \
        --dpkgopt='path-exclude=/usr/share/locale/*' \
        --customize-hook="chroot \"\$1\" sh -c 'cp -a /usr/src/$NVIDIA_SOURCE_DIR /tmp/nv && cd /tmp/nv && make -j\$(nproc) SYSSRC=/usr/src/linux-headers-$KERNEL_ABI NV_EXCLUDE_KERNEL_MODULES=\"$mods_excl\" modules > /tmp/nv/build.log 2>&1' || { tail -n 40 \"\$1/tmp/nv/build.log\" >&2; exit 1; }" \
        --customize-hook="cp \"\$1\"/tmp/nv/*.ko \"\$1/tmp/nv/build.log\" \"$work/ko/\"" \
        noble "$work/chroot" \
        "deb $ROOTFS_MIRROR noble main" \
        "deb $ROOTFS_MIRROR noble-updates main" \
        "deb $ROOTFS_SECURITY noble-security main" \
        || die "az NVIDIA modul fordítása nem sikerült (napló: $work/ko/build.log)"

    local m vm
    for m in $NVIDIA_MODULES; do
        [ -r "$work/ko/$m.ko" ] || die "nem készült el: $m.ko"
        vm=$(modinfo -F vermagic "$work/ko/$m.ko" | cut -d' ' -f1)
        [ "$vm" = "$KERNEL_ABI" ] || die "$m.ko rossz kernelhez készült: $vm (várt: $KERNEL_ABI)"
        strip --strip-debug "$work/ko/$m.ko"
    done
    rm -rf "$out"; mkdir -p "$out"
    for m in $NVIDIA_MODULES; do cp "$work/ko/$m.ko" "$out/"; done
    cp "$work/ko/build.log" "$out/build.log"
    printf 'nvidia=%s\ncsomag=%s\nkernel=%s\nmodulok=%s\n' \
        "$NVIDIA_VERSION" "$NVIDIA_PKG_VERSION" "$KERNEL_ABI" "$NVIDIA_MODULES" > "$out/BUILD-INFO"
    rm -rf "$work"
    chown -R "$owner": "$CACHE_DIR/drivers" 2>/dev/null || true
    ok "kész: $out ($(du -sm "$out" | cut -f1) MiB)"
}

# a nem-root lépésekből: sudo-val fordít, ha a modulok hiányoznak
ensure_drivers() {
    if nvidia_ko_ready; then
        info "NVIDIA modulok naprakészek: $(nvidia_ko_dir)"
        return 0
    fi
    if [ "$(id -u)" -ne 0 ]; then
        sudo "$BUILD_DIR/fusion-build" drivers
    else
        step_drivers
    fi
}
