# shellcheck shell=bash
# images — tesztelőknek kiadható, Rufusszal / balenaEtcherrel pendrive-ra írható képfájlok (root nélkül)
#
#   fuzio-<verzió>-pendrive.img.xz   a Fúzió a pendrive-ról fut (16 GB-os vagy nagyobb pendrive)
#   fuzio-<verzió>-telepito.img.xz   telepítő pendrive: a Fúzió Telepítő egy belső lemezre telepít (4 GB+)
#   SHA256SUMS, OLVASSEL-tesztelok.txt
# A kimenet: build/out/release/kiadas/ — a .img a lemezkép bájtra pontos másolata (DD-mód), xz-vel tömörítve.

step_images() {
    not_root
    need xz sha256sum
    local out; out=$(variant_dir)
    local dst="$out/kiadas" name="fuzio-${FUSION_VERSION}-${FUSION_MILESTONE}"
    [ -r "$out/fusionos.img" ] || die "előbb: build/fusion-build all (hiányzik: $out/fusionos.img)"
    [ -r "$out/fusionos-telepito.img" ] || die "előbb: build/fusion-build all (hiányzik: $out/fusionos-telepito.img)"
    mkdir -p "$dst"
    rm -f "$dst"/*.img.xz "$dst"/*.tmp "$dst"/SHA256SUMS
    step "Képfájlok a tesztelőknek (Rufus / balenaEtcher): $dst"
    local src target t0
    for pair in "fusionos.img:$name-pendrive.img.xz" "fusionos-telepito.img:$name-telepito.img.xz"; do
        src="$out/${pair%%:*}"; target="$dst/${pair#*:}"
        t0=$(date +%s)
        info "tömörítés: $(basename "$src") ($(( $(stat -c %s "$src") / 1048576 )) MiB) → $(basename "$target")"
        xz -T0 -6 -c --check=crc32 "$src" > "$target.tmp"      # crc32: a Rufus és az Etcher is ismeri
        mv "$target.tmp" "$target"
        info "  kész: $(( $(stat -c %s "$target") / 1048576 )) MiB, $(( $(date +%s) - t0 )) mp"
    done
    (cd "$dst" && sha256sum ./*.img.xz | sed 's|  \./|  |' > SHA256SUMS)
    _images_readme "$dst/OLVASSEL-tesztelok.txt" "$name"
    ok "kész: $dst"
    ls -la "$dst" | sed 's/^/    /'
}

_images_readme() {  # <fájl> <név>
    local mib; mib=$(image_total_mib)
    cat > "$1" <<EOF
Fúzió ${FUSION_VERSION} (${FUSION_MILESTONE}) — pendrive-képfájlok tesztelőknek
=====================================================================

Két fájl van, válaszd ki, mire kell:

1) $2-pendrive.img.xz
   A Fúzió a pendrive-ról fut, a gép lemezéhez nem nyúl.
   Pendrive: legalább 16 GB (a kép ${mib} MiB). A pendrive teljes tartalma törlődik.

2) $2-telepito.img.xz
   Telepítő pendrive: a „Fúzió Telepítő” a gép egyik lemezére telepíti a Fúziót.
   A kiválasztott lemez TÖRLŐDIK (gépelt megerősítés után). Pendrive: legalább 4 GB.

Felírás (a .img.xz fájlt nem kell kicsomagolni):
  - balenaEtcher (Windows, macOS, Linux): Flash from file → a .img.xz fájl → Select target → a pendrive → Flash.
  - Rufus (Windows): Eszköz → a pendrive; Rendszerindítás kiválasztása → KIJELÖLÉS → a .img.xz fájl → INDÍTÁS.
    (A Rufus a képfájlt bájtra pontosan írja ki — DD-mód; más beállítás nem kell.)
  - Linux parancssorból: xz -dc $2-pendrive.img.xz | sudo dd of=/dev/sdX bs=4M conv=fsync status=progress

Indítás:
  - A gépen UEFI-mód kell, a Secure Boot legyen KIKAPCSOLVA (a Fúzió nincs aláírva).
  - Bekapcsoláskor a gép indítómenüje (HP: F9, Dell: F12, Lenovo: F12, ASUS: F8 vagy Esc) → a pendrive.
  - Az első indítás 1–2 perc is lehet; a felhasználó: fusion, jelszó: fusion.

Hiba esetén: Beállítások → Hibajelentés → a jelentés a Letöltésekbe kerül (személyes adatok nélkül) —
ezt kérjük elküldeni. Ha a felület nem indul: Ctrl+Alt+F2, belépés (fusion / fusion), majd
  fusion-report -o /run/media/fusion/<pendrive>

Ellenőrzés (nem kötelező): az SHA256SUMS fájlban lévő összeg egyezzen a letöltött fájléval
  (Windows: certutil -hashfile <fájl> SHA256; Linux: sha256sum -c SHA256SUMS).
EOF
}
