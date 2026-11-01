"""Disposable worker-only integration for the actual operator backup commands."""
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import secrets
import shlex
import subprocess
import sys
import tarfile
import tempfile

from backup import DOCKER, require, run, output

ROOT = Path(__file__).resolve().parent.parent


def main():
    require(len(sys.argv) == 1, 'This test accepts no target or data')
    require(output(DOCKER + ['info', '--format', '{{.Name}}']) == 'relicrat-worker', 'Dedicated worker required')
    with tempfile.TemporaryDirectory(prefix='relicrat-operator-test-') as temporary:
        folder = Path(temporary)
        project = 'relicrat-operator-test-' + secrets.token_hex(8)
        os.environ['BUILDX_CONFIG'] = str(folder / 'buildx')
        (folder / 'buildx').mkdir()
        evidence = folder / 'evidence'
        evidence.mkdir()
        config = {'services': {
            'db': {'image': 'postgres:17-alpine', 'environment': {
                'POSTGRES_DB': 'relicrat_recovery', 'POSTGRES_USER': 'relicrat_recovery',
                'POSTGRES_PASSWORD': 'disposable-recovery-only'},
                'volumes': ['database:/var/lib/postgresql/data'],
                'healthcheck': {'test': ['CMD-SHELL', 'pg_isready -U relicrat_recovery -d relicrat_recovery'],
                                'interval': '2s', 'timeout': '5s', 'retries': 30}},
            'api': {'env_file': [str(ROOT/'infra/docker/owner-test.env')], 'build': {'context': str(ROOT / 'apps/api')}, 'environment': {
                'DATABASE_URL': 'postgresql+psycopg://relicrat_recovery:disposable-recovery-only@db:5432/relicrat_recovery',
                'MEDIA_ROOT': '/media', 'PYTHONPATH': '/app'},
                'volumes': ['media:/media', f'{evidence}:/evidence',
                            f'{ROOT}/scripts/backup-restore.py:/rehearsal/backup-restore.py:ro']}},
            'volumes': {'database': {}, 'media': {}}, 'networks': {'default': {'internal': True}}}
        compose_file = folder / 'compose.json'
        compose_file.write_text(json.dumps(config))
        compose = DOCKER + ['compose', '-p', project, '-f', str(compose_file)]
        tool = [sys.executable, str(ROOT / 'scripts/backup.py')]
        creates = tool + ['create', '--compose', str(compose_file), '--project', project, '--offline-confirmed']
        print(f'Operator test project: {project}', flush=True)
        try:
            run(compose + ['build', 'api'])
            run(compose + ['up', '-d', '--wait', 'db'])
            run(compose + ['run', '--rm', '--no-deps', 'api', 'alembic', 'upgrade', 'head'])
            run(compose + ['run', '--rm', '--no-deps', 'api', 'python', '/rehearsal/backup-restore.py', 'seed'])
            run(compose + ['up', '-d', 'api'])
            # Preserve an unreferenced hard-linked regular file too; backup must
            # store independent bytes rather than an unrestorable tar hardlink.
            run(compose + ['run', '--rm', '--no-deps', 'api', 'python', '-c',
                "import json,pathlib,os; key=json.loads(pathlib.Path('/evidence/manifest.json').read_text())['storage_key']; os.link(pathlib.Path('/media')/key, '/media/retained-orphan.png')"])
            # Corrupt source media: capture must fail closed and restart the app.
            run(compose + ['run', '--rm', '--no-deps', 'api', 'python', '/rehearsal/backup-restore.py', 'corrupt'])
            failure = subprocess.run(creates + [str(folder / 'failed-backup')])
            require(failure.returncode != 0 and (folder / 'failed-backup/INCOMPLETE').exists(), 'Failed capture was accepted')
            require(output(compose + ['ps', '-q', '--status', 'running', 'api']), 'Failed capture left app stopped')
            run(compose + ['run', '--rm', '--no-deps', 'api', 'python', '-c',
                "import json,pathlib; p=pathlib.Path('/evidence'); key=json.loads((p/'manifest.json').read_text())['storage_key']; (pathlib.Path('/media')/key).write_bytes((p/'original.png').read_bytes())"])
            bundle = folder / 'backup'
            run(creates + [str(bundle)])
            require(output(compose + ['ps', '-q', '--status', 'running', 'api']), 'Successful backup left app stopped')
            require(bundle.stat().st_mode & 0o077 == 0, 'Backup directory is not private')
            # Existing destination must be refused without modifying the backup.
            before = (bundle / 'manifest.json').read_bytes()
            require(subprocess.run(creates + [str(bundle)]).returncode != 0, 'Existing backup overwritten')
            require((bundle / 'manifest.json').read_bytes() == before, 'Existing backup changed')
            # Refuse a stale Compose environment before stopping any app.
            config['services']['api']['environment']['MEDIA_ROOT'] = '/wrong-media'
            compose_file.write_text(json.dumps(config))
            stale = subprocess.run(creates + [str(folder / 'stale-backup')], capture_output=True, text=True)
            require(stale.returncode != 0 and 'configuration differs' in stale.stderr, 'Stale configuration accepted')
            require(not (folder / 'stale-backup').exists(), 'Stale capture created backup')
            require(output(compose + ['ps', '-q', '--status', 'running', 'api']), 'Stale capture stopped app')
            config['services']['api']['environment']['MEDIA_ROOT'] = '/media'
            compose_file.write_text(json.dumps(config))
            run(compose + ['down', '--volumes'])
            print('Source containers, database and media destroyed before restore', flush=True)
            restored = folder / 'restored'
            run(tool + ['restore', str(bundle), str(restored)])
            state = json.loads((restored / 'restore.json').read_text())
            require(state['status'] == 'verified', 'Positive restore not verified')
            restored_compose = DOCKER + ['compose', '-p', state['project'], '-f', state['compose']]
            # Reuse the independent existing fixture verifier: every row/schema,
            # both reconciliation events, both movements, nested storage and PNG.
            synthetic = dict(line.split('=', 1) for line in shlex.split((ROOT/'infra/docker/owner-test.env').read_text(), comments=True))
            owner_env = [part for key, value in synthetic.items() for part in ('-e', key+'='+value)]
            run(restored_compose + ['run', '--rm', '--no-deps', *owner_env, '-e', 'PYTHONPATH=/app',
                '-v', f'{evidence}:/evidence:ro', '-v', f'{ROOT}/scripts/backup-restore.py:/rehearsal/backup-restore.py:ro',
                'api', 'python', '/rehearsal/backup-restore.py', 'verify'])
            require(not output(restored_compose + ['ps', '-q', '--status', 'running', 'api']), 'Restore exposed app')
            # Release only this verified disposable restore before the next one;
            # retained owner restores must not be pruned to make room for tests.
            run(restored_compose + ['down', '--volumes', '--remove-orphans'])
            # Damage with updated archive checksums must still fail restored-state
            # verification; this is stronger than a checksum-only test.
            for mode in ('checksum', 'missing', 'corrupt', 'unsafe', 'state'):
                damaged = folder / f'bundle-{mode}'
                shutil.copytree(bundle, damaged)
                if mode == 'checksum':
                    (damaged / 'database.dump').write_bytes(b'corrupt dump')
                elif mode == 'state':
                    expected = json.loads((damaged / 'state.json').read_text())
                    expected['tables']['owned_copies']['sha256'] = '0' * 64
                    (damaged / 'state.json').write_text(json.dumps(expected))
                    manifest = json.loads((damaged / 'manifest.json').read_text())
                    manifest['files']['state.json'] = hashlib.sha256((damaged / 'state.json').read_bytes()).hexdigest()
                    (damaged / 'manifest.json').write_text(json.dumps(manifest))
                else:
                    with tarfile.open(bundle / 'media.tar') as archive:
                        members = [(m, archive.extractfile(m).read() if m.isfile() else None) for m in archive]
                    with tarfile.open(damaged / 'media.tar', 'w') as archive:
                        for member, data in members:
                            if mode == 'missing' and member.isfile():
                                continue
                            if mode == 'corrupt' and member.isfile():
                                data = b'corrupt photo'
                                member.size = len(data)
                            archive.addfile(member, io.BytesIO(data) if data is not None else None)
                        if mode == 'unsafe':
                            archive.addfile(tarfile.TarInfo('../escape'))
                    manifest = json.loads((damaged / 'manifest.json').read_text())
                    manifest['files']['media.tar'] = hashlib.sha256((damaged / 'media.tar').read_bytes()).hexdigest()
                    (damaged / 'manifest.json').write_text(json.dumps(manifest))
                destination = folder / f'restored-{mode}'
                result = subprocess.run(tool + ['restore', str(damaged), str(destination)], capture_output=True, text=True)
                print(f'Negative {mode}: exit={result.returncode}\n{result.stderr}', flush=True)
                require(result.returncode != 0, f'Damaged {mode} restore accepted')
                message = {'checksum': 'Checksum mismatch', 'missing': 'Referenced media missing or corrupt',
                           'corrupt': 'Referenced media missing or corrupt', 'unsafe': 'Unsafe media archive member',
                           'state': 'Restored rows, migration head or media differ'}[mode]
                require(message in result.stderr, f'{mode} failed before expected boundary')
                if mode == 'checksum':
                    require(not destination.exists(), 'Checksum rejection created resources')
                else:
                    receipt = json.loads((destination / 'restore.json').read_text())
                    require(receipt['status'] == 'incomplete', 'Failed restore marked verified')
                    run(DOCKER + ['compose', '-p', receipt['project'], '-f', receipt['compose'],
                                  'down', '--volumes', '--remove-orphans'])
            print('Operator backup integration passed; 5 damage modes rejected', flush=True)
        finally:
            projects = [project]
            run(compose + ['down', '--volumes', '--remove-orphans', '--rmi', 'local'])
            for receipt in folder.glob('restored*/restore.json'):
                state = json.loads(receipt.read_text())
                projects.append(state['project'])
                run(DOCKER + ['compose', '-p', state['project'], '-f', state['compose'],
                              'down', '--volumes', '--remove-orphans'])
            for name in projects:
                for arguments in (['ps', '-aq'], ['volume', 'ls', '-q'], ['network', 'ls', '-q']):
                    require(not output(DOCKER + arguments + ['--filter', f'label=com.docker.compose.project={name}']),
                            f'Resources remain for {name}')
            print('Operator test cleanup checked', flush=True)


if __name__ == '__main__':
    main()
