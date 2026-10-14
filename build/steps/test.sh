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

# _mon <cfg-név> <parancs>: egy parancs a futó QEMU monitorának
_mon() {
    have python3 || return 1
    python3 -c '
import socket, sys, time
s = socket.socket(socket.AF_UNIX); s.connect(sys.argv[1])
time.sleep(0.3); s.recv(65536)
s.sendall((sys.argv[2] + "\n").encode()); time.sleep(0.8); s.close()
' "$OUT_DIR/test/qemu-$1.mon" "$2" 2>/dev/null
}

# USB-soros eszköz (FTDI 0403:6001 — a lézer szerep illeszkedik rá) külön xHCI-n
# (a QEMU usb-serial csak nyitott chardev-vel csatlakozik: ezért "file" háttér, nem "null"),
# a kihúzás/visszadugás a monitoron át: device_del / device_add
SERIAL_DEV="usb-serial,chardev=fser0,id=fser0dev,bus=fxhci.0,port=2"
# teszt-pendrive (M6, automatikus csatolás): ugyanazon az xHCI-n, három partícióval —
# FAT32 (FUSIONUSB), exFAT (FUSIONEXF), NTFS (FUSIONNTFS); az utóbbi kettő csak, ha a gépen van mkfs.exfat / mkntfs
STICK_DEV="usb-storage,drive=stick0,bus=fxhci.0,port=3,removable=on"
# üres USB-lemez a Lemezkezelő próbájához (formázás, címke, partíciók) — 96 MiB, partíciós tábla nélkül
SCRATCH_DEV="usb-storage,drive=scratch0,bus=fxhci.0,port=4,removable=on,serial=FUSIONSCRATCH"

# _btvirt: a BlueZ virtuális Bluetooth-vezérlője (bluez-test-tools) a teszthez, a csomagtárolóból (root nélkül)
_btvirt() {
    local f="$OUT_DIR/test/btvirt" d
    [ -x "$f" ] && return 0
    have apt-get && have dpkg-deb || return 1
    d=$(mktemp -d)
    ( cd "$d" && apt-get download -qq bluez-test-tools >/dev/null 2>&1 ) && dpkg-deb -x "$d"/bluez-test-tools_*.deb "$d/x" \
        && install -m 0755 "$d/x/usr/bin/btvirt" "$f"
    rm -rf "$d"
    [ -x "$f" ] || { warn "btvirt nem érhető el (bluez-test-tools) — a Bluetooth-próba kimarad"; return 1; }
}

# _make_stick <kép>: a partíciókat külön fájlban formázzuk, majd a helyükre másoljuk (root nélkül)
_make_stick() {
    local img=$1 d parts n=0 off
    d=$(mktemp -d)
    rm -f "$img"; truncate -s 200M "$img"
    printf 'label: gpt\nstart=2048, size=120832, type=EBD0A0A2-B9E5-4433-87C0-68B6B72699C7, name=FUSIONUSB\nstart=124928, size=65536, type=EBD0A0A2-B9E5-4433-87C0-68B6B72699C7, name=FUSIONEXF\nstart=192512, size=, type=EBD0A0A2-B9E5-4433-87C0-68B6B72699C7, name=FUSIONNTFS\n' \
        | sfdisk -q "$img" >/dev/null
    truncate -s $((120832 * 512)) "$d/p1"; mkfs.vfat -F 32 -n FUSIONUSB "$d/p1" >/dev/null
    printf 'FUSION-USB\n' > "$d/f.txt"; mcopy -i "$d/p1" "$d/f.txt" ::/fusion-usb.txt
    # a Bluetooth-próba virtuális vezérlője (btvirt) — a képben nincs, csak a teszt hozza
    _btvirt && mcopy -i "$d/p1" "$OUT_DIR/test/btvirt" ::/btvirt
    dd if="$d/p1" of="$img" bs=512 seek=2048 conv=notrunc status=none
    if command -v mkfs.exfat >/dev/null; then
        truncate -s $((65536 * 512)) "$d/p2"; mkfs.exfat -L FUSIONEXF "$d/p2" >/dev/null
        dd if="$d/p2" of="$img" bs=512 seek=124928 conv=notrunc status=none
    fi
    if command -v mkntfs >/dev/null; then
        off=$(sfdisk -d "$img" | awk -F'[=,]' '/name="FUSIONNTFS"/ {gsub(/ /,"",$2); gsub(/ /,"",$4); print $2" "$4}')
        set -- $off
        truncate -s $(($2 * 512)) "$d/p3"; mkntfs -q -F -Q -L FUSIONNTFS -s 512 -p "$1" -H 16 -S 63 "$d/p3" >/dev/null 2>&1
        dd if="$d/p3" of="$img" bs=512 seek="$1" conv=notrunc status=none
    fi
    rm -rf "$d"
}

# _qemu_run <cfg-név> <vga> <busz> <napló> <várt záró marker>
# QEMU_EXTRA (tömb): további QEMU-argumentumok; QEMU_HOTPLUG=1: a FUSION-M3 jelzésekre
# kihúzza és visszadugja a soros eszközt
_qemu_run() {
    local cfg="$1" vga="$2" bus="$3" log="$4" marker="$5"
    local out="$OUT_DIR/test" img="${QEMU_DISK:-$OUT_DIR/test/fusionos.img}"
    local snap="${QEMU_SNAPSHOT:-on}" noreboot=(-no-reboot); [ "${QEMU_REBOOT:-0}" = 1 ] && noreboot=()
    local accel="tcg"; [ -w /dev/kvm ] && accel="kvm"
    local diskdev
    case "$bus" in
        sata) diskdev=(-device "ahci,id=ahci0" -device "ide-hd,drive=disk0,bus=ahci0.0${QEMU_DISK_OPTS:+,$QEMU_DISK_OPTS}") ;;
        usb)  diskdev=(-device "qemu-xhci,id=xhci0" -device "usb-storage,drive=disk0,bus=xhci0.0") ;;
    esac
    cp "$(_ovmf_vars)" "$out/vars-$cfg.fd"
    rm -f "$log" "$out/screen-$cfg.ppm"
    timeout "${QEMU_TIMEOUT:-600}" qemu-system-x86_64 \
        -machine q35,accel="$accel" -m 2048 -smp 2 \
        -drive if=pflash,format=raw,readonly=on,file="$(_ovmf_code)" \
        -drive if=pflash,format=raw,file="$out/vars-$cfg.fd" \
        -drive file="$img",format=raw,if=none,id=disk0,snapshot="$snap" \
        "${diskdev[@]}" \
        -nic user,model=e1000e \
        -audiodev none,id=snd0 -device ich9-intel-hda -device hda-duplex,audiodev=snd0 \
        -vga "$vga" -display none -serial "file:$log" "${noreboot[@]}" \
        -monitor "unix:$out/qemu-$cfg.mon,server,nowait" \
        "${QEMU_EXTRA[@]}" >/dev/null 2>"$out/qemu-$cfg.err" &
    local qpid=$! unplugged=0 replugged=0
    RUN_SECS=0
    while kill -0 "$qpid" 2>/dev/null; do
        if [ "${QEMU_HOTPLUG:-0}" = 1 ]; then
            if [ "$unplugged" = 0 ] && grep -qa "FUSION-M3: UNPLUG-NOW" "$log"; then
                _mon "$cfg" "device_del fser0dev"; unplugged=1
            fi
            if [ "$replugged" = 0 ] && grep -qa "FUSION-M3: REPLUG-NOW" "$log"; then
                _mon "$cfg" "device_add $SERIAL_DEV"; replugged=1
            fi
        fi
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
    [ -s "$out/qemu-$cfg.err" ] && sed 's/^/      qemu: /' "$out/qemu-$cfg.err" | head -n 5 >&2
    return 0
}

_check() {  # _check <napló> <minta> <leírás>
    if grep -qa -- "$2" "$1"; then return 0; fi
    warn "hiányzik: $3  ($2)"; return 1
}

_test_ab() {
    local out="$OUT_DIR/test" log="$OUT_DIR/test/qemu-ab.log" upd="$OUT_DIR/test/ab-upd" bad
    FUSION_VARIANT="test" step_build >/dev/null
    FUSION_VARIANT="test" FUSION_TEST_AB=good step_image >/dev/null
    cp --sparse=always "$out/fusionos.img" "$out/ab.img"
    rm -rf "$upd"; mkdir -p "$upd"
    # „good”: ugyanaz a rendszerkép, újabb build (a systemd-boot az újabbat választja)
    sleep 1; FUSION_VARIANT="test" step_build >/dev/null
    _make_fupd "$out/update" "$upd/good.fupd" >/dev/null
    # „bad”: még újabb build, de a rendszerkép sérült (nem EROFS) — az initramfs nem tudja csatolni
    sleep 1; FUSION_VARIANT="test" step_build >/dev/null
    bad="$out/ab-bad.img"; head -c $((64 * 1024 * 1024)) /dev/zero | tr '\0' 'X' > "$bad"
    _make_update_dir "$upd/bad" "$out/$(uki_name A)" "$out/$(uki_name B)" "$bad" >/dev/null
    _make_fupd "$upd/bad" "$upd/bad.fupd" >/dev/null; rm -rf "$upd/bad"
    rm -f "$out/upd.img"; truncate -s 1600M "$out/upd.img"
    mkfs.ext4 -q -F -E nodiscard -L FUSIONUPD -d "$upd" "$out/upd.img"
    rm -rf "$upd" "$bad"
    step "QEMU EFI boot → A/B frissítés: A → B (véglegesítés) → hibás frissítés → 3 próba → vissza B-re"
    # shellcheck disable=SC2054  # a vesszők a QEMU-argumentumok részei
    QEMU_EXTRA=(-drive "file=$out/upd.img,format=raw,if=none,id=upd0,snapshot=on" -device "ide-hd,drive=upd0,bus=ahci0.1")
    QEMU_HOTPLUG=0; QEMU_TIMEOUT=3600
    QEMU_DISK="$out/ab.img" QEMU_SNAPSHOT=off QEMU_REBOOT=1 _qemu_run ab std sata "$log" "FUSION-AB: DONE"
    rm -f "$out/ab.img" "$out/upd.img"
    local ok_run=1 tries
    _check "$log" "FUSION-AB: BOOT step=good slot=A" "1. indítás: A slot" || ok_run=0
    _check "$log" "FUSION-AB: GUARD fusion-admin: " "a segéd csak engedélyezett helyről telepít" || ok_run=0
    _check "$log" "FUSION-AB:   frissítőcsomag: FusionOS .* — good.fupd" "telepítés .fupd fájlból, a felhasználó (fusion-admin)" || ok_run=0
    _check "$log" "FUSION-AB: APPLY good rc=0" "frissítés a B slotba" || ok_run=0
    _check "$log" "FUSION-AB: BOOT step=bad slot=B .*count=.*B+" "2. indítás: B, próbaként (számlálóval)" || ok_run=0
    _check "$log" "FUSION-AB: STATE VÉGLEGESÍTVE: fusionos-.*-B.efi" "a B véglegesítve (a számláló lekerült)" || ok_run=0
    _check "$log" "FUSION-AB:   új boot-bejegyzés: fusion-meres-nouveau" "a frissítés pótolta a hiányzó boot-bejegyzést" || ok_run=0
    _check "$log" "FUSION-AB: ENTRY nouveau=/EFI/Linux/fusionos-[^ ]*-B.efi slot=fusion.slot=B" "a pótolt bejegyzés a véglegesített B-re mutat" || ok_run=0
    _check "$log" "FUSION-AB: APPLY bad rc=0" "a hibás frissítés az A slotba" || ok_run=0
    tries=$(grep -ac "frissítés utáni próba-indítás" "$log")
    [ "$tries" -ge 3 ] || { warn "hiányzik: 3 sikertelen próba-indítás (volt: $tries)"; ok_run=0; }
    _check "$log" "FUSION-AB: BOOT step=final slot=B" "3 próba után magától a B indult" || ok_run=0
    _check "$log" "FUSION-AB:   *A: fusionos-.*-A+0-[0-9]*.efi  \[HIBÁS" "az A bejegyzés hibásként megjelölve" || ok_run=0
    _check "$log" "FUSION-AB: ENTRY-POTOLVA intel=/EFI/Linux/fusionos-[^ ]*-B.efi opts=1" "a hiányzó mérési bejegyzést a boot-check pótolta" || ok_run=0
    _check "$log" "FUSION-AB: FW count=3 first=eredeti" "3 UEFI-bejegyzés (F9), a boot-sorrend eleje változatlan" || ok_run=0
    _check "$log" "FUSION-AB: FWBOOT .*-kozvetlen render=fusion.ui.render=software fusion.slot=B" "indítás UEFI-bejegyzésről: a kiegészített parancssor átjut" || ok_run=0
    _check "$log" "FUSION-AB: DONE" "a teszt végigfutott" || ok_run=0
    grep -a 'FUSION-AB\|próba-indítás' "$log" | grep -v 'FUSION-AB:   [ 0-9]*%' | sed 's/^/      /' >&2
    if [ "$ok_run" -eq 1 ]; then ok "SIKERES ($RUN_SECS mp)"; return 0; fi
    warn "SIKERTELEN — napló: $log"; return 1
}

_test_installer() {
    local out="$OUT_DIR/test" log="$OUT_DIR/test/qemu-installer.log" ok_run=1
    step "QEMU EFI boot → telepítő pendrive (USB) → új telepítés és újratelepítés (DATA megmarad) → indítás a céllemezről"
    [ -r "$out/fusionos-telepito.img" ] || FUSION_VARIANT="test" step_installer_image
    rm -f "$out/target.img" "$out/t3backup.img" "$out/t3media.img"
    truncate -s 12G "$out/target.img"; truncate -s 4G "$out/t3backup.img"; truncate -s 3G "$out/t3media.img"
    # T3: mentőlemez (FUSIONBACKUP) és egy üres pendrive a FusionOS-ben készülő telepítőnek (FUSIONMEDIA)
    # shellcheck disable=SC2054  # a vesszők a QEMU-argumentumok részei
    QEMU_EXTRA=(-drive "file=$out/fusionos-telepito.img,format=raw,if=none,id=inst0,snapshot=on"
                -device qemu-xhci,id=ixhci -device "usb-storage,drive=inst0,bus=ixhci.0,removable=on,bootindex=1"
                -drive "file=$out/t3backup.img,format=raw,if=none,id=bk0" -device "usb-storage,drive=bk0,bus=ixhci.0,removable=on,serial=FUSIONBACKUP"
                -drive "file=$out/t3media.img,format=raw,if=none,id=md0" -device "usb-storage,drive=md0,bus=ixhci.0,removable=on,serial=FUSIONMEDIA")
    QEMU_HOTPLUG=0
    QEMU_DISK="$out/target.img" QEMU_SNAPSHOT=off QEMU_REBOOT=1 QEMU_DISK_OPTS="serial=FUSIONTARGET,bootindex=0" QEMU_TIMEOUT=4200 \
        _qemu_run installer std sata "$log" "FUSION-M1: POWEROFF"
    _check "$log" "FUSION-INST: BOOT slot=I installer=1 data=tmpfs state=running failed=0" "a telepítő pendrive elindul (telepítő mód, írható réteg RAM-ban)" || ok_run=0
    _check "$log" "FUSION-INST: WINDOW 1" "a Fusion Telepítő ablaka megjelenik" || ok_run=0
    _check "$log" "FUSION-INSTALLER: PAYLOAD ok" "a telepítendő .fupd a pendrive-on" || ok_run=0
    _check "$log" "FUSION-INSTALLER: RESULT ok" "a telepítő lemezlistája és felülete" || ok_run=0
    _check "$log" "FUSION-INST: GUARD .*nem egyezik.* | .*telepítő pendrive | .*DATA megőrzésével csak" "védelem: megerősítés, a telepítő pendrive, a DATA-megőrzés feltétele" || ok_run=0
    _check "$log" "FUSION-INST: NEW rc=0 .*parts=FUSION_ESP,FUSION_A,FUSION_B,FUSION_DATA fs=vfat,erofs,,ext4" "új telepítés: partíciók, rendszerkép, ESP, DATA" || ok_run=0
    _check "$log" "FUSION-INST: KEEP rc=0 .*marker=telepitett" "újratelepítés: a DATA tartalma megmaradt" || ok_run=0
    _check "$log" "FUSION-M1: BOOTDISK sda MARKER telepitett" "a telepített lemezről indult, a megtartott DATA-val" || ok_run=0
    _check "$log" "FUSION-M1: SLOT A" "A slot" || ok_run=0
    _check "$log" "FUSION-M7: BOOTCHECK ok: véglegesített rendszer" "a telepített rendszer véglegesített (nem próba)" || ok_run=0
    _check "$log" "FUSION-M1: FAILEDCOUNT 0" "a telepített rendszeren nincs hibás szolgáltatás" || ok_run=0
    _check "$log" "FUSION-M6: SHELL ready=yes" "Fusion Desktop a telepített rendszeren" || ok_run=0
    # T3: mentés és telepítő pendrive a futó FusionOS-ből; indítás az új pendrive-ról; új telepítés a mentésből
    _check "$log" "FUSION-T3: BACKUP rc=0 .*complete=True" "DATA mentése egy külső lemezre (fusion-backup)" || ok_run=0
    _check "$log" "FUSION-T3: LIST targets=[1-9] backups=1" "a mentés a listában" || ok_run=0
    _check "$log" "FUSION-T3: MEDIA rc=0 .*parts=FUSION_IESP,FUSION_ISYS,FUSION_IPAY guard=1" "telepítő pendrive a FusionOS-ből (.fupd-ből), gépelt megerősítéssel" || ok_run=0
    _check "$log" "FUSION-T3: BOOTNEXT ok" "indítás az új telepítő pendrive-ról (UEFI BootNext)" || ok_run=0
    _check "$log" "FUSION-T3: MEDIA-BOOT FUSIONMEDIA" "a FusionOS-ben készült telepítő pendrive elindul" || ok_run=0
    _check "$log" "FUSION-T3: RESTORE rc=0 .*marker=mentett wifi=1" "új telepítés a mentésből, Wi-Fi átvétele" || ok_run=0
    _check "$log" "FUSION-M1: BOOTDISK sda MARKER mentett" "a visszaállított rendszer elindul (a mentett DATA-val)" || ok_run=0
    grep -a 'FUSION-T3: [A-Z]' "$log" | sed 's/^/      /' >&2
    grep -a 'FUSION-INST' "$log" | grep -v '^.*FUSION-INST:   *\(  \|LÉPÉS\)' | sed 's/^/      /' | tail -n 40 >&2
    rm -f "$out/target.img" "$out/t3backup.img" "$out/t3media.img"
    if [ "$ok_run" -eq 1 ]; then ok "SIKERES ($RUN_SECS mp)"; return 0; fi
    warn "SIKERTELEN — napló: $log"; return 1
}

step_test() {
    not_root
    QEMU_EXTRA=(); QEMU_HOTPLUG=0
    need qemu-system-x86_64 timeout
    [ -n "$(_ovmf_code)" ] && [ -n "$(_ovmf_vars)" ] || die "OVMF nem található (sudo apt install ovmf)"
    [ -r "$(rootfs_img)" ] || die "nincs rendszerkép — előbb: build/fusion-build all"
    local out="$OUT_DIR/test" fails=0 cfg vga bus want log drv desk ok_run

    step "Egységtesztek (rendszer nélkül): Hardware Layer, Fusion API"
    sh "$FUSION_ROOT/tests/hwprobe-test.sh" > "$out.unit.log" 2>&1 || { cat "$out.unit.log"; die "hwprobe-test sikertelen"; }
    python3 "$FUSION_ROOT/tests/fusion-api-test.py" >> "$out.unit.log" 2>&1 || { cat "$out.unit.log"; die "fusion-api-test sikertelen"; }
    grep '^Eredmény' "$out.unit.log" | sed 's/^/    /'
    FUSION_VARIANT="test" step_build
    FUSION_VARIANT="test" step_image
    FUSION_VARIANT="test" step_installer_image

    for cfg in std-sata vmware-sata std-usb; do
        vga=${cfg%-*}; bus=${cfg#*-}
        case "$vga" in
            std)    want=generic-kms; drv=none;   desk=1 ;;
            # QEMU alatt a vmwgfx nem veszi át az eszközt ("unsupported hypervisor"):
            # a Hardware Layer ezt "failed"-ként jelzi, grafikus felület itt nincs.
            # A VMSVGA támogatott környezete a VirtualBox (kézi ellenőrzés).
            vmware) want=vmware-svga; drv=failed; desk=0 ;;
        esac
        log="$out/qemu-$cfg.log"
        # az std+SATA futásban egy USB-soros eszköz is van: az eszközréteg (M3) próbája
        local ser=0 serinfo=""
        if [ "$cfg" = std-sata ]; then
            ser=1; serinfo=", + USB-soros eszköz"
            # shellcheck disable=SC2054  # a vesszők a QEMU-argumentumok részei
            _make_stick "$out/stick.img"
            rm -f "$out/scratch.img"; truncate -s 96M "$out/scratch.img"
            QEMU_EXTRA=(-chardev "file,id=fser0,path=$out/serial-$cfg.out" -device qemu-xhci,id=fxhci -device "$SERIAL_DEV"
                        -drive "file=$out/stick.img,format=raw,if=none,id=stick0" -device "$STICK_DEV"
                        -drive "file=$out/scratch.img,format=raw,if=none,id=scratch0" -device "$SCRATCH_DEV")
            QEMU_HOTPLUG=1; QEMU_TIMEOUT=3200   # a Wine-környezet létrehozása KVM nélkül lassú; 0.0.40: + kamera, BT, CUPS
        else
            # terhelt gépen (KVM nélkül) a teljes selftest 1200 mp fölé is mehet (0.0.43: 1130 mp-nél vágta el)
            QEMU_EXTRA=(); QEMU_HOTPLUG=0; QEMU_TIMEOUT=1800
        fi
        step "QEMU EFI boot → FusionOS: -vga $vga, lemez: $bus (várt profil: $want)$serinfo"
        _qemu_run "$cfg" "$vga" "$bus" "$log" "FUSION-M1: SYSTEM UP"
        ok_run=1
        _check "$log" "FUSION-M1: SYSTEM UP state=running" "systemd fut, hibátlanul" || ok_run=0
        _check "$log" "FUSION-M1: ROOT overlay usr=erofs ro" "gyökér-overlay, /usr csak olvasható (EROFS)" || ok_run=0
        _check "$log" "FUSION-M1: MOUNTS data=ext4" "/data" || ok_run=0
        _check "$log" "FUSION-M1: SLOT A" "A slot" || ok_run=0
        _check "$log" "FUSION-M7: IMPORT owner=fusion WAITONLINE --any" "a /data/import a felhasználóé; wait-online: elég egy kapcsolat" || ok_run=0
        _check "$log" "FUSION-M7: BOOTCHECK ok: véglegesített rendszer (fusionos-.*-A.efi), slot A" "indulás-ellenőrzés (nem próba)" || ok_run=0
        _check "$log" "FUSION-M1: BOOTDISK sda MARKER none" "a boot-lemez felismerve (LoaderDevicePartUUID)" || ok_run=0
        _check "$log" "FUSION-M1: DISPLAY_PROFILE=$want STATUS=ok DRIVER=$drv" "hardverprofil és driver" || ok_run=0
        _check "$log" "FUSION-M1: GETTY active" "bejelentkezési képernyő" || ok_run=0
        _check "$log" "FUSION-M1: LOCALE hu_HU.UTF-8 KEYMAP hu" "magyar nyelv és billentyűzet" || ok_run=0
        _check "$log" "FUSION-M1: USER fusion:/home/fusion" "fusion felhasználó" || ok_run=0
        _check "$log" "FUSION-M1: MACHINE-ID ok" "machine-id" || ok_run=0
        _check "$log" "FUSION-M1: ROOTOWNER root UNSAFE 0" "a gyökér a root tulajdona, nincs 'unsafe path' figyelmeztetés" || ok_run=0
        _check "$log" "FUSION-M1: FAILEDCOUNT 0" "nincs hibás szolgáltatás" || ok_run=0
        if [ "$desk" -eq 1 ]; then
            _check "$log" "FUSION-M2: XORG up" "Fusion Desktop: Xorg fut" || ok_run=0
            _check "$log" "FUSION-M2: GL renderer=[^ ]" "OpenGL renderer" || ok_run=0
            _check "$log" "FUSION-M2: WM jwm" "ablakkezelő" || ok_run=0
            _check "$log" "FUSION-M2: XKB hu" "magyar billentyűzet az X-ben" || ok_run=0
            # M6: Fusion Shell — mindkét mérőváltozat: panel (dock, 40 px foglalás), Start menü
            # M6: Fusion Desktop — Shell (panel, Start menü, értesítés), Fájlkezelő, Beállítások
            _check "$log" "FUSION-M6: SHELL ready=yes .*panel=1 .*menu=1" "Fusion Shell: panel és Start menü" || ok_run=0
            _check "$log" 'FUSION-M6: USERDIRS XDG_DOWNLOAD_DIR="$HOME/Letöltések" dir=van' "Letöltések mappa (XDG)" || ok_run=0
            _check "$log" "FUSION-M6: FLATPAK-DL path=/home/fusion/Letöltések host=/home/fusion/Letöltések/fusion-flatpak-letoltes.AppImage" "Flatpak-program letöltése a valódi Letöltések mappába" || ok_run=0
            _check "$log" "FUSION-M6: X11 _NET_WM_WINDOW_TYPE_DOCK strut=40" "panel: dock, 40 px foglalás" || ok_run=0
            _check "$log" "FUSION-M6: NOTIFY rc=0 last=FusionOS önteszt toasts=[1-9]" "értesítés a D-Buson (org.freedesktop.Notifications) → buborék" || ok_run=0
            _check "$log" "FUSION-FILES: RESULT ok" "Fájlkezelő: másolás, mozgatás, törlés, archívumok, keresés, összehasonlítás" || ok_run=0
            _check "$log" "FUSION-M6: FILES window=1" "Fájlkezelő ablak" || ok_run=0
            _check "$log" "FUSION-WIFI: FUSION-SETTINGS: WIFI ok=True device=wlan[0-9] state=connected ssid=FusionTeszt networks=.*FusionTeszt\\*" "Beállítások → Wi-Fi: állapot és hálózatlista (iwd a D-Buson)" || ok_run=0
            _check "$log" "FUSION-M6:   FUSION-SETTINGS: WIFI ok=True .*known=.*FusionTeszt" "Beállítások → Wi-Fi: megjegyzett hálózat" || ok_run=0
            _check "$log" "FUSION-SETTINGS: DISPLAY ok=True" "Beállítások → Kijelző (xrandr)" || ok_run=0
            _check "$log" "FUSION-SETTINGS: PRINTER klipper=active moonraker=active nginx=active" "Beállítások → Nyomtató" || ok_run=0
            _check "$log" "FUSION-SETTINGS: PROGRAMS lightburn=nincs installers=" "Programkezelő: az ismert, nem telepített program (recept)" || ok_run=0
            _check "$log" "FUSION-SETTINGS: UPDATE version=$FUSION_VERSION slot=A entries=A:ok\* files=0 error=-" "Beállítások → Rendszerfrissítés: állapot (sudo fusion-admin update-status)" || ok_run=0
            _check "$log" "FUSION-TASKS: RESULT ok" "Feladatkezelő: lefagyott ablak felismerése és bezárása" || ok_run=0
            _check "$log" "FUSION-DISKS: GUARD ok" "Lemezkezelő: a FusionOS saját lemeze nem módosítható" || ok_run=0
            _check "$log" "FUSION-DISKS: RESULT ok" "Lemezkezelő: lemezlista (sudo), felület" || ok_run=0
            _check "$log" "FUSION-SETTINGS: REPORT dir=/home/fusion/Letöltések" "Beállítások → Hibajelentés" || ok_run=0
            _check "$log" "FUSION-J3: RENDER set=ok mode=software pss=[0-9]*MB back=ok file=gpu" "felület rajzolása: szoftveres ↔ grafikus kártya (Beállítások → Kijelző)" || ok_run=0
            _check "$log" "FUSION-J3: PAM lastlog=0 login=0" "nincs pam_lastlog-hiba a naplóban" || ok_run=0
            _check "$log" "FUSION-API: USER version=1 profile=generic-kms roles=laser,printer present=[a-z,-]* ROOT generic-kms (ok, driver: none)" "Fusion API (M8): a fusion csomag felhasználóként és rootként" || ok_run=0
            _check "$log" "FUSION-API: NOTIFY ok" "Fusion API: értesítés a fusion-notify-on át" || ok_run=0
            # M8b: a fusion parancssor, sémák, feladat-protokoll
            _check "$log" "FUSION-CLI: JSON api-version=ok system=ok hardware=ok devices=ok volumes=ok power=ok jobs=ok schema=ok programs list=ok" "fusion CLI: minden lekérdezés JSON-ja a leírás szerint" || ok_run=0
            _check "$log" "FUSION-CLI: VERSION $FUSION_VERSION 1 generic-kms" "fusion system: verzió, API, kijelzőprofil" || ok_run=0
            _check "$log" "FUSION-LASER: STATE ok present=[TF][a-z]* dev=" "Lézer állapot (M8d): a szerep a Fusion API-ból" || ok_run=0
            _check "$log" "FUSION-LASER: QML ok" "Lézer állapot: a felület betöltődik" || ok_run=0
            _check "$log" "FUSION-TRASH: count=2 auto=30 removed=1 left=friss.txt, count=1 auto=0 after=0" "Lomtár: automatikus ürítés 30 nap után, kikapcsolható, teljes ürítés" || ok_run=0
            _check "$log" "FUSION-PROGWIN: window=1 wait=" "a Programkezelő külön ablakban" || ok_run=0
            _check "$log" "FUSION-CLI: VALIDATE ok rc-hibas=1" "fusion validate: a receptek és szerepfájlok érvényesek, a hibás leírás 1-es kóddal" || ok_run=0
            _check "$log" "FUSION-CLI: JOB start=ok running=False rc=0 title=Hibajelentés file=van" "feladat-protokoll: a Beállítások hibajelentése a fusion.jobs-on át" || ok_run=0
            _check "$log" "FUSION-M6: CTRLALTDEL 1 target=masked" "Ctrl+Alt+Del: Feladatkezelő (a konzolon nem indít újra)" || ok_run=0
            _check "$log" "FUSION-SETTINGS: APPS prog-lightburn,printer,laser,mainsail,files,settings,programs,store,drive,tasks,disks,camera,vaskrom,terminal" "Start menü programlistája (Programkezelő-bejegyzéssel)" || ok_run=0
            # 0.0.40: kamera, Bluetooth, nyomtatás
            _check "$log" "FUSION-SETTINGS: QML ok" "Beállítások: minden oldal felülete betölthető" || ok_run=0
            # felhasználókezelés
            _check "$log" "FUSION-USERS: ADD felvéve: proba | LIST fusion:admin,proba:user auto=fusion" "felhasználó felvétele (Beállítások → Felhasználók)" || ok_run=0
            _check "$log" "FUSION-USERS: OWN-PASSWD a jelszó megváltozott | WRONG-OLD .*nem egyezik | NONADMIN-DISK .*rendszergazdai jog kell .*| BASE .*rögzített" "jelszócsere, korlátozott felhasználó, a fusion/fusion védett" || ok_run=0
            _check "$log" "FUSION-USERS: PERSIST uid=\([0-9]*\)/\1 hash=ok AUTOLOGIN 11 DELETED igen home=törölve" "a felhasználó a rendszerfrissítés után is megmarad; automatikus belépés; törlés" || ok_run=0
            # M9: jogosultságok
            _check "$log" "FUSION-M9: XINPUT added=[1-9][0-9]* failed=0 input-group=0" "bemeneti eszközök az input csoport nélkül (Xorg)" || ok_run=0
            _check "$log" "FUSION-M9: PERMISSIONS jogproba:sandbox:net=False:folders=Projektek,Letöltések:ro validate=ok" "fusion permissions: a programok jogai" || ok_run=0
            _check "$log" "FUSION-M9: CHECK True False" "jogosultság-kapu: saját program igen, ismeretlen nem" || ok_run=0
            _check "$log" "FUSION-G1: VASKROM SIM ok" "Vas & Króm: a gyorsulási modell" || ok_run=0
            _check "$log" "FUSION-G1: VASKROM ART ok" "Vas & Króm: a motor rajza (SVG)" || ok_run=0
            _check "$log" "FUSION-G1: VASKROM SOUND ok" "Vas & Króm: motorhang (V2, V8), kipörgés, jelzőhangok — kiszámolva" || ok_run=0
            _check "$log" "FUSION-G1: VASKROM QML ok 0 figyelmeztetés" "Vas & Króm: a felület minden oldala és egy próbafutam" || ok_run=0
            _check "$log" "FUSION-G1: VASKROM-LINK /usr/lib/fusion/desktop/games/vaskrom/fusion_vaskrom.py menu=True" "Vas & Króm: indító és Start menü (Játékok)" || ok_run=0
            _check "$log" "FUSION-J8: MODULES uvcvideo btusb btintel btrtl hci_vhci bnep hidp rfcomm fw=[1-9][0-9]* groups=2 qtmm=ok" "kamera- és Bluetooth-modulok, Intel BT-firmware, csoportok, Qt Multimedia" || ok_run=0
            _check "$log" "FUSION-M6: SETTINGS window=1 .*switched=1" "Beállítások ablak, egy példány (oldalváltás)" || ok_run=0
            _check "$log" "FUSION-M6: DASHBOARD viewable=1 type=_NET_WM_WINDOW_TYPE_DESKTOP" "irányítópult az asztalon (asztal típusú ablak)" || ok_run=0
            _check "$log" "FUSION-M6: USERNS restrict=0" "felhasználói névterek a homokozóhoz" || ok_run=0
            _check "$log" "FUSION-M6: SESSION-ENV 2" "a munkamenet-busz szolgáltatásai látják a kijelzőt (DISPLAY, XDG_CURRENT_DESKTOP)" || ok_run=0
            _check "$log" "FUSION-APPM: FLATPAK Flatpak 1\\." "Flatpak a képben" || ok_run=0
            _check "$log" "FUSION-APPM: SANDBOX ok" "homokozó (bubblewrap) a fusion felhasználóként" || ok_run=0
            _check "$log" "FUSION-APPM: CA ok" "tanúsítványok a HTTPS-hez (ca-certificates)" || ok_run=0
            _check "$log" "FUSION-APPM: PROGRAMS-DIR ok" "/data/programs a fusion felhasználóé" || ok_run=0
            _check "$log" "FUSION-APPM: PORTAL ok conf=ok" "asztali portálok telepítve, FusionOS-beállítás" || ok_run=0
            _check "$log" "FUSION-M6: PORTAL filechooser=v u [0-9]" "a portál elindul és fájlválasztót kínál (D-Bus)" || ok_run=0
            _check "$log" "FUSION-SETTINGS: STORE categories=10 text=ok" "Programbolt: kategóriák, leírás-átalakítás" || ok_run=0
            _check "$log" "FUSION-SOUND: KERNEL cards=[1-9] hda=1" "hang: HDA-hangkártya a kernelben" || ok_run=0
            _check "$log" "FUSION-SOUND: SERVER ok=True PulseAudio_(on_PipeWire.* sinks=[1-9]" "hang: PipeWire fut, van kimenet" || ok_run=0
            _check "$log" "FUSION-SOUND: SET volume=40 shell=40" "hangerő állítása; a panel látja" || ok_run=0
            _check "$log" "FUSION-SOUND: MUTE True False" "némítás be/ki" || ok_run=0
            _check "$log" "FUSION-SOUND: TEST rc=0" "próbahang lejátszása" || ok_run=0
            _check "$log" "FUSION-SOUND: FLATPAK-SOCKET yes" "PulseAudio-foglalat a Flatpak-programoknak" || ok_run=0
            _check "$log" "FUSION-SOUND: KEYS 4" "hangerő-billentyűk (JWM)" || ok_run=0
            _check "$log" "FUSION-DRIVE: RCLONE v1\.[0-9.]*[^ ]* status=1" "Google Drive: rclone a képben, kezdetben nincs bejelentkezés" || ok_run=0
            _check "$log" "FUSION-DRIVE: LOGIN url=ok redirect=307:accounts.google.com" "bejelentkezés: a helyi kiszolgáló a Google-oldalra irányít" || ok_run=0
            _check "$log" "FUSION-DRIVE: MOUNT 1 read=felho write=helyrol .*volume=Google Drive\* unit=active" "csatolás (ál-Drive): olvasás, írás, Fájlkezelő-kötet, szolgáltatás" || ok_run=0
            _check "$log" "FUSION-DRIVE: LOGOUT mounted=0 conf=nincs enabled=disabled" "leválasztás: csatolás, jegy, automatikus indítás le" || ok_run=0
            _check "$log" 'FUSION-DEV: STATUS {"node": "v22.99.0", "npm": "10.99.0", "wrangler": "4.99.0"} owner=fusion path=/data/dev/node/bin/node /home/fusion/.local/bin/wrangler' "fejlesztői eszközök: Node.js a DATA-ra (ellenőrzőösszeggel), npm-csomag a saját mappába, PATH" || ok_run=0
            _check "$log" "FUSION-DEV: REMOVED 0" "Node.js eltávolítása" || ok_run=0
        fi
        _check "$log" "FUSION-M6: GUARD rc=1 fusion-admin: FusionOS-partíció\\|FUSION-M6: GUARD rc=1 fusion-admin: a FusionOS saját lemeze" "a rendszer saját kötete nem csatolható" || ok_run=0
        if [ "$cfg" = std-usb ]; then
            _check "$log" "FUSION-M6: MEDIA none" "a FusionOS saját USB-lemeze nem csatolódik automatikusan" || ok_run=0
        fi
        if [ "$ser" = 1 ]; then
            # 0.0.40: kamera (vivid), Bluetooth (btvirt a teszt-pendrive-ról), nyomtatás (CUPS, PDF) — csak ebben a futásban
            _check "$log" "FUSION-J8: CAMERAS 1 vivid-000-vid-cap:virtuális" "kamera: a Fusion API listája (V4L2)" || ok_run=0
            _check "$log" "FUSION-J8: CAMERA FRAMES ok" "Kamera program: élőkép (Qt Multimedia, FFmpeg)" || ok_run=0
            _check "$log" "FUSION-J8: CAMERA CAPTURE ok" "Kamera program: fénykép az élőképből" || ok_run=0
            _check "$log" "FUSION-J8: CAMERA VIDEO ok .*h264" "Kamera: videófelvétel (H.264, MP4)" || ok_run=0
            _check "$log" "FUSION-J8: CAMERA RENDER ok .*(felület: software) formátum: 1280x720" "Kamera: szoftveres felületnél is OpenGL (élőkép), 1280×720" || ok_run=0
            _check "$log" "FUSION-J8: BT controllers=2 .*service=active" "Bluetooth: bluetoothd a (virtuális) vezérlőkkel" || ok_run=0
            _check "$log" "FUSION-J8: BT-POWER True" "Bluetooth: bekapcsolás" || ok_run=0
            _check "$log" "FUSION-J8: BT-SCAN True talalt=True" "Bluetooth: eszközkeresés" || ok_run=0
            _check "$log" "FUSION-J8: BT-PAIR True" "Bluetooth: párosítás a saját ügynökkel" || ok_run=0
            _check "$log" "FUSION-J8: BT-LIST powered=True paired=True" "Bluetooth: a párosított eszköz a listában" || ok_run=0
            _check "$log" "FUSION-J8: BT-REMOVE True" "Bluetooth: eltávolítás" || ok_run=0
            _check "$log" "FUSION-J8: PRINT add=True PDF .*list=PDF:kész:PDF-fájl:True test=True True pdf=%PDF- wait=[0-9]*s owner=fusion" "nyomtatás: PDF-nyomtató, próbaoldal a ~/PDF-be (CUPS)" || ok_run=0
            _check "$log" "FUSION-J8: PRINT-DISCOVER rc=0 json=list remove=True left=0" "nyomtatás: keresés (lpinfo), eltávolítás" || ok_run=0
            _check "$log" "FUSION-M3: LASER ttyUSB" "/dev/fusion/laser létrejött" || ok_run=0
            _check "$log" "FUSION-M3: OPEN fusion ok" "a fusion felhasználó root nélkül megnyitja" || ok_run=0
            _check "$log" "FUSION-M3: DB laser path:0403:6001:" "hozzárendelés rögzítve (port szerint)" || ok_run=0
            _check "$log" "FUSION-M3: GONE" "kihúzáskor a név eltűnik" || ok_run=0
            _check "$log" "FUSION-M3: BACK ttyUSB" "visszadugás után ugyanazzal a névvel visszatér" || ok_run=0
            _check "$log" "FUSION-M3: REOPEN fusion ok" "visszadugás után is megnyitható" || ok_run=0
            _check "$log" "FUSION-M3: KEEPAWAKE inhibit=1 usbpower=on unit=active" "a lézer USB-ja nem altatható, a gép nem alszik el (fedél sem)" || ok_run=0
            _check "$log" "FUSION-M3: KEEPAWAKE-GONE inhibit=0" "kihúzás után az alvás újra engedélyezett" || ok_run=0
            _check "$log" "FUSION-M3: KEEPAWAKE-BACK inhibit=1" "visszadugás után újra ébren tart" || ok_run=0
            # M4 PoC (kísérleti futtató): a Windows-program csak a COM3-at látja, és azon át ír a lézer-eszközre
            _check "$log" "FUSION-M4: WINE wine-$WINE_VERSION" "Wine $WINE_VERSION a képben" || ok_run=0
            _check "$log" "FUSION-M4:   *SERIALCOMM: COM3\s*\$" "a SERIALCOMM-ban csak a COM3 (automatikus portkeresés kikapcsolva)" || ok_run=0
            _check "$log" "FUSION-M4:   *COM3: megnyitva, 115200 8N1" "a Windows-program megnyitja a COM3-at" || ok_run=0
            _check "$log" "FUSION-M4:   *GL_RENDERER: llvmpipe" "OpenGL a Wine-on át (WGL)" || ok_run=0
            _check "$log" "FUSION-M4:   *CAM: MediaFrameSourceGroup.FindAllAsync OK" "Windows kamera-felsoroló (WinRT) — LightBurn 2.x induláshoz" || ok_run=0
            _check "$log" "FUSION-M4: CHECK rc=0" "fwr check hibátlan" || ok_run=0
            _check "$log" "FUSION-M4: SYSTRAY showsystray=1 notray=1" "a Wine saját tálcaablaka kikapcsolva" || ok_run=0
            # Fusion Programkezelő: leírás-alapú programok (Windows: fwr, Linux: archívum), társítás, eltávolítás
            _check "$log" "FUSION-PROG: SYNC win64 prefix=/data/fwr/lightburn port=laser icon=icon.png" "a régi helyű LightBurn leírást kap, újratelepítés nélkül" || ok_run=0
            _check "$log" "FUSION-PROG: ASSOC-LBRN lightburn" "a .lbrn fájlt a LightBurn nyitja" || ok_run=0
            _check "$log" "FUSION-PROG: WIN rc=0 name=FusionTeszt exe=C:.Program Files.FusionTeszt.fusionteszt.exe icon=icon.png owner=fusion" "általános Windows-telepítő: a program a parancsikonból felismerve, ikon a programból" || ok_run=0
            _check "$log" "FUSION-PROG: DESKTOP Exec=fusion-run fusionteszt %U" "XDG-bejegyzés (fusion-run)" || ok_run=0
            _check "$log" "FUSION-PROG: RUN rc=0 .* args=.*P:.proba teszt.lbrn" "indítás fájllal: a Windows-program a P: meghajtón kapja" || ok_run=0
            # a Fusion helyei a Windows-program fájlválasztójában (0.0.36)
            _check "$log" "FUSION-PLACES: D=Adatok import=van overlay=nincs programs=nincs E=/run/media/fusion Z=nincs C=Program" "D: Adatok (a DATA felhasználói mappái), E: pendrive, nincs Z:" || ok_run=0
            _check "$log" "FUSION-PLACES: DESKTOP Adatok,Letöltések,Pendrive,Projektek,Saját mappa, docs=/home/fusion/Projektek dl=/home/fusion/Letöltések" "Asztal-hivatkozások, Dokumentumok → Projektek, Letöltések" || ok_run=0
            _check "$log" "FUSION-PLACES: HIDDEN root=0 trash=0 control=0" "a „/”, a Lomtár és a Vezérlőpult nem látszik" || ok_run=0
            _check "$log" "FUSION-PLACES: RUN-DATA rc=0 args=.*D:.import.proba adat.lbrn" "indítás DATA-n lévő fájllal: D:\\import\\…" || ok_run=0
            _check "$log" "FUSION-PROG: DETECT archive win64" "telepítőfájl felismerése" || ok_run=0
            _check "$log" "FUSION-URL: handler=fusion-urlproba.desktop xdg-open=--single-instance-on-url fusionproba://open?file=https%3A%2F%2Fmedia.printables.com%2Fx.stl portal=--single-instance-on-url fusionproba://open?file=portal" "URL-séma: a böngésző linkje a programhoz jut, a portálon át is kérdés nélkül (Printables → PrusaSlicer)" || ok_run=0
            _check "$log" "FUSION-PROG: NATIVE assoc=fprobaprog out=/tmp/x.fprb" "Linux-program archívumból, fájltársítás (X-Fusion-Open)" || ok_run=0
            _check "$log" "FUSION-PROG: APPS prog-fprobaprog,prog-fusionteszt,prog-lightburn,printer" "a Start menü a leírásokból" || ok_run=0
            _check "$log" "FUSION-PROG: REMOVED left=desktop=0 fwr-lightburn=nincs" "eltávolítás: mappa, Windows-környezet, Start menü bejegyzés" || ok_run=0
            # M5: Klipper + Moonraker + webes felület; szoftveres MCU-val a teljes lánc
            _check "$log" "FUSION-M5: SERVICES klipper=active moonraker=active nginx=active" "Klipper, Moonraker, nginx fut" || ok_run=0
            _check "$log" "FUSION-M5: CONFIG serial: /dev/fusion/printer" "alapkonfiguráció: a nyomtató a /dev/fusion/printer szerepen" || ok_run=0
            _check "$log" "FUSION-M5: KLIPPY state=ready version=$KLIPPER_DESCRIBE" "Klipper ready (szoftveres MCU), a rögzített verzió" || ok_run=0
            _check "$log" "FUSION-M5: GCODE ok" "G-kód a Moonrakeren át" || ok_run=0
            _check "$log" "FUSION-M5: M115 FIRMWARE_NAME:Klipper" "M115 válasz a Klippertől" || ok_run=0
            _check "$log" "FUSION-M5: MACRO True" "a kliens-makrók (mainsail.cfg) betöltve" || ok_run=0
            _check "$log" "FUSION-M5: WEB fluidd=fluidd mainsail=Mainsail" "Fluidd (:80) és Mainsail (:81)" || ok_run=0
            _check "$log" "FUSION-M5: PROXY ready ready" "nginx -> Moonraker proxy mindkét felületen" || ok_run=0
            # M6: a pendrive kötetei automatikusan csatolódnak, a fusion felhasználóé, írhatók; kiadás
            _check "$log" "FUSION-M6: MEDIA FUSIONUSB fs=vfat uid=1000 file=FUSION-USB write=ok" "USB FAT32: automatikus csatolás, írható" || ok_run=0
            _check "$log" "FUSION-M6: GIO-SHOWN .*FUSIONUSB" "a pendrive a GTK-fájlválasztókban (Flatpak: PrusaSlicer) eszközként látszik" || ok_run=0
            if command -v mkfs.exfat >/dev/null; then
                _check "$log" "FUSION-M6: MEDIA FUSIONEXF fs=exfat uid=1000 file=- write=ok" "USB exFAT: automatikus csatolás, írható" || ok_run=0; fi
            if command -v mkntfs >/dev/null; then
                _check "$log" "FUSION-M6: MEDIA FUSIONNTFS fs=ntfs3 uid=1000 file=- write=ok" "USB NTFS (ntfs3): automatikus csatolás, írható" || ok_run=0; fi
            _check "$log" "FUSION-M6: EJECT rc=0 left=biztonságosan eltávolítható" "biztonságos eltávolítás (fusion-admin eject, a fusion felhasználóként)" || ok_run=0
            _check "$log" "FUSION-M6: SHELL-MEDIA\s*\$" "a Fusion Shell észleli a leválasztást" || ok_run=0
            # Lemezkezelő: valódi műveletek az üres USB-lemezen (a felhasználóként, a segéden át)
            _check "$log" "FUSION-DISK: LIST found removable=True system=False table=- parts=0" "Lemezkezelő: az üres USB-lemez a listában" || ok_run=0
            _check "$log" "FUSION-DISK: CONFIRM rc=1 .*nem egyezik" "lemezíró művelet csak a lemez nevével" || ok_run=0
            _check "$log" "FUSION-DISK: FORMAT rc=0 table=dos fs=vfat label=PROBA mounted=/run/media/fusion/PROBA write=ok" "formázás (MBR + FAT32), csatolás, írás" || ok_run=0
            _check "$log" "FUSION-DISK: LABEL rc=0 label=UJ NEV mounted=/run/media/fusion/UJ_NEV file=ok" "címke módosítása (csatolt kötet: leválasztás, átnevezés, visszacsatolás)" || ok_run=0
            _check "$log" "FUSION-DISK: DELETE rc=0 parts=0 free=1 media=\s*\$" "partíció törlése" || ok_run=0
            _check "$log" "FUSION-DISK: CREATE rc=0,0 parts=1:ext4:linux,2:exfat:Közös write=ab" "két új partíció (ext4 + exFAT), írhatók" || ok_run=0
            _check "$log" "FUSION-DISK: REFORMAT rc=0 fs=ntfs type=0[xX]0*7" "partíció újraformázása (NTFS, típuskód)" || ok_run=0
            _check "$log" "FUSION-DISK: WIPE rc=0 table=gpt parts=0 media=\s*\$" "a teljes lemez törlése (csatolt kötetekkel), új GPT" || ok_run=0
            _check "$log" "FUSION-DISK: GUARD fusion-disk: a FusionOS saját lemeze .* | fusion-disk: a FusionOS saját lemeze" "a rendszerlemez nem formázható, partíciója nem törölhető" || ok_run=0
            if grep -qa "FUSION-COM-OK" "$out/serial-$cfg.out" 2>/dev/null; then :; else
                warn "hiányzik: a COM3-ra írt sor nem érkezett meg az USB-soros eszközre ($out/serial-$cfg.out)"; ok_run=0
            fi
        else
            _check "$log" "FUSION-M3: LASER none" "soros eszköz nélkül nincs /dev/fusion/laser" || ok_run=0
            _check "$log" "FUSION-M4: WINE wine-$WINE_VERSION" "Wine $WINE_VERSION a képben" || ok_run=0
        fi
        _check "$log" "FUSION-M3: NOGRAB ok" "nincs ModemManager / brltty" || ok_run=0
        # hibajelentés: elkészül, minden szakasz benne van, a titkok maszkolva, a rendszeroldali rész (sudo) is
        _check "$log" "FUSION-REPORT: RUN rc=0 " "hibajelentés: elkészül (fusion-report, a felhasználóként)" || ok_run=0
        _check "$log" "FUSION-REPORT: SECTIONS ok,ok,ok,ok,ok,ok,ok,ok,ok,ok,ok,\s*\$" "hibajelentés: minden szakasz" || ok_run=0
        _check "$log" "FUSION-REPORT: MASK secret=0 email=0 ssid=0 alias=[1-9]" "hibajelentés: jelszó, e-mail, Wi-Fi-név maszkolva" || ok_run=0
        _check "$log" "FUSION-REPORT: SYSTEM update=[1-9][0-9]* pss=1 state=rendszerállapot: running" "hibajelentés: rendszeroldali rész (A/B-állapot, PSS) a segéden át" || ok_run=0
        # Wi-Fi: iwd fut, a ZBook firmware-je és drivere a képben, valódi kapcsolódás virtuális rádiókkal
        _check "$log" "FUSION-WIFI: IWD active" "iwd fut" || ok_run=0
        _check "$log" "FUSION-WIFI: FW /usr/lib/firmware/iwlwifi-7260-17.ucode" "Intel 7260 firmware" || ok_run=0
        _check "$log" "FUSION-WIFI: MODS iwlwifi iwlmvm" "iwlwifi / iwlmvm driver" || ok_run=0
        _check "$log" "FUSION-WIFI: STATE connected" "fusion-wifi connect (virtuális AP, jelszóval)" || ok_run=0
        _check "$log" "FUSION-WIFI: KNOWN FusionTeszt" "a hálózat megjegyezve" || ok_run=0
        _check "$log" "FUSION-WIFI: REPORT ps=[1-9][0-9]* assoc=[1-9][0-9]* iwd=1 link=[1-9]" "hibajelentés Wi-Fi része: energiatakarékosság, kapcsolat, napló" || ok_run=0
        grep -a 'FUSION-M2: \(XORG\|GL\|VULKAN\)\|FUSION-M3: \(LASER\|DB\|BACK\)\|FUSION-M4\|FUSION-M5\|FUSION-M6\|FUSION-FILES\|FUSION-SETTINGS' "$log" | sed 's/^/      /' >&2
        if [ "$ok_run" -eq 1 ]; then
            ok "SIKERES ($RUN_SECS mp)"
        else
            warn "SIKERTELEN — napló: $log"
            grep -a 'FUSION-M[1234]\|fusion-init\|FAILED\|Failed' "$log" | tail -n 20 | sed 's/^/      /' >&2
            fails=$((fails + 1))
        fi
    done

    # mérési bejegyzés (loader/entries): a szöveges konzol — a kiegészített parancssor átjut-e
    FUSION_VARIANT="test" FUSION_BOOT_DEFAULT="fusion-konzol.conf" step_build >/dev/null
    FUSION_VARIANT="test" step_image >/dev/null
    log="$out/qemu-konzol.log"
    step "QEMU EFI boot → mérési bejegyzés: szöveges konzol (fusion.desktop=0)"
    QEMU_EXTRA=(); QEMU_HOTPLUG=0; QEMU_TIMEOUT=600
    _qemu_run konzol std sata "$log" "FUSION-M1: SYSTEM UP"
    if _check "$log" "FUSION-M1: CMDLINE .*fusion.desktop=0" "a bejegyzés parancssora átjutott" \
       && _check "$log" "FUSION-M2: XORG disabled" "Desktop kikapcsolva" \
       && _check "$log" "FUSION-M1: FAILEDCOUNT 0" "nincs hibás szolgáltatás"; then
        ok "SIKERES ($RUN_SECS mp)"
    else
        warn "SIKERTELEN — napló: $log"; fails=$((fails + 1))
    fi

    # két FusionOS-lemez (pl. SSD + pendrive): a második lemezről indul; a slot és a DATA is
    # onnan kell jöjjön (a fusion-init a systemd-boot LoaderDevicePartUUID-ja alapján választ)
    FUSION_VARIANT="test" step_build >/dev/null
    FUSION_VARIANT="test" FUSION_IMAGE_MARKER="masodik" step_image >/dev/null
    mv "$out/fusionos.img" "$out/fusionos-masodik.img"
    FUSION_VARIANT="test" FUSION_IMAGE_MARKER="elso" step_image >/dev/null     # disk0 = "elso"
    log="$out/qemu-ketlemez.log"
    step "QEMU EFI boot → két FusionOS-lemez, indítás a másodikról (SATA 2. port)"
    # shellcheck disable=SC2054  # a vesszők a QEMU-argumentumok részei
    QEMU_EXTRA=(-drive "file=$out/fusionos-masodik.img,format=raw,if=none,id=disk1,snapshot=on"
                -device "ide-hd,drive=disk1,bus=ahci0.1,bootindex=0"); QEMU_HOTPLUG=0; QEMU_TIMEOUT=900
    _qemu_run ketlemez std sata "$log" "FUSION-M1: SYSTEM UP"
    if _check "$log" "FUSION-M1: BOOTDISK sdb MARKER masodik" "a boot-lemez (sdb) slotja és DATA-ja" \
       && _check "$log" "FUSION-M1: SYSTEM UP state=running" "systemd fut, hibátlanul" \
       && _check "$log" "FUSION-M1: FAILEDCOUNT 0" "nincs hibás szolgáltatás"; then
        ok "SIKERES ($RUN_SECS mp)"
    else
        warn "SIKERTELEN — napló: $log"; grep -a 'FUSION-M1\|fusion-init' "$log" | tail -n 12 | sed 's/^/      /' >&2
        fails=$((fails + 1))
    fi
    rm -f "$out/fusionos-masodik.img"

    # M7 — A/B frissítés: egyetlen futás, újraindításokkal, megmaradó lemezzel.
    #   1. A slot (véglegesített) → fusion-update apply „good” → a B slotba
    #   2. B próbaként indul → fusion-boot-check véglegesíti → apply „bad” (sérült rendszerkép) → az A slotba
    #   3–5. A próba: a fusion-init nem tud csatolni → újraindítás; 3 sikertelen próba után
    #   6. magától a B (véglegesített) indul; az A bejegyzés „hibás” (+0-3)
    _test_ab || fails=$((fails + 1))

    # T2 — telepítő pendrive: telepítés egy üres céllemezre (új + a DATA megőrzésével), majd indítás arról
    _test_installer || fails=$((fails + 1))

    # diagnosztika: a boot menü második bejegyzése, alapértelmezettként beállítva
    FUSION_VARIANT="test" FUSION_BOOT_DEFAULT="fusion-diag*" step_build >/dev/null
    FUSION_VARIANT="test" step_image >/dev/null
    log="$out/qemu-diag-usb.log"
    step "QEMU EFI boot → diagnosztika: -vga std, lemez: usb"
    QEMU_EXTRA=(); QEMU_HOTPLUG=0; QEMU_TIMEOUT=600
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
