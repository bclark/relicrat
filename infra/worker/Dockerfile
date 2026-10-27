# QEMU runs a separate guest kernel; this container has no host Docker socket.
FROM debian:12-slim
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl cloud-image-utils qemu-system-x86 qemu-utils \
    && rm -rf /var/lib/apt/lists/*
COPY start-vm.sh /usr/local/bin/start-vm
ENTRYPOINT ["sh", "/usr/local/bin/start-vm"]
