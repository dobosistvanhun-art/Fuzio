# shellcheck shell=bash
# wine — KÍSÉRLETI M4-MEGOLDÁS (proof-of-concept), nem a FusionOS végleges architektúrája.
#
# Az M4 funkcionális követelménye: a Windows-os LightBurn x64 fusson a FusionOS alatt, és a
# valódi GRBL lézervezérlőt USB-n, COM3-ként érje el. Ehhez az M4-ben egy kísérleti
# futtató kell; ez most a Wine, forrásból fordítva. A FusionOS-szintű rész ettől független:
# a COM3 a Fusion eszközréteg (M3) szerepére mutat (/dev/fusion/laser).
#
# Miért forrásból: az új WoW64 mód (egy 64 bites Wine futtat 32 és 64 bites
# Windows-programot is, 32 bites Linux-könyvtárak nélkül) fordítási opció
# (--enable-archs=i386,x86_64). A forrás a WINE_GIT tárolóból jön, a WINE_COMMIT-tal
# ellenőrizve, az fwr/wine-patches/*.patch kísérleti javításokkal.
#
# Eldobható mmdebstrap build-chrootban fordul (a rendszerképbe fordító nem kerül);
# az eredmény: build/cache/wine/<azonosító>/ — telepített fa + a diagnosztikai
# Windows-programok (fwr-comtest.exe, fwr-gltest.exe). Root kell; első alkalommal
# hosszú (4 magon ~1 óra), utána a gyorsítótárból jön.

wine_src_dir() { printf '%s/src/wine-%s' "$CACHE_DIR" "$WINE_VERSION"; }

# a build azonosítója: verzió + commit + a fordítás tényleges bemenetei (javítások,
# diagnosztikai programok, konfiguráció) — a megjegyzések nem számítanak bele
wine_build_id() {
    local h
    h=$( { cat "$FUSION_ROOT"/fwr/wine-patches/*.patch "$FUSION_ROOT"/fwr/tools/*.c 2>/dev/null
           printf '%s\n%s\n%s\n' "$WINE_CONFIGURE" "$WINE_BUILD_DEPS" "$WINE_BUILD_REV"; } \
        | sha256sum | cut -c1-8)
    printf 'wine-%s-%s-%s' "$WINE_VERSION" "${WINE_COMMIT:0:8}" "$h"
}
wine_out_dir() { printf '%s/wine/%s' "$CACHE_DIR" "$(wine_build_id)"; }
wine_ready() { [ -r "$(wine_out_dir)/BUILD-INFO" ] && [ -r "$(wine_out_dir)/wine.tar" ]; }

# a forrás letöltése (fetch lépés, root nélkül): git clone, commit-ellenőrzéssel
fetch_wine_source() {
    local src; src=$(wine_src_dir)
    need git
    if [ -d "$src/.git" ] && [ "$(git -C "$src" rev-parse HEAD 2>/dev/null)" = "$WINE_COMMIT" ]; then
        info "megvan: Wine $WINE_VERSION forrás (${WINE_COMMIT:0:12})"
        return 0
    fi
    step "Wine $WINE_VERSION forrás ($WINE_GIT, $WINE_REF)"
    rm -rf "$src"; mkdir -p "$(dirname "$src")"
    git -c advice.detachedHead=false clone -q --depth 1 --branch "$WINE_REF" "$WINE_GIT" "$src" \
        || die "nem sikerült letölteni a Wine forrását: $WINE_GIT ($WINE_REF)"
    local got; got=$(git -C "$src" rev-parse HEAD)
    [ "$got" = "$WINE_COMMIT" ] || { rm -rf "$src"; die "a Wine forrás commitja nem egyezik: $got (várt: $WINE_COMMIT)"; }
    ok "Wine forrás ellenőrizve: $WINE_REF = ${WINE_COMMIT:0:12}"
}

WINE_BUILD_DEPS="make,gcc,g++,flex,bison,gettext,pkgconf,gcc-mingw-w64-x86-64,gcc-mingw-w64-i686,\
libunwind-dev,libgnutls28-dev,libfreetype-dev,libfontconfig-dev,libegl-dev,libgl-dev,libvulkan-dev,\
libdbus-1-dev,libx11-dev,libxext-dev,libxrandr-dev,libxi-dev,libxcursor-dev,libxfixes-dev,\
libxinerama-dev,libxcomposite-dev,libxrender-dev,libxxf86vm-dev,libxkbfile-dev,binutils"

# a fordítás receptjének változata: ha a fusion-build.sh lépései érdemben változnak, növelni kell
WINE_BUILD_REV=1

# a Wine konfigurációja: WoW64, csak a FusionOS-ben használt alrendszerek
WINE_CONFIGURE="--prefix=/usr/lib/fusion/wine --enable-archs=i386,x86_64 --disable-tests \
--with-x --with-gnutls --with-freetype --with-fontconfig --with-opengl --with-vulkan --with-dbus \
--without-wayland --without-pulse --without-alsa --without-oss --without-gstreamer --without-ffmpeg \
--without-cups --without-sane --without-v4l2 --without-krb5 --without-gssapi --without-netapi \
--without-pcap --without-pcsclite --without-sdl --without-usb --without-capi --without-opencl \
--without-osmesa --without-gphoto --without-udev"

step_wine() {
    [ "$(id -u)" -eq 0 ] || die "a 'wine' lépéshez root kell:  sudo build/fusion-build wine  (vagy: build/fusion-build all)"
    need mmdebstrap chroot tar
    local owner="${SUDO_USER:-root}" src out work
    src=$(wine_src_dir); out=$(wine_out_dir); work="$OUT_DIR/wine-work"
    [ -d "$src/.git" ] || die "hiányzik a Wine forrása — előbb: build/fusion-build fetch"
    [ "$(git -C "$src" rev-parse HEAD)" = "$WINE_COMMIT" ] || die "a Wine forrás commitja nem egyezik — futtasd: build/fusion-build fetch"

    step "Wine $WINE_VERSION fordítása (WoW64, build-chroot) — első alkalommal hosszú, 4 magon ~1 óra"
    rm -rf "$work"; mkdir -p "$work/src" "$work/result" "$OUT_DIR"
    # a forrás .git nélkül, a javításokkal (a build-chrootba ez kerül)
    tar -C "$src" --exclude=.git -cf - . | tar -C "$work/src" -xf -
    local p
    for p in "$FUSION_ROOT"/fwr/wine-patches/*.patch; do
        [ -r "$p" ] || continue
        info "javítás: $(basename "$p")"
        (cd "$work/src" && patch -p1 --no-backup-if-mismatch -s < "$p") || die "a javítás nem alkalmazható: $p"
    done
    mkdir -p "$work/src/fusion-tools"; cp "$FUSION_ROOT"/fwr/tools/*.c "$work/src/fusion-tools/"

    local jobs; jobs=$(nproc)
    cat > "$work/src/fusion-build.sh" <<EOF
#!/bin/sh
set -e
cd /tmp/wine-src
./configure $WINE_CONFIGURE > /tmp/wine-configure.log 2>&1 || { tail -n 40 /tmp/wine-configure.log; exit 1; }
make -j$jobs > /tmp/wine-make.log 2>&1 || { tail -n 60 /tmp/wine-make.log; exit 1; }
make install DESTDIR=/tmp/wine-inst > /tmp/wine-install.log 2>&1 || { tail -n 40 /tmp/wine-install.log; exit 1; }
# a Unix-oldali binárisok hibakereső adatai nélkül (a Windows-oldali PE-k maradnak)
find /tmp/wine-inst -type f \( -name '*.so' -o -path '*/bin/*' \) -exec strip --strip-unneeded {} + 2>/dev/null || true
# diagnosztikai Windows-programok (64 bites PE)
cd /tmp/wine-src/fusion-tools
x86_64-w64-mingw32-gcc -O2 -s -o fwr-comtest.exe fwr-comtest.c
x86_64-w64-mingw32-gcc -O2 -s -o fwr-gltest.exe fwr-gltest.c -lopengl32 -lgdi32
grep -E '^(configure: WARNING|configure: libs)' /tmp/wine-configure.log > /tmp/wine-configure.summary || true
EOF
    chmod +x "$work/src/fusion-build.sh"

    # shellcheck disable=SC2016  # a $1-et az mmdebstrap helyettesíti be
    mmdebstrap --mode=root --variant=minbase --arch=amd64 \
        --components=main,universe \
        --include="$WINE_BUILD_DEPS" \
        --dpkgopt='path-exclude=/usr/share/doc/*' \
        --dpkgopt='path-exclude=/usr/share/man/*' \
        --dpkgopt='path-exclude=/usr/share/locale/*' \
        --customize-hook="cp -a '$work/src' \"\$1/tmp/wine-src\"" \
        --customize-hook='chroot "$1" /tmp/wine-src/fusion-build.sh' \
        --customize-hook="tar -C \"\$1/tmp/wine-inst/usr/lib/fusion/wine\" -cf '$work/result/wine.tar' . && cp \"\$1\"/tmp/wine-src/fusion-tools/*.exe '$work/result/' && cp \"\$1/tmp/wine-configure.summary\" '$work/result/configure.summary'" \
        noble "$work/chroot" \
        "deb $ROOTFS_MIRROR noble main universe" \
        "deb $ROOTFS_MIRROR noble-updates main universe" \
        "deb $ROOTFS_SECURITY noble-security main universe" \
        || die "a Wine fordítása nem sikerült (a hiba fent látszik)"

    rm -rf "$out"; mkdir -p "$out"
    cp "$work/result/"* "$out/"
    printf 'wine=%s\nref=%s\ncommit=%s\nconfigure=%s\npatches=%s\n' \
        "$WINE_VERSION" "$WINE_REF" "$WINE_COMMIT" "$WINE_CONFIGURE" \
        "$(for p in "$FUSION_ROOT"/fwr/wine-patches/*.patch; do printf '%s ' "$(basename "$p")"; done)" > "$out/BUILD-INFO"
    rm -rf "$work"
    chown -R "$owner": "$CACHE_DIR/wine" 2>/dev/null || true
    ok "kész: $out ($(du -sm "$out/wine.tar" | cut -f1) MiB)"
}

# a nem-root lépésekből: sudo-val fordít, ha még nincs kész build
ensure_wine() {
    if wine_ready; then info "Wine naprakész: $(wine_out_dir)"; return 0; fi
    if [ "$(id -u)" -ne 0 ]; then sudo "$BUILD_DIR/fusion-build" wine; else step_wine; fi
}
