# NVIDIA Kepler GPU-k a 470-es legacy driverrel.
# Új Kepler kártya támogatása: az eszközazonosítót a match.device listához kell adni.
#   0x0ff6  Quadro K1100M (GK107GLM) — HP ZBook 15 G2
id = nvidia-kepler-470
name = NVIDIA Kepler (470 legacy driver)
priority = 10
match.class = 0x0300 0x0302
match.vendor = 0x10de
match.device = 0x0ff6
display.driver = nvidia-470
display.server = x11
display.kernel_modules = nvidia nvidia-modeset nvidia-drm
gl.max = 4.6
vulkan.max = 1.2
requires_sole_adapter = yes
hint.multi_adapter = Több grafikus adapter látható. Ehhez a profilhoz a BIOS-ban ki kell kapcsolni a Hybrid Graphics opciót (diszkrét mód).
