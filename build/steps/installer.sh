# shellcheck shell=bash
# telepítő pendrive (T2) — a FusionOS telepítő módban (fusion.installer): Fusion Telepítő a céllemezre.
#
#   installer-image            a telepítő lemezképe: build/out/<változat>/fusionos-telepito.img (root nélkül; az 'all' része)
#   installer <eszköz>         a telepítő felírása egy USB-pendrive-ra (root: sudo build/fusion-build installer /dev/sdX)
#
# A pendrive partíciói (GPT):
#   FUSION_IESP   ESP: systemd-boot + a telepítő UKI-ja (fusion.installer=1) + diagnosztika
#   FUSION_ISYS   a rendszerkép (EROFS) — telepítő módban erről indul, az írható réteg RAM-ban
#   FUSION_IPAY   FAT32 („FUSIONINST”): a telepítendő .fupd + esp-static.tar — Windowson / Macen is látszik,
#                 a .fupd kicserélhető egy újabbra; ide mentődik a telepítő hibajelentése is

INST_ESP_MIB=256
INST_MIN_GIB=4
TYPE_BASIC=EBD0A0A2-B9E5-4433-87C0-68B6B72699C7

_inst_img() { printf '%s/fusionos-telepito.img' "$(variant_dir)"; }

_inst_readme() {
    cat <<EOF
FusionOS telepítő pendrive ($FUSION_VERSION, $FUSION_MILESTONE)

Indítás: a gép boot menüje (ZBook: F9) -> ez a pendrive. A Fusion Telepítő:
  - új telepítés egy lemezre (a lemez TELJES tartalma törlődik), vagy
  - újratelepítés egy meglévő FusionOS-lemezre a DATA megőrzésével (programok, Wi-Fi, beállítások maradnak).

Ebben a mappában:
  fusionos-*.fupd     a telepítendő rendszer — kicserélhető egy újabb .fupd fájlra (egyszerre csak egy legyen itt)
  esp-static.tar      a rendszerbetöltő állandó része (ne töröld)
  hibajelentes/       a telepítő hibajelentései
EOF
}

step_installer_image() {
    not_root
    need sfdisk mkfs.vfat mcopy mmd truncate dd
    local out; out=$(variant_dir)
    local rootimg; rootimg=$(rootfs_img)
    local fupd; fupd=$(ls "$out"/fusionos-*.fupd 2>/dev/null | head -n 1)
    [ -r "$out/fusion-installer.efi" ] && [ -r "$out/esp-static.tar" ] && [ -n "$fupd" ] \
        || die "előbb: build/fusion-build build (telepítő UKI, esp-static.tar, .fupd)"
    local img; img=$(_inst_img)
    local sys_mib pay_mib total
    sys_mib=$(( ( $(stat -c %s "$rootimg") / 1048576 + 64 + 63 ) / 64 * 64 ))
    pay_mib=$(( ( ( $(stat -c %s "$fupd") + $(stat -c %s "$out/esp-static.tar") ) / 1048576 + 256 + 63 ) / 64 * 64 ))
    total=$(( 1 + INST_ESP_MIB + sys_mib + pay_mib + 1 ))

    step "Telepítő pendrive lemezképe ($total MiB): $(basename "$img")"
    rm -f "$img"; truncate -s "${total}M" "$img"
    local mib=2048 s_esp=2048 s_sys s_pay
    s_sys=$(( s_esp + INST_ESP_MIB * mib )); s_pay=$(( s_sys + sys_mib * mib ))
    {
        echo "label: gpt"
        echo "start=$s_esp, size=$(( INST_ESP_MIB * mib )), type=$TYPE_ESP, name=\"FUSION_IESP\""
        echo "start=$s_sys, size=$(( sys_mib * mib )), type=$TYPE_DATA, name=\"FUSION_ISYS\""
        echo "start=$s_pay, size=$(( pay_mib * mib )), type=$TYPE_BASIC, name=\"FUSION_IPAY\""
    } | sfdisk --quiet --no-reread --no-tell-kernel "$img" >/dev/null || die "a particionálás nem sikerült"

    # ESP: systemd-boot + a telepítő UKI-ja (és a diagnosztika)
    local f="$out/inst-esp.fat"; rm -f "$f"; truncate -s "${INST_ESP_MIB}M" "$f"
    mkfs.vfat -F 32 -n FUSIONIESP "$f" >/dev/null
    mmd -i "$f" ::/EFI ::/EFI/BOOT ::/EFI/systemd ::/EFI/Linux ::/loader
    mcopy -i "$f" /usr/lib/systemd/boot/efi/systemd-bootx64.efi ::/EFI/BOOT/BOOTX64.EFI
    mcopy -i "$f" /usr/lib/systemd/boot/efi/systemd-bootx64.efi ::/EFI/systemd/systemd-bootx64.efi
    mcopy -i "$f" "$out/fusion-installer.efi" ::/EFI/Linux/fusion-installer.efi
    [ -r "$out/fusion-diag.efi" ] && mcopy -i "$f" "$out/fusion-diag.efi" ::/EFI/Linux/fusion-diag.efi
    printf 'timeout 3\ndefault fusion-installer*\nconsole-mode keep\neditor yes\n' > "$out/inst-loader.conf"
    mcopy -i "$f" "$out/inst-loader.conf" ::/loader/loader.conf
    dd if="$f" of="$img" bs=1M seek=1 conv=notrunc,sparse status=none
    rm -f "$f" "$out/inst-loader.conf"

    # rendszerkép
    dd if="$rootimg" of="$img" bs=1M seek=$(( 1 + INST_ESP_MIB )) conv=notrunc,sparse status=none

    # a telepítendő csomag
    f="$out/inst-pay.fat"; rm -f "$f"; truncate -s "${pay_mib}M" "$f"
    mkfs.vfat -F 32 -n FUSIONINST "$f" >/dev/null
    _inst_readme > "$out/inst-readme.txt"
    mcopy -i "$f" "$fupd" "::/$(basename "$fupd")"
    mcopy -i "$f" "$out/esp-static.tar" ::/esp-static.tar
    mcopy -i "$f" "$out/inst-readme.txt" ::/OLVASS-EL.txt
    mmd -i "$f" ::/hibajelentes
    dd if="$f" of="$img" bs=1M seek=$(( 1 + INST_ESP_MIB + sys_mib )) conv=notrunc,sparse status=none
    rm -f "$f" "$out/inst-readme.txt"
    ok "kész: $img — ESP ${INST_ESP_MIB}M, rendszer ${sys_mib}M, csomag ${pay_mib}M ($(basename "$fupd"))"
}

# a telepítő felírása egy pendrive-ra (Mint): a lemezkép + a GPT-másolat a pendrive végére
step_installer() {
    local dev="${1:-}" img; img=$(_inst_img)
    [ "$(id -u)" -eq 0 ] || die "root kell:  sudo build/fusion-build installer /dev/sdX"
    need lsblk sfdisk wipefs dd cmp blockdev udevadm
    [ -n "$dev" ] || die "add meg a pendrive-ot, pl.:  sudo build/fusion-build installer /dev/sdX   (lista: lsblk -d -o NAME,TRAN,SIZE,MODEL)"
    [ -r "$img" ] || die "nincs telepítő lemezkép — előbb (root nélkül): build/fusion-build all"
    dev=$(readlink -f "$dev")
    local USB_MIN_GIB="$INST_MIN_GIB"
    _disk_checks "$dev" 0
    local need_b; need_b=$(stat -c %s "$img")
    [ "$(lsblk -dbno SIZE "$dev")" -ge "$need_b" ] || die "a pendrive túl kicsi: legalább $(( need_b / 1048576 )) MiB kell"

    step "Telepítő pendrive"
    info "Eszköz:  $dev — $DEV_DESC, ${DEV_SIZE_GIB} GiB"
    info "Lemezkép: $(basename "$img") ($(( need_b / 1048576 )) MiB)"
    lsblk -o NAME,SIZE,FSTYPE,LABEL,MOUNTPOINTS "$dev" | sed 's/^/      /'
    _confirm "$dev" "A pendrive TELJES tartalma törlődik."

    _unmount_fusion "$dev"
    wipefs -a -q "$dev"
    info "írás..."
    dd if="$img" of="$dev" bs=4M conv=fsync status=progress || die "az írás nem sikerült"
    blockdev --flushbufs "$dev" 2>/dev/null || true
    info "ellenőrzés (visszaolvasás)..."
    cmp -n "$need_b" "$img" "$dev" >/dev/null || die "a pendrive tartalma eltér a lemezképtől — hibás pendrive?"
    # a GPT tartalék fejléce a pendrive végére (a lemezkép kisebb a pendrive-nál)
    sfdisk --quiet --relocate gpt-bak-std "$dev" >/dev/null 2>&1 || warn "a GPT tartalék fejléce nem helyezhető át (nem baj)"
    udevadm settle
    ok "kész. A pendrive-ról: F9 (boot menü) → a pendrive UEFI-bejegyzése → Fusion Telepítő."
}
