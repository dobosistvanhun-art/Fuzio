#!/bin/sh
# =============================================================================
#  Fusion Hardware Layer — fusion-hwprobe tesztek hamis sysfs-fákkal.
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
    FUSION_SYSFS="$sys" FUSION_RUN="$run" $RUNNER "$PROBE" -q
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
m=$(eval echo "\$$#")
case " $FAKE_BROKEN " in *" $m "*) exit 1 ;; esac
echo "$m" >> "$FAKE_LOG"; exit 0
EOS
chmod +x "$FAKEBIN/modinfo" "$FAKEBIN/modprobe"

# apply_check <név> <sysfs> <FAKE_MODS> <FAKE_BROKEN> <várt állapot> <várt betöltött modulok>
apply_check() {
    run="$TMP/apply-$1"; log="$TMP/apply-$1.log"; : > "$log"
    FUSION_MODINFO="$FAKEBIN/modinfo" FUSION_MODPROBE="$FAKEBIN/modprobe" \
        FAKE_MODS="$3" FAKE_BROKEN="$4" FAKE_LOG="$log" \
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
apply_check zbook-m2 "$TMP/zbook-discrete" "nvidia nvidia-modeset nvidia-drm" "" loaded "nvidia nvidia-modeset nvidia-drm"
# VirtualBox VMSVGA -> vmwgfx betöltve
apply_check vbox "$TMP/vbox-vmsvga" "vmwgfx" "" loaded "vmwgfx"
# a modul megvan, de nem tölthető be -> failed
apply_check vbox-broken "$TMP/vbox-vmsvga" "vmwgfx" "vmwgfx" failed ""
# firmware framebuffer: nincs modul -> none
apply_check fw "$TMP/no-pci-display" "" "" none ""

echo "Eredmény: $PASS sikeres, $FAIL hibás"
[ "$FAIL" -eq 0 ]
