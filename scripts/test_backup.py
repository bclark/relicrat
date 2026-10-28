"""Local trust-boundary checks; integration lives in test-operator-backup.py."""
import importlib.util
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('backup', Path(__file__).with_name('backup.py'))
backup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(backup)


class BackupTests(unittest.TestCase):
    def bundle(self, root):
        for name in backup.FILES:
            (root / name).write_bytes(b'synthetic')
        data = {'format': 1, 'api_image': 'sha256:' + '1' * 64, 'db_image': 'sha256:' + '2' * 64,
                'files': {name: backup.digest(root / name) for name in backup.FILES}}
        (root / 'manifest.json').write_text(json.dumps(data))
        return data

    def test_capture_lock_rejects_competing_backup_and_releases_on_error(self):
        with tempfile.TemporaryDirectory() as folder:
            key = Path(folder).name
            try:
                with self.assertRaisesRegex(RuntimeError, 'simulated'):
                    with backup.capture_lock(key):
                        with self.assertRaisesRegex(RuntimeError, 'Another backup'):
                            with backup.capture_lock(key):
                                self.fail('Concurrent capture acquired lock')
                        raise RuntimeError('simulated interruption')
                with backup.capture_lock(key):
                    pass
            finally:
                (Path(tempfile.gettempdir()) / f'relicrat-backup-{key}.lock').unlink()

    def test_complete_bundle_and_each_damaged_member(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.bundle(root)
            backup.validate_bundle(root)
            for name in backup.FILES:
                with self.subTest(name=name):
                    (root / name).write_bytes(b'corrupt')
                    with self.assertRaisesRegex(RuntimeError, 'Checksum mismatch'):
                        backup.validate_bundle(root)
                    (root / name).write_bytes(b'synthetic')

    def test_incomplete_missing_extra_symlink_and_bad_image(self):
        for kind in ('incomplete', 'missing', 'extra', 'symlink', 'image'):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                data = self.bundle(root)
                if kind == 'incomplete':
                    (root / 'INCOMPLETE').touch()
                elif kind == 'missing':
                    (root / 'media.tar').unlink()
                elif kind == 'extra':
                    (root / 'extra').touch()
                elif kind == 'symlink':
                    (root / 'media.tar').unlink()
                    (root / 'media.tar').symlink_to(root / 'database.dump')
                else:
                    data['api_image'] = 'arbitrary:latest'
                    (root / 'manifest.json').write_text(json.dumps(data))
                with self.assertRaises(RuntimeError):
                    backup.validate_bundle(root)

    def test_archive_rejects_links_traversal_devices_and_duplicates(self):
        for kind in ('traversal', 'absolute', 'symlink', 'hardlink', 'device', 'duplicate'):
            with self.subTest(kind=kind), io.BytesIO() as stream:
                with tarfile.open(fileobj=stream, mode='w') as archive:
                    info = tarfile.TarInfo({'traversal': '../escape', 'absolute': '/escape'}.get(kind, 'photo.png'))
                    info.type = {'symlink': tarfile.SYMTYPE, 'hardlink': tarfile.LNKTYPE,
                                 'device': tarfile.CHRTYPE}.get(kind, tarfile.REGTYPE)
                    info.linkname = 'elsewhere'
                    archive.addfile(info)
                    if kind == 'duplicate':
                        archive.addfile(info)
                stream.seek(0)
                with tarfile.open(fileobj=stream) as archive:
                    with self.assertRaisesRegex(RuntimeError, 'Unsafe media'):
                        backup.check_members(archive)

    def test_archive_accepts_regular_nested_file_and_directory(self):
        with io.BytesIO() as stream:
            with tarfile.open(fileobj=stream, mode='w') as archive:
                directory = tarfile.TarInfo('ab')
                directory.type = tarfile.DIRTYPE
                archive.addfile(directory)
                archive.addfile(tarfile.TarInfo('ab/photo.png'))
            stream.seek(0)
            with tarfile.open(fileobj=stream) as archive:
                backup.check_members(archive)

    def test_media_rejects_links_and_hashes_exact_bytes(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'photo.png').write_bytes(b'exact photo')
            self.assertEqual(backup.media_files(root)['photo.png']['size'], 11)
            (root / 'link').symlink_to(root / 'photo.png')
            with self.assertRaisesRegex(RuntimeError, 'links'):
                backup.media_files(root)


if __name__ == '__main__':
    unittest.main()
