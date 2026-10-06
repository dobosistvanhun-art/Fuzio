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

# _make_initramfs <kimeneti fájl> <init script> <modulok (szóközzel)>
_make_initramfs() {
    local outfile="$1" initsrc="$2" modlist="$3"
    local root="$CACHE_DIR/root" ir="$outfile.d"
    rm -rf "$ir"; mkdir -p "$ir"/{bin,sbin,usr/bin,usr/sbin,dev,proc,sys,run,etc,tmp,newroot,lib/modules/fusion,usr/lib/fusion/hardware,usr/share/fusion}
    local bb=""
    for bb in "$root/usr/bin/busybox" "$root/bin/busybox"; do [ -x "$bb" ] && break; done
    [ -x "$bb" ] || die "a busybox nem található a busybox-static csomagban"
    cp "$bb" "$ir/bin/busybox"
    local app
    for app in $("$ir/bin/busybox" --list); do
        [ "$app" = busybox ] || ln -s busybox "$ir/bin/$app"
    done
    install -m 0755 "$initsrc" "$ir/init"
    install -m 0755 "$FUSION_ROOT/hardware/fusion-hwprobe" "$ir/usr/lib/fusion/hardware/fusion-hwprobe"
    cp -r "$FUSION_ROOT/hardware/profiles" "$ir/usr/lib/fusion/hardware/profiles"
    printf "FUSION_VERSION='%s'\nFUSION_MILESTONE='%s'\nFUSION_PRETTY_NAME='FusionOS %s (%s)'\n" \
        "$FUSION_VERSION" "$FUSION_MILESTONE" "$FUSION_VERSION" "$FUSION_MILESTONE" > "$ir/etc/fusion-release"
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
    read -r -a mods <<< "$modlist"
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
    (cd "$ir" && find . -print0 | LC_ALL=C sort -z | cpio --null -o -H newc -R 0:0 --quiet) \
        | zstd -q -19 -T0 > "$outfile"
    rm -rf "$ir"
    ok "initramfs: $(basename "$outfile") ($(du -h "$outfile" | cut -f1))"
}

# _make_uki <kimenet .efi> <initramfs> <parancssor> <PRETTY_NAME> <IMAGE_VERSION>
_make_uki() {
    local outfile="$1" initrd="$2" cmdline="$3" pretty="$4" imgver="$5"
    local root="$CACHE_DIR/root" osrel="$outfile.os-release"
    printf 'NAME="FusionOS"\nID=fusionos\nPRETTY_NAME="%s"\nVERSION_ID=%s\nIMAGE_ID=fusionos\nIMAGE_VERSION=%s\n' \
        "$pretty" "$FUSION_VERSION" "$imgver" > "$osrel"
    ukify build \
        --linux "$root/boot/vmlinuz-$KERNEL_ABI" \
        --initrd "$initrd" \
        --cmdline "$cmdline" \
        --os-release "@$osrel" \
        --uname "$KERNEL_ABI" \
        --stub /usr/lib/systemd/boot/efi/linuxx64.efi.stub \
        --output "$outfile" >/dev/null
    rm -f "$osrel"
    ok "UKI: $(basename "$outfile") ($(du -h "$outfile" | cut -f1)) — $cmdline"
}

step_build() {
    not_root
    need cpio zstd ukify depmod gzip
    local root="$CACHE_DIR/root" out; out=$(variant_dir)
    [ -r "$root/boot/vmlinuz-$KERNEL_ABI" ] || die "előbb futtasd: build/fusion-build fetch"
    local sdboot=/usr/lib/systemd/boot/efi/systemd-bootx64.efi
    [ -r /usr/lib/systemd/boot/efi/linuxx64.efi.stub ] && [ -r "$sdboot" ] \
        || die "hiányzik a systemd-boot-efi csomag (build/fusion-build deps)"
    mkdir -p "$out"

    local variant="${FUSION_VARIANT:-release}" cm_base cm_main cm_diag
    if [ "$variant" = "test" ]; then
        cm_base="$CMDLINE_TEST"; cm_diag="$CMDLINE_DIAG_TEST"
    else
        cm_base="$CMDLINE_RELEASE"; cm_diag="$CMDLINE_DIAG"
    fi
    cm_main="$cm_base fusion.slot=A"
    BUILD_STAMP=${FUSION_BUILD_STAMP:-$(date -u +%Y%m%d%H%M%S)}

    step "FusionOS initramfs (fusion-init, $variant)"
    _make_initramfs "$out/initramfs-fusion.cpio.zst" "$FUSION_ROOT/initramfs/fusion/init" "$FUSION_MODULES"
    step "Diagnosztikai initramfs (M0 boot-teszt, $variant)"
    _make_initramfs "$out/initramfs-diag.cpio.zst" "$FUSION_ROOT/initramfs/m0/init" "$DIAG_MODULES"

    step "UKI-k (Unified Kernel Image) — A és B slot, build: $BUILD_STAMP"
    local uki ukib diag sl
    uki=$(uki_name A); ukib=$(uki_name B); diag="fusion-diag.efi"
    rm -f "$out"/fusionos-*.efi
    for sl in A B; do
        # IMAGE_VERSION: a systemd-boot ez alapján rendez (a legújabb build elöl)
        _make_uki "$out/$(uki_name $sl)" "$out/initramfs-fusion.cpio.zst" "$cm_base fusion.slot=$sl" \
            "FusionOS $FUSION_VERSION ($FUSION_MILESTONE) — $sl" "$FUSION_VERSION-$BUILD_STAMP-$sl"
    done
    _make_uki "$out/$diag" "$out/initramfs-diag.cpio.zst" "$cm_diag" \
        "FusionOS diagnosztika" "$FUSION_VERSION-diag"
    # telepítő pendrive (T2): ugyanaz a rendszer telepítő módban (FUSION_ISYS, írható réteg RAM-ban)
    _make_uki "$out/fusion-installer.efi" "$out/initramfs-fusion.cpio.zst" "$cm_base fusion.installer=1" \
        "FusionOS $FUSION_VERSION telepítő" "$FUSION_VERSION-$BUILD_STAMP-installer"

    step "ESP-fa (systemd-boot)"
    local esp="$out/esp"
    rm -rf "$esp"
    mkdir -p "$esp/EFI/BOOT" "$esp/EFI/systemd" "$esp/EFI/Linux" "$esp/loader"
    cp "$sdboot" "$esp/EFI/BOOT/BOOTX64.EFI"          # cserélhető média alapútvonala
    cp "$sdboot" "$esp/EFI/systemd/systemd-bootx64.efi"
    cp "$out/$uki" "$esp/EFI/Linux/$uki"
    cp "$out/$diag" "$esp/EFI/Linux/$diag"
    printf 'timeout 5\ndefault %s\nconsole-mode keep\neditor yes\n' "${FUSION_BOOT_DEFAULT:-fusionos-*}" > "$esp/loader/loader.conf"

    # mérési bejegyzések: ugyanaz az UKI, kiegészített parancssorral
    # (a systemd-stub Secure Boot nélkül a boot menü által adott parancssort használja)
    mkdir -p "$esp/loader/entries"
    local id title extra n=0
    while IFS='|' read -r id title extra; do
        [ -n "$id" ] || continue
        printf 'title %s\nsort-key zz-%s\nefi /EFI/Linux/%s\noptions %s %s\n' \
            "$title" "$id" "$uki" "$cm_main" "$extra" > "$esp/loader/entries/$id.conf"
        n=$((n + 1))
    done <<< "${BOOT_MEASURE_ENTRIES:-}"
    ok "ESP kész: $(du -sh "$esp" | cut -f1) — menü: FusionOS (A), FusionOS diagnosztika, $n mérési bejegyzés"

    # a telepítőnek: a céllemez ESP-jének állandó része (systemd-boot, loader.conf, bejegyzések, diagnosztika) —
    # a rendszer UKI-ja a .fupd-ből kerül mellé
    tar -C "$esp" --owner=0 --group=0 --numeric-owner --exclude='./EFI/Linux/fusionos-*' -cf "$out/esp-static.tar" . \
        || die "az esp-static.tar nem készült el"

    _make_update_dir "$out/update" "$out/$uki" "$out/$ukib"
    _make_fupd "$out/update" "$out/fusionos-$FUSION_VERSION-$FUSION_MILESTONE-$BUILD_STAMP.fupd"
}

# egyetlen frissítőfájl (pendrive-ra / Letöltésekbe): tömörítetlen tar, a manifest elöl
# (a rendszerkép már tömörített EROFS) — Beállítások → Rendszerfrissítés, vagy: fusion-update apply <fájl>
_make_fupd() {  # <frissítőcsomag-mappa> <kimenet .fupd>
    local d="$1" f="$2"
    rm -f "$(dirname "$f")"/fusionos-*.fupd
    tar -C "$d" --format=gnu --owner=0 --group=0 --numeric-owner -cf "$f.tmp" \
        fusion-update.manifest uki-A.efi uki-B.efi rootfs.erofs || die "a frissítőfájl nem készült el: $f"
    mv "$f.tmp" "$f"
    ok "frissítőfájl: $(basename "$f") ($(du -h "$f" | cut -f1))"
}

# frissítőcsomag-mappa (M7): fusion-update.manifest + rootfs.erofs + uki-A.efi + uki-B.efi
# (a fájlok kemény hivatkozások — nem foglalnak külön helyet)
_make_update_dir() {  # <mappa> <A uki> <B uki> [rendszerkép]
    local d="$1" ua="$2" ub="$3" img="${4:-$(rootfs_img)}" f
    rm -rf "$d"; mkdir -p "$d"
    ln "$img" "$d/rootfs.erofs" 2>/dev/null || cp "$img" "$d/rootfs.erofs"
    ln "$ua" "$d/uki-A.efi" 2>/dev/null || cp "$ua" "$d/uki-A.efi"
    ln "$ub" "$d/uki-B.efi" 2>/dev/null || cp "$ub" "$d/uki-B.efi"
    {
        echo "# FusionOS frissítőcsomag (fusion-update apply <mappa>)"
        echo "FUSION_VERSION=$FUSION_VERSION"
        echo "FUSION_MILESTONE=$FUSION_MILESTONE"
        echo "BUILD_STAMP=$BUILD_STAMP"
        echo "UKI_A=$(basename "$ua")"
        echo "UKI_B=$(basename "$ub")"
        for f in rootfs.erofs uki-A.efi uki-B.efi; do
            echo "$f $(sha256sum "$d/$f" | cut -d' ' -f1) $(stat -c %s "$d/$f")"
        done
    } > "$d/fusion-update.manifest"
    ok "frissítőcsomag: $d ($(basename "$ua") / $(basename "$ub"))"
}
