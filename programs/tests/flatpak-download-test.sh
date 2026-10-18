#!/bin/sh
# Fúzió — próba: egy Flatpak-program (homokozóban, xdg-download joggal — mint a Firefox) „letölt” egy fájlt;
# a fájlnak a valódi Letöltések mappába kell kerülnie (és nem a homokozó ideiglenes ~/Downloads mappájába).
# Hálózat nélkül: a futtatókörnyezet a rendszer saját dash-ából és libc-jéből készül, helyi tárolóból települ.
#   flatpak-download-test.sh <munkamappa>     (a fusion felhasználóként, a munkamenetben)
# kimenet: „DL path=<ahova a homokozó írt> host=<a fájl a saját mappában, ha ott van>”
set -e
W=${1:?munkamappa}
rm -rf "$W"; mkdir -p "$W"; cd "$W"
mkdir -p rt/files rt/usr/bin rt/usr/lib/x86_64-linux-gnu rt/usr/lib64
cp /usr/bin/dash rt/usr/bin/dash; ln -s dash rt/usr/bin/sh
cp -L /lib/x86_64-linux-gnu/libc.so.6 rt/usr/lib/x86_64-linux-gnu/
cp -L /lib64/ld-linux-x86-64.so.2 rt/usr/lib64/
printf '[Runtime]\nname=org.fusionos.TestRuntime\nruntime=org.fusionos.TestRuntime/x86_64/1\nsdk=org.fusionos.TestRuntime/x86_64/1\n' > rt/metadata
flatpak build-export --runtime repo rt 1 >/dev/null
flatpak --user remote-delete --force fusiontest >/dev/null 2>&1 || true
flatpak --user remote-add --no-gpg-verify fusiontest "$W/repo"
flatpak --user install -y --noninteractive fusiontest org.fusionos.TestRuntime >/dev/null
flatpak build-init app org.fusionos.DownloadTest org.fusionos.TestRuntime org.fusionos.TestRuntime 1 >/dev/null
mkdir -p app/files/bin
cat > app/files/bin/dl <<'EOF'
#!/bin/sh
# mint egy böngésző: az XDG Letöltések mappa, ennek hiányában ~/Downloads
d=""
while IFS= read -r line; do
    case "$line" in XDG_DOWNLOAD_DIR=*) d=${line#XDG_DOWNLOAD_DIR=}; d=${d#\"}; d=${d%\"} ;; esac
done < "${XDG_CONFIG_HOME:-$HOME/.config}/user-dirs.dirs" 2>/dev/null || true
case "$d" in \$HOME*) d="$HOME${d#\$HOME}" ;; esac
[ -n "$d" ] || d="$HOME/Downloads"
echo letoltes > "$d/fusion-flatpak-letoltes.AppImage" 2>/dev/null && echo "$d" || echo "HIBA:$d"
EOF
chmod +x app/files/bin/dl
flatpak build-finish app --command=dl --filesystem=xdg-download >/dev/null
flatpak build-export repo app >/dev/null
flatpak --user install -y --noninteractive fusiontest org.fusionos.DownloadTest >/dev/null
out=$(flatpak run org.fusionos.DownloadTest 2>/dev/null | tail -n 1)
host=$(find "$HOME" -name fusion-flatpak-letoltes.AppImage -not -path "$HOME/.var/*" -not -path "$W/*" 2>/dev/null | head -n 1)
echo "DL path=$out host=$host"
rm -f "$host"
flatpak --user uninstall -y --noninteractive org.fusionos.DownloadTest org.fusionos.TestRuntime >/dev/null 2>&1 || true
flatpak --user remote-delete --force fusiontest >/dev/null 2>&1 || true
rm -rf "$W"
