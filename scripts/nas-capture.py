"""NAS-side fresh encrypted capture; copied restore/off-site success remain separate."""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import uuid
from zoneinfo import ZoneInfo

from operations import atomic_json, private_config

D = ['docker', '--host', 'unix:///var/run/docker.sock']
RUN = re.compile(r'[0-9]{8}T[0-9]{6}Z-[0-9a-f]{6}')
FILES = {'backup/database.dump', 'backup/media.tar', 'backup/state.json', 'backup/manifest.json', 'images.tar.gz', 'image-ids.json', 'source.tar'}


def require(value, message):
    if not value:
        raise ValueError(message)


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def output(args, **kwargs):
    return subprocess.check_output(args, text=True, **kwargs).strip()


@contextmanager
def lock(root):
    with (root/'capture.lock').open('a') as stream:
        os.chmod(stream.name, 0o600)
        fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield


def preflight(c, capture_space=False):
    require(output(D+['info', '--format', '{{.Name}}']) == c['engine'], 'Wrong worker engine')
    require(re.fullmatch('[a-z0-9][a-z0-9_-]{0,90}', c['project']), 'Unapproved inventory project')
    require(re.fullmatch('[0-9a-f]{40}', c['source_commit']), 'Invalid source commit')
    require(shutil.disk_usage(c['recovery_root']).free >= c['minimum_free_bytes'], 'Worker capacity reserve exhausted')
    for field, expected in [('backup_script', 'backup_script_sha256'), ('compose', 'compose_sha256'), ('owner_env', 'owner_env_sha256'), ('source_tar', 'source_tar_sha256')]:
        path = Path(c[field])
        require(path.is_file() and not path.is_symlink() and digest(path) == c[expected], 'Recorded deployment configuration changed')
    require(not Path(c['owner_env']).stat().st_mode & 0o077, 'Owner environment permissions changed')
    require(json.loads(Path(c['symphony_state']).read_text())['status'] == 'stopped', 'Unexpected coding writer')
    state = {}
    for service, name in c['containers'].items():
        item = json.loads(output(D+['inspect', name]))[0]
        expected = c['images']['web' if service == 'phone' else service]
        require(item['State']['Running'] and item['Image'] == expected and not item['HostConfig']['PortBindings'], 'Running services changed')
        require(item['Config']['Labels']['com.docker.compose.project'] == (c['phone_project'] if service == 'phone' else c['project']), 'Container ownership changed')
        state[service] = item['Id']
    if capture_space:
        media = int(output(D+['exec', c['containers']['api'], 'python', '-c', "import os;from pathlib import Path;r=Path(os.environ['MEDIA_ROOT']);files=list(r.rglob('*'));assert not any(p.is_symlink() for p in files);print(sum(p.stat().st_size for p in files if p.is_file()))"]))
        database = int(output(D+['exec', c['containers']['db'], 'sh', '-c', 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atqc \'select pg_database_size(current_database())\'']))
        images = sum(int(output(D+['image','inspect','--format','{{.Size}}',ident])) for ident in set(c['images'].values()))
        require(shutil.disk_usage(c['recovery_root']).free >= c['minimum_free_bytes'] + 2*(database+media) + images, 'Worker lacks capture staging space plus reserve')
    return state


def worker_capture(c, run):
    require(RUN.fullmatch(run), 'Invalid capture identity')
    before = preflight(c, capture_space=True)
    root = Path(c['recovery_root'])/'off-host'/run
    require(root.parent.is_dir() and not root.parent.is_symlink(), 'Missing private capture root')
    root.mkdir(mode=0o700)
    owner = dict(item.split('=', 1) for item in shlex.split(Path(c['owner_env']).read_text(), comments=True))
    subprocess.run([sys.executable, c['backup_script'], 'create', '--compose', c['compose'], '--project', c['project'], '--offline-confirmed', str(root/'backup')], env={**os.environ, **owner}, check=True)
    require(preflight(c) == before, 'App containers changed during capture')
    shutil.copyfile(c['source_tar'], root/'source.tar')
    (root/'image-ids.json').write_text(json.dumps(c['images']))
    with (root/'images.tar.gz').open('xb') as target:
        save = subprocess.Popen(D+['image', 'save', *sorted(set(c['images'].values()))], stdout=subprocess.PIPE)
        try:
            compressed = subprocess.run(['gzip', '-c'], stdin=save.stdout, stdout=target)
            save.stdout.close()
            require(save.wait() == 0 and compressed.returncode == 0, 'Image export failed')
        finally:
            if save.poll() is None:
                save.kill()
                save.wait()
    manifest = {'format': 1, 'source_commit': c['source_commit'], 'owner_credentials_included': False, 'files': {name: digest(root/name) for name in sorted(FILES)}}
    (root/'capsule.json').write_text(json.dumps(manifest, indent=2))
    require({str(p.relative_to(root)) for p in root.rglob('*') if p.is_file()} == FILES | {'capsule.json'}, 'Unexpected capture file')
    require(preflight(c) == before, 'Application restart/identity check failed')
    return {'run': run, 'capsule': str(root), 'source_commit': c['source_commit'], 'source_tar_sha256': c['source_tar_sha256'], 'captured_at_utc': json.loads((root/'backup/manifest.json').read_text())['created_at'], 'images': c['images'], 'app_restart_verified': True, 'capsule_bytes': sum(p.stat().st_size for p in root.rglob('*') if p.is_file())}


def capture(c):
    root = Path(c['root'])
    require(root.is_dir() and not root.is_symlink() and not root.stat().st_mode & 0o077, 'NAS control root must be private')
    require(Path(c['certificate']).is_file() and not Path(c['certificate']).is_symlink() and digest(c['certificate']) == c['certificate_sha256'], 'Recipient certificate changed')
    require(shutil.disk_usage(root).free >= c['minimum_free_bytes'], 'NAS capacity reserve exhausted')
    local_date = datetime.now(ZoneInfo(c.get('timezone', 'America/New_York'))).date().isoformat()
    with lock(root):
        latest = root/'LATEST.json'
        if latest.exists():
            old = json.loads(latest.read_text())
            if old['local_date'] == local_date:
                require(RUN.fullmatch(old['run']) and old['archive'] == old['run']+'.tar.cms', 'Unsafe capture archive reference')
                require(old['status'] == 'encrypted-capture-awaiting-copied-restore', 'Unrecognized capture receipt')
                require(old['source_commit'] == c['source_commit'], 'Release changed after today\'s capture; explicit review required')
                path = root/'archives'/old['archive']
                require(path.is_file() and not path.is_symlink() and digest(path) == old['sha256'], 'Existing capture bytes changed')
                return old
        run = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+uuid.uuid4().hex[:6]
        record = {'run': run, 'local_date': local_date, 'status': 'capturing', 'source_commit': c['source_commit'], 'systemd_invocation_id': os.environ.get('INVOCATION_ID')}
        record_path = root/'runs'/(run+'.json')
        atomic_json(record_path, record)
        args = [*c['worker_ssh'], shlex.join(['python3', c['worker_script'], 'worker', '--config', c['worker_config'], '--run', run])]
        with (root/'runs'/(run+'.log')).open('x') as log:
            os.chmod(log.name, 0o600)
            result = subprocess.run(args, stdout=subprocess.PIPE, stderr=log)
            log.write(result.stdout.decode(errors='replace'))
        require(result.returncode == 0, 'Fresh capture failed; private worker/NAS staging retained')
        lines = result.stdout.decode().splitlines()
        records = [json.loads(line[15:]) for line in lines if line.startswith('CAPTURE_RECORD ')]
        require(len(records) == 1 and records[0]['run'] == run and records[0]['source_commit'] == c['source_commit'], 'Wrong capture receipt')
        record.update(records[0])
        require(record['capsule'] == c['worker_recovery_root']+'/off-host/'+run, 'Unowned capture directory')
        require(shutil.disk_usage(root).free >= c['minimum_free_bytes'] + record['capsule_bytes'], 'NAS lacks archive space plus reserve')
        archive = root/'archives'/(run+'.tar.cms')
        partial = archive.with_suffix('.cms.partial')
        with partial.open('xb') as target:
            os.chmod(partial, 0o600)
            sender = subprocess.Popen([*c['worker_ssh'], shlex.join(['tar', '-cf', '-', '-C', record['capsule'], '.'])], stdout=subprocess.PIPE)
            try:
                encrypted = subprocess.run(['openssl', 'cms', '-encrypt', '-binary', '-aes-256-gcm', '-stream', '-outform', 'DER', c['certificate']], stdin=sender.stdout, stdout=target, stderr=subprocess.DEVNULL)
                sender.stdout.close()
                require(sender.wait() == 0 and encrypted.returncode == 0, 'Encryption/transfer incomplete')
                target.flush()
                os.fsync(target.fileno())
            finally:
                if sender.poll() is None:
                    sender.kill()
                    sender.wait()
        partial.rename(archive)
        record.update(status='encrypted-capture-awaiting-copied-restore', archive=archive.name, bytes=archive.stat().st_size, sha256=digest(archive), authenticated_decryption_verified=False, copied_restore_verified=False, cloud_verified=False)
        atomic_json(record_path, record)
        atomic_json(latest, record)
        return record


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('mode', choices=['worker', 'capture'])
    p.add_argument('--config', type=Path, required=True)
    p.add_argument('--run')
    a = p.parse_args()
    os.umask(0o077)
    c = private_config(a.config)
    if a.mode == 'worker':
        result = worker_capture(c, a.run)
        print('CAPTURE_RECORD '+json.dumps(result))
    else:
        capture(c)
        print('NAS encrypted capture recorded; copied restore and off-site verification remain separate')


if __name__ == '__main__':
    main()
