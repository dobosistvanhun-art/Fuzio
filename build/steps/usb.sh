# shellcheck shell=bash
# usb — a FusionOS felírása egy USB-pendrive-ra. Root kell hozzá.
#
# Biztonság:
#   - csak teljes lemezt fogad el (pl. /dev/sdc, nem /dev/sdc1);
#   - csak USB-n csatlakozó eszközt;
#   - méretkorlát (USB_MIN_GIB .. USB_MAX_GIB);
#   - nem lehet rajta a futó rendszer (/, /boot, /home stb.);
#   - a felhasználónak be kell gépelnie az eszköz nevét a megerősítéshez.

step_usb() {
    local dev="${1:-}" esp_src
    [ "$(id -u)" -eq 0 ] || die "az 'usb' lépéshez root kell:  sudo build/fusion-build usb /dev/sdX"
    need lsblk sfdisk wipefs mkfs.vfat mkfs.ext4 udevadm partx blockdev mmd mcopy
    [ -n "$dev" ] || die "add meg a pendrive-ot, pl.:  sudo build/fusion-build usb /dev/sdc   (lista: lsblk -d -o NAME,TRAN,SIZE,MODEL)"
    esp_src="$OUT_DIR/release/esp"
    [ -d "$esp_src/EFI" ] || die "nincs kész release ESP — előbb (root nélkül): build/fusion-build all"
    local rootimg; rootimg=$(rootfs_img)
    [ -r "$rootimg" ] || die "nincs rendszerkép — előbb: build/fusion-build all"

    dev=$(readlink -f "$dev")
    [ -b "$dev" ] || die "nem blokkeszköz: $dev"
    local type; type=$(lsblk -dno TYPE "$dev" 2>/dev/null)
    if [ "$type" = "part" ]; then
        local parent; parent=$(lsblk -dno PKNAME "$dev")
        die "$dev egy partíció. A teljes pendrive kell: /dev/$parent   (a teljes eszköz törlődik!)"
    fi
    [ "$type" = "disk" ] || die "$dev nem lemez (típus: ${type:-ismeretlen})"

    local tran size_b size_gib model vendor
    tran=$(lsblk -dno TRAN "$dev" | tr -d ' ')
    size_b=$(lsblk -dbno SIZE "$dev" | tr -d ' ')
    size_gib=$((size_b / 1024 / 1024 / 1024))
    model=$(lsblk -dno MODEL "$dev" | sed 's/ *$//')
    vendor=$(lsblk -dno VENDOR "$dev" | sed 's/ *$//')
    [ "$tran" = "usb" ] || die "$dev nem USB-eszköz (csatlakozás: ${tran:-ismeretlen}). Belső lemezre a FusionOS nem írható."
    [ "$size_gib" -ge "$USB_MIN_GIB" ] || die "$dev túl kicsi: ${size_gib} GiB (legalább $USB_MIN_GIB GiB kell)"
    [ "$size_gib" -le "$USB_MAX_GIB" ] || die "$dev gyanúsan nagy: ${size_gib} GiB (legfeljebb $USB_MAX_GIB GiB) — biztos, hogy pendrive?"

    # nem lehet rajta a futó rendszer
    local mp
    while read -r mp; do
        case "$mp" in
            /|/boot|/boot/efi|/home|/usr|/var) die "$dev tartalmazza a futó rendszer egy részét ($mp) — megszakítva." ;;
        esac
    done < <(lsblk -lno MOUNTPOINTS "$dev" | sed '/^$/d')

    step "Célpendrive"
    info "Eszköz:  $dev"
    info "Típus:   ${vendor:+$vendor }${model:-ismeretlen}"
    info "Méret:   ${size_gib} GiB, USB"
    info "Jelenlegi tartalom:"
    lsblk -o NAME,SIZE,FSTYPE,LABEL,MOUNTPOINTS "$dev" | sed 's/^/      /'
    echo
    printf '%sA pendrive TELJES tartalma törlődik.%s\n' "$C_ERR" "$C_0"
    printf 'Megerősítéshez írd be az eszköz nevét (%s): ' "$(basename "$dev")"
    local answer; read -r answer
    [ "$answer" = "$(basename "$dev")" ] || die "megszakítva (a beírt név nem egyezik)."

    step "Leválasztás és particionálás"
    while read -r mp; do
        [ -n "$mp" ] && umount "$mp" && info "leválasztva: $mp"
    done < <(lsblk -lno MOUNTPOINTS "$dev" | sed '/^$/d' | sort -r)
    wipefs -a -q "$dev"
    sfdisk_script rest | sfdisk --quiet --wipe always --wipe-partitions always "$dev" >/dev/null 2>&1 \
        || die "a particionálás nem sikerült ($dev)"
    udevadm settle
    local p1 p2 p3 p4 i=0
    p1=$(part_dev "$dev" 1); p2=$(part_dev "$dev" 2); p3=$(part_dev "$dev" 3); p4=$(part_dev "$dev" 4)
    # Ha a kernel nem olvasta újra a partíciótáblát (pl. az asztali környezet épp
    # fogta a régi partíciót), frissítjük: -a felveszi a hiányzó partíciókat,
    # -u a meglévőket igazítja az új táblához. Mindkettő kell.
    local want_p1; want_p1=$(( ESP_MIB * 2048 ))
    _kernel_sees_layout() {
        [ -b "$p4" ] && [ "$(cat "/sys/class/block/$(basename "$p1")/size" 2>/dev/null)" = "$want_p1" ]
    }
    while ! _kernel_sees_layout && [ $i -lt 10 ]; do
        blockdev --rereadpt "$dev" 2>/dev/null || true
        partx -a "$dev" 2>/dev/null || true
        partx -u "$dev" 2>/dev/null || true
        udevadm settle
        _kernel_sees_layout || sleep 1
        i=$((i + 1))
    done
    if ! _kernel_sees_layout; then
        lsblk -o NAME,SIZE,MOUNTPOINTS "$dev" | sed 's/^/      /' >&2
        die "a kernel nem látja az új partíciókat. Húzd ki és dugd vissza a pendrive-ot, majd futtasd újra ugyanezt a parancsot."
    fi
    lsblk -o NAME,SIZE,PARTLABEL "$dev" | sed 's/^/      /'

    step "Fájlrendszerek"
    mkfs.vfat -F 32 -n FUSION_ESP "$p1" >/dev/null
    wipefs -a -q "$p3"                          # B slot: üres (az A/B frissítés az M7-ben)
    info "A slot: rendszerkép írása ($(( $(stat -c %s "$rootimg") / 1024 / 1024 )) MiB)..."
    dd if="$rootimg" of="$p2" bs=4M conv=fsync status=none || die "a rendszerkép írása nem sikerült ($p2)"
    # visszaolvasásos ellenőrzés: a slot eleje bájtra egyezik a rendszerképpel.
    # Előbb ürítjük az eszköz gyorsítótárát, hogy valóban a pendrive-ról olvassunk.
    blockdev --flushbufs "$p2" 2>/dev/null || true
    cmp -n "$(stat -c %s "$rootimg")" "$rootimg" "$p2" >/dev/null || die "a slot tartalma eltér a rendszerképtől ($p2) — hibás pendrive?"
    info "A slot: ellenőrizve (visszaolvasás egyezik)"
    local stage; stage=$(mktemp -d)
    cat > "$stage/README.txt" <<EOF
FusionOS adatpartíció (FUSION_DATA). Az M0 ezt a partíciót nem használja.
EOF
    # nodiscard: a teljes partícióra küldött TRIM sok pendrive-on percekig tart
    mkfs.ext4 -q -F -E nodiscard -L FUSION_DATA -d "$stage" "$p4"
    rm -rf "$stage"
    ok "ESP (FAT32), A slot (rendszerkép), DATA (ext4) kész; B üres"

    step "Bootloader és UKI másolása"
    # mtools: csatolás nélkül ír a FAT-partícióra (nincs ütközés az automatikus csatolással)
    local d f rel
    while IFS= read -r d; do
        rel=${d#"$esp_src"}; [ -n "$rel" ] || continue
        mmd -i "$p1" "::$rel" 2>/dev/null || die "nem sikerült a könyvtár létrehozása az ESP-n: $rel"
    done < <(find "$esp_src" -mindepth 1 -type d | sort)
    while IFS= read -r f; do
        rel=${f#"$esp_src"}
        mcopy -i "$p1" "$f" "::$rel" 2>/dev/null || die "nem sikerült a másolás az ESP-re: $rel"
        info "$rel"
    done < <(find "$esp_src" -type f | sort)
    sync
    ok "kész. Indítsd újra a ZBookot, F9 (boot menü) → a pendrive UEFI-bejegyzése."
}
