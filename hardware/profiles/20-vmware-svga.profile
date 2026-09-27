# VMware SVGA II kompatibilis virtuális adapter.
# Ezt az azonosítót adja a VirtualBox VMSVGA és a QEMU "-vga vmware" is.
id = vmware-svga
name = VMware SVGA II kompatibilis virtuális grafika
priority = 20
match.class = 0x0300
match.vendor = 0x15ad
match.device = 0x0405
display.driver = vmwgfx
display.server = x11
display.kernel_modules = vmwgfx
gl.max = software
vulkan.max = none
