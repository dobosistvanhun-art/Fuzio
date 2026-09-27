# Általános tartalék: bármely PCI grafikus adapter, amelyhez a kernelnek van
# KMS-drivere (pl. QEMU std VGA / bochs-drm), vagy amely a firmware framebufferen marad.
id = generic-kms
name = Általános grafikus adapter (KMS / modesetting)
priority = 90
match.class = 0x0300 0x0302 0x0380
match.vendor = *
match.device = *
display.driver = modesetting
display.server = x11
gl.max = software
vulkan.max = none
