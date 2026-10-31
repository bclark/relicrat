"""NAS loopback adapter for Tailscale Serve and a separate HTTPS-origin frontend.

TLS terminates in Serve. Never publish this listener or reuse the Mac frontend:
this adapter pins one HTTPS origin and forwards only its Secure owner cookie.
"""
import argparse
import base64
import http.server
from http.cookies import SimpleCookie, CookieError
import importlib.util
import json
import os
import stat
from pathlib import Path
import re
import shlex
import subprocess
import sys
from urllib.parse import urlsplit


def sibling(name):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


preview = sibling('private-preview')


def https_origin(value):
    url = urlsplit(value)
    if (url.scheme != 'https' or not url.hostname or url.username or url.password or
            url.path not in ('', '/') or url.query or url.fragment or
            url.netloc != url.netloc.lower() or url.port not in (None, 443)):
        raise ValueError('Use one HTTPS hostname on its standard port')
    if not re.fullmatch(r'[a-z0-9][a-z0-9.-]*', url.hostname):
        raise ValueError('Use a DNS hostname')
    return 'https://' + url.hostname


class Handler(http.server.BaseHTTPRequestHandler):
    def setup(self):
        super().setup()
        self.connection.settimeout(15)

    def do_GET(self): self.forward()
    def do_POST(self): self.forward()

    def forward(self):
        origin = self.server.origin
        # Reject ambiguous framing and authority before invoking the worker.
        for name in ('Host', 'Origin', 'Content-Length', 'Content-Type', 'Cookie'):
            if len(self.headers.get_all(name, [])) > 1:
                self.send_error(400); return
        if self.headers.get('Host') != origin.removeprefix('https://'):
            self.send_error(403); return
        if self.command == 'POST' and self.headers.get('Origin') != origin:
            self.send_error(403); return
        target = self.requestline.split()[1]
        if (not target.startswith('/') or target.startswith('//') or '#' in target or
                any(ord(c) < 32 for c in target) or self.headers.get('Transfer-Encoding')):
            self.send_error(400); return
        raw_length = self.headers.get('Content-Length', '0')
        if not re.fullmatch(r'[0-9]{1,9}', raw_length):
            self.send_error(400); return
        length = int(raw_length)
        if length > 17 * 1024 * 1024:
            self.send_error(413); return
        headers = {key: self.headers[key] for key in ('Host', 'Origin', 'Content-Type', 'Accept') if key in self.headers}
        # Next reconstructs its request URL behind the TLS terminator. These
        # values are fixed here; client Forwarded/X-Forwarded-* never pass through.
        headers['X-Forwarded-Proto'] = 'https'
        headers['X-Forwarded-Host'] = origin.removeprefix('https://')
        cookies = [v.strip() for v in self.headers.get('Cookie', '').split(';')
                   if v.strip().startswith('__Host-relicrat_session=')]
        if cookies:
            headers['Cookie'] = '; '.join(cookies)
        try:
            body = self.rfile.read(length)
            if len(body) != length:
                self.send_error(400); return
            request = {'path': target, 'method': self.command, 'headers': headers,
                       'body': base64.b64encode(body).decode()}
            result = self.server.relay(request)
            data = base64.b64decode(result['body'], validate=True)
            status = result['status']
            if not isinstance(status, int) or not 200 <= status <= 599:
                raise ValueError('Invalid upstream status')
            response_headers = []
            for key, values in result['headers'].items():
                if key.lower() not in ('content-type', 'cache-control', 'x-content-type-options',
                                      'x-frame-options', 'referrer-policy', 'content-security-policy',
                                      'location', 'retry-after', 'set-cookie'):
                    continue
                for value in values if isinstance(values, list) else [values]:
                    if not isinstance(value, str) or '\r' in value or '\n' in value:
                        raise ValueError('Invalid upstream header')
                    if key.lower() == 'set-cookie':
                        parsed = SimpleCookie(); parsed.load(value)
                        if set(parsed) != {'__Host-relicrat_session'}:
                            raise ValueError('Expected the owner cookie')
                        cookie = parsed['__Host-relicrat_session']
                        if (not cookie['secure'] or not cookie['httponly'] or
                                cookie['samesite'].lower() != 'strict' or cookie['path'] != '/' or cookie['domain']):
                            raise ValueError('Expected a Secure host-only owner cookie')
                    response_headers.append((key, value))
            self.send_response(status)
            for key, value in response_headers: self.send_header(key, value)
            self.send_header('Strict-Transport-Security', 'max-age=86400')
            self.send_header('Permissions-Policy', 'camera=(self), microphone=()')
            self.send_header('Content-Length', str(len(data)))
            self.send_header('Connection', 'close')
            self.end_headers()
            self.wfile.write(data)
        except (subprocess.SubprocessError, ValueError, OSError, KeyError, TypeError, CookieError):
            self.send_error(502, 'Private connection unavailable')

    def log_message(self, *args):
        pass  # No passwords, cookies or collection query strings in logs.


SSH_BASE = ['ssh', '-T', '-o', 'BatchMode=yes', '-o', 'ForwardAgent=no',
            '-o', 'IdentitiesOnly=yes', '-o', 'StrictHostKeyChecking=yes',
            '-o', 'ConnectTimeout=10']


def load_transport(path):
    # Operator-owned local configuration, never data supplied by an HTTP client.
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd) as file:
        info = os.fstat(file.fileno())
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid() or
                info.st_mode & 0o077 or info.st_size > 65536):
            raise ValueError('Use a private regular transport file owned by this user')
        config = json.load(file)
    if not isinstance(config, dict) or set(config) != {'ssh_args', 'engine_name'}:
        raise ValueError('Transport requires ssh_args and engine_name only')
    args, engine = config['ssh_args'], config['engine_name']
    if (not isinstance(args, list) or not 1 <= len(args) <= 64 or
            any(not isinstance(v, str) or not v or '\x00' in v for v in args) or
            not isinstance(engine, str) or not re.fullmatch(r'[a-zA-Z0-9_.-]{1,100}', engine)):
        raise ValueError('Invalid private SSH transport configuration')
    return SSH_BASE + args, engine


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--origin', required=True)
    parser.add_argument('--container', required=True)
    parser.add_argument('--port', type=int, required=True)
    parser.add_argument('--transport-config', type=Path, required=True)
    args = parser.parse_args()
    try: origin = https_origin(args.origin)
    except ValueError as error: parser.error(str(error))
    if not re.fullmatch(r'[a-z0-9][a-z0-9_.-]{0,120}', args.container) or not 0 <= args.port <= 65535:
        parser.error('Invalid fixed container or loopback port')
    try: ssh, expected_engine = load_transport(args.transport_config)
    except (ValueError, OSError) as error: parser.error(str(error))
    engine = subprocess.check_output(ssh + ["docker --host unix:///var/run/docker.sock info --format '{{.Name}}'"], text=True).strip()
    if engine != expected_engine: parser.error('Use the configured private engine')
    item = json.loads(subprocess.check_output(ssh + ['docker --host unix:///var/run/docker.sock inspect ' + shlex.quote(args.container)]))[0]
    env = dict(v.split('=', 1) for v in item['Config']['Env'])
    if (not item['State']['Running'] or item['HostConfig']['PortBindings'] or
            env.get('RELICRAT_WEB_ORIGIN') != origin or env.get('RELICRAT_ALLOW_LOOPBACK_HTTP') == '1'):
        parser.error('Use the running private frontend configured for this exact HTTPS origin')
    command = 'docker --host unix:///var/run/docker.sock exec -i ' + shlex.quote(args.container) + ' node -e ' + shlex.quote(preview.PROGRAM)
    def relay(request):
        result = subprocess.run(ssh + [command], input=json.dumps(request).encode(), capture_output=True, check=True, timeout=45)
        return json.loads(result.stdout)
    server = preview.LoopbackServer(('127.0.0.1', args.port), Handler)
    server.origin, server.relay = origin, relay
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()


if __name__ == '__main__': main()
