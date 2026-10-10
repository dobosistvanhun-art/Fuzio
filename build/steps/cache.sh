# shellcheck shell=bash
# FusionOS build — a rögzített letöltések (build/cache) mentése és visszatöltése (A3, 0.0.30)
#
# Miért: az Ubuntu 2026-ban kivezette a 470-es NVIDIA-ágat; ha a rögzített csomagok (470-server, a 6.8-as kernel)
# eltűnnek a tárolóból, a FusionOS a mentett cache-ből továbbra is buildelhető.
#
#   cache-export [<mappa>]   build/cache → <mappa>/fusionos-cache-<dátum>.tar.zst (+ .sha256)
#                            (alapértelmezett mappa: ~/Fusion) — a build/cache/root kimarad (a .deb-ekből újra kibontható)
#   cache-import <fájl>      a mentés visszatöltése a build/cache-be (a meglévő fájlokat felülírja)

step_cache_export() {
    not_root
    local dir="${1:-$HOME/Fusion}" stamp out
    [ -d "$CACHE_DIR" ] || die "nincs build/cache — előbb: build/fusion-build fetch"
    mkdir -p "$dir" || die "a cél mappa nem hozható létre: $dir"
    stamp=$(date +%Y%m%d-%H%M)
    out="$dir/fusionos-cache-$stamp.tar.zst"
    step "A build/cache mentése → $out"
    info "tartalom (a build/cache/root kimarad):"
    (cd "$CACHE_DIR" && du -sh -- * 2>/dev/null | grep -v '[[:space:]]root$' | sed 's/^/      /')
    # a mentés leírása (a fájlok listája SHA-256-tal kerül a csomagba)
    local man="$CACHE_DIR/CACHE-MANIFEST.txt"
    {
        echo "FusionOS build/cache mentés — $(date -Iseconds)"
        echo "FusionOS-verzió: ${FUSION_VERSION:-?}"
        echo
        (cd "$CACHE_DIR" && find . -path ./root -prune -o -type f \( -name '*.deb' -o -name '*.zip' -o -name '*.tar*' \) -print \
            | sort | xargs -r sha256sum)
    } > "$man"
    local err; err=$(mktemp)
    if ! tar -C "$CACHE_DIR" --exclude=./root --numeric-owner -cf - . 2>"$err" | zstd -T0 -10 -q -o "$out" -f \
        || [ -s "$err" ]; then
        cat "$err" >&2; rm -f "$err" "$out"
        die "a mentés nem sikerült (olvashatatlan fájl? → sudo chown -R \$USER build/cache)"
    fi
    rm -f "$err"
    (cd "$dir" && sha256sum "$(basename "$out")" > "$(basename "$out").sha256")
    ok "kész: $out ($(du -h "$out" | cut -f1))"
    info "Másold biztonságos helyre (Google Drive / külső lemez). Visszatöltés: build/fusion-build cache-import <fájl>"
}

step_cache_import() {
    not_root
    local f="${1:-}"
    [ -n "$f" ] && [ -f "$f" ] || die "használat: build/fusion-build cache-import <fusionos-cache-….tar.zst>"
    if [ -f "$f.sha256" ]; then
        step "Ellenőrzés (SHA-256)"
        (cd "$(dirname "$f")" && sha256sum -c "$(basename "$f").sha256") || die "a mentés sérült (SHA-256 eltér)"
    fi
    step "Visszatöltés → build/cache"
    mkdir -p "$CACHE_DIR"
    zstd -dc "$f" | tar -C "$CACHE_DIR" -xf - || die "a kibontás nem sikerült"
    if [ -f "$CACHE_DIR/CACHE-MANIFEST.txt" ]; then
        (cd "$CACHE_DIR" && sed -n '/^[0-9a-f]\{64\}  /p' CACHE-MANIFEST.txt | sha256sum -c --quiet) \
            || die "a visszatöltött fájlok egy része eltér a leírástól"
    fi
    ok "kész — a build a mentett csomagokból fut (fetch: a meglévő, ellenőrzött fájlokat nem tölti le újra)"
}
