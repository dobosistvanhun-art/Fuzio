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

# _make_stick <kép>: a partíciókat külön fájlban formázzuk, majd a helyükre másoljuk (root nélkül)
_make_stick() {
    local img=$1 d parts n=0 off
    d=$(mktemp -d)
    rm -f "$img"; truncate -s 200M "$img"
    printf 'label: gpt\nstart=2048, size=120832, type=EBD0A0A2-B9E5-4433-87C0-68B6B72699C7, name=FUSIONUSB\nstart=124928, size=65536, type=EBD0A0A2-B9E5-4433-87C0-68B6B72699C7, name=FUSIONEXF\nstart=192512, size=, type=EBD0A0A2-B9E5-4433-87C0-68B6B72699C7, name=FUSIONNTFS\n' \
        | sfdisk -q "$img" >/dev/null
    truncate -s $((120832 * 512)) "$d/p1"; mkfs.vfat -F 32 -n FUSIONUSB "$d/p1" >/dev/null
    printf 'FUSION-USB\n' > "$d/f.txt"; mcopy -i "$d/p1" "$d/f.txt" ::/fusion-usb.txt
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
        sata) diskdev=(-device "ahci,id=ahci0" -device "ide-hd,drive=disk0,bus=ahci0.0") ;;
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
    _check "$log" "FUSION-AB: APPLY bad rc=0" "a hibás frissítés az A slotba" || ok_run=0
    tries=$(grep -ac "frissítés utáni próba-indítás" "$log")
    [ "$tries" -ge 3 ] || { warn "hiányzik: 3 sikertelen próba-indítás (volt: $tries)"; ok_run=0; }
    _check "$log" "FUSION-AB: BOOT step=final slot=B" "3 próba után magától a B indult" || ok_run=0
    _check "$log" "FUSION-AB:   *A: fusionos-.*-A+0-[0-9]*.efi  \[HIBÁS" "az A bejegyzés hibásként megjelölve" || ok_run=0
    _check "$log" "FUSION-AB: DONE" "a teszt végigfutott" || ok_run=0
    grep -a 'FUSION-AB\|próba-indítás' "$log" | grep -v 'FUSION-AB:   [ 0-9]*%' | sed 's/^/      /' >&2
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

    FUSION_VARIANT="test" step_build
    FUSION_VARIANT="test" step_image

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
            QEMU_HOTPLUG=1; QEMU_TIMEOUT=2400   # a Wine-környezet létrehozása KVM nélkül lassú
        else
            QEMU_EXTRA=(); QEMU_HOTPLUG=0; QEMU_TIMEOUT=600
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
            _check "$log" "FUSION-M6: CTRLALTDEL 1 target=masked" "Ctrl+Alt+Del: Feladatkezelő (a konzolon nem indít újra)" || ok_run=0
            _check "$log" "FUSION-SETTINGS: APPS prog-lightburn,printer,mainsail,files,settings,programs,store,drive,tasks,disks,terminal" "Start menü programlistája (Programkezelő-bejegyzéssel)" || ok_run=0
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
            _check "$log" "FUSION-PROG: DETECT archive win64" "telepítőfájl felismerése" || ok_run=0
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
            if command -v mkfs.exfat >/dev/null; then
                _check "$log" "FUSION-M6: MEDIA FUSIONEXF fs=exfat uid=1000 file=- write=ok" "USB exFAT: automatikus csatolás, írható" || ok_run=0; fi
            if command -v mkntfs >/dev/null; then
                _check "$log" "FUSION-M6: MEDIA FUSIONNTFS fs=ntfs3 uid=1000 file=- write=ok" "USB NTFS (ntfs3): automatikus csatolás, írható" || ok_run=0; fi
            _check "$log" "FUSION-M6: EJECT rc=0 left=biztonságosan eltávolítható" "biztonságos eltávolítás (fusion-admin eject, a fusion felhasználóként)" || ok_run=0
            _check "$log" "FUSION-M6: SHELL-MEDIA\s*\$" "a Fusion Shell észleli a leválasztást" || ok_run=0
            # Lemezkezelő: valódi műveletek az üres USB-lemezen (a felhasználóként, a segéden át)
            _check "$log" "FUSION-DISK: LIST found removable=True system=False table=- parts=0" "Lemezkezelő: az üres USB-lemez a listában" || ok_run=0
            _check "$log" "FUSION-DISK: CONFIRM rc=1 .*nem egyezik" "lemezíró művelet csak a lemez nevével" || ok_run=0
            _check "$log" "FUSION-DISK: FORMAT rc=0 table=dos fs=vfat label=PROBA mounted=/run/media/PROBA write=ok" "formázás (MBR + FAT32), csatolás, írás" || ok_run=0
            _check "$log" "FUSION-DISK: LABEL rc=0 label=UJ NEV mounted=/run/media/UJ_NEV file=ok" "címke módosítása (csatolt kötet: leválasztás, átnevezés, visszacsatolás)" || ok_run=0
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
        _check "$log" "FUSION-REPORT: SECTIONS ok,ok,ok,ok,ok,ok,ok,ok,ok,ok,\s*\$" "hibajelentés: minden szakasz" || ok_run=0
        _check "$log" "FUSION-REPORT: MASK secret=0 email=0 ssid=0 alias=[1-9]" "hibajelentés: jelszó, e-mail, Wi-Fi-név maszkolva" || ok_run=0
        _check "$log" "FUSION-REPORT: SYSTEM update=[1-9][0-9]* pss=1 state=rendszerállapot: running" "hibajelentés: rendszeroldali rész (A/B-állapot, PSS) a segéden át" || ok_run=0
        # Wi-Fi: iwd fut, a ZBook firmware-je és drivere a képben, valódi kapcsolódás virtuális rádiókkal
        _check "$log" "FUSION-WIFI: IWD active" "iwd fut" || ok_run=0
        _check "$log" "FUSION-WIFI: FW /usr/lib/firmware/iwlwifi-7260-17.ucode" "Intel 7260 firmware" || ok_run=0
        _check "$log" "FUSION-WIFI: MODS iwlwifi iwlmvm" "iwlwifi / iwlmvm driver" || ok_run=0
        _check "$log" "FUSION-WIFI: STATE connected" "fusion-wifi connect (virtuális AP, jelszóval)" || ok_run=0
        _check "$log" "FUSION-WIFI: KNOWN FusionTeszt" "a hálózat megjegyezve" || ok_run=0
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
