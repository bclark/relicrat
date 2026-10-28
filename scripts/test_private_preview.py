"""Bridge access boundaries and cookie propagation, with no SSH/network exposure."""
import base64
import http.client
import importlib.util
import json
from pathlib import Path
import subprocess
import threading
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('preview', Path(__file__).with_name('private-preview.py'))
preview = importlib.util.module_from_spec(spec); spec.loader.exec_module(preview)


class BridgeTests(unittest.TestCase):
    def setUp(self):
        self.server = preview.LoopbackServer(('127.0.0.1', 0), preview.Handler)
        self.server.container = 'relicrat-synthetic-web-1'
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True); self.thread.start()
        self.origin = f'http://127.0.0.1:{self.server.server_port}'

    def tearDown(self):
        self.server.shutdown(); self.server.server_close(); self.thread.join()

    def request(self, method='GET', path='/', headers=None, body=None):
        connection = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=5)
        connection.request(method, path, headers=headers or {}, body=body)
        response = connection.getresponse(); data = response.read()
        result = response.status, dict(response.getheaders()), data
        connection.close(); return result

    def test_foreign_host_origin_path_and_bad_lengths_never_invoke_ssh(self):
        cases = [('GET','/', {'Host':'evil.test'}), ('POST','/', {'Origin':'https://evil.test'}),
                 ('GET','//evil.test',{}), ('POST','/',{'Origin':self.origin,'Content-Length':'-1'}),
                 ('POST','/',{'Origin':self.origin,'Content-Length':str(17*1024*1024+1)})]
        with patch.object(preview.subprocess, 'run') as relay:
            for method, path, headers in cases:
                with self.subTest(headers=headers):
                    self.assertIn(self.request(method,path,headers)[0], [400,403,413])
            relay.assert_not_called()

    def test_only_owner_cookie_is_relayed_and_login_cookie_redirects_are_preserved(self):
        response = {'status':307, 'headers':{'set-cookie':['relicrat_loopback_session=opaque; HttpOnly; SameSite=Strict; Path=/'], 'location':'/login','cache-control':'no-store'}, 'body':base64.b64encode(b'exact').decode()}
        with patch.object(preview.subprocess,'run',return_value=subprocess.CompletedProcess([],0,json.dumps(response).encode())) as relay:
            status, headers, body = self.request(headers={'Cookie':'other_app=secret; relicrat_loopback_session=opaque', 'Authorization':'Bearer never-forward'})
            self.assertEqual((status, body),(307,b'exact'))
            self.assertIn('HttpOnly',headers['set-cookie']); self.assertEqual(headers['location'],'/login')
            forwarded=json.loads(relay.call_args.kwargs['input'])
            self.assertEqual(forwarded['headers']['Cookie'],'relicrat_loopback_session=opaque')
            self.assertNotIn('Authorization',forwarded['headers'])
            self.assertNotIn('other_app',str(relay.call_args.args))


if __name__=='__main__': unittest.main()
