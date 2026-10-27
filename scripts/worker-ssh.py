"""Two ordinary SSH sessions; does not require NAS TCP forwarding or an agent."""
import os
import shlex
import sys

interactive = not sys.argv[1:]
tty = '-tt' if interactive else '-T'
remote = '/home/bclark/relicrat-worker'
inner = ['ssh', tty, '-o', 'BatchMode=yes', '-o', 'ForwardAgent=no',
         '-o', 'IdentitiesOnly=yes', '-o', 'StrictHostKeyChecking=accept-new',
         '-o', 'ConnectTimeout=10', '-o', f'UserKnownHostsFile={remote}/known_hosts',
         '-o', 'HostKeyAlias=relicrat-worker', '-i', remote + '/operator_ed25519',
         '-p', '22222', 'worker@127.0.0.1', *sys.argv[1:]]
os.execvp('ssh', ['ssh', tty, '-o', 'BatchMode=yes', '-o', 'ForwardAgent=no',
                 '-o', 'StrictHostKeyChecking=yes', '-o', 'ConnectTimeout=10',
                 'technodrome', shlex.join(inner)])
