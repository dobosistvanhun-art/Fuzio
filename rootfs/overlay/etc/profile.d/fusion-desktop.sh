# Fúzió — a Fúzió Desktop indítása a tty1-es belépés után.
# Kikapcsolás egy indításra: a boot menüben (e) a parancssor végére: fusion.desktop=0
if [ "$(tty 2>/dev/null)" = /dev/tty1 ] && [ -z "${DISPLAY:-}" ] && [ "$(id -u)" -ne 0 ] \
   && ! grep -qw 'fusion.desktop=0' /proc/cmdline 2>/dev/null; then
    /usr/lib/fusion/bin/fusion-session
    echo
    echo "  A Fúzió Desktop leállt. Újraindítás: fusion-session"
    echo "  Napló: ~/.local/share/fusion/session.log"
    echo
fi
