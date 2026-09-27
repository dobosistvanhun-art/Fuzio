# shellcheck shell=bash
# build — initramfs + UKI + ESP-fa összeállítása, root nélkül.

# modul-függőségek feloldása a modules.dep alapján (függőség előbb)
_resolve_modules() {
    local moddir="$1"; shift
    local -A seen=()
    local order=()
    _visit() {
        local m="$1" path line deps d
        line=$(grep -E "/${m//-/[-_]}\.ko(\.zst)?:" "$moddir/modules.dep" | head -n1)
        [ -n "$line" ] || die "kernelmodul nem található: $m"
        path=${line%%:*}
        [ -n "${seen[$path]:-}" ] && return
        seen[$path]=1
        deps=${line#*:}
        for d in $deps; do
            d=$(basename "$d"); d=${d%.zst}; d=${d%.ko}
            _visit "$d"
        done
        order+=("$path")
    }
    local m
    for m in "$@"; do _visit "$m"; done
    printf '%s\n' "${order[@]}"
}

step_build() {
    not_root
    need cpio zstd ukify depmod gzip
    local root="$CACHE_DIR/root" out; out=$(variant_dir)
    [ -r "$root/boot/vmlinuz-$KERNEL_ABI" ] || die "előbb futtasd: build/fusion-build fetch"
    local stub=/usr/lib/systemd/boot/efi/linuxx64.efi.stub
    local sdboot=/usr/lib/systemd/boot/efi/systemd-bootx64.efi
    [ -r "$stub" ] && [ -r "$sdboot" ] || die "hiányzik a systemd-boot-efi csomag (build/fusion-build deps)"

    local variant="${FUSION_VARIANT:-release}" cmdline
    if [ "$variant" = "test" ]; then cmdline="$CMDLINE_TEST"; else cmdline="$CMDLINE_RELEASE"; fi

    step "Initramfs összeállítása (M0, $variant)"
    local ir="$out/initramfs-root"
    rm -rf "$ir"; mkdir -p "$ir"/{bin,sbin,usr/bin,usr/sbin,dev,proc,sys,run,etc,tmp,lib/modules/fusion,usr/lib/fusion/hardware,usr/share/fusion}
    local bb=""
    for bb in "$root/usr/bin/busybox" "$root/bin/busybox"; do [ -x "$bb" ] && break; done
    [ -x "$bb" ] || die "a busybox nem található a busybox-static csomagban"
    cp "$bb" "$ir/bin/busybox"
    local app
    for app in $("$ir/bin/busybox" --list); do
        [ "$app" = busybox ] || ln -s busybox "$ir/bin/$app"
    done
    install -m 0755 "$FUSION_ROOT/initramfs/m0/init" "$ir/init"
    install -m 0755 "$FUSION_ROOT/hardware/fusion-hwprobe" "$ir/usr/lib/fusion/hardware/fusion-hwprobe"
    cp -r "$FUSION_ROOT/hardware/profiles" "$ir/usr/lib/fusion/hardware/profiles"
    cat > "$ir/etc/fusion-release" <<EOF
FUSION_VERSION='$FUSION_VERSION'
FUSION_MILESTONE='$FUSION_MILESTONE'
FUSION_PRETTY_NAME='FusionOS $FUSION_VERSION ($FUSION_MILESTONE)'
EOF
    # konzol betűkészlet
    local font="$root/usr/share/consolefonts/$CONSOLE_FONT"
    if [ -r "$font" ]; then
        gzip -dc "$font" > "$ir/usr/share/fusion/console.psf"
    else
        warn "a konzol betűkészlet nem található ($CONSOLE_FONT) — az ékezetek hibásak lehetnek"
    fi
    # kernelmodulok, kicsomagolva (a busybox insmod nem tud zstd-t)
    local moddir="$root/lib/modules/$KERNEL_ABI"
    [ -f "$moddir/modules.dep" ] || depmod -b "$root" "$KERNEL_ABI"
    local rel base mods
    read -r -a mods <<< "$M0_MODULES"
    : > "$ir/lib/modules/fusion/modules.order"
    while read -r rel; do
        base=$(basename "$rel"); base=${base%.zst}
        if [[ "$rel" == *.zst ]]; then
            zstd -q -d -c "$moddir/$rel" > "$ir/lib/modules/fusion/$base"
        else
            cp "$moddir/$rel" "$ir/lib/modules/fusion/$base"
        fi
        echo "$base" >> "$ir/lib/modules/fusion/modules.order"
    done < <(_resolve_modules "$moddir" "${mods[@]}")
    info "modulok: $(tr '\n' ' ' < "$ir/lib/modules/fusion/modules.order")"
    # cpio (newc) + zstd; a fájltulajdonos a cpio-ban root
    (cd "$ir" && find . -print0 | LC_ALL=C sort -z | cpio --null -o -H newc -R 0:0 --quiet) \
        | zstd -q -19 -T0 > "$out/initramfs.cpio.zst"
    ok "initramfs: $(du -h "$out/initramfs.cpio.zst" | cut -f1)"

    step "UKI (Unified Kernel Image) készítése"
    cat > "$out/os-release" <<EOF
NAME="FusionOS"
ID=fusionos
PRETTY_NAME="FusionOS $FUSION_VERSION ($FUSION_MILESTONE)"
VERSION_ID=$FUSION_VERSION
IMAGE_ID=fusionos
IMAGE_VERSION=$FUSION_VERSION-$FUSION_MILESTONE
EOF
    local uki; uki=$(uki_name)
    ukify build \
        --linux "$root/boot/vmlinuz-$KERNEL_ABI" \
        --initrd "$out/initramfs.cpio.zst" \
        --cmdline "$cmdline" \
        --os-release "@$out/os-release" \
        --uname "$KERNEL_ABI" \
        --stub "$stub" \
        --output "$out/$uki" >/dev/null
    ok "UKI: $uki ($(du -h "$out/$uki" | cut -f1)), parancssor: $cmdline"

    step "ESP-fa (systemd-boot)"
    local esp="$out/esp"
    rm -rf "$esp"
    mkdir -p "$esp/EFI/BOOT" "$esp/EFI/systemd" "$esp/EFI/Linux" "$esp/loader"
    cp "$sdboot" "$esp/EFI/BOOT/BOOTX64.EFI"          # cserélhető média alapútvonala
    cp "$sdboot" "$esp/EFI/systemd/systemd-bootx64.efi"
    cp "$out/$uki" "$esp/EFI/Linux/$uki"
    cat > "$esp/loader/loader.conf" <<EOF
timeout 5
default fusionos-*
console-mode keep
editor yes
EOF
    ok "ESP kész: $(du -sh "$esp" | cut -f1)"
}
