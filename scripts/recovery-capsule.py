"""Authenticate an encrypted recovery capsule before validating or extracting it."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import tarfile

MEMBERS = {'backup/database.dump', 'backup/media.tar', 'backup/state.json', 'backup/manifest.json', 'images.tar.gz', 'image-ids.json', 'source.tar', 'capsule.json'}


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def members(tar, allowed=None):
    seen = set()
    for item in tar:
        p = PurePosixPath(item.name)
        name = str(p)
        if p.is_absolute() or '..' in p.parts or not (item.isdir() or item.isfile()) or name in seen:
            raise ValueError('Unsafe or duplicate archive member')
        seen.add(name)
        if allowed is not None and ((item.isfile() and name not in allowed) or (item.isdir() and name not in ('.', 'backup'))):
            raise ValueError('Unexpected capsule member')
    return {str(PurePosixPath(m.name)): m for m in tar.getmembers() if m.isfile()}


def verify_images(path, expected):
    if set(expected) != {'api', 'db', 'web'} or not all(re.fullmatch(r'sha256:[0-9a-f]{64}', x) for x in expected.values()):
        raise ValueError('Invalid image identities')
    with tarfile.open(path) as tar:
        names = members(tar)
        if 'index.json' in names:
            index = json.load(tar.extractfile(names['index.json']))
            if {x['digest'] for x in index['manifests']} != set(expected.values()):
                raise ValueError('OCI image IDs differ')
            for name, item in names.items():
                if name.startswith('blobs/sha256/'):
                    if not re.fullmatch(r'blobs/sha256/[0-9a-f]{64}', name):
                        raise ValueError('Invalid OCI blob name')
                    with tar.extractfile(item) as stream:
                        actual = hashlib.file_digest(stream, 'sha256').hexdigest()
                    if actual != name.rsplit('/', 1)[1]:
                        raise ValueError('Corrupt OCI blob')
            for ident in expected.values():
                if 'blobs/sha256/' + ident.split(':')[1] not in names:
                    raise ValueError('Missing OCI identity')
        else:
            manifest = json.load(tar.extractfile(names['manifest.json']))
            actual = set()
            for entry in manifest:
                with tar.extractfile(names[entry['Config']]) as stream:
                    actual.add('sha256:' + hashlib.file_digest(stream, 'sha256').hexdigest())
            if actual != set(expected.values()):
                raise ValueError('Saved image configs differ')


def validate(root, source_commit, source_sha256=None):
    root = Path(root)
    if {str(p.relative_to(root)) for p in root.rglob('*') if p.is_file()} != MEMBERS or any(p.is_symlink() for p in root.rglob('*')):
        raise ValueError('Unexpected capsule filesystem')
    manifest = json.loads((root/'capsule.json').read_text())
    if manifest['format'] != 1 or manifest['owner_credentials_included'] is not False or manifest['source_commit'] != source_commit:
        raise ValueError('Wrong capsule provenance')
    if set(manifest['files']) != MEMBERS - {'capsule.json'}:
        raise ValueError('Wrong capsule file set')
    for name, expected in manifest['files'].items():
        if not re.fullmatch('[0-9a-f]{64}', expected) or digest(root/name) != expected:
            raise ValueError('Capsule checksum mismatch')
    if source_sha256 and digest(root/'source.tar') != source_sha256:
        raise ValueError('Source differs from reviewed git archive')
    with tarfile.open(root/'source.tar') as source:
        entries = members(source)
        if any('.env.owner' in PurePosixPath(n).parts or '.ssh' in PurePosixPath(n).parts or n.endswith(('recipient-key.pem', 'operator_ed25519')) for n in entries):
            raise ValueError('Excluded credential file in source')
    images = json.loads((root/'image-ids.json').read_text())
    verify_images(root/'images.tar.gz', images)
    backup = json.loads((root/'backup/manifest.json').read_text())
    if backup['api_image'] != images['api'] or backup['db_image'] != images['db']:
        raise ValueError('Backup and saved images differ')
    if set(backup['files']) != {'database.dump', 'media.tar', 'state.json'}:
        raise ValueError('Wrong backup file set')
    for name, expected in backup['files'].items():
        if digest(root/'backup'/name) != expected:
            raise ValueError('Backup checksum differs')
    return images


def authenticated_envelope(archive):
    # Ask OpenSSL to identify the envelope and cipher; never parse cryptography
    # ourselves or retain its potentially huge encrypted-content dump.
    process = subprocess.Popen(['openssl','cms','-cmsout','-print','-inform','DER','-in',str(archive)], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
    content_type = None
    algorithm = False
    result = False
    try:
        for _ in range(100):
            line = process.stdout.readline(4096).strip()
            if not line:
                if process.poll() is not None:
                    break
                continue
            if content_type is None and line.startswith('contentType:'):
                content_type = line == 'contentType: id-smime-ct-authEnvelopedData (1.2.840.113549.1.9.16.1.23)'
            if line == 'contentEncryptionAlgorithm:':
                algorithm = True
            elif algorithm and line.startswith('algorithm:'):
                result = content_type and line == 'algorithm: aes-256-gcm (2.16.840.1.101.3.4.1.46)'
                break
    finally:
        process.stdout.close()
        if process.poll() is None:
            process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
    return bool(result)


def decrypt(archive, cert, key, destination, source_commit, expected_sha256=None, source_sha256=None):
    archive, destination = Path(archive), Path(destination)
    key = Path(key)
    if key.is_symlink() or not key.is_file() or key.stat().st_mode & 0o077 or key.parent.stat().st_mode & 0o077:
        raise ValueError('Recovery key and its directory must be private regular files/directories')
    if destination.exists() or archive.is_symlink():
        raise ValueError('Use a new destination and a regular encrypted archive')
    if expected_sha256 and digest(archive) != expected_sha256:
        raise ValueError('Encrypted archive checksum differs')
    if shutil.disk_usage(destination.parent).free < max(5*1024**3, archive.stat().st_size*6):
        raise ValueError('Insufficient private recovery staging capacity')
    if not authenticated_envelope(archive):
        raise ValueError('Recovery requires an authenticated CMS AES-256-GCM envelope')
    destination.mkdir(mode=0o700)
    plain = destination/'authenticated.tar'
    # GCM failure may leave partial output. It is retained privately but never opened.
    result = subprocess.run(['openssl', 'cms', '-decrypt', '-binary', '-inform', 'DER', '-in', str(archive), '-recip', str(cert), '-inkey', str(key), '-out', str(plain)], capture_output=True)
    if result.returncode:
        raise ValueError('Authenticated decryption failed; private staging retained')
    capsule = destination/'capsule'
    capsule.mkdir(mode=0o700)
    with tarfile.open(plain) as tar:
        actual = members(tar, MEMBERS)
        if set(actual) != MEMBERS:
            raise ValueError('Missing capsule member')
        for name, item in actual.items():
            target = capsule/name
            target.parent.mkdir(mode=0o700, exist_ok=True)
            with tar.extractfile(item) as source, target.open('xb') as output:
                shutil.copyfileobj(source, output)
            target.chmod(0o600)
    images = validate(capsule, source_commit, source_sha256)
    plain.unlink()
    return {'status': 'authenticated-capsule-verified', 'archive_sha256': digest(archive), 'source_commit': source_commit, 'images': images, 'capsule': str(capsule)}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--archive', type=Path, required=True)
    p.add_argument('--cert', type=Path, required=True)
    p.add_argument('--key', type=Path, required=True)
    p.add_argument('--destination', type=Path, required=True)
    p.add_argument('--source-commit', required=True)
    p.add_argument('--sha256')
    p.add_argument('--source-sha256')
    a = p.parse_args()
    os.umask(0o077)
    result = decrypt(a.archive, a.cert, a.key, a.destination, a.source_commit, a.sha256, a.source_sha256)
    (a.destination/'receipt.json').write_text(json.dumps(result, indent=2))
    print('Authenticated capsule verified; private receipt saved')


if __name__ == '__main__':
    main()
