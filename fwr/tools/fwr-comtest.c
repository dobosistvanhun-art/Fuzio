/*
 * FusionOS — fwr-comtest: a Fusion Windows Runtime soros ellenőrzője.
 *   1. kiírja a HKLM\HARDWARE\DEVICEMAP\SERIALCOMM tartalmát (ebből listáznak
 *      a Windows-programok, pl. a LightBurn);
 *   2. megnyitja a megadott COM-portot (alapértelmezés: COM3), 115200 8N1,
 *      és egy azonosító sort ír rá.
 * Kilépési kód: 0 = rendben, 1 = SERIALCOMM hiba, 2 = a port nem nyitható,
 *               3 = beállítási / írási hiba.
 */
#include <windows.h>
#include <stdio.h>
#include <string.h>

int main(int argc, char **argv)
{
    const char *port = argc > 1 ? argv[1] : "COM3";
    const char *line = argc > 2 ? argv[2] : "FUSION-COM-OK\r\n";
    char path[64], name[256], data[256];
    HKEY key;
    DWORD i, nlen, dlen, type, written = 0;
    int found = 0;
    HANDLE h;
    DCB dcb;
    COMMTIMEOUTS to;

    if (RegOpenKeyExA(HKEY_LOCAL_MACHINE, "HARDWARE\\DEVICEMAP\\SERIALCOMM", 0, KEY_READ, &key)) {
        printf("SERIALCOMM: nincs\n");
        return 1;
    }
    printf("SERIALCOMM:");
    for (i = 0; ; i++) {
        nlen = sizeof(name); dlen = sizeof(data);
        if (RegEnumValueA(key, i, name, &nlen, NULL, &type, (BYTE *)data, &dlen)) break;
        printf(" %s", data);
        if (!_stricmp(data, port)) found = 1;
    }
    printf("\n");
    RegCloseKey(key);
    if (!found) { printf("%s: nincs a SERIALCOMM-ban\n", port); return 1; }

    snprintf(path, sizeof(path), "\\\\.\\%s", port);
    h = CreateFileA(path, GENERIC_READ | GENERIC_WRITE, 0, NULL, OPEN_EXISTING, 0, NULL);
    if (h == INVALID_HANDLE_VALUE) { printf("%s: nem nyitható (hiba %lu)\n", port, GetLastError()); return 2; }

    memset(&dcb, 0, sizeof(dcb)); dcb.DCBlength = sizeof(dcb);
    if (!GetCommState(h, &dcb)) { printf("%s: GetCommState hiba %lu\n", port, GetLastError()); return 3; }
    dcb.BaudRate = 115200; dcb.ByteSize = 8; dcb.Parity = NOPARITY; dcb.StopBits = ONESTOPBIT;
    dcb.fDtrControl = DTR_CONTROL_ENABLE; dcb.fRtsControl = RTS_CONTROL_ENABLE;
    if (!SetCommState(h, &dcb)) { printf("%s: SetCommState hiba %lu\n", port, GetLastError()); return 3; }
    memset(&to, 0, sizeof(to)); to.WriteTotalTimeoutConstant = 2000;
    SetCommTimeouts(h, &to);
    if (!WriteFile(h, line, (DWORD)strlen(line), &written, NULL) || written != strlen(line)) {
        printf("%s: írási hiba %lu\n", port, GetLastError()); return 3;
    }
    FlushFileBuffers(h);
    CloseHandle(h);
    printf("%s: megnyitva, 115200 8N1, %lu bájt kiírva\n", port, written);
    return 0;
}
