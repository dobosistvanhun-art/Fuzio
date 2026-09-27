#!/bin/sh
# =============================================================================
#  Fusion eszközréteg — fusion-devd tesztek (hamis udev-környezettel)
#  Futtatás:  sh tests/devices-test.sh
#             SHELL_UNDER_TEST="busybox sh" sh tests/devices-test.sh
# =============================================================================
set -u
ROOT=$(cd "$(dirname "$0")/.." && pwd)
DEVD="$ROOT/devices/fusion-devd"
RUNNER=${SHELL_UNDER_TEST:-sh}
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
PASS=0; FAIL=0

export FUSION_DEVICES_DB="$TMP/etc/fusion/devices.conf"
export FUSION_DEVICES_LOCK="$TMP/run/devices.lock"
export FUSION_DEV="$TMP/dev"
export FUSION_SYSFS="$TMP/sys"
mkdir -p "$FUSION_DEV" "$TMP/props"

# ál-udevadm: "info -q property -n <eszköz>" a $TMP/props/<név> fájlból; trigger -> napló
cat > "$TMP/udevadm" <<EOS
#!/bin/sh
case "\$1" in
    info)  eval "n=\\\${\$#}"; cat "$TMP/props/\$(basename "\$n")" 2>/dev/null ;;
    trigger|settle) echo "\$*" >> "$TMP/udevadm.log" ;;
esac
exit 0
EOS
chmod +x "$TMP/udevadm"
export FUSION_UDEVADM="$TMP/udevadm"

ok()   { PASS=$((PASS + 1)); echo "  OK    $1"; }
bad()  { FAIL=$((FAIL + 1)); echo "  HIBA  $1"; [ -n "${2:-}" ] && printf '%s\n' "$2" | sed 's/^/        /'; }

# ev <vid> <pid> <sorozatszám|-> <id_path>: a udev IMPORT kimenete
ev() {
    ser=$3; [ "$ser" = "-" ] && ser=""
    ID_VENDOR_ID=$1 ID_MODEL_ID=$2 ID_SERIAL_SHORT=$ser ID_PATH=$4 $RUNNER "$DEVD" udev
}
# expect <leírás> <kimenet> <várt sorok, | elválasztva>
expect() {
    got=$(printf '%s' "$2" | tr '\n' '|' | sed 's/|$//')
    if [ "$got" = "$3" ]; then ok "$1"; else bad "$1: várt [$3], kapott [$got]"; fi
}
db() { grep -v '^#' "$FUSION_DEVICES_DB" 2>/dev/null | tr '\n' '|' | sed 's/|$//'; }

PORT2="pci-0000:00:14.0-usb-0:2:1.0"
PORT3="pci-0000:00:14.0-usb-0:3:1.0"
PORT9="pci-0000:00:14.0-usb-0:9:1.0"
PORT1="pci-0000:00:14.0-usb-0:1:1.0"

echo "fusion-devd tesztek ($RUNNER)"

# 1. első CH340 a 2-es porton, üres nyilvántartás -> automatikusan a lézer lesz
out=$(ev 1a86 7523 - "$PORT2")
expect "CH340 első bedugás -> laser (új)" "$out" "FUSION_ROLE=laser|FUSION_DEVICE_KEY=path:1a86:7523:$PORT2|FUSION_ROLE_NEW=1"
$RUNNER "$DEVD" record laser "path:1a86:7523:$PORT2" /devices/x/ttyUSB0
expect "record -> nyilvántartás" "$(db)" "laser path:1a86:7523:$PORT2"

# 2. kihúzás-visszadugás ugyanabba a portba -> ugyanaz a szerep, már nem új
out=$(ev 1a86 7523 - "$PORT2")
expect "CH340 visszadugva ugyanoda -> laser" "$out" "FUSION_ROLE=laser|FUSION_DEVICE_KEY=path:1a86:7523:$PORT2"

# 3. CH340 másik porton -> nem kap szerepet, csak jelölt (a lézer a 2-es porthoz kötött)
out=$(ev 1a86 7523 - "$PORT3")
expect "CH340 másik porton -> jelölt" "$out" "FUSION_CANDIDATE=laser"

# 4. CP2102 sorozatszámmal -> nyomtató, sorozatszám szerinti kulccsal
out=$(ev 10c4 ea60 A1B2C3 "$PORT9")
expect "CP2102 -> printer (új, sorozatszám)" "$out" "FUSION_ROLE=printer|FUSION_DEVICE_KEY=serial:10c4:ea60:A1B2C3|FUSION_ROLE_NEW=1"
$RUNNER "$DEVD" record printer "serial:10c4:ea60:A1B2C3" /devices/x/ttyUSB1

# 5. CP2102 más portban -> a sorozatszám alapján ugyanaz a nyomtató
out=$(ev 10c4 ea60 A1B2C3 "$PORT1")
expect "CP2102 más porton -> printer" "$out" "FUSION_ROLE=printer|FUSION_DEVICE_KEY=serial:10c4:ea60:A1B2C3"

# 6. másik CP2102 (más sorozatszám) -> jelölt
out=$(ev 10c4 ea60 ZZZ999 "$PORT3")
expect "második CP2102 -> jelölt" "$out" "FUSION_CANDIDATE=printer"

# 7. ismeretlen soros eszköz (PL2303) -> semmi
out=$(ev 067b 2303 - "$PORT3")
expect "PL2303 -> nincs szerep" "$out" ""

# 8. egyszerre bedugott két CH340: a második record nem írja felül az elsőt,
#    és a második eszköz szabályai újrafutnak (a név nem kettőződik)
: > "$TMP/udevadm.log"
$RUNNER "$DEVD" record laser "path:1a86:7523:$PORT3" /devices/x/ttyUSB2
expect "verseny: a nyilvántartás változatlan" "$(db)" "laser path:1a86:7523:$PORT2|printer serial:10c4:ea60:A1B2C3"
if grep -q "trigger --action=change $FUSION_SYSFS/devices/x/ttyUSB2" "$TMP/udevadm.log"; then ok "verseny: a vesztes eszköz újraértékelve"; else bad "verseny: nincs újraértékelés" "$(cat "$TMP/udevadm.log")"; fi

# 9. kézi hozzárendelés: a lézer a 3-as portra kerül
touch "$FUSION_DEV/ttyUSB2"
printf 'ID_VENDOR_ID=1a86\nID_MODEL_ID=7523\nID_PATH=%s\nID_MODEL=USB_Serial\n' "$PORT3" > "$TMP/props/ttyUSB2"
out=$($RUNNER "$DEVD" assign laser ttyUSB2 2>&1)
expect "assign laser ttyUSB2 -> nyilvántartás" "$(db)" "printer serial:10c4:ea60:A1B2C3|laser path:1a86:7523:$PORT3"
out=$(ev 1a86 7523 - "$PORT3")
expect "assign után a 3-as port a lézer" "$out" "FUSION_ROLE=laser|FUSION_DEVICE_KEY=path:1a86:7523:$PORT3"
out=$(ev 1a86 7523 - "$PORT2")
expect "assign után a 2-es port jelölt" "$out" "FUSION_CANDIDATE=laser"

# 10. forget: a nyomtató szerep felszabadul, a következő CP2102 automatikusan megkapja
$RUNNER "$DEVD" forget printer >/dev/null
expect "forget printer" "$(db)" "laser path:1a86:7523:$PORT3"
out=$(ev 10c4 ea60 ZZZ999 "$PORT3")
expect "forget után a CP2102 új nyomtató" "$out" "FUSION_ROLE=printer|FUSION_DEVICE_KEY=serial:10c4:ea60:ZZZ999|FUSION_ROLE_NEW=1"

# 10b. más típusú eszköz a lézer portjában nem veszi át a lézer szerepet
out=$(ev 10c4 ea60 QQQ111 "$PORT3")
expect "CP2102 a lézer portjában -> nyomtató, nem lézer" "$out" "FUSION_ROLE=printer|FUSION_DEVICE_KEY=serial:10c4:ea60:QQQ111|FUSION_ROLE_NEW=1"

# 11. sorozatszám nélküli eszköz sorozatszámos szerephez -> port szerinti kulcs
rm -f "$FUSION_DEVICES_DB"
out=$(ev 2341 0042 - "$PORT1")
expect "Arduino sorozatszám nélkül -> printer port szerint" "$out" "FUSION_ROLE=printer|FUSION_DEVICE_KEY=path:2341:0042:$PORT1|FUSION_ROLE_NEW=1"

# 12. nagybetűs azonosítók is illeszkednek
out=$(ev 1A86 7523 - "$PORT2")
expect "nagybetűs vid -> laser" "$out" "FUSION_ROLE=laser|FUSION_DEVICE_KEY=path:1a86:7523:$PORT2|FUSION_ROLE_NEW=1"

# 13. assign ismeretlen szerepre / nem létező eszközre -> hiba, nincs írás
if $RUNNER "$DEVD" assign kavefozo ttyUSB2 >/dev/null 2>&1; then bad "ismeretlen szerep elfogadva"; else ok "ismeretlen szerep elutasítva"; fi
if $RUNNER "$DEVD" assign laser ttyUSB7 >/dev/null 2>&1; then bad "nem létező eszköz elfogadva"; else ok "nem létező eszköz elutasítva"; fi

# 14. list: szerepek és állapotok (hamis /dev/fusion)
rm -f "$FUSION_DEVICES_DB"; $RUNNER "$DEVD" record laser "path:1a86:7523:$PORT2" >/dev/null
mkdir -p "$FUSION_DEV/fusion"; touch "$FUSION_DEV/ttyUSB0"; ln -sf ../ttyUSB0 "$FUSION_DEV/fusion/laser"
out=$($RUNNER "$DEVD" list)
if printf '%s' "$out" | grep -q "Lézer (GRBL) (laser)" && printf '%s' "$out" | grep -q "csatlakoztatva: .*/fusion/laser -> ttyUSB0" \
   && printf '%s' "$out" | grep -q "3D nyomtató (Klipper) (printer)" && printf '%s' "$out" | grep -q "nincs hozzárendelve" \
   && printf '%s' "$out" | grep -q "Windows:  COM3"; then
    ok "list: szerepek, állapot, COM3"
else
    bad "list kimenete" "$out"
fi

echo "Eredmény: $PASS sikeres, $FAIL hibás"
[ "$FAIL" -eq 0 ]
