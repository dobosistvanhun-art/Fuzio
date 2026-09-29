# shellcheck shell=bash
# Lemezre írás — root kell hozzá.
#
#   usb <eszköz>                      a FusionOS felírása egy USB-pendrive-ra (a teljes pendrive törlődik)
#   install <eszköz> [kapcsolók]      telepítés egy lemezre (a teljes lemez törlődik)
#       --internal                    belső (SATA/NVMe) lemez engedélyezése — pl. a ZBook optikai
#                                     helyén lévő SSD; e nélkül csak USB-eszközre ír
#       --data-from <könyvtár|partíció>
#                                     a DATA tartalmának átvétele egy meglévő FusionOS-ről (pl. a
#                                     pendrive FUSION_DATA-ja): telepített Windows-programok (LightBurn),
#                                     Wi-Fi, nyomtató-adatok — semmit nem kell újratelepíteni
#       --wifi-file <fájl>            Wi-Fi-hálózat előre beállítva (SSID=… és PSK=… sorok)
#   update <eszköz> [--wifi-file <fájl>]
#                                     rendszerfrissítés egy meglévő FusionOS-lemezen: ESP + A slot
#                                     újraírva, a DATA (programok, beállítások, adatok) MEGMARAD
#
# Biztonság:
#   - csak teljes lemezt fogad el (pl. /dev/sdb, nem /dev/sdb1);
#   - USB-eszköz, vagy belső lemez csak kifejezett --internal kapcsolóval;
#   - nem lehet rajta a futó rendszer (/, /boot, /boot/efi, /home, /usr, /var, swap);
#   - más, csatolt fájlrendszer (nem FUSION_*) esetén megáll: előbb le kell választani;
#   - a felhasználónak be kell gépelnie az eszköz nevét a megerősítéshez;
#   - update: csak FusionOS-lemezen (FUSION_ESP/A/B/DATA partíciók), és a DATA-hoz nem nyúl.

# a lemez ellenőrzése; kiírja a jellemzőit (DEV_TRAN, DEV_SIZE_GIB, DEV_DESC globálisok)
_disk_checks() {  # <eszköz> <allow_internal 0|1>
    local dev="$1" internal="$2" type tran size_b model vendor mp name label
    [ -b "$dev" ] || die "nem blokkeszköz: $dev"
    type=$(lsblk -dno TYPE "$dev" 2>/dev/null)
    if [ "$type" = "part" ]; then
        die "$dev egy partíció. A teljes lemez kell: /dev/$(lsblk -dno PKNAME "$dev")"
    fi
    if [ "$type" = "loop" ] && [ "${FUSION_ALLOW_LOOP:-0}" = 1 ]; then
        tran=loop    # csak a fejlesztői próbákhoz (lemezkép-fájl)
    else
        [ "$type" = "disk" ] || die "$dev nem lemez (típus: ${type:-ismeretlen})"
        tran=$(lsblk -dno TRAN "$dev" | tr -d ' ')
    fi
    size_b=$(lsblk -dbno SIZE "$dev" | tr -d ' ')
    DEV_SIZE_GIB=$((size_b / 1024 / 1024 / 1024))
    model=$(lsblk -dno MODEL "$dev" 2>/dev/null | sed 's/ *$//')
    vendor=$(lsblk -dno VENDOR "$dev" 2>/dev/null | sed 's/ *$//')
    DEV_TRAN="$tran"; DEV_DESC="${vendor:+$vendor }${model:-ismeretlen}"
    if [ "$tran" != usb ] && [ "$tran" != loop ]; then
        [ "$internal" = 1 ] || die "$dev nem USB-eszköz (csatlakozás: ${tran:-ismeretlen}, $DEV_DESC). Belső lemezre csak kifejezetten: --internal"
    fi
    [ "$DEV_SIZE_GIB" -ge "$USB_MIN_GIB" ] || die "$dev túl kicsi: ${DEV_SIZE_GIB} GiB (legalább $USB_MIN_GIB GiB kell)"
    if [ "$tran" = usb ]; then
        [ "$DEV_SIZE_GIB" -le "$USB_MAX_GIB" ] || die "$dev gyanúsan nagy: ${DEV_SIZE_GIB} GiB (legfeljebb $USB_MAX_GIB GiB) — biztos, hogy pendrive?"
    fi
    # nem lehet rajta a futó rendszer, és más csatolt fájlrendszer sem
    while read -r name; do
        mp=$(lsblk -no MOUNTPOINT "/dev/$name" 2>/dev/null | head -n 1)
        label=$(lsblk -no LABEL "/dev/$name" 2>/dev/null | head -n 1)
        [ -n "$mp" ] || continue
        case "$mp" in
            /|/boot|/boot/efi|/home|/usr|/var|/var/*|\[SWAP\]) die "$dev tartalmazza a futó rendszer egy részét ($mp) — megszakítva." ;;
        esac
        case "$label" in
            FUSION_*) ;;    # a FusionOS saját partíciói (automatikus csatolás): leválasztjuk
            *) die "$dev egyik partíciója csatolva van: /dev/$name → $mp (${label:-címke nélkül}). Ha biztosan törölhető, előbb: sudo umount $mp" ;;
        esac
    done < <(lsblk -lno NAME "$dev")
    if grep -q "^$dev" /proc/swaps 2>/dev/null; then die "$dev-n aktív swap van — megszakítva."; fi
}

# a GPT-partíció neve (udev nélkül is: közvetlen beolvasással)
_partlabel() {
    local l; l=$(lsblk -dno PARTLABEL "$1" 2>/dev/null)
    [ -n "$l" ] || l=$(blkid -p -s PART_ENTRY_NAME -o value "$1" 2>/dev/null)
    printf '%s' "$l"
}

_confirm() {  # <eszköz> <üzenet>
    local dev="$1" answer
    echo
    printf '%s%s%s\n' "$C_ERR" "$2" "$C_0"
    printf 'Megerősítéshez írd be az eszköz nevét (%s): ' "$(basename "$dev")"
    read -r answer
    [ "$answer" = "$(basename "$dev")" ] || die "megszakítva (a beírt név nem egyezik)."
}

_unmount_fusion() {  # <eszköz>: a FUSION_* partíciók leválasztása
    local mp
    while read -r mp; do
        [ -n "$mp" ] && umount "$mp" && info "leválasztva: $mp"
    done < <(lsblk -lno MOUNTPOINTS "$1" | sed '/^$/d' | sort -r)
}

_wait_layout() {  # <eszköz>: a kernel lássa az új partíciótáblát
    local dev="$1" p1 p4 want_p1 i=0
    p1=$(part_dev "$dev" 1); p4=$(part_dev "$dev" 4); want_p1=$(( ESP_MIB * 2048 ))
    _kernel_sees_layout() {
        [ -b "$p4" ] && [ "$(cat "/sys/class/block/$(basename "$p1")/size" 2>/dev/null)" = "$want_p1" ]
    }
    # Ha a kernel nem olvasta újra a partíciótáblát (pl. az asztali környezet épp fogta a régi
    # partíciót): -a felveszi a hiányzó partíciókat, -u a meglévőket igazítja. Mindkettő kell.
    while ! _kernel_sees_layout && [ $i -lt 10 ]; do
        blockdev --rereadpt "$dev" 2>/dev/null || true
        partx -a "$dev" 2>/dev/null || true
        partx -u "$dev" 2>/dev/null || true
        udevadm settle
        _kernel_sees_layout || sleep 1
        i=$((i + 1))
    done
    _kernel_sees_layout && return 0
    lsblk -o NAME,SIZE,MOUNTPOINTS "$dev" | sed 's/^/      /' >&2
    die "a kernel nem látja az új partíciókat. (Pendrive: húzd ki és dugd vissza.) Futtasd újra ugyanezt a parancsot."
}

# a rendszerkép az A slotba, visszaolvasásos ellenőrzéssel
_write_slot() {  # <partíció>
    local p="$1" rootimg; rootimg=$(rootfs_img)
    info "A slot: rendszerkép írása ($(( $(stat -c %s "$rootimg") / 1024 / 1024 )) MiB)..."
    dd if="$rootimg" of="$p" bs=4M conv=fsync status=none || die "a rendszerkép írása nem sikerült ($p)"
    # az eszköz gyorsítótárát ürítjük, hogy valóban a lemezről olvassunk vissza
    blockdev --flushbufs "$p" 2>/dev/null || true
    cmp -n "$(stat -c %s "$rootimg")" "$rootimg" "$p" >/dev/null || die "a slot tartalma eltér a rendszerképtől ($p) — hibás lemez?"
    info "A slot: ellenőrizve (visszaolvasás egyezik)"
}

# az ESP: újraformázás és a release ESP-fa másolása (mtools: csatolás nélkül)
_write_esp() {  # <partíció>
    local p="$1" esp_src="${FUSION_ESP_DIR:-$OUT_DIR/release/esp}" d f rel   # FUSION_ESP_DIR: csak fejlesztői próbához
    mkfs.vfat -F 32 -n FUSION_ESP "$p" >/dev/null || die "az ESP formázása nem sikerült ($p)"
    while IFS= read -r d; do
        rel=${d#"$esp_src"}; [ -n "$rel" ] || continue
        mmd -i "$p" "::$rel" 2>/dev/null || die "nem sikerült a könyvtár létrehozása az ESP-n: $rel"
    done < <(find "$esp_src" -mindepth 1 -type d | sort)
    while IFS= read -r f; do
        rel=${f#"$esp_src"}
        mcopy -i "$p" "$f" "::$rel" 2>/dev/null || die "nem sikerült a másolás az ESP-re: $rel"
        info "$rel"
    done < <(find "$esp_src" -type f | sort)
}

# Wi-Fi-hálózat az iwd-nek, a DATA gyökér-rétegében (/var/lib/iwd)
_seed_wifi() {  # <DATA csatolási pontja> <wifi-fájl>
    local data="$1" file="$2" ssid psk name dir
    ssid=$(sed -n 's/^SSID=//p' "$file" | head -n 1)
    psk=$(sed -n 's/^PSK=//p' "$file" | head -n 1)
    [ -n "$ssid" ] && [ -n "$psk" ] || die "a Wi-Fi-fájlban SSID=… és PSK=… sor kell: $file"
    [ ${#psk} -ge 8 ] && [ ${#psk} -le 63 ] || die "a Wi-Fi-jelszó 8–63 karakter lehet"
    # az iwd fájlneve: az SSID, ha csak betű/szám/szóköz/-/_; különben "=" + hexa
    if printf '%s' "$ssid" | grep -q '^[A-Za-z0-9 _-]*$'; then name="$ssid"
    else name="=$(printf '%s' "$ssid" | od -An -v -tx1 | tr -d ' \n')"; fi
    dir="$data/overlay/root/upper/var/lib/iwd"
    install -d -m 0700 "$dir"
    umask 077
    printf '[Security]\nPassphrase=%s\n\n[Settings]\nAutoConnect=true\n' "$psk" > "$dir/$name.psk"
    chmod 0600 "$dir/$name.psk"
    ok "Wi-Fi beállítva: $ssid (a jelszó csak a DATA-n van)"
}

_install_or_usb() {  # <mód: usb|install> <eszköz> [kapcsolók]
    local mode="$1" dev="${2:-}" internal=0 data_from="" wifi_file=""
    shift 2 || true
    while [ $# -gt 0 ]; do
        case "$1" in
            --internal)  internal=1 ;;
            --data-from) data_from="${2:-}"; shift ;;
            --wifi-file) wifi_file="${2:-}"; shift ;;
            *) die "ismeretlen kapcsoló: $1" ;;
        esac
        shift
    done
    [ "$mode" = usb ] && internal=0
    [ "$(id -u)" -eq 0 ] || die "root kell:  sudo build/fusion-build $mode /dev/sdX"
    need lsblk sfdisk wipefs mkfs.vfat mkfs.ext4 udevadm partx blockdev mmd mcopy
    [ -n "$dev" ] || die "add meg a céllemezt, pl.:  sudo build/fusion-build $mode /dev/sdX   (lista: lsblk -d -o NAME,TRAN,SIZE,MODEL)"
    [ -d "$OUT_DIR/release/esp/EFI" ] || die "nincs kész release ESP — előbb (root nélkül): build/fusion-build all"
    [ -r "$(rootfs_img)" ] || die "nincs rendszerkép — előbb: build/fusion-build all"
    [ -z "$wifi_file" ] || [ -r "$wifi_file" ] || die "a Wi-Fi-fájl nem olvasható: $wifi_file"
    dev=$(readlink -f "$dev")
    _disk_checks "$dev" "$internal"

    # a DATA forrása: könyvtár (csatolt FUSION_DATA) vagy partíció (csak olvashatóan csatoljuk)
    local src_mnt="" src_tmp=""
    if [ -n "$data_from" ]; then
        if [ -b "$data_from" ]; then
            [ "$(lsblk -no PKNAME "$(readlink -f "$data_from")")" != "$(basename "$dev")" ] \
                || die "a --data-from a céllemezen van — az törlődne"
            src_tmp=$(mktemp -d); mount -o ro "$data_from" "$src_tmp" || die "nem csatolható: $data_from"
            src_mnt="$src_tmp"
        elif [ -d "$data_from" ]; then
            src_mnt=$(readlink -f "$data_from")
            local srcdev; srcdev=$(findmnt -no SOURCE --target "$src_mnt" 2>/dev/null)
            [ -z "$srcdev" ] || [ "$(lsblk -no PKNAME "$srcdev" 2>/dev/null)" != "$(basename "$dev")" ] \
                || die "a --data-from a céllemezen van — az törlődne"
        else
            die "a --data-from nem könyvtár és nem partíció: $data_from"
        fi
        [ -d "$src_mnt/overlay" ] || [ -d "$src_mnt/fwr" ] || die "a --data-from nem FusionOS DATA-nak tűnik (nincs overlay/ vagy fwr/): $data_from"
    fi

    step "Céllemez"
    info "Eszköz:  $dev"
    info "Típus:   $DEV_DESC"
    info "Méret:   ${DEV_SIZE_GIB} GiB, ${DEV_TRAN:-?}"
    info "Jelenlegi tartalom:"
    lsblk -o NAME,SIZE,FSTYPE,LABEL,MOUNTPOINTS "$dev" | sed 's/^/      /'
    [ -n "$src_mnt" ] && info "DATA átvétele innen: $data_from ($(du -sh "$src_mnt" 2>/dev/null | cut -f1))"
    _confirm "$dev" "A lemez TELJES tartalma törlődik."

    step "Leválasztás és particionálás"
    _unmount_fusion "$dev"
    wipefs -a -q "$dev"
    sfdisk_script rest | sfdisk --quiet --wipe always --wipe-partitions always "$dev" >/dev/null 2>&1 \
        || die "a particionálás nem sikerült ($dev)"
    udevadm settle
    _wait_layout "$dev"
    local p1 p2 p3 p4
    p1=$(part_dev "$dev" 1); p2=$(part_dev "$dev" 2); p3=$(part_dev "$dev" 3); p4=$(part_dev "$dev" 4)
    lsblk -o NAME,SIZE,PARTLABEL "$dev" | sed 's/^/      /'

    step "Fájlrendszerek"
    wipefs -a -q "$p3"                          # B slot: üres (az A/B frissítés az M7-ben)
    _write_slot "$p2"
    # nodiscard: a teljes partícióra küldött TRIM sok pendrive-on percekig tart
    mkfs.ext4 -q -F -E nodiscard -L FUSION_DATA "$p4"
    if [ -n "$src_mnt" ] || [ -n "$wifi_file" ]; then
        local dst; dst=$(mktemp -d)
        mount "$p4" "$dst" || die "a DATA nem csatolható ($p4)"
        if [ -n "$src_mnt" ]; then
            info "DATA átvétele (tulajdonosok, jogok, overlay-jelölések megtartásával)..."
            tar -C "$src_mnt" --numeric-owner --xattrs --xattrs-include='*' --acls \
                --exclude=./lost+found --exclude=./overlay/root/work -cf - . \
                | tar -C "$dst" --numeric-owner --xattrs --xattrs-include='*' --acls -xpf - \
                || { umount "$dst"; die "a DATA átvétele nem sikerült"; }
            ok "DATA átvéve ($(du -sh "$dst" | cut -f1))"
        fi
        [ -n "$wifi_file" ] && _seed_wifi "$dst" "$wifi_file"
        sync; umount "$dst"; rmdir "$dst"
    fi
    [ -n "$src_tmp" ] && { umount "$src_tmp"; rmdir "$src_tmp"; }
    ok "ESP, A slot (rendszerkép), DATA (ext4) kész; B üres"

    step "Bootloader és UKI"
    _write_esp "$p1"
    sync
    if [ "$DEV_TRAN" = usb ]; then
        ok "kész. Indítsd újra a ZBookot, F9 (boot menü) → a pendrive UEFI-bejegyzése."
    elif [ "$DEV_TRAN" != loop ] && [ -d /sys/firmware/efi ] && have efibootmgr; then
        step "UEFI boot-bejegyzés"
        step_bootentry "$dev" quiet || warn "a boot-bejegyzés nem sikerült — később: sudo build/fusion-build bootentry $dev"
        ok "kész. Indítsd újra a ZBookot, F9 (boot menü) → „FusionOS”."
    else
        ok "kész. Indítsd újra a ZBookot, F9 (boot menü) → a(z) $DEV_DESC lemez UEFI-bejegyzése (vagy: sudo build/fusion-build bootentry $dev)."
    fi
}

step_usb()     { _install_or_usb usb "$@"; }
step_install() { _install_or_usb install "$@"; }

step_update() {
    local dev="${1:-}" wifi_file=""
    shift || true
    while [ $# -gt 0 ]; do
        case "$1" in
            --wifi-file) wifi_file="${2:-}"; shift ;;
            *) die "ismeretlen kapcsoló: $1" ;;
        esac
        shift
    done
    [ "$(id -u)" -eq 0 ] || die "root kell:  sudo build/fusion-build update /dev/sdX"
    need lsblk mkfs.vfat udevadm blockdev mmd mcopy cmp
    [ -n "$dev" ] || die "add meg a FusionOS-lemezt, pl.:  sudo build/fusion-build update /dev/sdb"
    [ -d "$OUT_DIR/release/esp/EFI" ] || die "nincs kész release ESP — előbb (root nélkül): build/fusion-build all"
    [ -r "$(rootfs_img)" ] || die "nincs rendszerkép — előbb: build/fusion-build all"
    [ -z "$wifi_file" ] || [ -r "$wifi_file" ] || die "a Wi-Fi-fájl nem olvasható: $wifi_file"
    dev=$(readlink -f "$dev")
    # frissítéshez belső lemez is jó: a FusionOS-elrendezés és a partíciónevek védik a többi lemezt
    _disk_checks "$dev" 1
    local p1 p2 p3 p4 i want name
    p1=$(part_dev "$dev" 1); p2=$(part_dev "$dev" 2); p3=$(part_dev "$dev" 3); p4=$(part_dev "$dev" 4)
    i=1
    for want in "$PART_ESP" "$PART_A" "$PART_B" "$PART_DATA"; do
        name=$(_partlabel "$(part_dev "$dev" $i)")
        [ "$name" = "$want" ] || die "$dev nem FusionOS-lemez (a(z) $i. partíció neve: '${name:-nincs}', várt: $want). Új telepítés: install"
        i=$((i + 1))
    done
    local slot_b img_b
    slot_b=$(blockdev --getsize64 "$p2"); img_b=$(stat -c %s "$(rootfs_img)")
    [ "$img_b" -le "$slot_b" ] || die "a rendszerkép ($((img_b / 1048576)) MiB) nem fér az A slotba ($((slot_b / 1048576)) MiB)"

    step "Frissítendő FusionOS-lemez"
    info "Eszköz:  $dev ($DEV_DESC, ${DEV_SIZE_GIB} GiB, ${DEV_TRAN:-?})"
    lsblk -o NAME,SIZE,FSTYPE,LABEL,MOUNTPOINTS "$dev" | sed 's/^/      /'
    info "Új rendszer: FusionOS $FUSION_VERSION ($FUSION_MILESTONE)"
    info "A DATA ($p4) MEGMARAD: telepített programok, Wi-Fi, beállítások, nyomtató-adatok."
    _confirm "$dev" "Az ESP és az A slot felülíródik (a DATA-hoz nem nyúl)."

    step "Frissítés"
    _unmount_fusion "$dev"
    _write_slot "$p2"
    if [ -n "$wifi_file" ]; then
        local dst; dst=$(mktemp -d)
        mount "$p4" "$dst" || die "a DATA nem csatolható ($p4)"
        _seed_wifi "$dst" "$wifi_file"
        sync; umount "$dst"; rmdir "$dst"
    fi
    step "Bootloader és UKI"
    _write_esp "$p1"
    sync
    ok "kész: FusionOS $FUSION_VERSION ($FUSION_MILESTONE) — a DATA változatlan. Indítás: F9 → a lemez UEFI-bejegyzése."
}

# UEFI boot-bejegyzés a FusionOS-lemezhez (a ZBook F9-menüjében „FusionOS” néven jelenik meg).
# A HP firmware a belső SATA-lemez ESP-jét magától nem ajánlja fel — e nélkül csak a
# „Boot from EFI file” tallózásával indítható. A jelenlegi első bejegyzés (a Mint) marad az első.
step_bootentry() {
    local dev="${1:-}" quiet="${2:-}"
    [ "$(id -u)" -eq 0 ] || die "root kell:  sudo build/fusion-build bootentry /dev/sdX"
    [ -d /sys/firmware/efi ] || die "a Mint nem UEFI-módban fut — boot-bejegyzés nem hozható létre"
    need efibootmgr
    [ -n "$dev" ] || die "add meg a FusionOS-lemezt, pl.:  sudo build/fusion-build bootentry /dev/sdb"
    dev=$(readlink -f "$dev")
    [ "$(_partlabel "$(part_dev "$dev" 1)")" = "$PART_ESP" ] || die "$dev nem FusionOS-lemez (nincs $PART_ESP az 1. partíción)"
    local old_order old_first n new rest=""
    old_order=$(efibootmgr | sed -n 's/^BootOrder: //p')
    # a korábbi FusionOS-bejegyzések törlése (újratelepítéskor megváltozik a partíció azonosítója)
    for n in $(efibootmgr | sed -n 's/^Boot\([0-9A-Fa-f]\{4\}\)[* ] *FusionOS\b.*/\1/p'); do
        efibootmgr -q -b "$n" -B && info "régi FusionOS-bejegyzés törölve: Boot$n"
        old_order=$(printf '%s' "$old_order" | tr ',' '\n' | grep -vix "$n" | paste -sd, -)
    done
    efibootmgr -q -c -d "$dev" -p 1 -L "FusionOS" -l '\EFI\BOOT\BOOTX64.EFI' || die "az efibootmgr nem hozta létre a bejegyzést"
    new=$(efibootmgr | sed -n 's/^Boot\([0-9A-Fa-f]\{4\}\)[* ] *FusionOS\b.*/\1/p' | head -n 1)
    [ -n "$new" ] || die "a FusionOS-bejegyzés nem látszik az efibootmgr listájában"
    # sorrend: az eddigi első (a Mint) marad elöl, utána a FusionOS, majd a többi
    old_first=$(printf '%s' "$old_order" | cut -d, -f1)
    rest=$(printf '%s' "$old_order" | tr ',' '\n' | sed '1d' | grep -vix "$new" | paste -sd, -)
    if [ -n "$old_first" ]; then
        efibootmgr -q -o "$old_first,$new${rest:+,$rest}" || warn "a boot-sorrend nem állítható vissza — ellenőrizd: efibootmgr"
    fi
    [ -n "$quiet" ] || efibootmgr | sed -n '/^BootOrder\|FusionOS\|^Boot'"$old_first"'/p' | sed 's/^/      /'
    ok "UEFI-bejegyzés: Boot$new „FusionOS” — F9 menüben választható; az alapértelmezett indítás változatlan."
}
