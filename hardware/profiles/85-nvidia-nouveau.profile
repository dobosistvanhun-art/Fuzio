# NVIDIA — nyílt forrású Nouveau driver (mérési / tartalék út, 0.0.30).
# Automatikusan nem választódik: a Keplerre a 10-es (470) profil nyer; a ZBookon a boot menü
# „mérés: Nouveau” bejegyzése kéri kézzel (fusion.display.profile=nvidia-nouveau).
# Keplernél órajel-állítás (reclocking) nélkül a teljesítmény töredék — a mérés éppen ezt nézi.
id = nvidia-nouveau
name = NVIDIA (Nouveau, nyílt forrású driver)
priority = 85
match.class = 0x0300 0x0302
match.vendor = 0x10de
match.device = *
display.driver = nouveau
display.server = x11
display.kernel_modules = nouveau
display.xorg_driver = modesetting
gl.max = mesa
vulkan.max = none
