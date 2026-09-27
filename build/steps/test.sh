# shellcheck shell=bash
# test — automatikus EFI boot-teszt QEMU + OVMF alatt (fejlesztői ellenőrzés).
# Három konfigurációval indít, és a soros naplóból ellenőrzi az eredményt:
#   std  + SATA  -> QEMU std VGA (1234:1111)   -> várt profil: generic-kms
#   vmware + SATA -> VMware SVGA II (15ad:0405) -> várt profil: vmware-svga  (= VirtualBox VMSVGA)
#   std  + USB   -> a lemezkép USB-pendrive-ként (xHCI + usb-storage), mint a ZBookon

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

step_test() {
    not_root
    need qemu-system-x86_64 timeout
    local code vars; code=$(_ovmf_code); vars=$(_ovmf_vars)
    [ -n "$code" ] && [ -n "$vars" ] || die "OVMF nem található (sudo apt install ovmf)"

    FUSION_VARIANT="test" step_build
    FUSION_VARIANT="test" step_image
    local out="$OUT_DIR/test" img="$OUT_DIR/test/fusionos.img"
    local accel="tcg"; [ -w /dev/kvm ] && accel="kvm"

    local fails=0 cfg vga bus want log diskdev
    for cfg in std-sata vmware-sata std-usb; do
        vga=${cfg%-*}; bus=${cfg#*-}
        case "$vga" in std) want=generic-kms ;; vmware) want=vmware-svga ;; esac
        case "$bus" in
            sata) diskdev=(-device "ahci,id=ahci0" -device "ide-hd,drive=disk0,bus=ahci0.0") ;;
            usb)  diskdev=(-device "qemu-xhci,id=xhci0" -device "usb-storage,drive=disk0,bus=xhci0.0") ;;
        esac
        log="$out/qemu-$cfg.log"
        step "QEMU EFI boot: -vga $vga, lemez: $bus (várt profil: $want, gyorsítás: $accel)"
        cp "$vars" "$out/vars-$cfg.fd"
        rm -f "$log"
        timeout 300 qemu-system-x86_64 \
            -machine q35,accel="$accel" -m 1024 -smp 2 \
            -drive if=pflash,format=raw,readonly=on,file="$code" \
            -drive if=pflash,format=raw,file="$out/vars-$cfg.fd" \
            -drive file="$img",format=raw,if=none,id=disk0,snapshot=on \
            "${diskdev[@]}" \
            -vga "$vga" -display none -serial "file:$log" -no-reboot \
            -monitor "unix:$out/qemu-$cfg.mon,server,nowait" >/dev/null 2>&1 &
        local qpid=$!
        # képernyőkép a tartási idő alatt (ha van python3)
        local t=0
        while kill -0 "$qpid" 2>/dev/null; do
            if [ ! -f "$out/screen-$cfg.ppm" ] && grep -qs 'FUSION-M0: BOOT OK' "$log"; then
                sleep 2
                have python3 && python3 - "$out/qemu-$cfg.mon" "$out/screen-$cfg.ppm" <<'PY' 2>/dev/null || true
import socket, sys, time
s = socket.socket(socket.AF_UNIX); s.connect(sys.argv[1])
time.sleep(0.3); s.recv(65536)
s.sendall(("screendump %s\n" % sys.argv[2]).encode()); time.sleep(1.5); s.close()
PY
            fi
            sleep 1; t=$((t + 1))
        done
        wait "$qpid" 2>/dev/null
        if grep -q 'FUSION-M0: BOOT OK' "$log" \
           && grep -q 'FUSION-M0: PARTITIONS 4/4' "$log" \
           && grep -q "FUSION-M0: DISPLAY_PROFILE=$want " "$log"; then
            ok "SIKERES ($t mp): $(grep -o 'Betöltött UKI:.*' "$log" | head -n1)"
        else
            warn "SIKERTELEN — napló: $log"
            tail -n 25 "$log" | sed 's/^/      /' >&2
            fails=$((fails + 1))
        fi
    done
    [ "$fails" -eq 0 ] || die "$fails boot-teszt sikertelen"
    ok "minden boot-teszt sikeres"
}
