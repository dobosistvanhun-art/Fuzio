# Intel integrált grafika (i915 KMS).
id = intel-kms
name = Intel integrált grafika (i915)
priority = 50
match.class = 0x0300 0x0380
match.vendor = 0x8086
match.device = *
display.driver = i915
display.server = x11
display.kernel_modules = i915
gl.max = mesa
vulkan.max = mesa
display.xorg_driver = modesetting
