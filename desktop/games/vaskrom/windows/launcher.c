/* Vas & Króm — Windows-indító: a mellette lévő runtime\pythonw.exe-vel elindítja a game\fusion_vaskrom.py-t */
#include <windows.h>
#include <wchar.h>

int WINAPI wWinMain(HINSTANCE h, HINSTANCE p, PWSTR cmd, int show) {
    wchar_t dir[MAX_PATH], py[MAX_PATH], line[3 * MAX_PATH];
    DWORD n = GetModuleFileNameW(NULL, dir, MAX_PATH);
    if (n == 0 || n >= MAX_PATH) return 1;
    wchar_t *s = wcsrchr(dir, L'\\');
    if (s) *s = 0;
    _snwprintf(py, MAX_PATH, L"%ls\\runtime\\pythonw.exe", dir);
    _snwprintf(line, 3 * MAX_PATH, L"\"%ls\" \"%ls\\game\\fusion_vaskrom.py\" %ls", py, dir, cmd ? cmd : L"");
    STARTUPINFOW si = { sizeof(si) };
    PROCESS_INFORMATION pi;
    if (!CreateProcessW(py, line, NULL, NULL, FALSE, 0, NULL, dir, &si, &pi)) {
        MessageBoxW(NULL, L"A játék nem indul: hiányzik a runtime mappa (pythonw.exe). Csomagold ki a teljes ZIP-et.",
                    L"Vas & Króm", MB_ICONERROR);
        return 1;
    }
    CloseHandle(pi.hThread);
    CloseHandle(pi.hProcess);
    return 0;
}
