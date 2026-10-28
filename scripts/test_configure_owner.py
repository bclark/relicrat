"""Private, exclusive setup output and standard-library password verification."""
import contextlib
import importlib.util
import io
import os
from pathlib import Path
import tempfile
import unittest
import warnings
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('configure_owner',Path(__file__).with_name('configure-owner.py'))
setup=importlib.util.module_from_spec(spec);spec.loader.exec_module(setup)
from relicrat.credentials import verify_password, hash_password


class ConfigureTests(unittest.TestCase):
    def test_private_file_no_secret_output_and_existing_file_is_untouched(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'.env.owner'
            args=['configure-owner.py','--origin','http://127.0.0.1:3000','--allow-loopback-http','--output',str(path)]
            output=io.StringIO()
            with patch('sys.argv',args),patch.object(setup.getpass,'getpass',return_value='synthetic-only-password'),contextlib.redirect_stdout(output):
                setup.main()
            self.assertEqual(path.stat().st_mode & 0o777,0o600)
            self.assertNotIn('synthetic-only-password',output.getvalue())
            content=path.read_text();self.assertNotIn('synthetic-only-password',content)
            encoded=next(line.split('=',1)[1].strip("'") for line in content.splitlines() if line.startswith('RELICRAT_OWNER_PASSWORD_HASH='))
            self.assertTrue(verify_password('synthetic-only-password',encoded))
            self.assertFalse(verify_password('incorrect-password',encoded))
            with patch('sys.argv',args),contextlib.redirect_stderr(io.StringIO()),self.assertRaises(SystemExit):
                setup.main()
            self.assertEqual(path.read_text(),content)

    def test_unavailable_hidden_input_creates_no_file(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'.env.owner'
            def unavailable(*args):
                warnings.warn('No hidden input', setup.getpass.GetPassWarning)
                return 'must-not-be-used'
            with patch('sys.argv', ['setup', '--origin', 'https://private.test', '--output', str(path)]), patch.object(setup.getpass, 'getpass', side_effect=unavailable), contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                setup.main()
            self.assertFalse(path.exists())

    def test_unsafe_origin_weak_password_and_no_plain_remote_http(self):
        for origin in ['http://remote.test','https://user:secret@private.test','https://private.test/path','https://private.test:bad',"https://private.test'bad"]:
            with self.subTest(origin=origin),patch('sys.argv',['setup','--origin',origin]),contextlib.redirect_stderr(io.StringIO()),self.assertRaises(SystemExit):
                setup.main()
        with self.assertRaises(ValueError):hash_password('short-password')


if __name__=='__main__':unittest.main()
