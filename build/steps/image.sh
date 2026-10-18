# shellcheck shell=bash
# image — GPT lemezkép (ESP + A + B + DATA) a VirtualBoxhoz / QEMU-hoz, root nélkül.

_data_readme() {
    cat <<EOF
Fúzió adatpartíció (FUSION_DATA)

Ide kerülnek majd a felhasználói adatok, beállítások, a Windows-programok
környezetei és a Klipper-konfiguráció. Az M0 ezt a partíciót nem használja.
EOF
}

step_image() {
    not_root
    need sfdisk mkfs.vfat mcopy mmd mkfs.ext4 truncate dd
    local out; out=$(variant_dir)
    [ -d "$out/esp" ] || die "előbb futtasd: build/fusion-build build"
    local rootimg; rootimg=$(rootfs_img)
    [ -r "$rootimg" ] || die "nincs rendszerkép — előbb: build/fusion-build rootfs (vagy all)"
    local img="$out/fusionos.img" total; total=$(image_total_mib)

    step "Lemezkép készítése ($total MiB, ritka fájl)"
    rm -f "$img"
    truncate -s "${total}M" "$img"
    sfdisk_script "$IMAGE_DATA_MIB" | sfdisk --quiet --no-reread --no-tell-kernel "$img" >/dev/null
    info "GPT: $PART_ESP ${ESP_MIB}M, $PART_A ${SLOT_MIB}M, $PART_B ${SLOT_MIB}M, $PART_DATA ${IMAGE_DATA_MIB}M"

    # ESP: FAT32 fájlrendszer külön fájlban, majd a helyére másolva
    local espimg="$out/esp.fat"
    rm -f "$espimg"
    truncate -s "${ESP_MIB}M" "$espimg"
    mkfs.vfat -F 32 -n FUSION_ESP "$espimg" >/dev/null
    local d f rel
    while IFS= read -r d; do
        rel=${d#"$out/esp"}; [ -n "$rel" ] && mmd -i "$espimg" "::$rel"
    done < <(find "$out/esp" -mindepth 1 -type d | sort)
    while IFS= read -r f; do
        rel=${f#"$out/esp"}; mcopy -i "$espimg" "$f" "::$rel"
    done < <(find "$out/esp" -type f | sort)
    dd if="$espimg" of="$img" bs=1M seek=1 conv=notrunc,sparse status=none
    rm -f "$espimg"

    # A slot: a Fúzió rendszerkép (EROFS)
    dd if="$rootimg" of="$img" bs=1M seek=$((1 + ESP_MIB)) conv=notrunc,sparse status=none
    info "A slot: $(basename "$rootimg") ($(( $(stat -c %s "$rootimg") / 1024 / 1024 )) MiB); B slot: üres"

    # DATA: ext4, a tartalmát a -d kapcsoló tölti fel (root nélkül)
    local dataimg="$out/data.ext4" stage="$out/data-stage"
    rm -rf "$stage" "$dataimg"; mkdir -p "$stage"
    _data_readme > "$stage/README.txt"
    # a teszthez: melyik lemezkép DATA-járól indult a rendszer (több lemezes boot-próba)
    [ -n "${FUSION_IMAGE_MARKER:-}" ] && echo "$FUSION_IMAGE_MARKER" > "$stage/.fusion-test-marker"
    # a teszthez: A/B frissítés próbája (a fusion-selftest ennek alapján frissít és indít újra)
    [ -n "${FUSION_TEST_AB:-}" ] && echo "$FUSION_TEST_AB" > "$stage/.fusion-test-ab"
    truncate -s "${IMAGE_DATA_MIB}M" "$dataimg"
    mkfs.ext4 -q -F -E nodiscard -L FUSION_DATA -d "$stage" "$dataimg"
    dd if="$dataimg" of="$img" bs=1M seek=$((1 + ESP_MIB + 2 * SLOT_MIB)) conv=notrunc,sparse status=none
    rm -rf "$dataimg" "$stage"

    ok "kész: $img (lemezen ténylegesen: $(du -h "$img" | cut -f1))"
}
