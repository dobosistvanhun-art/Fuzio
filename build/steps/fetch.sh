# shellcheck shell=bash
# fetch — a build bemeneteinek letöltése az Ubuntu tárolóból, root nélkül.

# _download <url> <célfájl> <sha256>: letöltés .part fájlba, ellenőrzés, átnevezés
_download() {
    local url="$1" file="$2" sum="$3"
    if have curl; then curl -fsSL --retry 3 -o "$file.part" "$url" || { rm -f "$file.part"; return 1; }
    elif have wget; then wget -q -O "$file.part" "$url" || { rm -f "$file.part"; return 1; }
    else warn "nincs curl/wget a közvetlen letöltéshez"; return 1; fi
    if [ "$(sha256sum "$file.part" | cut -d' ' -f1)" != "$sum" ]; then
        rm -f "$file.part"; die "${file##*/}: a letöltött csomag ellenőrzőösszege nem egyezik"
    fi
    mv "$file.part" "$file"
}

# _fetch_pool <csomag> <cél>: közvetlen letöltés az Ubuntu archívumból (FETCH_POOL), sha256-tal
_fetch_pool() {
    local name="$1" dest="$2" line n path sum
    for line in ${FETCH_POOL:-}; do
        IFS='|' read -r n path sum <<<"$line"
        [ "$n" = "$name" ] || continue
        info "az apt nem találta — közvetlen letöltés: $UBUNTU_MIRROR/$path"
        _download "$UBUNTU_MIRROR/$path" "$dest/${path##*/}" "$sum" || return 1
        ok "letöltve és ellenőrizve: ${path##*/}"
        return 0
    done
    return 1
}

# nvidia_debs_dir: a rögzített NVIDIA csomagok helye
nvidia_debs_dir() { printf '%s/nvidia' "$CACHE_DIR"; }

# _fetch_nvidia: a rögzített NVIDIA 470 csomagok (NVIDIA_DEBS) letöltése és ellenőrzése
_fetch_nvidia() {
    local dir line n path sum file
    dir=$(nvidia_debs_dir); mkdir -p "$dir"
    step "NVIDIA $NVIDIA_VERSION csomagok (rögzített verzió, SHA256)"
    for line in $NVIDIA_DEBS; do
        IFS='|' read -r n path sum <<<"$line"
        file="$dir/${path##*/}"
        if [ -r "$file" ] && [ "$(sha256sum "$file" | cut -d' ' -f1)" = "$sum" ]; then
            info "megvan: $n"; continue
        fi
        info "letöltés: $n $NVIDIA_PKG_VERSION"
        _download "$UBUNTU_MIRROR/$path" "$file" "$sum" \
            || die "nem sikerült letölteni: $UBUNTU_MIRROR/$path"
    done
    # régi verziók eltávolítása
    local keep f
    for f in "$dir"/*.deb; do
        keep=0
        for line in $NVIDIA_DEBS; do
            path=${line#*|}; path=${path%%|*}
            [ "${f##*/}" = "${path##*/}" ] && keep=1
        done
        [ "$keep" -eq 1 ] || rm -f "$f"
    done
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

    _fetch_nvidia
    ok "NVIDIA $NVIDIA_VERSION: $(find "$(nvidia_debs_dir)" -name '*.deb' | wc -l) csomag"
}
