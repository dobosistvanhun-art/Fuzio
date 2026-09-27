# Utolsó tartalék: nincs PCI grafikus adapter vagy nem illeszkedik profil —
# a firmware (UEFI GOP) által átadott framebuffer marad.
id = firmware-fb
name = Firmware framebuffer (UEFI GOP / simpledrm)
priority = 99
match.kind = firmware
display.driver = simpledrm
display.server = none
gl.max = none
vulkan.max = none
