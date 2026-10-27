#!/bin/sh
set -eu
cd /data
if [ ! -f worker.qcow2 ]; then
    # The checksum pins the Ubuntu 24.04 image reviewed during provisioning.
    curl --fail --location --retry 3 --output base.img.part \
        https://cloud-images.ubuntu.com/noble/current/noble-server-cloudimg-amd64.img
    echo '04e8f2461a16a44e78a370284471f29616cdd9baf1893df25807b71f985b6c94  base.img.part' | sha256sum --check
    qemu-img convert -O qcow2 base.img.part worker.qcow2.part
    qemu-img resize worker.qcow2.part 40G
    printf 'instance-id: relicrat-worker-v1\nlocal-hostname: relicrat-worker\n' > meta-data
    cloud-localds seed.img /bootstrap/user-data.yaml meta-data
    mv worker.qcow2.part worker.qcow2
    rm base.img.part
fi
exec qemu-system-x86_64 \
    -name relicrat-worker -machine q35,accel=kvm -cpu host -smp 2 -m 4096 \
    -nographic -monitor none \
    -drive if=virtio,format=qcow2,file=worker.qcow2 \
    -drive if=virtio,format=raw,file=seed.img,readonly=on \
    -netdev user,id=net0,hostfwd=tcp:0.0.0.0:2222-:22 \
    -device virtio-net-pci,netdev=net0
