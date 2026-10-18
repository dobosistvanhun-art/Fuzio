#!/usr/bin/env bash
# =============================================================================
#  Fúzió — Phase 0: Hardware Discovery
#  fusion-hardware-discovery.sh  v0.1.1
#
#  Célgép: HP ZBook 15 G2 (a jelenlegi Linux Mint telepítésen futtatandó)
#
#  Mit csinál:
#    Összegyűjti a Fúzió kernel-, driver-, display-, boot- és eszközdöntéseihez
#    szükséges hardver- és driverinformációkat EGYETLEN szövegfájlba:
#        ./fusion-hardware-report.txt
#    A végén automatikus összefoglalót készít:
#        HARDWARE OK / DRIVER OK / DRIVER MISSING / FIRMWARE MISSING / TECHNICAL WARNING
#
#  Amit NEM csinál:
#    - nem telepít, nem tölt be/ki modult, nem mountol, nem ír konfigurációt;
#    - kizárólag olvas. Az egyetlen írt fájl a jelentés (root futásnál a
#      jelentés tulajdonosa visszaáll a sudo-t hívó felhasználóra).
#
#  Futtatás (ajánlott, teljes jelentés — a grafikus munkamenet termináljából):
#        sudo bash fusion-hardware-discovery.sh
#  Futtatás root nélkül (a root-igényes részek kihagyva, jelölve):
#        bash fusion-hardware-discovery.sh
#
#  Tipp: futtatás előtt csatlakoztasd a GRBL lézert és a Klipper MCU-t USB-n,
#  hogy a soros eszközök is bekerüljenek a jelentésbe.
#
#  Adatvédelem: MAC-címek, sorozatszámok, UUID-k, IP-címek, hosztnév,
#  felhasználónév, Wi-Fi SSID és USB-soros sorozatszámok maszkolva kerülnek
#  a jelentésbe. Küldés előtt egyszer azért érdemes átfutni.
# =============================================================================

set -u
export LC_ALL=C
export LANG=C

SCRIPT_VERSION="0.1.1"
SCRIPT_NAME="$(basename "$0")"
REPORT_NAME="fusion-hardware-report.txt"

# --- kimeneti hely ----------------------------------------------------------
if [ -w "$(pwd)" ]; then
    REPORT="$(pwd)/$REPORT_NAME"
else
    REPORT="${HOME:-/tmp}/$REPORT_NAME"
fi

# --- futási környezet -------------------------------------------------------
IS_ROOT=0
[ "$(id -u)" -eq 0 ] && IS_ROOT=1

TARGET_USER="${SUDO_USER:-${USER:-$(id -un)}}"
TARGET_HOME="$(getent passwd "$TARGET_USER" 2>/dev/null | cut -d: -f6)"
[ -z "$TARGET_HOME" ] && TARGET_HOME="${HOME:-/root}"
TARGET_UID="$(id -u "$TARGET_USER" 2>/dev/null || echo 0)"

HAVE_TIMEOUT=0
command -v timeout >/dev/null 2>&1 && HAVE_TIMEOUT=1

have() { command -v "$1" >/dev/null 2>&1; }

# --- X11 / grafikus környezet (glxinfo, xrandr) -------------------------------
X_DISPLAY="${DISPLAY:-}"
if [ -z "$X_DISPLAY" ] && [ -S /tmp/.X11-unix/X0 ]; then X_DISPLAY=":0"; fi
X_AUTH="${XAUTHORITY:-}"
if [ -z "$X_AUTH" ] || [ ! -r "$X_AUTH" ]; then
    for f in "$TARGET_HOME/.Xauthority" "/run/user/$TARGET_UID/gdm/Xauthority"; do
        [ -r "$f" ] && { X_AUTH="$f"; break; }
    done
fi

# =============================================================================
#  Maszkolás
# =============================================================================
HOST_NAME="$(hostname 2>/dev/null || cat /etc/hostname 2>/dev/null || echo '')"
esc() { printf '%s' "$1" | sed -e 's/[][\.*^$/+?(){}|]/\\&/g'; }

MASK_EXTRA=()
if [ -n "$HOST_NAME" ] && [ "${#HOST_NAME}" -ge 3 ]; then
    MASK_EXTRA+=(-e "s/\\b$(esc "$HOST_NAME")\\b/<HOST>/g")
fi
if [ -n "$TARGET_USER" ] && [ "$TARGET_USER" != "root" ] && [ "${#TARGET_USER}" -ge 3 ]; then
    MASK_EXTRA+=(-e "s#/home/$(esc "$TARGET_USER")#/home/<USER>#g")
    MASK_EXTRA+=(-e "s#/media/$(esc "$TARGET_USER")#/media/<USER>#g")
    MASK_EXTRA+=(-e "s/\\b$(esc "$TARGET_USER")\\b/<USER>/g")
fi

mask() {
    sed -E \
        -e 's/([0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}/XX:XX:XX:XX:XX:XX/g' \
        -e 's/[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}/<UUID>/g' \
        -e 's/(UUID=)[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}/\1<UUID>/g' \
        -e 's/((Serial Number|SerialNumber|Serial No|serial_number|Asset Tag|Service Tag|LU WWN Device Id|Chassis Serial)[[:space:]]*[:=][[:space:]]*).*/\1<MASZKOLVA>/I' \
        -e 's/(usb-[^ /]*_)[A-Za-z0-9]*[0-9][A-Za-z0-9]*(-if[0-9]+)/\1<SERIAL>\2/g' \
        -e 's/(ssid[[:space:]]+).*/\1<MASZKOLVA>/I' \
        "${MASK_EXTRA[@]}"
}

# hálózati részekhez: IP-címek maszkolása is
mask_net() {
    mask | sed -E \
        -e 's/\b([0-9]{1,3}\.){3}[0-9]{1,3}(\/[0-9]{1,2})?\b/x.x.x.x\2/g' \
        -e 's/\b[0-9a-fA-F]{1,4}(:[0-9a-fA-F]{0,4}){2,7}(\/[0-9]{1,3})?/<IPv6>\2/g'
}

# =============================================================================
#  Jelentésíró segédfüggvények
# =============================================================================
SEC_NO=0
SEP="================================================================================"

out() { printf '%s\n' "$*" | mask >> "$REPORT"; }

section() {
    SEC_NO=$((SEC_NO + 1))
    printf '\n%s\n=== [%02d] %s ===\n%s\n' "$SEP" "$SEC_NO" "$1" "$SEP" >> "$REPORT"
    printf '  [%02d] %s\n' "$SEC_NO" "$1"
}

_exec() {
    if [ "$HAVE_TIMEOUT" -eq 1 ]; then timeout 30 "$@" 2>&1; else "$@" 2>&1; fi
}

# run <parancs...>  — futtatás normál jogosultsággal, maszkolt kimenet
run() {
    printf '\n$ %s\n' "$*" >> "$REPORT"
    if ! have "$1"; then
        printf '[NEM ELÉRHETŐ: a(z) "%s" parancs nincs telepítve]\n' "$1" >> "$REPORT"
        return 0
    fi
    _exec "$@" | mask >> "$REPORT"
}

run_net() {
    printf '\n$ %s\n' "$*" >> "$REPORT"
    if ! have "$1"; then
        printf '[NEM ELÉRHETŐ: a(z) "%s" parancs nincs telepítve]\n' "$1" >> "$REPORT"
        return 0
    fi
    _exec "$@" | mask_net >> "$REPORT"
}

# run_root <parancs...>  — csak root futásnál, csak olvasó műveletre használva
run_root() {
    printf '\n$ sudo %s\n' "$*" >> "$REPORT"
    if [ "$IS_ROOT" -ne 1 ]; then
        printf '[ROOT SZÜKSÉGES — kihagyva. Teljes jelentéshez: sudo bash %s]\n' "$SCRIPT_NAME" >> "$REPORT"
        return 0
    fi
    if ! have "$1"; then
        printf '[NEM ELÉRHETŐ: a(z) "%s" parancs nincs telepítve]\n' "$1" >> "$REPORT"
        return 0
    fi
    printf '[root jogosultsággal, csak olvasás]\n' >> "$REPORT"
    _exec "$@" | mask >> "$REPORT"
}

# run_x <parancs...>  — a grafikus munkamenet felhasználójaként (X11 hozzáférés)
run_x() {
    local label="$*"
    printf '\n$ %s   (DISPLAY=%s)\n' "$label" "${X_DISPLAY:-nincs}" >> "$REPORT"
    if ! have "$1"; then
        printf '[NEM ELÉRHETŐ: a(z) "%s" parancs nincs telepítve]\n' "$1" >> "$REPORT"
        return 0
    fi
    if [ -z "$X_DISPLAY" ]; then
        printf '[NINCS GRAFIKUS KIJELZŐ — a scriptet a grafikus munkamenet termináljából futtasd]\n' >> "$REPORT"
        return 0
    fi
    x_exec "$@" 2>&1 | mask >> "$REPORT"
}

x_exec() {
    if [ "$IS_ROOT" -eq 1 ] && [ -n "${SUDO_USER:-}" ] && have sudo; then
        sudo -u "$SUDO_USER" env DISPLAY="$X_DISPLAY" XAUTHORITY="$X_AUTH" XDG_RUNTIME_DIR="/run/user/$TARGET_UID" "$@"
    else
        env DISPLAY="$X_DISPLAY" ${X_AUTH:+XAUTHORITY="$X_AUTH"} "$@"
    fi
}

show_file() {
    printf '\n$ cat %s\n' "$1" >> "$REPORT"
    if [ -r "$1" ]; then mask < "$1" >> "$REPORT"; else printf '[NEM OLVASHATÓ vagy nem létezik]\n' >> "$REPORT"; fi
}

sysval() { [ -r "$1" ] && tr -d '\n' < "$1" 2>/dev/null; }

version_ge() { [ "$(printf '%s\n%s\n' "$2" "$1" | sort -V | head -n1)" = "$2" ]; }

# =============================================================================
#  Összefoglaló gyűjtők
# =============================================================================
S_HW=(); S_DRV_OK=(); S_DRV_MISS=(); S_FW_MISS=(); S_WARN=(); S_INFO=()
hw()   { S_HW+=("$*"); }
dok()  { S_DRV_OK+=("$*"); }
dmis() { S_DRV_MISS+=("$*"); }
fwm()  { S_FW_MISS+=("$*"); }
warn() { S_WARN+=("$*"); }
info() { S_INFO+=("$*"); }

# =============================================================================
#  Nyers adatok az elemzéshez (nem kerülnek így a jelentésbe)
# =============================================================================
KLOG=""
if have journalctl; then KLOG="$(journalctl -k -b 0 --no-pager 2>/dev/null)"; fi
if [ -z "$KLOG" ] && have dmesg; then KLOG="$(dmesg 2>/dev/null)"; fi
LSPCI_K="$(lspci -nnk 2>/dev/null)"
LSMOD="$(lsmod 2>/dev/null)"
LSUSB="$(lsusb 2>/dev/null)"

# =============================================================================
#  Jelentés
# =============================================================================
: > "$REPORT" || { echo "HIBA: nem írható: $REPORT" >&2; exit 1; }

echo "Fúzió Phase 0 — Hardware Discovery v$SCRIPT_VERSION"
echo "Jelentés: $REPORT"
[ "$IS_ROOT" -ne 1 ] && echo "FIGYELEM: root nélkül fut — a root-igényes részek kimaradnak. Teljes jelentés: sudo bash $SCRIPT_NAME"
echo

{
    echo "$SEP"
    echo " Fúzió — Hardware Discovery Report"
    echo "$SEP"
    echo " Script verzió : $SCRIPT_VERSION"
    echo " Időpont       : $(date '+%Y-%m-%d %H:%M:%S %z')"
    echo " Futási mód    : $([ "$IS_ROOT" -eq 1 ] && echo 'root (sudo) — teljes, csak olvasó' || echo 'normál felhasználó — root-igényes részek kihagyva')"
    echo " Grafikus kijelző: ${X_DISPLAY:-nincs}"
    echo " Maszkolva     : MAC, sorozatszám, UUID, IP, hosztnév, felhasználónév, SSID"
    echo " Az automatikus összefoglaló a jelentés VÉGÉN található."
    echo "$SEP"
} | mask >> "$REPORT"

# ---------------------------------------------------------------------------
section "Rendszer: kernel, disztribúció, parancssor"
run uname -a
show_file /etc/os-release
show_file /proc/cmdline
printf '\n$ cat /proc/sys/kernel/tainted\n%s\n' "$(sysval /proc/sys/kernel/tainted)" >> "$REPORT"
run uptime

# ---------------------------------------------------------------------------
section "Firmware / BIOS / UEFI / Secure Boot"
{
    echo
    echo "--- /sys/class/dmi/id (root nélkül olvasható mezők) ---"
    for k in sys_vendor product_name product_version board_vendor board_name bios_vendor bios_version bios_date; do
        printf '%-16s: %s\n' "$k" "$(sysval /sys/class/dmi/id/$k)"
    done
    echo
    if [ -d /sys/firmware/efi ]; then
        echo "Boot mód       : UEFI"
        echo "EFI bitszélesség: $(sysval /sys/firmware/efi/fw_platform_size)"
    else
        echo "Boot mód       : Legacy BIOS / CSM"
    fi
} | mask >> "$REPORT"
SB_STATE="ismeretlen"
if have mokutil; then
    run mokutil --sb-state
    mokutil --sb-state 2>/dev/null | grep -qi 'enabled' && SB_STATE="enabled"
    mokutil --sb-state 2>/dev/null | grep -qi 'disabled' && SB_STATE="disabled"
fi
SB_VAR=/sys/firmware/efi/efivars/SecureBoot-8be4df61-93ca-11d2-aa0d-00e098032b8c
if [ "$SB_STATE" = "ismeretlen" ] && [ -r "$SB_VAR" ]; then
    v="$(od -An -t u1 -j4 -N1 "$SB_VAR" 2>/dev/null | tr -d ' ')"
    [ "$v" = "1" ] && SB_STATE="enabled"
    [ "$v" = "0" ] && SB_STATE="disabled"
fi
printf '\nSecure Boot állapot (összesítve): %s\n' "$SB_STATE" >> "$REPORT"
run_root dmidecode

# ---------------------------------------------------------------------------
section "CPU és memória"
run lscpu
printf '\n$ grep microcode /proc/cpuinfo (első sor)\n%s\n' "$(grep -m1 microcode /proc/cpuinfo 2>/dev/null)" >> "$REPORT"
run free -h
run_root dmidecode -t memory

# ---------------------------------------------------------------------------
section "PCI eszközök és kernel driverek (lspci -nnk)"
run lspci -nnk

# ---------------------------------------------------------------------------
section "Betöltött kernelmodulok (lsmod)"
run lsmod

# ---------------------------------------------------------------------------
section "GPU-k: NVIDIA + Intel"
{
    echo
    echo "--- Grafikus PCI eszközök ---"
    printf '%s\n' "$LSPCI_K" | grep -A3 -E '\[03(00|02|80)\]'
    echo
    echo "--- Grafikus kernelmodulok ---"
    printf '%s\n' "$LSMOD" | grep -E '^(nvidia|nvidia_drm|nvidia_modeset|nvidia_uvm|nouveau|i915|drm_kms_helper|drm) ' || echo "(nincs találat)"
} | mask >> "$REPORT"
show_file /proc/driver/nvidia/version
run modinfo -F version nvidia
run nvidia-smi
run nvidia-smi --query-gpu=name,driver_version,vbios_version,pstate,temperature.gpu,memory.total --format=csv
run prime-select query
{
    echo
    echo '$ dpkg -l (nvidia / mesa csomagok)'
    if have dpkg-query; then
        dpkg-query -W -f='${db:Status-Abbrev} ${Package} ${Version}\n' 2>/dev/null \
            | grep -E '^ii .*(nvidia|libnvidia|mesa|xserver-xorg-video|libgl1|vulkan)' || echo "(nincs találat)"
    else
        echo "[NEM ELÉRHETŐ: dpkg-query]"
    fi
} | mask >> "$REPORT"

# ---------------------------------------------------------------------------
section "Kijelzők, X11/Wayland munkamenet, OpenGL/Vulkan"
{
    echo
    echo "--- DRM csatlakozók (melyik GPU hajtja melyik kimenetet) ---"
    for c in /sys/class/drm/card*-*; do
        [ -e "$c" ] || continue
        name="$(basename "$c")"
        card="${name%%-*}"
        drv="$(basename "$(readlink -f /sys/class/drm/$card/device/driver 2>/dev/null)" 2>/dev/null)"
        printf '%-28s status=%-12s enabled=%-9s driver=%s\n' \
            "$name" "$(sysval "$c/status")" "$(sysval "$c/enabled")" "${drv:-?}"
    done
    echo
    echo "--- Munkamenetek (loginctl) ---"
    if have loginctl; then
        for s in $(loginctl list-sessions --no-legend 2>/dev/null | awk '{print $1}'); do
            loginctl show-session "$s" -p Name -p Type -p Class -p Desktop -p Active 2>/dev/null | tr '\n' ' '
            echo
        done
    else
        echo "[NEM ELÉRHETŐ: loginctl]"
    fi
} | mask >> "$REPORT"
run_x xrandr --query
run_x xrandr --listproviders
run_x glxinfo -B
printf '\n--- PRIME render offload teszt (csak hibrid módban releváns) ---\n' >> "$REPORT"
run_x env __NV_PRIME_RENDER_OFFLOAD=1 __GLX_VENDOR_LIBRARY_NAME=nvidia glxinfo -B
run_x vulkaninfo --summary

GLX_RENDERER=""
if have glxinfo && [ -n "$X_DISPLAY" ]; then
    GLX_RENDERER="$(x_exec glxinfo -B 2>/dev/null | grep -m1 'OpenGL renderer string' | cut -d: -f2- | sed 's/^ *//')"
fi

# ---------------------------------------------------------------------------
section "Hang: ALSA kártyák és kodekek"
show_file /proc/asound/cards
{
    for codec in /proc/asound/card*/codec#*; do
        [ -r "$codec" ] || continue
        echo
        echo "--- $codec ---"
        grep -E '^(Codec|Address|Vendor Id|Subsystem Id|Revision Id|Default PCM|Modem Function|AFG Function)' "$codec"
    done
} | mask >> "$REPORT"
run aplay -l
if have pactl; then
    printf '\n$ pactl info (a munkamenet felhasználójaként)\n' >> "$REPORT"
    if [ "$IS_ROOT" -eq 1 ] && [ -n "${SUDO_USER:-}" ]; then
        sudo -u "$SUDO_USER" env XDG_RUNTIME_DIR="/run/user/$TARGET_UID" pactl info 2>&1 | mask >> "$REPORT"
    else
        pactl info 2>&1 | mask >> "$REPORT"
    fi
fi

# ---------------------------------------------------------------------------
section "Hálózat: interfészek, Ethernet, Wi-Fi"
run_net ip -br link
run_net ip -br addr
{
    echo
    echo "--- Interfészek és driverek ---"
    for n in /sys/class/net/*; do
        i="$(basename "$n")"; [ "$i" = "lo" ] && continue
        drv="$(basename "$(readlink -f "$n/device/driver" 2>/dev/null)" 2>/dev/null)"
        wl="nem"; [ -d "$n/wireless" ] && wl="igen"
        printf '%-16s driver=%-12s wireless=%s\n' "$i" "${drv:--}" "$wl"
    done
    echo
    echo "--- Hálózati PCI eszközök ---"
    printf '%s\n' "$LSPCI_K" | grep -A3 -E '\[02(00|80)\]'
} | mask_net >> "$REPORT"
run_net nmcli -f DEVICE,TYPE,STATE device
run_net nmcli radio
run_net iw dev
run rfkill list
{
    echo
    echo "--- iwlwifi kernelüzenetek ---"
    printf '%s\n' "$KLOG" | grep -i 'iwlwifi' | tail -n 25
} | mask >> "$REPORT"

# ---------------------------------------------------------------------------
section "Bluetooth"
{
    echo
    echo "--- USB Bluetooth eszközök ---"
    printf '%s\n' "$LSUSB" | grep -iE 'bluetooth|8087:' || echo "(nincs találat)"
    echo
    echo "--- /sys/class/bluetooth ---"
    ls /sys/class/bluetooth 2>/dev/null || echo "(nincs Bluetooth adapter regisztrálva)"
    echo
    echo "--- btusb / bluetooth modul ---"
    printf '%s\n' "$LSMOD" | grep -E '^(btusb|btintel|bluetooth) ' || echo "(nincs betöltve)"
} | mask >> "$REPORT"
if have bluetoothctl; then
    printf '\n$ bluetoothctl show (név/alias maszkolva)\n' >> "$REPORT"
    _exec bluetoothctl show < /dev/null | sed -E 's/((Name|Alias):).*/\1 <MASZKOLVA>/' | mask >> "$REPORT"
fi

# ---------------------------------------------------------------------------
section "USB eszközök"
run lsusb
run lsusb -t

# ---------------------------------------------------------------------------
section "Tárolók: SATA / SSD / partíciók"
run lsblk -d -o NAME,TYPE,SIZE,MODEL,REV,ROTA,TRAN,DISC-GRAN
run lsblk -o NAME,SIZE,TYPE,FSTYPE,MOUNTPOINTS
run df -hT -x tmpfs -x devtmpfs -x squashfs
{
    echo
    echo "--- SATA/AHCI kernelüzenetek ---"
    printf '%s\n' "$KLOG" | grep -iE 'SATA link|ahci|ata[0-9]+: .*(ATA-|configured)' | tail -n 20
} | mask >> "$REPORT"
for d in /sys/block/sd* /sys/block/nvme*; do
    [ -e "$d" ] || continue
    run_root smartctl -i -H "/dev/$(basename "$d")"
done

# ---------------------------------------------------------------------------
section "Soros eszközök: /dev/serial/by-id, ttyUSB, ttyACM"
run ls -l /dev/serial/by-id/
run ls -l /dev/serial/by-path/
{
    echo
    echo '$ ls -l /dev/ttyUSB* /dev/ttyACM*'
    if compgen -G '/dev/ttyUSB*' >/dev/null || compgen -G '/dev/ttyACM*' >/dev/null; then
        ls -l /dev/ttyUSB* /dev/ttyACM* 2>/dev/null
    else
        echo "(nincs csatlakoztatott USB-soros eszköz)"
    fi
    for t in /dev/ttyUSB* /dev/ttyACM*; do
        [ -e "$t" ] || continue
        echo
        echo "--- udevadm: $t ---"
        udevadm info -q property -n "$t" 2>/dev/null \
            | grep -E '^(DEVNAME|ID_VENDOR_ID|ID_MODEL_ID|ID_VENDOR=|ID_MODEL=|ID_USB_DRIVER|ID_BUS|ID_USB_INTERFACE_NUM)'
    done
    echo
    echo "--- USB-soros driverek ---"
    printf '%s\n' "$LSMOD" | grep -E '^(ch341|cp210x|ftdi_sio|pl2303|cdc_acm|usbserial) ' || echo "(nincs betöltve)"
    echo
    echo "--- Jogosultság: a felhasználó csoportjai ---"
    id "$TARGET_USER" 2>/dev/null
    echo
    echo "--- Soros portot lefoglaló szolgáltatások ---"
    if have systemctl; then
        printf 'ModemManager : %s\n' "$(systemctl is-active ModemManager 2>/dev/null)"
        printf 'brltty       : %s\n' "$(systemctl is-active brltty 2>/dev/null)"
        printf 'brltty-udev  : %s\n' "$(systemctl is-active brltty-udev 2>/dev/null)"
    fi
    ls /usr/lib/udev/rules.d/*brltty* /lib/udev/rules.d/*brltty* 2>/dev/null
} | mask >> "$REPORT"

# ---------------------------------------------------------------------------
section "ACPI: akkumulátor, tápegység, hőmérséklet"
{
    for b in /sys/class/power_supply/*; do
        [ -e "$b" ] || continue
        echo
        echo "--- $(basename "$b") ---"
        for k in type manufacturer model_name technology status capacity cycle_count \
                 energy_full energy_full_design energy_now charge_full charge_full_design online; do
            [ -r "$b/$k" ] && printf '%-20s: %s\n' "$k" "$(sysval "$b/$k")"
        done
    done
    echo
    echo "--- Thermal zónák ---"
    for z in /sys/class/thermal/thermal_zone*; do
        [ -e "$z" ] || continue
        t="$(sysval "$z/temp")"
        [ -n "$t" ] && printf '%-18s %-14s %s °C\n' "$(basename "$z")" "$(sysval "$z/type")" "$((t / 1000))"
    done
} | mask >> "$REPORT"
run sensors

# ---------------------------------------------------------------------------
section "Firmware: betöltött és hiányzó firmware-ek (kernelnapló)"
{
    echo
    echo "--- Firmware-rel kapcsolatos kernelüzenetek ---"
    printf '%s\n' "$KLOG" | grep -iE 'firmware|microcode|fw version|DMC' | grep -viE 'efi: |ACPI: .*table' | tail -n 60
} | mask >> "$REPORT"

# ---------------------------------------------------------------------------
section "Kernel hibák és figyelmeztetések (aktuális boot)"
if have journalctl; then
    run journalctl -k -b 0 -p err --no-pager
else
    printf '[NEM ELÉRHETŐ: journalctl]\n' >> "$REPORT"
fi

# ---------------------------------------------------------------------------
section "Kernelnapló: journalctl -k (aktuális boot)"
run journalctl -k -b 0 --no-pager

# ---------------------------------------------------------------------------
section "Kernel ring buffer: dmesg"
if [ "$IS_ROOT" -ne 1 ] && [ "$(sysval /proc/sys/kernel/dmesg_restrict)" = "1" ]; then
    printf '\n$ sudo dmesg\n[ROOT SZÜKSÉGES — dmesg_restrict=1, kihagyva. A kernelnapló a journalctl -k szakaszban szerepel.]\n' >> "$REPORT"
else
    run dmesg
fi

# =============================================================================
#  Automatikus elemzés
# =============================================================================
echo
echo "Összefoglaló készítése..."

# --- CPU / RAM ---------------------------------------------------------------
CPU_MODEL="$(grep -m1 'model name' /proc/cpuinfo 2>/dev/null | cut -d: -f2- | sed 's/^ *//')"
[ -n "$CPU_MODEL" ] && hw "CPU: $CPU_MODEL ($(nproc 2>/dev/null) szál)"
MEM_KB="$(awk '/MemTotal/ {print $2}' /proc/meminfo 2>/dev/null)"
[ -n "$MEM_KB" ] && hw "RAM: $((MEM_KB / 1024 / 1024 + 1)) GB körül ($((MEM_KB / 1024)) MiB látható)"
printf '%s\n' "$KLOG" | grep -qiE 'microcode: .*(updated|revision)' || info "Mikrokód-frissítés nem látható a kernelnaplóban (intel-microcode csomag?)"

# --- PCI eszközök és driverek ------------------------------------------------
HAS_NVIDIA=0; HAS_INTEL_GPU=0; NVIDIA_DRV=""; HAS_WIFI=0; HAS_ETH=0; HAS_AUDIO=0
while IFS=$'\t' read -r slot cls desc drv mods; do
    [ -z "$slot" ] && continue
    short="$(printf '%s' "$desc" | sed -E 's/^[^:]*: //; s/ \(rev [0-9a-f]+\)//')"
    key=0
    case "$cls" in
        0300|0302|0380)
            key=1
            if printf '%s' "$desc" | grep -q '\[10de:'; then HAS_NVIDIA=1; NVIDIA_DRV="$drv"; hw "dGPU: $short"
            elif printf '%s' "$desc" | grep -q '\[8086:'; then HAS_INTEL_GPU=1; hw "iGPU: $short"
            else hw "GPU: $short"; fi ;;
        0403) key=1; HAS_AUDIO=1; hw "Hang: $short" ;;
        0200) key=1; HAS_ETH=1; hw "Ethernet: $short" ;;
        0280) key=1; HAS_WIFI=1; hw "Wi-Fi: $short" ;;
        0c03) key=1; hw "USB vezérlő: $short" ;;
        0106|0108|0104|0101) key=1; hw "Tároló vezérlő: $short" ;;
    esac
    if [ -n "$drv" ]; then
        [ "$key" -eq 1 ] && dok "$short → $drv"
    elif [ -n "$mods" ]; then
        dmis "$slot $short (elérhető modul: $mods, de nincs betöltve/hozzárendelve)"
    elif [ "$key" -eq 1 ]; then
        dmis "$slot $short (nincs kernel driver)"
    fi
done < <(printf '%s\n' "$LSPCI_K" | awk '
    /^[0-9a-f]/ {
        if (slot != "") print slot "\t" cls "\t" desc "\t" drv "\t" mods
        slot = $1; line = $0; sub(/^[^ ]+ /, "", line)
        cls = ""
        if (match(line, /\[[0-9a-f][0-9a-f][0-9a-f][0-9a-f]\]/)) cls = substr(line, RSTART + 1, 4)
        desc = line; drv = ""; mods = ""; next
    }
    /Kernel driver in use:/ { drv = $NF; next }
    /Kernel modules:/ { m = $0; sub(/.*Kernel modules: */, "", m); mods = m; next }
    END { if (slot != "") print slot "\t" cls "\t" desc "\t" drv "\t" mods }')

[ "$HAS_NVIDIA" -eq 0 ] && warn "NVIDIA GPU nem látható a PCI buszon (BIOS-ban letiltva vagy lekapcsolt állapotban?)"
[ "$HAS_WIFI" -eq 0 ] && warn "Wi-Fi eszköz nem található a PCI buszon"
[ "$HAS_ETH" -eq 0 ] && warn "Ethernet vezérlő nem található"
[ "$HAS_AUDIO" -eq 0 ] && warn "HD Audio vezérlő nem található"

# Hibrid / diszkrét mód
if [ "$HAS_NVIDIA" -eq 1 ] && [ "$HAS_INTEL_GPU" -eq 1 ]; then
    info "Mindkét GPU látható → a BIOS Hybrid Graphics valószínűleg BE van kapcsolva"
elif [ "$HAS_NVIDIA" -eq 1 ] && [ "$HAS_INTEL_GPU" -eq 0 ]; then
    info "Csak az NVIDIA GPU látható → a BIOS Hybrid Graphics valószínűleg KI van kapcsolva (diszkrét mód)"
fi
EDP_DRV=""
for c in /sys/class/drm/card*-eDP-*; do
    [ -e "$c" ] || continue
    card="$(basename "$c")"; card="${card%%-*}"
    EDP_DRV="$(basename "$(readlink -f /sys/class/drm/$card/device/driver 2>/dev/null)" 2>/dev/null)"
done
[ -n "$EDP_DRV" ] && info "A belső panelt (eDP) a(z) '$EDP_DRV' driver kezeli"

# NVIDIA driver részletek
NV_VER=""
if [ -r /proc/driver/nvidia/version ]; then
    NV_VER="$(grep -oE '[0-9]{3}\.[0-9]+(\.[0-9]+)?' /proc/driver/nvidia/version | head -n1)"
fi
if [ "$HAS_NVIDIA" -eq 1 ]; then
    case "$NVIDIA_DRV" in
        nvidia)  dok "NVIDIA zárt driver aktív, verzió: ${NV_VER:-ismeretlen}" ;;
        nouveau) info "NVIDIA GPU a nouveau driverrel fut (nyílt forrású; Kepleren kézi reclocking nélkül lassú)" ;;
        "")      dmis "NVIDIA GPU-hoz nincs driver hozzárendelve" ;;
    esac
fi
if printf '%s\n' "$LSMOD" | grep -q '^nvidia ' && printf '%s\n' "$LSMOD" | grep -q '^nouveau '; then
    warn "Az nvidia és a nouveau modul egyszerre van betöltve — driverütközés"
fi
KVER="$(uname -r | cut -d- -f1)"
if [ -n "$NV_VER" ] && printf '%s' "$NV_VER" | grep -q '^470\.'; then
    if version_ge "$KVER" "6.10"; then
        warn "NVIDIA $NV_VER + kernel $KVER: a 470-es ág hivatalosan nem támogatja ezt a kernelt, közösségi foltokkal fut — a kernel baseline-nál kritikus"
    else
        info "NVIDIA $NV_VER + kernel $KVER: folt nélkül támogatott kombináció"
    fi
    [ "$NV_VER" != "470.256.02" ] && info "Az utolsó 470-es kiadás a 470.256.02; a telepített: $NV_VER"
fi
if have nvidia-smi && [ "$NVIDIA_DRV" = "nvidia" ]; then
    nvidia-smi >/dev/null 2>&1 || warn "nvidia-smi hibával fut — a driver és a userspace könyvtárak eltérhetnek"
fi

# OpenGL renderer
if [ -n "$GLX_RENDERER" ]; then
    info "Aktív OpenGL renderer: $GLX_RENDERER"
    printf '%s' "$GLX_RENDERER" | grep -qiE 'llvmpipe|softpipe|swrast' && warn "Szoftveres OpenGL renderelés ($GLX_RENDERER) — nincs GPU-gyorsítás"
elif [ -z "$X_DISPLAY" ]; then
    warn "Nincs grafikus kijelző — az OpenGL/xrandr adatok hiányoznak; futtasd a grafikus munkamenet termináljából"
elif ! have glxinfo; then
    info "glxinfo nincs telepítve (mesa-utils csomag) — az OpenGL adatok hiányoznak"
fi
have vulkaninfo || info "vulkaninfo nincs telepítve (vulkan-tools) — a Vulkan szint (DXVK-hoz fontos) nem mérhető"

# Munkamenet típusa
if have loginctl; then
    SESS_TYPES="$(for s in $(loginctl list-sessions --no-legend 2>/dev/null | awk '{print $1}'); do loginctl show-session "$s" -p Type --value 2>/dev/null; done | sort -u | tr '\n' ' ')"
    [ -n "$SESS_TYPES" ] && info "Munkamenet-típus(ok): $SESS_TYPES"
fi

# --- Boot / UEFI / Secure Boot -----------------------------------------------
if [ -d /sys/firmware/efi ]; then
    hw "Boot: UEFI mód ($(sysval /sys/firmware/efi/fw_platform_size)-bit)"
else
    warn "A rendszer Legacy BIOS/CSM módban bootolt — a Fúzió UEFI-t céloz"
fi
case "$SB_STATE" in
    enabled)
        if [ -n "$NV_VER" ]; then
            warn "Secure Boot BE + zárt NVIDIA modul: saját kernelnél modulaláírás (MOK) kell, vagy Secure Boot kikapcsolás"
        else
            info "Secure Boot bekapcsolva"
        fi ;;
    disabled) info "Secure Boot kikapcsolva" ;;
    *) info "Secure Boot állapota nem állapítható meg" ;;
esac
BIOS_VER="$(sysval /sys/class/dmi/id/bios_version)"; BIOS_DATE="$(sysval /sys/class/dmi/id/bios_date)"
PRODUCT="$(sysval /sys/class/dmi/id/product_name)"
[ -n "$PRODUCT" ] && hw "Gép: $PRODUCT"
[ -n "$BIOS_VER" ] && info "BIOS: $BIOS_VER ($BIOS_DATE) — vesd össze a HP legfrissebb ZBook 15 G2 BIOS-ával"
printf '%s' "$PRODUCT" | grep -qi 'ZBook 15 G2' || warn "A gép nem ZBook 15 G2-ként azonosítja magát ('$PRODUCT')"

# Kernel taint
TAINT="$(sysval /proc/sys/kernel/tainted)"
if [ -n "$TAINT" ] && [ "$TAINT" != "0" ]; then
    flags=""
    [ $((TAINT & 1)) -ne 0 ] && flags="$flags P(zárt modul)"
    [ $((TAINT & 512)) -ne 0 ] && flags="$flags W(kernel warning)"
    [ $((TAINT & 4096)) -ne 0 ] && flags="$flags O(fán kívüli modul)"
    [ $((TAINT & 8192)) -ne 0 ] && flags="$flags E(aláíratlan modul)"
    info "Kernel taint=$TAINT:$flags"
    [ $((TAINT & 512)) -ne 0 ] && warn "A kernel WARNING-ot rögzített ebben a bootban — lásd a hibák szakaszt"
fi

# --- Hálózat / Bluetooth -----------------------------------------------------
if printf '%s\n' "$LSUSB" | grep -qiE 'bluetooth|8087:07dc|8087:0a2a'; then
    hw "Bluetooth: $(printf '%s\n' "$LSUSB" | grep -iE 'bluetooth|8087:07dc|8087:0a2a' | head -n1 | sed -E 's/^Bus [0-9]+ Device [0-9]+: ID //')"
    if printf '%s\n' "$LSMOD" | grep -q '^btusb '; then dok "Bluetooth → btusb"; else dmis "Bluetooth eszköz látható, de a btusb modul nincs betöltve"; fi
else
    info "USB Bluetooth adapter nem látható (rfkill-lel tiltva vagy hiányzik)"
fi
if have rfkill; then
    rfkill list 2>/dev/null | grep -q 'Hard blocked: yes' && warn "Rádió hardveresen tiltva (Wi-Fi kapcsoló / BIOS)"
fi

# --- Tárolók ----------------------------------------------------------------
if have lsblk; then
    lsb_field() { printf '%s' "$2" | sed -nE "s/.*\\b$1=\"([^\"]*)\".*/\\1/p"; }
    while IFS= read -r line; do
        [ -z "$line" ] && continue
        name="$(lsb_field NAME "$line")"; size="$(lsb_field SIZE "$line")"
        model="$(lsb_field MODEL "$line")"; tran="$(lsb_field TRAN "$line")"; rota="$(lsb_field ROTA "$line")"
        kind="SSD"; [ "$rota" = "1" ] && kind="HDD"
        hw "Tároló: /dev/$name $size $kind ${tran:-?} ${model:-}"
    done < <(lsblk -d -n -P -o NAME,SIZE,MODEL,TRAN,ROTA -e 7,11 2>/dev/null)
fi
printf '%s\n' "$KLOG" | grep -qE 'SATA link up 1\.5 Gbps' && warn "Van 1.5 Gbps-re csatlakozott SATA link — kábel/port/energiatakarékossági beállítás?"

# --- Hang --------------------------------------------------------------------
if [ -r /proc/asound/cards ] && grep -q '\[' /proc/asound/cards; then
    for codec in /proc/asound/card*/codec#*; do
        [ -r "$codec" ] || continue
        cname="$(grep -m1 '^Codec:' "$codec" | cut -d: -f2- | sed 's/^ *//')"
        [ -n "$cname" ] && hw "Hangkodek: $cname"
    done
else
    warn "Nincs ALSA hangkártya regisztrálva"
fi

# --- USB-soros / Klipper / GRBL ------------------------------------------------
SERIAL_COUNT=0
for t in /dev/ttyUSB* /dev/ttyACM*; do [ -e "$t" ] && SERIAL_COUNT=$((SERIAL_COUNT + 1)); done
if [ "$SERIAL_COUNT" -gt 0 ]; then
    hw "USB-soros eszközök: $SERIAL_COUNT db"
    for t in /dev/ttyUSB* /dev/ttyACM*; do
        [ -e "$t" ] || continue
        d="$(udevadm info -q property -n "$t" 2>/dev/null | awk -F= '/^ID_USB_DRIVER=/{print $2}')"
        [ -n "$d" ] && dok "$(basename "$t") → $d"
    done
else
    info "Nincs csatlakoztatott USB-soros eszköz — csatlakoztasd a GRBL lézert és a Klipper MCU-t, majd futtasd újra"
fi
if [ "$TARGET_USER" != "root" ] && ! id -nG "$TARGET_USER" 2>/dev/null | grep -qw dialout; then
    warn "A(z) '$TARGET_USER' felhasználó nincs a 'dialout' csoportban — soros portok (GRBL/Klipper) root nélkül nem érhetők el"
fi
if have systemctl && [ "$(systemctl is-active ModemManager 2>/dev/null)" = "active" ]; then
    warn "A ModemManager fut — lefoglalhatja a ttyACM eszközöket (Klipper MCU / GRBL); a Fúzióban ezt kezelni kell"
fi
if ls /usr/lib/udev/rules.d/*brltty* /lib/udev/rules.d/*brltty* >/dev/null 2>&1; then
    warn "A brltty udev szabályai telepítve vannak — ismert, hogy lefoglalja a CH340 alapú USB-soros eszközöket (sok GRBL lézer ilyen)"
fi

# --- Akkumulátor és hőmérséklet ---------------------------------------------
for b in /sys/class/power_supply/BAT*; do
    [ -e "$b" ] || continue
    full="$(sysval "$b/energy_full")"; design="$(sysval "$b/energy_full_design")"
    [ -z "$full" ] && { full="$(sysval "$b/charge_full")"; design="$(sysval "$b/charge_full_design")"; }
    if [ -n "$full" ] && [ -n "$design" ] && [ "$design" -gt 0 ] 2>/dev/null; then
        pct=$((full * 100 / design))
        hw "Akkumulátor $(basename "$b"): $(sysval "$b/model_name") — állapot ${pct}% a gyári kapacitáshoz képest"
        [ "$pct" -lt 60 ] && warn "Akkumulátor kopott (${pct}%) — hosszú fordításoknál/teszteknél hálózati táp ajánlott"
    else
        hw "Akkumulátor $(basename "$b"): jelen"
    fi
done
# Csak valós szenzorok: CPU csomag (x86_pkg_temp) és NVIDIA GPU. Az 'acpitz' zónák a
# ZBookon statikus trip-pont értékeket is mutathatnak (pl. állandó 85 °C), ezért azokat
# csak INFO-ként jelezzük.
for z in /sys/class/thermal/thermal_zone*; do
    [ -e "$z" ] || continue
    t="$(sysval "$z/temp")"; [ -z "$t" ] && continue
    ty="$(sysval "$z/type")"
    if [ "$ty" = "x86_pkg_temp" ] && [ "$((t / 1000))" -ge 85 ]; then
        warn "Magas CPU-hőmérséklet: $((t / 1000)) °C (terhelés nélkül? hűtés/paszta ellenőrzés)"
    fi
done
ACPI_HOT="$(for z in /sys/class/thermal/thermal_zone*; do [ "$(sysval "$z/type")" = "acpitz" ] || continue; t="$(sysval "$z/temp")"; [ -n "$t" ] && [ "$((t / 1000))" -ge 85 ] && basename "$z"; done | tr '\n' ' ')"
[ -n "$ACPI_HOT" ] && info "acpitz zónák ≥85 °C ($ACPI_HOT) — a ZBookon valószínűleg statikus ACPI érték, nem valós mérés; a CPU/GPU szenzorok a mérvadók"
if have nvidia-smi; then
    GT="$(nvidia-smi --query-gpu=temperature.gpu --format=csv,noheader,nounits 2>/dev/null | head -n1 | tr -d ' ')"
    [ -n "$GT" ] && [ "$GT" -ge 85 ] 2>/dev/null && warn "Magas GPU-hőmérséklet: ${GT} °C"
fi

# --- Firmware ----------------------------------------------------------------
while read -r fw; do
    [ -n "$fw" ] && fwm "$fw"
done < <(printf '%s\n' "$KLOG" | grep -iE 'Direct firmware load for .* failed|firmware: failed to load|failed to load firmware|no suitable firmware found|possible missing firmware' \
          | sed -E 's/^.*kernel: //; s/^\[[ 0-9.]+\] //' | sort -u | head -n 30)

# --- Kernel hibák --------------------------------------------------------------
if have journalctl; then
    ERR_COUNT="$(journalctl -k -b 0 -p err --no-pager -q 2>/dev/null | wc -l)"
    if [ "${ERR_COUNT:-0}" -gt 0 ]; then
        warn "$ERR_COUNT kernel hibaüzenet (prioritás: err) ebben a bootban — részletek a 'Kernel hibák' szakaszban"
    fi
fi

# =============================================================================
#  Összefoglaló kiírása
# =============================================================================
emit() {
    local tag="$1"; shift
    local n=$#
    if [ "$n" -eq 0 ]; then
        printf '[%s] (nincs)\n' "$tag"
    else
        for x in "$@"; do printf '[%s] %s\n' "$tag" "$x"; done
    fi
}

SUMMARY="$(
    echo
    echo "$SEP"
    echo "=== AUTOMATIKUS ÖSSZEFOGLALÓ ==="
    echo "$SEP"
    echo
    emit "HARDWARE OK" "${S_HW[@]+"${S_HW[@]}"}"
    echo
    emit "DRIVER OK" "${S_DRV_OK[@]+"${S_DRV_OK[@]}"}"
    echo
    emit "DRIVER MISSING" "${S_DRV_MISS[@]+"${S_DRV_MISS[@]}"}"
    echo
    emit "FIRMWARE MISSING" "${S_FW_MISS[@]+"${S_FW_MISS[@]}"}"
    echo
    emit "TECHNICAL WARNING" "${S_WARN[@]+"${S_WARN[@]}"}"
    echo
    emit "INFO" "${S_INFO[@]+"${S_INFO[@]}"}"
    echo
    printf 'Összesen: %d hardver OK, %d driver OK, %d driver hiányzik, %d firmware hiányzik, %d figyelmeztetés\n' \
        "${#S_HW[@]}" "${#S_DRV_OK[@]}" "${#S_DRV_MISS[@]}" "${#S_FW_MISS[@]}" "${#S_WARN[@]}"
    [ "$IS_ROOT" -ne 1 ] && echo "MEGJEGYZÉS: root nélkül futott — a dmidecode, smartctl és dmesg adatok hiányoznak (sudo bash $SCRIPT_NAME)."
    echo "$SEP"
)"

printf '%s\n' "$SUMMARY" | mask >> "$REPORT"

if [ "$IS_ROOT" -eq 1 ] && [ -n "${SUDO_USER:-}" ]; then
    chown "$SUDO_USER": "$REPORT" 2>/dev/null
fi

printf '%s\n' "$SUMMARY" | mask
echo
echo "Kész. Jelentés: $REPORT ($(wc -l < "$REPORT") sor)"
echo "Küldés előtt érdemes egyszer átnézni, hogy nem maradt-e benne személyes adat."
