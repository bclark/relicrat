"""Synthetic private HTTPS adapter framing, origin and cookie boundaries."""
import base64
import http.client
import importlib.util
from pathlib import Path
import threading
import json
import tempfile
import unittest
from unittest.mock import Mock

spec = importlib.util.spec_from_file_location('https_bridge', Path(__file__).with_name('private-https-bridge.py'))
bridge = importlib.util.module_from_spec(spec); spec.loader.exec_module(bridge)


class BridgeTests(unittest.TestCase):
    def setUp(self):
        self.server = bridge.preview.LoopbackServer(('127.0.0.1', 0), bridge.Handler)
        self.server.origin = 'https://phone.example.test'
        self.server.relay = Mock(return_value={'status': 200, 'headers': {}, 'body': base64.b64encode(b'synthetic').decode()})
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True); self.thread.start()
    def tearDown(self):
        self.server.shutdown(); self.server.server_close(); self.thread.join()
    def request(self, method='GET', path='/', headers=None, body=None):
        c = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=5)
        c.request(method, path, headers={'Host':'phone.example.test', **(headers or {})}, body=body)
        r = c.getresponse(); result = r.status, r.getheaders(), r.read(); c.close(); return result
    def test_rejected_inputs_do_not_reach_worker(self):
        cases = [('GET','/',{'Host':'evil.test'}),('POST','/',{}),('POST','/',{'Origin':'https://evil.test'}),
                 ('GET','//evil.test',{}),('GET','/bad#fragment',{}),
                 ('POST','/',{'Origin':self.server.origin,'Content-Length':'-1'}),
                 ('POST','/',{'Origin':self.server.origin,'Content-Length':'17825793'}),
                 ('POST','/',{'Origin':self.server.origin,'Transfer-Encoding':'chunked'})]
        for method,path,headers in cases:
            with self.subTest(path=path,headers=headers): self.assertIn(self.request(method,path,headers)[0],(400,403,413))
        self.server.relay.assert_not_called()
    def test_duplicate_authority_and_framing_rejected(self):
        for key, value in [('Host','phone.example.test'),('Origin',self.server.origin),('Content-Length','0'),('Cookie','a=b')]:
            c = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=5)
            c.putrequest('GET','/',skip_host=True); c.putheader('Host','phone.example.test')
            if key!='Host':c.putheader(key,value)
            c.putheader(key,value);c.endheaders();r=c.getresponse();self.assertEqual(r.status,400);r.read();c.close()
        self.server.relay.assert_not_called()
    def test_trusted_scheme_secure_cookie_and_body_are_preserved(self):
        cookie='__Host-relicrat_session=opaque; Path=/; HttpOnly; SameSite=Strict; Secure'
        self.server.relay.return_value={'status':307,'headers':{'set-cookie':[cookie],'location':'/login','connection':'keep-alive'},'body':base64.b64encode(b'exact').decode()}
        status,headers,body=self.request('POST','/api/v1/auth/login',{'Origin':self.server.origin,'Content-Type':'application/json','X-Forwarded-Proto':'http','X-Forwarded-Host':'evil.test','Forwarded':'host=evil.test','Authorization':'Bearer never-relay','Cookie':'unrelated=private; relicrat_loopback_session=wrong; __Host-relicrat_session=opaque'},b'{}')
        self.assertEqual((status,body),(307,b'exact'))
        self.assertIn(('set-cookie',cookie),headers)
        request=self.server.relay.call_args.args[0];self.assertEqual(request['body'],base64.b64encode(b'{}').decode())
        self.assertEqual(request['headers']['Cookie'],'__Host-relicrat_session=opaque')
        self.assertEqual(request['headers']['X-Forwarded-Proto'],'https')
        self.assertEqual(request['headers']['X-Forwarded-Host'],'phone.example.test')
        self.assertNotIn('Authorization',request['headers']);self.assertNotIn('Forwarded',request['headers'])
        self.assertEqual(dict(headers)['Permissions-Policy'],'camera=(self), microphone=()')
    def test_bad_upstream_returns_bounded_error(self):
        self.server.relay.side_effect=ValueError('private details')
        status,headers,body=self.request();self.assertEqual(status,502);self.assertNotIn(b'private details',body)
    def test_bad_upstream_cookie_or_header_is_rejected_before_headers_are_sent(self):
        for headers in ({'set-cookie':'relicrat_loopback_session=bad; Path=/'},
                        {'set-cookie':'__Host-relicrat_session=bad; Path=/; HttpOnly; SameSite=Strict'},
                        {'location':'/login\r\nInjected: value'}):
            self.server.relay.return_value={'status':200,'headers':headers,'body':''}
            self.assertEqual(self.request()[0],502)
    def test_private_transport_keeps_machine_values_out_of_source(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'transport.json'
            path.write_text(json.dumps({'ssh_args':['example-worker-alias'], 'engine_name':'example-engine'}));path.chmod(0o600)
            command, engine = bridge.load_transport(path)
            self.assertEqual(command, bridge.SSH_BASE+['example-worker-alias'])
            self.assertEqual(engine,'example-engine')
            self.assertIn('StrictHostKeyChecking=yes',command)
            self.assertIn('ForwardAgent=no',command)
    def test_transport_rejects_public_symlink_or_invalid_configuration(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'transport.json'
            path.write_text('{}');path.chmod(0o644)
            with self.assertRaises(ValueError):bridge.load_transport(path)
            path.chmod(0o600)
            link = Path(directory)/'link';link.symlink_to(path)
            with self.assertRaises(OSError):bridge.load_transport(link)
            for config in ({}, {'ssh_args':'not-an-array','engine_name':'example'},
                           {'ssh_args':['alias'],'engine_name':'bad engine'},
                           {'ssh_args':['alias'],'engine_name':'example','unexpected':'value'}):
                path.write_text(json.dumps(config))
                with self.assertRaises(ValueError):bridge.load_transport(path)
    def test_origin_configuration_is_exact_https(self):
        self.assertEqual(bridge.https_origin('https://phone.example.test/'),'https://phone.example.test')
        self.assertEqual(bridge.https_origin('https://phone.example.test:443'),'https://phone.example.test')
        for origin in ['http://phone.example.test','https://user:pass@phone.example.test','https://phone.example.test/path','https://phone.example.test?query','https://PHONE.example.test','https://phone.example.test:444']:
            with self.subTest(origin=origin),self.assertRaises(ValueError):bridge.https_origin(origin)


if __name__=='__main__':unittest.main()
