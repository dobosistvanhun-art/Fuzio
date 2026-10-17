#!/bin/bash
# Vas & Króm — Windows-változat (hordozható mappa + VasEsKrom.exe indító), ZIP-be csomagolva
#
#   desktop/games/vaskrom/windows/build-windows.sh [kimeneti-mappa]
#
# Mit csinál (Linuxon, Windows nélkül):
#   1. Windows-Python (beágyazható, 3.13, a PyPI python-embed csomagjából) → runtime\
#   2. PyQt6 6.6 Windows-kerekek (a PyPI-ről) → runtime\Lib\site-packages — a nem használt Qt-részek nélkül
#      (a Qt 6.6 kell: a 6.7+ a Windows saját ICU-ját kéri, az régi Windowson és Wine alatt nincs)
#   3. a játék (Python + QML + képek) + DejaVu betűk → game\
#   4. VasEsKrom.exe: kis C indító ikonnal (mingw-w64), a runtime\pythonw.exe-vel indítja a játékot
#   5. ZIP: VasEsKrom-<verzió>-windows.zip (kicsomagolás után a VasEsKrom.exe indul; telepítés nem kell)
#
# Kell hozzá: python3 + pip, PyQt6 (az ikonhoz; más Python: QTPYTHON=…), x86_64-w64-mingw32-gcc / windres (mingw-w64), unzip, zip,
# internet a PyPI-hez. Próba (nem kötelező): WINE=<wine> esetén a játék öntesztje Wine alatt.
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
GAME=$(dirname "$HERE")
ROOT=$(cd "$GAME/../../.." && pwd)
. "$ROOT/VERSION"
OUT=${1:-$ROOT/build/out/windows}
WORK=$OUT/work
APP=$WORK/VasEsKrom
PYQT="PyQt6==6.6.1 PyQt6-Qt6==6.6.3 PyQt6-sip==13.13.0"
EMBED="python-embed==3.13.0"

for c in python3 unzip zip x86_64-w64-mingw32-gcc x86_64-w64-mingw32-windres; do
    command -v "$c" >/dev/null || { echo "hiányzik: $c (mingw-w64, zip, unzip)"; exit 1; }
done
rm -rf "$WORK"; mkdir -p "$WORK/dl" "$APP/runtime/Lib/site-packages" "$APP/game/fonts"

echo "==> Windows-Python (beágyazható) és PyQt6-kerekek a PyPI-ről"
python3 -m pip download -q --no-deps --no-binary :all: "$EMBED" -d "$WORK/dl"
python3 -m pip download -q --no-deps --only-binary :all: --platform win_amd64 --python-version 3.13 --implementation cp $PYQT -d "$WORK/dl"
tar -xzf "$WORK"/dl/python_embed-*.tar.gz -C "$WORK/dl"
unzip -q "$WORK"/dl/python_embed-*/src3.13/python_embed/data.zip -d "$WORK/dl/embed"
cp -r "$WORK"/dl/embed/cp313/. "$APP/runtime/"
printf 'python313.zip\r\n.\r\nLib\\site-packages\r\n..\\game\r\nimport site\r\n' > "$APP/runtime/python313._pth"
for w in "$WORK"/dl/*.whl; do unzip -q -o "$w" -d "$APP/runtime/Lib/site-packages"; done

echo "==> a nem használt Qt-részek eltávolítása"
P=$APP/runtime/Lib/site-packages/PyQt6
for pat in Bluetooth Designer Help Labs Nfc Pdf Positioning Quick3D QuickTest Test RemoteObjects Sensors SerialPort \
           SpatialAudio Sql TextToSpeech WebChannel WebSockets QuickTimeline QuickControls2Fusion QuickControls2Imagine \
           QuickControls2Material QuickControls2Universal QuickWidgets MultimediaWidgets PrintSupport Xml Concurrent DBus \
           OpenGLWidgets SvgWidgets ShaderTools QuickParticles; do
    rm -f "$P"/Qt6/bin/Qt6"$pat"*.dll "$P"/Qt"$pat"*.pyd
done
rm -rf "$P"/Qt6/translations "$P"/Qt6/qsci
for d in QtQuick3D QtPositioning QtRemoteObjects QtSensors QtTest QtTextToSpeech QtWebChannel QtWebSockets \
         QtQuick/Particles QtQuick/Timeline QtQuick/Pdf; do rm -rf "$P/Qt6/qml/$d"; done
for st in Material Universal Fusion Imagine FluentWinUI3 Windows macOS iOS; do rm -rf "$P/Qt6/qml/QtQuick/Controls/$st"; done
for d in sqldrivers position sensors texttospeech designer qmltooling canbus assetimporters; do rm -rf "$P/Qt6/plugins/$d"; done
find "$APP/runtime" -name '*.pyi' -delete

echo "==> a játék"
cp "$GAME"/fusion_vaskrom.py "$GAME"/model.py "$GAME"/art.py "$GAME"/sound.py "$APP/game/"
cp -r "$GAME/qml" "$GAME/img" "$APP/game/"
for f in /usr/share/fonts/truetype/dejavu/DejaVuSans.ttf /usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf \
         /usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf /usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf \
         /usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf; do [ -r "$f" ] && cp "$f" "$APP/game/fonts/"; done

echo "==> VasEsKrom.exe (indító, ikonnal)"
QT_QPA_PLATFORM=offscreen "${QTPYTHON:-python3}" - "$ROOT/desktop/icons/app-vaskrom.svg" "$WORK/vaskrom.ico" <<'PY'
import sys
from PyQt6.QtGui import QGuiApplication, QImage, QPainter
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtCore import QRectF
app = QGuiApplication([])
r = QSvgRenderer(sys.argv[1])
img = QImage(256, 256, QImage.Format.Format_ARGB32); img.fill(0)
p = QPainter(img); r.render(p, QRectF(0, 0, 256, 256)); p.end()
assert img.save(sys.argv[2], "ICO"), "az ICO nem menthető"
PY
cp "$WORK/vaskrom.ico" "$APP/game/vaskrom.ico"
cat > "$WORK/res.rc" <<EOF
1 ICON "vaskrom.ico"
1 VERSIONINFO
FILEVERSION 0,0,${FUSION_VERSION##*.},0
PRODUCTVERSION 0,0,${FUSION_VERSION##*.},0
BEGIN
  BLOCK "StringFileInfo"
  BEGIN
    BLOCK "040E04B0"
    BEGIN
      VALUE "FileDescription", "Vas & Krom - motoros gyorsulasi jatek"
      VALUE "ProductName", "Vas & Krom"
      VALUE "ProductVersion", "${FUSION_VERSION}"
    END
  END
  BLOCK "VarFileInfo"
  BEGIN
    VALUE "Translation", 0x40E, 1200
  END
END
EOF
(cd "$WORK" && x86_64-w64-mingw32-windres res.rc -O coff -o res.o)
x86_64-w64-mingw32-gcc -O2 -municode -mwindows -s -o "$APP/VasEsKrom.exe" "$HERE/launcher.c" "$WORK/res.o"

cat > "$APP/OLVASSEL.txt" <<EOF
Vas & Króm ${FUSION_VERSION} — Windows-változat
=====================================

Indítás: VasEsKrom.exe (a mappát ne szedd szét — a runtime és a game mappa kell mellé).
Telepíteni nem kell; törléshez elég a mappát törölni.
A mentés: %APPDATA%\\VasEsKrom   — a képek gyorsítótára: %LOCALAPPDATA%\\VasEsKrom

Windows 10 vagy 11 (64 bites) kell. Ha a Windows „ismeretlen kiadó” figyelmeztetést ad
(SmartScreen): További információ → Futtatás mindenképp.

Irányítás a versenyen: SZÓKÖZ = gáz (tartsd), JOBB NYÍL / ENTER = kuplung, utána ugyanezzel váltasz.
EOF

if [ -n "${WINE:-}" ]; then
    echo "==> próba Wine alatt (önteszt)"
    (cd "$APP" && WINEDEBUG=-all "$WINE" runtime/python.exe game/fusion_vaskrom.py --selftest) | tail -n 6
fi

echo "==> ZIP"
ZIP="$OUT/VasEsKrom-${FUSION_VERSION}-windows.zip"
rm -f "$ZIP"
(cd "$WORK" && zip -q -r -9 "$ZIP" VasEsKrom)
echo "kész: $ZIP ($(( $(stat -c %s "$ZIP") / 1048576 )) MB)"
