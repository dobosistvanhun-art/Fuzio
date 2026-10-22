#!/bin/sh
# =============================================================================
#  Fúzió Hardware Layer — fusion-hwprobe tesztek hamis sysfs-fákkal.
#  Futtatás:  sh tests/hwprobe-test.sh        (bash vagy busybox sh is jó)
#             SHELL_UNDER_TEST="busybox sh" sh tests/hwprobe-test.sh
# =============================================================================
set -u
ROOT=$(cd "$(dirname "$0")/.." && pwd)
PROBE="$ROOT/hardware/fusion-hwprobe"
RUNNER=${SHELL_UNDER_TEST:-sh}
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
PASS=0; FAIL=0

# mkpci <sysfs> <slot> <class> <vendor> <device> <boot_vga> <driver|->
mkpci() {
    d="$1/bus/pci/devices/$2"
    mkdir -p "$d"
    echo "$3" > "$d/class"; echo "$4" > "$d/vendor"; echo "$5" > "$d/device"
    [ "$6" != "-" ] && echo "$6" > "$d/boot_vga"
    if [ "$7" != "-" ]; then
        mkdir -p "$1/bus/pci/drivers/$7"
        ln -s "../../../bus/pci/drivers/$7" "$d/driver"
    fi
}

# check <név> <sysfs> <várt profil> <várt állapot>
check() {
    name=$1; sys=$2; want_p=$3; want_s=$4
    run="$TMP/run-$name"
    FUSION_CMDLINE="${CMDLINE_FILE:-/dev/null}" FUSION_SYSFS="$sys" FUSION_RUN="$run" $RUNNER "$PROBE" -q
    env="$run/hardware/display.env"
    got_p=$(sed -n "s/^FUSION_DISPLAY_PROFILE='\(.*\)'$/\1/p" "$env" 2>/dev/null)
    got_s=$(sed -n "s/^FUSION_DISPLAY_STATUS='\(.*\)'$/\1/p" "$env" 2>/dev/null)
    if [ "$got_p" = "$want_p" ] && [ "$got_s" = "$want_s" ]; then
        PASS=$((PASS + 1)); echo "  OK    $name: $got_p / $got_s"
    else
        FAIL=$((FAIL + 1)); echo "  HIBA  $name: várt $want_p / $want_s, kapott ${got_p:-<üres>} / ${got_s:-<üres>}"
        sed 's/^/        /' "$env" 2>/dev/null
    fi
}

echo "fusion-hwprobe tesztek ($RUNNER)"

# 1. ZBook diszkrét mód (Phase 0b): csak a Quadro látható
S="$TMP/zbook-discrete"
mkpci "$S" 0000:00:1f.2 0x010601 0x8086 0x8c03 - ahci
mkpci "$S" 0000:01:00.0 0x030000 0x10de 0x0ff6 1 nvidia
mkpci "$S" 0000:01:00.1 0x040300 0x10de 0x0e1b - snd_hda_intel
check zbook-discrete "$S" nvidia-kepler-470 ok

# 2. ZBook hibrid mód (Phase 0): Intel a boot VGA, NVIDIA mellette
S="$TMP/zbook-hybrid"
mkpci "$S" 0000:00:02.0 0x030000 0x8086 0x0416 1 i915
mkpci "$S" 0000:01:00.0 0x030000 0x10de 0x0ff6 0 nvidia
check zbook-hybrid "$S" nvidia-kepler-470 warning

# 3. ZBook diszkrét mód, még driver nélkül (initramfs, modulok előtt)
S="$TMP/zbook-nodriver"
mkpci "$S" 0000:01:00.0 0x030000 0x10de 0x0ff6 1 -
check zbook-nodriver "$S" nvidia-kepler-470 ok

# 4. VirtualBox VMSVGA
S="$TMP/vbox-vmsvga"
mkpci "$S" 0000:00:02.0 0x030000 0x15ad 0x0405 1 -
check vbox-vmsvga "$S" vmware-svga ok

# 5. VirtualBox VBoxSVGA
S="$TMP/vbox-vboxsvga"
mkpci "$S" 0000:00:02.0 0x030000 0x80ee 0xbeef 1 -
check vbox-vboxsvga "$S" virtualbox-vga ok

# 6. QEMU std VGA (bochs) — nincs saját profil, az általános tartalék illik
S="$TMP/qemu-std"
mkpci "$S" 0000:00:01.0 0x030000 0x1234 0x1111 1 -
check qemu-std "$S" generic-kms ok

# 7. Nincs PCI grafikus adapter — firmware framebuffer tartalék
S="$TMP/no-pci-display"
mkpci "$S" 0000:00:1f.2 0x010601 0x8086 0x8c03 - ahci
check no-pci-display "$S" firmware-fb fallback

# 8. Nagybetűs azonosítók a sysfs-ben (robosztusság)
S="$TMP/uppercase"
mkpci "$S" 0000:01:00.0 0x030000 0x10DE 0x0FF6 1 nvidia
check uppercase "$S" nvidia-kepler-470 ok

# 9. Két azonos prioritású adapter: a boot_vga=1 nyer
S="$TMP/tie-bootvga"
mkpci "$S" 0000:00:02.0 0x030000 0x1234 0x1111 0 -
mkpci "$S" 0000:00:03.0 0x030000 0x1af4 0x1050 1 -
check tie-bootvga "$S" generic-kms ok
slot=$(sed -n "s/^FUSION_DISPLAY_ADAPTER='\(.*\)'$/\1/p" "$TMP/run-tie-bootvga/hardware/display.env")
if [ "$slot" = "0000:00:03.0" ]; then PASS=$((PASS + 1)); echo "  OK    tie-bootvga: a boot_vga adapter nyert ($slot)"
else FAIL=$((FAIL + 1)); echo "  HIBA  tie-bootvga: várt 0000:00:03.0, kapott $slot"; fi

# 10. A display.env shell-lel betölthető, és a profilkulcsok átjönnek
# shellcheck disable=SC1091
. "$TMP/run-zbook-hybrid/hardware/display.env"
if [ "${FUSION_PROFILE_DISPLAY_DRIVER:-}" = "nvidia-470" ] && [ "${FUSION_PROFILE_VULKAN_MAX:-}" = "1.2" ] && [ -n "${FUSION_DISPLAY_MESSAGE:-}" ]; then
    PASS=$((PASS + 1)); echo "  OK    display.env betölthető, profilkulcsok és üzenet megvan"
else
    FAIL=$((FAIL + 1)); echo "  HIBA  display.env tartalma hiányos"
fi

# 10b. kézi profilválasztás (mérési boot-bejegyzések, 0.0.30): fusion.display.profile=<id>
CMDLINE_FILE="$TMP/cmdline-ov"
echo "quiet fusion.display.profile=intel-kms" > "$CMDLINE_FILE"
check override-intel-hybrid "$TMP/zbook-hybrid" intel-kms manual
slot=$(sed -n "s/^FUSION_DISPLAY_ADAPTER='\(.*\)'$/\1/p" "$TMP/run-override-intel-hybrid/hardware/display.env")
if [ "$slot" = "0000:00:02.0" ]; then PASS=$((PASS + 1)); echo "  OK    override-intel-hybrid: az Intel adapter ($slot)"
else FAIL=$((FAIL + 1)); echo "  HIBA  override-intel-hybrid: várt 0000:00:02.0, kapott $slot"; fi
check override-intel-discrete "$TMP/zbook-discrete" nvidia-kepler-470 warning
echo "quiet fusion.display.profile=nvidia-nouveau" > "$CMDLINE_FILE"
check override-nouveau "$TMP/zbook-discrete" nvidia-nouveau manual
CMDLINE_FILE=""
# Nouveau-profil automatikusan nem nyer a 470 ellen
check auto-nem-nouveau "$TMP/zbook-nodriver" nvidia-kepler-470 ok

# 11-13. --apply: ál-modinfo/modprobe. FAKE_MODS = létező modulok, FAKE_BROKEN = betölthetetlenek
FAKEBIN="$TMP/fakebin"; mkdir -p "$FAKEBIN"
cat > "$FAKEBIN/modinfo" <<'EOS'
#!/bin/sh
m=$(eval echo "\$$#")
case " $FAKE_MODS " in *" $m "*) echo "/lib/modules/x/$m.ko"; exit 0 ;; esac
exit 1
EOS
cat > "$FAKEBIN/modprobe" <<'EOS'
#!/bin/sh
# ál-modprobe: a betöltött modult és paramétereit a hamis sysfs-be írja (module/<név>/parameters)
if [ "$1" = "-r" ]; then
    echo "-r $2" >> "$FAKE_LOG"; rm -rf "$FUSION_SYSFS/module/$(echo "$2" | tr - _)"; exit 0
fi
m=$1; shift
case " $FAKE_BROKEN " in *" $m "*) exit 1 ;; esac
echo "$m${*:+ $*}" >> "$FAKE_LOG"
d="$FUSION_SYSFS/module/$(echo "$m" | tr - _)"
[ -d "$d" ] && exit 0          # már betöltve: a paraméterek nem változnak (mint a valóságban)
mkdir -p "$d/parameters"
for kv in "$@"; do
    v=${kv#*=}; case "$v" in 1) v=Y ;; 0) v=N ;; esac
    echo "$v" > "$d/parameters/${kv%%=*}"
done
exit 0
EOS
chmod +x "$FAKEBIN/modinfo" "$FAKEBIN/modprobe"

# apply_check <név> <sysfs> <FAKE_MODS> <FAKE_BROKEN> <várt állapot> <várt betöltött modulok>
apply_check() {
    run="$TMP/apply-$1"; log="$TMP/apply-$1.log"; : > "$log"
    [ "${KEEP_MODULES:-}" = 1 ] || rm -rf "$2/module"
    FUSION_MODINFO="$FAKEBIN/modinfo" FUSION_MODPROBE="$FAKEBIN/modprobe" \
        FAKE_MODS="$3" FAKE_BROKEN="$4" FAKE_LOG="$log" FUSION_CMDLINE="${CMDLINE_FILE:-/dev/null}" FUSION_MODPROBE_D="$run/modprobe.d" FUSION_BIND_WAIT=0 \
        FUSION_SYSFS="$2" FUSION_RUN="$run" $RUNNER "$PROBE" --apply -q
    st=$(sed -n "s/^FUSION_DISPLAY_DRIVER_STATE='\(.*\)'$/\1/p" "$run/hardware/display.env")
    loaded=$(tr '\n' ' ' < "$log" | sed 's/ $//')
    if [ "$st" = "$5" ] && [ "$loaded" = "$6" ]; then
        PASS=$((PASS + 1)); echo "  OK    apply $1: $st [${loaded}]"
    else
        FAIL=$((FAIL + 1)); echo "  HIBA  apply $1: várt $5 [$6], kapott $st [$loaded]"
    fi
}
# ZBook M1-ben: az NVIDIA driver még nincs telepítve -> missing, semmi nem töltődik be
apply_check zbook-m1 "$TMP/zbook-discrete" "i915 vmwgfx" "" missing ""
# ZBook M2-től: minden NVIDIA modul megvan -> loaded, sorrendben
apply_check zbook-m2 "$TMP/zbook-discrete" "nvidia nvidia-modeset nvidia-drm" "" loaded "nvidia nvidia-modeset nvidia-drm modeset=1"
# VirtualBox VMSVGA -> vmwgfx betöltve, az eszközt átvette
S="$TMP/vbox-bound"
mkpci "$S" 0000:00:02.0 0x030000 0x15ad 0x0405 1 vmwgfx
apply_check vbox "$S" "vmwgfx" "" loaded "vmwgfx"
# QEMU -vga vmware: a vmwgfx betöltődik, de az eszközt nem veszi át -> failed
apply_check vbox-unbound "$TMP/vbox-vmsvga" "vmwgfx" "" failed "vmwgfx"
# a modul megvan, de nem tölthető be -> failed
apply_check vbox-broken "$TMP/vbox-vmsvga" "vmwgfx" "vmwgfx" failed ""
# firmware framebuffer: nincs modul -> none
apply_check fw "$TMP/no-pci-display" "" "" none ""

# conf_check <leírás> <fájl> <minta> [nincs]: a generált fájlban van (vagy nincs) a minta
conf_check() {
    if grep -q -- "$3" "$2" 2>/dev/null; then found=1; else found=0; fi
    if { [ "${4:-}" = nincs ] && [ $found -eq 0 ]; } || { [ "${4:-}" != nincs ] && [ $found -eq 1 ]; }; then
        PASS=$((PASS + 1)); echo "  OK    $1"
    else
        FAIL=$((FAIL + 1)); echo "  HIBA  $1  ($3 ${4:-})"; sed 's/^/        /' "$2" 2>/dev/null
    fi
}
# Xorg beállítás a profilból (M2)
X="$TMP/apply-zbook-m2/hardware"
conf_check "xorg: NVIDIA driver"         "$X/xorg-display.conf" 'Driver "nvidia"'
conf_check "xorg: BusID decimális"       "$X/xorg-display.conf" 'BusID "PCI:1@0:0:0"'
conf_check "xorg: nincs automatikus második GPU-képernyő" "$X/xorg-display.conf" 'Option "AutoAddGPU" "false"'
conf_check "xorg: NVIDIA modulútvonal"   "$X/xorg-display.conf" 'ModulePath "/usr/lib/x86_64-linux-gnu/nvidia/xorg"'
conf_check "xorg: root-jog a profilból (auto)" "$X/Xwrapper.config" 'needs_root_rights=auto'
conf_check "modprobe.d: nvidia_drm modeset=1" "$TMP/apply-zbook-m2/modprobe.d/fusion-hardware-options.conf" 'options nvidia_drm modeset=1'
conf_check "modprobe.d: nincs videómemória-mentés (0.0.56: a 470-es driverrel beragadt)" "$TMP/apply-zbook-m2/modprobe.d/fusion-hardware-options.conf" 'PreserveVideoMemoryAllocations' nincs
X="$TMP/apply-zbook-m1/hardware"
conf_check "xorg: driver nélkül nincs Device szakasz" "$X/xorg-display.conf" 'Section "Device"' nincs
conf_check "xorg: át nem vett eszköznél nincs Device szakasz" "$TMP/apply-vbox-unbound/hardware/xorg-display.conf" 'Section "Device"' nincs
X="$TMP/apply-vbox/hardware"
conf_check "xorg: VMSVGA -> modesetting" "$X/xorg-display.conf" 'Driver "modesetting"'
conf_check "xorg: VMSVGA root=auto"      "$X/Xwrapper.config"   'needs_root_rights=auto'
# kernel parancssori felülírás: nvidia-drm.modeset=0 és fusion.xorg.root=auto
CMDLINE_FILE="$TMP/cmdline"; echo "quiet nvidia_drm.modeset=0 fusion.xorg.root=yes fusion.slot=A" > "$CMDLINE_FILE"
apply_check zbook-cmdline "$TMP/zbook-discrete" "nvidia nvidia-modeset nvidia-drm" "" loaded "nvidia nvidia-modeset nvidia-drm"
conf_check "parancssor: modprobe.d-ben nincs modeset" "$TMP/apply-zbook-cmdline/modprobe.d/fusion-hardware-options.conf" 'modeset' nincs
conf_check "parancssor: fusion.xorg.root=yes" "$TMP/apply-zbook-cmdline/hardware/Xwrapper.config" 'needs_root_rights=yes'
CMDLINE_FILE=""

# az nvidia-drm-et egy udev-szabály előbb, paraméter nélkül töltötte be (a ZBookon mért eset):
# a Hardware Layer észreveszi (modeset=N), újratölti modeset=1-gyel, és jelenti
S="$TMP/zbook-discrete"
rm -rf "$S/module"; mkdir -p "$S/module/nvidia_drm/parameters"; echo N > "$S/module/nvidia_drm/parameters/modeset"
KEEP_MODULES=1 apply_check zbook-udev-elobb "$S" "nvidia nvidia-modeset nvidia-drm" "" loaded "nvidia nvidia-modeset nvidia-drm modeset=1 -r nvidia-drm nvidia-drm modeset=1"
conf_check "újratöltés után modeset=Y" "$S/module/nvidia_drm/parameters/modeset" '^Y$'
conf_check "a jelentésben a tényleges érték" "$TMP/apply-zbook-udev-elobb/hardware/display.env" "FUSION_DISPLAY_MODULE_PARAMS='nvidia_drm.modeset=Y'"

echo "Eredmény: $PASS sikeres, $FAIL hibás"
[ "$FAIL" -eq 0 ]
