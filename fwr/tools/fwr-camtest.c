/*
 * FusionOS — fwr-camtest: a Windows kamera-felsoroló (WinRT) próbája
 *
 * Ugyanazt a hívássort végzi, mint a C++/WinRT-vel írt programok (pl. LightBurn 2.x)
 * induláskor: Windows.Media.Capture.Frames.MediaFrameSourceGroup.FindAllAsync(),
 * majd a lista bejárása. Ha az osztály hiányzik, a valódi program kezeletlen
 * kivétellel leáll — itt ez "CAM: HIBA" sorként látszik.
 *
 * Kimenet (siker): CAM: MediaFrameSourceGroup.FindAllAsync OK, kamerák: N
 * Kilépési kód: 0 = rendben, 1 = hiba.
 *
 * Fordítás: x86_64-w64-mingw32-gcc -O2 -s -o fwr-camtest.exe fwr-camtest.c -lole32
 * (az M4 kísérleti futtató próbája; a futtató: Wine + FusionOS M4 kiegészítés)
 */
#define COBJMACROS
#include <windows.h>
#include <stdio.h>

typedef struct HSTRING__ *HSTRING;
typedef enum { AsyncStarted = 0, AsyncCompleted = 1, AsyncCanceled = 2, AsyncError = 3 } AsyncStatus;

/* a combase.dll WinRT-függvényei (futás közben töltjük be, import-könyvtár nem kell) */
typedef HRESULT (WINAPI *pRoInitialize)(int);
typedef HRESULT (WINAPI *pRoGetActivationFactory)(HSTRING, REFIID, void **);
typedef HRESULT (WINAPI *pWindowsCreateString)(const WCHAR *, UINT32, HSTRING *);
typedef HRESULT (WINAPI *pWindowsDeleteString)(HSTRING);
typedef const WCHAR *(WINAPI *pWindowsGetStringRawBuffer)(HSTRING, UINT32 *);

/* interfész-azonosítók (Windows SDK; a paraméterezettek a WinRT-szabály szerint számolva) */
static const GUID IID_Statics   = {0x1c48bfc5,0x436f,0x4508,{0x94,0xcf,0xd5,0xd8,0xb7,0x32,0x64,0x45}};
static const GUID IID_AsyncInfo = {0x00000036,0x0000,0x0000,{0xc0,0x00,0x00,0x00,0x00,0x00,0x00,0x46}};
static const GUID IID_OpVV      = {0xa795889f,0x6d49,0x5687,{0xaa,0xbe,0xf2,0xfc,0x62,0x37,0xfa,0x1a}};
static const GUID IID_HandlerVV = {0xcff78a64,0xbd44,0x5638,{0xaf,0x2f,0x54,0x0c,0x23,0xb3,0x22,0xe7}};
static const GUID IID_VV        = {0xd01148ae,0xcccd,0x56eb,{0xb2,0xb4,0xa7,0xd2,0xac,0xce,0x14,0xec}};
static const GUID IID_Iterable  = {0xd0b71deb,0x76e8,0x5833,{0x96,0x23,0x2b,0x1e,0x1a,0x8e,0x1b,0x72}};
static const GUID IID_Unknown_  = {0x00000000,0x0000,0x0000,{0xc0,0x00,0x00,0x00,0x00,0x00,0x00,0x46}};
static const GUID IID_DevStatics = {0xc17f100e,0x3a46,0x4a78,{0x80,0x13,0x76,0x9d,0xc9,0xb9,0x73,0x90}};
static const GUID IID_Agile     = {0x94ea2b94,0xe9cc,0x49e0,{0xc0,0xff,0xee,0x64,0xca,0x8f,0x5b,0x90}};

/* nyers vtáblák (IInspectable = IUnknown + 3) */
#define INSPECTABLE_METHODS(T) \
    HRESULT (WINAPI *QueryInterface)(T *, REFIID, void **); \
    ULONG (WINAPI *AddRef)(T *); ULONG (WINAPI *Release)(T *); \
    HRESULT (WINAPI *GetIids)(T *, ULONG *, IID **); \
    HRESULT (WINAPI *GetRuntimeClassName)(T *, HSTRING *); \
    HRESULT (WINAPI *GetTrustLevel)(T *, int *);

typedef struct Statics Statics; typedef struct AsyncOp AsyncOp; typedef struct AsyncInfo AsyncInfo;
typedef struct VecView VecView; typedef struct Iterable Iterable; typedef struct Iterator Iterator;
typedef struct Handler Handler;

struct StaticsVtbl { INSPECTABLE_METHODS(Statics)
    HRESULT (WINAPI *FindAllAsync)(Statics *, AsyncOp **);
    HRESULT (WINAPI *FromIdAsync)(Statics *, HSTRING, AsyncOp **);
    HRESULT (WINAPI *GetDeviceSelector)(Statics *, HSTRING *); };
struct Statics { const struct StaticsVtbl *v; };

struct AsyncOpVtbl { INSPECTABLE_METHODS(AsyncOp)
    HRESULT (WINAPI *put_Completed)(AsyncOp *, Handler *);
    HRESULT (WINAPI *get_Completed)(AsyncOp *, Handler **);
    HRESULT (WINAPI *GetResults)(AsyncOp *, void **); };
struct AsyncOp { const struct AsyncOpVtbl *v; };

struct AsyncInfoVtbl { INSPECTABLE_METHODS(AsyncInfo)
    HRESULT (WINAPI *get_Id)(AsyncInfo *, UINT32 *);
    HRESULT (WINAPI *get_Status)(AsyncInfo *, AsyncStatus *);
    HRESULT (WINAPI *get_ErrorCode)(AsyncInfo *, HRESULT *);
    HRESULT (WINAPI *Cancel)(AsyncInfo *);
    HRESULT (WINAPI *Close)(AsyncInfo *); };
struct AsyncInfo { const struct AsyncInfoVtbl *v; };

struct VecViewVtbl { INSPECTABLE_METHODS(VecView)
    HRESULT (WINAPI *GetAt)(VecView *, UINT32, void **);
    HRESULT (WINAPI *get_Size)(VecView *, UINT32 *);
    HRESULT (WINAPI *IndexOf)(VecView *, void *, UINT32 *, BOOLEAN *);
    HRESULT (WINAPI *GetMany)(VecView *, UINT32, UINT32, void **, UINT32 *); };
struct VecView { const struct VecViewVtbl *v; };

struct IterableVtbl { INSPECTABLE_METHODS(Iterable) HRESULT (WINAPI *First)(Iterable *, Iterator **); };
struct Iterable { const struct IterableVtbl *v; };

struct IteratorVtbl { INSPECTABLE_METHODS(Iterator)
    HRESULT (WINAPI *get_Current)(Iterator *, void **);
    HRESULT (WINAPI *get_HasCurrent)(Iterator *, BOOLEAN *); };
struct Iterator { const struct IteratorVtbl *v; };

/* Windows.Devices.Enumeration: DeviceInformation statikus metódusai és a DeviceWatcher */
typedef struct DevStatics DevStatics; typedef struct Watcher Watcher; typedef struct EvHandler EvHandler;
typedef struct { INT64 value; } EvToken;
struct DevStaticsVtbl { INSPECTABLE_METHODS(DevStatics)
    void *CreateFromIdAsync, *CreateFromIdAsyncAdditionalProperties, *FindAllAsync, *FindAllAsyncDeviceClass,
         *FindAllAsyncAqsFilter, *FindAllAsyncAqsFilterAndAdditionalProperties, *CreateWatcher, *CreateWatcherDeviceClass;
    HRESULT (WINAPI *CreateWatcherAqsFilter)(DevStatics *, HSTRING, Watcher **); };
struct DevStatics { const struct DevStaticsVtbl *v; };
struct WatcherVtbl { INSPECTABLE_METHODS(Watcher)
    HRESULT (WINAPI *add_Added)(Watcher *, EvHandler *, EvToken *);   HRESULT (WINAPI *remove_Added)(Watcher *, EvToken);
    HRESULT (WINAPI *add_Updated)(Watcher *, EvHandler *, EvToken *); HRESULT (WINAPI *remove_Updated)(Watcher *, EvToken);
    HRESULT (WINAPI *add_Removed)(Watcher *, EvHandler *, EvToken *); HRESULT (WINAPI *remove_Removed)(Watcher *, EvToken);
    HRESULT (WINAPI *add_EnumerationCompleted)(Watcher *, EvHandler *, EvToken *); HRESULT (WINAPI *remove_EnumerationCompleted)(Watcher *, EvToken);
    HRESULT (WINAPI *add_Stopped)(Watcher *, EvHandler *, EvToken *); HRESULT (WINAPI *remove_Stopped)(Watcher *, EvToken);
    HRESULT (WINAPI *get_Status)(Watcher *, int *);
    HRESULT (WINAPI *Start)(Watcher *);
    HRESULT (WINAPI *Stop)(Watcher *); };
struct Watcher { const struct WatcherVtbl *v; };

/* esemény-kezelő (TypedEventHandler): IUnknown + Invoke(sender, args); a próbában minden IID-t elfogad */
struct EvHandlerVtbl {
    HRESULT (WINAPI *QueryInterface)(EvHandler *, REFIID, void **);
    ULONG (WINAPI *AddRef)(EvHandler *); ULONG (WINAPI *Release)(EvHandler *);
    HRESULT (WINAPI *Invoke)(EvHandler *, IUnknown *, IUnknown *); };
struct EvHandler { const struct EvHandlerVtbl *v; HANDLE event; LONG ref; LONG calls; };
static HRESULT WINAPI e_qi(EvHandler *h, REFIID iid, void **out) { (void)iid; *out = h; InterlockedIncrement(&h->ref); return S_OK; }
static ULONG WINAPI e_addref(EvHandler *h) { return InterlockedIncrement(&h->ref); }
static ULONG WINAPI e_release(EvHandler *h) { return InterlockedDecrement(&h->ref); }
static HRESULT WINAPI e_invoke(EvHandler *h, IUnknown *s, IUnknown *a) { (void)s; (void)a; InterlockedIncrement(&h->calls); if (h->event) SetEvent(h->event); return S_OK; }
static const struct EvHandlerVtbl evhandler_vtbl = { e_qi, e_addref, e_release, e_invoke };

/* befejezés-kezelő (delegate): IUnknown + Invoke */
struct HandlerVtbl {
    HRESULT (WINAPI *QueryInterface)(Handler *, REFIID, void **);
    ULONG (WINAPI *AddRef)(Handler *); ULONG (WINAPI *Release)(Handler *);
    HRESULT (WINAPI *Invoke)(Handler *, AsyncOp *, AsyncStatus); };
struct Handler { const struct HandlerVtbl *v; HANDLE event; LONG ref; };

static HRESULT WINAPI h_qi(Handler *h, REFIID iid, void **out)
{
    if (IsEqualGUID(iid, &IID_Unknown_) || IsEqualGUID(iid, &IID_HandlerVV) || IsEqualGUID(iid, &IID_Agile))
    { *out = h; InterlockedIncrement(&h->ref); return S_OK; }
    *out = NULL; return E_NOINTERFACE;
}
static ULONG WINAPI h_addref(Handler *h) { return InterlockedIncrement(&h->ref); }
static ULONG WINAPI h_release(Handler *h) { return InterlockedDecrement(&h->ref); }
static HRESULT WINAPI h_invoke(Handler *h, AsyncOp *op, AsyncStatus st) { (void)op; (void)st; SetEvent(h->event); return S_OK; }
static const struct HandlerVtbl handler_vtbl = { h_qi, h_addref, h_release, h_invoke };

#define FAIL(...) do { printf("CAM: HIBA: " __VA_ARGS__); printf("\n"); return 1; } while (0)

int main(void)
{
    static const WCHAR cls[] = L"Windows.Media.Capture.Frames.MediaFrameSourceGroup";
    HMODULE combase = LoadLibraryW(L"combase.dll");
    pRoInitialize RoInit; pRoGetActivationFactory RoGetAF; pWindowsCreateString WCreate;
    pWindowsDeleteString WDelete; pWindowsGetStringRawBuffer WRaw;
    HSTRING name = NULL, sel = NULL;
    Statics *statics = NULL; AsyncOp *op = NULL, *op2 = NULL; AsyncInfo *info = NULL;
    VecView *view = NULL; Iterable *iterable = NULL; Iterator *it = NULL; void *group = (void *)1;
    AsyncStatus st = AsyncStarted; UINT32 size = 0; BOOLEAN has = TRUE; HRESULT hr;
    Handler handler = { &handler_vtbl, NULL, 1 };

    if (!combase) FAIL("combase.dll nem tölthető be");
    RoInit  = (pRoInitialize)GetProcAddress(combase, "RoInitialize");
    RoGetAF = (pRoGetActivationFactory)GetProcAddress(combase, "RoGetActivationFactory");
    WCreate = (pWindowsCreateString)GetProcAddress(combase, "WindowsCreateString");
    WDelete = (pWindowsDeleteString)GetProcAddress(combase, "WindowsDeleteString");
    WRaw    = (pWindowsGetStringRawBuffer)GetProcAddress(combase, "WindowsGetStringRawBuffer");
    if (!RoInit || !RoGetAF || !WCreate || !WDelete || !WRaw) FAIL("hiányzó WinRT-függvény a combase-ben");

    RoInit(1 /* RO_INIT_MULTITHREADED — a C++/WinRT alapértéke */);
    WCreate(cls, lstrlenW(cls), &name);

    hr = RoGetAF(name, &IID_Statics, (void **)&statics);
    if (FAILED(hr)) FAIL("RoGetActivationFactory 0x%08lx (az osztály nincs meg: a LightBurn 2.x itt leáll)", hr);

    hr = statics->v->FindAllAsync(statics, &op);
    if (FAILED(hr) || !op) FAIL("FindAllAsync 0x%08lx", hr);

    /* a C++/WinRT .get() útja: IAsyncInfo.Status, ha kell, Completed-kezelő és várakozás */
    hr = op->v->QueryInterface(op, &IID_AsyncInfo, (void **)&info);
    if (FAILED(hr)) FAIL("IAsyncInfo QI 0x%08lx", hr);
    info->v->get_Status(info, &st);
    if (st == AsyncStarted)
    {
        handler.event = CreateEventW(NULL, TRUE, FALSE, NULL);
        hr = op->v->put_Completed(op, &handler);
        if (FAILED(hr)) FAIL("put_Completed 0x%08lx", hr);
        if (WaitForSingleObject(handler.event, 5000) != WAIT_OBJECT_0) FAIL("FindAllAsync nem fejeződött be 5 s alatt");
        info->v->get_Status(info, &st);
    }
    if (st != AsyncCompleted) FAIL("FindAllAsync állapot: %d", (int)st);

    /* a típusos felület: IAsyncOperation<IVectorView<MediaFrameSourceGroup>> */
    {
        AsyncOp *typed = NULL;
        hr = op->v->QueryInterface(op, &IID_OpVV, (void **)&typed);
        if (FAILED(hr)) FAIL("IAsyncOperation<IVectorView<MediaFrameSourceGroup>> QI 0x%08lx", hr);
        typed->v->Release(typed);
    }

    hr = op->v->GetResults(op, (void **)&view);
    if (FAILED(hr) || !view) FAIL("GetResults 0x%08lx", hr);
    {
        VecView *typedv = NULL;
        hr = view->v->QueryInterface(view, &IID_VV, (void **)&typedv);
        if (FAILED(hr)) FAIL("IVectorView<MediaFrameSourceGroup> QI 0x%08lx", hr);
        typedv->v->Release(typedv);
    }
    hr = view->v->get_Size(view, &size);
    if (FAILED(hr)) FAIL("IVectorView.Size 0x%08lx", hr);

    /* bejárás (range-for): IIterable<MediaFrameSourceGroup>.First, HasCurrent */
    hr = view->v->QueryInterface(view, &IID_Iterable, (void **)&iterable);
    if (FAILED(hr)) FAIL("IIterable<MediaFrameSourceGroup> QI 0x%08lx", hr);
    hr = iterable->v->First(iterable, &it);
    if (FAILED(hr) || !it) FAIL("IIterable.First 0x%08lx", hr);
    it->v->get_HasCurrent(it, &has);
    if (size == 0 && has) FAIL("üres listán HasCurrent = igaz");

    /* a többi statikus metódus */
    hr = statics->v->GetDeviceSelector(statics, &sel);
    if (FAILED(hr)) FAIL("GetDeviceSelector 0x%08lx", hr);
    hr = statics->v->FromIdAsync(statics, name, &op2);
    if (FAILED(hr) || !op2) FAIL("FromIdAsync 0x%08lx", hr);
    hr = op2->v->GetResults(op2, &group);
    if (FAILED(hr)) FAIL("FromIdAsync.GetResults 0x%08lx", hr);

    /* kamerafigyelő, ahogy a LightBurn 2.x használja: DeviceInformation.CreateWatcher(kamera-szelektor),
       feliratkozás mind a négy eseményre, Start, EnumerationCompleted, Stop, leiratkozás */
    {
        static const WCHAR dcls[] = L"Windows.Devices.Enumeration.DeviceInformation";
        HSTRING dname = NULL; DevStatics *ds = NULL; Watcher *w = NULL;
        EvHandler added = { &evhandler_vtbl, NULL, 1, 0 }, updated = { &evhandler_vtbl, NULL, 1, 0 };
        EvHandler removed = { &evhandler_vtbl, NULL, 1, 0 }, done = { &evhandler_vtbl, NULL, 1, 0 };
        EvToken t1, t2, t3, t4;

        WCreate(dcls, lstrlenW(dcls), &dname);
        hr = RoGetAF(dname, &IID_DevStatics, (void **)&ds);
        if (FAILED(hr)) FAIL("DeviceInformation RoGetActivationFactory 0x%08lx", hr);
        hr = ds->v->CreateWatcherAqsFilter(ds, sel, &w);
        if (FAILED(hr) || !w) FAIL("DeviceInformation.CreateWatcher 0x%08lx", hr);
        if (FAILED(hr = w->v->add_Added(w, &added, &t1))) FAIL("DeviceWatcher.Added 0x%08lx", hr);
        if (FAILED(hr = w->v->add_Updated(w, &updated, &t2))) FAIL("DeviceWatcher.Updated 0x%08lx", hr);
        if (FAILED(hr = w->v->add_Removed(w, &removed, &t3))) FAIL("DeviceWatcher.Removed 0x%08lx (a LightBurn 2.x itt leáll)", hr);
        done.event = CreateEventW(NULL, TRUE, FALSE, NULL);
        if (FAILED(hr = w->v->add_EnumerationCompleted(w, &done, &t4))) FAIL("DeviceWatcher.EnumerationCompleted 0x%08lx", hr);
        if (FAILED(hr = w->v->Start(w))) FAIL("DeviceWatcher.Start 0x%08lx", hr);
        if (WaitForSingleObject(done.event, 10000) != WAIT_OBJECT_0) FAIL("DeviceWatcher: nincs EnumerationCompleted 10 s alatt");
        w->v->Stop(w);
        if (FAILED(hr = w->v->remove_Added(w, t1)) || FAILED(hr = w->v->remove_Updated(w, t2)) ||
            FAILED(hr = w->v->remove_Removed(w, t3)) || FAILED(hr = w->v->remove_EnumerationCompleted(w, t4)))
            FAIL("DeviceWatcher leiratkozás 0x%08lx", hr);
        printf("CAM: DeviceWatcher OK (kamerák: %ld)\n", added.calls);
        w->v->Release(w); ds->v->Release(ds); WDelete(dname);
    }

    printf("CAM: MediaFrameSourceGroup.FindAllAsync OK, kamerák: %u\n", size);
    printf("CAM: FromIdAsync OK (%s), GetDeviceSelector OK\n", group ? "eszköz" : "nincs ilyen eszköz");

    if (group) ((IUnknown *)group)->lpVtbl->Release((IUnknown *)group);
    op2->v->Release(op2); WDelete(sel);
    it->v->Release(it); iterable->v->Release(iterable); view->v->Release(view);
    info->v->Release(info); op->v->Release(op); statics->v->Release(statics);
    WDelete(name);
    return 0;
}
