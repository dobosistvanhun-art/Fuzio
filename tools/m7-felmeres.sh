#!/bin/bash
# FusionOS — M7 (A/B frissítés) előtti felmérés. NEM MÓDOSÍT SEMMIT; személyes adatot nem ír ki
# (Wi-Fi-hálózatnevek, saját fájlnevek helyett csak darabszám és méret).
#
#   FusionOS-en (Terminál, sudo nélkül):   bash m7-felmeres.sh
#       → a bootloader adatai (systemd-boot változat, funkciók: boot-számlálás), slot, ESP
#   Minten (a FusionOS-lemez DATA-ja csak olvashatóan):   sudo bash m7-felmeres.sh /dev/sdb
#       → mi van a DATA írható rendszerrétegében (overlay), mekkora, mi változott az /etc-ben
#
# A kimenetet (m7-felmeres.txt) kérem visszaküldeni.
set -u
OUT="$PWD/m7-felmeres.txt"
exec > >(tee "$OUT") 2>&1
echo "== FusionOS M7-felmérés  $(date '+%Y-%m-%d %H:%M')  ($(uname -r))"

EV=/sys/firmware/efi/efivars
LG=4a67b082-0a4c-41cf-b6c7-440b29bb8c4f
efistr() { [ -r "$EV/$1-$LG" ] && cat "$EV/$1-$LG" | tail -c +5 | tr -d '\000'; }   # az efivarfs nem léptethető
if [ -r /usr/lib/fusion/fusion-release ] || [ -r /etc/fusion-release ]; then
    echo "-- FusionOS: $(. /usr/lib/fusion/fusion-release 2>/dev/null; echo "${FUSION_VERSION:-?} (${FUSION_MILESTONE:-?})")"
    echo "slot: $(cat /run/fusion/slot 2>/dev/null)   boot-lemez: $(cat /run/fusion/boot-disk 2>/dev/null)"
    echo "bootloader: $(efistr LoaderInfo)"
    echo "firmware:   $(efistr LoaderFirmwareInfo)  (UEFI $(efistr LoaderFirmwareType))"
    echo "elindított bejegyzés: $(efistr LoaderEntrySelected)"
    if [ -r "$EV/LoaderFeatures-$LG" ]; then
        f=$(od -An -t u8 -j 4 -N 8 "$EV/LoaderFeatures-$LG" | tr -d ' ')
        echo "funkciók (LoaderFeatures=$f):"
        for b in "0:időkorlát" "1:egyszeri időkorlát" "2:alapértelmezett bejegyzés (EFI-változó)" "3:egyszeri bejegyzés (oneshot)" \
                 "4:BOOT-SZÁMLÁLÁS (automatikus visszaállás)" "5:XBOOTLDR" "6:véletlenszám-mag"; do
            n=${b%%:*}; echo "   $( (( (f >> n) & 1 )) && echo igen || echo nem )  ${b#*:}"
        done
    else
        echo "LoaderFeatures: nem olvasható (nem a systemd-boot indította?)"
    fi
    echo "-- ESP-bejegyzések (csak a fájlnevek):"
    lsblk -lno NAME,PARTLABEL,SIZE,FSTYPE 2>/dev/null | grep FUSION_
    echo "-- memória / DATA:"; df -h /data 2>/dev/null | tail -n 1
    exit 0
fi

# --- Minten: a DATA csak olvashatóan (noload: a napló sem íródik vissza) ---
dev=${1:-}
[ "$(id -u)" -eq 0 ] || { echo "Minten root kell:  sudo bash $0 /dev/sdX"; exit 1; }
[ -b "$dev" ] || { echo "add meg a FusionOS-lemezt, pl.: sudo bash $0 /dev/sdb"; exit 1; }
data=${M7_DATA_DEV:-$(lsblk -lnpo NAME,PARTLABEL "$dev" | awk '$2=="FUSION_DATA"{print $1}')}   # M7_*_DEV: csak fejlesztői próbához
esp=${M7_ESP_DEV:-$(lsblk -lnpo NAME,PARTLABEL "$dev" | awk '$2=="FUSION_ESP"{print $1}')}
[ -n "$data" ] || { echo "$dev nem FusionOS-lemez (nincs FUSION_DATA)"; exit 1; }
lsblk -o NAME,SIZE,FSTYPE,PARTLABEL "$dev"
m=$(mktemp -d); e=$(mktemp -d)
cleanup() { umount "$m" 2>/dev/null; umount "$e" 2>/dev/null; rmdir "$m" "$e"; }
trap cleanup EXIT
mount -o ro,noload "$data" "$m" || { echo "a DATA nem csatolható csak olvashatóan"; exit 1; }
U="$m/overlay/root/upper"
echo "-- DATA: $(df -h "$m" | awk 'NR==2{print $3" foglalt / "$2}')"
echo "-- DATA felső szint:"; du -xsh "$m"/* 2>/dev/null | sed "s#$m/##"
echo "-- írható rendszerréteg (overlay upper) összesen: $(du -xsh "$U" 2>/dev/null | cut -f1)"
for d in etc var root opt srv usr home; do [ -e "$U/$d" ] && echo "   /$d: $(du -xsh "$U/$d" | cut -f1), $(find "$U/$d" -xdev | wc -l) elem"; done
echo "-- /var részletesen:"; du -xh --max-depth=3 "$U/var" 2>/dev/null | sort -h | tail -n 25 | sed "s#$U##; s#/var/lib/iwd/.*#/var/lib/iwd/(rejtve)#"
echo "-- /home/fusion: rejtett mappák (beállítások) és a többi összesítve:"
H="$U/home/fusion"
[ -d "$H" ] && du -xsh "$H"/.[!.]* 2>/dev/null | sort -h | tail -n 15 | sed "s#$H/##"
[ -d "$H" ] && echo "   egyéb (saját fájlok/mappák): $(find "$H" -mindepth 1 -maxdepth 1 ! -name '.*' | wc -l) elem, $(du -xsc "$H"/[!.]* 2>/dev/null | tail -n1 | cut -f1) KiB"
echo "-- az /etc-ben módosított / új fájlok (a rendszerképhez képest):"
find "$U/etc" -xdev \( -type f -o -type l -o -type c \) 2>/dev/null | sed "s#$U##" | sed 's#^/etc/NetworkManager/system-connections/.*#/etc/NetworkManager/system-connections/(rejtve)#' | sort | uniq -c | awk '{print "   "$2}' | head -n 80
echo "-- törlésjelölők (overlay whiteout) száma: $(find "$U" -xdev -type c 2>/dev/null | wc -l)"
echo "-- a korábbi frissítésekből félretett fájlok (stale): $(ls "$m/overlay/stale" 2>/dev/null | wc -l) alkalom"
echo "-- image-release: $(sed -n "s/^FUSION_VERSION=//p" "$m/overlay/image-release" 2>/dev/null | tr -d "'")"
if [ -n "$esp" ] && mount -o ro "$esp" "$e" 2>/dev/null; then
    echo "-- ESP: $(df -h "$e" | awk 'NR==2{print $3" / "$2}')"; (cd "$e" && find EFI/Linux loader -type f | sort | sed 's/^/   /')
fi
echo "== kész: $OUT"
