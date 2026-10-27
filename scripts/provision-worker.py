"""Provision the dedicated VM on Technodrome; never transfers a private SSH key."""
from pathlib import Path
import io
import shlex
import subprocess
import tarfile


def main():
    root = Path(__file__).resolve().parent.parent
    ssh = ['ssh', '-T', '-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=yes',
           '-o', 'ConnectTimeout=10', 'technodrome']
    remote = '/home/bclark/relicrat-worker'
    subprocess.run(ssh + [f'set -eu; mkdir -p {remote}; chmod 700 {remote}; '
                          f'if [ ! -f {remote}/operator_ed25519 ]; then '
                          f'ssh-keygen -q -t ed25519 -N "" -C relicrat-worker-operator '
                          f'-f {remote}/operator_ed25519; fi'], check=True)
    public = subprocess.check_output(ssh + [f'cat {remote}/operator_ed25519.pub'], text=True).strip()
    with io.BytesIO() as data:
        with tarfile.open(fileobj=data, mode='w') as archive:
            for name in ('.dockerignore', 'Dockerfile', 'compose.yaml', 'start-vm.sh'):
                archive.add(root / 'infra/worker' / name, arcname=name)
            template = (root / 'infra/worker/user-data.yaml.template').read_text()
            rendered = template.replace('@@OPERATOR_SSH_KEY@@', public).encode()
            entry = tarfile.TarInfo('user-data.yaml')
            entry.size = len(rendered)
            entry.mode = 0o600
            archive.addfile(entry, io.BytesIO(rendered))
        data.seek(0)
        subprocess.run(ssh + [f'mkdir -p {remote} && chmod 700 {remote}'], check=True)
        subprocess.run(ssh + [f'tar -xf - -C {remote}'], input=data.read(), check=True)
    command = shlex.join(['docker', 'compose', '--project-name', 'relicrat-worker',
                          '--file', remote + '/compose.yaml', 'up', '--build', '--detach'])
    subprocess.run(ssh + [command], check=True)
    print('VM starting. Connect with: sh scripts/worker-ssh.sh')


if __name__ == '__main__':
    main()
