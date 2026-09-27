# shellcheck shell=bash
# fetch — a build bemeneteinek letöltése az Ubuntu tárolóból, root nélkül.

# _fetch_pool <csomag> <cél>: közvetlen letöltés az Ubuntu archívumból (FETCH_POOL), sha256-tal
_fetch_pool() {
    local name="$1" dest="$2" line n path sum file
    for line in ${FETCH_POOL:-}; do
        IFS='|' read -r n path sum <<<"$line"
        [ "$n" = "$name" ] || continue
        file="$dest/${path##*/}"
        info "az apt nem találta — közvetlen letöltés: $UBUNTU_MIRROR/$path"
        if have curl; then curl -fsSL --retry 3 -o "$file.part" "$UBUNTU_MIRROR/$path" || { rm -f "$file.part"; return 1; }
        elif have wget; then wget -q -O "$file.part" "$UBUNTU_MIRROR/$path" || { rm -f "$file.part"; return 1; }
        else warn "nincs curl/wget a közvetlen letöltéshez"; return 1; fi
        if [ "$(sha256sum "$file.part" | cut -d' ' -f1)" != "$sum" ]; then
            rm -f "$file.part"; die "$name: a letöltött csomag ellenőrzőösszege nem egyezik"
        fi
        mv "$file.part" "$file"; ok "letöltve és ellenőrizve: ${path##*/}"
        return 0
    done
    return 1
}

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
        compgen -G "$debs/${name}_*.deb" >/dev/null || _fetch_pool "$name" "$debs"
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
