# FusionOS 0.0.32 (j3) — a felület rajzolása választható + két naplóhiba

A mérések (0.0.31, ZBook, 2026-10-08) alapján: a szoftveres rajzolás ~95 MB-ot spórol (Fusion Shell + Beállítások),
lassulás nem volt érezhető. Végleges döntés előtt néhány nap napi használat — ezért most kapcsoló lett belőle.

| | |
| --- | --- |
| Beállítások → Kijelző → **Felület rajzolása** | „Grafikus kártya” (OpenGL — az alapértelmezés, mint eddig) vagy „Szoftveres”. Váltáskor a panel és az asztal azonnal újraindul az új móddal; a többi Fusion-program a következő megnyitáskor. A LightBurnt, a Firefoxot és a többi programot nem érinti. A mérési boot-bejegyzés („Fusion meres - szoftveres felulet”) továbbra is felülírja. |
| Hibajelentés | új sor a fejlécben: „Felület: …” |
| Xorg | „(EE) NVIDIA(GPU-1): Failed to initialize the NVIDIA graphics device” — az Xorg a kiválasztott kártyát még egyszer, második „GPU-képernyőként” is fel akarta venni. A Hardware Layer most kikapcsolja ezt (`AutoAddGPU false`): csak a profil által kiválasztott adapter fut. |
| Napló | „PAM unable to dlopen(pam_lastlog.so)” minden belépéskor — a sor kikerült a login PAM-beállításából. |

## Frissítés

Minten (~/Fusion): `fusionos-j3.tar.gz` kibontása, `build/fusion-build all`, majd a `.fupd` → Beállítások →
Rendszerfrissítés.

## Kipróbálás

1. Beállítások → Kijelző → Felület rajzolása → **Szoftveres** → a panel és az asztal pár mp alatt újraindul.
2. Pár nap használat; ha bármi lassabbnak tűnik, ugyanitt vissza „Grafikus kártya”.
3. Egy hibajelentés: a fejlécben „Felület: szoftveres”, a memóriarészben a fusion_shell ~80 MB; az Xorg-részben
   nincs „NVIDIA(GPU-1)” hiba, a naplóban nincs pam_lastlog.
