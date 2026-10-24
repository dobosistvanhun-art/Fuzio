# shellcheck shell=bash
# icu — a Windows rendszer-ICU-ja a Fúzió Windows Runtime-hoz (fwr)
#
# A Windows 10 (1903) óta a System32-ben van az ICU (icuuc.dll, icuin.dll, icu.dll), és a Qt 6-os
# Windows-programok egy része erre épít: a LightBurn 2.2.00 Qt6Core.dll-je az icuuc.dll-t importálja,
# nélküle a program el sem indul (c0000135). A Wine-ban nincs ilyen DLL, ezért itt készül:
#   - az ICU forrásából (ICU_URL, SHA256-tal ellenőrizve), MinGW-vel, statikusan (más DLL nem kell hozzá),
#   - verziószám nélküli függvénynevekkel (U_DISABLE_RENAMING), ahogy a Windows exportálja őket,
#   - icuuc.dll: a teljes ICU (common + i18n + adatok) a C API-val,
#     icuin.dll és icu.dll: továbbító DLL-ek az icuuc.dll-re (mint a Windowsban, egy példány fut).
# Eldobható mmdebstrap build-chrootban fordul; az eredmény: build/cache/icu/<azonosító>/*.dll.
# Root kell; 4 magon ~10 perc, utána a gyorsítótárból jön. Az fwr a környezet előkészítésekor
# a program Windows-környezetének System32 mappájába másolja (fwr prepare).

ICU_BUILD_REV=1
ICU_BUILD_DEPS="make,g++,python3,gcc-mingw-w64-x86-64-posix,g++-mingw-w64-x86-64-posix,binutils-mingw-w64-x86-64"

icu_src_file() { printf '%s/src/%s' "$CACHE_DIR" "${ICU_URL##*/}"; }
icu_build_id() {
    local h
    h=$(printf '%s\n%s\n%s\n' "$ICU_SHA256" "$ICU_BUILD_REV" "$ICU_BUILD_DEPS" | sha256sum | cut -c1-8)
    printf 'icu-%s-%s' "$ICU_VERSION" "$h"
}
icu_out_dir() { printf '%s/icu/%s' "$CACHE_DIR" "$(icu_build_id)"; }
icu_ready() { local d; d=$(icu_out_dir); [ -r "$d/BUILD-INFO" ] && [ -r "$d/icuuc.dll" ] && [ -r "$d/icuin.dll" ] && [ -r "$d/icu.dll" ]; }

# a forrás letöltése (fetch lépés, root nélkül), SHA256-tal
fetch_icu_source() {
    local f; f=$(icu_src_file)
    if [ -r "$f" ] && [ "$(sha256sum "$f" | cut -d' ' -f1)" = "$ICU_SHA256" ]; then
        info "megvan: ICU $ICU_VERSION forrás"; return 0
    fi
    step "ICU $ICU_VERSION forrás ($ICU_URL)"
    mkdir -p "$(dirname "$f")"
    _download "$ICU_URL" "$f" "$ICU_SHA256" || die "nem sikerült letölteni az ICU forrását: $ICU_URL"
    ok "ICU forrás ellenőrizve (SHA256)"
}

step_icu() {
    [ "$(id -u)" -eq 0 ] || die "az 'icu' lépéshez root kell:  sudo build/fusion-build icu  (vagy: build/fusion-build all)"
    need mmdebstrap chroot tar
    local owner="${SUDO_USER:-root}" src out work jobs
    src=$(icu_src_file); out=$(icu_out_dir); work="$OUT_DIR/icu-work"
    [ -r "$src" ] && [ "$(sha256sum "$src" | cut -d' ' -f1)" = "$ICU_SHA256" ] || die "hiányzik az ICU forrása — előbb: build/fusion-build fetch"

    step "ICU $ICU_VERSION fordítása Windowsra (icuuc.dll, icuin.dll, icu.dll) — első alkalommal ~10 perc"
    rm_work "$work"; mkdir -p "$work/src" "$work/result" "$OUT_DIR"
    cp "$src" "$work/src/icu.tgz"
    jobs=$(nproc)
    cat > "$work/src/fusion-build.sh" <<EOS
#!/bin/sh
set -e
cd /tmp/icu-src
tar xzf icu.tgz
# 1. a gazdagépre (az adatfordító eszközök a kereszt-fordításhoz)
mkdir native && cd native
../icu/source/configure --disable-tests --disable-samples > /tmp/icu-native.log 2>&1 || { tail -n 30 /tmp/icu-native.log; exit 1; }
make -j$jobs >> /tmp/icu-native.log 2>&1 || { tail -n 40 /tmp/icu-native.log; exit 1; }
cd ..
# 2. Windowsra: statikus könyvtárak, verziószám nélküli nevek, beépített adatok
mkdir win && cd win
CC=x86_64-w64-mingw32-gcc-posix CXX=x86_64-w64-mingw32-g++-posix \\
CPPFLAGS="-DU_DISABLE_RENAMING=1 -DU_STATIC_IMPLEMENTATION" CFLAGS=-O2 CXXFLAGS=-O2 \\
../icu/source/configure --host=x86_64-w64-mingw32 --with-cross-build=/tmp/icu-src/native \\
    --enable-static --disable-shared --with-data-packaging=static \\
    --disable-tests --disable-samples --disable-extras --disable-tools --disable-layoutex > /tmp/icu-win.log 2>&1 \\
    || { tail -n 30 /tmp/icu-win.log; exit 1; }
make -j$jobs >> /tmp/icu-win.log 2>&1 || { tail -n 40 /tmp/icu-win.log; exit 1; }
# 3. a DLL-ek: az exportlista a C API (a C++ belső nevek nem — a Windows sem exportálja őket)
mkdir out
api() { x86_64-w64-mingw32-nm -g --defined-only "\$1" | awk '\$2 ~ /^[TDRB]\$/ {print \$3}' | grep -vE '^(_|\\.)' | sort -u; }
api lib/libsicuuc.a > out/uc.txt
api lib/libsicuin.a > out/in.txt
{ echo EXPORTS; cat out/uc.txt out/in.txt | awk '!s[\$0]++'; } > out/icuuc.def
x86_64-w64-mingw32-g++-posix -shared -o out/icuuc.dll out/icuuc.def \\
    -Wl,--whole-archive lib/libsicuin.a lib/libsicuuc.a -Wl,--no-whole-archive lib/sicudt.a \\
    -static -static-libgcc -static-libstdc++ -s
# icuin.dll: az i18n rész, icu.dll: minden — továbbítással az icuuc.dll-re
{ echo EXPORTS; awk '{print \$1" = icuuc."\$1}' out/in.txt; } > out/icuin.def
{ echo EXPORTS; cat out/uc.txt out/in.txt | awk '!s[\$0]++ {print \$1" = icuuc."\$1}'; } > out/icu.def
echo 'void fusion_icu_forwarder(void){}' > out/fwd.c
x86_64-w64-mingw32-gcc-posix -shared -nostdlib -Wl,--entry=0 -s -o out/icuin.dll out/fwd.c out/icuin.def
x86_64-w64-mingw32-gcc-posix -shared -nostdlib -Wl,--entry=0 -s -o out/icu.dll out/fwd.c out/icu.def
# ellenőrzés: a Qt által használt alapfüggvények ott vannak
for f in u_strToUpper u_strToLower ucnv_open ucol_open ucol_strcoll uidna_openUTS46 ubrk_open unorm2_getNFCInstance; do
    grep -qx "\$f" out/uc.txt out/in.txt || { echo "hiányzik az exportból: \$f"; exit 1; }
done
EOS
    chmod +x "$work/src/fusion-build.sh"

    # shellcheck disable=SC2016  # a $1-et az mmdebstrap helyettesíti be
    mmdebstrap --mode=root --variant=minbase --arch=amd64 \
        --components=main,universe \
        --include="$ICU_BUILD_DEPS" \
        --dpkgopt='path-exclude=/usr/share/doc/*' \
        --dpkgopt='path-exclude=/usr/share/man/*' \
        --dpkgopt='path-exclude=/usr/share/locale/*' \
        --customize-hook="cp -a '$work/src' \"\$1/tmp/icu-src\"" \
        --customize-hook='chroot "$1" /tmp/icu-src/fusion-build.sh' \
        --customize-hook="cp \"\$1\"/tmp/icu-src/win/out/*.dll '$work/result/'" \
        noble "$work/chroot" \
        "deb $ROOTFS_MIRROR noble main universe" \
        "deb $ROOTFS_MIRROR noble-updates main universe" \
        "deb $ROOTFS_SECURITY noble-security main universe" \
        || die "az ICU fordítása nem sikerült (a hiba fent látszik)"

    rm -rf "$out"; mkdir -p "$out"
    cp "$work/result/"*.dll "$out/"
    printf 'icu=%s\nurl=%s\nsha256=%s\nrev=%s\n' "$ICU_VERSION" "$ICU_URL" "$ICU_SHA256" "$ICU_BUILD_REV" > "$out/BUILD-INFO"
    rm_work "$work"
    chown -R "$owner": "$CACHE_DIR/icu" 2>/dev/null || true
    ok "kész: $out ($(du -sm "$out" | cut -f1) MiB)"
}
