# shellcheck shell=bash
# vdi / vm — fejlesztői VirtualBox-környezet (a Fúzió buildtől független fejlesztői eszköz).

VM_NAME="${FUSION_VM_NAME:-FusionOS-dev}"
VM_CTL="SATA"

_vm_exists()  { VBoxManage showvminfo "$VM_NAME" >/dev/null 2>&1; }
_vm_running() { VBoxManage list runningvms 2>/dev/null | grep -q "^\"$VM_NAME\" "; }

step_vdi() {
    not_root
    local out; out=$(variant_dir)
    local img="$out/fusionos.img" vdi="$out/fusionos-dev.vdi"
    [ -r "$img" ] || die "előbb futtasd: build/fusion-build image"
    step "VDI készítése a lemezképből"
    if have VBoxManage && _vm_exists; then
        _vm_running && die "a(z) $VM_NAME VM fut — előbb állítsd le."
        VBoxManage storageattach "$VM_NAME" --storagectl "$VM_CTL" --port 0 --device 0 --medium none >/dev/null 2>&1 || true
    fi
    if have VBoxManage; then
        VBoxManage closemedium disk "$vdi" --delete >/dev/null 2>&1 || true
    fi
    rm -f "$vdi"
    if have qemu-img; then
        qemu-img convert -f raw -O vdi "$img" "$vdi"
    elif have VBoxManage; then
        VBoxManage convertfromraw "$img" "$vdi" --format VDI >/dev/null
    else
        die "sem qemu-img, sem VBoxManage nem érhető el (build/fusion-build deps)"
    fi
    ok "kész: $vdi ($(du -h "$vdi" | cut -f1))"
}

step_vm() {
    not_root
    need VBoxManage
    local usb=0 a
    for a in "$@"; do [ "$a" = "--usb" ] && usb=1; done
    local out; out=$(variant_dir)
    local vdi="$out/fusionos-dev.vdi" img="$out/fusionos.img"
    # a VDI-t újra kell készíteni, ha hiányzik vagy a lemezkép frissebb
    if [ ! -r "$vdi" ] || { [ -r "$img" ] && [ "$img" -nt "$vdi" ]; }; then
        step_vdi
    fi

    step "VirtualBox VM: $VM_NAME"
    _vm_running && die "a(z) $VM_NAME VM fut — előbb állítsd le."
    if ! _vm_exists; then
        VBoxManage createvm --name "$VM_NAME" --ostype Ubuntu_64 --register >/dev/null
        VBoxManage modifyvm "$VM_NAME" \
            --firmware efi --memory 4096 --cpus 2 \
            --graphicscontroller vmsvga --vram 128 \
            --nic1 nat --rtcuseutc on \
            --boot1 disk --boot2 none --boot3 none --boot4 none >/dev/null
        VBoxManage storagectl "$VM_NAME" --name "$VM_CTL" --add sata --controller IntelAhci --portcount 1 --bootable on >/dev/null
        info "létrehozva (EFI, 4 GB RAM, 2 CPU, VMSVGA)"
    else
        info "már létezik — csak a lemez cserélődik"
    fi
    # soros konzol naplófájlba (hibakereséshez)
    VBoxManage modifyvm "$VM_NAME" --uart1 0x3F8 4 --uartmode1 file "$out/vm-serial.log" >/dev/null 2>&1 || true
    VBoxManage storageattach "$VM_NAME" --storagectl "$VM_CTL" --port 0 --device 0 --medium none >/dev/null 2>&1 || true
    VBoxManage storageattach "$VM_NAME" --storagectl "$VM_CTL" --port 0 --device 0 --type hdd --medium "$vdi" >/dev/null
    ok "lemez csatolva: $vdi"

    if [ "$usb" -eq 1 ]; then
        step "USB-átadás (fejlesztői követelmény: VirtualBox Extension Pack)"
        if ! VBoxManage list extpacks 2>/dev/null | grep -q 'Oracle VirtualBox Extension Pack'; then
            warn "az Extension Pack nincs telepítve — USB 2.0/3.0 átadás nélkül a lézer és a nyomtató nem adható át."
        else
            VBoxManage modifyvm "$VM_NAME" --usbxhci on >/dev/null
            local info_; info_=$(VBoxManage showvminfo "$VM_NAME" --machinereadable 2>/dev/null)
            _filter() {
                local name="$1" vid="$2" pid="$3"
                if printf '%s' "$info_" | grep -q "=\"$name\""; then
                    info "szűrő már megvan: $name"
                else
                    VBoxManage usbfilter add 0 --target "$VM_NAME" --name "$name" --vendorid "$vid" --productid "$pid" >/dev/null
                    info "szűrő hozzáadva: $name ($vid:$pid)"
                fi
            }
            _filter "Fusion: lézer (CH340)" 1a86 7523
            _filter "Fusion: 3D nyomtató (CP2102)" 10c4 ea60
            warn "amíg a VM fut, ezeket az eszközöket a VM kapja meg — a Minten futó Klipper és LightBurn közben nem éri el őket."
        fi
    fi
    ok "indítás: build/fusion-build vm-start   (vagy a VirtualBox felületéről)"
}

step_vm_start() {
    need VBoxManage
    _vm_exists || die "nincs ilyen VM: $VM_NAME — előbb: build/fusion-build vm"
    VBoxManage startvm "$VM_NAME" --type gui
}
