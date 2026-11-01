"""Offline, trusted-operator backup for the current single-writer Compose stack.

No online snapshot, external archive ingestion, or in-place restore is supported.
"""
import argparse
from contextlib import contextmanager
import fcntl
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import secrets
import signal
import subprocess
import sys
import tarfile
import tempfile
from urllib.parse import urlsplit, unquote

DOCKER = ['docker', '--host', 'unix:///var/run/docker.sock']
FILES = ('database.dump', 'media.tar', 'state.json')


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def run(args, **kwargs):
    return subprocess.run(args, check=True, **kwargs)


def output(args):
    return subprocess.check_output(args, text=True).strip()


def inspect_container(compose, service):
    ids = output(compose + ['ps', '-q', service]).splitlines()
    require(len(ids) == 1, f'{service} must have exactly one running container')
    return json.loads(output(DOCKER + ['inspect', ids[0]]))[0]


def inside(compose, mode, destination=None):
    # No service ports are published by compose run. Execute this same helper,
    # not an API server; the live app remains stopped throughout capture.
    args = compose + ['run', '--rm', '-T', '--no-deps', '--entrypoint', 'python', 'api', '-', '_inside', mode]
    with Path(__file__).open('rb') as code:
        return run(args, stdin=code, stdout=destination or subprocess.PIPE).stdout


def capture(compose, directory):
    state = inside(compose, 'state')
    (directory / 'state.json').write_bytes(state)
    with (directory / 'database.dump').open('xb') as target:
        run(compose + ['exec', '-T', 'db', 'sh', '-ec',
            'exec pg_dump -h 127.0.0.1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" --format=custom'], stdout=target)
    with (directory / 'media.tar').open('xb') as target:
        inside(compose, 'archive', target)
    # Detect unexpected writers during the dump/archive window.
    require(state == inside(compose, 'state'), 'State changed during capture; backup incomplete')


@contextmanager
def capture_lock(container_id):
    # Same database container => same lock even through another Compose file.
    # Keep the empty lock file: unlinking it would permit races between inodes.
    path = Path(tempfile.gettempdir()) / f'relicrat-backup-{container_id}.lock'
    descriptor = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, 'r+') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError('Another backup is capturing this database') from None
        try:
            yield
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


def backup(args):
    require(re.fullmatch(r'[a-z0-9][a-z0-9_-]*', args.project), 'Invalid project name')
    compose = DOCKER + ['compose', '-p', args.project, '-f', str(args.compose.resolve())]
    api, db = inspect_container(compose, 'api'), inspect_container(compose, 'db')
    config = json.loads(output(compose + ['config', '--format', 'json']))
    require(set(config['services']) <= {'db', 'api', 'web'}, 'Only the single-writer db/api/web stack is supported')
    # A stale Compose file or rebuilt tag must never select a different helper
    # image/environment/volume than the app whose backup we are taking.
    for name, container in (('api', api), ('db', db)):
        # Compose's --hash does not resolve env_file like `up` does. Hash the
        # fully resolved model in memory; credentials never enter a temp file.
        expected_hash = subprocess.check_output(
            DOCKER + ['compose', '-p', args.project, '-f', '-', 'config', '--hash', name],
            input=json.dumps(config), text=True).strip().split()[-1]
        require(container['Config']['Labels'].get('com.docker.compose.config-hash') == expected_hash,
                f'{name} Compose configuration differs from running container')
    image = config['services']['api'].get('image', args.project + '-api')
    require(output(DOCKER + ['image', 'inspect', '--format', '{{.Id}}', image]) == api['Image'],
            'API image tag differs from running container')
    env = config['services']['api']['environment']
    url = urlsplit(env.get('DATABASE_URL', ''))
    db_env = config['services']['db']['environment']
    require(url.scheme == 'postgresql+psycopg' and url.hostname == 'db' and
            url.port in (None, 5432) and unquote(url.path) == '/' + db_env.get('POSTGRES_DB', '') and
            unquote(url.username or '') == db_env.get('POSTGRES_USER'),
            'API must point to this Compose database')
    root = env.get('MEDIA_ROOT')
    require(root and any(m['Type'] == 'volume' and m['Destination'] == root for m in api['Mounts']),
            'MEDIA_ROOT must be a named volume')
    require(any(m['Type'] == 'volume' and m['Destination'] == '/var/lib/postgresql/data' for m in db['Mounts']),
            'PostgreSQL must use its own named data volume')
    running = output(compose + ['ps', '--services', '--status', 'running']).splitlines()
    writers = [name for name in ('web', 'api') if name in running]
    with capture_lock(db['Id']):
        # Exclusive directory creation: failed/interrupted attempts remain incomplete
        # for inspection and can never overwrite a prior backup.
        args.directory.mkdir(mode=0o700)
        (args.directory / 'INCOMPLETE').touch(mode=0o600)
        try:
            run(compose + ['stop', *writers])
            for name in writers:
                require(not output(compose + ['ps', '-q', '--status', 'running', name]), 'Writer did not stop')
            capture(compose, args.directory)
            manifest = {'format': 1, 'created_at': datetime.now(timezone.utc).isoformat(),
                        'api_image': api['Image'], 'db_image': db['Image'],
                        'files': {name: digest(args.directory / name) for name in FILES}}
            (args.directory / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
            (args.directory / 'INCOMPLETE').unlink()
        finally:
            # start preserves the original containers/configuration; it never creates
            # a missing service or starts an app that was already stopped.
            run(compose + ['start', *reversed(writers)])
    print(f'Backup completed: {args.directory.resolve()}; app restarted')


def validate_bundle(directory):
    require(not (directory / 'INCOMPLETE').exists(), 'Backup is incomplete')
    require(not directory.is_symlink(), 'Backup directory must not be a symlink')
    require({p.name for p in directory.iterdir()} == set(FILES) | {'manifest.json'}, 'Unexpected backup contents')
    for name in (*FILES, 'manifest.json'):
        path = directory / name
        require(path.is_file() and not path.is_symlink(), 'Backup members must be regular files')
    manifest = json.loads((directory / 'manifest.json').read_text())
    require(manifest.get('format') == 1 and set(manifest.get('files', {})) == set(FILES), 'Unsupported backup manifest')
    for name in FILES:
        require(digest(directory / name) == manifest['files'][name], f'Checksum mismatch: {name}')
    for name in ('api_image', 'db_image'):
        require(re.fullmatch(r'sha256:[0-9a-f]{64}', manifest.get(name, '')), 'Invalid image identity')
    return manifest


def restore(args):
    bundle = args.directory.resolve()
    manifest = validate_bundle(args.directory)
    # Images must already exist locally. No tag resolution or arbitrary pull.
    for key in ('api_image', 'db_image'):
        require(output(DOCKER + ['image', 'inspect', '--format', '{{.Id}}', manifest[key]]) == manifest[key],
                'The exact backup images must be available locally')
    args.destination.mkdir(mode=0o700)
    project = 'relicrat-restore-' + secrets.token_hex(8)
    password = secrets.token_hex(24)
    config = {'services': {
        'db': {'image': manifest['db_image'], 'environment': {
            'POSTGRES_DB': 'relicrat', 'POSTGRES_USER': 'relicrat', 'POSTGRES_PASSWORD': password},
            'volumes': ['database:/var/lib/postgresql/data'],
            # The image's temporary initialization server listens only on Unix sockets.
            # Probe the same TCP endpoint used by pg_restore, not that early server.
            'healthcheck': {'test': ['CMD-SHELL', 'pg_isready -h 127.0.0.1 -U relicrat -d relicrat'],
                            'interval': '2s', 'timeout': '5s', 'retries': 30}},
        'api': {'image': manifest['api_image'], 'environment': {
            'DATABASE_URL': f'postgresql+psycopg://relicrat:{password}@db:5432/relicrat',
            'MEDIA_ROOT': '/var/lib/relicrat/media'},
            'volumes': ['media:/var/lib/relicrat/media']}},
        'volumes': {'database': {}, 'media': {}}, 'networks': {'default': {'internal': True}}}
    config_path = args.destination.resolve() / 'compose.json'
    config_path.write_text(json.dumps(config, indent=2) + '\n')
    config_path.chmod(0o600)
    compose = DOCKER + ['compose', '-p', project, '-f', str(config_path)]
    receipt = args.destination / 'restore.json'
    state = {'project': project, 'status': 'incomplete', 'compose': str(config_path), 'bundle': str(bundle)}
    receipt.write_text(json.dumps(state, indent=2) + '\n')
    print(f'Restore project: {project}; receipt: {receipt.resolve()}', flush=True)
    # Always fresh project/volumes, no existing-target flag, no app listeners.
    # Failure keeps only these new resources offline for operator inspection.
    run(compose + ['up', '-d', '--wait', 'db'])
    with (bundle / 'database.dump').open('rb') as source:
        run(compose + ['exec', '-T', 'db', 'pg_restore', '-h', '127.0.0.1', '-U', 'relicrat', '-d', 'relicrat',
                       '--exit-on-error', '--single-transaction', '--no-owner', '--no-privileges'], stdin=source)
    # Stream archive bytes to a no-network helper with only the fresh media volume.
    volume = project + '_media'
    run(DOCKER + ['volume', 'create', '--label', f'com.docker.compose.project={project}', '--label', 'com.docker.compose.volume=media', volume], stdout=subprocess.DEVNULL)
    program = Path(__file__).read_text()
    with (bundle / 'media.tar').open('rb') as source:
        run(DOCKER + ['run', '--rm', '-i', '--network', 'none', '--entrypoint', 'python',
                      '--mount', f'type=volume,source={volume},target=/var/lib/relicrat/media',
                      '-e', 'MEDIA_ROOT=/var/lib/relicrat/media', manifest['api_image'],
                      '-c', program, '_inside', 'extract'], stdin=source)
    actual = inside(compose, 'state')
    require(json.loads(actual) == json.loads((bundle / 'state.json').read_bytes()),
            'Restored rows, migration head or media differ; restore remains offline')
    state['status'] = 'verified'
    receipt.write_text(json.dumps(state, indent=2) + '\n')
    print('Restore verified: all rows, migration head, referenced photos and exact media checksums; no app started')


def media_files(root):
    files = {}
    require(root.is_dir() and not root.is_symlink(), 'Invalid media root')
    for path in sorted(root.rglob('*')):
        require(not path.is_symlink(), 'Media links are not supported')
        if path.is_dir():
            continue
        require(path.is_file(), 'Media must contain only regular files/directories')
        files[path.relative_to(root).as_posix()] = {'size': path.stat().st_size, 'sha256': digest(path)}
    return files


def check_members(archive):
    names = set()
    for member in archive:
        path = PurePosixPath(member.name)
        require(member.name and not path.is_absolute() and '..' not in path.parts and
                member.name.rstrip('/') == path.as_posix() and
                member.name not in names and (member.isfile() or member.isdir()), 'Unsafe media archive member')
        names.add(member.name)


def internal(mode):
    root = Path(os.environ['MEDIA_ROOT'])
    if mode == 'archive':
        media_files(root)
        with tarfile.open(fileobj=sys.stdout.buffer, mode='w|', dereference=True) as archive:
            for child in sorted(root.iterdir()):
                archive.add(child, arcname=child.name)
        return
    if mode == 'extract':
        require(not any(root.iterdir()), 'Restore media must be empty')
        # Seekable spool permits validating every member before any extraction.
        import tempfile
        import shutil
        with tempfile.TemporaryFile() as stream:
            shutil.copyfileobj(sys.stdin.buffer, stream)
            stream.seek(0)
            with tarfile.open(fileobj=stream) as archive:
                check_members(archive)
                archive.extractall(root, filter='data')
        return
    require(mode == 'state', 'Unknown internal operation')
    from alembic.config import Config
    from alembic.script import ScriptDirectory
    from sqlalchemy import inspect, text
    from relicrat.database import session_factory
    files = media_files(root)
    tables = {}
    with session_factory()() as db:
        quote = db.bind.dialect.identifier_preparer.quote
        for table in sorted(inspect(db.bind).get_table_names(schema='public')):
            checksum = hashlib.sha256()
            count = 0
            for row in db.execute(text(f'SELECT to_jsonb(t)::text FROM public.{quote(table)} AS t ORDER BY to_jsonb(t)::text')):
                checksum.update(row[0].encode() + b'\n')
                count += 1
            tables[table] = {'rows': count, 'sha256': checksum.hexdigest()}
        revision = sorted(db.execute(text('SELECT version_num FROM alembic_version')).scalars())
        require(revision == sorted(ScriptDirectory.from_config(Config('alembic.ini')).get_heads()), 'Migration head differs from API image')
        for key, size, checksum in db.execute(text('SELECT storage_key, byte_size, sha256 FROM media_assets')):
            require(key in files and files[key]['size'] == size and
                    (checksum is None or files[key]['sha256'] == checksum), 'Referenced media missing or corrupt')
    print(json.dumps({'tables': tables, 'revision': revision, 'media': files}, sort_keys=True))


def main():
    if sys.argv[1:2] == ['_inside']:
        internal(sys.argv[2])
        return
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='operation', required=True)
    command = sub.add_parser('create', help='Pause the single-writer app and back up its database/media')
    command.add_argument('--compose', type=Path, required=True, help='Trusted local db/api/web Compose file')
    command.add_argument('--project', required=True)
    command.add_argument('--offline-confirmed', action='store_true', required=True,
                         help='Confirm no external DB/media writers; app downtime is acceptable')
    command.add_argument('directory', type=Path, help='New backup directory (must not exist)')
    command = sub.add_parser('restore', help='Restore a trusted backup to a fresh isolated project, leaving it offline')
    command.add_argument('directory', type=Path)
    command.add_argument('destination', type=Path, help='New private directory for restore configuration/receipt')
    args = parser.parse_args()
    os.umask(0o077)
    require(output(DOCKER + ['info', '--format', '{{.Name}}']) == 'relicrat-worker',
            'This initial workflow requires the isolated relicrat-worker engine')
    def interrupted(signum, frame):
        raise RuntimeError(f'Interrupted ({signum}); inspect incomplete backup/restore receipt')
    for signum in (signal.SIGTERM, signal.SIGHUP, signal.SIGINT):
        signal.signal(signum, interrupted)
    if args.operation == 'create':
        backup(args)
    else:
        restore(args)


if __name__ == '__main__':
    main()
