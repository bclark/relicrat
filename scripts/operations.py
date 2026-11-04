"""Private read-only health snapshots and loopback dashboard, using stdlib only."""
import argparse
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import threading
import time
import urllib.error
import urllib.request

UTC = timezone.utc
GOOD = {'verified-offhost-copy-and-disposable-restore', 'verified-offsite-parts', 'verified-and-cleaned'}


def now():
    return datetime.now(UTC)


def age(value, current):
    stamp = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if stamp.tzinfo is None:
        raise ValueError('Timestamp needs a timezone')
    seconds = (current - stamp).total_seconds()
    if seconds < -300:
        raise ValueError('Timestamp is in the future')
    return max(0, seconds)


def read_json(path):
    p = Path(path)
    if p.is_symlink() or p.stat().st_size > 2 * 1024 * 1024:
        raise ValueError('Unsafe or oversized JSON')
    return json.loads(p.read_text())


def private_config(path):
    p = Path(path)
    if p.stat().st_mode & 0o077:
        raise ValueError('Configuration must be private')
    return read_json(p)


def atomic_json(path, value):
    p = Path(path)
    temporary = p.with_name(p.name + '.new-' + str(os.getpid()))
    with temporary.open('x') as output:
        os.chmod(temporary, 0o600)
        json.dump(value, output, indent=2)
        output.flush()
        os.fsync(output.fileno())
    temporary.replace(p)


def check(ident, label, state, detail):
    return {'id': ident, 'label': label, 'state': state, 'detail': detail}


def capacity(ident, label, path, minimum):
    free = shutil.disk_usage(path).free
    return check(ident, label, 'ok' if free >= minimum else 'action', f'{free / 1024**3:.1f} GiB available; reserve {minimum / 1024**3:.1f} GiB')


def receipt_path(item):
    if 'path' in item:
        return Path(item['path'])
    root = Path(item['root']).resolve()
    ref = Path(read_json(item['latest'])['receipt'])
    candidate = ref if ref.is_absolute() else root/ref
    if not candidate.resolve().is_relative_to(root) or candidate.is_symlink():
        raise ValueError('Receipt pointer escaped its approved root')
    return candidate


def receipt_check(ident, label, receipt, current, max_age=36*3600):
    try:
        r = read_json(receipt)
        if not re.fullmatch('[0-9a-f]{40}', r.get('source_commit','')) or not re.fullmatch('[0-9a-f]{64}',r.get('sha256','')):
            raise ValueError('Missing recovery identity')
        if r.get('status') not in GOOD:
            raise ValueError('Unverified receipt')
        if ident == 'mac-backup' and not all(r.get(k) is True for k in ('restore_verified', 'member_checksums_verified', 'saved_image_ids_verified')):
            raise ValueError('Missing restore evidence')
        if ident == 'cloud-backup' and not all(r.get(k) is True for k in ('all_downloaded_parts_verified', 'downloaded_manifest_verified', 'full_archive_sha256_verified', 'owner_only_metadata_verified', 'cms_authenticated_decryption_verified')):
            raise ValueError('Missing cloud readback evidence')
        seconds = age(r['completed_at_utc'], current)
        return check(ident, label, 'ok' if seconds <= max_age else 'action', f'Verified {int(seconds // 3600)} hours ago; source {r["source_commit"][:7]}')
    except (OSError, ValueError, KeyError, TypeError):
        return check(ident, label, 'unknown', 'Verified evidence is missing or invalid')


WORKER_PROBE = '''import json,subprocess,shutil
from pathlib import Path
c=CONFIG;D=['docker','--host','unix:///var/run/docker.sock']
assert subprocess.check_output(D+['info','--format','{{.Name}}'],text=True).strip()==c['engine']
checks=[]
for service,name in c['containers'].items():
 v=json.loads(subprocess.check_output(D+['inspect',name],stderr=subprocess.DEVNULL))[0]
 checks.append({'service':service,'running':v['State']['Running'],'image_matches':v['Image']==c['images']['web' if service=='phone' else service],'private':not bool(v['HostConfig']['PortBindings']),'restart_policy':v['HostConfig']['RestartPolicy']['Name'],'healthy':v['State'].get('Health',{}).get('Status')=='healthy' if service=='db' else True})
api_health=subprocess.run(D+['exec',c['containers']['api'],'python','-c',"import urllib.request;assert urllib.request.urlopen('http://127.0.0.1:8000/health',timeout=5).status==200"],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=15).returncode==0
web_health=subprocess.run(D+['exec',c['containers']['web'],'node','-e',"fetch('http://127.0.0.1:3000/login').then(r=>process.exit(r.status===200?0:1)).catch(()=>process.exit(1))"],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=15).returncode==0
print(json.dumps({'api_health':api_health,'web_health':web_health,'services':checks,'free_bytes':shutil.disk_usage(c['capacity_path']).free,'symphony_stopped':json.loads(Path(c['symphony_state']).read_text())['status']=='stopped'}))
'''


def collect(config, current=None):
    current = current or now()
    checks = []
    if 'remote_snapshot' in config:
        try:
            result = subprocess.run(config['remote_snapshot'], capture_output=True, timeout=45, check=True)
            if len(result.stdout) > 65536:
                raise ValueError('Oversized snapshot')
            remote = json.loads(result.stdout)
            fresh = age(remote['checked_at_utc'], current) <= 900
            imported = []
            for item in remote['checks']:
                if item['state'] not in ('ok', 'action', 'unknown') or not re.fullmatch(r'[a-z0-9-]{1,60}', item['id']) or item['id'] == 'nas-monitor':
                    raise ValueError('Invalid remote check')
                imported.append(check(item['id'], str(item['label'])[:100], item['state'] if fresh else 'unknown', str(item['detail'])[:300] if fresh else 'Stale NAS evidence; current state unverified'))
            if len(imported) > 30 or len({c['id'] for c in imported}) != len(imported):
                raise ValueError('Invalid remote check set')
            checks.append(check('nas-monitor', 'NAS monitoring', 'ok' if fresh else 'action', f'NAS checked {int(age(remote["checked_at_utc"], current)//60)} minutes ago' if fresh else 'NAS checks are stale'))
            checks.extend(imported)
        except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError):
            checks.append(check('nas-monitor', 'NAS monitoring', 'unknown', 'Cannot read a fresh NAS snapshot'))
    if 'worker_ssh' in config:
        try:
            code = WORKER_PROBE.replace('CONFIG', repr(config['worker']))
            result = subprocess.run([*config['worker_ssh'], 'python3 -'], input=code.encode(), capture_output=True, timeout=45, check=True)
            worker = json.loads(result.stdout)
            valid = worker['api_health'] and worker['web_health'] and all(s['running'] and s['image_matches'] and s['private'] and s['healthy'] for s in worker['services']) and len(worker['services']) == len(config['worker']['containers'])
            if config['worker'].get('expected_restart_policy'):
                valid = valid and all(s['restart_policy'] == config['worker']['expected_restart_policy'] for s in worker['services'])
            checks.append(check('app-services', 'Application services', 'ok' if valid else 'action', 'API and web respond; expected images running privately' if valid else 'A service is stopped, changed or unexpectedly exposed'))
            checks.append(check('worker-capacity', 'Worker storage', 'ok' if worker['free_bytes'] >= config['minimum_free_bytes'] else 'action', f'{worker["free_bytes"] / 1024**3:.1f} GiB available'))
            checks.append(check('symphony', 'Background coding worker', 'ok' if worker['symphony_stopped'] else 'action', 'Stopped as required' if worker['symphony_stopped'] else 'Unexpected background writer'))
        except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError):
            checks.extend(check(ident, label, 'unknown', 'Worker could not be checked') for ident, label in [('app-services', 'Application services'), ('worker-capacity', 'Worker storage'), ('symphony', 'Background coding worker')])
    if 'nas_vm' in config:
        try:
            expected = config['nas_vm']
            result = subprocess.run(['docker', 'inspect', expected['container']], capture_output=True, timeout=15, check=True)
            item = json.loads(result.stdout)[0]
            valid = item['State']['Running'] and item['Image'] == expected['image'] and item['HostConfig']['RestartPolicy']['Name'] == 'unless-stopped' and item['HostConfig']['PortBindings'] == expected['port_bindings']
            checks.append(check('worker-vm', 'Isolated worker VM', 'ok' if valid else 'action', 'Running; boot restart policy and access match' if valid else 'Worker VM state or configuration changed'))
        except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError):
            checks.append(check('worker-vm', 'Isolated worker VM', 'unknown', 'NAS worker VM could not be checked'))
    for service in config.get('capture_services', []):
        try:
            result = subprocess.run(['systemctl', '--user', 'show', service, '--property=Result', '--value'], capture_output=True, timeout=10, check=True).stdout.decode().strip()
            checks.append(check('nas-capture-service', 'NAS capture task', 'ok' if result == 'success' else 'action', 'Last task exited successfully' if result == 'success' else 'Last capture task failed; previous recovery copies are preserved'))
        except (OSError, ValueError, subprocess.SubprocessError):
            checks.append(check('nas-capture-service', 'NAS capture task', 'unknown', 'Capture task result is unavailable'))
    if 'capacity_path' in config:
        try:
            checks.append(capacity(config['capacity_id'], config['capacity_label'], config['capacity_path'], config['minimum_free_bytes']))
        except OSError:
            checks.append(check(config['capacity_id'], config['capacity_label'], 'unknown', 'Storage could not be checked'))
    for ident, item in config.get('receipts', {}).items():
        try:
            path = receipt_path(item)
            if item.get('archive_root'):
                r = read_json(path)
                archive = Path(r['archive'])
                if archive.is_symlink() or archive.parent.resolve() != Path(item['archive_root']).resolve() or archive.stat().st_size != r['bytes']:
                    raise ValueError('Recovery archive missing or changed')
            checks.append(receipt_check(ident, item['label'], path, current, item.get('max_age_seconds', 36*3600)))
        except (OSError, ValueError, KeyError, TypeError):
            checks.append(check(ident, item['label'], 'unknown', 'Verified receipt or archive is unavailable'))
    if 'capture_latest' in config:
        try:
            r = read_json(config['capture_latest'])
            if r.get('status') != 'encrypted-capture-awaiting-copied-restore' or not re.fullmatch('[0-9a-f]{64}', r['sha256']):
                raise ValueError('Invalid capture receipt')
            archive = Path(config['capture_latest']).parent/'archives'/r['archive']
            if Path(r['archive']).name != r['archive'] or archive.is_symlink() or archive.stat().st_size != r['bytes']:
                raise ValueError('Encrypted capture file is missing or changed')
            seconds = age(r['captured_at_utc'], current)
            checks.append(check('nas-capture', 'NAS encrypted capture', 'ok' if seconds < 36*3600 else 'action', f'Captured {int(seconds // 3600)} hours ago; copied restore and cloud verification are separate'))
        except (OSError, ValueError, KeyError, TypeError):
            checks.append(check('nas-capture', 'NAS encrypted capture', 'unknown', 'No completed encrypted capture yet'))
    for item in config.get('http_checks', []):
        try:
            request = urllib.request.Request(item['url'])
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            try:
                with opener.open(request, timeout=10) as response:
                    actual = response.status
            except urllib.error.HTTPError as error:
                actual = error.code
                error.close()
            checks.append(check(item['id'], item['label'], 'ok' if actual == item['expected_status'] else 'action', f'HTTP {actual}; expected {item["expected_status"]}'))
        except (OSError, ValueError):
            checks.append(check(item['id'], item['label'], 'unknown', 'Endpoint could not be reached'))
    return {'format': 1, 'checked_at_utc': current.isoformat(), 'checks': list({c['id']: c for c in checks}.values())}


def record(snapshot, output):
    """Persist the current incident set; unchanged polls do not create new alerts."""
    p = Path(output)
    incident_path = p.with_name('incidents.json')
    try:
        previous = read_json(incident_path)
    except FileNotFoundError:
        previous = {'open': {}, 'changes': []}
    opened = {c['id']: {'label': c['label'], 'state': c['state']} for c in snapshot['checks'] if c['state'] != 'ok'}
    observed = {c['id'] for c in snapshot['checks']}
    for ident, item in previous['open'].items():
        if ident not in observed:
            opened[ident] = {'label': item['label'], 'state': 'unknown'}
            snapshot['checks'].append(check(ident, item['label'], 'unknown', 'This check was not observed; recovery is unverified'))
    changes = previous.get('changes', [])[-99:]
    for ident in sorted(set(previous['open']) | set(opened)):
        if previous['open'].get(ident) != opened.get(ident):
            changes.append({'checked_at_utc': snapshot['checked_at_utc'], 'id': ident, 'state': opened.get(ident, {}).get('state', 'recovered')})
    atomic_json(incident_path, {'open': opened, 'changes': changes})
    atomic_json(p, snapshot)


def sync_evidence(config):
    """Send only verification metadata, never archives, keys or collection data."""
    fields = {'status', 'source_commit', 'sha256', 'completed_at_utc', 'restore_verified', 'member_checksums_verified', 'saved_image_ids_verified', 'all_downloaded_parts_verified', 'downloaded_manifest_verified', 'full_archive_sha256_verified', 'owner_only_metadata_verified', 'cms_authenticated_decryption_verified'}
    payload = {}
    for ident, name in [('mac-backup', 'mac.json'), ('cloud-backup', 'cloud.json')]:
        item = config['receipts'][ident]
        checked = collect({'receipts': {ident: item}})['checks'][0]
        if checked['state'] == 'unknown':
            raise ValueError('Cannot synchronize unverified recovery evidence')
        r = read_json(receipt_path(item))
        payload[name] = {key: r[key] for key in fields if key in r}
    code = """import json,os,tempfile
from pathlib import Path
r=Path(ROOT);assert r.is_dir() and not r.is_symlink() and not r.stat().st_mode & 0o077
for name,value in PAYLOAD.items():
 assert name in {'mac.json','cloud.json'}
 with tempfile.NamedTemporaryFile(mode='w',dir=r,delete=False) as f:
  os.chmod(f.name,0o600);json.dump(value,f);f.flush();os.fsync(f.fileno());temporary=Path(f.name)
 temporary.replace(r/name)
""".replace('ROOT', repr(config['evidence_root'])).replace('PAYLOAD', repr(payload))
    result = subprocess.run(config['evidence_ssh'], input=code.encode(), capture_output=True, timeout=45)
    if result.returncode:
        raise ValueError('NAS evidence synchronization failed')


def serve(config, report, output, port):
    report = Path(report)
    if report.is_symlink() or not report.is_file():
        raise ValueError('Dashboard must be a regular file')
    def refresh():
        while True:
            try:
                record(collect(config), output)
            except Exception:
                # Failed collection is unknown, never a preserved green snapshot.
                record({'format': 1, 'checked_at_utc': now().isoformat(), 'checks': [check('collector', 'Operations checks', 'unknown', 'Collector failed')]}, output)
            time.sleep(60)
    threading.Thread(target=refresh, daemon=True).start()
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.headers.get('Host') not in (f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}'):
                self.send_error(403)
                return
            path = self.path.split('?')[0]
            if path in ('/', '/project-dashboard.html'):
                body, kind = report.read_bytes(), 'text/html; charset=utf-8'
            elif path == '/operations.json':
                try:
                    value = read_json(output)
                    if age(value['checked_at_utc'], now()) > 180:
                        raise ValueError('Stale collector')
                    body = json.dumps(value).encode()
                except (OSError, ValueError, KeyError):
                    self.send_error(503)
                    return
                kind = 'application/json'
            else:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header('Content-Type', kind)
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Referrer-Policy', 'no-referrer')
            self.send_header('Content-Security-Policy', "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'")
            self.end_headers()
            self.wfile.write(body)
        def log_message(self, *args):
            pass
    server = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    print(f'http://127.0.0.1:{server.server_port}/#operations', flush=True)
    server.serve_forever()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['collect', 'serve', 'sync-evidence'])
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--report', type=Path)
    parser.add_argument('--port', type=int, default=0)
    args = parser.parse_args()
    os.umask(0o077)
    config = private_config(args.config)
    if args.mode == 'sync-evidence':
        sync_evidence(config)
    elif args.mode == 'collect':
        record(collect(config), args.output)
    else:
        serve(config, args.report, args.output, args.port)


if __name__ == '__main__':
    main()
