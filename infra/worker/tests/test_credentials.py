"""Run on the provisioned worker: python3 -m unittest discover -s infra/worker/tests."""
import io
import os
from pathlib import Path
import runpy
import subprocess
import tempfile
import unittest
from unittest.mock import patch


class CredentialsTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.home = Path(self.directory.name)
        self.token_path = self.home / '.config/relicrat/github-token'
        self.environment = dict(os.environ, HOME=str(self.home))

    def helper(self, protocol, host, path):
        return subprocess.check_output(
            ['/usr/local/bin/relicrat-git-credential', 'get'],
            input=f'protocol={protocol}\nhost={host}\npath={path}\n\n',
            text=True, env=self.environment)

    def test_helper_limits_token_to_selected_https_repository(self):
        self.token_path.parent.mkdir(parents=True)
        self.token_path.write_text('fake-unit-test-token')
        for path in ('bclark/relicrat', 'bclark/relicrat.git'):
            self.assertIn('password=fake-unit-test-token', self.helper('https', 'github.com', path))
        for protocol, host, path in (
            ('http', 'github.com', 'bclark/relicrat'),
            ('https', 'example.com', 'bclark/relicrat'),
            ('https', 'github.com', 'bclark/other-repo'),
            ('https', 'github.com', 'bclark/relicrat.git/extra'),
        ):
            self.assertEqual('', self.helper(protocol, host, path))

    def test_helper_handles_missing_credentials(self):
        self.assertEqual('', self.helper('https', 'github.com', 'bclark/relicrat'))

    def login(self, response):
        with patch.dict(os.environ, self.environment, clear=True), \
                patch('getpass.getpass', return_value='fake-unit-test-token'), \
                patch('urllib.request.urlopen', return_value=io.BytesIO(response)), \
                patch('sys.stdout', new_callable=io.StringIO) as output:
            runpy.run_path('/usr/local/bin/relicrat-github-login', run_name='__main__')
            self.assertNotIn('fake-unit-test-token', output.getvalue())

    def test_login_stores_token_with_private_permissions(self):
        self.login(b'{"full_name": "bclark/relicrat"}')
        self.assertEqual('fake-unit-test-token', self.token_path.read_text())
        self.assertEqual(0o600, self.token_path.stat().st_mode & 0o777)
        self.assertEqual(0o700, self.token_path.parent.stat().st_mode & 0o777)

    def test_login_does_not_store_token_for_unexpected_repository(self):
        with self.assertRaises(SystemExit):
            self.login(b'{"full_name": "bclark/other-repo"}')
        self.assertFalse(self.token_path.exists())


if __name__ == '__main__':
    unittest.main()
