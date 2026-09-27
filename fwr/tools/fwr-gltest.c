/*
 * FusionOS — fwr-gltest: a Fusion Windows Runtime OpenGL-útjának ellenőrzője.
 * Egy rejtett ablakon WGL-környezetet hoz létre (ahogy egy Qt/OpenGL-program,
 * pl. a LightBurn), és kiírja a renderelőt és a verziót. Wine alatt ez a
 * Wine -> EGL/GLX -> Linux GL-driver (NVIDIA 470 / Mesa) utat méri.
 * Kilépési kód: 0 = rendben, 1 = nincs ablak/DC, 2 = nincs pixelformátum,
 *               3 = nincs GL-környezet.
 */
#include <windows.h>
#include <GL/gl.h>
#include <stdio.h>

int main(void)
{
    WNDCLASSA wc = {0};
    PIXELFORMATDESCRIPTOR pfd = {0};
    HWND wnd; HDC dc; HGLRC rc; int pf;

    wc.lpfnWndProc = DefWindowProcA;
    wc.hInstance = GetModuleHandleA(NULL);
    wc.lpszClassName = "fwr-gltest";
    RegisterClassA(&wc);
    wnd = CreateWindowA("fwr-gltest", "fwr-gltest", WS_OVERLAPPEDWINDOW, 0, 0, 64, 64,
                        NULL, NULL, wc.hInstance, NULL);
    if (!wnd || !(dc = GetDC(wnd))) { printf("GL: nincs ablak\n"); return 1; }

    pfd.nSize = sizeof(pfd); pfd.nVersion = 1;
    pfd.dwFlags = PFD_DRAW_TO_WINDOW | PFD_SUPPORT_OPENGL | PFD_DOUBLEBUFFER;
    pfd.iPixelType = PFD_TYPE_RGBA; pfd.cColorBits = 32; pfd.cDepthBits = 24;
    pf = ChoosePixelFormat(dc, &pfd);
    if (!pf || !SetPixelFormat(dc, pf, &pfd)) { printf("GL: nincs pixelformátum\n"); return 2; }
    rc = wglCreateContext(dc);
    if (!rc || !wglMakeCurrent(dc, rc)) { printf("GL: nincs környezet\n"); return 3; }

    printf("GL_VENDOR: %s\n", (const char *)glGetString(GL_VENDOR));
    printf("GL_RENDERER: %s\n", (const char *)glGetString(GL_RENDERER));
    printf("GL_VERSION: %s\n", (const char *)glGetString(GL_VERSION));

    wglMakeCurrent(NULL, NULL); wglDeleteContext(rc);
    ReleaseDC(wnd, dc); DestroyWindow(wnd);
    return 0;
}
