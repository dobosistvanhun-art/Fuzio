#!/bin/sh
# FusionOS — a Programkezelő Windows-tesztprogramjának fordítása (mingw-w64 kell: gcc-mingw-w64-x86-64)
# Az eredmény (programs/tests/fusionteszt-setup.exe) a tárolóban van; csak a forrás változásakor kell.
set -e
cd "$(dirname "$0")/../programs/tests"
x86_64-w64-mingw32-windres fusionteszt.rc -O coff -o fusionteszt.res
x86_64-w64-mingw32-gcc -O2 -s -municode -mwindows -o fusionteszt-setup.exe fusionteszt.c fusionteszt.res -lole32 -luuid -lshell32
rm -f fusionteszt.res
ls -la fusionteszt-setup.exe
