"""Mac loopback-only HTTP access over the existing two-hop worker SSH helper.

No NAS ports or SSH forwarding changes. Single web replica; synthetic data only.
"""
import argparse
import base64
import http.server
import json
from pathlib import Path
import re
import shlex
import socketserver
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
# Native HTTP preserves the browser Host; Next's owner boundary pins that value.
PROGRAM = """const http=require('http'),fs=require('fs');const q=JSON.parse(fs.readFileSync(0,'utf8'));const body=Buffer.from(q.body,'base64');if(q.method==='POST')q.headers['content-length']=String(body.length);const r=http.request({hostname:'127.0.0.1',port:3000,path:q.path,method:q.method,headers:q.headers},s=>{const a=[];s.on('data',x=>a.push(x));s.on('end',()=>process.stdout.write(JSON.stringify({status:s.statusCode,headers:Object.fromEntries(['content-type','cache-control','x-content-type-options','x-frame-options','referrer-policy','content-security-policy','location','retry-after','set-cookie'].filter(k=>s.headers[k]!==undefined).map(k=>[k,s.headers[k]])),body:Buffer.concat(a).toString('base64')})));});r.setTimeout(35000,()=>r.destroy(new Error('timeout')));r.on('error',()=>{process.exitCode=1;});r.end(q.method==='POST'?body:undefined);"""


class LoopbackServer(http.server.ThreadingHTTPServer):
    daemon_threads = True
    def server_bind(self):
        # Avoid HTTPServer's unnecessary reverse-DNS lookup for this loopback URL.
        socketserver.TCPServer.server_bind(self)
        self.server_name = 'localhost'
        self.server_port = self.server_address[1]


class Handler(http.server.BaseHTTPRequestHandler):
    def setup(self):
        super().setup()
        self.connection.settimeout(15)

    def do_GET(self): self.forward()
    def do_POST(self): self.forward()

    def forward(self):
        origin = f'http://127.0.0.1:{self.server.server_port}'
        if self.headers.get('Host') != origin.removeprefix('http://'):
            self.send_error(403); return
        if self.command == 'POST' and self.headers.get('Origin') != origin:
            self.send_error(403); return
        if not self.path.startswith('/') or self.requestline.split()[1].startswith('//') or self.headers.get('Transfer-Encoding'):
            self.send_error(400); return
        try:
            length = int(self.headers.get('Content-Length', '0'))
        except ValueError:
            self.send_error(400); return
        if not 0 <= length <= 17 * 1024 * 1024:
            self.send_error(413); return
        headers = {key: self.headers[key] for key in ['Host', 'Origin', 'Content-Type', 'Accept'] if key in self.headers}
        # Do not relay unrelated localhost apps' cookies, or browser Authorization.
        cookies = [value.strip() for value in self.headers.get('Cookie', '').split(';') if value.strip().startswith('relicrat_loopback_session=')]
        if cookies:
            headers['Cookie'] = '; '.join(cookies)
        request = {'path': self.path, 'method': self.command, 'headers': headers,
                   'body': ''}
        try:
            data = self.rfile.read(length)
        except OSError:
            self.send_error(400); return
        if len(data) != length:
            self.send_error(400); return
        request['body'] = base64.b64encode(data).decode()
        command = 'docker --host unix:///var/run/docker.sock exec -i ' + shlex.quote(self.server.container) + ' node -e ' + shlex.quote(PROGRAM)
        try:
            result = subprocess.run([sys.executable, str(ROOT/'scripts/worker-ssh.py'), command],
                                    input=json.dumps(request).encode(), capture_output=True, check=True, timeout=45)
            response = json.loads(result.stdout)
            data = base64.b64decode(response['body'], validate=True)
            self.send_response(response['status'])
            for key, values in response['headers'].items():
                for value in values if isinstance(values, list) else [values]:
                    self.send_header(key, value)
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        except (subprocess.SubprocessError, ValueError, OSError, KeyError, TypeError):
            self.send_error(502, 'Private preview connection unavailable')

    def log_message(self, *args):
        pass  # No credentials, session IDs or collection URLs in bridge logs.


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', required=True)
    parser.add_argument('--port', type=int, default=3000, help='Mac loopback port; 0 allocates a test port')
    args = parser.parse_args()
    if not re.fullmatch(r'[a-z0-9][a-z0-9_-]*', args.project) or not 0 <= args.port <= 65535:
        parser.error('Invalid Compose project or loopback port')
    result = subprocess.run([sys.executable, str(ROOT/'scripts/worker-ssh.py'), "docker --host unix:///var/run/docker.sock info --format '{{.Name}}'"], capture_output=True, text=True, check=True)
    if result.stdout.strip() != 'relicrat-worker':
        parser.error('Use the isolated relicrat-worker engine')
    server = LoopbackServer(('127.0.0.1', args.port), Handler)
    server.container = args.project + '-web-1'
    print(f'http://127.0.0.1:{server.server_port}', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
