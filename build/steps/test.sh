# shellcheck shell=bash
# test — automatikus EFI boot-teszt QEMU + OVMF alatt (fejlesztői ellenőrzés).
#
# FusionOS (alapértelmezett boot-bejegyzés), a soros naplóból ellenőrizve:
#   std    + SATA  -> QEMU std VGA (1234:1111)   -> profil: generic-kms
#   vmware + SATA  -> VMware SVGA II (15ad:0405) -> profil: vmware-svga (= VirtualBox VMSVGA), driver: vmwgfx
#   std    + USB   -> a lemezkép USB-pendrive-ként (xHCI + usb-storage), mint a ZBookon
# Diagnosztika (a boot menü második bejegyzése):
#   std    + USB   -> az M0 ellenőrző képernyő
#
# Minden FusionOS-futásnál: systemd "running", gyökér-overlay, /usr csak olvasható
# (EROFS), /data ext4, A slot, getty, nincs hibás szolgáltatás, magyar locale.

_ovmf_code() {
    local f
    for f in /usr/share/OVMF/OVMF_CODE_4M.fd /usr/share/OVMF/OVMF_CODE.fd /usr/share/ovmf/OVMF.fd; do
        [ -r "$f" ] && { echo "$f"; return; }
    done
}
_ovmf_vars() {
    local f
    for f in /usr/share/OVMF/OVMF_VARS_4M.fd /usr/share/OVMF/OVMF_VARS.fd; do
        [ -r "$f" ] && { echo "$f"; return; }
    done
}

# _qemu_run <cfg-név> <vga> <busz> <napló> <várt záró marker>
_qemu_run() {
    local cfg="$1" vga="$2" bus="$3" log="$4" marker="$5"
    local out="$OUT_DIR/test" img="$OUT_DIR/test/fusionos.img"
    local accel="tcg"; [ -w /dev/kvm ] && accel="kvm"
    local diskdev
    case "$bus" in
        sata) diskdev=(-device "ahci,id=ahci0" -device "ide-hd,drive=disk0,bus=ahci0.0") ;;
        usb)  diskdev=(-device "qemu-xhci,id=xhci0" -device "usb-storage,drive=disk0,bus=xhci0.0") ;;
    esac
    cp "$(_ovmf_vars)" "$out/vars-$cfg.fd"
    rm -f "$log" "$out/screen-$cfg.ppm"
    timeout 600 qemu-system-x86_64 \
        -machine q35,accel="$accel" -m 2048 -smp 2 \
        -drive if=pflash,format=raw,readonly=on,file="$(_ovmf_code)" \
        -drive if=pflash,format=raw,file="$out/vars-$cfg.fd" \
        -drive file="$img",format=raw,if=none,id=disk0,snapshot=on \
        "${diskdev[@]}" \
        -nic user,model=e1000e \
        -vga "$vga" -display none -serial "file:$log" -no-reboot \
        -monitor "unix:$out/qemu-$cfg.mon,server,nowait" >/dev/null 2>&1 &
    local qpid=$!
    RUN_SECS=0
    while kill -0 "$qpid" 2>/dev/null; do
        if [ ! -f "$out/screen-$cfg.ppm" ] && grep -qs "$marker" "$log"; then
            sleep 1
            have python3 && python3 - "$out/qemu-$cfg.mon" "$out/screen-$cfg.ppm" <<'PY' 2>/dev/null || true
import socket, sys, time
s = socket.socket(socket.AF_UNIX); s.connect(sys.argv[1])
time.sleep(0.3); s.recv(65536)
s.sendall(("screendump %s\n" % sys.argv[2]).encode()); time.sleep(1.5); s.close()
PY
        fi
        sleep 1; RUN_SECS=$((RUN_SECS + 1))
    done
    wait "$qpid" 2>/dev/null || true
}

_check() {  # _check <napló> <minta> <leírás>
    if grep -qa -- "$2" "$1"; then return 0; fi
    warn "hiányzik: $3  ($2)"; return 1
}

step_test() {
    not_root
    need qemu-system-x86_64 timeout
    [ -n "$(_ovmf_code)" ] && [ -n "$(_ovmf_vars)" ] || die "OVMF nem található (sudo apt install ovmf)"
    [ -r "$(rootfs_img)" ] || die "nincs rendszerkép — előbb: build/fusion-build all"
    local out="$OUT_DIR/test" fails=0 cfg vga bus want log drv ok_run

    FUSION_VARIANT="test" step_build
    FUSION_VARIANT="test" step_image

    for cfg in std-sata vmware-sata std-usb; do
        vga=${cfg%-*}; bus=${cfg#*-}
        case "$vga" in
            std)    want=generic-kms; drv=none ;;
            vmware) want=vmware-svga; drv=loaded ;;
        esac
        log="$out/qemu-$cfg.log"
        step "QEMU EFI boot → FusionOS: -vga $vga, lemez: $bus (várt profil: $want)"
        _qemu_run "$cfg" "$vga" "$bus" "$log" "FUSION-M1: SYSTEM UP"
        ok_run=1
        _check "$log" "FUSION-M1: SYSTEM UP state=running" "systemd fut, hibátlanul" || ok_run=0
        _check "$log" "FUSION-M1: ROOT overlay usr=erofs ro" "gyökér-overlay, /usr csak olvasható (EROFS)" || ok_run=0
        _check "$log" "FUSION-M1: MOUNTS data=ext4" "/data" || ok_run=0
        _check "$log" "FUSION-M1: SLOT A" "A slot" || ok_run=0
        _check "$log" "FUSION-M1: DISPLAY_PROFILE=$want STATUS=ok DRIVER=$drv" "hardverprofil és driver" || ok_run=0
        _check "$log" "FUSION-M1: GETTY active" "bejelentkezési képernyő" || ok_run=0
        _check "$log" "FUSION-M1: LOCALE hu_HU.UTF-8 KEYMAP hu" "magyar nyelv és billentyűzet" || ok_run=0
        _check "$log" "FUSION-M1: USER fusion:/home/fusion" "fusion felhasználó" || ok_run=0
        _check "$log" "FUSION-M1: MACHINE-ID ok" "machine-id" || ok_run=0
        _check "$log" "FUSION-M1: ROOTOWNER root UNSAFE 0" "a gyökér a root tulajdona, nincs 'unsafe path' figyelmeztetés" || ok_run=0
        _check "$log" "FUSION-M1: FAILEDCOUNT 0" "nincs hibás szolgáltatás" || ok_run=0
        if [ "$ok_run" -eq 1 ]; then
            ok "SIKERES ($RUN_SECS mp)"
        else
            warn "SIKERTELEN — napló: $log"
            grep -a 'FUSION-M1\|fusion-init\|FAILED\|Failed' "$log" | tail -n 20 | sed 's/^/      /' >&2
            fails=$((fails + 1))
        fi
    done

    # diagnosztika: a boot menü második bejegyzése, alapértelmezettként beállítva
    FUSION_VARIANT="test" FUSION_BOOT_DEFAULT="fusion-diag*" step_build >/dev/null
    FUSION_VARIANT="test" step_image >/dev/null
    log="$out/qemu-diag-usb.log"
    step "QEMU EFI boot → diagnosztika: -vga std, lemez: usb"
    _qemu_run diag-usb std usb "$log" "FUSION-M0: BOOT OK"
    if _check "$log" "FUSION-M0: BOOT OK" "diagnosztika fut" \
       && _check "$log" "FUSION-M0: PARTITIONS 4/4" "4 partíció"; then
        ok "SIKERES ($RUN_SECS mp)"
    else
        warn "SIKERTELEN — napló: $log"; fails=$((fails + 1))
    fi
    # a teszt-image visszaállítása a FusionOS alapértelmezésre
    FUSION_VARIANT="test" step_build >/dev/null
    FUSION_VARIANT="test" step_image >/dev/null

    [ "$fails" -eq 0 ] || die "$fails boot-teszt sikertelen"
    ok "minden boot-teszt sikeres"
}
