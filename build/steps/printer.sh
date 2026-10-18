# shellcheck shell=bash
# printer — M5: Klipper + Moonraker (3D nyomtató) a Fúzióhoz
#
# A Klipper és a Moonraker Python-programok; a futtatáshoz saját, rögzített Python-környezet
# (venv) kell. Ezt egy eldobható mmdebstrap build-chrootban készítjük (a rendszerképbe
# fordító nem kerül):
#   - klippy-env, moonraker-env: a projektek saját, rögzített requirements-fájljaiból
#   - a Klipper C-segédkönyvtára (c_helper.so) előre lefordítva (a képben nincs gcc)
#   - a Klipper "Linux MCU" programja (klipper-linux-mcu): szoftveres MCU — a QEMU-teszt ezzel
#     viszi végig a teljes láncot valódi nyomtató nélkül
# Eredmény: build/cache/printer/<azonosító>/printer.tar (a /usr/lib/fusion/printer fa) + BUILD-INFO.
#
# A pip a build-chrootban a PyPI-ról tölt (hálózat kell). Ha a gazdagépen proxy van
# (HTTPS_PROXY) és saját tanúsítvány (PIP_CERT / SSL_CERT_FILE), azokat továbbadjuk.

printer_src_dir() { printf '%s/src/%s-%s' "$CACHE_DIR" "$1" "${2:0:12}"; }
webui_dir()       { printf '%s/webui' "$CACHE_DIR"; }

# git forrás egy rögzített commitra (fetch lépés, root nélkül)
_fetch_git_commit() {  # <név> <git-url> <commit>
    local name="$1" url="$2" commit="$3" dir
    dir=$(printer_src_dir "$name" "$commit")
    if [ -d "$dir/.git" ] && [ "$(git -C "$dir" rev-parse HEAD 2>/dev/null)" = "$commit" ]; then
        info "megvan: $name (${commit:0:12})"; return 0
    fi
    rm -rf "$dir"; mkdir -p "$dir"
    git -C "$dir" init -q
    git -C "$dir" fetch -q --depth 1 "$url" "$commit" || { rm -rf "$dir"; die "nem sikerült letölteni: $name ($url, $commit)"; }
    git -C "$dir" -c advice.detachedHead=false checkout -q FETCH_HEAD
    [ "$(git -C "$dir" rev-parse HEAD)" = "$commit" ] || { rm -rf "$dir"; die "$name: a commit nem egyezik"; }
    ok "$name forrás ellenőrizve: ${commit:0:12}"
}

fetch_printer_sources() {
    need git
    step "Klipper-lánc forrásai (M5)"
    _fetch_git_commit klipper "$KLIPPER_GIT" "$KLIPPER_COMMIT"
    _fetch_git_commit moonraker "$MOONRAKER_GIT" "$MOONRAKER_COMMIT"
    _fetch_git_commit mainsail-config "$MAINSAIL_CONFIG_GIT" "$MAINSAIL_CONFIG_COMMIT"
    _fetch_git_commit fluidd-config "$FLUIDD_CONFIG_GIT" "$FLUIDD_CONFIG_COMMIT"
    local line name ver url sum dest
    mkdir -p "$(webui_dir)"
    for line in $WEBUI_ZIPS; do
        IFS='|' read -r name ver url sum <<<"$line"
        dest="$(webui_dir)/$name-$ver.zip"
        if [ -r "$dest" ] && [ "$(sha256sum "$dest" | cut -d' ' -f1)" = "$sum" ]; then
            info "megvan: $name $ver"; continue
        fi
        _download "$url" "$dest" "$sum" || die "nem sikerült letölteni: $name $ver ($url)"
        ok "$name $ver ellenőrizve (SHA256)"
    done
}

# a fordítás receptjének változata: ha a lépések érdemben változnak, növelni kell
PRINTER_BUILD_REV=1

PRINTER_BUILD_DEPS="python3,python3-venv,python3-dev,python3-pip,gcc,g++,make,libffi-dev,libsodium-dev,zlib1g-dev,libjpeg-dev,ca-certificates"

printer_build_id() {
    local h
    h=$( { printf '%s\n' "$KLIPPER_COMMIT" "$MOONRAKER_COMMIT" "$PRINTER_BUILD_DEPS" "$PRINTER_BUILD_REV"
           cat "$BUILD_DIR/steps/printer.sh"; } | sha256sum | cut -c1-8)
    printf 'printer-%s-%s-%s' "${KLIPPER_COMMIT:0:8}" "${MOONRAKER_COMMIT:0:8}" "$h"
}
printer_out_dir() { printf '%s/printer/%s' "$CACHE_DIR" "$(printer_build_id)"; }
printer_ready() { [ -r "$(printer_out_dir)/BUILD-INFO" ] && [ -r "$(printer_out_dir)/printer.tar" ]; }

step_printer() {
    [ "$(id -u)" -eq 0 ] || die "a 'printer' lépéshez root kell:  sudo build/fusion-build printer  (vagy: build/fusion-build all)"
    need mmdebstrap chroot tar
    local owner="${SUDO_USER:-root}" out work ksrc msrc
    ksrc=$(printer_src_dir klipper "$KLIPPER_COMMIT"); msrc=$(printer_src_dir moonraker "$MOONRAKER_COMMIT")
    [ -d "$ksrc/.git" ] && [ -d "$msrc/.git" ] || die "hiányzik a Klipper/Moonraker forrása — előbb: build/fusion-build fetch"
    out=$(printer_out_dir); work="$OUT_DIR/printer-work"

    step "Klipper + Moonraker futtatókörnyezet (build-chroot, rögzített Python-csomagok)"
    rm_work "$work"; mkdir -p "$work/stage/klipper" "$work/stage/moonraker" "$work/result" "$OUT_DIR"
    # forrás .git nélkül; a verziót fájlba írjuk (a képben nincs git)
    tar -C "$ksrc" --exclude=.git -cf - . | tar -C "$work/stage/klipper" -xf -
    tar -C "$msrc" --exclude=.git -cf - . | tar -C "$work/stage/moonraker" -xf -
    printf '%s\n' "$KLIPPER_DESCRIBE" > "$work/stage/klipper/klippy/.version"
    printf '%s\n' "$MOONRAKER_DESCRIBE" > "$work/stage/moonraker/moonraker/.version"

    # proxy / tanúsítvány továbbadása a pip-nek (ha a gazdagépen van)
    local cert="${PIP_CERT:-${SSL_CERT_FILE:-${REQUESTS_CA_BUNDLE:-}}}" envs=""
    [ -n "$cert" ] && [ -r "$cert" ] && cp "$cert" "$work/stage/pip-ca.crt" && envs="PIP_CERT=/tmp/stage/pip-ca.crt "
    for v in HTTPS_PROXY https_proxy HTTP_PROXY http_proxy NO_PROXY no_proxy; do
        [ -n "${!v:-}" ] && envs="$envs$v='${!v}' "
    done

    cat > "$work/stage/build.sh" <<'EOF'
#!/bin/sh
set -e
P=/usr/lib/fusion/printer
mkdir -p $P/bin
mv /tmp/stage/klipper $P/klipper
mv /tmp/stage/moonraker $P/moonraker

# Klipper: saját környezet a rögzített requirements-fájlból
python3 -m venv $P/klippy-env
$P/klippy-env/bin/pip install -q --no-cache-dir --upgrade pip > /tmp/pip-k.log 2>&1 || { tail -n 30 /tmp/pip-k.log; exit 1; }
$P/klippy-env/bin/pip install -q --no-cache-dir -r $P/klipper/scripts/klippy-requirements.txt >> /tmp/pip-k.log 2>&1 || { tail -n 30 /tmp/pip-k.log; exit 1; }
# a C-segédkönyvtár előre lefordítva (futáskor nincs gcc)
cd $P/klipper/klippy && $P/klippy-env/bin/python -c 'import chelper; chelper.get_ffi(); print("c_helper.so kész")'
test -f $P/klipper/klippy/chelper/c_helper.so

# Klipper "Linux MCU" (szoftveres MCU a teszthez / gazdagép-MCU-nak)
cd $P/klipper
printf 'CONFIG_MACH_LINUX=y\n' > .config
make olddefconfig > /tmp/mcu.log 2>&1 && make -j"$(nproc)" >> /tmp/mcu.log 2>&1 || { tail -n 30 /tmp/mcu.log; exit 1; }
install -m 0755 out/klipper.elf $P/bin/klipper-linux-mcu
grep -E '^CONFIG_MACH|^CONFIG_BOARD' .config > $P/bin/klipper-linux-mcu.config || true
make clean > /dev/null 2>&1; rm -rf out .config .config.old
# a képben csak a gazdaprogram és a példakonfigurációk kellenek (a firmware-források nem)
rm -rf $P/klipper/src $P/klipper/lib $P/klipper/docs $P/klipper/test $P/klipper/.github

# Moonraker: saját környezet a rögzített requirements-fájlból
python3 -m venv $P/moonraker-env
$P/moonraker-env/bin/pip install -q --no-cache-dir --upgrade pip > /tmp/pip-m.log 2>&1 || { tail -n 30 /tmp/pip-m.log; exit 1; }
$P/moonraker-env/bin/pip install -q --no-cache-dir -r $P/moonraker/scripts/moonraker-requirements.txt >> /tmp/pip-m.log 2>&1 || { tail -n 30 /tmp/pip-m.log; exit 1; }
rm -rf $P/moonraker/docs $P/moonraker/tests $P/moonraker/.github

# előfordított Python-bájtkód (a képben csak olvasható a fájlrendszer)
$P/klippy-env/bin/python -m compileall -q $P/klipper/klippy > /dev/null || true
$P/moonraker-env/bin/python -m compileall -q $P/moonraker/moonraker > /dev/null || true

# a telepített csomagok pontos listája (ellenőrizhetőség)
{ echo "# klippy-env"; $P/klippy-env/bin/pip freeze; echo "# moonraker-env"; $P/moonraker-env/bin/pip freeze; } > /tmp/pip-freeze.txt
python3 --version > /tmp/python-version.txt
echo PRINTER-BUILD-OK
EOF
    chmod +x "$work/stage/build.sh"

    # shellcheck disable=SC2016  # a $1-et az mmdebstrap helyettesíti be
    mmdebstrap --mode=root --variant=minbase --arch=amd64 \
        --components=main,universe \
        --include="$PRINTER_BUILD_DEPS" \
        --dpkgopt='path-exclude=/usr/share/doc/*' \
        --dpkgopt='path-exclude=/usr/share/man/*' \
        --dpkgopt='path-exclude=/usr/share/locale/*' \
        --customize-hook="cp -a '$work/stage' \"\$1/tmp/stage\"" \
        --customize-hook="chroot \"\$1\" env -i PATH=/usr/sbin:/usr/bin:/sbin:/bin HOME=/root LANG=C.UTF-8 $envs /tmp/stage/build.sh" \
        --customize-hook="tar -C \"\$1/usr/lib/fusion/printer\" -cf '$work/result/printer.tar' . && cp \"\$1/tmp/pip-freeze.txt\" \"\$1/tmp/python-version.txt\" '$work/result/'" \
        noble "$work/chroot" \
        "deb $ROOTFS_MIRROR noble main universe" \
        "deb $ROOTFS_MIRROR noble-updates main universe" \
        "deb $ROOTFS_SECURITY noble-security main universe" \
        || die "a Klipper/Moonraker környezet építése nem sikerült (a hiba fent látszik)"

    rm -rf "$out"; mkdir -p "$out"
    cp "$work/result/"* "$out/"
    printf 'klipper=%s (%s)\nmoonraker=%s (%s)\npython=%s\n' \
        "$KLIPPER_DESCRIBE" "$KLIPPER_COMMIT" "$MOONRAKER_DESCRIBE" "$MOONRAKER_COMMIT" \
        "$(cat "$out/python-version.txt")" > "$out/BUILD-INFO"
    rm_work "$work"
    chown -R "$owner": "$CACHE_DIR/printer" 2>/dev/null || true
    ok "kész: $out ($(du -sm "$out/printer.tar" | cut -f1) MiB)"
}

ensure_printer() {
    if printer_ready; then info "Klipper-környezet naprakész: $(printer_out_dir)"; return 0; fi
    if [ "$(id -u)" -ne 0 ]; then sudo -E "$BUILD_DIR/fusion-build" printer; else step_printer; fi
}
