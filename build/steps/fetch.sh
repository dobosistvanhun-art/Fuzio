# shellcheck shell=bash
# fetch — a build bemeneteinek letöltése az Ubuntu tárolóból, root nélkül.

step_fetch() {
    not_root
    need apt-get dpkg-deb sha256sum
    step "Csomagok letöltése (apt-get download, root nélkül)"
    local debs="$CACHE_DIR/debs" root="$CACHE_DIR/root"
    mkdir -p "$debs"
    local spec name ver
    for spec in $FETCH_PACKAGES; do
        name=${spec%%=*}; ver=${spec#*=}
        if compgen -G "$debs/${name}_*.deb" >/dev/null; then
            if [ -z "$ver" ] || compgen -G "$debs/${name}_${ver//:/%3a}_*.deb" >/dev/null; then
                info "megvan: $name ${ver:-(legfrissebb)}"
                continue
            fi
            rm -f "$debs/${name}"_*.deb
        fi
        info "letöltés: $name ${ver:-(legfrissebb)}"
        if [ -n "$ver" ]; then
            (cd "$debs" && apt-get download -q "$name=$ver" 2>&1 | grep -v '^W: Download is performed unsandboxed') \
                || true
        else
            (cd "$debs" && apt-get download -q "$name" 2>&1 | grep -v '^W: Download is performed unsandboxed') \
                || true
        fi
        compgen -G "$debs/${name}_*.deb" >/dev/null \
            || die "nem sikerült letölteni: $name ${ver} — futtasd: sudo apt update. Ha a verzió már nincs a tárolóban, frissítsd a build/config/build.conf fájlt (apt-cache policy $name)."
    done

    step "Csomagok kibontása"
    rm -rf "$root"; mkdir -p "$root"
    local d
    for d in "$debs"/*.deb; do
        dpkg-deb -x "$d" "$root"
    done
    (cd "$debs" && sha256sum ./*.deb) > "$CACHE_DIR/packages.sha256"
    [ -r "$root/boot/vmlinuz-$KERNEL_ABI" ] || die "a kernel nem található: boot/vmlinuz-$KERNEL_ABI"
    ok "kész: $(find "$debs" -name '*.deb' | wc -l) csomag, kernel $KERNEL_ABI"
}
