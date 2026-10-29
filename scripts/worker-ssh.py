"""Two ordinary SSH sessions; does not require NAS TCP forwarding or an agent."""
import os
import shlex
import sys

# QEMU sees loopback connections as its own gateway, avoiding return-route
# collisions when guest Docker allocates the NAS container's source subnet.
RELAY = """import os, select, socket, sys
with socket.create_connection(('127.0.0.1', int(sys.argv[1])), timeout=10) as connection:
    connection.settimeout(None)
    readers = [0, connection]
    while True:
        ready, _, _ = select.select(readers, [], [])
        for source in ready:
            if source == 0:
                data = os.read(0, 65536)
                if data:
                    connection.sendall(data)
                else:
                    connection.shutdown(socket.SHUT_WR)
                    readers.remove(0)
            else:
                data = connection.recv(65536)
                if not data:
                    sys.exit(0)
                sys.stdout.buffer.write(data)
                sys.stdout.buffer.flush()
"""


def main():
    interactive = not sys.argv[1:]
    tty = '-tt' if interactive else '-T'
    remote = '/home/bclark/relicrat-worker'
    proxy = shlex.join(['docker', 'exec', '-i', 'relicrat-worker-vm-1',
                        'python3', '-c', RELAY, '2222'])
    inner = ['ssh', tty, '-o', 'BatchMode=yes', '-o', 'ForwardAgent=no',
             '-o', 'IdentitiesOnly=yes', '-o', 'StrictHostKeyChecking=accept-new',
             '-o', 'ConnectTimeout=10', '-o', f'UserKnownHostsFile={remote}/known_hosts',
             '-o', 'HostKeyAlias=relicrat-worker', '-i', remote + '/operator_ed25519',
             '-o', 'ProxyCommand=' + proxy,
             '-p', '22222', 'worker@127.0.0.1', *sys.argv[1:]]
    os.execvp('ssh', ['ssh', tty, '-o', 'BatchMode=yes', '-o', 'ForwardAgent=no',
                     '-o', 'StrictHostKeyChecking=yes', '-o', 'ConnectTimeout=10',
                     'technodrome', shlex.join(inner)])


if __name__ == '__main__':
    main()
