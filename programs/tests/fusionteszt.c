/* Fúzió — FusionTeszt: a Fúzió Programkezelő Windows-telepítési próbája (a QEMU-tesztben)
 *
 *   fusionteszt-setup.exe   telepítőként: C:\Program Files\FusionTeszt\fusionteszt.exe +
 *                           Start menü parancsikonok (FusionTeszt, Uninstall FusionTeszt) — mint egy
 *                           valódi telepítő (IShellLink); a Programkezelő ezekből ismeri fel a programot
 *   fusionteszt.exe [fájl]  programként: a parancssort a C:\users\Public\fusionteszt-args.txt-be írja,
 *                           és megnyit egy „FusionTeszt” ablakot 20 mp-re
 *
 * Fordítás: tools/build-fusionteszt.sh (mingw-w64; az eredmény a tárolóban van, a Wine-buildtől független)
 */
#include <windows.h>
#include <shlobj.h>
#include <objbase.h>
#include <stdio.h>
#include <wchar.h>

static int make_link(const wchar_t *lnk, const wchar_t *target, const wchar_t *args)
{
    IShellLinkW *sl; IPersistFile *pf; HRESULT hr;
    hr = CoCreateInstance(&CLSID_ShellLink, NULL, CLSCTX_INPROC_SERVER, &IID_IShellLinkW, (void **)&sl);
    if (FAILED(hr)) return 0;
    sl->lpVtbl->SetPath(sl, target);
    if (args) sl->lpVtbl->SetArguments(sl, args);
    hr = sl->lpVtbl->QueryInterface(sl, &IID_IPersistFile, (void **)&pf);
    if (SUCCEEDED(hr)) { hr = pf->lpVtbl->Save(pf, lnk, TRUE); pf->lpVtbl->Release(pf); }
    sl->lpVtbl->Release(sl);
    return SUCCEEDED(hr);
}

static LRESULT CALLBACK wndproc(HWND w, UINT m, WPARAM wp, LPARAM lp)
{
    if (m == WM_TIMER || m == WM_CLOSE) { DestroyWindow(w); return 0; }
    if (m == WM_DESTROY) { PostQuitMessage(0); return 0; }
    return DefWindowProcW(w, m, wp, lp);
}

int WINAPI wWinMain(HINSTANCE inst, HINSTANCE prev, PWSTR cmd, int show)
{
    wchar_t self[MAX_PATH], low[MAX_PATH], *base;
    GetModuleFileNameW(NULL, self, MAX_PATH);
    base = wcsrchr(self, L'\\'); base = base ? base + 1 : self;
    wcsncpy(low, base, MAX_PATH - 1); low[MAX_PATH - 1] = 0; _wcslwr(low);
    (void)prev;

    if (wcsstr(low, L"setup")) {
        wchar_t pfd[MAX_PATH], dir[MAX_PATH], dst[MAX_PATH], progs[MAX_PATH], lnk[MAX_PATH];
        if (FAILED(SHGetFolderPathW(NULL, CSIDL_PROGRAM_FILES, NULL, 0, pfd))) return 2;
        swprintf(dir, MAX_PATH, L"%ls\\FusionTeszt", pfd); CreateDirectoryW(dir, NULL);
        swprintf(dst, MAX_PATH, L"%ls\\fusionteszt.exe", dir);
        if (!CopyFileW(self, dst, FALSE)) return 3;
        CoInitialize(NULL);
        if (FAILED(SHGetFolderPathW(NULL, CSIDL_COMMON_PROGRAMS, NULL, 0, progs))) return 4;
        swprintf(lnk, MAX_PATH, L"%ls\\FusionTeszt", progs); CreateDirectoryW(lnk, NULL);
        swprintf(lnk, MAX_PATH, L"%ls\\FusionTeszt\\FusionTeszt.lnk", progs);
        if (!make_link(lnk, dst, NULL)) return 5;
        swprintf(lnk, MAX_PATH, L"%ls\\FusionTeszt\\Uninstall FusionTeszt.lnk", progs);
        make_link(lnk, dst, L"/uninstall");
        CoUninitialize();
        return 0;
    }

    FILE *f = _wfopen(L"C:\\users\\Public\\fusionteszt-args.txt", L"w");
    if (f) { fwprintf(f, L"%ls\n", cmd ? cmd : L""); fclose(f); }
    WNDCLASSW wc = {0};
    wc.lpfnWndProc = wndproc; wc.hInstance = inst; wc.lpszClassName = L"FusionTesztWnd";
    wc.hbrBackground = (HBRUSH)(COLOR_WINDOW + 1);
    wc.hIcon = LoadIconW(inst, MAKEINTRESOURCEW(1));
    RegisterClassW(&wc);
    HWND w = CreateWindowW(L"FusionTesztWnd", L"FusionTeszt", WS_OVERLAPPEDWINDOW, 100, 100, 420, 240, NULL, NULL, inst, NULL);
    ShowWindow(w, show ? show : SW_SHOW);
    SetTimer(w, 1, 20000, NULL);
    MSG msg;
    while (GetMessageW(&msg, NULL, 0, 0) > 0) { TranslateMessage(&msg); DispatchMessageW(&msg); }
    return 0;
}
