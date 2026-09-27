# VirtualBox VBoxVGA / VBoxSVGA virtuális adapter.
id = virtualbox-vga
name = VirtualBox VBoxVGA/VBoxSVGA virtuális grafika
priority = 21
match.class = 0x0300
match.vendor = 0x80ee
match.device = 0xbeef
display.driver = vboxvideo
display.server = x11
display.kernel_modules = vboxvideo
gl.max = software
vulkan.max = none
display.xorg_driver = modesetting
